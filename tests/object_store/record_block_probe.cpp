/*
 * Copyright (C) 2026 EloqData Inc.
 * SPDX-License-Identifier: Apache-2.0
 */
#include <fcntl.h>
#include <unistd.h>

#include <charconv>
#include <iostream>

#include "absl/strings/str_cat.h"
#include "bycorf/io/storage.h"
#include "bycorf/net/server.h"
#include "lavik/metrics.h"
#include "lavik/object_store/azure_blob_client.h"
#include "lavik/object_store/record_block_objects.h"
#include "lavik/object_store/s3_client.h"
#include "lavik/storage/engine.h"
#include "lavik/tx/tx_shard.h"

namespace {
using namespace lavik;
using namespace storage;
using namespace object_store;
using bycorf::Task;
using bycorf::Worker;
using Work = std::function<Task<absl::Status>(StorageEngine&, Worker&)>;

class StorageRun final : public bycorf::Service {
 public:
  StorageRun(StorageEngine& storage, const Work& work)
      : storage_(storage), work_(work) {}
  void Prepare(unsigned) override {}
  void Stop() noexcept override {}
  Task<absl::Status> Run(Worker& worker, bycorf::ServiceContext) override {
    BindMemoryAccountingShard(worker.id());
    tx::TxRuntime::Get()->shard(worker.id()).Bind(worker);
    result_ = co_await storage_.InitializeWorker(worker);
    if (result_.ok()) result_ = co_await work_(storage_, worker);
    worker.RequestStop();
    co_return result_;
  }
  void FinalizeWorker(Worker& worker) noexcept override {
    storage_.FinalizeWorker(worker);
  }
  absl::Status result_ = absl::UnknownError("worker did not run");

 private:
  StorageEngine& storage_;
  const Work& work_;
};

StorageEngineOptions Options(const std::string& path) {
  StorageEngineOptions options;
  options.data_files_ = {path};
  options.database_count_ = 1;
  options.defrag_paused_ = true;
  options.record_crc_ = true;
  options.flush_max_ms_ = 5;
  options.buffers_.storage_write_buffer_count_ = 2;
  return options;
}
absl::Status RunStorage(StorageEngineOptions options, const Work& work) {
  StorageEngine storage(std::move(options));
  auto status = storage.Prepare(1);
  if (!status.ok()) return status;
  StorageRun service(storage, work);
  bycorf::Server server;
  server.AddService(&service);
  bycorf::ServerOptions runtime;
  runtime.thread_count_ = 1;
  runtime.pin_workers_ = false;
  runtime.recv_buffer_count_ = 0;
  status = server.Start(runtime);
  if (!status.ok()) return status;
  server.WaitUntilStopped();
  return service.result_;
}

constexpr std::array<std::string_view, 3> keys{"first", "second", "third"};
const std::array<std::string, 3> values{"one", std::string("two\0bytes", 9),
                                        "three"};

Task<absl::Status> WriteAndFlush(StorageEngine& storage, Worker& worker) {
  for (std::size_t i = 0; i < keys.size(); ++i) {
    auto set = co_await storage.Set(0, keys[i], values[i]);
    if (!set.ok()) co_return set.status();
    for (;;) {
      const auto stats = co_await storage.DurabilityStats();
      if (stats.failed_) co_return absl::InternalError("storage flush failed");
      if (!stats.pending()) break;
      auto waited =
          co_await bycorf::SleepFor(worker, std::chrono::milliseconds(1));
      if (!waited.ok()) co_return waited;
    }
  }
  co_return absl::OkStatus();
}

// A free slot can retain a CRC-valid header from its previous allocation.
absl::Status SeedInactiveSlot(const std::string& target, std::uint32_t slot) {
  std::array<std::byte, kBlockHeaderSlotBytes> stale;
  EncodeBlockHeader({.allocation_epoch_ = 77,
                     .committed_bytes_ = kBlockHeaderBytes + kDirectIoAlignment,
                     .record_count_ = 1,
                     .header_sequence_ = 2,
                     .layout_worker_count_ = 1},
                    stale);
  const int fd = ::open(target.c_str(), O_WRONLY | O_CLOEXEC);
  if (fd < 0) return absl::InternalError("open fixture target");
  const bool written =
      ::pwrite(fd, stale.data(), stale.size(),
               LocalBlockOffset(slot) + kBlockHeaderSlotBytes) ==
          static_cast<ssize_t>(stale.size()) &&
      ::fdatasync(fd) == 0;
  if (::close(fd) != 0 || !written)
    return absl::InternalError("seed inactive block slot");
  return absl::OkStatus();
}

template <typename Client>
absl::Status Exercise(const Client& client, const std::string& source,
                      const std::string& target) {
  constexpr std::uint64_t remote_id = 1001;
  RecordBlockObjects<Client> writer(client, remote_id);
  std::vector<std::uint32_t> offsets;
  std::uint64_t source_id = 0;
  std::optional<RecordBlockImage> saved;
  auto options = Options(source);
  options.record_block_flush_ =
      [&](RecordBlockFlush flush) -> Task<absl::Status> {
    auto status = co_await writer.Upload(flush);
    if (!status.ok()) co_return status;
    offsets.push_back(flush.offset_);
    source_id = flush.source_block_id_;
    co_return absl::OkStatus();
  };
  auto status = RunStorage(
      std::move(options),
      [&](StorageEngine& storage, Worker& worker) -> Task<absl::Status> {
        auto status = co_await WriteAndFlush(storage, worker);
        if (!status.ok()) co_return status;
        if (offsets.size() != keys.size())
          co_return absl::DataLossError("expected three real flushes");
        RecordBlockObjects<Client> reader(client, remote_id);
        auto image = co_await reader.Download();
        if (!image.ok()) co_return image.status();
        saved.emplace(*std::move(image));

        const std::string middle = absl::StrCat(remote_id, "_", offsets[1]);
        auto original = co_await client.Get(middle);
        if (!original.ok()) co_return original.status();
        original->at(0) ^= 1;
        auto tag = co_await client.Put(middle, *original);
        if (!tag.ok()) co_return tag.status();
        auto corrupt = co_await reader.Download();
        if (!absl::IsDataLoss(corrupt.status()))
          co_return absl::InternalError("accepted corrupt header");
        status = co_await client.Delete(middle);
        if (!status.ok()) co_return status;
        auto gap = co_await reader.Download();
        if (!absl::IsDataLoss(gap.status()))
          co_return absl::InternalError("accepted missing interior fragment");
        co_return absl::OkStatus();
      });
  if (!status.ok()) return status;

  // Prepare formats the fresh target's metadata. Only the downloaded objects
  // supply block content and the installation must activate the destination.
  {
    StorageEngine fresh(Options(target));
    status = fresh.Prepare(1);
    if (!status.ok()) return status;
  }
  const std::uint32_t slot = LocalBlockId(source_id) == 3 ? 4 : 3;
  status = SeedInactiveSlot(target, slot);
  if (!status.ok()) return status;
  status = saved->Install(target, slot);
  if (!status.ok()) return status;
  if (!absl::IsAlreadyExists(saved->Install(target, slot)))
    return absl::InternalError("occupied slot accepted");

  return RunStorage(
      Options(target),
      [](StorageEngine& storage, Worker&) -> Task<absl::Status> {
        for (std::size_t i = 0; i < keys.size(); ++i) {
          auto got = co_await storage.Get(0, keys[i]);
          if (!got.ok()) co_return got.status();
          auto data = got->value_bytes();
          if (std::string_view(reinterpret_cast<const char*>(data.data()),
                               data.size()) != values[i])
            co_return absl::DataLossError(
                "cold recovery returned wrong record");
        }
        co_return absl::OkStatus();
      });
}
}  // namespace

int main(int argc, char** argv) {
  if (argc != 5) return 2;
  std::string_view provider(argv[1]), port(argv[2]);
  net::HttpEndpoint endpoint{.address_ = "127.0.0.1"};
  auto [end, ec] = std::from_chars(port.begin(), port.end(), endpoint.port_);
  if (ec != std::errc{} || end != port.end() || !endpoint.port_) return 2;
  std::string container, account, secret;
  for (auto* field : {&container, &account, &secret})
    if (!std::getline(std::cin, *field) || field->empty()) return 2;
  InitWorkerMetrics(1);
  tx::TxRuntime::Create(1);
  auto status = InitMemoryLimit(1024ULL * 1024 * 1024, 1);
  if (!status.ok()) return 1;
  if (provider == "azure") {
    auto client = AzureBlobClient::Create(endpoint, account, container, secret,
                                          AzureAccountAddressing::kPath);
    status =
        client.ok() ? Exercise(*client, argv[3], argv[4]) : client.status();
  } else if (provider == "s3") {
    S3Client client(endpoint, "us-east-1", container, {account, secret});
    status = Exercise(client, argv[3], argv[4]);
  } else
    return 2;
  if (!status.ok()) std::cerr << status << '\n';
  return status.ok() ? 0 : 1;
}

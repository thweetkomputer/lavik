# Lavik v0.1.0 and Aerospike: YCSB throughput and tail latency

**English** | [简体中文](README.zh-CN.md)

Both databases were freshly loaded with **100 million records, each containing 10 × 128 B fields**. The complete **A/B/C/D × 100K/unlimited** matrix contains 16 measured windows of 300 seconds each; all warmup and measured phases have zero errors. **Lavik defrag stays enabled throughout.**

Aerospike uses default performance settings and original host policy. Lavik uses 12 workers with 4 CPUs for system/IRQ isolation and io_uring on a raw RAID0 partition. CPU allocation and database settings differ between these deployments.

## Throughput and tail latency

![YCSB throughput](ycsb-qps.png)

Measured unlimited total-throughput differences relative to Aerospike: A **+4.36%**, B **+25.13%**, C **+28.76%**, D **+25.56%**.

Each operation cell is **operation QPS; p99 / p99.9 / p99.99 (ms)**. Read/write percentiles remain separate. Reaching a rate target does not imply lower tail latency.

| Workload | Rate limit | Operation | Aerospike (defaults, original host policy) | Lavik (100ms, 12+4 isolation) |
|---|---|---|---:|---:|
| A | Unlimited | Total QPS | 507,401 | 529,501 |
| A | Unlimited | READ | 253,704; 1.407 / 2.953 / 5.219 | 264,758; 2.105 / 5.083 / 6.883 |
| A | Unlimited | UPDATE | 253,697; 1.196 / 2.255 / 3.561 | 264,743; 1.532 / 2.831 / 4.435 |
| A | 100K | Total QPS | 99,883 | 99,966 |
| A | 100K | READ | 49,932; 0.342 / 0.437 / 1.317 | 49,987; 0.372 / 0.530 / 1.046 |
| A | 100K | UPDATE | 49,951; 0.292 / 0.385 / 1.208 | 49,979; 0.337 / 0.474 / 1.046 |
| B | Unlimited | Total QPS | 461,404 | 577,373 |
| B | Unlimited | READ | 438,351; 1.274 / 2.313 / 4.539 | 548,492; 0.776 / 1.818 / 4.835 |
| B | Unlimited | UPDATE | 23,053; 1.087 / 1.853 / 3.389 | 28,881; 0.702 / 1.578 / 4.467 |
| B | 100K | Total QPS | 99,827 | 99,967 |
| B | 100K | READ | 94,829; 0.374 / 0.498 / 1.417 | 94,968; 0.482 / 0.856 / 1.920 |
| B | 100K | UPDATE | 4,998; 0.321 / 0.426 / 1.348 | 4,999; 0.410 / 0.653 / 1.436 |
| C | Unlimited | READ | 461,251; 1.253 / 1.982 / 4.431 | 593,911; 0.707 / 1.556 / 5.119 |
| C | 100K | READ | 99,902; 0.379 / 0.481 / 1.322 | 99,970; 0.406 / 0.495 / 1.173 |
| D | Unlimited | Total QPS | 460,167 | 577,808 |
| D | Unlimited | READ | 437,177; 1.246 / 2.055 / 4.379 | 548,915; 0.790 / 1.824 / 4.683 |
| D | Unlimited | INSERT | 22,991; 1.077 / 1.754 / 2.611 | 28,893; 0.724 / 1.589 / 4.443 |
| D | 100K | Total QPS | 99,901 | 99,961 |
| D | 100K | READ | 94,906; 0.351 / 0.442 / 1.275 | 94,962; 0.368 / 0.488 / 1.035 |
| D | 100K | INSERT | 4,995; 0.311 / 0.404 / 1.186 | 4,999; 0.354 / 0.479 / 1.205 |

![p99](ycsb-p99.png)

![p99.9](ycsb-p999.png)

![p99.99](ycsb-p9999.png)

## Hardware and storage

| Item | Configuration |
|---|---|
| Server | Azure Standard_L16aos_v4, Japan West zone 2; AMD EPYC 9V74; 16 logical CPUs / 8 physical cores; 125.8 GiB Linux RAM |
| Client | Azure Standard_F32als_v6; AMD EPYC 9V74; 32 physical cores, 62.8 GiB RAM; Java 17; YCSB process restricted to CPUs 0–15 |
| OS | Ubuntu 24.04; Linux 6.17.0-1022-azure on both machines; no reboot |
| Network | One client 10.84.0.5 → server 10.84.1.4; kernel TCP over accelerated mlx5 |
| Disks | Six local NVMe, each 1,919,850,381,312 B; Linux RAID0, 512 KiB chunk |
| Partitions | Two distinct raw partitions; each 1,099,494,850,560 B; 24 MiB alignment; no filesystem; fully zeroed before load |
| Monitoring | Per-phase effective configuration, process, IRQ, storage and client counters; Lavik metrics enabled |

## Data and workloads

| Workload | READ | UPDATE | INSERT | Read distribution |
|---|---:|---:|---:|---|
| A | 50% | 50% | 0 | Uniform |
| B | 95% | 5% | 0 | Uniform |
| C | 100% | 0 | 0 | Uniform |
| D-Uniform | 95% | 0 | 5% | Fixed original 100M keys |

| Records | Aerospike | Lavik |
|---|---:|---:|
| Initial | 100,000,000 | 100,000,000 |
| After complete matrix | 108,497,069 | 110,271,711 |

## Database and host configuration

| Setting | Aerospike | Lavik |
|---|---|---|
| Version | Community Edition 8.1.2.4-4 | v0.1.0 standard x86_64 release |
| Storage | `storage-engine device`, raw RAID0 partition | `--storage=uring`, raw RAID0 partition |
| CPU | Original host policy, CPUs 0–15; defaults `service-threads=80`, `auto-pin=none` | 12 pinned workers on CPUs 0–11; system tasks, workqueue and NIC IRQs on CPUs 12–15 |
| systemd | Default system.slice, no affinity override | lavik-bench.slice, AllowedCPUs/CPUAffinity=0–11 |
| Flush | Defaults: 1 MiB, 1000 ms | 128 KiB write chunks, 100 ms |
| Cache | Defaults: max-write-cache=64 MiB, post-write-cache=256 MiB, read-page-cache=false | Release defaults |
| Index | Default indexes-memory-budget=0 | Release defaults |
| GC / defrag | Defaults | Enabled; 8 active jobs/device; block and record sleep=0 |
| READ | All 10 bins | HGETALL, all 10 fields |
| UPDATE | REPLACE_ONLY, all 10 bins | LAVIK.HREPLACE, all 10 fields |
| INSERT | CREATE_ONLY | HMSET, redis.scanindex=none |
| Binding | YCSB Aerospike, Java client 3.1.2 | YCSB Redis, Jedis 3.9.0 |
| Replication / TTL | One node, RF=1, namespace ycsb; default TTL 0 | One instance DB0, no replica, no TTL |

Lavik is the unmodified standard release package: `v0.1.0 / feb61224e414c5653fd09560e20c9d214db1e3ac`; SHA-256 `7bf8d204a137678cee0e1a621b02661181373fbbfe1366bc1c201942b9dcf420`. Aerospike SHA-256 `6e1b2bd6deebd5816f4f369ac1db4151217ed0be3b66578bdd6f15c24e6af8d0`.

## Measurement method and limits

- Matches the [September YCSB method](../ycsb-rerun-2026-09-13/README.md): fresh 100M-record databases, C/A/B/D order, 100K then unlimited for each workload; Aerospike first, then Lavik. Databases share the RAID0 sequentially, never concurrently. There are no clears or restarts between measured cases.
- Each case uses 256 YCSB workers, a separate one-million-operation warmup JVM and a fresh 300-second measurement JVM. `-target 100000` is the total rate across threads and operations. The measurement operation cap is 2 billion, so the timer controls termination. Initial JIT/ramp-up stays in the measured window.
- `fieldcount=10`, `fieldlength=128`, constant field lengths; `readallfields=true`, `writeallfields=true`; hashed key names; uniform reads; no SCAN or read-modify-write; 10,000 ms client timeouts. Raw field payload is 128 GB (119.21 GiB), excluding keys, field names, indexes and record metadata.
- D reads only the original 100M keys. Warmup/measured inserts use disjoint starting IDs: 2B/4B at 100K, 6B/8B unlimited. Equal starting sizes do not imply equal final sizes because D insert counts depend on throughput.
- Every load reconciles exactly 100M successful INSERTs with the server count. Each database is stopped cleanly and recovered after loading. Eight distributed records, all ten field lengths and their SHA-256 values are compared before/after recovery. Every phase reconciles client successes with database command counters and record-count deltas; errors must remain zero.
- Aerospike configuration changes only required cluster/listener/namespace/RF/device settings. CPU scheduling, IRQs, threads, caches, flushing, index budget and reclamation retain defaults. Effective values are recorded before/after every phase. Lavik's separate 12+4 CPU/IRQ policy is applied only after Aerospike stops, and restored afterward. Completion IRQ destinations and per-CPU interrupt deltas verify that benchmark NIC completion IRQs do not execute on Lavik worker CPUs during phases.
- Lavik defrag is enabled throughout load, recovery, warmup and measurement, with 8 active jobs/device and no additional sleep. `CONFIG GET defrag-paused` and `DEFRAG STATUS` are captured per phase. Tomb Raider and active expiration use release defaults in this YCSB group. Periodic 100 ms flushing is not a per-write synchronous durability guarantee.
- CPU numbers are logical CPUs: workers 0–11 occupy six physical cores and system/IRQ CPUs 12–15 occupy two separate physical cores (SMT2). Source-based routing sends replies from 10.84.1.4 through eth1/table 101; the management interface is not the benchmark reply path.
- QPS = successful operations / actual YCSB RunTime. Total QPS sums successful reads and writes. Each operation's p99/p99.9/p99.99 comes from its complete-window ordinary HDR histogram, not an average of interval percentiles; intended histograms remain in raw logs. Equal YCSB worker counts do not imply equal TCP connection counts.
- This is a new measurement batch. It reuses no historical timing results. The client model/CPU differs from the September report and is limited to 16 CPUs for the benchmark. The standard GCC/x86-64-v2 Lavik package replaces the old native build. The raw partitions have the same capacity/alignment but new locations. These differences preclude interpreting historical changes as code-only effects.
- Three setup attempts failed before any records were inserted: missing Aerospike runtime directories, a missing `python` launcher alias, then listener readiness preceding partition ownership. Their logs are retained under `evidence/setup-failure-*`. Runtime prerequisites were completed and readiness now waits for all 4096 master partitions. The Java bindings and database performance settings were unchanged. None of these setup attempts is a measured window.
- The custom YCSB source is `eloqdata/YCSB@a47bf01c4f197d2ff2eecbbebd9743da5a1cae47`, with the recorded LAVIK.HREPLACE command-name patch. The exact binding source and JAR hashes are archived.
- One five-minute measurement per cell; run-to-run variability and confidence intervals are not estimated. Product order is fixed. CPU allocation, host policies, caches and persistence differ between the two requested deployments, so the result is not a single-variable comparison.

| Database | Measured window (UTC) | Cases |
|---|---|---:|
| Aerospike | 2026-10-13T09:54:41Z – 2026-10-13T10:35:42Z | 8 |
| Lavik | 2026-10-13T10:39:09Z – 2026-10-13T11:20:04Z | 8 |

At completion the original CPU/IRQ policy is restored, Lavik has stopped cleanly, and Aerospike has recovered with its final data verified. These counts describe the end of the YCSB matrix. After complete evidence archival and offline verification, the six scratch devices were rebuilt with authorization for the subsequent latest-peer and Lavik 1B batch; the YCSB datasets are no longer retained.

## Evidence and reproduction

[Results JSON](results.json) · [Operation CSV](summary.csv) · [Binary identity](binaries.json) · [Server inventory](server-inventory.json) · [Client inventory](client-inventory.json) · [Network path](network-path.json) · [YCSB source](evidence/client-source/source.json) · [Client JAR hashes](evidence/client-jars.sha256) · [All phases](evidence/phases.json) · [Runner](evidence/runner.py) · [Host policy](evidence/host_policy.py) · [Client commands](evidence/ycsb_client.py) · [Effective Aerospike configuration](evidence/aerospike.conf) · [Storage](evidence/storage-after.json) · [Completion](evidence/complete.json) · [Checksums](SHA256SUMS)

```sh
python3 perf_reports/lavik-v0.1.0-aerospike-ycsb-2026-10-13/verify_report.py
python3 perf_reports/lavik-v0.1.0-aerospike-ycsb-2026-10-13/build_assets.py
```

Offline verification needs Python 3.11+; figure generation needs Matplotlib 3.11.2. The verifier checks both fresh loads, all 32 phases, 16 measured windows, 28 operation rows, per-phase host/database policy, both language tables and archived file hashes. It never starts databases or opens raw devices. A live rerun needs new scratch media and unused D insert ranges. Private keys, executable downloads and generated databases are not included.

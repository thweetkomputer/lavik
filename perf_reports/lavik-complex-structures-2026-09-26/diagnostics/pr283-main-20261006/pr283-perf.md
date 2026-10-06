# PR #283：独立 ZINCRBY perf

main `5a3903d9` 与候选 `ace4198b`，大对象 100 MiB / 1024 B / 8 keys、小对象 64 KiB / 128 B / 64 keys，均为 c80。每个版本分别新建数据，保持与正式配对相同的生产二进制和服务配置。

每个 worker 单独以 99 Hz task-clock、16 KiB DWARF 采样 25 秒；命令与存储计数窗口为 30 秒。各线程 self 占比按 approximate event count 加权，保留 0.1% 截断的缺失质量，不重新归一化。含轮询、后台和内核 CPU，不能当作请求专属 CPU 时间，也不能用不同窗口的命令数换算 CPU/命令。

符号口径：SipHash12 为含 `::SipHash12(` 的符号；memmove 为 `__memmove` 前缀；mimalloc 为 `_mi_` 或 `mi_` 前缀。只统计报告中的自身 CPU 占比，不是分配次数或复制字节数。

| 大小 / 版本 | SipHash12 | memmove | mimalloc | Worker::RunOnce | 报告覆盖率 |
|---|---:|---:|---:|---:|---:|
| 100 MiB / 1024 B / parent | 2.948% | 2.324% | 3.899% | 21.415% | 87.009% |
| 100 MiB / 1024 B / candidate | 3.147% | 2.202% | 3.483% | 21.953% | 88.049% |
| 64 KiB / 128 B / parent | 3.676% | 3.350% | 5.207% | 11.139% | 82.436% |
| 64 KiB / 128 B / candidate | 2.977% | 3.241% | 4.570% | 10.635% | 82.627% |

这四组采样中，mimalloc 和 memmove 的自身占比均有所下降，幅度较小；大对象 SipHash12 占比上升，小对象下降。占比变化与减少临时分配和复制的方向相符，但不能据此证明绝对 CPU 时间、分配次数或整体吞吐的改变量。

采样仅覆盖 ZINCRBY c80，没有覆盖正式对照中小对象 ZSCORE c320 的异常，不能用于解释该读取回退；[六个异常点的配置核验](small-read-c320-audit.json)保留了这一限制。

## 存储计数窗口

| 大小 / 版本 | ZINCRBY calls | 读取次数/命令 | 读取字节/命令 | 窗口写入次数 |
|---|---:|---:|---:|---:|
| 100 MiB / 1024 B / parent | 1152319 | 0.208696 | 18878.819 | 2204195 |
| 100 MiB / 1024 B / candidate | 1156682 | 0.209192 | 19091.902 | 2214822 |
| 64 KiB / 128 B / parent | 2387972 | 0.096662 | 10829.424 | 4321647 |
| 64 KiB / 128 B / candidate | 2567692 | 0.079661 | 9132.500 | 4598627 |

计数为 server-wide 增量，包含后台活动和采集边界重叠；独立预置的物理页布局和后续写入演化可能不同。它们不是逐请求 I/O 跟踪。此改动保留存储读取和可变快照的重写编码，不能把这里的物理计数差异归因为源码减少了存储读取。正式 QPS 取自独立的三轮配对，带 perf 的吞吐不混入。

## 每组前十个 self 热点

为便于阅读，表内函数参数和过长符号省略；完整符号保留在聚合 JSON 和原始 self 报告中。

### 100 MiB / 1024 B / parent

| 符号 | 自身占比 |
|---|---:|
| `bycorf::Worker::RunOnce` | 21.415% |
| `bycorf::Worker::PollStorage` | 3.130% |
| `lavik::storage::{anonymous}::SipHash12` | 2.948% |
| `absl::lts_20250512::crc_internal::{anonymous}::CRC32AcceleratedX86ARMCombinedMultipleStreams<3ul, 0ul, ` | 2.394% |
| `__memmove_avx512_unaligned_erms` | 2.324% |
| `handle_softirqs` | 2.118% |
| `lavik::storage::GroupedHashObject::FindRecord` | 2.069% |
| `_mi_theap_malloc_zero` | 1.942% |
| `_raw_spin_unlock_irqrestore` | 1.776% |
| `bycorf::Worker::DrainCrossCore` | 1.768% |

[原始报告](../../raw/lavik-diagnostic-parent5a3903d9-pr283-zincrby-104857600-1024-c80-20261006/diagnostic-c80/)

### 100 MiB / 1024 B / candidate

| 符号 | 自身占比 |
|---|---:|
| `bycorf::Worker::RunOnce` | 21.953% |
| `bycorf::Worker::PollStorage` | 3.669% |
| `lavik::storage::{anonymous}::SipHash12` | 3.147% |
| `absl::lts_20250512::crc_internal::{anonymous}::CRC32AcceleratedX86ARMCombinedMultipleStreams<3ul, 0ul, ` | 2.574% |
| `handle_softirqs` | 2.303% |
| `__memmove_avx512_unaligned_erms` | 2.202% |
| `lavik::storage::GroupedHashObject::FindRecord` | 2.098% |
| `_raw_spin_unlock_irqrestore` | 1.901% |
| `bycorf::Worker::DrainCrossCore` | 1.856% |
| `do_syscall_64` | 1.811% |

[原始报告](../../raw/lavik-diagnostic-candidateace4198b-pr283-zincrby-104857600-1024-c80-20261006/diagnostic-c80/)

### 64 KiB / 128 B / parent

| 符号 | 自身占比 |
|---|---:|
| `bycorf::Worker::RunOnce` | 11.139% |
| `lavik::storage::{anonymous}::SipHash12` | 3.676% |
| `_mi_theap_malloc_zero` | 3.356% |
| `__memmove_avx512_unaligned_erms` | 3.350% |
| `handle_softirqs` | 3.119% |
| `absl::lts_20250512::hash_internal::LowLevelHashLenGt32` | 2.917% |
| `bycorf::Worker::PollStorage` | 2.783% |
| `absl::lts_20250512::crc_internal::{anonymous}::CRC32AcceleratedX86ARMCombinedMultipleStreams<3ul, 0ul, ` | 2.323% |
| `do_syscall_64` | 1.707% |
| `absl::lts_20250512::Status lavik::storage::{anonymous}::ValidateEntrySpan<lavik::storage::OrderedCollectionEntry>` | 1.583% |

[原始报告](../../raw/lavik-diagnostic-parent5a3903d9-pr283-zincrby-65536-128-c80-20261006/diagnostic-c80/)

### 64 KiB / 128 B / candidate

| 符号 | 自身占比 |
|---|---:|
| `bycorf::Worker::RunOnce` | 10.635% |
| `__memmove_avx512_unaligned_erms` | 3.241% |
| `handle_softirqs` | 3.056% |
| `bycorf::Worker::PollStorage` | 2.996% |
| `lavik::storage::{anonymous}::SipHash12` | 2.977% |
| `_mi_theap_malloc_zero` | 2.908% |
| `absl::lts_20250512::hash_internal::LowLevelHashLenGt32` | 2.877% |
| `absl::lts_20250512::crc_internal::{anonymous}::CRC32AcceleratedX86ARMCombinedMultipleStreams<3ul, 0ul, ` | 2.422% |
| `lavik::storage::StorageEngine::Impl::WriteRecordLocked` | 1.711% |
| `do_syscall_64` | 1.632% |

[原始报告](../../raw/lavik-diagnostic-candidateace4198b-pr283-zincrby-65536-128-c80-20261006/diagnostic-c80/)

[完整聚合输入与符号](pr283-self-comparison.json) · [profile 来源](profiles.json) · [命令计数核验](profile-command-audit.json) · [基数和原始结果核验](profile-observations.json) · [完整 QPS 配对](pr283-complete.md)

复算：`python3 summarize-perf.py --input profiles.json --report-root <report目录>`，再用本页的 `render-perf.py` 渲染。原始 `.perf` 和非空完整栈保留在本机记录路径；发布每线程 self、采样日志、来源、指标和零采样线程的空栈。

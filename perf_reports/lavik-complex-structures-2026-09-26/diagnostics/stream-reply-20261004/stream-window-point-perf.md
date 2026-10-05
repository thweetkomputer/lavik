# Stream 读取窗口：点查询 XRANGE 独立 perf

固定父版本 `adec3a34` 与候选 `5b9ebded`，8 个 100 MiB / 128 B Stream，点查 XRANGE c2560。复用同配置父版本的旧采样，候选使用独立的新预置数据，两次不是同期配对。全部 8 个 key 的 819,200 元素前后不变；无命令错误、服务正常退出，来源和二进制身份核对通过。

[采样来源](stream-window-point-profiles.json) · [逐线程和完整热点摘要](stream-window-point-self-comparison.json) · [self 输入哈希](stream-window-point-self-inputs.json) · [共用汇总脚本](summarize-stream-followup-self.py)

| 版本 | RunOnce self | PollStorage self | memmove self | 分配器入口 self | StreamRecordKey self | 读取数 / XRANGE | 读取字节 / XRANGE | 已报告 CPU 覆盖率 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| parent-point | 17.86% | 0.75% | 0.59% | 1.34% | 1.71% | 0.8437 | 7,209.99 | 88.55% |
| window-point | 17.02% | 0.84% | 0.64% | 1.49% | 1.59% | 0.8379 | 7,137.96 | 88.50% |

点查的主要 CPU 热点分布相近，每命令存储读取量也相近。与全量 c1 读取相比，这里没有出现同等幅度的轮询占比下降。分配器和复制的相对占比变化不能说明每条命令的分配次数或复制量变化，也不足以解释[三轮不采样对照](stream-window-large-reads.md)中点查 QPS 中位 −1.07%、p99 中位 +1.37% 的差异。不把本次采样中的命令数变化当作干净 QPS 收益。

父/候选计数窗口分别记录 4,054,631 / 4,150,131 条 XRANGE。每个服务线程记录 25 秒、99 Hz task-clock / 16 KiB DWARF，存储与命令计数窗口为 30 秒，不能相除换算 CPU/命令。self 以线程近似事件数加权，包含后台、轮询及内核 CPU；输入两位小数、0.1% 截断，约 11.5% 未报告份额不重新归一化。lost samples 均为零，零样本辅助线程保留；这不保证调用栈全部完整。IO 为服务整体计数，受后台、抓取边界和独立预置的物理布局影响。

#275 的两组独立 perf 已完成。全量读取收益仍见[全量诊断](stream-window-full-perf.md)及三轮对照；小对象写入和尾延迟回退、原 RDB 超时仍保留。PR 继续为草稿，不建议作为通用优化合并。新 head `291cbcb7` 的 CI 仍须单独完成。当前仅收尾已有候选，没有新增优化或 PR。

# Stream 读取窗口：全量 XRANGE 独立 perf

固定父版本 `adec3a34` 与候选 `5b9ebded`，8 个 100 MiB / 128 B Stream，XRANGE 全量 c1。候选重新预置独立数据；父版本复用此前同配置、同 SHA 的已完成采样，因此两次不是同期配对。所有 key 均保持 819,200 个元素；无命令错误、服务正常退出，来源和二进制身份核对通过。

[采样来源及限制](stream-window-full-profiles.json) · [两版本完整摘要](stream-window-full-self-comparison.json) · [原 self 输入哈希](stream-window-full-self-inputs.json) · [共用汇总脚本](summarize-stream-followup-self.py)

| 版本 | RunOnce self | PollStorage self | memmove self | 分配器入口 self | StreamRecordKey self | 读取数 / XRANGE | 读取字节 / XRANGE | 已报告 CPU 覆盖率 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| parent-full | 49.94% | 18.94% | 1.14% | 0.35% | 1.11% | 19,399.47 | 167,503,974 | 99.41% |
| window-full | 17.97% | 6.10% | 4.56% | 1.25% | 4.60% | 19,282.52 | 166,674,232 | 97.59% |

候选在这个已完成的全量读取诊断中，轮询 CPU 占比下降，字符串处理、复制及分配器的相对占比上升；每命令约 1.9 万次存储读取及约 167 MB 的读取字节基本不变。这与有限窗口重叠读页、提高吞吐的实现方向一致，但该比较不能单独证明因果，也不能把相对 CPU 占比当作每命令 CPU、分配次数或延迟分解。性能收益仍以[三轮不采样对照](stream-window-large-reads.md)为准。

每个服务线程记录 25 秒、99 Hz task-clock / 16 KiB DWARF；命令和存储计数窗口为 30 秒，两者不能相除推导 CPU/命令。self 按线程近似事件数加权，输入保留两位小数和 0.1% 截断，未报告比例不重新归一化。全部 lost samples 为零，零样本辅助线程仍保留；这不证明所有调用栈完整。存储计数包含后台、抓取边界重叠和不同物理布局的影响；父/候选窗口记录 15/64 条 XRANGE，计数较少。

这不是新的干净 QPS 点。[点查独立采样](stream-window-point-perf.md)也已完成，不从全量样本解释点查回退。完整 60 点对照中的小对象写入和尾延迟回退、原 RDB 超时仍保留，#275 继续为草稿，不建议作为通用优化合并。当前只验证已有候选，没有新增优化或 PR。新 head `291cbcb7` 的 CI 也不能由这些旧提交结果替代。

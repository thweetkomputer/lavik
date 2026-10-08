# 合并后 main `c55e52c9` 与四库随机增删

固定 main `c55e52c98d785dec9603d33ddcf55eab299eb11e`，包含 #286、#287、#288。原有 28 组命令网格选定 278 点：278 成功、0 失败；另外 4 组批量 HSET/SADD 导入完成。新增随机增删四库选定 160 点：159 点纳入曲线、1 点因长度范围检查留空，生成 10 张 QPS/p99 图。

[主报告](../../README.zh-CN.md) · [新增随机增删](mixed-writes.md) · [原有命令与三库差距](main-gap-summary.md) · [与上一轮 main 的观测对比](previous-main-comparison.md) · [构建与硬件](host-and-build.json) · [命令核验](main-command-audit.json) · [混合写核验](mixed-command-audit.json) · [绘图核验](report-audit.json)

原有图沿用此前协议：每点 8 秒，扩展 key 数 LSET 为 10 秒，pipeline=1，278 个选定测点和四组批量导入重新测量 Lavik；其他三库保留明确的历史源数据。新增图四库均重新测量、每点 30 秒；两种数据集不拼接为同一曲线。每次测量独占同一测试主机，构建与功能验证先完成；未在本轮吞吐窗口挂 perf。

原有 List/Stream/ZSet 覆盖 64 KiB、1 MiB、100 MiB/key 和 128/1024 B 元素；Hash/Set 及扩展 LSET 使用 1 MiB/50,000 keys、100 MiB/500 keys。新随机增删使用 8 MiB/8 keys、100 MiB/8 keys、1 KiB 元素。数据规模、key 数、协议、存储配置和来源均在图标题、manifest 和 raw 中保留。

两次旧命令扫描不是同期配对实验，Hash/Set 的进程 digest seed 与布局可能不同，不把主分支整体变化直接解释成 #288 的收益。此前 Fenwick 消融测量仍只代表其固定实测提交。

## 功能验证

- `unit-tests`：135 通过，0 跳过，0 失败。
- `native-tests-private-tmp`：74 通过，35 跳过，0 失败。
- `hash-native-tests-private-tmp`：16 通过，20 跳过，0 失败。

故障注入用例按生产构建配置跳过，不记作已执行。首次命令级验证被临时目录包装脚本中残留的旧路径白名单拦住，尚未启动测试；修正为本任务私有目录后，复用已核验 SHA 的二进制完成全部测试。初次启动失败日志保留，未伪装成数据库测试通过。

## 失败与收尾

20 个短时协议检查完成后、正式测点启动前，一次磁盘空闲检查遇到临时设备占用并拒绝继续。等待两次间隔 2 秒的空闲快照后通过原有检查，再开始正式测量；未跳过保护检查，未覆盖正式结果。原始启动日志保留。

原有 278 个选定点均成功，所有服务正常退出。

四库 200 次测量全部落盘后，Kvrocks RAID 已拆除，但收尾设备空闲检查又出现一次短暂占用。通过原有幂等恢复流程重试，并取得两次空闲快照后继续旧网格；没有重跑混合测点。见 [恢复记录](mixed-cleanup-retry.json)。

六块授权测试 NVMe 已恢复内核驱动；测试服务停止、Kvrocks RAID 拆除，SPDK hugepages 和 no-IOMMU 设置恢复。见 [主机核验](host-final.json)。原工作区已有的 `perf_reports/README.md` 修改未动；主机运行状态文件不随报告提交。

[执行器](refresh-main.py) · [原有网格](run-condition.py) · [批量导入](run-import.py) · [新增混合写](run-mixed-suite.py) · [构建验证](validate-native.py) · [协议](protocol.json) · [完成日志](main-refresh-driver.log) · [证据索引](main-evidence-index.json)。运行脚本保留实际机器、二进制和磁盘白名单路径；移机需配置相应环境。

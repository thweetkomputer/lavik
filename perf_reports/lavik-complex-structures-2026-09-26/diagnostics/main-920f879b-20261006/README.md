# 合并后 main `920f879b` 完整复测

固定提交 `920f879b05636d066ef0485f1ee1121813ef79ac`，28/28 组吞吐条件共 332 个测点，332 成功、0 失败；另完成 4/4 组批量 HSET/SADD 导入。包含已合并的 #275、#282、#285，以及 main 上的其他变更。#283 已关闭未合并，不纳入本轮。

[主报告](../../README.zh-CN.md) · [与上轮 main 的观测对比](previous-main-comparison.md) · [与另外三库的逐命令差距](main-gap-summary.md) · [构建与硬件](host-and-build.json) · [功能测试](versions.json) · [绘图核验](report-audit.json) · [命令计数核验](main-command-audit.json) · [证据索引](main-evidence-index.json)

## 测量范围与解释

List、Stream、ZSet 覆盖 64 KiB、1 MiB、100 MiB/key，各有 128 B 与 1024 B 元素；Hash/Set 覆盖 1 MiB/50,000 keys 与 100 MiB/500 keys，各有两种元素大小；另有两组扩展键数的 LSET。点操作使用 c80/320/1280/2560/5120，全量读取使用小对象 c16/80、大对象 c1/4/16。每点 8 秒，扩展 LSET 为 10 秒，pipeline=1。

同一台 AMD EPYC 9V74、16 vCPU 主机，12 个服务 worker、六块授权 NVMe、SPDK 持久化、8 GiB EAL。生产二进制关闭测试故障注入，记录 GCC/native/LTO 配置、主源码和 Bycorf/子模块身份。编译和功能验证在压测前完成，没有与压测并行。临时目录通过独立挂载命名空间使用工作盘，宿主 `/tmp` 不变。

各条件独立预置并逐 key 核验。Hash/Set 命令扫描使用 RESTORE 后重启，其预置时间不计作批量 HSET/SADD 成绩。本轮沿用原图表协议，没有采用固定 digest seed 的专门对照；因此与旧 main 的差异也可能包含路由布局和后台工作变化，不能直接解释为某个合并 PR 的收益。

其他三个系统本轮未重跑。Redis/Valkey 关闭持久化；Kvrocks 关闭 WAL，使用无压缩 RAID0 和 80 GiB cache；Lavik 不缓存字段或页内容。图表保留历史源数据，不能据此宣称同等持久性下追平。此次没有新增 perf 采样；旧 PR 的 perf 和三轮对照保留原始提交身份，不能转记为当前 main 的热点或吞吐。

合并前 #275 的小 Stream 全量读取尾延迟回退，以及 #285 的分散 Hash 写入/写后读取代价，均保留在历史报告中。合并状态不等于这些代价已消除，本轮当前 main 的实际结果全部呈现。

## 功能验证

- `unit-tests`：130 通过、0 跳过、0 失败。
- `native-tests-private-tmp`：74 通过、35 跳过、0 失败。
- `hash-native-tests-private-tmp`：16 通过、20 跳过、0 失败。

上述是本机生产构建验证；故障注入用例的跳过不算成功执行。CI 状态见 [当前固定提交的 CI](https://github.com/eloqdata/lavik/actions/runs/37486998302) 与本目录的状态快照，不以吞吐通过替代功能覆盖。

## 批量导入

每组 50,000 keys、1 MiB/key，8 个客户端、pipeline=64、每命令约 16 KiB 元素；时间包含逐命令 RESP 编码和客户端处理。单位为秒，越低越好。

| 类型 / 元素大小 | main | Redis（历史） | Valkey（历史） | Kvrocks（历史） |
|---|---:|---:|---:|---:|
| hash / 1024 B | 197.60 | 84.64 | 72.79 | 97.39 |
| hash / 128 B | 957.51 | 413.19 | 229.75 | 470.21 |
| set / 1024 B | 209.42 | 82.87 | 82.04 | 118.92 |
| set / 128 B | 897.43 | 153.09 | 154.95 | 513.28 |

## 失败、收尾与复现

本轮 332 个吞吐测点均成功完成；所有服务正常退出。

六块 scratch NVMe 已恢复原驱动与主机设置，见 [收尾核验](host-final.json)。主机运行状态文件不随报告提交。

[执行顺序](refresh-main.py) · [吞吐运行器](run-condition.py) · [导入运行器](run-import.py) · [构建与功能测试](validate-native.py) · [命令日志](commands.jsonl) · [完成日志](main-refresh-driver.log) · [绘图](render-main-refresh.py) · [核验](audit-current.py)。脚本保留本次工作区、二进制、数据盘白名单和主机锁路径；移机时需准备对应环境。

绘图使用已有的独立 Python 环境，版本见 [绘图环境](render-environment.json)。首次后处理因系统 Python 缺少 matplotlib 而停止；切换绘图环境后完成，未重跑或修改测量数据。原始异常日志保留。

旧版清单保存在 `previous-current-main.json`、`previous-current-imports.json` 及其他 `previous-*.json` 中。原始数据不改名、不覆盖；旧 PR 报告作为历史记录保留。


CI 快照：`completed` / `success`，17 项任务成功；完整任务列表见 [current-ci.json](current-ci.json)。后续状态以固定运行链接为准。

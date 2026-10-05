# #275 rebase 后的 bootstrap CI 失败与测试修复

`0b1fb8bc` 的 [CI 37327265108](https://github.com/eloqdata/lavik/actions/runs/37327265108) 已结束：14 项成功，amd64 第 2 分片及两个汇总项失败。唯一实际失败用例为 `meta_integration.gate_bootstrap`；该分片的 276 个用例中其余用例通过，其他 11 个分片通过。

失败时 `late_meta` 在 leader 选出后立即提交创建请求，收到精确回复：`ERR clustercreate 1 preflight pre-commit-failed another cluster creation or Meta membership change is in progress`。`src/meta/ctl_server.cpp` 的 `HandleClusterCreate` 在获取 membership gate 失败时返回这条回复，发生在提交提案之前。leader 就绪不能保证此时 gate 可用；这次失败不发生在 Stream 读窗口路径。

修复提交 `dbd72cb1` 只修改测试夹具及其已有的轻量测试文件：保留同一请求身份，仅重试上述精确回复，采用 10 秒 admission 预算；每次调用超时不超过剩余预算，超过预算的成功也不接受。其他拒绝、空回复和通信错误立即失败。原 gate 的整体超时不变，生产代码未改变，不将此修复宣称为此前 RDB 超时的根因或修复。

本地 8 个夹具回归用例通过，包括 6 个新增的 admission 行为测试和 2 个原有启动顺序测试；Ruff check/format 和 diff 检查通过。基准仍占用测试主机，本地没有运行真实进程集成测试；[新 head CI 37332687744](https://github.com/eloqdata/lavik/actions/runs/37332687744) 待完成。PR 仍因已记录的性能回退与历史 RDB 超时保持草稿。

[完整 CI 终态](pr275-after270-full-ci.json) · [原分片日志](pr275-after270-amd64-shard2.log) · [修复身份及本地验证记录](pr275-bootstrap-admission-fix.json)。性能测量仍使用原有冻结提交和二进制。

发布的日志仅去除行尾空白；原始下载日志保留在本机，原始及发布版 SHA-256 均记录在修复证据中，未删除日志行。

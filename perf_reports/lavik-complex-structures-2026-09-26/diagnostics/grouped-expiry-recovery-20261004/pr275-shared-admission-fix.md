# #275：共用启动 admission 等待逻辑

`dbd72cb1` 的完整 CI 结束为 13 项成功、两个测试分片失败、两个汇总项失败。amd64 第 2 分片的原 bootstrap 用例已在 2.89 秒通过。另一个失败发生在 arm64 第 1 分片的 Data-control TLS 启动：选举后创建集群再次收到精确的提交前 membership-gate busy 拒绝；日志同时记录初始成员身份仍在协调。

提交 `c7c3aa28` 将原 bootstrap 的有限重试移到 `gate_cluster_create.py`，由 bootstrap 和 Data-control 两个夹具共用，避免复制实现。保持同一请求身份、10 秒 admission 预算、剩余预算约束调用超时及拒绝超时成功；其他拒绝和通信异常立即失败。总体测试超时、生产实现、冻结性能二进制均不改变。

9 个轻量回归用例及 Ruff check/format、diff 检查通过，新增用例直接走 Data-control 的请求构造路径，验证 busy 后不会生成新 operation identity。[新提交完整 CI](https://github.com/eloqdata/lavik/actions/runs/37339320997) 待完成；本地没有在性能测试期间启动编译或真实进程重现。

同轮 [ListIndirect RESTORE 超时](pr275-list-restore-timeout.md) 是独立未解决问题，不能由这个夹具修复解释。PR 保持草稿。

[完整失败 CI](pr275-bootstrap-fix-full-ci.json) · [Data-control 失败日志](pr275-bootstrap-fix-arm64-shard1.log) · [bootstrap 通过日志](pr275-bootstrap-fix-amd64-shard2-passed.log) · [提交、验证及原始/发布日志哈希](pr275-shared-admission-fix.json)。发布日志仅去除行尾空白，没有删除行。

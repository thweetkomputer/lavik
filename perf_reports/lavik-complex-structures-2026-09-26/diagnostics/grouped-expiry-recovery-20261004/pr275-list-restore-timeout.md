# #275：arm64 ListIndirect RESTORE 超时

修复 Meta bootstrap 夹具后的 `dbd72cb1` 在 [CI 37332687744 的 arm64 第 0 分片](https://github.com/eloqdata/lavik/actions/runs/37332687744/job/111843850154) 失败。实际失败用例为 `GroupedFullDiskExpirationE2e.ReclaimsGraphAndRecovers/ListIndirect`；有序结构套件共 109 个用例，107 通过、1 跳过、1 失败。这与上一轮的 Meta bootstrap busy 拒绝不同。

新诊断确认：三个 RESTORE 中第二个请求失败（零起始 `restore_index=1`），key 为 32 KiB，List 含一个 9 MiB member，设备为 136 MiB。异常为 `response timed out`、errno=11，整次 `Command` 耗时 55,206 ms。客户端接收超时配置为 15 秒，但整次耗时包含构造/发送请求及读取回复，不能把 55.2 秒全算作等待服务端回复，也不能据此定位发送阻塞。

诊断时主线程在 poll 中休眠，两个工作线程均在 `io_cqring_wait`，io-wq 线程也在等待；内核 stack 文本为空，没有用户态回溯。这些只是异常后的单次状态快照，不足以判定存储、网络、调度或协程等待的具体原因。

上一提交 `0b1fb8bc` 的同一 arm64 第 0 分片全部 274 个 CTest 用例通过，有序结构套件耗时 618.26 秒。`0b1fb8bc` 到 `dbd72cb1` 只改了两个 Meta Python 测试文件，生产代码相同。前一轮通过不证明本次失败无害，也不能宣称它是 Stream 读窗口引入或已排除的回归。

[失败分片日志](pr275-bootstrap-fix-arm64-shard0.log) · [上一轮通过日志](pr275-after270-arm64-shard0-passed.log) · [精确身份、哈希及 artifact 清单](pr275-list-restore-timeout.json)。发布日志仅去除行尾空白，原始字节保留在本机。CI artifact 共 9 个文件，包含失败服务端日志及 CTest 记录，未包含保留磁盘镜像或 core，无法据此重放现场。

根因未确定。保留失败，不扩大超时、不盲目重跑、不修改未经证实的生产路径；#275 继续保持草稿，原有小对象性能回退与历史 RDB 超时结论不变。后续定位需要发送/接收阶段信息或可重放的失败现场；既有性能队列继续运行，未在其运行期间启动本地重现或编译。

该轮完整 CI 随后结束：13 项成功、两个分片及两个汇总项失败；另一个实际失败为 Data-control startup busy 拒绝。[共享夹具修复 `c7c3aa28`](pr275-shared-admission-fix.md) 不改变这里的 RESTORE 未解决结论。

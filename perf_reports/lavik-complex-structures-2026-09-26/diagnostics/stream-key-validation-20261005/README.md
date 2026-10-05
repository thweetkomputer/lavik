# Stream 页内 key 校验复用（实验）

当前独立 Stream 点查采样提示 `StreamRecordKey` 是一个可见 CPU 成本；源码审查发现 `ValidateEntrySpan` 在比较相邻记录顺序时重新解析上一条记录。对于包含 N 个有效记录的页，原路径调用解析器 2N−1 次。

[原型 `7869a6fb`](https://github.com/thweetkomputer/lavik/commit/7869a6fbe978018fd0519cf2ee94626e8de2afce) 基于 main `4610d607`，在同步校验期间保留上一条已检查 key 的借用视图，将上述次数降为 N。span 中的记录在整个调用内保持不变，视图不跨调用或挂起点；每个当前 key 仍完整校验，重复/逆序、score、大小检查及错误结果保留。仅改本地算法，没有持久格式或架构变更。

格式与差异检查通过，[amd64/arm64 CI](https://github.com/thweetkomputer/lavik/actions/runs/37263238928) 已启动；已有 StreamRecords 与 GroupedCollectionTest 测试将随完整 CI 执行。尚未本机编译或测量候选，未提 PR。调用次数下降不能换算成 QPS 收益；待现有诊断和对照完成后再决定是否保留。

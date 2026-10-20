# 第八课：LEAN 源码阅读、回归与升级维护

[课程目录](../../docs/curriculum.md) · [逐行中文代码](main.py) · [上一课](../07-live-deployment/README.md)

## 目标与先修

完成前七课后，沿一根行情、一条信号、一张订单追踪官方引擎，并建立升级前后可重复的回归基线。官方源码保持原文与许可证，自写课件逐行中文注释；没有把整套上游源码翻译或重写。

## 实验：系统不变量

```sh
python3 -m unittest discover -s tests -v
python3 scripts/run_lean.py maintenance
```

本课算法检查 SPY 行情结束时间严格前进、不晚于算法时钟、有效行情至少 100 根、完整成交恰好一次和现金非负。成功标记 `COURSE_OK:08` 含行情数量与成交数量。它不是通过硬编码收益小数保证“成功”，而是检查基础行为；非负现金也不等同于证明整个会计系统资产守恒。

工具测试另行覆盖权益图表 close 字段、采样回撤、空曲线失败、真实执行配置拒绝、GET 路径限制和重定向拒绝。Python 工具测试不需要券商、Docker 或 MySQL；真正算法仍需 Docker 中的 LEAN。

## 源码导航作业

在固定的 vendor/lean 版本中查找下列文件。先看接口与调用者，再看具体实现，避免一次阅读全部文件。

| 问题 | 阅读入口 | 观察方法 |
|---|---|---|
| 算法如何定义初始化和数据回调 | Algorithm/QCAlgorithm.cs、Common/Interfaces/IAlgorithm.cs | 对照课程 initialize/on_data |
| 谁推进时钟并调用策略 | Engine/AlgorithmManager.cs | 找 Slice 与算法回调路径 |
| 数据如何从文件进入策略 | Engine/DataFeeds、Common/Data | 区分 Time、EndTime、时区与填充 |
| 指标何时就绪 | Indicators/SimpleMovingAverage.cs、Indicators/IndicatorBase.cs | 对照第三课 is_ready |
| Insight 如何变成目标 | Algorithm.Framework/Portfolio、Algorithm.Framework/Risk | 对照第四课目标裁剪 |
| 订单请求和确认如何流转 | Common/Orders、Engine/TransactionHandlers | 对照第六课 Ticket 与事件 |
| 费用、滑点、成交由谁决定 | Common/Orders/Fees、Common/Orders/Slippage、Common/Orders/Fills | 对照第五课成本敏感性 |
| 实时券商在哪接入 | Common/Interfaces/IBrokerage.cs、Brokerages/Brokerage.cs | 区分接口、发行适配器与真实账户 |
| 输出图表与统计如何形成 | Engine/Results、Common/Statistics | 对照 evaluation.json 与原统计 |

用编辑器搜索类名和方法名，记录“输入 → 输出 → 调用位置”。不要因为读到一个文件就假定所有代码路径都经过它。

## 构建与运行版本的区别

configs/engine-lock.json 固定学习源码与实际镜像，两者独立记录。当前 Python 课程由官方预编译镜像执行；修改 vendor/lean 的 C# 不会改变该镜像。要研究引擎修改，先在单独分支按固定版本官方 readme.md/.vscode/readme.md 建立其 .NET 工具链，再构建测试。当前课程没有完成本机 C# 全量构建、官方全部单元测试或全部回归；不把小样例通过当成这些工作的替代。

## 升级操作步骤

1. 保存旧源码提交、镜像摘要、课程参数、数据清单和旧结果。保留可回滚版本。
2. 在独立分支升级一种对象：先只变镜像或只变源码，明确哪个实际影响运行；阅读对应发行变更。
3. 运行工具测试，再运行八课的固定实验；第二课用同一份 MySQL 快照，第三至八课使用同一份样例。
4. 比较订单状态、数量、费用、现金、权益和缺失数据，解释所有差异。不能只看最终收益相近。
5. 对有意变化更新基线与说明；意外变化未解释则保留旧版。升级也不能自动切换模拟或真实环境。

运行 `python3 scripts/run_suite.py` 可以顺序执行八课及成本/停机场景并生成本地汇总。先完成第二课导出；套件没有 MySQL 写入、券商请求或真实部署能力。结果文件的时间、运行耗时可能不同，不能对整个 JSON 做字节级相等断言。

## 备份、恢复与教学分发

GitHub 保存代码和文档，MySQL 保存本机数据，results 保存本机实验；三者用途不同。私有仓库不会自动备份 .env、原始下载或数据库。数据库使用自己保管的备份与恢复流程，在独立测试库验证恢复后再覆盖任何现有库。课堂分发只给不含凭据的代码、SQL 和获准分发的数据；不要上传本机账号、API 密钥和私人账户报告。

## 练习与参考答案

- 为什么升级后利润更高仍可能有问题？可能是数据缺失、费用模型或成交时点变了，先解释机制再看收益。
- 修改 lessons/main.py 会生效吗？下一次运行读取课程目录，会生效；修改 C# 需要重新构建对应运行产物。
- 第八课检查证明了什么？只证明该固定样例覆盖的基础路径满足不变量，没有证明所有证券、交易所或异常情景。
- 结课作业：为一个改动写“旧版本、改动、预期影响、实际差异、回滚方式”五段报告；不允许只放收益截图。

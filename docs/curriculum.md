# LEAN 全流程中文课程（八课）

这是一套可照着学习、修改、运行和检查的完整课程材料，覆盖数据 → 因子 → 组合风控 → 评估 → 模拟准备 → 真实盘部署方法 → 引擎维护。自写算法与工具按有意义的执行语句提供中文注释；每课有步骤、验收、练习、答案及限制。官方源码保留原文，通过导航学习。

“课程材料完成”与“生产交易系统验收完成”是两件事。八课历史实验已在真正 LEAN 中运行；第六课另有模拟账户只读核验。券商订单、持续实时策略、完整异常恢复和真实资金部署尚未验收，课程明确给出相应作业与证据要求。

## 从第一课开始

| 课 | 材料与代码 | 实验入口 | 完成后能做什么 |
|---|---|---|---|
| 01 | [最小策略](../lessons/01-first-backtest/README.md) · [代码](../lessons/01-first-backtest/main.py) | first | 解释时钟、信号、订单事件和最终资产 |
| 02 | [数据与 MySQL](../lessons/02-data-mysql/README.md) · [代码](../lessons/02-data-mysql/main.py) | data | 只读导出、固定快照、校验可用日期、接入自定义数据 |
| 03 | [指标与因子](../lessons/03-factors/README.md) · [代码](../lessons/03-factors/main.py) | factors | 理解指标就绪、历史输入、信号延迟与研究偏差 |
| 04 | [组合与风控](../lessons/04-portfolio-risk/README.md) · [代码](../lessons/04-portfolio-risk/main.py) | portfolio | 分开信号/目标/执行，裁剪仓位并演练回撤停机 |
| 05 | [回测评估](../lessons/05-backtest-evaluation/README.md) · [代码](../lessons/05-backtest-evaluation/main.py) | evaluation | 重算采样收益回撤，比较成本，设计时间外验证 |
| 06 | [券商模拟准备](../lessons/06-paper-orders/README.md) · [代码](../lessons/06-paper-orders/main.py) | orders | 演练订单撤销与确认，只读检查真实模拟账户 |
| 07 | [真实盘部署方法](../lessons/07-live-deployment/README.md) · [代码](../lessons/07-live-deployment/main.py) | deployment | 填写限额计划，演练正常/停机，解释对账和事故处理 |
| 08 | [引擎维护](../lessons/08-engine-maintenance/README.md) · [代码](../lessons/08-engine-maintenance/main.py) | maintenance | 阅读引擎调用路径，建立回归、升级及回滚流程 |

运行方式为 `python3 scripts/run_lean.py 实验入口`，第二课须先按该课说明导出本机 MySQL 数据。不要直接用宿主机 Python 执行 main.py，它依赖容器里的 AlgorithmImports。

## 学习节奏与交付

先完整读一遍本课说明，在纸上预测结果，然后看逐行注释、运行实验、核对日志，最后完成练习。每课保存一页学习记录：问题、数据来源、参数、运行目录、观察、尚未解释的差异。没有推荐固定学习天数，按能否解释和重现来决定是否继续。

第二至五课是研究链；第六至七课是交易执行链；第八课贯穿维护。不要用五天样例宣称策略有盈利能力，也不要通过删断言、挑参数或隐去亏损来完成练习。

## 结课项目与评分表

选择一组你能解释其经济含义的证券，提出一个简单信号。先在小样例复现机制，再对经过核对、包含公司行动和可得时间的数据展开研究。当前课程不附送全市场高质量历史面板；数据不足就将该部分标记待完成。

| 交付 | 通过标准 |
|---|---|
| 数据卡 | 标识、时区、单位、复权、缺失、公开时间与版本可解释 |
| 因子定义 | 输入、计算窗口、就绪条件、信号可用时间明确 |
| 组合规则 | 单票、总敞口、挂单占用与退出规则明确 |
| 评估报告 | 保留失败实验、成本、基准、样本划分及局限 |
| 订单账本 | 能区分请求与确认，解释部分成交与重复请求风险 |
| 运行计划 | 限额、停机、对账、重启与人工接管有具体步骤 |
| 版本报告 | 源码、镜像、数据版本及回滚方法可追溯 |

当前课程示例演示上述方法；你的多证券正式研究与持续券商运行属于后续实作，不能仅凭样例打勾。

## 常用配套入口

- [学习路线](learning-path.md)、[配置字段](zh/configuration.md)、[官方例子导读](zh/official-example.md)
- [实际验证记录](verification.md)、[模拟与实盘路线](zh/execution-roadmap.md)
- [MySQL 只读练习 SQL](../sql/course02.sql)、[结果分析工具](../scripts/analyze_results.py)
- [顺序实验套件](../scripts/run_suite.py)、[离线工具测试](../tests/test_course_tools.py)

## 最小术语表

CIK 是 SEC 公司标识，Ticker 是可能变化的证券代码；期末是财务覆盖结束日，公开时间决定当时能否使用该信息；因子是明确计算口径的特征，Insight 是框架信号，PortfolioTarget 是目标持仓，OrderTicket 是订单句柄，Fill 是成交确认，Slip/Slippage 是滑点，Drawdown 是相对过去峰值的回撤。理解词语要回到每课的时间和数据例子。

# 官方 BasicTemplateAlgorithm 逐行中文导读

对应固定版本的 [官方原文件](../../vendor/lean/Algorithm.Python/BasicTemplateAlgorithm.py)。版权与 Apache-2.0 许可证头完整保留，本文是外部中文说明，没有修改官方文件。代码行位置会随着上游升级变化，应以固定提交和实际代码为准。

## 文件头

QUANTCONNECT.COM、版权年份、Apache 许可证网址及免责声明说明代码来源和使用条件。它们不是算法逻辑，复制或修改官方代码时仍需保留相应归属和许可。`<summary>`、`<meta>` 等注释主要用于文档分类，不会自己发出订单。

## 所有可执行行

| 原代码 | 中文解释 |
|---|---|
| `from AlgorithmImports import *` | 引入 LEAN 汇总接口。QCAlgorithm、Resolution 以及示例使用的 np 等由运行环境提供。星号导入是官方示例约定，不代表普通 Python 已经安装 LEAN。 |
| `class BasicTemplateAlgorithm(QCAlgorithm):` | 定义算法类，并继承引擎基础类。启动配置通过这个类名选择算法；类本身还没有开始交易。 |
| `def initialize(self):` | 定义初始化回调，LEAN 会在历史数据流开始前调用它。self 指向当前算法对象。 |
| `self.set_start_date(2013,10,7)` | 设置回测开始日期，使用官方样例可覆盖的日期，不是电脑时钟。 |
| `self.set_end_date(2013,10,11)` | 设置结束日期。这不自动表达“结束前一定卖出全部持仓”。 |
| `self.set_cash(100000)` | 给历史虚拟账户配置 100,000 美元初始资金；不会往银行或券商转账。 |
| `self.add_equity("SPY", Resolution.MINUTE)` | 订阅 SPY 分钟级股票行情。使用引擎的证券、时区和交易时段等机制，不是手写一个 CSV 循环。 |
| `self.debug("numpy test >>> print numpy.pi: " + str(np.pi))` | 验证容器内 numpy 可用：取圆周率，转成字符串，与提示文字连接后写日志。不是交易信号。 |
| `def on_data(self, data):` | 定义每次行情 Slice 到来时的处理逻辑。官方基本例子逻辑很短，更严谨的有效数据检查可对照我们第一课。 |
| `if not self.portfolio.invested:` | 检查当前投资组合是否没有持仓。not 是逻辑取反。判断依据是持仓状态，不是“之前是否请求过订单”。 |
| `self.set_holdings("SPY", 1)` | 请求把 SPY 调整到总资产的约 100%；这里的 1 表示 100%，不是 1 股。引擎会处理数量计算和购买力等限制。 |

## 特别容易误解的地方

- initialize 声明规则，on_data 接收行情；不是先让 Python 顺序执行一遍这两个函数就结束。
- portfolio.invested 是持仓状态，而订单从提交到成交之间有状态变化。官方这个最小例子不等于完整的生产级订单管理。
- set_holdings 是仓位目标接口，结果受模型、费用、股数和现金等影响。回测成交不等于市场上一定能按相同价格成交。
- 五天样例可以检查引擎和环境，不能论证某种策略有效。
- 我们没有直接在官方源码里塞进中文改动，因此仍能清楚区分“官方基线”和“自己的学习算法”。

下一步对照 [第一课逐行注释版本](../../lessons/01-first-backtest/main.py)：它使用更小的资金、20% 目标、一次请求标志以及订单事件日志，方便观察过程。它是学习练习，不是声称逐字复制官方算法。

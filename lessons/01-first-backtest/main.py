"""第一课：用真实 LEAN 引擎观察一个最小策略的完整生命周期。

运行入口：在仓库根目录执行 python3 scripts/run_lean.py first。
数据范围：官方附带的 2013 年 10 月 7 日至 11 日 SPY 分钟样例。
本课目标：分清信号、目标仓位、订单请求、订单事件和实际持仓。
这是历史回测，不会向 Alpaca 或其他券商发送订单。
"""

# 导入 LEAN 提供的统一算法入口；QCAlgorithm、Resolution、BrokerageName 等都来自这里。
# 普通 Python 环境通常没有这个模块，需要由 LEAN 容器加载，而不是直接运行本文件。
from AlgorithmImports import *


# 定义策略类；继承 QCAlgorithm 后，才拥有 LEAN 的时间、数据、账户、下单和日志接口。
# 类名与启动配置中的 algorithm-type-name 一致，否则引擎无法选择本课算法。
class FirstBacktest(QCAlgorithm):
    """只发出一次 SPY 仓位目标，让每个事件都容易观察。"""

    # LEAN 在回测开始前调用此方法；它负责声明规则，不是一个反复运行的交易循环。
    def initialize(self):
        # 设置历史回测开始日期；选择样例覆盖的日期，避免把没有文件误认为策略没有信号。
        self.set_start_date(2013, 10, 7)
        # 设置回测结束日期；停止回测不等于自动平仓，最后的账户价值包含持仓市值。
        self.set_end_date(2013, 10, 11)
        # 设置虚拟起始资金 2,500；本课默认账户货币为美元，与券商真实账户资金无关。
        self.set_cash(2500)
        # 订阅 SPY 股票，每分钟接收一根行情柱；add_equity 返回 Security 对象。
        # 保存它的 Symbol 标识，以后用它查行情、设置仓位，避免只依赖可能变更的代码字符串。
        # 这一行没有显式指定复权方式；本课沿用 LEAN 默认设置，不把样例价格当成当前报价。
        self.symbol = self.add_equity('SPY', Resolution.MINUTE).symbol
        # 选择 QuantConnect 默认券商模型和现金账户；模型决定费用、购买力等模拟规则。
        # 这是“采用哪种模拟规则”，不是登录券商，更不是授权真实下单。
        # Python 枚举拼写为 QUANT_CONNECT_BROKERAGE，注意 CONNECT 前的下划线。
        self.set_brokerage_model(BrokerageName.QUANT_CONNECT_BROKERAGE, AccountType.CASH)
        # 自己定义的状态变量：记录是否已经尝试发出本课的一次目标请求。
        # False/True 只表示本课程序状态，不表示订单失败/成交；成交需要查看订单事件。
        self._submitted = False

    # 每当 LEAN 推进数据流并产生一个 Slice，就会调用此方法。
    # data 是该时刻的数据集合，并不保证每次都包含所有证券的有效 TradeBar。
    def on_data(self, data):
        # 已经尝试过一次，或者本次 Slice 没有 SPY 行情时，不生成新的仓位请求。
        # or 是短路运算：前一个条件成立时，不再计算后一个条件。
        if self._submitted or not data.bars.contains_key(self.symbol):
            # 只结束这一次 on_data 调用；算法仍会继续接收之后的行情。
            return
        # 先标记，再请求仓位；避免后续分钟反复执行本课的同一目标。
        # 本课故意不做订单拒绝后的自动重试；那需要后续独立的订单状态机。
        self._submitted = True
        # f 字符串把算法时间插入日志；回测中的 self.time 是历史算法时钟，不是电脑当前时间。
        # 本课日志用于教学追踪，不是某种正式的因子预测或买入推荐。
        self.debug(f'SIGNAL {self.time}: first available bar; target 20% SPY')
        # 请求将 SPY 调整到总资产的约 20%，不是“买 0.2 股”，也不是每次再买入 20%。
        # LEAN 根据价格、整股数量、费用和购买力等计算订单；最终占比可能不是恰好 20%。
        # 这一步是发出目标请求；能否成交、何时成交和成交价格由后续引擎模型决定。
        self.set_holdings(self.symbol, 0.20)

    # 订单状态变化时调用；一个订单可以依次产生 Submitted、Filled 等多条事件。
    # 在实际券商环境还可能出现部分成交、撤单和拒单，不能把一次调用等同于一次完整交易。
    def on_order_event(self, order_event):
        # 记录事件全部文本，包括订单编号、状态、数量、成交价格和费用等可用信息。
        # 对照 SIGNAL 日志，可以理解“形成交易意图”和“确认成交”之间的区别。
        self.debug(f'ORDER {self.time}: {order_event}')

    # LEAN 完成算法回测后调用；适合汇总结果，但不用于给历史信号补入未来信息。
    def on_end_of_algorithm(self):
        # 总资产通常是现金加持仓市值等，不是现金余额，也不是已经兑现的全部利润。
        # 本课未显式平仓，因此结尾仍可能持有 SPY；五天结果不能用于证明策略长期有效。
        self.debug(f'END portfolio value: {self.portfolio.total_portfolio_value}')

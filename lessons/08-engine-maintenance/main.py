"""第八课：用小型回归算法验证历史时钟、数据顺序、订单和资产守恒边界。"""
# 使用 LEAN 原生生命周期。
from AlgorithmImports import *

# 不用复杂策略干扰基础系统回归。
class MaintenanceCourse(QCAlgorithm):
    # 初始化回归状态。
    def initialize(self):
        # 固定样例起点，保证比较环境一致。
        self.set_start_date(2013, 10, 7)
        # 固定样例终点。
        self.set_end_date(2013, 10, 11)
        # 固定虚拟资金。
        self.set_cash(2500)
        # 固定现金模型。
        self.set_brokerage_model(BrokerageName.QUANT_CONNECT_BROKERAGE, AccountType.CASH)
        # 订阅同一证券和相同频率。
        self.symbol = self.add_equity('SPY', Resolution.MINUTE).symbol
        # 上一次收到行情的时刻用于顺序检查。
        self.previous_end = None
        # 用计数验证数据流不是空的。
        self.bar_count = 0
        # 防止重复发起回归订单。
        self.requested = False
        # 累积完整成交事件数量。
        self.fills = 0

    # 每次接收行情验证基本不变量。
    def on_data(self, data):
        # 没有 SPY TradeBar 时不计数。
        if not data.bars.contains_key(self.symbol):
            # 等待有效数据。
            return
        # 保存当前行情柱。
        bar = data.bars[self.symbol]
        # 本课单一 SPY 分钟订阅的结束时间应严格前进。
        if self.previous_end is not None and bar.end_time <= self.previous_end:
            # 倒序或重复会影响指标，必须暴露。
            raise ValueError('行情时间没有严格前进')
        # 当前完整行情不能位于算法时钟之后。
        if bar.end_time > self.time:
            # 这是未来数据泄漏的基本检查。
            raise ValueError('算法读取未来行情')
        # 保存当前结束时间。
        self.previous_end = bar.end_time
        # 累积真实接收的行情数。
        self.bar_count += 1
        # 第一根有效行情发一笔一股回归订单。
        if not self.requested:
            # 请求前标记。
            self.requested = True
            # 使用引擎订单系统，不直接修改虚拟现金。
            self.market_order(self.symbol, 1, tag='lesson08-regression')

    # 只对完整成交事件计数。
    def on_order_event(self, event):
        # 提交状态和撤单状态不能计为成交。
        if event.status == OrderStatus.FILLED:
            # 本课没有拆单，预期恰好一次。
            self.fills += 1

    # 用不变量代替对某个收益小数的硬编码。
    def on_end_of_algorithm(self):
        # 样例应有足够的分钟行情和一个完整成交。
        if self.bar_count < 100 or self.fills != 1:
            # 检查数据缺失、重复请求和模型升级。
            raise ValueError('基础回归数量不符合预期')
        # 一股订单不应使 2500 美元现金账户成为负余额。
        if self.portfolio.cash < 0:
            # 购买力或数量处理异常。
            raise ValueError('现金不变量失败')
        # 输出数据量和成交数，供升级前后核对。
        self.debug(f'COURSE_OK:08 bars={self.bar_count} fills={self.fills}')

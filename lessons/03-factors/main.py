"""第三课：20/60 分钟均线、就绪状态、延后一根行情执行的方向信号。"""
# 使用真实 LEAN 指标和账户 API。
from AlgorithmImports import *

# 信号与成交都交给 LEAN；这里不手写收益曲线。
class FactorCourse(QCAlgorithm):
    # 设置官方样例区间。
    def initialize(self):
        # 从周一开始观察指标逐步累积。
        self.set_start_date(2013, 10, 7)
        # 五天数据用于技术验证，不用于参数优选。
        self.set_end_date(2013, 10, 11)
        # 小资金便于观察整股约束。
        self.set_cash(2500)
        # 显式使用现金账户，避免不知情地使用杠杆。
        self.set_brokerage_model(BrokerageName.QUANT_CONNECT_BROKERAGE, AccountType.CASH)
        # 保存 SPY 标识。
        self.symbol = self.add_equity('SPY', Resolution.MINUTE).symbol
        # sma 会随订阅自动更新，不需要手动重复 update。
        self.fast = self.sma(self.symbol, 20, Resolution.MINUTE)
        # 慢指标需要至少 60 个样本才就绪。
        self.slow = self.sma(self.symbol, 60, Resolution.MINUTE)
        # pending 是上一根已形成的方向信号，None 表示没有待处理目标。
        self.pending = None
        # 记录前一个信号，避免每分钟重复调仓。
        self.previous_signal = None
        # 计数用来验证算法确实研究了指标。
        self.ready_bars = 0

    # 每根有效行情到来后处理。
    def on_data(self, data):
        # 没有 SPY 行情时不执行目标。
        if not data.bars.contains_key(self.symbol):
            # 不使用上一次数据冒充本次有效行情。
            return
        # 先处理上一根行情形成的目标，不使用本根新指标值决定这个请求。
        if self.pending is not None:
            # True 配置 20%，False 配置空仓；成交仍采用 LEAN 默认模型，不宣称下一根开盘价。
            self.set_holdings(self.symbol, 0.20 if self.pending else 0)
            # 清空待处理目标。
            self.pending = None
        # 就绪前禁止输出均线方向。
        if not self.slow.is_ready:
            # 前 59 根仍在积累窗口。
            return
        # 增加有效因子观察计数。
        self.ready_bars += 1
        # 读取当前已完成行情对应的快慢均线。
        signal = self.fast.current.value > self.slow.current.value
        # 只有方向发生变化时，才排队到下一根有效行情。
        if signal != self.previous_signal:
            # 保存未来一次回调要执行的方向。
            self.pending = signal
            # 更新方向记忆。
            self.previous_signal = signal
            # 显示因子值、算法时间和计划方向。
            self.debug(f'FACTOR {self.time} fast={self.fast.current.value} slow={self.slow.current.value} next={signal}')

    # 就绪计数为零表示实验没有真正开始。
    def on_end_of_algorithm(self):
        # 检查完整指标窗口存在。
        if self.ready_bars == 0:
            # 没有足够数据时显式失败。
            raise ValueError('指标从未就绪')
        # 启动器要求看到结束标记。
        self.debug(f'COURSE_OK:03 ready_bars={self.ready_bars}')

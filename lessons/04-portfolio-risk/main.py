"""第四课：使用官方 Framework 分离证券范围、信号、组合、风控和执行。"""
# 官方框架类型由统一入口导入。
from AlgorithmImports import *

# 自定义风控继承官方接口，只输出目标，不在此直接下单。
class TeachingRisk(RiskManagementModel):
    # 传入目标仓位上限和账户回撤阈值。
    def __init__(self, symbols):
        # 保存受本模型管理的两个证券。
        self.symbols = symbols
        # 账户历史峰值在第一次调用时初始化。
        self.peak = 0
        # 本课停机后保持退出，不自动清除。
        self.halted = False
        # 记录上限约束实际发挥作用的次数。
        self.cap_events = 0

    # LEAN 把组合模型产生的目标传给本方法。
    def manage_risk(self, algorithm, targets):
        # 总资产包含现金与持仓市值。
        equity = algorithm.portfolio.total_portfolio_value
        # 峰值只能使用已经观察到的账户价值。
        self.peak = max(self.peak, equity)
        # 0.3% 是为了短样例演示触发路径，不是投资建议或生产参数。
        if equity <= self.peak * 0.997:
            # 一旦触发就保持停止状态。
            self.halted = True
        # 风险目标要覆盖组合模型未来的新入场目标。
        if self.halted:
            # 取消尚未过期的观点，避免框架把旧信号继续当作有效观点。
            algorithm.insights.cancel(self.symbols)
            # 返回每个受管证券的零仓位目标。
            return [PortfolioTarget(symbol, 0) for symbol in self.symbols]
        # 准备经过上限修正的目标。
        adjusted = []
        # 按证券逐一检查，不混淆目标比例和股数。
        for target in targets:
            # 读取目标证券的最新可见价格。
            price = algorithm.securities[target.symbol].price
            # 没有合法价格时不产生无法解释的数量。
            if price <= 0:
                # 等待后续可用行情。
                continue
            # 将 20% 资产目标换成整股上限，剩余资金留作现金。
            cap = int(equity * 0.20 / price)
            # 本课只做多；把负数和超限股数一起约束。
            quantity = max(0, min(target.quantity, cap))
            # 统计是否实际裁剪过组合模型的目标。
            if quantity != target.quantity:
                # 计数证明风险路径被运行过。
                self.cap_events += 1
            # 输出修正目标，交给执行模型处理。
            adjusted.append(PortfolioTarget(target.symbol, quantity))
        # 不在风控模块里调用 market_order。
        return adjusted

# 用官方框架搭建同一套策略的五个层次。
class PortfolioCourse(QCAlgorithm):
    # 初始化。
    def initialize(self):
        # 选择同一段已知样例。
        self.set_start_date(2013, 10, 7)
        # 避免声称有多年历史验证。
        self.set_end_date(2013, 10, 11)
        # 设置课程账户。
        self.set_cash(2500)
        # 使用现金模型。
        self.set_brokerage_model(BrokerageName.QUANT_CONNECT_BROKERAGE, AccountType.CASH)
        # 框架创建订阅时统一采用分钟数据。
        self.universe_settings.resolution = Resolution.MINUTE
        # 使用样例中同时存在的 SPY 和 IBM。
        symbols = [Symbol.create(ticker, SecurityType.EQUITY, Market.USA) for ticker in ['SPY', 'IBM']]
        # Universe 明确证券集合，不用今天的全市场列表冒充历史股票池。
        self.set_universe_selection(ManualUniverseSelectionModel(symbols))
        # 固定向上观点只是拆解框架的教学工具，不是经检验的盈利模型。
        self.set_alpha(ConstantAlphaModel(InsightType.PRICE, InsightDirection.UP, timedelta(days=1), 0.01))
        # 等权组合模型先产生基础目标，随后由风险模型裁剪。
        self.set_portfolio_construction(EqualWeightingPortfolioConstructionModel(Resolution.DAILY))
        # 保存模型引用，以便结束时检查约束是否执行。
        self.risk = TeachingRisk(symbols)
        # 将模型注册到官方风控链路。
        self.set_risk_management(self.risk)
        # 执行模型根据修正后的目标即时生成模拟订单。
        self.set_execution(ImmediateExecutionModel())

    # 在结束点检查组合上限确实被使用。
    def on_end_of_algorithm(self):
        # 没有裁剪说明样例或代码未覆盖预期教学路径。
        if self.risk.cap_events == 0:
            # 失败要显式暴露。
            raise ValueError('仓位上限路径未覆盖')
        # 留下风控是否触发以及裁剪次数。
        self.debug(f'COURSE_OK:04 capped={self.risk.cap_events} halted={self.risk.halted}')

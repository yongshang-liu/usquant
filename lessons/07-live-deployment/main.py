"""第七课：真实盘上线前的离线执行闸门与停止开仓演练，不发送真实订单。"""
# 使用官方回测账户和订单接口。
from AlgorithmImports import *

# 实盘上线需要验证的条件，先在离线算法中写成可观察的门禁。
class DeploymentCourse(QCAlgorithm):
    # 初始化部署演练。
    def initialize(self):
        # 固定历史样例起点。
        self.set_start_date(2013, 10, 7)
        # 固定结束日期。
        self.set_end_date(2013, 10, 11)
        # 演练资金，不是实盘账户余额。
        self.set_cash(2500)
        # 现金账户模型。
        self.set_brokerage_model(BrokerageName.QUANT_CONNECT_BROKERAGE, AccountType.CASH)
        # 只允许 SPY 作为课程标的。
        self.symbol = self.add_equity('SPY', Resolution.MINUTE).symbol
        # scenario=kill 用来故障注入，验证停止开仓，而不是伪造市场回撤。
        self.scenario = self.get_parameter('scenario') or 'normal'
        # 参数白名单避免拼写错误被悄悄忽略。
        if self.scenario not in ('normal', 'kill'):
            # 不认识的演练模式立即失败。
            raise ValueError('scenario 只接受 normal 或 kill')
        # 记录是否已执行一次课程入场。
        self.requested = False
        # 记录安全闸门拦截次数。
        self.blocked = 0

    # 每次有效行情都先检查门禁，再考虑生成订单。
    def on_data(self, data):
        # 没有行情，或者已经执行过本课动作时不继续。
        if self.requested or not data.bars.contains_key(self.symbol):
            # 不使用过期数据发新请求。
            return
        # 读取这根行情的结束时刻。
        end = data.bars[self.symbol].end_time
        # 以算法时钟检查数据新鲜度，不把历史时间与电脑当前时间相减。
        if self.time - end > timedelta(minutes=2) or end > self.time:
            # 新鲜度不合格，记录拦截。
            self.blocked += 1
            # 本根不发单。
            return
        # 故障注入模式禁止任何入场；这个 kill 只演示“禁止开仓”，不是自动平仓系统。
        if self.scenario == 'kill':
            # 计数供结束断言检查。
            self.blocked += 1
            # 没有实际券商请求。
            return
        # 读取本次可见成交参考价格。
        price = self.securities[self.symbol].price
        # 只允许一股且金额不超过 500 美元及账户的 20%。
        if price <= 0 or price > min(500, self.portfolio.total_portfolio_value * 0.20):
            # 价格或额度不合法，保持等待。
            self.blocked += 1
            # 拦截订单。
            return
        # 请求前写入一次性标志；生产系统还需要持久化幂等和账户对账。
        self.requested = True
        # 仅发送给 LEAN 回测事务处理器的模拟订单。
        self.market_order(self.symbol, 1, tag='lesson07-offline-rehearsal')

    # 根据所选演练模式检查预期行为。
    def on_end_of_algorithm(self):
        # 故障注入必须确实拦截，且不得出现课程入场。
        if self.scenario == 'kill' and (self.requested or self.blocked == 0):
            # 没有拦住意味着测试失败。
            raise ValueError('kill 门禁没有生效')
        # 普通模式必须覆盖可用行情和额度允许路径。
        if self.scenario == 'normal' and not self.requested:
            # 不是仅启动进程就算完成。
            raise ValueError('普通执行路径未覆盖')
        # 输出验收结论，明确是离线演练。
        self.debug(f'COURSE_OK:07 scenario={self.scenario} blocked={self.blocked} offline_only=True')

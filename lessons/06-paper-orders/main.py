"""第六课：离线演练未成交限价单、撤单、再次入场和订单回报。"""
# 使用 LEAN 的真实订单状态与 Ticket。
from AlgorithmImports import *

# 这里只演练状态机；实际券商纸盘需另外验证。
class OrderCourse(QCAlgorithm):
    # 初始化数据和状态。
    def initialize(self):
        # 样例第一天。
        self.set_start_date(2013, 10, 7)
        # 样例最后一天。
        self.set_end_date(2013, 10, 11)
        # 模拟资金。
        self.set_cash(2500)
        # 禁止使用杠杆的现金模型。
        self.set_brokerage_model(BrokerageName.QUANT_CONNECT_BROKERAGE, AccountType.CASH)
        # 订阅分钟行情。
        self.symbol = self.add_equity('SPY', Resolution.MINUTE).symbol
        # Ticket 是订单操作句柄，不是持仓。
        self.ticket = None
        # 从挂单开始计数，在第三根有效行情请求撤单。
        self.bars_seen = 0
        # 一次撤单请求也要防重复。
        self.cancel_requested = False
        # 第二笔市场单只能请求一次。
        self.market_requested = False
        # 记录是否收到明确撤单确认。
        self.cancel_confirmed = False
        # 记录是否收到成交确认。
        self.fill_confirmed = False

    # 随有效行情推进状态机。
    def on_data(self, data):
        # 缺失数据不触发订单操作。
        if not data.bars.contains_key(self.symbol):
            # 等待下一次有效行情。
            return
        # 一根有效行情使计数加一。
        self.bars_seen += 1
        # 第一次创建远离当前价格的买入限价单。
        if self.ticket is None:
            # 本样例 90% 价格只为稳定制造“挂单等待”的教学路径。
            limit = round(float(data.bars[self.symbol].close) * 0.90, 2)
            # LEAN 返回 Ticket，可通过它查询状态或请求撤销。
            self.ticket = self.limit_order(self.symbol, 1, limit, tag='lesson06-limit-once')
            # 本根行情结束，不马上撤单。
            return
        # 两根行情后发送一次撤单，不把撤单请求当成成功确认。
        if self.bars_seen >= 3 and not self.cancel_requested:
            # 先置标志，避免重入时重复请求。
            self.cancel_requested = True
            # cancel 返回请求结果；最终状态仍由 on_order_event 确认。
            self.ticket.cancel('lesson06-cancel-once')
        # 只有确认旧单取消后，才能提交本课第二笔市场单。
        if self.cancel_confirmed and not self.market_requested:
            # 同样先标记后请求，防止每分钟重发。
            self.market_requested = True
            # 一股只为观察订单生命周期，不是生产仓位设计。
            self.market_order(self.symbol, 1, tag='lesson06-market-once')

    # 订单事件是状态确认来源。
    def on_order_event(self, event):
        # 全量输出事件便于核对同一订单的不同状态。
        self.debug(f'ORDER_STATE {event}')
        # 只有明确 CANCELED 事件才认为撤单完成。
        if event.status == OrderStatus.CANCELED:
            # 更新确认状态，之后才允许新市场单。
            self.cancel_confirmed = True
        # 只有 Filled 才是本课完整成交确认。
        if event.status == OrderStatus.FILLED:
            # 部分成交不在这里误记成全部成交。
            self.fill_confirmed = True

    # 两条状态路径都覆盖才通过。
    def on_end_of_algorithm(self):
        # 同时检查撤单和成交确认。
        if not self.cancel_confirmed or not self.fill_confirmed:
            # 未覆盖路径说明需要检查事件日志。
            raise ValueError('撤单或成交确认路径未覆盖')
        # 标记本次离线演练完成，不代表券商联网验证。
        self.debug('COURSE_OK:06 canceled_and_filled=True')

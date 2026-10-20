"""第五课：固定策略、显式滑点，随后用独立脚本读真实 LEAN 结果。"""
# 导入引擎和滑点模型。
from AlgorithmImports import *

# 策略不扫描参数，只提供对照实验用的单一滑点输入。
class EvaluationCourse(QCAlgorithm):
    # 设定实验条件。
    def initialize(self):
        # 五天样例只验证评估流程。
        self.set_start_date(2013, 10, 7)
        # 终止在样例末日。
        self.set_end_date(2013, 10, 11)
        # 固定资金，便于比较成本情景。
        self.set_cash(2500)
        # 明确现金账户。
        self.set_brokerage_model(BrokerageName.QUANT_CONNECT_BROKERAGE, AccountType.CASH)
        # 保存 Security 对象，以配置其成交滑点。
        security = self.add_equity('SPY', Resolution.MINUTE)
        # 提取 Symbol，后续目标请求使用它。
        self.symbol = security.symbol
        # 参数单位为基点；缺省 5 bps 等于价格的 0.05%。
        bps = float(self.get_parameter('cost-bps') or '5')
        # 拒绝不合理负数或极端输入。
        if not 0 <= bps <= 100:
            # 参数超界不自动修正。
            raise ValueError('cost-bps 必须在 0 到 100 之间')
        # 此模型只控制滑点；券商模型的手续费仍单独生效。
        security.set_slippage_model(ConstantSlippageModel(bps / 10000))
        # 显式设置同标的基准，用于对照方向与暴露差异。
        self.set_benchmark(self.symbol)
        # 防止重复请求本课的初始目标。
        self.requested = False

    # 第一次有效行情才请求目标。
    def on_data(self, data):
        # 数据缺失或已经请求时不做新操作。
        if self.requested or not data.bars.contains_key(self.symbol):
            # 保持等待或维持持仓。
            return
        # 请求前标记。
        self.requested = True
        # 固定 20% 目标，不随测试结果改仓位。
        self.set_holdings(self.symbol, 0.20)

    # 检查策略至少进入有效数据处理路径。
    def on_end_of_algorithm(self):
        # 缺少行情时不能称为完成。
        if not self.requested:
            # 给出明确错误。
            raise ValueError('没有有效行情')
        # 独立分析脚本会读取本次真实结果，而不是重新模拟。
        self.debug('COURSE_OK:05')

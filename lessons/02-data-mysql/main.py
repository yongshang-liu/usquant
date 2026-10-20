"""第二课：把 MySQL 只读快照作为 LEAN 自定义观察数据，不冒充可交易证券。"""
# 引入 LEAN 类型及其 datetime、timedelta。
from AlgorithmImports import *

# 定义原始日线观察类型；它不是已经具备公司行动信息的原生股票。
class RawClose(PythonData):
    # 指定固定文件来源，避免回测中直接连接会变化的数据库。
    def get_source(self, config, date, is_live_mode):
        # 本课只读本机挂载文件，不使用远程 HTTP。
        return SubscriptionDataSource('/CourseData/lesson02/nvda.csv', SubscriptionTransportMedium.LOCAL_FILE)

    # LEAN 将 CSV 的每一行交给 reader 解释。
    def reader(self, config, line, date, is_live_mode):
        # 跳过表头和空行；错误的数据行不静默吞掉。
        if not line.strip() or line.startswith('session,'):
            # 表头不是数据观测。
            return None
        # 本课字段都是简单数值/日期，没有带逗号的字符串。
        fields = line.split(',')
        # 构造新的数据对象，不能在多行之间复用同一实例。
        point = RawClose()
        # 绑定 LEAN 创建的自定义 Symbol。
        point.symbol = config.symbol
        # 可用时间来自导出契约，是完整日线结束之后的次日零点。
        point.time = datetime.strptime(fields[6], '%Y-%m-%d')
        # 这是一个在该时间点可见的观测，不设为之前一整天已经可知。
        point.end_time = point.time
        # value 是用于观察的原始收盘价。
        point.value = float(fields[4])
        # 原交易日保留为额外字段，不与可用日期混用。
        point['session'] = fields[0]
        # 返回这条解析完成的观测。
        return point

# 此课验证数据边界，不下单。
class DataCourse(QCAlgorithm):
    # 初始化固定验证范围。
    def initialize(self):
        # 起点覆盖第一条可用日。
        self.set_start_date(2024, 1, 1)
        # 最后一条一月日线在二月一日可见。
        self.set_end_date(2024, 2, 2)
        # 虚拟账户只用来满足引擎初始化。
        self.set_cash(2500)
        # 常数基准避免额外请求该时期不存在的官方 SPY 样例。
        self.set_benchmark(lambda time: 1)
        # 明确按纽约时间解释快照；不向前填补缺失数据。
        self.observed = self.add_data(RawClose, 'NVDA_SOURCE', Resolution.DAILY, TimeZones.NEW_YORK, False).symbol
        # 用计数检查到底接收了多少行。
        self.count = 0

    # 每条自定义数据到达后记录观察。
    def on_data(self, data):
        # 并非每次 Slice 都一定有本课数据。
        if not data.contains_key(self.observed):
            # 没有时保持等待。
            return
        # 提取当前已可用观测。
        point = data[self.observed]
        # 验证没有在交易日收盘之前使用完整日线。
        if self.time.date() <= datetime.strptime(point['session'], '%Y-%m-%d').date():
            # 数据时钟错误时直接失败。
            raise ValueError('完整日线被提前暴露')
        # 记录接收行数。
        self.count += 1
        # 显示原交易日和实际观察时间的区别。
        self.debug(f'DATA session={point["session"]} available={self.time} raw_close={point.value}')

    # 数据课必须实际收到记录才算完成。
    def on_end_of_algorithm(self):
        # 不把空回测当成成功。
        if self.count == 0:
            # 检查导出文件和挂载位置。
            raise ValueError('未接收 MySQL 快照')
        # 验收标记由启动器读取。
        self.debug(f'COURSE_OK:02 observations={self.count}')

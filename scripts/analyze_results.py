"""第五课：读取真实 LEAN 输出，重算区间收益和采样最大回撤，不重新回测。"""
# 解析路径参数。
import argparse
# 用 UTC 时间将采样点归到日期。
from datetime import datetime, timezone
# 标准 JSON 读取器。
import json
# 结果文件路径工具。
from pathlib import Path

# 从 LEAN 的 OHLC 或点值图表中提取时刻与收盘/数值。
def points(values):
    # 同时支持数组图表点与对象图表点，未知格式直接失败。
    result = []
    # 每一项是一个采样点，不一定是独立交易日。
    for item in values:
        # 数组形式：普通点为 [time,value]，OHLC 为 [time,open,high,low,close]。
        if isinstance(item, list):
            # 取最后一项，避免把 open 当成期末权益。
            stamp, value = item[0], item[-1]
        else:
            # 对象形式通常使用 x/y 或 close 字段。
            stamp, value = item['x'], item.get('close', item.get('y'))
        # 数值统一为 float，仅用于报告统计，不改动原始会计记录。
        result.append((int(stamp), float(value)))
    # 稳定按时间排列，不依赖 JSON 原始键序。
    return sorted(result)

# 汇总连续资金曲线的采样收益和回撤。
def summarize(equity):
    # 空曲线不产生零收益结论。
    if not equity or equity[0][1] <= 0:
        # 明确提示输出缺失。
        raise ValueError('缺少有效权益曲线')
    # 峰值从第一个观察值开始。
    peak = equity[0][1]
    # 最大回撤从零开始。
    drawdown = 0.0
    # 顺序处理，不能用未来峰值回算过去。
    for stamp, value in equity:
        # 更新当前已观察峰值。
        peak = max(peak, value)
        # 计算相对该峰值的损失比例。
        drawdown = max(drawdown, 1 - value / peak)
    # 不做五天收益的无意义长期年化。
    return dict(sample_return=equity[-1][1] / equity[0][1] - 1,
                sampled_max_drawdown=drawdown, observations=len(equity))

# 从一份完整结果生成分析文件。
def analyze(path):
    # 读取实际 LEAN 结果，而非手写样例收益。
    result = json.loads(path.read_text())
    # 明确选择账户权益系列。
    equity = points(result['charts']['Strategy Equity']['series']['Equity']['values'])
    # 只对已经存在的真实采样点计算。
    report = summarize(equity)
    # 保留引擎原统计，供比较采样口径差异。
    report['engine_statistics'] = result['statistics']
    # 记录真实订单数量，不把样本点数量当交易次数。
    report['order_count'] = len(result.get('orders', {}))
    # 按 UTC 日期保留当天最后一个权益采样。
    daily = {}
    # 同一天可能有多个样本。
    for stamp, value in equity:
        # 时区明确标为 UTC；此处只是报告分组，不定义交易所收盘时刻。
        daily[datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()] = value
    # 本样例用时间先后分组演示，不声称是真正未触碰的样本外数据。
    report['calendar_days'] = daily
    # 明确研究边界，防止误解数字精度。
    report['limitations'] = '短样例只验证评估流程；采样回撤可能遗漏盘中极值，没有未触碰的样本外检验。'
    # 返回可序列化结果。
    return report

# 命令行入口。
def main():
    # 接收主结果 JSON 路径，不接受 summary 文件冒充完整图表。
    parser = argparse.ArgumentParser(description=__doc__)
    # 用户必须指定一次实际回测结果。
    parser.add_argument('result', type=Path)
    # 解析命令。
    args = parser.parse_args()
    # 执行分析。
    report = analyze(args.result)
    # 写在同一运行目录，保留来源关联。
    output = args.result.parent / 'evaluation.json'
    # 中文报告保持可读编码。
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    # 不打印长账户对象，只提示报告位置。
    print(output)

# 被单元测试导入时不自动读文件。
if __name__ == '__main__':
    # 启动独立评估。
    main()

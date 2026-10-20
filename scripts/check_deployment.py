"""第七课：检查上线计划是否完整；只生成报告，不生成可执行的实盘配置。"""
# 接收示例计划文件。
import argparse
# 解析配置。
import json
# 路径处理。
from pathlib import Path

# 检查数字边界和准备条件；这不是券商授权接口。
def inspect(plan):
    # 只接受教学演练阶段，避免用户误以为该脚本能部署实盘。
    if plan['stage'] != 'offline-rehearsal' or plan['live_enabled'] is not False:
        # 拒绝已开启真实执行的计划。
        raise ValueError('本工具只接受实盘关闭的离线演练计划')
    # 本课固定使用模拟环境进行学习。
    if plan['paper_trading'] is not True:
        # 不接受真实账户模式。
        raise ValueError('当前课程配置必须指向模拟环境')
    # 总资金必须为正，单笔金额不能超过总资金。
    if not 0 < plan['max_order_usd'] <= plan['total_capital_usd']:
        # 边界不符合要求时停止。
        raise ValueError('资金限额无效')
    # 单票与总敞口具有明确的包含关系。
    if not 0 < plan['max_position_fraction'] <= plan['max_gross_fraction'] <= 1:
        # 无法解释的仓位约束不能放行。
        raise ValueError('仓位限额无效')
    # 学习阶段不开放杠杆或做空。
    if plan['allow_short'] or plan['allow_leverage']:
        # 生产中这些能力需要独立风险设计。
        raise ValueError('本课不支持杠杆或做空')
    # 风险阈值必须是有效正比例。
    if not all(0 < plan[key] < 1 for key in ('daily_loss_fraction', 'drawdown_fraction')):
        # 不接受负数、零或超过全部资产的阈值。
        raise ValueError('损失阈值无效')
    # 列出尚未完成的操作准备，不能自动把它们改成 True。
    missing = [key for key in ('account_reconciled', 'restart_test_passed', 'operator_approved') if plan[key] is not True]
    # 即使所有清单完成，本脚本也没有下单或部署能力。
    return dict(configuration_valid=True, missing_checks=missing, kill_switch=plan['kill_switch'],
                executable=False, real_orders_enabled=False, note='清单检查不是实盘验收或授权')

# 命令行入口。
def main():
    # 提供可选文件路径。
    parser = argparse.ArgumentParser(description=__doc__)
    # 默认使用不含任何密钥的示例。
    parser.add_argument('plan', nargs='?', type=Path, default=Path(__file__).resolve().parents[1] / 'configs/deployment-plan.example.json')
    # 解析参数。
    args = parser.parse_args()
    # 将检查结论显示给学习者。
    print(json.dumps(inspect(json.loads(args.plan.read_text())), ensure_ascii=False, indent=2))

# 导入时不进行任何操作。
if __name__ == '__main__':
    # 执行纯本地检查。
    main()

"""顺序运行八课及成本/停机场景，只调用断网 LEAN 启动器。"""
# JSON 用来保存本地汇总，不包含券商账户。
import json
# 只通过参数数组调用现有课程启动器。
import subprocess
# 使用当前 Python，不依赖固定安装目录。
import sys
# 定位代码和结果。
from pathlib import Path

# 仓库根目录。
ROOT = Path(__file__).resolve().parents[1]

# 每次明确检查数据前置条件，然后运行全部课程。
def main():
    # 第二课必须先由用户运行只读导出，套件不会隐式访问数据库。
    if not (ROOT / 'local-data/lesson02/nvda.csv').is_file():
        # 缺少数据时在任何回测开始前失败。
        raise SystemExit('请先按第二课说明运行 scripts/export_mysql.py')
    # 按教学顺序列出课程，额外覆盖两个参数分支。
    cases = [('first', []), ('data', []), ('factors', []), ('portfolio', []),
             ('evaluation', ['--parameter', 'cost-bps=5']), ('orders', []),
             ('deployment', ['--parameter', 'scenario=normal']), ('maintenance', []),
             ('evaluation', ['--parameter', 'cost-bps=20']),
             ('deployment', ['--parameter', 'scenario=kill'])]
    # 收集每次已通过验收的结果位置。
    completed = []
    # 顺序执行，避免多个容器争抢课程资源。
    for lesson, arguments in cases:
        # 每次运行前记录现有目录，避免拿旧报告冒充新结果。
        before = set((ROOT / 'results').glob('*'))
        # 启动器负责真实引擎调用及各课验收；失败立即停止整个套件。
        subprocess.run([sys.executable, str(ROOT / 'scripts/run_lean.py'), lesson] + arguments,
                       cwd=ROOT, check=True)
        # 获取本次新建且名称匹配的结果目录。
        created = set((ROOT / 'results').glob('*-' + lesson)) - before
        # 每次运行应恰好产生一份结果目录。
        if len(created) != 1:
            # 不猜测某个旧结果是否可用。
            raise RuntimeError('无法唯一定位本次结果')
        # 保存参数与相对目录，便于逐项复查。
        completed.append(dict(lesson=lesson, parameters=arguments, result=str(created.pop().relative_to(ROOT))))
    # 汇总不替代每次原始日志，且放在忽略目录内。
    destination = ROOT / 'results/course-suite.json'
    # 明确这些是历史实验，不是券商成交验收。
    destination.write_text(json.dumps(dict(mode='offline-backtesting', cases=completed,
                                         broker_orders_submitted=0), indent=2, ensure_ascii=False))
    # 告知学习者汇总位置。
    print(destination)

# 导入时不启动任何回测。
if __name__ == '__main__':
    # 开始顺序验收。
    main()

"""课程工具的边界测试：覆盖时间曲线、部署拒绝、路径限制和配置隔离。"""
# 标准 unittest 不依赖外部测试框架。
import unittest
# 解析结果与测试计划。
import json
# 动态加载脚本而不执行命令行入口。
import runpy
# 支持脚本之间的同目录导入。
import sys
# 定位仓库路径。
from pathlib import Path

# 从测试文件定位根目录。
ROOT = Path(__file__).resolve().parents[1]
# 允许 paper_preflight 找到 export_mysql 的配置读取函数。
sys.path.insert(0, str(ROOT / 'scripts'))
# 导入评估函数，不读取真实报告。
analysis = runpy.run_path(str(ROOT / 'scripts/analyze_results.py'))
# 导入纯本地部署检查，不访问网络。
deployment = runpy.run_path(str(ROOT / 'scripts/check_deployment.py'))
# 导入只读预检客户端，不执行 main。
paper = runpy.run_path(str(ROOT / 'scripts/paper_preflight.py'))

# 使用失败用例检验重要边界。
class CourseToolTests(unittest.TestCase):
    # 验证 OHLC 中读取 close，不误取 open。
    def test_chart_close_and_drawdown(self):
        # 100、80、120 代表先跌再涨，最大采样回撤应为 20%。
        curve = analysis['points']([[1, 9, 10, 8, 100], [2, 9, 10, 8, 80], [3, 9, 10, 8, 120]])
        # 统计只使用观测到的峰值。
        report = analysis['summarize'](curve)
        # 收益与回撤是不同概念。
        self.assertAlmostEqual(report['sample_return'], 0.2)
        # 后来上涨不能抹去早前回撤。
        self.assertAlmostEqual(report['sampled_max_drawdown'], 0.2)

    # 验证不能从空报告得到“零收益成功”。
    def test_empty_curve_rejected(self):
        # 期待清晰失败。
        with self.assertRaises(ValueError):
            # 空数据不是一个有效实验。
            analysis['summarize']([])

    # 验证实盘计划不会因为清单字段被勾选就生成执行能力。
    def test_live_plan_never_executable(self):
        # 从无密钥示例加载。
        plan = json.loads((ROOT / 'configs/deployment-plan.example.json').read_text())
        # 检查必须明确不可执行。
        self.assertFalse(deployment['inspect'](plan)['executable'])
        # 模拟误把真实开关打开。
        plan['live_enabled'] = True
        # 课程工具必须拒绝，而不是替用户上线。
        with self.assertRaises(ValueError):
            # 验证拒绝路径。
            deployment['inspect'](plan)

    # 验证不能复用只读工具访问提交订单路径。
    def test_paper_path_and_redirect_rejected(self):
        # GET 路径白名单会在读取密钥前拦截。
        with self.assertRaises(ValueError):
            # 任意订单提交路径不属于本课只读接口。
            paper['get']('/v2/orders')
        # 禁止认证请求跟随服务器跳转。
        with self.assertRaises(PermissionError):
            # 不进行实际网络操作，只调用跳转拒绝函数。
            paper['NoRedirect']().redirect_request(None, None, 302, '', {}, 'https://example.com')

# 直接运行时执行这些测试；CI 也可通过 discover 查找。
if __name__ == '__main__':
    # 标准测试入口。
    unittest.main()

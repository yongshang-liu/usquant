"""第六课：只读核验 Alpaca 模拟账户，不包含 POST、撤单或真实账户入口。"""
# 生成简短的本机核验报告。
import json
# 读取本机环境变量。
import os
# 检查时间的时区信息。
from datetime import datetime, timezone
# 路径工具只用于定位本机 .env 和结果目录。
from pathlib import Path
# 标准 HTTP GET 客户端。
import urllib.request
# 复用本课程自己的安全配置读取函数，不启用旧引擎。
from export_mysql import load_env

# 固定模拟域名，不接受来自命令行的替换域名。
PAPER = 'https://paper-api.alpaca.markets'

# 拒绝重定向，避免把身份头转发到非预期目标。
class NoRedirect(urllib.request.HTTPRedirectHandler):
    # 服务器返回跳转时调用这个方法。
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # 明确失败，不跟随新地址。
        raise PermissionError('模拟账户请求不允许跳转')

# 只允许预先列出的只读接口。
def get(path):
    # URL 路径白名单阻止脚本被当成任意券商操作工具。
    if path not in ('/v2/account', '/v2/clock', '/v2/positions', '/v2/orders?status=open&limit=500'):
        # 未授权路径不发网络请求。
        raise ValueError('仅允许账户预检 GET')
    # 在内存中构造认证头，不打印、不写报告。
    headers = {'APCA-API-KEY-ID': os.environ['ALPACA_API_KEY'],
               'APCA-API-SECRET-KEY': os.environ['ALPACA_SECRET_KEY']}
    # method 明确固定 GET；脚本没有提交请求体。
    request = urllib.request.Request(PAPER + path, headers=headers, method='GET')
    # 使用禁止跳转的客户端。
    opener = urllib.request.build_opener(NoRedirect())
    # 设置超时，失败后不自动发送新订单。
    with opener.open(request, timeout=20) as response:
        # 解析返回内容，完整内容只在进程内存中存在。
        return json.load(response)

# 核验账户状态，输出最少必要信息。
def main():
    # 密钥从本机私有配置加载。
    load_env()
    # 查询模拟账户，不使用真实域名。
    account = get('/v2/account')
    # 查询交易时钟，休市不等于连接失败。
    clock = get('/v2/clock')
    # 查询真实模拟账户现有持仓，不能假定为空。
    positions = get('/v2/positions')
    # 查询未完成订单；上限 500，不能将恰好 500 条解释为完整清单。
    orders = get('/v2/orders?status=open&limit=500')
    # 保存脱敏结论，不存账号、资产金额或认证头。
    report = dict(checked_at=datetime.now(timezone.utc).isoformat(), mode='paper',
                  account_active=account.get('status') == 'ACTIVE',
                  blocked=any(account.get(k, False) for k in ('trading_blocked', 'account_blocked', 'trade_suspended_by_user')),
                  market_open=clock['is_open'], next_open=clock['next_open'],
                  position_count=len(positions), open_order_count=len(orders),
                  order_list_may_be_truncated=len(orders) == 500, orders_submitted=0)
    # 报告位于本机忽略目录。
    directory = Path(__file__).resolve().parents[1] / 'results/paper-preflight'
    # 创建目录。
    directory.mkdir(parents=True, exist_ok=True)
    # 保存脱敏结果，便于学习连接检查。
    (directory / 'report.json').write_text(json.dumps(report, indent=2))
    # 输出也仅包含脱敏结论。
    print(json.dumps(report))

# 直接运行才会访问券商模拟 GET。
if __name__ == '__main__':
    # 无凭据或网络失败时明确报错，不伪装已验证。
    main()

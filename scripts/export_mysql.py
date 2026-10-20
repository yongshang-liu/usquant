"""第二课：只读导出 MySQL 行情，生成可核对的固定课程快照。"""
# 导入参数解析，允许选择输出目录。
import argparse
# CSV 用标准库处理，避免手工拼接字段破坏格式。
import csv
# 摘要用于检查后续是否修改了快照。
import hashlib
# 清单保留来源和行数。
import json
# 环境变量只在本机进程内保存连接凭据。
import os
# 日期用于保守设置完整日线的可用时间。
from datetime import date, datetime, timedelta, timezone
# 使用绝对路径定位项目。
from pathlib import Path

# 从脚本位置定位根目录，不依赖当前终端位置。
ROOT = Path(__file__).resolve().parents[1]

# 只读取简单键值，不把配置当 shell 脚本执行。
def load_env():
    # .env 不存在时，由数据库连接阶段提示缺少配置。
    if not (ROOT / '.env').exists():
        # 不凭空生成任何密钥。
        return
    # 逐行处理本机私有配置。
    for line in (ROOT / '.env').read_text().splitlines():
        # 跳过注释，只处理有等号的行。
        if '=' in line and not line.lstrip().startswith('#'):
            # 第一个等号之前是变量名，之后是值。
            key, value = line.split('=', 1)
            # 已有环境变量优先；不打印任何值。
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

# 从真实 MySQL 读取一个月 NVDA 原始日线，只用于数据接入练习。
def main():
    # 定义命令行界面。
    parser = argparse.ArgumentParser(description=__doc__)
    # 默认输出在被 Git 忽略的本机目录中。
    parser.add_argument('--output', type=Path, default=ROOT / 'local-data/lesson02')
    # 解析输入。
    args = parser.parse_args()
    # 加载本机配置。
    load_env()
    # PyMySQL 是数据库客户端；课程依赖清单给出安装方法。
    import pymysql
    # 使用已有数据库普通用户，不需要 root 或修改权限。
    db = pymysql.connect(host=os.getenv('MYSQL_HOST', '127.0.0.1'),
                         port=int(os.getenv('MYSQL_PORT', '3306')),
                         user=os.environ['MYSQL_USER'], password=os.environ['MYSQL_PASSWORD'],
                         database=os.getenv('MYSQL_DATABASE', 'usquant'), charset='utf8mb4')
    # 无论成功失败，都必须关闭连接。
    try:
        # 新事务只读，防止本练习写入生产表。
        with db.cursor() as cursor:
            # 明确只读事务属性。
            cursor.execute('SET TRANSACTION READ ONLY')
            # 开始一致性读取。
            cursor.execute('START TRANSACTION WITH CONSISTENT SNAPSHOT')
            # 分清来源和复权；范围是半开区间，按时间稳定排序。
            cursor.execute("SELECT ts,open,high,low,close,volume FROM bars WHERE symbol=%s AND source=%s AND adjustment=%s AND ts >= %s AND ts < %s ORDER BY ts",
                           ('NVDA', 'alpaca-iex', 'raw', '2024-01-01', '2024-02-01'))
            # 一次读取这个小范围，课程不导出整个数据库。
            rows = cursor.fetchall()
        # 没有记录时停止，不制造假行情。
        if not rows:
            # 提示数据准备问题。
            raise ValueError('MySQL 中缺少 NVDA 2024-01 原始日线')
        # 创建课程快照目录。
        args.output.mkdir(parents=True, exist_ok=True)
        # 临时文件写完后才提交到固定文件名，减少中断损坏。
        temp = args.output / 'nvda.csv.part'
        # 使用 newline 防止 Windows 出现多余空行。
        with temp.open('w', newline='') as stream:
            # 使用标准 CSV 写入器。
            writer = csv.writer(stream)
            # 公开字段契约：最后一列表示本课保守设定的可用日期。
            writer.writerow(['session', 'open', 'high', 'low', 'close', 'volume', 'available_date'])
            # 检查并导出每条记录。
            for ts, op, high, low, close, volume in rows:
                # 原始时间戳带时区；取其交易日期，当前选定数据是美股日线。
                session = datetime.fromisoformat(ts).date()
                # 用次日纽约零点作为保守可用点，而不是当日开盘就看到全天收盘。
                available = session + timedelta(days=1)
                # 保留原始价格，不在这一课混入拆股复权处理。
                writer.writerow([session.isoformat(), op, high, low, close, volume, available.isoformat()])
        # 读取已完成临时文件计算内容摘要。
        digest = hashlib.sha256(temp.read_bytes()).hexdigest()
        # 清单记录采集边界，不包含密码或账号。
        manifest = dict(symbol='NVDA', source='alpaca-iex', adjustment='raw', rows=len(rows),
                        first_session=rows[0][0][:10], last_session=rows[-1][0][:10], sha256=digest,
                        exported_at=datetime.now(timezone.utc).isoformat(), purpose='custom-data-read-only')
        # 如果已有同名快照但内容改变，拒绝覆盖，让研究者主动决定版本迁移。
        destination = args.output / 'nvda.csv'
        # 相同快照允许重复运行，不同版本需要新的输出目录。
        if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            # 保留旧快照，清理本次未提交临时文件。
            temp.unlink()
            # 版本变化必须显式处理。
            raise ValueError('快照变化：请使用新的输出目录保留版本')
        # 原子替换同内容或新文件。
        temp.replace(destination)
        # 清单与数据一起保存，用于核对。
        (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2))
        # 只输出非敏感的行数和路径。
        print(json.dumps(dict(rows=len(rows), path=str(destination))))
    finally:
        # 只读事务结束不需要提交写入。
        db.rollback()
        # 释放连接。
        db.close()

# 直接运行时才进入数据库读取流程。
if __name__ == '__main__':
    # 启动课程导出。
    main()

# USQuant：美股小资金量化 MVP

已在当前 Mac 环境运行 Python + C++ 的离线链路：合成行情 → 严格清洗 → 数据库 → 均线策略 → 下一根开盘成交 → 风控 → 持久化结果与 HTML 报告。另有 Alpaca 模拟账户限价单接口；实盘入口禁用。

[开源项目调研](docs/research.md) · [架构与后续工作](docs/architecture.md) · [验证记录](docs/verification.md)

## 快速运行

在本目录执行（Python ≥3.9，C++17 编译器；离线模式没有第三方 Python 依赖）：

```sh
python3 scripts/build_cpp.py
python3 -m unittest discover -s tests -v
python3 -m usquant demo --native
python3 -m usquant paper --native
```

打开 `reports/latest.html` 查看权益和成交。每次运行产生独立 `reports/<run_id>.json`，并写入数据库 `runs` 表。`demo` 使用固定的 260 根合成日线；合成数据只验证程序，收益没有投资含义，也不使用真实交易日历。`paper` 是离线历史回放，每次重新初始化资金，不是券商模拟盘或持续运行交易机器人。

不编译 C++ 时，省略 `--native` 可运行 Python 版本。选择 `--native` 时库缺失会明确失败，不会静默回退。

## CSV 数据

必填列：`symbol,ts,open,high,low,close,volume`。可选：`source`（默认 csv）、`adjustment`（默认 raw）。`ts` 必须含时区，例如 `2024-01-02T21:00:00+00:00`。

```sh
python3 -m usquant ingest --csv /absolute/path/bars.csv
python3 -m usquant backtest --symbol SPY --source csv --native
python3 -m usquant paper --symbol SPY --source csv --native
```

清洗会统一 UTC、排序并合并完全相同的重复记录。非法数值、OHLC 错误和冲突重复数据中止整个批次。数据库价格字段仅容忍 1e-12 的浮点舍入差异以支持 Mac/Linux 重复导入，其他字段精确比较，不覆盖已有记录。主键包括 symbol/time/source/adjustment，避免混合不同数据源。当前引擎一次只接受一个股票的 raw 日线序列。调用方必须保证输入是完成的日线，不能输入分钟线或未完成的当天行情。

## MySQL 部署

本机已安装 Docker Desktop，MySQL 8.4 容器已启动。全部 21 项测试通过，包括真实 MySQL 数据读写和事务回滚。

新机器安装 Docker 后，创建 `.env`（不要提交），把 `.env.example` 中两个数据库密码改为不同的强密码。本机已生成私有配置，请勿覆盖：

```sh
cp .env.example .env
# 编辑 .env 后：
set -a
. ./.env
set +a
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install '.[mysql]'
docker compose up -d --wait
python3 -m usquant demo --backend mysql --native
USQUANT_TEST_MYSQL=1 python3 -m unittest discover -s tests -v
```

Compose 只绑定 127.0.0.1；MySQL 使用持久卷。凭据来自环境变量，不进入运行报告。Python 不会自动读取 `.env`，Compose 会。停止服务使用 `docker compose stop`，保留数据库卷。

## 真实行情（只读）

Alpaca 凭据只通过环境变量提供，建议使用模拟账户凭据。默认 IEX，不假定拥有 SIP 权限。尚未填写 Alpaca 凭据，目前仅用模拟 HTTP 响应验证分页与 GET 请求，未进行真实 API 验证。

```sh
export ALPACA_API_KEY='your-key'
export ALPACA_SECRET_KEY='your-secret'
python3 -m usquant fetch --symbol SPY --start 2024-01-01T00:00:00Z --end 2024-04-01T00:00:00Z
python3 -m usquant backtest --symbol SPY --source alpaca-iex --native
```

抓取使用 raw 日线，保存独立 CSV 快照。建议使用历史结束日期，避免未完成日线。HTTP 错误中止运行；尚无自动重试/速率控制/流式接入。没有下载第三方框架代码或从网页抓取行情。

## 策略、成交与风控

配置见 `config/example.json`：初始 2500 USD、5/20 日均线、整数股仅做多。上一根收盘快均线高于慢均线，下一根开盘入场；反向信号下一根开盘平仓。现金保留手续费，成交价格包含固定方向滑点。

默认单股票仓位 20%、单笔入场金额 500 USD、历史已知成交量参与率 1%、峰值回撤 8%、单日损失 3%。停机后本次运行不会重新开仓；已有持仓在可成交的下一根开盘尝试退出。紧急开关拒绝入场。零成交量不模拟成交。停机阈值不能保证实际亏损不超过阈值，隔夜跳空仍可能超限。

清仓为风险减少动作，不受入场金额/参与率限制；这只是研究撮合假设，并不说明市场能全部成交。期末持仓按收盘价估值，不强制平仓。回测结果含总收益、最大回撤、成交记录和每根权益；未实现 Sharpe、基准比较或样本外策略评估。

## 实盘边界与未完成项

`python3 -m usquant live` 明确失败；`LiveBroker` 构造也拒绝运行。配置或环境变量不能打开实盘。后续必须单独得到用户确认，再实现并审查执行适配器。

生产前还需：交易日历/数据陈旧检查、拆分与分红、退市与幸存者偏差、持续模拟账户和重启恢复、订单状态机及幂等键、部分成交和账户对账、告警、断线与限频、结算资金和账户交易权限。README 中的样例策略没有被证明具有盈利能力。

## Alpaca 模拟账户实时接口

固定连接 `https://paper-api.alpaca.markets`，拒绝重定向，不能配置实盘地址。先配置模拟账户的 ALPACA_API_KEY、ALPACA_SECRET_KEY。预览仅发 GET；加 --submit 才向模拟账户发订单：

```sh
python3 -m usquant.paper_broker --symbol SPY --qty 1 --side buy --client-id spy-test-001
python3 -m usquant.paper_broker --symbol SPY --qty 1 --side buy --client-id spy-test-001 --submit
```

仅支持正常交易时段、整数股、股价 ≥1 USD 的美股限价 DAY 单。入场检查：现金、单笔金额、单股仓位、总敞口、单日损失、已观察峰值回撤、kill switch。禁止卖超已有持仓；有任何挂单时拒绝新订单；报价超过 60 秒或来自未来时拒绝。没有离线回测的成交量参与率撮合模型。

提交前写入 data/paper.sqlite。重复原 client-id 查询券商状态而不再次 POST，同一 id 参数不能改变。超时后按原 id 对账，未决提交阻止其他新订单；未查到旧订单时必须人工检查模拟账户，不要更换 id 或删除日志绕过保护。日志保存订单状态和账户峰值，不保存凭据。accepted 不等于成交。

每次只执行一次；回测信号尚未自动循环提交。本接口已通过模拟 HTTP 测试，但未提供凭据，未接真实模拟账户。请使用专用模拟账户，避免其他程序同时交易；本地锁不能约束外部操作。峰值只覆盖本程序观察期。实盘必须另行明确确认后实现。

## 容器内完整离线 MVP

填好 .env 数据库密码后：

```sh
docker compose --profile mvp build app
docker compose --profile mvp run --rm app
```

构建编译 C++ 并运行单元测试；启动等待 MySQL 健康后执行 demo。报告写回 reports/，数据库保留在卷。当前机器已完成该流程验证。容器默认没有券商凭据，只运行离线链路。

## 当前 Mac 已安装的环境

Docker Desktop、GitHub CLI、项目 .venv 和 MySQL 驱动已安装。若终端找不到 docker，可使用项目包装脚本：

```sh
./scripts/docker.sh compose up -d --wait mysql
./scripts/verify_mysql.sh
./scripts/docker.sh compose --profile mvp run --rm app
```

验证脚本读取本机 .env，不输出密码。MySQL 只绑定 127.0.0.1:3306。用 `./scripts/docker.sh compose stop` 停止服务并保留数据；再次运行 up 恢复。未来编辑源码后，容器执行前重新 build app。

[GitHub 学习指南](docs/github-guide.md)。GitHub 私有仓库：[yongshangliuknu-afk/usquant](https://github.com/yongshangliuknu-afk/usquant)。本机和 GitHub 的代码通过 Git 同步。

# Local LEAN verification — 20 October 2026

Both backtests ran with the actual official ARM64 Docker image, network disabled, no brokerage credentials, and read-only upstream sample data/source mounts. Host is Apple silicon. Container reports LEAN v2.5.0.0 and Python 3.11.9.

| Run | Algorithm | Dates | Orders | Ending equity |
|---|---|---|---|---|
| `20261020-115749-467045-official` | Unmodified upstream BasicTemplateAlgorithm | 7–11 October 2013 | 1 | USD 101,691.92 (initial USD 100,000) |
| `20261020-115820-103816-first` | FirstBacktest learning exercise | 7–11 October 2013 | 1 | USD 2,506.39 (initial USD 2,500) |

The exercise logged a signal at 7 October 2013 09:31 New York time, Submitted and Filled events for 3 SPY shares, a USD 1 modelled fee, and final portfolio value. The result JSON contained statistics and orders; the launcher returned success only after inspecting output artifacts. All 11 data requests succeeded in both completed runs. These are five-day engine/learning checks, not evidence of investment performance; annualized statistics from this tiny sample are not meaningful.

Each result directory contains `config.json`, `provenance.json`, `console.log`, algorithm log, result JSON, summary JSON and order events as emitted by LEAN. Runtime artifacts are local, excluded from GitHub. Source and prebuilt image references are pinned independently; the engine was not compiled locally from the checked-out source. Full upstream unit/regression suites were not run. AMD64 is configured but not locally tested on this ARM machine.

The first exercise initially failed on an enum spelling; it was corrected to `QUANT_CONNECT_BROKERAGE` and rerun successfully. Failed-run logs remain locally for traceability. Static syntax and offline-configuration checks also passed. No broker paper or real orders were sent, and no scheduled process was installed.


## 八课课程整体验收 — 2026-10-20

八课及额外成本/停机分支由 scripts/run_suite.py 顺序运行，全部通过各课断言、结果统计与订单数检查。使用本机同一官方 ARM64 镜像，容器断网，不挂载密钥。下表是实际运行记录，金额单位 USD，初始资金均为 2500。

| 实验 | 本地运行编号 | 订单数 | 期末资产 | 完成证据 |
|---|---|---|---|---|
| first default | `20261020-124822-961040-first` | 1 | 2506.39 | 结果统计与订单验收通过 |
| data default | `20261020-124827-877516-data` | 0 | 2500 | 2024-02-01 00:00:00 COURSE_OK:02 observations=21 |
| factors default | `20261020-124832-774173-factors` | 41 | 2460.70 | 2013-10-11 16:00:00 COURSE_OK:03 ready_bars=1891 |
| portfolio default | `20261020-124837-593962-portfolio` | 4 | 2493.24 | 2013-10-11 16:00:00 COURSE_OK:04 capped=6 halted=True |
| evaluation --parameter cost-bps=5 | `20261020-124842-592088-evaluation` | 1 | 2506.18 | 2013-10-11 16:00:00 COURSE_OK:05 |
| orders default | `20261020-124847-601331-orders` | 2 | 2501.49 | 2013-10-11 16:00:00 COURSE_OK:06 canceled_and_filled=True |
| deployment --parameter scenario=normal | `20261020-124852-648620-deployment` | 1 | 2501.46 | 2013-10-11 16:00:00 COURSE_OK:07 scenario=normal blocked=0 offline_only=True |
| maintenance default | `20261020-124857-518848-maintenance` | 1 | 2501.46 | 2013-10-11 16:00:00 COURSE_OK:08 bars=1950 fills=1 |
| evaluation --parameter cost-bps=20 | `20261020-124902-411329-evaluation` | 1 | 2505.52 | 2013-10-11 16:00:00 COURSE_OK:05 |
| deployment --parameter scenario=kill | `20261020-124907-314617-deployment` | 0 | 2500 | 2013-10-11 16:00:00 COURSE_OK:07 scenario=kill blocked=1950 offline_only=True |

第二课从现有 MySQL 只读一致性事务导出 NVDA 2024-01 的 21 条 raw IEX 日线，保留内容哈希；LEAN 接收 21 条，不交易。SQL 练习四条查询分别返回 18 个系列分组、21 条行情、50 条受限财务记录和 8 个公司分组，没有写入数据库。这里只验证既有小样本，不声称全市场覆盖或严格历史财务面板。

第五课两种滑点情景均已从主结果生成 evaluation.json。第三课 41 张请求中 40 张成交、1 张购买力不足而无效，费用 $40；订单数量不能当成交数量。第三课亏损及第四课回撤停机结果原样保留，不以正收益作为完成标准。第六课两张订单包含一张已撤和一张已成交，都是历史模拟。

Alpaca paper 预检另外完成四种 GET，账户 active、未 blocked，查询时持仓与未完成订单均为 0；orders_submitted=0。这只证明当时的只读连接，未验证 LEAN 券商订单或持续实时运行。私有报告和数据快照不提交 GitHub。

标准 unittest 的 4 个边界测试、全部自写 Python 语法、课程本地文档链接检查通过。GitHub CI 执行语法和工具测试，不下载引擎或访问账户。源码全量构建、官方全部回归、AMD64、券商部分成交/拒单/断线/重启恢复、生产风控和真实订单仍未验收；第六至八课提供操作方法和后续作业，不能将课件完成理解为生产部署完成。

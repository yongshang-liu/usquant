# 美股量化开源项目调研

核查日期：2026-10-08。资料为项目官方仓库、许可证、提交和发布页面。GitHub 网页部分日期未加载，未把搜索抓取日期当作最后提交日期。下面的适用性判断是本项目的工程评估，没有复制这些项目的源码。

| 项目 | 架构及职责 | 维护证据与边界 | 许可证 | 对本项目的价值 |
|---|---|---|---|---|
| [LEAN](https://github.com/QuantConnect/Lean) | C# 引擎，支持 Python 策略；事件驱动；数据、算法、交易和券商模块完整 | 完整测试、工具和券商生态；[发布页](https://github.com/QuantConnect/Lean/releases) 的正式 release 不适合单独推断当前开发频率，需结合提交记录 | Apache-2.0 | 学习数据/策略/交易隔离；直接采用会引入 .NET，偏离 C++ 要求 |
| [Backtrader](https://github.com/mementum/backtrader) | Python Cerebro，feed/strategy/broker/analyzer；事件回测和传统券商接口 | [主分支提交页](https://github.com/mementum/backtrader/commits/master/) 需核查选定版本最近提交，旧接口有维护风险；旧券商接口需重新验证 | GPL-3.0 | 适合研究事件语义；不作为新系统的默认执行依赖 |
| [vectorbt](https://github.com/polakowo/vectorbt) | NumPy/pandas/Numba 向量化研究；参数扫描快 | [发布页](https://github.com/polakowo/vectorbt/releases) 需锁定采用版本；社区版和商业产品须分开评估 | [Apache-2.0 + Commons Clause](https://github.com/polakowo/vectorbt/blob/master/LICENSE.md)，属于 fair-code，不能简单视为无限制开源 | 适合批量研究，不能代替订单生命周期；MVP 不引入该依赖 |
| [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) | Rust 核心、Python 接口；确定性事件驱动；统一行情与交易适配器 | develop/nightly 构建和安全检查；[官方组织](https://github.com/nautechsystems) 提供提交记录；二进制和操作系统要求需核查 | LGPL-3.0；另有[商标政策](https://github.com/nautechsystems/nautilus_trader/blob/develop/TRADEMARK.md) | 最值得参考回测/实时共享领域模型；Rust 技术栈不同，集成留到后续 |
| [Qlib](https://github.com/microsoft/qlib) | 数据处理、特征、模型训练、实验管理和投资组合研究；含 Cython 扩展 | [发布页](https://github.com/microsoft/qlib/releases) 有持续功能/修复记录，仓库有 tests 与研究集成；不是开箱即用美股券商执行系统 | MIT | 后续接入因子与 ML；初期简单策略先验证数据和成本 |
| [Alpaca Python SDK / 示例](https://github.com/alpacahq/alpaca-py/tree/master/examples) | 行情、账户、历史请求和交易流 SDK；不是独立回测引擎 | [发布页](https://github.com/alpacahq/alpaca-py/releases) 需与所用 API 版本核对；官方 SDK 和 examples 同仓维护 | [Apache-2.0](https://github.com/alpacahq/alpaca-py/blob/master/LICENSE) | 参考美股接入边界；本版实现 REST 行情及固定模拟账户订单适配器，实盘禁用 |

许可证结论只描述核查的官方文件；如果以后复制、修改或分发第三方代码，需按锁定版本重新核查其许可证和依赖。本项目目前不依赖以上六个框架。

## MVP 决策

Python 负责采集、清洗、存储、策略调度、风控和报告；C++17 提供通过 C ABI/ctypes 调用的均线计算模块；MySQL 作为部署存储，SQLite 提供无服务离线验证路径。采用单股票、日线、整数股、现金、仅做多模型，降低首次验证范围。回测和本地模拟回放共享同一个执行引擎。

下一阶段若需要成熟执行系统，优先评估 NautilusTrader 的券商覆盖及运维成本，或接受 .NET 后选择 LEAN。不要为了使用 C++ 而重新实现完整交易所订单系统。

## 数据与模拟边界

[Alpaca 行情 FAQ](https://docs.alpaca.markets/us/docs/market-data-faq) 区分 IEX 与 SIP：覆盖范围和权限不同，免费 IEX 数据不能等同全市场成交量。读取接口明确指定 feed、raw adjustment，分页并留存 CSV 快照。用户提供凭据后才能验证其数据权限；本次没有访问账户。

[Alpaca 模拟交易说明](https://docs.alpaca.markets/us/docs/paper-trading) 明确模拟撮合不能覆盖所有真实交易因素。本地回放更简单：没有订单簿、排队、部分成交、券商拒单、借券、实际交易日历、公司行动、税费或实时数据延迟模型。当前结果不能用来决定真实资金投入。

接口依据：[订单与 client_order_id](https://docs.alpaca.markets/us/docs/working-with-orders)、[按 client-id 查询订单](https://docs.alpaca.markets/us/reference/getorderbyclientorderid)。适配器为独立实现，没有复制 SDK 源码。

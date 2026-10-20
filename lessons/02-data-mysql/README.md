# 第二课：MySQL → 固定快照 → LEAN 自定义数据

## 学完后你应能做到

解释数据库记录、导出文件和算法数据对象的区别；用只读事务提取一个确定范围；核对行数和哈希；说明完整日线何时才可用。理解为什么“已经能把 CSV 读进 LEAN”不等于“已完成股票公司行动和财务因子处理”。

先修：第一课、基本 SELECT、日期与路径。代码在 [main.py](main.py)、[逐行注释导出器](../../scripts/export_mysql.py)，只读查询在 [course02.sql](../../sql/course02.sql)。

## 数据契约

本实验用 MySQL 中 NVDA 的 2024 年 1 月日线，来源固定为 alpaca-iex、复权固定为 raw。它不是全市场综合成交数据，也不应拿原始价格跨拆股直接计算长期收益。字段 session 是原行情日期；available_date 是本课采用的保守可用点：次日纽约零点。

例如 1 月 3 日完整日线不能在 1 月 3 日开盘时被算法看见。本课延后至 1 月 4 日零点。它仅演示保守时序，不是对服务商真实发布延迟的精确建模。证券身份、公司行动和交易日历需要另行验证。

## 按顺序运行

```sh
# 已有本项目 .venv 时，直接用它导出；其他电脑可创建自己的虚拟环境。
python3 -m venv .course-venv
# 安装课程 MySQL 客户端；不替换 LEAN 引擎。
.course-venv/bin/python -m pip install -r requirements-course.txt
# 本机已有 .venv 可把下面的解释器换成 .venv/bin/python。
.course-venv/bin/python scripts/export_mysql.py
# 将只读快照作为自定义数据交给真实 LEAN。
python3 scripts/run_lean.py data
```

Windows 使用虚拟环境下 Scripts/python.exe。凭据从本机 .env 或环境变量读取，不填到命令行、不提交 GitHub。数据库需要包含既有 bars 表；空电脑不自动下载完整数据库，缺少数据时程序会停止。

## 按代码顺序理解

导出器打开只读一致性事务，用参数化 SQL 固定证券、来源、复权和半开时间区间。它不修改 bars，也不从整个数据库提取所有信息。CSV 写完计算 SHA256，同名文件若发生变化，要求研究者改用新目录，而不是静默覆盖。

main.py 的 RawClose 是 PythonData 子类。get_source 指明容器里的文件位置；reader 逐行构造全新对象，分别设置 symbol、time、end_time、value 和原交易日。DataCourse 注册自定义订阅后只观察、不交易，并断言实际接收到数据。

原始 CSV 和清单在 local-data/lesson02；容器只读挂载该目录，不知道 MySQL 密码。该设计避免每次回测都读取一个正在变动的数据库。

## 实际验收

本机初次验证导出 21 行，LEAN 接收 21 条观测，0 笔订单，DATA 日志展示 session 与 available 的时间差。零订单对数据课是正常的，不能沿用第一课“必须有订单”的验收标准。COURSE_OK:02 必须出现在日志。

## 财务数据的补充练习

在 Sequel Ace 执行 course02.sql 的后两条查询。观察同一 period_end 可能有多个 accession、filed、期间起点和单位。不要把这些记录相加，不要以“公司×年份”直接去重。accepted_utc 缺失时不能填成 period_end。

本课没有把所有财务观测展开成一个虚假的标准因子表，也没有声称当前 SEC API 是严格历史时点档案。将来写财务因子时，应选择特定概念、单位、期间和披露版本，并依据可用时刻加入算法。

## 动手练习与参考答案

1. 为什么使用 `< '2024-02-01'`？因为半开区间让相邻月份边界不重复，也不用猜 1 月最后一天的最后一秒。
2. 为什么用新对象解析每行？重复复用可变对象可能让前一条记录被后一条值覆盖，破坏事件流。
3. 试着修改快照后再次导出。预期拒绝覆盖；恢复原快照或选择新版本目录，不要关闭检查来掩盖数据修订。
4. 有多少价格系列？按 symbol/source/adjustment 分组计数，而不是只按 symbol 合并。raw 和 all 不能混成一条时间序列。
5. 为什么这不是可交易的 NVDA 原生数据？PythonData 观察对象没有自动补齐股票代码映射、拆股股息、原生交易时段和执行模型。不要直接给 NVDA_SOURCE 下单。

## 排错

数据库连接失败：先确认 Docker MySQL、主机和端口，再检查本机配置，不公开密码。No module named pymysql：说明用了错误解释器。未接收快照：检查文件、容器挂载和可用时间是否落在回测范围。收到重复行：检查是否开启了填充，或把同一固定文件逐日当新数据重复解析。

完成标准：能解释 21 行从哪里来、何时进入算法、为什么没有订单，并保留清单和结果目录。下一课：[指标和因子](../03-factors/README.md)。

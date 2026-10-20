# 运行配置逐项解释

JSON 标准不允许写 // 或 # 注释，因此 configs/engine-lock.json 和每次生成的 config.json 保持可解析，中文说明集中放在这里。修改运行目录中的 config.json 不会改变下一次自动生成的配置；要调整课程入口，应理解 scripts/run_lean.py 的 prepare。

## 一、固定版本文件 engine-lock.json

| 字段 | 解释 |
|---|---|
| source_repository | 官方源码仓库地址，说明来源与归属，不是我们的原创引擎。 |
| source_commit | 作为学习基线的源码提交号。Git 子模块固定到一个具体版本，避免每次打开看到不同代码。 |
| images | 按 CPU 架构记录实际运行镜像。源代码提交与预编译镜像分别固定，不能声称它们一定是完全相同的构建。 |
| arm64 | Apple 芯片使用的官方 ARM 镜像。摘要 @sha256 表示按内容标识选取镜像，不是不断变化的 latest。 |
| amd64 | Intel/AMD x86-64 对应镜像；虽然 AMD64 名称含 AMD，Intel 电脑也使用这一架构。当前本机只验证了 ARM64。 |
| note | 提醒使用者区分“读哪一版源码”和“实际运行哪一份二进制”。 |

## 二、生成的引擎配置

| 字段 | 解释 |
|---|---|
| environment | 当前为 backtesting，选择历史回测处理器组合。 |
| environments | 本次配置只留下 backtesting。官方源文件中的其他环境仍完整保留。 |
| live-mode | 当前 False，使用历史模式。未来 True 表示实时模式，**不等于一定使用真实资金**，券商纸盘也可能需要实时模式。 |
| close-automatically | 回测完成后退出进程，方便自动化检查。 |
| data-folder | 容器内的历史数据位置 /Lean/Data，本课映射到官方 Data。 |
| results-destination-folder | 容器内输出位置 /Results，对应本机此次 results 子目录。 |
| object-store-root | 算法可用的 Object Store 位置；本课放在本次结果目录的 storage 中。 |
| algorithm-language | Python 是策略语言，核心引擎仍是 C#。 |
| algorithm-type-name | 要实例化的类名，official 为 BasicTemplateAlgorithm，first 为 FirstBacktest。 |
| algorithm-location | 对应 Python 文件的容器路径，不是本机路径。 |
| python-additional-paths | 给容器内 Python 增加模块查找路径，不会安装缺失包。 |
| job-user-id | 本地占位用户编号 0，不代表已经登录云平台。 |
| api-access-token | 当前为空，不读取或上传你的云平台 API 密钥。 |
| job-organization-id | 当前为空，没有绑定 QuantConnect 云组织。 |
| algorithm-id | 本地算法作业名称，帮助区分日志文件，不是股票代码。 |
| job-project-id | 本地占位项目编号，不是账户号码。 |

官方配置还有系统处理器字段。log-handler 管日志，job-queue-handler 提供作业，data-provider 读取文件，map/factor provider 管代码映射和公司行动相关文件；回测环境里的 setup/result/data-feed/real-time/history/transaction handler 分别管理初始化、结果、数据推进、模拟时钟、历史读取和订单事务。它们都是 LEAN 组件，不是我们自己替代实现。

## 三、本机目录与容器目录

| 本机 | 容器内 | 权限与原因 |
|---|---|---|
| vendor/lean/Data | /Lean/Data | 只读，保护官方样例。 |
| vendor/lean | /Upstream | 只读，用来加载官方 Python 示例。 |
| lessons | /Lessons | 只读，容器不能改课程代码。 |
| 本次 results 子目录 | /Results | 可写，保存真实运行过程。 |

Docker run 是启动容器，--rm 是运行后移除临时容器，不会删除绑定的结果。--network none 禁止运行中访问网络；宿主机首次下载镜像仍可能需要联网。--cpus 2 与 --memory 4g 限定计算资源。我们没有传 --env-file，也没有挂载本机 .env 或券商密钥。

## 四、provenance.json

source_commit 是本次查询到的实际源码提交；runtime_image 是实际选择的镜像摘要；architecture 是架构；lesson 是课程；mode 是 offline-backtesting。文件名时间是本机运行时间，不是历史交易日期。

这一份清单帮助复现，但不自动证明数据无偏差，也不等同于完整的数据授权或历史时点审计。

# 本机验证记录

日期：2026-10-08（用户时区 Asia/Seoul）。macOS ARM64，Python 3.9.6。

- C++17 指标编译成功，与 Python 多窗口 SMA 数值一致。
- Docker Desktop 已安装；服务版本 29.8.2，Compose v5.5.1。
- MySQL 8.4 容器健康，端口仅绑定 127.0.0.1；密码在本机 .env，不进入 Git。
- 项目虚拟环境与 PyMySQL RSA 认证依赖已安装。修复了真实 MySQL 测试暴露的加密依赖缺失。
- 全部 21 项测试通过，无跳过，包含真实 MySQL 读写、重复导入与事务回滚。
- MySQL demo 完整运行：260 根合成日线、10 次成交，最终权益 2601.726883 USD。仅程序回归数据，不能视为投资收益。
- SQLite 离线链路与报告生成通过。
- 实盘 CLI 拒绝执行，LiveBroker 拒绝构造。
- Alpaca 行情分页、模拟账户订单与风控通过伪响应测试；未填写真实凭据、未发送券商订单。
- Docker 应用构建测试通过；容器内 Python+C++ → MySQL → 回测 → 报告完整运行成功，结果与 Mac 本地相同。
- 项目已初始化独立 main Git 仓库，排除了 .env、数据库、订单日志和编译产物；GitHub 已完成用户授权，私有仓库为 yongshang-liu/usquant。远程 Actions 的结果以 GitHub 页面为准。

重现：在项目目录运行 `./scripts/verify_mysql.sh`；容器使用 README 的 build/run 命令。

跨平台验证发现 Mac/Linux libm 的末位浮点差异会误报数据冲突。存储层价格比较容忍 1e-12 相对/绝对误差，仍拒绝实质冲突；原始数据不覆盖，已补回归验证。

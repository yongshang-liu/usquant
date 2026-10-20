# LEAN 中文系统学习路线

完整材料已整理为[八课课程目录](curriculum.md)。从第一课开始，先预测、再运行、最后解释，不需要一次读懂全部引擎。

1. [最小策略与订单事件](../lessons/01-first-backtest/README.md)：谁调用 initialize、on_data、on_order_event？
2. [数据与 MySQL](../lessons/02-data-mysql/README.md)：一个数字在当时是否可知？只读导出并接入真实 LEAN。
3. [指标与因子](../lessons/03-factors/README.md)：信号用了什么历史数据？指标是否已就绪？
4. [组合与风险](../lessons/04-portfolio-risk/README.md)：信号如何变成仓位？超限时怎样处理？
5. [回测与评估](../lessons/05-backtest-evaluation/README.md)：成本和采样会怎样改变结论？如何保留真正的样本外？
6. [订单与券商模拟准备](../lessons/06-paper-orders/README.md)：请求、撤销、成交怎样确认？怎样先核验模拟账户？
7. [真实盘部署方法](../lessons/07-live-deployment/README.md)：限额、停机、重启和人工接管怎样设计？
8. [引擎与维护](../lessons/08-engine-maintenance/README.md)：沿源码追踪事件，怎样测试、升级与回滚？

每课都有中文说明、自写代码的逐行注释、运行步骤、验收及带答案练习。官方源码保持原样，源码导读按涉及模块展开，没有声称翻译全部引擎。配套[配置解释](zh/configuration.md)和[实际验证记录](verification.md)帮助你区分方法、材料与运行证据。

八课历史实验已经实际运行；券商模拟账户完成只读访问。新的 LEAN 持续券商模拟及真实盘尚未部署，课程保留完整学习路线和操作作业，当前不发送券商订单。未来真实盘目标继续保留，实施时按具体策略、账户和限额另行验收。

# C08 只读阶段观察器的构建序列

根线程完整审阅四文件补丁并冻结capture后，单次显式运行此owner。它仅依次调用已审构建helper的DebugCPU、Debug、Release动作，保留每个真实helper出口及其自身MSBuild收据。前项失败即停止后续配置，原始日志和部分产物保留，不重试。

CPU关闭两个测试宏；GPU配置启用C08_STAGE_TRACE及C08_CAUSAL_TRACE。程序/对象位于独立tests/outputs和无空格Temp路径，原canonical、runtime_r5/r6与原r2 PRE受保护。构建不是观察器实现、物理或论文验收。

本owner不调用help、GenCase、solver、native、VTK或清理。终态仅向原线程queue一次，45秒超时视为可能已投递，不重发、不布防另一个watcher。后续Debug短检查及.90秒Release观察都需根线程审阅各自新入口及前置结果后另行启动；其他psi仍未准入。

唯一入口为 `D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_causal_build_sequence_r1.py --execution-authorized --notify`。旧全3秒结果及本轮图CSV不因构建改变。没有SHA扫描。

# C08 NoPen 独立短窗诊断

用户明确要求试开 NoPenetration。本轮仅使用 tests 内隔离程序，从原服务器10秒弹性PRE重新开展一次撤墙后0.15秒GPU计算；不是从失败塑性PART重启，也不重跑10秒预载。正式XML/BAT/runtime不修改。

只改变既有 NoPenetration=1，并通过命令 `-mdbc_freeslip:1` 保留该设置。ψ=0、dp=.04、dt=2.5e-6 s、输出.01 s、应力率修正、动态渗流/变孔隙/变k等全部保持控制组，人工应力关闭。总全局步上限4060000，对应15个实际保存帧。没有额外half或长程自动准入。

现有NoPen对保留左FreeSlip墙和底NoSlip墙的法向速度及位移生效；切向滑移政策仍各自保持。它不是严格的几何gap投影，也没有把约束反力同步反馈给finished Ace、Darcy与J/应变积分，故本轮只能诊断旧投影是否截断穿透失稳链，不据正常退出宣称完整u-pl物理一致性或正式验收。

隔离源码仅豁免该handoff容器的NoPen组合、将弹性源准入合同中NoPen两个字段映射回源Std/false，其他源ID、材料、几何、法向、时钟与原生安全门保持。程序日志及BI4标明LegacyProjectionDiagnostic，明确没有声称源与接收阶段是同一NoPen算子。

准备新增本owner脚本、配置和记录；结果输出 `outputs/upl_c08_nopen_short_r2`。所有start/call/run/status在logs，原始输出只读保留。求解后单独审查实际15帧22数组、6800 IDs、实际时钟、signed dterror、P0与J/n/V/rho/k ledger，检查z<0和固定7010以及全体土粒压力、沉降、应力、速度与κ，和原AS0保存的11帧做描述性对比。未达0.15秒则报告真实退出/首因与最后已保存console行，不推断未保存停止时刻。

本脚本全文审阅及隔离DebugCPU/Release构建通过后才可调用；它不解码、不启动后续solver、不queue、不重新布防。失败或部分输出禁止覆盖或盲目重跑。

R1 stopped before GenCase/solver: the configuration writer emitted a duplicate XML declaration. Its invalid config and run receipt remain protected. R2 changes only XML serialization and output tag; no solver was started or repeated in R1.

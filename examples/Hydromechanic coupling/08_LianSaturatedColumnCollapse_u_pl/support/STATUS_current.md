# 当前发包状态

**ψ0 r4完整GPU接收计算正在运行（2026-11-08 02:22:08 +09:00观测），目标从原10 s认证PRE继续到总时刻13 s。owner PID70440→根BAT/cmd PID78608→solver PID77788；GenCase PID79792已真实exit0。ψ=+2.5°和ψ=−5°尚未启动，本轮CPU源及CPU接收均未启动。** 启动/状态证据为 `tests/logs/upl_c08_formal_psi0_r4_r1.start.json`、同prefix的 `.status.json`；solver实际创建于02:20:54，exe为 `support/runtime_r4/DualSPHysics5.2_GEO_win64.exe`，argv含 `-gpu:0 -stable -mdbc_freeslip:1`，实际父进程为78608。当前只记录运行中，不预记正常退出或native/物理通过。

本次读取的Run.out最后原样PART行为 `Part_0001     10.020000       4008000     4000    2413.36  08-11-2026 04:22:09`。实际设备为RTX3050；按目前早期控制台速率估计剩余约2小时，会随运行变化，不是受控性能基准、解码后的精确native时钟或保证完成时刻。owner已以`--notify`启动，终态将按既定流程仅尝试一次同线程回调；目前尚未终止，不在此主动发起通知或下一求解。

根已复核新正式程序对原NoPen 0.15 s结果的15帧回归，全部22数组及signed-clock逐字节相同；其范围仍是该短窗，不代表本次完整3 s已通过。当前代码/配置checkpoint已由根核实本地与远端一致：`3d19842d174eea580287801265f23c1cc62bad1f`；程序身份仍以实际启动记录及其冻结构建来源为准。

原完整ψ0 r3 GPU失败及其out原样保留，最后保存总时刻10.11 s；已定位state墙点791并观察到土点7010穿底。人工应力短试也失败，约推迟7.25 ms。既有NoPen开启/AS关闭的0.15 s GPU诊断已完成，15帧原生安全门通过、保存帧未见穿底/左墙；该短窗结论见 `tests/notes/upl_c08_nopen_result_r1.md`，不替代正在运行的完整3 s审查。

人工应力结论与图CSV见 `tests/notes/upl_c08_as_short_review_r1.md`。墙应力放大主要来自侧向稀薄支撑的外推，见 `tests/notes/upl_c08_wall_stress_decompose_r1.md`。本轮r4采用既有NoPen法向速度/位移的受限分步投影；Run.out明确 `No Penetration=True`、`ArtificialStress="None"` 和正式policy `LegacyOperatorSplitReleaseOnly`。投影约束反力未回馈同一步Darcy，`ReactionClosed=false`；不据正常退出声称反力闭合接触或论文精度验收。

当前运行使用根目录r4正式模板、`support/runtime_r4`程序及r4后处理，操作说明见根 `README.md` 和 `README_server_r4.md`。旧r3输入、runtime、失败out及README保留，本轮未移动或覆盖；更早r1/r2根入口的可恢复归档和历史runtime/ZIP/manifest也保留。

服务器r2 GPU 10 s PRE已回传本机。实际Run.out确认本次加载原 `CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4`，源为legacy MR1 ElasticV1，实际时刻10.000000000374257、completed_step=4000000。随后只撤右墙260个样本，damping/Shepard关闭，FreeSeepage保持开启；源数据未改名或重算。三个GPU r4入口均固定该源；CPU入口固定自己的r3 CPU源，当前不存在即拒绝，不能将GPU源当作CPU证据。已有r4 out也拒绝覆盖。

当前r4接收启动器接入完整双击流程：求解前检查Python 3及numpy/matplotlib和runtime中的C08Native/PartVTK；优先D:/anaconda3/python.exe，否则PATH的python，不自动安装。接收正常退出后执行native→PartFluid→PartBound→PNG/CSV。本轮没有r4 PRELOAD入口，不重跑既有10 s源；正在运行的ψ0尚未执行本次后处理。

原入口加`--postprocess`只处理已完成输出，绝不GenCase或求解；`--unattended`可与它任意顺序并用。已完成且匹配的后处理可复用，失败或未绑定的部分结果不覆盖。回传r2 PRE的Fluid/Bound各1001帧已完成，不需要重新认领或导出。PartFluid/PartBound分别保存，预载为5000/2060，撤墙后接收为5000/1800；不生成PartAll。官方VTK显示坐标float，原BI4精度保留，κ不是完整塑性应变张量。

现有LianCollapse_upl_win64_r3.zip及其manifest/SHA仍是更新前历史快照，未包含本次入口/后处理更新，不以旧清单证明当前文件。使用新流程需同步当前脚本及所需runtime工具，并安装Python依赖；无须重编物理程序。

已通过四种构建、CPU/GPU源与接收短窗的全部22数组及带符号时钟精确连续性、旧默认回归、三个材料短承接、塑性源拒绝及新路径解压/四份GenCase输入检查。源码及说明见tests/notes/upl_preload_handoff_root_r1.md。

10 s源的正常完成已观测；三组完整塌陷、论文精度及预载平衡的物理验收仍需实际数据。通用塑性/HG/任意 PART 重启仍不在本次范围内。所有旧包、程序和原始结果均保留。

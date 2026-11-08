# 当前发包状态

**根目录r5单组ψ0的3 s计算及自动后处理已完成，物理验收待排查。** 原owner80120→根BAT/cmd81612→GPU solver63384所有权与真实退出均通过，GenCase/solver/BAT均exit0；RTX3050实际求解耗时约7972 s。已完成global5200000、300帧，实际末时刻13.000000001326498 s、相对原PRE为3.000000000952241 s。唯一native读取、分别PartFluid/PartBound各300帧及全部PNG/CSV均成功，不重复这些工具。前60帧的22数组/time和signed clock与保留窗口逐字节相同；原数值门和浅床5点检查通过，全程土粒最低z=.01243938 m，无保存帧穿底。

完整窗出现新的物理问题：τ=.63/.64 s有−450.667/+1352.125 kPa压力簇，约.8 s后运动很弱；末前缘粒子中心x=4.70149 m、速度RMS9.04e−5 m/s，1.2 s形态尚未复现论文的后退分块/滑出。末仍3781/5000土点为负孔压。当前只进行保存状态的自由面、压力/AS—加速度—Darcy分项审查，未归因于某项已证实bug；另两组仍锁定，无新solver/half/PRE。图和数据见`figures/collapse_psi0_r5`，结论见`tests/notes/upl_c08_r5_science_review_r1.md`、`upl_c08_r5_psi0_paper_review_r1.md`；终态审计见`tests/logs/upl_c08_formal_psi0_r5_r1.terminal_audit.json`。原终态通知已投递一次，不重新布防。

后续离线18点分解已完成：所选邻域C条件数1.004–2.682；负峰5809的直接扩散恢复负压，但pressure→raw-Ace→Darcy通道可翻向，AS谱响应只部分缓和。没有据此证明完整因果或修改方程。完整结果及分项审查已验证保存本地/远端`190a2c3f82af1e656e0bb249303268409b01e054`。更清楚的有符号对数压力图在`tests/figures/upl_c08_r5_pressure_fields_r1.png`，对应原CSV不变。

**阶段观测器已通过 GPU Debug 40 更新和 Release 0.03 s 实现回归。** Debug 内存检查零错误/零泄漏；6805 IDs 的22数组、实际时间载荷及signed clock均与保留同配置对照逐byte相同，Release对根r5前三帧也完全一致。Release 4503条阶段记录的更新、排水和RHS分项检查通过；原初始化额外PONDING保留。原生读取器各仅执行一次，首次Registry预检的零读取失败单独保留并用r2入口修复，未重跑solver。详见`tests/notes/upl_c08_stage_trace_smoke_result_r1.md`及原run/native_r2/review/trace.check记录。

三份隔离构建及原owner76072的真实退出均已核验，默认CPU Debug宏关闭、GPU Debug/Release宏启用；程序、r2 PRE和runtime_r5保护未变。原构建owner只通知过一次，不重新布防。

源码只增加默认undef的`C08_STAGE_TRACE`三个ID日志，未改物理表达式或替换runtime_r5。短窗通过不证明压力脉冲或物理精度通过。

**已单独准入并启动0.66 s阶段观测窗。** `upl_c08_stage_trace_window_GPU_r1`：原owner72580→实际GPU solver77844，创建时间/exe/argv/parent已核对，RTX3050、dt2.5 us、264000新更新、66个计划保存帧。输入只改测试窗TimeMax/TimeOut，复用原r2 GPU PRE，不重算10 s；0.60–0.66 s逐步记录3个原ID。新66帧读取器编译/link真实退出均0，原22数组/6805点数值检查不变，但还未读取本次活动输出。短回归本地/远端节点`f4e68b5`，窗口准备节点`73d8290`。当前只运行这一个窗；终态由direct owner单次同线程通知，再独立审查native/CSV，不自动解码或新求解。其他ψ、half、新PRE和正式长程未准入。

准入依据：保留浅床点的0.6 s候选正常完成且60帧原生门通过。`upl_c08_bedkeep_window_GPU_r1`实际owner58076→GPU solver22148，三个真实退出均0，耗时1584.609 s，末native=10.600000000564705 s。仅一次6805点/22数组解码；全窗无穿底，最低土粒z=.0130940694 m，最初3帧完整22/time/signed记录与已通过短窗逐byte一致。τ=.53最大速度从旧AS1的5.914994降为1.710602 m/s；τ=.6速度RMS回落至.495537 m/s。四种solver构建全部通过，完整窗口证据已保存本地/远端`c55852d93af3b0100c2acb90d5c51b06d2c775b9`。

仍有τ=.34近床ID7013的−115985 Pa负压脉冲和末上部负压区域，尚无论文精度/物理验收。根只准入一个新ψ0完整3 s诊断，不自动启动另两组；决定、完整4PNG/7CSV及局限见`tests/notes/upl_c08_bedkeep_window_result_r1.md`、`tests/logs/upl_c08_bedkeep_window_decision_r1.json`。新r5入口/runtime准备并检查前不得把旧r4当成该候选。

本轮只复用原r2认证PRE，不重算10 s。`keep_bed_overlap=true`在撤墙事件保留原ID 1800/1852/1904/1956/2008作为NoSlip浅床，其余255个右墙点退休，活动6805=1805固定+5000土粒。AS ε=.2/exp2.55、NoPen固定平面、dt2.5 us及原数值门不变；ReactionClosed=false。Predictor投影后的半步状态会反馈本步Corrector，但额外接触冲量没有同阶段Darcy闭合，不能概括为完全没有本步水力反馈。

新CPU Debug、GPU Debug/Release构建通过；CPU/GPU各40更新/1帧6805点原生检查通过，GPU memcheck 0错误/0泄漏，跨后端pRMS=.001723329 Pa、XYZmax=1.252068e−9 mm。新选项关闭的3帧对原AS开启短窗，全部22数组、layout、time及signed clocks整文件逐byte相同。开启后0.03 s/3帧原生门通过：末帧最大速度.136565（旧.191152）m/s、最大κ=.0225326（旧.0410586）、最小z=.0199834（旧.0174043）m；是边界算子改变的描述性收益，不套用half误差或理论精度结论。审查见`tests/figures/upl_c08_bedkeep_short_review_r1_*`，启动前准入见`tests/logs/upl_c08_bedkeep_window_GPU_r1.admission.json`。根目录runtime/XML/BAT均未替换。

以下保留此前AS＋固定平面的实现记录：沿用AS既有ε=.2/exp2.55、dt2.5 us和原r2 GPU认证PRE；只放行严格handoff范围内的组合，并补时步拒绝分项日志。CPU/GPU各40更新、1帧原生22数组/6800IDs检查通过，GPU memcheck 0错误/0泄漏。跨后端pRMS=.001724343 Pa、材料XYZ最大差1.252068e−9 mm。AS关闭的新Release前2帧与保留固定平面54帧的实际共同前缀，完整22数组/time/signed clock逐byte一致。

AS开启的0.03 s短窗正常完成并通过3帧原生22数组/6800IDs/ledger/clock/signed/FS/接触门；最大保存速度.191152 m/s、最小z=.0174043 m，无穿左墙/底面。四种配置构建全部通过。

**0.6 s AS组合窗口`upl_c08_asplane_window_GPU_r1`已失败，不准入正式三组。** 原owner74200→solver80168身份一致，Popen/Win32/solver均exit1，无所有权错误，必要输入/程序/PRE stat均未变。耗时1318.422 s；最后原样console为`Part_0052     10.530000       4212000     4000    2518.45  08-11-2026 05:21:28`，53帧原PART及60行启动前计划全部保留。53帧已由独立partial适配器一次性解码，原22数组/6800IDs/clock/ledger/FS/平面门通过，末native时刻10.530000000542486 s；这不改变solver失败结论。

首因是`DynamicPoreWall` stage0、sorted_slot564、native828，真实报告的力阶段step_start=10.532042500543135、step4212817，B=(4.42,0,−.06)、normal=(0,0,.119999997)，要求有限饱和一阶镜像拟合；不是时步拒绝。此阶段报告不是最后保存native状态，不捏造未保存故障数据。53帧图CSV见`upl_c08_asplane_partial_review_r1_*`：τ=.49时AS使负孔压极值由−973054.5降至−50429.8 Pa，但τ=.53土点7014仍达−168014.3 Pa、5.915 m/s。局部828现有nearest重试在最后保存态det=.27498，不能据未保存的错误盲加MLS重试。另已确认撤墙移除了5个浅床原点、留下.24 m支撑缺口；当前只修该明确几何问题。原dt/半径/det/饱和门不改，不增加half或重跑10 s。审计见`tests/logs/upl_c08_asplane_failure_audit_r1.json`；旧终态通知仅投递过一次，不重挂。

CPU短测实际exit0，原owner仅因Run.csv配置说明中未转义的AS分号而后检失败；原failed记录/CSV未改，已用独立offline adoption重新核全部原post门，随后只解码一次。未来入口r2仅修解析与实际日志等号格式，不改数值门或求解器。相关记录以`upl_c08_asplane_*`、`upl_c08_as_plane_native_r2*`及`upl_c08_as_short_review_r1*`为标签。

**r4入口暂缓继续计算，不能将其余两组当作已准入。** 新固定平面接触候选正在`tests`独立验证，未替换`runtime_r4`或原正式XML/BAT。四种构建、host组件17点/两反例、CPU/GPU Debug 2 ms实际接收及native均通过；GPU memcheck为0错误/0泄漏。两帧跨后端pRMS最大差.00428253 Pa，各材料XYZ最大差1.91257e−7 mm。NoPen关闭3帧对旧关闭11帧中的真实共有前缀，完整22数组/time/signed clock逐byte一致。

AS关闭的GPU Release候选`upl_c08_plane_on_GPU_r1`已失败退出，目标0.6 s/60帧未完成。实际solver PID77916、parent/owner81040、argv/创建身份一致；Popen/Win32均exit1，ownership_errors为空，30项输入/程序/runtime/PRE stat均未变。最后原样PART行为`Part_0053     10.540000       4216000     4000    2425.38  08-11-2026 03:47:15`。54个原始PART已独立partial解码一次，全部原生门通过，末native时刻10.54000000054566；所有保存帧未穿底，最小z=+7.1525574e−9 m。0.49 s内部ID4808出现−973054.5 Pa，不能据几何改善验收。完整图CSV和两项条件压力算子诊断已保存到本地/远端`4688bd1b0890559f67494127cb770b42d9ac48a8`；原始BI4及程序归档原位保护。

本次首因不是旧MLS错误，而是`DtVariable`在step4218523拒绝`current=2.5e-06 bound=2.49899e-06 DtMin=1e-08`。旧日志不能区分力/波速黏性/扩散/渗透率梯度分项，不从未保存故障点推断原因。冻结几何诊断未见所选矩阵近奇异，但压力—加速度—Darcy耦合响应不能只看直接扩散项；详见`tests/notes/upl_c08_plane_result_r1.md`。原dt/墙拟合阈值和必要稳定门未放宽、不加half链。此旧完成通知已真实投递exit0，不重挂。

原启动前记录仍见`tests/logs/upl_c08_plane_window_admission_r1.json`，真实start/call/run/status均保留。首次调用在任何GenCase/solver前因准入记录文件名撞fresh保护而拒绝；保留记录改用非冲突名后才启动这一次真实求解，见`upl_c08_plane_window_launch_guard_r1.json`。

诊断checkpoint本地/远端为`4262eb5c0633a449c0f7fc8c83878b91622332aa`。新接触代码仍为受限候选，`FixedPlaneStageProjectionReleaseOnly`、`ReactionClosed=false`；正式三组尚未准入。

**ψ0 r4完整GPU接收计算失败，尚未完成3 s塌陷。** 原owner PID70440→根BAT/cmd PID78608→solver PID77788均已结束，GenCase exit0、solver exit1、根BAT exit1。输入/程序的106项冻结stat未改变，未重复求解、未调用正式后处理。ψ=+2.5°和ψ=−5°尚未启动。原始start/call/run/status见 `tests/logs/upl_c08_formal_psi0_r4_r1.*`，唯一完成通知已投递，不再布防。

最后原样PART行为 `Part_0042     10.430000       4172000     4000    2355.02  08-11-2026 04:21:21`；43帧真实native末时刻10.430000000510745 s。错误为dynamic wall stage0、native823，报告step_start=10.43789250051325、step=4175157，要求有效饱和一阶镜像拟合。此未保存力阶段时刻与最后保存状态分开记录，不虚构未保存的状态。实际GPU为RTX3050，耗时约1060.6 s。

失败输出已独立只读解码一次，43帧、6800个原生ID及22数组的原安全门通过；前15帧对已封存NoPen短窗全部typed记录及signed clock逐字节相同，见 `tests/logs/upl_c08_r4_partial_r1.check.json`。这不是正常完成或物理通过。后续保存帧再次穿底，最小z约−25.0 mm；正在审查接触积分和墙支撑，不能将0.15 s收益外推为全程有效。最新运行记录checkpoint为本地/远端`59dcecce792cfd4ad3ec941cca797430beb3a94f`。

原完整ψ0 r3 GPU失败及其out原样保留，最后保存总时刻10.11 s；已定位state墙点791并观察到土点7010穿底。人工应力短试也失败，约推迟7.25 ms。既有NoPen开启/AS关闭的0.15 s GPU诊断已完成，15帧原生安全门通过、保存帧未见穿底/左墙；该短窗结论见 `tests/notes/upl_c08_nopen_result_r1.md`，不替代正在运行的完整3 s审查。

人工应力结论与图CSV见 `tests/notes/upl_c08_as_short_review_r1.md`。墙应力放大主要来自侧向稀薄支撑的外推，见 `tests/notes/upl_c08_wall_stress_decompose_r1.md`。本轮r4采用既有NoPen法向速度/位移的受限分步投影；Run.out明确 `No Penetration=True`、`ArtificialStress="None"` 和正式policy `LegacyOperatorSplitReleaseOnly`。投影约束反力未回馈同一步Darcy，`ReactionClosed=false`；不据正常退出声称反力闭合接触或论文精度验收。

失败运行使用根目录r4正式模板及`support/runtime_r4`，未进入r4后处理；不能用这些入口重跑同名结果。旧r3/r4输入、runtime、失败out及README保留；更早r1/r2根入口的可恢复归档和历史runtime/ZIP/manifest也保留。

服务器r2 GPU 10 s PRE已回传本机。实际Run.out确认本次加载原 `CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4`，源为legacy MR1 ElasticV1，实际时刻10.000000000374257、completed_step=4000000。随后只撤右墙260个样本，damping/Shepard关闭，FreeSeepage保持开启；源数据未改名或重算。三个GPU r4入口均固定该源；CPU入口固定自己的r3 CPU源，当前不存在即拒绝，不能将GPU源当作CPU证据。已有r4 out也拒绝覆盖。

当前r4接收启动器接入完整双击流程：求解前检查Python 3及numpy/matplotlib和runtime中的C08Native/PartVTK；优先D:/anaconda3/python.exe，否则PATH的python，不自动安装。仅接收正常退出才执行native→PartFluid→PartBound→PNG/CSV；本次失败未执行这些步骤。没有r4 PRELOAD入口，不重跑既有10 s源。

原入口加`--postprocess`只处理已完成输出，绝不GenCase或求解；`--unattended`可与它任意顺序并用。已完成且匹配的后处理可复用，失败或未绑定的部分结果不覆盖。回传r2 PRE的Fluid/Bound各1001帧已完成，不需要重新认领或导出。PartFluid/PartBound分别保存，预载为5000/2060，撤墙后接收为5000/1800；不生成PartAll。官方VTK显示坐标float，原BI4精度保留，κ不是完整塑性应变张量。

现有LianCollapse_upl_win64_r3.zip及其manifest/SHA仍是更新前历史快照，未包含本次入口/后处理更新，不以旧清单证明当前文件。使用新流程需同步当前脚本及所需runtime工具，并安装Python依赖；无须重编物理程序。

已通过四种构建、CPU/GPU源与接收短窗的全部22数组及带符号时钟精确连续性、旧默认回归、三个材料短承接、塑性源拒绝及新路径解压/四份GenCase输入检查。源码及说明见tests/notes/upl_preload_handoff_root_r1.md。

10 s源的正常完成已观测；三组完整塌陷、论文精度及预载平衡的物理验收仍需实际数据。通用塑性/HG/任意 PART 重启仍不在本次范围内。所有旧包、程序和原始结果均保留。

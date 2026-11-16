# C04 Release128：独立唯一native与同后端/跨后端审查作者稿

尚未执行。新增同名support Python和本文；无solver、build、VTK、hash/Git、
half/reference/peak或自动下一任务。只支持独立实际Release启动128的A/B/C。

两phase分别root准入：`native`唯一调用既有C04原r1 reader GPU；`review`
仅消费成功唯一读取，不重复。tag严格为
`upl_tpi_cryer_gpu_Release_[ABC]_startup128_rN`；输出`<tag>_native_r1`，
分开收据`<tag>.native_r1.json`与`<tag>.native_review_r1.json`。
既有/活动/partial读取器或任何既有新收据均保护，不覆盖重试。

admission stage为`upl_tpi_cryer_gpu_release_native_r1.PHASE_admission`，
passed=true、精确tag，native需one_native_read_only=true，review需
offline_only=true。B/C review另需`cpu_reference_review`完整stat entry，
指向真正相应scheme的passed CPU128 review，不自动猜测参考或启动CPU。

## 身份、真实源与原native门

绑定actualrun/start/call、真正direct GPU target的Popen/Win32双出口、
PID/creation/exe/argv/parent、实际UPL_TPI_GPU_R1、passed full111 Release
程序/runtime及r2source。DebugB2真实memcheck/16fixture/native/formula
review为已完成前置，不能仅信Debug solver0或从build推断device执行。
原job root_admission本身明确列消费，不删除metadata绑定来绕preflight。

原5列clock，initial与completed128/saved127/end2^-13；实际dt2^-20按
scalar+=dt核对。原C04 r1 reader可直接读这2帧，保持全部37181IDs/
8fixed/37173soil/22typed、3D非周期geometry、原radius.0525、有限/弹性、
P0/float excess、fixed marker、J/n/V/rho/k、FS和signed necessary-step门。
非初始signed interval非空且<=1e-14，初始signed值原样保留。

全部样本仍pre-drain，post-open帧/receiver数为0，不是排水后验收。
原物理程序的raw load/separation/natural/pore guards不变；保存J质量×
LoadAce只作proxy，不能声称另行重算/证明原力阶段.001预算。reader
验证22typed但仅导出common26，不能升级成全raw22 bit证明。

## A：真旧GPU128默认路径回归

A必须完全无private policy/csv/summary。对真实旧
`upl_cryer_freebody_smoke128_GPU_r1_native`的common26、native_ids.csv、
整个clock28（包括signed和初始值）逐byte完全相同。原控制solver/native
实际call须exit0；不追认不存在的独立旧run/start。这里是同后端，
FSNormal也不屏蔽。若出现差异保留失败并诊断，不用CPU或新B替代旧A。

## B/C：精确压力历史及真正同scheme CPU128

复用已审Debug native作者中的纯bits/f32_FTZ数学，不调用其Debug
context或解码。绑定实际C04cu/h和Release原NVCC flags：use_fast_math、
无-G、无FTZ/fmad关闭；压力源固定ddiv_rn/dadd_rn/double2float_rn。
输入float扩double与RN转float按signed FTZ精确复现，无ULP/绝对容差。
原J corrector允许其真实编译规则的两种精确非fused/fused算序，不改变dt。

逐2帧74346真实soil行：B α.5/C α0、β0、cold ID-ownedhistory、源step127、
实际source/save clocks、half/q/raw/final、全部S/R row与保存p/J对应；
每非初始S必须正，不masked/regularized。全128生命周期33307008 core7
bits、128commit/endpoint、HG0checks0；只有保存态逐材料导出，
不声称每个unsaved history已经独立观察。

同scheme CPU reference必须是真正passed
`upl_tpi_cryer_cpu_DebugCPU_[B/C]_startup128_rN`及其唯一native读取。
initial材料IDs/XYZ/初始V表完全相同，2个实际time/Step/dt配对，不插值。
每帧全37173土粒孔压RMS<=5Pa，固定材料XYZ位移差最大<=.005mm。
另外描述已保存骨架有效应力六分量的Frobenius RMS和J差，不额外增加应力阈值；总应力需要另按 sigma_total=sigma_effective-pI 计算，不能把此六分量直接标成总应力。

FSNormal只保各自native finite检查，不设跨后端bit门。两份signed
诊断均完整保留并各守原门，不要求浮点后端间dterror byte相同。
新B/C之间或相对finite-Kw A不是该跨后端同scheme误差，也不套这项5Pa门。

任何失败保留真实raw/partial/首因；完成solver后的检查错误仅修新离线
分析，不重跑solver或成功解码。即使全部通过，也只是128步实施资格，
不是峰值、完整3D物理、一般边界或restart验收，无自动更长窗。

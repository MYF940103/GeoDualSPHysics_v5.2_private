# C04 GPU Release128：A/B/C各独立单job运行作者稿

尚未执行。只新增同名support Python和本文；根线程完整审阅并分别准入一次
才允许运行所选一个job。不是A→B→C自动链，不调用help/native/build/VTK、
不启PRE/half/峰窗/长程，不发通知，不做Git或hash。

## 必须先有真正DebugB2资格

硬前置收据：`logs/upl_tpi_cryer_gpu_Debug_B_debug2steps_r1.native_review_r1.json`，
stage=`upl_tpi_cryer_gpu_debug2_native_r1.review`，必须实际passed并保持消费stat。
本文不把计划写成既成事实，执行时读取实际最终收据。需原生completion为
GPU、2updates/2frames、end2^-19、22数组/37181IDs，以及74346侧车行、37173
末态公式检查、520422 core7检查、HG0、ULP容差新增0；绑定其真实一次native
read与该审查root admission。其Debug memcheck/16device fixtures由此完成的
资格链提供，Release本次不再启动memcheck或额外Debug控制。

还必须有实际passed `logs/upl_tpi_cryer_gpu_Release_r1.build.json`：同一
`upl_tpi_cryer_gpu_r2.prepare.json`，97CL/14CUDA全111新对象、旧对象复用0、
真实GEO Release主程序和4项runtime；不替用Debug程序或旧Release对象。

## 固定输入与真实128步计划

复用原 `upl_cryer_freebody_short_r1_seed` XML+BI4，引用真实旧GPU128 call
核其seed与 `-gpu -stable` 来源。不重跑GenCase，不改正式XML，不从PART重启。
原三维非周期sphere、dt2^-20、Wendland、37181=37173soil+8fixed、HG0/SPR0、
原材料/AV/阻尼/原始外载/应力率修正/必要时步门均不改。

每job实际命令仅 `-gpu -stable PREFIX FRESH_OUT -dirdataout data -svres
-nsteps:128`。不覆写TimeMax，不加mDBC或其它物理参数。原TimeOut2^-13，
通过128次真正binary64 `scalar +=dt` 生成五列计划：

- part0，time0，completed0，savedStep0。
- part1，time2^-13=.0001220703125，completed128，savedStep127。

末帧对应原普通输出目标，不误写为forced final。原ramp2^-8、drain2^-7均
尚未到达；没有event或post-drain样本，不用空掩码宣称排水已验证。

## 单job选择及通用owner

仅tag `upl_tpi_cryer_gpu_Release_A_startup128_rN`、`..._B_...`或`..._C_...`，
configuration=Release、scheme=A/B/C、window=startup128；每个需不同root准入。
环境仅通过原通用owner设置 `UPL_TPI_GPU_R1` 对应所选方案。A走原有限Kw
默认路径，B为α=.5/β0，C为α0/β0；不是同物理半步或5Pa跨模型等价。

复用已经C04 Debug2独立审过的 C02 `upl_tpi_gpu_run_r3.run_owned` 通用
owner，不调用它的C02 context/schedule/check_output/HG门。此次
memcheck_program=None，真正Popen目标就是solver：保留原CreateProcess
句柄、真实PID/creation/exe/argv/parent、Popen/Win32出口和target句柄出口。
不伪造内部退出，不通过旧LASTEXITCODE或仅Run.out文字判断。

启动前列出现有solver；只允许root精确绑定且实际stopped的暂停旧GPU，
活动/未知GPU拒绝，不停止/恢复/更换任何旧owner。CPU可并行。输出目录、
start/tool.start/call/run/status/log/clock等已有即保护，失败保留第一真实
错误与最后原始PART，不推断未保存时间或自动重跑。

## 实际输出检查与未覆盖范围

三组都核真实Pos-Cell GPU模式、正常出口、128updates、2原生帧、全部
37181/8数量、零排除、HG0无force summary。A必须无实际device fixture
且无 `UplTpiCryerGpuR1.policy.json/.csv/.summary.json`。其与保留原GPU128
的实际clock/Step及字段对照另行原生审核，runner不预先宣称任何raw22位证明。

B/C console需恰有一次实际16case source/role fixture marker；build不算
fixture通过。policy需真实方案/α/β/M0/ID-owned cold history；summary需
128commit/endpoint、33307008 core7 checks、HG snapshots0与实际end。helper
自身Finish仍要求原Pre/Cor/J各一次的完整生命周期，runner不伪造独立J原生
对照。原22typed arrays、全部IDs、P0/J/κ/FS/ledger/真实clock/signed以及
逐材料侧车公式审查都待独立唯一reader，不由exit0代替。

不得从两个保存态宣称输出了128步逐ID记录。native PorePressRate仍为旧
Kw/n缩放residual诊断，非B/C dp/dt。保留实际CUDA的RN/FTZ/FMA，不用禁
fast-math或放宽ULP/物理阈值来制造吻合；科学review另行准入。此窗口尚无
峰值、消散或1%理论精度资格，也不接公共XML或完整状态重启。

## root admission与产物

stage=`upl_tpi_cryer_gpu_release_run_r1.run_admission`，passed=true、
one_job_only=true；job包含精确tag/configuration/scheme/window，无memcheck
工具。required_passed_checks列根选择的真实已完成source/CPU/GPU资格。
inputs绑定script/note、两个实际C02 owner/stat helper、Python/psutil、
本prepare/build、3TU/diff/2helper、新program/runtime、真实旧GPU128 call、
原seedXML+BI4、DebugB2最终native review及其root admission/native read
receipt与其它声明前置checks。若Debug审查仍pending则不能启动本job。

新日志 `<tag>.start/.tool.start/.call/.run/.status/.log/.clock.csv`，输出
`tests/outputs/<tag>`。预留memcheck路径也不得已存在，但不会启动该工具。
clock由本job启动前独立生成并封存stat。成功仍只是
pending_unique_native_review；其它方案/下一物理窗需根独立决定，不自动执行。

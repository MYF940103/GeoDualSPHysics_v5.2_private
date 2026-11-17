# C02 私有 M0 Eq40 时步策略作者稿

尚未执行 prepare/build/solver/native。仅新增同标签 host header、source-prepare
Python 与本文，交根完整审阅后按 CPU/GPU 分别一次独立准入。公共 src、所有旧
源/程序/partial、已退役保守fullB及暂停C08不改；不启动full/half/C或通知器。

## 本次处理范围

原实际 B 压力采用 M0 one-defect 时间更新，但 DtVariable 仍用有限 Kw/n 的
undrained wave 必要界。此候选把时间算子和必要时步 policy 对齐，不改压力
方程/空间算子/AV/HG、物理 Kw、Rhydro 参考或真实 J/material 更新次数。

只有已经显式选 B/C，且私有环境 `UPL_TPI_M0_DT_R1=EQ40_RH1` 时生效。
A 首先短路，甚至不读取新 policy；B/C 无 policy 也保留旧路径。未知非空
policy 只在已开 B/C 时拒绝。没有公共 XML 接口或 R_h 自由调参。

本轮固定 R_h=1，采用 Eq40 形式的必要界：

`min(CFL*sqrt(h/AceMax), CFL*h/(max(c_skeleton,max,10*VelMax)+h*ViscDtMax), R_h*dt_hydro_explicit)`。

其中 `c_skeleton,i^2=(K+4G/3)/rho(J_i)`，真正原 finite-Kw 调用仍提供
`dt_hydro_explicit=PoreDtSafety*h^2/max((Kw/n_i)*k_i/gamma)`；其原 undrained
wave 只作独立诊断。原 constant-k/porosity/decay-domain检查也保留。不能把
这个必要界称为 one-defect 或一般耦合谱的充分稳定性证明。

原 force 归约、AV 速度差及 `cbar=Cs0` 原样；HG 的实际 `dt<=.2*tau`、
work/spin 等独立硬门原样，另记其 GetDtLimit 参考值，不把 HG 检查伪装成
Eq40 的新项。初态参考量级：骨架 wave+AV（零V/ViscDt）约100.542523us，
旧Kw wave约6.376503us、explicit hydro约47.660318us；不是未知当前min。

## 窄新网格与 bounded scope

保留真实 ramp/drainage tD=.0100002288818359375 s，只接受固定
`dt=tD/1000=1.0000228881835938e-5 s` 或 `dt=tD/500=2.0000457763671876e-5 s`。
首轮根选前者；本资产不生成输入或自动运行第二步长/C。HydroMechDrainageFixedGrid
的原网格检查不放宽，物理 tD 不为整数10us擅自改动。新的 source-clock
preopen/postopen 应随实际步数1000/500及下一更新审查，不沿用1600字面值。

仅 policy 分支放行 TimeMax<=2s。无policy时 CPU 原<=.15、GPU 原<=.15或
旧唯一full2Tv准入条件均原样；新policy不能借此再跑完整2Tv。每个新job必须
fresh/cold history；不支持 variable-dt、PART history restart 或中途切换policy。
新计划须独立 scalar+=新dt，不缩放旧A1682表或用n*dt替代真实保存时间。

## 新共享 host-only helper

`support/upl_tpi_m0_dt_r2.h` 是新增独立 namespace/free API，只含标准C++14
host逻辑；若被 CUDA 编译实际包含则 #error。没有改旧类布局、vtable、公共
class header 或原 device structures/inline predicates。

`Enabled`、`AllowedDt`、`Init/Record/Saved/Finish` 提供固定policy和低开销
三phase计数/保存interval诊断。不是每ID/每update写大CSV：每真实原生保存
只写一行，字段记录interval与total Pre/Cor/Endpoint调用数、force/skeleton
wave+AV/hydro必要界min、legacyKw wave与HG参考min、selected bound min及
`max(locked_dt-selected_bound)`。总min/计数在interval reset后继续保留。

三个phase来自此限定Symplectic真实调用，不是从forcecalls猜测：CPU/GPU
ComputeStep_Sym分别在 predictor调用DtVariable(false)、corrector调用
DtVariable(true)，既有额外endpoint再调用DtVariable(false)。根据 final与
真实 EndpointActive 分辨；Record严格检查0/1/2顺序、同source step/time和
固定dt，每完整步各一次，64位total。此模式不接受其它积分器/额外Dt调用。

Saved紧跟原压力Saved和原JSph::SaveData之后，因此与原生interval边界相同。
初始interval独立标empty，原native初始dterror可能为0或旧初始诊断，绝不
重写。非初始interval应与原 `JDsFixedDt::max(fixed-bound)` signed值按真实
表达式核对，阈值仍<=1e-14且不得empty；不再伪称这个bound含旧Kw wave。
empty行的 DBL_MAX/-DBL_MAX 是显式未采样sentinel，不是物理极值或原生
dterror；reader不得拿它们作范围/误差统计，也不得借此删掉原生初始诊断。
Finish在最后Saved后仍从独立total封summary，最后interval清空不丢总数据。

新产物为 `UplTpiM0DtR1.policy.json/.csv/.summary.json`。原压力侧车schema
和原22原生数组不变；既有 PorePressRate 仍是legacy Kw/n residual诊断，
不是B/C dp/dt。物理、理论、峰值、full、效率及A0ULP资格仍待实际测试。

## 源准备与 exact diff

脚本：`support/upl_tpi_m0_dt_r2_prepare.py`。
一次只 `--backend CPU` 或 `--backend GPU`，必须另带
`--execution-authorized --admission ROOT_JSON`；不自动准备另一后端或构建。

CPU基座：passed `upl_tpi_cpu_r1.prepare.json` 的flat266成员及真实
`upl_tpi_cpu_release_link_r3.build.json` ancestry。新267成员；只改JSphCpu.cpp
和JSphCpuSingle.cpp，加新header；原CPU私有inline helper全文不变。

GPU基座：passed `upl_tpi_gpu_full2tv_r1.prepare.json` 的flat269成员及真实
`upl_tpi_gpu_full2tv_Release_r1.build.json` ancestry。新270成员；只改
JSphGpu.cpp、JSphGpuSingle.cpp与旧private h的IMPLEMENTATION host段。
后者只新增host include并扩私有Init的dt条件，前88行device/API前缀逐byte
验证不变；cuh、所有CU、public class headers和shared device结构完全原字节。

GPU用原 `ComputePorosityWaveSpeed2` 外签名取得骨架尺度：该次scale调用
`kw=0,khyd=0,maxdiffusion=NULL`。物理压力函数仍传真Kw，原trueKw scale
调用仍存在；不能直接调用仍传真Kw的GetPorosityStepWaveGpu来替代。
此方案不用改/重编CUDA算子。CPU在private DtVariable做同义 current-J loop，
复用原GetPorosityFeedbackStateCpu。新增host source需实际权威recipe构建；
保留对象与ODR闭包由builder独立审核，prepare不把它们宣称已编译通过。

新树 `tests/outputs/upl_tpi_m0_dt_{CPU,GPU}_r2_source`，收据
`tests/logs/upl_tpi_m0_dt_{CPU,GPU}_r2.prepare.json`。准备会写新source_diff.json，
逐改文件保留完整unified exact diff；未改成员逐byte复制核对，旧树不写。
没有旧SHA扫描、工具子进程、GenCase、native、求解、Git或queue。

准入stage=`upl_tpi_m0_dt_r2.prepare_admission`，passed=true、prepare_only=true、
backend=CPU/GPU；inputs绑定作者三文件、Python、所选passed base prepare/build
及其全部files的实际stat。输出给 base_prepare/base_build、base_source_entries
的original/pinned_snapshot、files、source_diff、changed_sources/headers和精确
两host recompile_sources。已有输出或receipt一律保护，失败另保留首因/partial，
不得重跑旧准备或覆盖失败。

后续应先做policy/helper组件与默认A原参数实际0ULP回归，再根逐job准入新固定
dt的B窄窗CPU/GPU、原生22/ledger/IDs/BC/HG与原精度门；只在必要证据通过后
考虑2s。任何新dt/profile均不能未经审查把旧reader的CandidateDt/DrainStep硬值
直接套过来，也不据正常出口自动发包或恢复已退役fullB。

## r1 编译首因与 r2 最小修复

原r1 DebugCPU实际CL出口2，因基类JSphCpu没有派生JSphCpuSingle的HourglassCpu成员；GPU同样是派生持有。原r1 source/失败build/call/log全部保留。r2只删除基础时步函数新增的HG对象诊断引用，传DBL_MAX并明确HG_limit_reference_available=false。每interval的HG reference列DBL_MAX是不可观测sentinel，绝非实际HG界；不能纳入物理极值。原派生积分器的HG刚性/更新/缓存/spin安全门与Run.out摘要原样，不削弱阈值。selected force/skeleton/hydro界、物理Kw、时间层、压力算术和A路径不变。

namespace/header/新产物stage升r2以区分构建，侧车前缀仍为UplTpiM0DtR1（保持schema），私有环境名UPL_TPI_M0_DT_R1及EQ40_RH1值维持不变。新prepare输出树与收据为r2，旧r1不覆盖。最初未消费的r2.prepare_admission.json因准备脚本输出路径笔误在执行前被取代；只使用新prepare_admission_r2.json，不运行旧准入。

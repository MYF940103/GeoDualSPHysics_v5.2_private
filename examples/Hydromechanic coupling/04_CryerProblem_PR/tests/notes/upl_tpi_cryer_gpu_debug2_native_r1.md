# C04 GPU DebugB2：两阶段独立 native/read-review 作者稿

尚未执行。只新增同名 Python 和本文，不构建新reader，不solver/VTK/hash/
Git、长窗、half或自动后续。仅适用已actualpassed的C04 DebugB2单job。

独立阶段：`--phase native`复用原C04
`upl_cryer_public_native_DebugCPU_r1/reader.exe --read GPU DATA PLAN FRESHOUT`，
输出`<tag>_native_r1`和`<tag>.native_r1.json`；另一次root准入的
`--phase review`仅消费已成功完整解码，写`<tag>.native_review_r1.json`。
两phase不串行自动触发，reader/call/partial已存在或对应reader正在活动时
不重解码。任何receipt已存在都保护，不覆盖/自动换标签。

stage=`upl_tpi_cryer_gpu_debug2_native_r1.PHASE_admission`、passed=true、
精确tag，native需one_native_read_only=true，review需offline_only=true。
inputs包含真正消费stat，特别是原job root_admission本身也须列入，避免
之前CPU只因漏绑定metadata导致的preflight假拒。不会为了通过删除该绑定。

## 真来源/原生安全

核实际run/start/call、工具/target真Win32出口、target creation/exe/argv、
实际GPU B环境、memcheck0 errors和16 device source-role fixture；绑定
实际full111 Debug程序、原r2 prepare和runtime，不依赖build来推断fixture。
同一实际program的全Debug构建和原compiler flags是新来源，不混旧native
输出作为当前物理结果。

原C04 reader已真实读取旧GPU/CPU128，支持任何合法2帧prefix计划，因此
2updates的initial及savedStep1可直接用，不修改旧loader或任何native。
保持37181=8fixed+37173soil、22typed arrays、原3D/非周期sphere、实际
dt2^-20、clock0/2^-19、全部IDs、P0/float excess、弹性κ0、固定标记、
J/n/V/rho/k ledger、半径.0525、有限FS/法向和signed dterror<=1e-14等
原门。非初始interval必须非空，初始signed值不掩盖、不改写。

本窗完全pre-drain，postopen帧/receiver检查数为0，不能叫排水后验收。
reader只验证22typed并导出common26/clock，不是全raw22逐bit比较；没有
将FSNormal跨后端bit误差列为新门。DebugB2只与CPU128共享initial，不能
宣称存在t=2dt的CPU求解真值；本稿不制造该reference或重跑CPU。

## 精确CUDA压力/历史审查

绑定真正编译的C04 helper.h/.cuh和build实际JSphGpu_ker.cu NVCC flags。
该source明确`__ddiv_rn`、`__dadd_rn`、`__double2float_rn`，实际flags保留
`-G -use_fast_math`而无FTZ关闭。故以RN双精度divide/add、输入float转
double时FTZ和RN转float后的有符号FTZ精确复现原策略；不加任何ULP或
绝对误差容差。此数学实现与C02已取真实PTX证据的同源码转换链一致，
没有冒称本稿调用了C04 cuobjdump或Debug与Release生成码逐字节一致。
若绑定source/flags改变，拒绝该模型，不默许新的舍入分支。

逐两帧74346行真实ID检查：原28列schema、cold initial、sourceStep1、
真正source/save clocks、α.5/β0、history prediction、实际half/q、全部
S/R double row、float raw/final与native保存p、Jfull对应。非drained row
S必须正；本窗三个drained标志全0，不屏蔽负压或替换任何材料行。

唯一原Jcorrector使用`Jn+(dt*Jhalf)*thetaHalf`。原CUDA保留默认fmad，
按先rounded product，后分开乘加或真正fused乘加的两个精确binary64
路径复现，以Fraction精确构造fused结果，不扩大ULP。endpoint θ不当J
积分源。summary必须2commit/endpoint、520422 core7 bits、HG checks0。
只有两真实保存态逐材料导出，不能说每个unsaved history独立观察过。

HG0无adapter或伪计数。此检查仅实施/内存/保存态生命期资格，不是压力
峰值/理论精度、独立half、完整固结、restart或正式物理验收。失败保留
真实partial/首因，只修新离线分析，不重跑已完成solver或解码。

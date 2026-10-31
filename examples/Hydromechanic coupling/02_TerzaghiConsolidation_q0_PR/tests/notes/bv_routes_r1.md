# CPU边界速度路由、矩阵与阶段审计

2026-11-01。仅说明当前实现、既有证据及本轮最小修复的边界，不代替制造场的最终执行收据，也不新增物理验收。行号是本次工作树的定位提示，长期身份以源码/程序/输入哈希和各轮不可变收据为准。此记录不重写历史清单，不把历史程序的通过状态自动赋给当前重链接程序。

## 1. 三套速度不是同一个物理对象

设土粒子速度为 `vi`，真实边界粒子速度为 `vb=Velrhopc[j].xyz`，运动学壁速为 `vw=MotionVelc[j]`。`BoundNormalc[j]`是从边界粒子到真实ghost的位移；单位法向为 `n`，`Pt=I−n⊗n`。ghost位于 `xj+BoundNormalc[j]`，墙平面通过 `xj+BoundNormalc[j]/2`。

| 对象/局部变量 | 来源 | 不是何物 |
| --- | --- | --- |
| 真实速度 `vb`、`dv_rhop=vi−vb` | 当前力阶段的 `Velrhopc`；固定墙保持真实零速 | 不以ghost速度覆盖真实壁面运动学 |
| 切向速度 `TangenVelc[j]`、`dv_visc` | 现有mDBC外推后作切向投影；有效NoSlip/FreeSlip时 `dv_visc=vi−TangenVelc[j]`，否则回落 `dv_rhop` | 不等于完整向量镜像速度；其法向分量已投影去除 |
| 导数速度 `BoundDerivativeVelc[j]`、`dv_rhop_deriv` | SPR的一阶MLS与本面反射；启用且有效时为 `vi−BoundDerivativeVelc[j]`，否则回落 `dv_rhop` | 力阶段临时scratch，不写真实速度，也不是新位移自由度 |

来源：`JSphCpu.cpp / Mdbc2TangenVel`（约2919行）、`InteractionMdbcCorrectionT2`（约3230行）、`ComputeBoundaryDerivativeVelocity`（1685–1730）、`InteractionForcesFluid`（2429–2446）。mDBC本身更新壁面ρ/σ及切向辅助量，不把外推速度写入壁面xyz；SPR也不改 `Velrhopc/MotionVelc`。

### 本面反射映射

用 `vg0` 表示现有mDBC的零阶速度外推，用 `vg` 表示SPR一阶MLS速度。对本阶段允许的固定墙，`vb=vw=0`；以下写成一般代数形式只是解释函数，**不是开放运动墙**。

| SlipMode | mDBC的切向辅助速度 | SPR导数辅助速度 |
| --- | --- | --- |
| Vel0 | 无NoSlip/FreeSlip切向替换，保留真实壁速 | `vb+[(vb−vg)·n]n`，保留真实壁速的切向部分；不是完整NoSlip |
| NoSlip | `Pt(2vw−vg0)` | `2vb−vg`，全部分量反射 |
| FreeSlip | `Pt(vg0)` | `vg+2[(vb−vg)·n]n`，切向延续、法向反射 |

旧水平Vel0另保留z分量的float转换、负号、fallback及signed-zero路径。其位兼容特例不能被解释为一般SPR只重构z。一般固定平面使用三分量与本面法向；每个mk须表示独立平面，不能用平均角点法向冒充多面。

无效mDBC2壁面按 `BoundModec==BMODE_MDBC2OFF` 回退真实壁速，不允许由另一套MLS重新激活。Fluid-Bound交互同时将其质量贡献归零并跳过孔压路径。依据 `JSphCpu.cpp:2369–2371、2439–2440、2451`；Vel0沿用其既有有效性判据。

## 2. 下游路由与矩阵：同速度不等于同算子

| 下游 | SPR关闭 | SPR开启且壁面有效 | 梯度/其他处理 |
| --- | --- | --- | --- |
| 连续方程/密度率ρ | `dv_rhop` | `dv_rhop_deriv` | 仍为raw核梯度；含 `rho_i/rho_j` 权重，不被G1自动校正 |
| 孔压压缩源，PairDivergence | `dv_visc` | `dv_rhop_deriv` | `PoreCompressionGradCorr`决定是否用接收点C；真排水receiver不演化该率 |
| 应变/自旋/弹性应力率 | `dv_visc` | `dv_rhop_deriv` | `SoilStressRateGradCorr`决定是否用C；随后分解strain/spin并计算本构率 |
| 人工/层流黏性、黏性步长估计 | `dv_visc` | 仍为 `dv_visc` | SPR不应直接改变同一冻结状态的黏性输入 |
| 应力内力、孔压反馈、围压 | 不使用这套导数镜像速度 | 同左 | 使用当前应力/孔压/加载值与原动量离散；不能因G1存在就称力学梯度也已校正 |
| Darcy项 | 当前孔压、孔压ghost及几何 | 同左 | 与SPR速度无关；可选symC只作用土–土Darcy，壁面仍用既有路径 |
| NoPen接触修正 | `vi−MotionVelc[j]` | 同左 | 另见第4节，不读取导数ghost作真实壁速 |

主要入口：`JSphCpu.cpp:2462–2477、2481–2501、2581–2602、2631–2639`。孔压率在独立路径写回（约2654–2656行）。SPR准入要求G1、孔压梯度校正及PairDivergence同时开启；`DensityRate`孔压源的兼容模式不能据此继承SPR准入。

一阶MLS矩阵A用于在ghost附近拟合字段，`InterpolateBoundaryGhostFieldT`可一次处理三个速度右端项；它与 `ComputeFreeSurfaceTracking/ComputeCorrMat` 提供的粒子处核矩逆C不是同一个矩阵。多面SPR仅在需要时移动**拟合中心**，再求回原ghost，不移动真实粒子或墙；标量孔压外推不启用这个速度专用recenter路径。

因此需要分别陈述三种一致性：边界速度映射是否正确、粒子导数是否再现仿射场、力与应变率是否负伴随。前两者通过不自动证明第三者；ρ仍raw而S/P用C，亦不应宣称S/P/R是同一空间算子。

## 3. Predictor/Corrector阶段

`JSphCpuSingle::Interaction_Forces`（约737–764行）按以下顺序执行：

1. 按 `MDBCCorrector || interstep!=SymCorrector` 决定是否重做mDBC；
2. 设置InterStep、准备/清零力和率的scratch；
3. 每个力阶段重新计算SPR导数速度；
4. 计算自由面/C、加载、排水压力覆盖，进入真实融合邻居环。

`ComputeStep_Sym`（约940–969行）先在tn状态求力，再推进predictor，分格后在半步状态求corrector力。默认 `MDBCCorrector=1` 时两阶段均更新mDBC；设0时半步可沿用tn的 `TangenVel/BoundMode/壁面ρσ`，而SPR仍从半步流体速度重建。这是现有可选时层差别，不可用“SPR每阶段刷新”掩盖，也不能把mDBC0的通过结果推广为与mDBC1等价。

新 `bv_mls_cpu_r1.cpp`只观察不同幅值的两个冻结字段与InterStep标记，不调用积分器，TimeStep/Nstep保持0；它不是实际半步轨迹或新的半步物理验收。其最终构建、初始化、MLS及consumer成败由root封存的新check/运行收据补充，此说明不预判。

## 4. NoPen、塑性及几何限制

`JSphCpu.cpp:2552–2573`从真实粒子速度与MotionVel累积NoPen修正；Symplectic corrector在应力已积分之后改写速度和位移（约4374–4385行），不会在同阶段重新计算ρ/p/σ率。该投影和SPR是两种不同操作，不能把NoPen投影造成的变形直接当作同阶段应变率已经重新一致计算。

现有NoPen按坐标分量处理，原倾斜墙的旋转一致性问题已被保留证据证实；SPR只允许轴对齐NoSlip/FreeSlip+NoPen，倾斜组合继续拒绝。依据 `JSphCpuSingle::ConfigDomain`（约224–227行）和下列历史说明。一般曲面、运动墙、塑性/软化、大转动、精确HG重启均不由这些短弹性制造场或脉动试验验收。

## 5. 本轮CPU最小应力率写回修复与DDT边界

当前CPU只将最终六个 `rsigma[p1] += rsigmap1` 移到 `if(shift||arp1||acep1||visc)` 之后（约2686–2691行），避免有效弹性/自旋率被不相关的加速度/连续方程写回条件吞掉。没有改变应力率公式、速度反射、载荷、C、积分或默认开关；具体真实复现、前后结果及当前程序回归以root最终check为准。

**dsigma合并块原位保留**（约2662–2668行）。GPU同样只在原outer guard及DDT/sentinel条件成立时合并扩散，随后无条件写六分量（`JSphGpu_ker.cu`约2122–2159行）。不能借此修复额外改变应力扩散的启用条件。

| DensityDT | 既有应力扩散/sentinel语义 |
| --- | --- |
| 0 | dsigma全零，不执行应力扩散 |
| 1 | Form1；遇DBC边界将xx置FLT_MAX，mDBC不由该规则禁用 |
| 2 | Form2含原重力静力修正；遇边界将xx置FLT_MAX，排除浮体邻居 |
| 3 | Form2仅非边界邻居，不由边界触发xx sentinel |

`xx==FLT_MAX`禁用整组六分量，不能逐分量继续写入应力率。P1浮体且DDT非0时也使用该标记。

另登记一个**未在本轮验收的既有差异**：CPU的fluid-fluid与fluid-bound为两个调用，各自重置局部dsigma并写回；GPU两类邻居共享局部dsigma。DDT1/2遇边界sentinel时，对先前fluid扩散项的影响可能不同。不要把本次六字段外移称作已修复此差异；需要独立冻结场和数值审查。本轮不扩大DDT适用范围。

## 6. 既有证据索引与待补覆盖

以下仅索引当时绑定的源码/程序，不宣称当前binary已经逐项重跑：

- 单面18变体（2D/3D、水平/旋转面、三SlipMode）、共享标量MLS、实际ct S/P/R与rawρ接线：`mdbc_vector_r1.md`、`../logs/mdbc_vector_review_r2.check.json`；旧Vel0及SPR关闭短窗见 `mdbc_vector_015_c/h.check.json`、`mdbc_vector_off01.check.json`。
- CPU静止凸多面及轴NoPen短脉动：`spr_planes_r1.md`、`../logs/spr_planes_review_r2.check.json`、`spr_planes_final_regression_r1.check.json`。原斜NoPen拒绝与伪法向修正在该说明独立登记。
- GPU多面/旧单面制造场、脉动半步、旧路径及支持范围拒绝：`spr_gpu_planes_r1.md`、`../logs/spr_gpu_delivery_r1.check.json`、`spr_gpu_scope_r1.check.json`。
- 混合mk侧FreeSlip/底NoSlip：case05 `tests/notes/lian_spr_mix_review_r1.md`、`tests/logs/lian_spr_mix_review_r1.check.json`、`lian_spr_mix_regression_r1.check.json`及 `lian_spr_half_review_r1.check.json`；不把统一单面试验冒称混合滑移证明。
- 3D edge/corner的NoSlip/FreeSlip，CPU/GPU与独立短半步：`spr_3d_review_r1.md`、`../logs/spr_3d_audit_r1.check.json`。是2 ms有限弹性检查，不是完整3D固结理论或一般边界验收。

本轮最小新增覆盖分两层：`bv_pair_cpu_r1.cpp`由root负责纯消费者实际ct写回边界；`bv_mls_cpu_r1.cpp`复用真实mDBC/MLS，补固定水平FreeSlip相容切向常量平移、3D绕法向刚体旋转以及mDBC0/1阶段观察，不重复旧NoSlip仿射剪切。零预应力旋转只检验strain/compression null及路由，不检验非零预应力Jaumann客观性。前置初始化或构建失败必须原位保留，不能取消准入guard或将未执行项写成通过。

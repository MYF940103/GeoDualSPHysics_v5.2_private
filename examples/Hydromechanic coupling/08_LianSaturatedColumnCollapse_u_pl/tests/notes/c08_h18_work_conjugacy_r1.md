# C08 H1.8：零推进离散功共轭与虚速度审计

本阶段仅作者新增`support/c08_h18_work_conjugacy_r1.cpp`、`support/c08_h18_work_conjugacy_r1_build.py`及本文；没有导入、执行、构建、求解、解码、VTK、Git或SHA扫描。源程序、PRE、正式输入、现有工具及旧失败均不修改。根完整审阅后分别决定一次build和一次组件调用；没有自动后续物理窗口。

旧pair-force工具只对两对材料点给出直接项与全邻域选项差，没有全5000材料的梯度、功共轭或虚速度检查。本工具复用其原样typed22/301读取、ID/cell恢复、J/n/V/rho/k ledger和不推进保护，仍只用AS.3/n2.55完整结果的Parts38/76/92/300（completed2076001/2152001/2184001/2600000）。不是将最新AV.2轨迹当作原AS03状态。每状态只有一次原`Interaction_Forces(INTERSTEP_SymCorrector)`，总计4次实际CPU force/Darcy调用，没有ASoff/AVoff时间窗或额外真实force。

## 冻结实现与算术

实际物理实现为`outputs/c08_preload_schema2_source_r1/full_source.zip`及已成功`logs/c08_h18_late_rhs_r1.build.json`绑定的86原DebugCPU对象、160归档头和原编译/链接配方。新builder仅编译一个entry，链接87对象；不改物理对象、Single、CUDA、类ABI或公共源。编译依赖检查禁止current public头泄入。新entry使用原`JSphCpu.cpp`的两个全局符号`GetStrainSpinRateTensor_sym`和`GetStressRateTensor_Elastic`，不是再写材料模型。

关键冻结源位置（原ZIP的`src/source/JSphCpu.cpp`）：

- 2245/2282：动量先将六分量有效应力取为float。2264–2275：位移、rr2及Wendland梯度为float；AS开启走`GetKernel_WabFac`。2315–2322：总应力与孔压合并后double乘Vj/rhoi，逐分量float提交。
- 2347–2366：AS用真实`ArtificialStressc`、`W(r)/W(dp)`及`powf`，double乘积后float提交。2549–2567：AV使用真实切向ghost速度差、float dot/mu/cs0及J导出的混合密度，单独减float提交。
- 2393–2410：物理/黏性/导数ghost速度路径分开。2553–2556：导数速度差先乘`-float(Vj)`，再float累加每行原梯度；2611–2620：每次soil/Bound调用分别应用C、构造应变/旋转率，再算应力率。2666–2671按调用顺序累加Rσ。704–708给C变换的确切double乘、float回写顺序。
- 2417–2441：θ另用`GetKernel_Fac`和double位置/体积累加（并保留`PoreCompressionGradCorr`选择），不能把它与AS动量的WabFac路径机械认作逐bit同一个数。2820–2826：先soil、后wall两次邻域调用。
- `JSphCpuSingle.cpp`695–749：实际重建墙、FS、AS后调用原force，再计算动态孔压率；重力没有加进Ace。2D的Ace.y最终置零。NoPenScratch只是本次force所生成的候选，不执行固定平面投影，也不把它当投影反力。

新工具按真实cell范围、support和inactive-wall规则独立遍历全部soil-soil与soil-wall有向邻居。总应力/AS/AV先保留double的逐对影子，并同时按上述原float提交/累加次序重建整行Ace。原float原梯度、C变换、调用原应力率函数及两组提交次序也独立重建。每soil导出实际与重建force/Rσ/θ、误差和预算及bit相等标志。要求误差不越过基于IEEE u、实际donor数和绝对项和的舍入预算；这是实现算术检查，不是新物理误差容限。bit标志是观察项，不暗改为新跨GPU等价门。

θ预算为`γ_double(32N+128) Σ|θij|`；force预算为`γ_float(12N+64) max_component Σ|aij|`，另有正常浮点下溢量级项。Rσ预算传播原梯度绝对项和、C一范数、弹性模量与应力旋转项上界。双精度功恒等式预算同时计入全局求和和有向pair算术，采用`γ_double(128*donors+128)`乘相关绝对功和；没有拟合数值常数、epsilon矩阵夹紧或物理门放宽。

## 离散功的准确含义

令`Ti=float(σeff_i)−p_i I`，`Vi=V0 Ji`，`rho_i=rho_w+(rho0−rho_w)/Ji`，`mi=Vi rho_i`，`gij`为原raw float核梯度。原总应力动量影子为

```
aσ_i = Σj Vj/rho_i (Ti+Tj) gij
Lraw_i = Σj Vj (vj−vi) ⊗ gij
LC_i = apply_rows(Ci,Lraw_i)
Pσ = Σi mi vi·aσ_i
Iraw = Σi Vi Ti:Lraw_i
IC = Σi Vi Ti:LC_i
ΓG1 = IC−Iraw
```

对完整soil-soil有向子算子，raw梯度反对称给`Pσ+Iraw≈0`。工具检查此double影子的算术闭合，并报告G1差`ΓG1`。`ΓG1≠0`说明这两个给定算子不直接互为离散伴随；**不单凭这一点断言代码错误、轨迹不稳定或修改C一定更准确**。储能、压力、塑性返回、时间推进及接触投影不在这个零步等式中，亦没有建立全耦合能量守恒定理。

墙只有soil接收动量方程。真实固定墙速度为0；导数使用原重建镜像速度`vder_j`。因此墙项不能套soil-soil零和恒等式。单独报告

```
port_wall = Σsoil_i,wall_j ViVj[vi·Tj gij + vder_j·Ti gij]
Pσ_wall + Iraw_wall − port_wall ≈ 0
```

另给使用真实wall速度0的`Iraw_physical`，逐wall保存真实/导数/黏性速度、应力、P/P0/J、slip和mode。该端口是镜像积分及支持的代数项，不是已闭合物理墙反力功；未保存的before/after投影状态不重建。

AS、AV、重力功单列，AS/AV为完整邻域literal double影子，不把原float整行四舍五入误认新物理分量。gravity只报告`Σmi vi·g`。混合惯性并非常质量：给`Σmi`、`mdot_proxy=rho_w ΣVi θi`和`.5 Σmdot_i |vi|²`，仅是当前u-pl/J ledger的条件性开系数项，不是实测质量通量或流体质量守恒。不得将遗漏的Darcy、压力储能、塑性、FS投影、墙支持或可变惯性功归为bug。

## 预先声明的soil-only虚速度

Part300实际速度小可能隐藏功差。工具捕获完整实际soil-soil有向stencil后，在不修改原数组、不再调用force的情况下，冻结真实C/V/T，计算4个代数probe：

1. 材料6767/6865两端分别`±0.5 m/s`沿当前连线，其余soil速度0。
2. 材料4953/4954，同上。
3. 健康参照：按原native ID字典序，选首个当前距离`[.9,1.1]dp`、两端nearest-soil均`>=.85dp`、两端距所有保留墙粒子均`>=2H`的邻接对；不按功、误差或期望结果选取。无此对则保留诊断失败，不能临时挑拟合对。
4. 全soil同向平移`u=(1,0,0)m/s`。

健康参照按此支撑/间距规则逐态选取，可能不是四个时刻的同一材料对；两疑似对始终固定ID。每probe重新累计全soil raw/corrected梯度、冻结应力虚功及raw恒等式，输出V加权`||u||`、`||sym Lraw||`、`||sym LC||`、raw/C散度范数和`||B u||/||u||`。这些是给定算子的灵敏度指标，不是完整特征值、最小奇异值、模态增长率或时间窗物理修复，Γ本身也不能证明zero-energy模态。虚墙拟合/导数不能由实际ghost值硬推，因此虚probe**只含soil-soil**，`walls_closed=0`；没有对虚运动调用墙重建或NoPen，不能据此评判完整wall算子。

## 输出与后续独立审阅

唯一新输出目录为`outputs/c08_h18_work_conjugacy_r1`；program为`outputs/c08_h18_work_conjugacy_r1_build/C08H18WorkConjugacyR1.exe`，build收据为同tag`.build.json`。

- `soil.csv`20000行：每状态全部5000材料的原C/Rσ/trace/θ/v/σ/rho/V/force，literal误差/预算及raw/C L。
- `groups.csv`40000行：每soil按soil/wall分组的stress/AS/AV功、梯度及墙端口。
- `walls.csv`7220行：4×1805真实重建的墙字段。
- `summary.csv`8行：4×soil/wall的raw闭合、G1差、AS/AV/重力与质量代理。
- `virtual.csv`16行：4状态×4预声明probe，全部soil-only。
- `completion.json`：实际force_calls=4、行数、原5000土体primary逐bit不变和最大literal误差；physical_steps/material_steps/new_OFF_windows=0，physical_acceptance=false。

soil primary不变检查为既有位置、速度/rho、六应力、κ、p/P0/J及其ledger、ID/墙角色、真实clock；θ/FS是原force合法生成的观察量，不谎称全部22数组在force前后相等。保护输入typed22/layout/clocks/completion/metadata、原PRE/seed/run/native-review及真实program/runtime的stat，无SHA重扫。失败保留原首因、partial及旧结果，不自动重试、求解或推进其他ψ。

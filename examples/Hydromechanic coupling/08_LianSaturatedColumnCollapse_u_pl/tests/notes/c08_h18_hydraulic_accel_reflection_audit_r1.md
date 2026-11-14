# C08 NoSlip速度与水力加速度镜像的只读审计

本记录仅整理冻结源码、既有制造测试与数学推导；不修改原算子、输入或数据，不运行新组件、求解器、读取器、构建或参数试验。当前Q规则不是已证实bug，以下候选也没有物理准入。不能仅因速度与加速度的ghost符号不同就盲目翻转切向加速度。

## 当前实际规则

审计归档为 `tests/outputs/c08_preload_schema2_source_r1/full_source.zip`。CPU `src/source/JSphCpu_mdbc.cpp:1173–1184` 的静止墙导数速度采用NoSlip full-image `v*=-v_mirror`，FreeSlip采用 `v*=Q v_mirror`。Q=I−2nnᵀ，是固定轴平面的几何反射。物理固定墙速度仍为零；AV tangent速度是另一条独立支路。

CPU同文件1238–1259的stage2对所有slip使用

\[
A_w^*=Q(A_m+g)-g,
\]

其中A是代码Ace、a_s=A+g才是总固体加速度。stage2唯一持久写是墙Ace，不改σ/p/J/θ/C/full/tangent速度。GPU归档 `JSphGpu_mdbc_ker.cuh:49–52,183–188` 用等价的normal-head写法：只加减g_n，因为Q保持g_t；不是另一个物理模型。

同阶段Darcy在CPU `JSphCpu.cpp:3174–3185,3228–3260` 实际先刷新墙Ace，再使用

\[
D_a=\sum_j V_j(A_j-A_i)\cdot(C_i\nabla W_{ij}).
\]

内部压力项是 `LP−gp·Lx+rho_w*Da`；自由渗出FS分支保留 `LP+rho_w*(Ai·Lx+Da)`；另有实际变k链项。不能把Da从这些项中孤立出来宣布整体正确或错误。固定平面NoPen的分步投影反力未证明反馈同阶段Darcy，`ReactionClosed=false`限制仍在。

## Q有明确的水力扩展理由

Darcy驱动写成

\[
h=\nabla p+\rho_w(a_s-g),\qquad q\propto-h.
\]

不可渗透只要求物理墙面 `n·h=0`，不唯一规定所有切向场在墙外的延拓。令 `p_e=p−rho_w*g_n·x`，当前scalar pressure-head采用even镜像，而总加速度按极向量几何镜像 `a_s*=Q a_s`。这样有

\[
\nabla p^*=Q\nabla p_{e,m}+\rho_wg_n,
\qquad h^*=Qh_m,
\]

因为Q g_t=g_t。这是一个刻意的无通量flux反射模型。ghost不是独立的物理材料点；它为导数速度、粘性和水力算子服务时可以采用不同扩展。该论证提供模型动机，不等于实际MLS/LP/Taylor/FS离散已经通过所有近墙精度和耦合稳定测试。

## 既有测试并非只测法向

`support/upl_noslip_cpu_component_r1.cpp:94,107–120` 明确赋予XYZ非零affine Ace，在x-normal墙上预期normal翻号、两个tangent分量保持even，对NoSlip同样如此。`notes/upl_noslip_cpu_component_r1.json` 的separation说明专门要求非零切向Ace能检测“误把NoSlip full速度符号用于Darcy Ace”。

已完成记录包括：

- `notes/upl_noslip_cpu_review_r1.json`：Wendland/Cubic共12条件、3072墙记录、1536 NoSlip记录，保留原roundoff预算；这是重构/实现验证。
- `notes/upl_noslip_gpu_review_r1.json`及`upl_noslip_gpu_component_r1.json`：12条件、24墙记录、36次stage调用，实际memcheck错误及泄漏为零；也明确NoSlip速度负号不能进入几何C或Darcy Ace。
- C08混合墙 `upl_ck2_free_wall_cpu_r1`/GPU对应测试使用垂向drive；它检验底面法向及侧面切向传播，但没有给底面NoSlip的 `a_t=A*x*z` cross项完整PDE精度证明。

这些测试证明当前Q意图和程序实现，不是全Darcy方程或真实collapse的精度验收。未找到已封存的NoSlip切向cross多项式完整RHS解析测试，不能把已有affine重构通过扩大成该项已验证。

## 速度的partial_t与物质加速度必须区分

在固定空间反射 `Rx` 上，NoSlip全odd速度延拓满足 `v^o(x,t)=−v(Rx,t)`，因此固定坐标的partial_t确实翻号。但总固体加速度是物质导数，不一般等于 `−a_m`。

设L=∇v、P_t=(I+Q)/2，则

\[
L^o=-LQ,\qquad
a^o=-\partial_t v+LQv
=-a+L(I+Q)v=-a+2LP_tv.
\]

只有镜像处切向v为零、该对流修正恰好为零，或v=0的瞬时制造场，才可简化全odd加速度。FreeSlip `v*=Qv(Rx)` 则物质导数严格协变为 `a*=Qa`。真实移动粒子上的MLS权重/拟合点变化还未由单个保存态完整观测，不能只对当前full-image值作时间导数就推导出完整材料加速度。

## 相互补充、可以证伪的制造场

以下仅为未来候选设计，不由本note启动。先取底面z=0、g=0、常J/k、瞬时v=0和θ=0；在远离其它墙/FS干扰的真实接收点，给定

\[
a=(Axz,0,Bz),\qquad \operatorname{div}a=Az+B.
\]

墙上a=0，因此符合静止NoSlip瞬时运动学。纯 `a_t=A*z` 的切向散度为零，不能辨识这里的cross误差。

第一种场可取 `p=p0+Px*x²+Pz*z²`，墙上∂np=0。NoSlip全odd加速度保持 `a_x=A*x*z` 多项式延拓，而当前Q使切向分量变成 `A*x*|z|`。在理想完整对称核/同体积下，Q的散度相当于 `A*kernel_average(|z|)+B`，相对物理点值多出 `A*(E|z+ξ|−z)`，近墙量级O(h)。这有辨识力，但要分别报告LP、Taylor、Da与完整RHS；不能只因Da更接近点值就选新边界。这个瞬时quadratic压力场也不能直接当作满足所有高阶初边值兼容条件的全程解析解。

第二种互补配平场取相同a，但令

\[
p=p0-\rho_wAz^3/6-\rho_wBz^2/2.
\]

在物理半空间，Δp=−rho_w(Az+B)，所以完整连续Darcy RHS为零，且墙上a=0、∂np=0。当前Q配合同一even压力延拓给出

\[
a_x^*=Ax|z|,\quad a_z^*=Bz,\quad
p^*=p0-\rho_wA|z|^3/6-\rho_wBz^2/2,
\]

在整个扩展域仍有 `Δp*+rho_w*div(a*)=0`。若只把加速度改为全odd、压力仍even，墙外会产生 `rho_w*A*(z−|z|)`假源；可能破坏原配平。因此这两个场应相互补充：分别检验单项近墙一致性和完整水力平衡。现有pair-C/Eta2/Taylor算子并非连续微分的机器精确版本，不能给第二个场虚构零截断误差预算或放宽旧门；应保留实际完整项和真实face flux的独立比较。

## 保存态上最低成本的条件敏感性

若只把NoSlip hydraulic Ace由Q改全odd、冻结全部soil Ace/C/p/J/k/FS，则

\[
\delta A_w=-(I+Q)(A_m+g)=-2P_ta_m.
\]

对当前水平底g_t=0，就是切向 `δA_w,t=−2*A_w,t`、normal不变。完整RHS的此项条件响应为

\[
\delta D_{a,i}=\sum_{w\in B_{NS}}V_w\delta A_w\cdot(C_i g_{iw}),
\qquad
\delta R_i={K_w\over n_i}{k_i\over\gamma_w}\rho_w\delta D_{a,i}.
\]

由于receiver Ai未变，该冻结干预不改变LP/pressure-Taylor、FS的receiver-Ace·Lx或变k链项。它可判断真实P29–31近床场对这种符号改变是否敏感，但只能命名为全odd候选的shadow响应；不是正确性或修复证明。真正机械物质导数候选还含 `2L P_t v` 及拟合几何时间依赖，当前数据未完整观察。

先辨明水力模型与完整离散，再决定是否值得新增实现；不能因shadow孔压较平滑、某一Da项较小或正常退出，就盲翻符号、丢掉负孔压、修改时步门、启动另一ψ或宣称问题已修复。所有旧结果与原认证PRE保持原样。

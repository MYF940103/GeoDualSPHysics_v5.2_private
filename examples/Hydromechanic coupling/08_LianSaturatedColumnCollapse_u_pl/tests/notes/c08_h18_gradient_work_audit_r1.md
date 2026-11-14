# C08 原核动量、G1 梯度及压力压缩项的虚功审计

本记录只整理数学与冻结源码审查；不修改源码、参数、原数据或已成功资产，不执行构建、组件、求解器、读取器、VTK 或 Git。它不是新物理验收，也未选定新的内力算子。目标是利用已保存的14态，先判断梯度非伴随通道是否值得继续定位，而不是预设它是团聚或孔压偏差的原因。

## 1. 实际代码范围与记号

审计对象是 `tests/outputs/c08_preload_schema2_source_r1/full_source.zip` 中的 `src/source/JSphCpu.cpp` 与 `JSphCpu_mdbc.cpp`，不是可能继续开发的工作树源码。前者当前动量支路在2313–2322行，速度差选择在2393–2410行，double θ逐对求值在2417–2440行，float体积/九梯度累加在2553–2556行，G1及弹性应力率在2611–2620行。`ApplyGradCorr` 在704–709行；弹性/Jaumann helper在1958–2023行。这里的行号属于上述归档。

令土粒子集合为 F，固定墙求积点集合为 B。当前 C08 为二维、单位出平面厚度；V 的单位是 m²，m 的单位是 kg/m，因此下述功率为 W/m。定义

\[
g_{ij}=\nabla_i W_{ij}=\mathrm{fac}_{ij}(x_i-x_j),\quad
V_i=V_0J_i,\quad m_i=\rho_{t,i}V_i,
\]

\[
S_i=\sigma^{\mathrm{eff}}_i,\qquad T_i=S_i-p_iI.
\]

应力采用代码中的拉应力为正约定。动量实际先把六个有效应力分量从保存的 double 转成 float，再参与总应力求和；压力也是原生 float。故与当前 force 求值对齐的审计应使用 `float32(S_native)` 再转 double 的 S，以及绝对原生 p；不能以 `p-P0` 代替 p。P0固定参考差不是该动量方程的压力，也不等于论文的塑性超孔压。使用原生 double 应力可作为另列的精度敏感性描述，但不能将其命名为当前力的真值。

下面首先推导相同支持集、同一核梯度与体积、冻结状态下的实数离散代数。实际源码还有 float体积、float核梯度、不同累计顺序及 float加速度提交，不能从实数恒等式直接宣称逐位守恒。

## 2. 土—土：原核内力与原梯度互为伴随

对一个土—土邻居对，当前总应力内力在实数离散代数下为

\[
F_{ij}^{0}=m_i a_{ij}^{\mathrm{stress}}
=V_iV_j(T_i+T_j)g_{ij},\qquad F_{ji}^{0}=-F_{ij}^{0}.
\]

此式只含总应力动量项，不含重力、人工应力 AS、人工粘性 AV、residual viscosity 或接触投影。定义同一土—土求积的原速度梯度与对称部分

\[
L_i^{0,F}=-\sum_{j\in F}V_j(v_i-v_j)\otimes g_{ij},\qquad
D_i^{0,F}=\operatorname{sym}L_i^{0,F}.
\]

若反向邻居存在且采用相同体积、核及状态，每个无序对只计一次，则

\[
\begin{aligned}
P_F^0
&=\sum_{i\in F}m_iv_i\cdot a_i^{\mathrm{stress},F}\\
&=\sum_{i<j}V_iV_j(v_i-v_j)\cdot(T_i+T_j)g_{ij}\\
&=-\sum_{i\in F}V_iT_i:D_i^{0,F}.
\end{aligned}
\]

对称应力只与梯度的对称部分作功。这个恒等式不要求粒子规则或梯度对线性场精确；它要求力与梯度确实使用同一个离散配对。它也不是完整热力学或弹塑性积分验收。

## 3. G1 与原核动量间的有限离散功差

当前 G1 对每个速度分量的梯度向量左乘 Ci，因此矩阵形式为

\[
L_i^{1,F}=L_i^{0,F}C_i^T
=-\sum_{j\in F}V_j(v_i-v_j)\otimes(C_i g_{ij}).
\]

如果动量仍是原核内力，而材料率使用 G1，则实数离散虚功差为

\[
\begin{aligned}
R_F^{\mathrm{ideal}}
&=P_F^0+\sum_iV_iT_i:D_i^{1,F}\\
&=\sum_iV_iT_i:(D_i^{1,F}-D_i^{0,F})\\
&=-\sum_{i<j}V_iV_j(v_i-v_j)\cdot
\{T_i(C_i-I)+T_j(C_j-I)\}g_{ij}.
\end{aligned}
\]

所以存在一般非零的非伴随通道，但它没有固定正负号。Ci=I、速度差全零、应力为零或上述收缩恰好全局抵消时它为零；只凭 J≈1、均匀应力、线性场修正精确或局部塑性历史，均不能单独断言它为零，也不能单凭它非零就认定张拉或能量注入根因。梯度校正本身可改善一致性；这里审计的是成套离散之间的关系。

对有效应力与压力必须分开记账：

\[
P_F^0=-\sum_iV_iS_i:D_i^{0,F}
+\sum_iV_ip_i\operatorname{tr}L_i^{0,F}.
\]

当前孔隙率/压缩源实际使用 double θ，而 G1 使用 float九梯度累计后再乘 Ci。两者连续表达相同，但实际体积舍入、核 Fac 参数、二次支持筛选及求和顺序不同。若采用实际 θ_i^F，则对应的条件性比较为

\[
\Delta W_F
=\sum_iV_iS_i:(D_i^{1,F}-D_i^{0,F})
-\sum_iV_ip_i(\theta_i^F-\operatorname{tr}L_i^{0,F}).
\]

不要把 `tr(Rsigma)/(3K)` 当作 θ 的定义或完整应变率替代品。原 helper 的 float刚度组合及 Jaumann 各分量抵消均保留；Rσ只是本次弹性客观应力率，不包含随后塑性返回/张拉修复导致的应力变化。

## 4. 墙：full-image 速度不是物理墙速度

物理固定墙速度为零，但导数使用拟合和反射得到的 full-image 速度 \(v_w^*\)。AV 的 tangent 速度是另一条支路，不能为了形式一致而任意替换。当前 NoSlip 的 ghost应力含外推，FreeSlip 含张量反射；详见归档 `JSphCpu_mdbc.cpp:1175–1186`。每个 receiver 没有独立、严格一一对应的镜像伙伴。

土节点上的墙应力力功与 G1 墙内功分别为

\[
P_B^0=\sum_{i\in F,w\in B}V_iV_w
v_i\cdot(T_i+T_w)g_{iw},
\]

\[
W_B^1=-\sum_{i,w}V_iV_w
(v_i-v_w^*)\cdot T_iC_i g_{iw}.
\]

因此

\[
R_B=P_B^0+W_B^1
=\sum_{i,w}V_iV_w
\{v_i\cdot(T_i+T_w)g_{iw}
-(v_i-v_w^*)\cdot T_iC_i g_{iw}\}.
\]

即使 Ci=I，仍有

\[
R_B\big|_{C=I}=\sum_{i,w}V_iV_w
\{v_i\cdot T_wg_{iw}+v_w^*\cdot T_i g_{iw}\}.
\]

这在理想匹配的镜像几何、速度、应力及完整求积关系下可以抵消；不能因物理墙速度为零就令所有离散墙功为零。边界牵引、镜像消元、外力反力和约束功必须一起说明。当前固定平面 NoPen 的分步投影反力没有证明反馈到同阶段 Darcy；观察到 stage2 hydraulic wall Ace 不能证明这个反力闭合。此问题与 G1 的 Ci 功差应分开记录。

## 5. 只用现有14态能计算什么

已有 `c08_h18_bed_gradient_probe_r1` 的 scope 是原AS03与 radial轨迹各 Part28–34，共14个真实保存态；本 note 不启动该组件，也不重新分析其未完成数据。后续根线程可仅消费已成功生成的 `gradient.csv`、`soil.csv` 与已解码 typed22；不需要新物理轨迹或新原生读取。

`gradient.csv` 给每个土ID的 fluid/bound 两pass九个 raw/corrected 梯度、fresh实际 θ、绝对 p、fresh FS及支持计数；`soil.csv` 给实际 V；typed22 的 Sigd=(xx,yy,zz)、Sigij=(xy,yz,xz)提供全部六应力。必须按实际case、part、completed_step、time和ID连接，不插值，不删除异常ID。保存的 prior-stage θ 不能替代本次 fresh CPU θ。

对每个 pass f=F/B，建议量名与公式如下，单位全部 W/m：

| 描述性量名 | 计算式 |
|---|---|
| `effective_gradient_work_raw_f` | \(\sum_iV_iS_i:D_i^{0,f}\) |
| `effective_gradient_work_corrected_f` | \(\sum_iV_iS_i:D_i^{1,f}\) |
| `effective_gradient_correction_work_delta_f` | \(\sum_iV_iS_i:(D_i^{1,f}-D_i^{0,f})\) |
| `pressure_gradient_correction_work_delta_f` | \(-\sum_iV_ip_i(\operatorname{tr}L_i^{1,f}-\operatorname{tr}L_i^{0,f})\) |
| `pressure_theta_gradient_work_gap_f` | \(\sum_iV_ip_i(\operatorname{tr}L_i^{1,f}-\theta_i^f)\) |
| `coupled_gradient_virtual_work_delta_f` | 上三项之和 |

双收缩应按真实分量顺序计算：

\[
S:\Delta D=S_{xx}\Delta L_{xx}+S_{yy}\Delta L_{yy}+S_{zz}\Delta L_{zz}
+S_{xy}(\Delta L_{xy}+\Delta L_{yx})
+S_{yz}(\Delta L_{yz}+\Delta L_{zy})
+S_{xz}(\Delta L_{xz}+\Delta L_{zx}).
\]

等价的对称张量写法是对角项加 \(2S_{xy}\Delta D_{xy}+2S_{yz}\Delta D_{yz}+2S_{xz}\Delta D_{xz}\)。不能把 ij 的真实 xy/yz/xz 顺序误读为 xy/xz/yz。

以上应命名为 **reported-gradient virtual-work diagnostic**。CSV中的 raw 梯度已经包含 float(V) 和 float累计；动量还有独立的逐对 float提交。现有 soil 总Ace混合了重力、AS、AV等，没有纯应力加速度，因此这些量不是实际 `Σm v·a_stress`，不能称真实 GPU 阶段能量残差。墙 CSV 只覆盖四个局部ID且没有本次 fresh ghost σ/p，无法从其恢复完整实际墙力功；旧native ghost字段不能替代本次CPU重建真值。

保留所有 signed贡献及各项绝对值尺度，避免只展示大项抵消后的净值。可按已有的有墙求积支持/无墙支持、fresh FS、κ>0历史及四个focus分组；有墙求积不等于接触，κ>0不等于当前塑性加载。描述尺度可分别用 \(\sum V|S:D^0|\)、\(\sum V|S:D^1|\)、\(\sum V|p\theta|\)，分母为零不夹值、不增加物理门。若异常功差在近床与问题ID先于近距恶化集中，可支持进一步定位；若远小于相应内功/压缩功，可反驳其为主导机制。非零本身不足以确定原因。

## 6. 如采用同一个完整速度梯度，其离散伴随候选应是什么

仅考虑同一个全速度梯度同时承担有效应力应变率和压力压缩源、并令 θ=tr L 的理想离散系统。土—土的伴随成对内力应为

\[
F_{ij}^{\mathrm{adj}}=V_iV_j
\{T_iC_i+T_jC_j\}g_{ij},\qquad
F_{ji}^{\mathrm{adj}}=-F_{ij}^{\mathrm{adj}}.
\]

于是 \(\sum_i v_i\cdot F_i^{\mathrm{adj}}=-\sum_iV_iT_i:D_i^1\)。这是该梯度的转置作用，不是把 \(C_i\) 随意乘到原应力和上。一般有

\[
(T_i+T_j)(C_i+C_j)/2\ne T_iC_i+T_jC_j,
\]

且矩阵顺序不能随意换成 \(C_iT_i\)。若有效应力梯度与压力 θ 保留不同支持/核/体积求值，则必须分别取两个算子的伴随并相加，不能仅凭其连续公式相同而套用这一单算子式。浮点舍入也不是一个精确线性映射的转置，实施后仍需量化原舍入差。

需要分别满足的性质为：

- **线动量**：相同无序pair的反向贡献必须严格反号；支持互反、体积与核一致，不遗漏反向边或只单侧改 Ci。墙对物理土系统提供外力，必须另有明确反力/牵引记账。
- **角动量**：该候选一般不是逐对中心力，所以仅有对称 T 和 Fji=−Fij 不足以保证逐对零力矩。对一个无外力的完整土系统，如果同一梯度精确再现任意刚体旋转，使每个 \(D_i^1(\Omega x)=0\)，则由虚功恒等可推出全局内力矩为零。仿射完整性条件可写为 \(M_iC_i^T=I\)，其中 \(M_i=-\sum_jV_j(x_i-x_j)\otimes g_{ij}\)。近边界缺支持、混用墙/土算子、退化拟合和浮点求值均需单独审查；受约束固定墙本来可以提供外力矩，不能要求土系统自身角动量不变。
- **功率**：同一完整 L、同一应力与压力、同一配对和边界自由度下才有上述伴随恒等；它不是单独修正内力后自动获得的总能量证明。

若墙 full-image 速度已被消元为冻结状态下的线性映射 \(v_w^*=\sum_kB_{wk}v_k+b_w\)，则墙应变算子的伴随还包含 \(B_{wk}^T\) 对所有插值donor的回传。把 ghost速度当物理固定0、或仅在现有墙应力力上乘 Ci，都不是这个消元算子的完整转置。另一种理论处理是把扩展ghost系统连同其应力、速度与约束一并记账；当前代码并未据此得到新的成套验收。

因此不得只改内力而忽略外牵引/载荷离散、墙镜像/接触反力、同阶段 wall Ace及Darcy加速度散度、压力与有限Kw储存项、AS和AV的独立功/边界性质。AS不是当前弹性内能，AV使用tangent速度是独立的耗散边界路径，不能无论用途将三种速度差全部强制统一。任何候选也必须保留均匀应力平衡、原旧算法OFF控制及现有必要时步和原生安全门；本记录不自动准入该修改或试验。

## 7. 不得扩大成总能量结论

当前 \(m_i=\rho_{t,i}V_i=V_0[\rho_wJ_i+(\rho_0-\rho_w)]\) 随 J 变化。因此 \(\sum_i m_iv_i\cdot a_i\) 是瞬时力功，并不单独等于 \(d(\sum_i m_i|v_i|^2/2)/dt\)：尚有 \(\sum_i\dot m_i|v_i|^2/2\) 及耦合质量/渗流输运的解释。塑性 \(S:D\) 又包含不可恢复功，有限Kw压力储存和边界排水/约束功也未在本 note 闭合。离散伴随虚功、耗散性、材料返回一致性与完整耦合能量守恒是不同检查，不能互相替代。

本轮只新增此数学 note；无新组件、无解码/求解/构建/参数扫描/半步链，所有既有正式结果、PRE及失败证据保持原样。

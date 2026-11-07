# DP apex：物理闭合与算法范围审查（只读研究，2026-11-07）

本记录不修改生产、不构建、不运行，也不变更已闭合 r2 包和旧证据。结论是：完整的顶点算法不能只把 `ApexNeeded` 改成 `q=0` 后继续沿用光滑返回的历史量。零、负剪胀下某些试应力不存在原塑性势允许的顶点返回；保留旧 tension-cracking 功能则应明确它是额外的应力/张拉政策。

## 1. 当前代码和原文实际说了什么

- `src/source/FunSoilMaterial.h:69–76`：现 MR1 只承认弹性和光滑径向返回；`qtr=0` 或光滑区间末端仍超屈服即 `ApexNeeded`。`36` 的提交条件不允许 apex。这是明确未实现的范围，不能解释成完整 DP 顶点支持。
- 同文件 `51–55` 用 `κ=κold+λ/√3` 和 `I=Itr−9Kβ(κ)λ`，适用于其光滑方向假设；`95–97` 将 κ 写成 float。这里的 κ 是等效偏塑性应变，不能换成文献里另一个定义的硬化变量。
- 旧 `JSphCpu.cpp:3946–3977`：先由第一次应力修正计算并累加 κ，随后做 trace 平移和 deviatoric scaling；最后两项修正没有重新纳入 κ。这也是旧 fast 与“完全一致返回”不能混称的原因。CPU/GPU 原有 fast 路径应原位保留，不能为填新路径的缺口顺带改掉已验收路径。
- 本地 Bui 2008 原文 `src/papers/elastoplastic basic/Num Anal Meth Geomechanics - 2008 - Bui - Lagrangian meshfree particles method  SPH  for large deformation and failure.md:466–492`，§3.3.1、式(29)–(30)：当 trace 超过圆锥顶点时平移三个正应力，保留剪应力。`522–550`，式(31)–(33)：另做应力比例回缩。这是两步应力修复政策，原文没有给出与同一个非关联势一致的 apex λ、κ 或塑性功更新。[Bui 2008 原始出版页](https://onlinelibrary.wiley.com/doi/10.1002/nag.688)
- Zhao 2019 本地原文 `src/papers/u-pw/2019 - Zhao - A generic approach to modelling flexible confined boundary conditions in SPH and.md:454–478`，式(39)–(41)，同样把 beyond-apex trace 修正和超屈服缩放分开。
- GeoDualSPHysics 原文 `src/papers/elastoplastic basic/GeoDualSPHysics.md:167–212`，表1和式(10)–(12)：定义等效偏塑性 κ，以及 PS、3D 外接/中接系数；没有给出 apex 特殊分支。不能凭其常规应力返回公式推断已经解决所有顶点状态。[GeoDualSPHysics 原始论文](https://jzhao.people.ust.hk/home/PDFs/2026-CPC-Ruofeng.pdf)
- Bui & Nguyen 2021 本地 `Bui 2021-CG.md:794–824` 对应应力校正/半隐式返回，并回引 Bui 2008 的修正；该文本也不能提供本项目完整 apex 历史闭合。

## 2. 本项目符号下的推导

以下是从给定的流动法则独立推导，张拉为正；`q=√J2=√(s:s/2)`，`I=tr σ`，`α=DP_phi(κ)`，`β=DP_psi(κ)`：

\[
f=q+\alpha I-k_c,\qquad g=q+\beta I,
\quad\Delta\kappa=\sqrt{\tfrac23\Delta e^p:\Delta e^p}.
\]

`K,G>0`；采用同一完整应力增量的端点 BE 约定。势在 q=0 时的偏量次梯度满足 `v∈∂q(0)`、`tr v=0`、`v:v≤1/2`：

\[
\Delta\varepsilon^p=\lambda(v+\beta\mathbf1),\quad
s=s^{tr}-2G\lambda v,\quad I=I^{tr}-9K\beta\lambda.
\]

**光滑返回 q>0**：`v=s/(2q)`，因此 `q=qtr−Gλ`、`Δκ=λ/√3`，并且 `0≤λ<qtr/G`。

**顶点返回 q=0**：

\[
\Delta e^p=\frac{s^{tr}}{2G},\qquad
\kappa_A=\kappa_{old}+\frac{q^{tr}}{\sqrt3G},\qquad
\lambda\ge\lambda_0=\frac{q^{tr}}G.
\]

所以顶点处 κ 不再随额外体积塑性乘子继续增长。对 `αA>0`：

\[
I_A=\frac{k_c(\kappa_A)}{\alpha(\kappa_A)},\qquad
\lambda_A=\frac{I^{tr}-I_A}{9K\beta(\kappa_A)}.
\]

必须实测/代回 `λA≥λ0`、`f=0`、次梯度范数、应力—塑性应变关系和 κ，不能只检查 q 非负。

| 情形 | 原 g 的 apex 可行性 | 必须区别的风险 |
|---|---|---|
| β>0 | 上式 λA 有限，且 λA≥λ0 时才可能成立 | 软化可导致光滑分支多根；还需先检查实际光滑根和加载延续性 |
| β=0 | 必须 Itr=IA；这时可选最小 λ0，最终 σ/κ 唯一而 λ 不唯一 | Itr>IA 的静水张拉不能由原 g 降低 trace；把 trace 截断是额外政策 |
| β<0 | 代数上可能有 λA≥λ0，但不代表物理可接受或唯一 | 可能与光滑根并存；正 IA 下顶点端点塑性功为负 |
| qtr=0 | κA=κold；若 β>0 且 Itr>IA 可有纯体积顶点流 | β=0/负β时一般不能消除过大的正 trace |
| α=0 且 kc>0 | 屈服面退化成圆柱，没有有限静水顶点 | 应走 von-Mises 型光滑返回，不能计算 kc/α；静水张拉另由选定张拉政策决定 |

`Itr=IA` 的判断只能用清楚的应力容差，不应通过改写输入 trace 或给 β 加任意 epsilon 造出解。φ 或 ψ 的三维映射只改变 α、β、kc 及其导数，不改变上述不变量和次梯度推导。

## 3. 塑性功与反例

由实际修正反算应变，而不是只信 λ：

\[
\Delta\varepsilon_v^p=(I^{tr}-I)/(3K),\qquad
\Delta e^p=(s^{tr}-s)/(2G).
\]

同轴修正时端点机械塑性功为

\[
W_p^{BE}=\sigma_{new}:\Delta\varepsilon^p
=\frac{q(q^{tr}-q)}G+\frac{I(I^{tr}-I)}{9K}.
\]

光滑屈服上它等于 `λ[kc+(β−α)I]`；顶点上等于 `λ β IA`。若 `kc>0, α>0, β<0`，顶点的这个端点机械功为负。不能用把 κ 继续写成 `λ/√3` 或把负功截零掩盖。

这是机械塑性功审查；若另外定义硬化/损伤自由能，严格热力学耗散还须减去相应储能变化。本项目当前指数软化没有给出这样的自由能函数，不能把“端点功非负”冒充完整热力学证明。

一个无量纲完美塑性反例：`G=1, 9K=25, α=0.2, β=−0.1, kc=1, qtr=1, Itr=1.25`。此时 `ftr=0.25`；这些 α/β 落在平面应变 DP 映射的可达范围内。

- 光滑根 `λ=0.5`，`q=0.5,I=2.5`，满足原 f/g。
- 另一个代数顶点根 `λ=1.5≥λ0=1`，`q=0,I=5`，也满足次梯度代数关系，但其端点功 `−0.75`。

因此“顶点 λ 非负且大于 qtr/G”仍不足以确定唯一物理解，更不能简单优先顶点。这个反例无需代码改动即可复算。

## 4. 如何保留旧张拉处理而不谎称同一模型

如果需要处理 ψ=0 或负ψ的全部张拉状态，必须把额外张拉/开裂政策说清楚。一个可审的完整组合是

\[
f_s=q+\alpha(\kappa)I-k_c(\kappa)\le0,\quad
f_t=I-I_t(\kappa)\le0,
\]

\[
g_s=q+\beta(\kappa)I,\quad g_t=I,
\]

\[
q=\max(q^{tr}-G\lambda_s,0),\quad
I=I^{tr}-9K(\beta\lambda_s+\lambda_t),\quad
\kappa=\kappa_{old}+\frac{\min(\lambda_s,q^{tr}/G)}{\sqrt3}.
\]

两套乘子分别满足互补条件。应实现/验证 shear-only、tension-only、两面交线、必要的顶点子分支，不以“先 clip 再缩放”代替互补条件。纯体积张拉分支不增加偏塑性 κ；联合分支 κ 必须由实际偏应变修正计算。

必要的物理选择包括：张拉面是平均应力截断还是最大主应力 Rankine 面；It 的数值/与强度的关系；张拉势；张拉是否有独立损伤历史/能量。不能从普通 DP f/g 自动推导这些选择。[Itasca 官方 DP 文档](https://docs.itascacg.com/pfc600/common/models/drucker/doc/modeldrucker.html) 明确将剪切 DP 与张拉面/张拉势分开，是可参考的完整分支结构；其参数/历史定义不能直接当本项目实验参数。

若取 `It=kc/α` 以接近 Bui 的 trace 上限，这个张拉面只在圆锥顶点处接触原屈服面：它能给 ψ=0 等缺少体积方向的 beyond-apex 状态提供附加张拉流，但仍不是原 g 的解，也**不能保证负ψ的整个近张拉光滑区都有非负端点塑性功**。对负β，若要求整个保留的光滑区都满足这一功条件，需 `It≤kc/(α−β)<kc/α` 或采用其他明确的张拉/损伤模型；这会改变旧模型的张拉强度，不能静默加入。

没有实测张拉强度时，选择 `It=0` 是另一种明确的无张拉强度假设，但对于有黏聚力土会改变原 DP 的张拉承载，不能称为“只是提高精度”。采用 Rankine 截断还会引入主应力方向/交线处理，开销和验证范围大于平均应力截断。

## 5. 最小可实施顺序与不确定性

1. 保持已验证的 fast 和 C08 r2 文件原样；新统一模块显式区分 `Elastic/Smooth/Apex/Tension/NoAdmissibleFlow/NonConverged`。缺少物理解与求解不收敛不是同一个错误。
2. 先独立验证各 DP 系数映射、φ/c/ψ 软化导数、光滑一致返回，以及**确实可行**的纯 apex（正β）和零β边界态。κ 用实际偏塑性增量，不复制论文另一种硬化变量。
3. 负ψ、零ψ高静水张拉、φ=0、近零φ、纯静水 qtr=0、软化多根、回转客观性均单列材料点测试。对不闭合状态准确返回原因，不能错误声称完整模型已实现。
4. 在决定张拉政策后才加组合流/开裂分支，至少验证互补、有限应力、κ和塑性应变一致、机械功诊断、CPU/GPU同一数学，以及既有路径回归。**这一步是模型选择，不是多加几个 assert 可以解决的问题。**
5. 通过这些单点/短窗后再交长期计算；不能仅以没有 NaN 或 f≤0 作为完整材料验收。

未唯一确定的核心：用户要求“统一完整 DP”究竟指保留 Bui 的既有张拉修复政策，还是要求同一非关联 g 在全部应力空间的严格 flow；对 ψ≤0 两者并不等价。若研究范围包含显著张拉，需要明确物理政策，而不能承诺两者同时逐点等价。

## 6. 补充主要文献与适用限制

- [Sysala et al., 2015, arXiv:1503.03605v3](https://arxiv.org/html/1503.03605)：§3.1 式(3.5)–(3.9)、§3.3 式(3.16)–(3.28)；web lines248–267、308–384 给出次梯度和顶点/光滑区分。其假设 `β>0`、硬化函数非减，而且内部变量演化定义是 `Δbarεp=ξΔλ`；不能据此把本项目的**等效偏塑性 κ**在 apex 也设置成 λ/√3，或宣称负ψ与软化下仍享有该文唯一性定理。
- [Hjiaj, Fortin & de Saxcé, 2003](https://www.sciencedirect.com/science/article/pii/S0020722502003762), DOI 10.1016/S0020-7225(02)00376-2：讨论非关联 DP 的完整顶点处理及变分/双势结构。当前可检索的是作者摘要/出版方段落，未获得完整公式；本记录**没有**假称复现了其具体双势算法。
- Bui 2008、GeoDualSPHysics 与 Zhao 2019 的本地原文定位见§1。Bui 中 tension cracking 与 SPH 人工应力抑制聚团是不同层次；不能将新的材料顶点返回当作已经解决数值拉伸不稳定，也不能反向以人工应力替代材料闭合。


## 7. 官方开源实现的交叉审查（模型借鉴，不复制代码）

[OpenSees 官方 DruckerPrager.cpp](https://github.com/OpenSees/OpenSees/blob/master/SRC/material/nD/UWmaterials/DruckerPrager.cpp)，GitHub `fetch_file` 返回 blob `b35c9fecee56eb12118f23c374ec70e8e674e894`。1-based 源码行408/411是两条独立的剪切与张拉屈服函数；516/517分别更新 shear 历史 alpha1 和含体积/张拉贡献的 alpha2。源码同一局部积分器处理一个或两个活动面、两套乘子以及互补关系。这证实成熟实现会明确增加张拉面/势和历史，而不是把一次 trace 截断称为原剪切势的完整流动。[官方源码定位](https://github.com/OpenSees/OpenSees/blob/master/SRC/material/nD/UWmaterials/DruckerPrager.cpp#L403-L522)

但该实现还带运动硬化、独立张拉软化，偏应力范数归一化也与本项目 q=√J2 不同。其 alpha1、alpha2 不能直接叫作本项目 κ，也不能把其全张量塑性应变范数和累计偏塑性历史混为一谈。特别是顶点处乘子与偏塑性增量不再一一对应。若采用类似的独立张拉损伤，后续持久状态/输出/重启也需显式加入该历史，不能仅借一段应力返回函数。

本次仅分析流程和数学，未复制 OpenSees 实现。该文件旧许可头对商业用途有限制，不应把代码直接移入本项目。

[MOOSE 官方 SolidMechanicsPlasticDruckerPrager 源码参考](https://mooseframework.inl.gov/docs/doxygen/modules/classSolidMechanicsPlasticDruckerPrager.html) 的构造器实际在源码67–73行约束初始 φ、ψ∈[0,π/2] 且 ψ≤φ。它支持硬化/软化接口，仍不能充当 ψ=−5° 的直接真值。官方 [CappedDruckerPragerStressUpdate](https://mooseframework.inl.gov/releases/moose/2022-06-10/source/materials/CappedDruckerPragerStressUpdate.html) 另有 tensile/compressive strength、独立硬化对象及顶点/交线平滑；启用这些选项是另一种模型闭合。可借其活动面/校验结构，不能将平滑锥或额外 cap 的结果当作未平滑原 DP 的逐点等价参考。

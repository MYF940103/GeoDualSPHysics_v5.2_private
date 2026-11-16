# C08 ψ+2.5°：Eq19、Eq47与自由面水力边界只读审计

本记录只依据已冻结代码、原论文和已有派生结果。没有修改源码、输入、PRE或已完成结果；没有运行solver、reader、build、VTK、Git或hash。只复核已有physical check及其6个选定时刻的spatial CSV（30000行），未重扫301帧typed数据。

## 来源与版本

- 原文：src/papers/u-pw/Lian 2023 u-pl.md，尤其190–214、226–267、395–474、584–608、838–888、909–943行。
- 原PDF：src/papers/PDF/Lian 2023 u-pl.pdf，第11页Eq47已渲染并目视确认；本次只读使用 [PDF skill](C:/Users/syosh/.codex/plugins/cache/openai-primary-runtime/pdf/26.1112.11011/skills/pdf/SKILL.md)，未创建/编辑PDF。
- 下文代码行均指 tests/outputs/c08_h18_hg_groups_build_r1_build/frozen/src/source 中的实际冻结版本，不混用当前public源码行号。
- 已有结果：logs/c08_h18_hg_psi2p5_full3_physical_r1.check.json；figures/c08_h18_hg_psi2p5_full3_physical_r1_spatial.csv。本记录不把正常出口/native安全或图像相似当物理验收。

## Eq19与塑性历史：未发现此处符号或量纲错误

论文Eq19为 ψ=ψ0 exp(−sf ε_eq^p)，Eq13/15使用 g=ξψ I1+q、q=√J2，ε_eq^p为累积等效偏塑性应变。由 ∂g/∂s=s/(2q)、s:s=2q²，可得 Δε_eq^p=Δλ/√3；体积塑性增量为 Δε_v^p=3ξψΔλ。

FunSoilMaterial.h49–60正是 ψ=psi0 exp(−sf κ)，并计算 dψ/dκ=−sfψ；106–109用 κ_new=κ_old+λ/√3、I_new=I_trial−9Kξψλ。故κ定义、DP塑性体积项与论文该部分一致。正ψ保持正、负ψ保持负，均向零衰减；参数sf单位为逆κ，角度传入为弧度（JSph.cpp4084–4096）。Apex的偏塑性κ在到达q=0时饱和，另有既存张拉面策略（FunSoilMaterial.h125–149），不能因此声称论文完整apex策略相同。

当前κmax=0.06820569187402725且sf=.2，ψ/ψ0=0.98645148，ψ约2.46613°。衰减本来只有约1.35%，不足以期待3秒内迅速消除剪胀吸力。这不是Eq19漏接的证据。仅有κ>0也是累计历史，不能代替“本步正在塑性剪胀”。

## 当前有限Kw显式压力更新没有独立重复添加塑性体积源

GPUker1965–1966、2282从导数速度差累加总θ=∇·v；1393–1404用 Jdot=Jθ演进J。n=1−(1−n0)/J，因此在连续层面自动满足 ndot=(1−n)θ。

GPUker1588/1600的完整压力率是

    pdot=(Kw/n)[−θ+(k/γw) lap+chain/γw]。

lp/lx/gp/加速度散度在1538–1587计算；变量k与grad(k)链项在1593–1601。1611覆盖写入完整rate，不是加到旧压缩源。没有另加 Δε_v^p 或 Δκ 压力源，不能把塑性体积项再手工加一次。塑性通过应力返回、运动与总θ进入耦合。

GPUker1356–1363更新 p_new=float(double(p_base)+dt*double(rate))。冻结host1770–1776为predictor半步，1902–1904为corrector从原p_base加完整dt；并非TPI的前两步压力外推。当前为有限Kw=1GPa的动态u-pl显式质量式。

## Eq47实际是TPI负压力行的修正，不能直接复制系数到当前率式

论文先在Eq30取 n/Kw→0；Eq33定义 Aij，Eq36定义Bi，Eq38–39以 p_i^a=(1+α)p_i^n−αp_i^(n−1)、α=.5近似隐式邻居压力。PDF第11页Eq47的负压力分支为

    p_i^(n+1)=[Bi+Σj Aij p_j^a+(β/Δt)p_i^a]/[Σj Aij+β/Δt]，β=.04。

正压力侧沿原TPI式；原文没有给零点分支的额外规则，也没有明确列β单位。文字限定用于考虑塑性的土，并解释其目的是减缓塑性剪胀引起的负孔压增长；方程本身却不含Δλ/Δκ/塑性体积率的局部筛选项。因此它不是把显式pdot乘.04，也不是只乘塑性体积源，更不是负压截零。原文同节明确批评负压cut-off会丢失负超孔压物理。

令S=ΣAij、D=Bi+ΣAij p_j^a，Eq47可重写 S(p_i^(n+1)−D/S)+(β/Δt)(p_i^(n+1)−p_i^a)=0。它增加对自身外推压力的局部储存/松弛项，所修正对象是TPI椭圆压力行。直接加入当前有限n/Kw模型会改变存储/残差与时间记忆，必须另行推导、量纲核对并明确人工正则化性质，不能宣称质量守恒或与论文等价。

数量级上，若将其按同一γw倍乘残差解释为附加存储，当前 γw n/Kw约3.4323e−6（相应长度单位下），而β为.04；二者约差1.17e4倍。这只是条件性存储尺度类比，不能当作已实现的等价方程或直接参数推荐。

## 论文C08并不是全暴露面p=0 Dirichlet

MD881–883明确：三面墙impermeable，自由面使用文献[36]的free-seepage treatment，并采用ponding p_l≤0。该条件与4.3柔性基础在ramp后施加零孔压排水（MD780–786）不同，不能把后者搬来称为C08论文边界。MD923–943另说明Eq47稳定与非稳定结果不同；上部零压区在随后剪胀时仍可出现负压。

当前GPUker1108–1109只将真实FS正p投影为0，保留负p；host1425–1434在completed geometry执行这项ponding，predictor不在这项策略中直接约束。HydroMechDrainage=1则不同：GPUker1104–1106将真实排水节点的p与rate都置0，1356–1363在每次压力更新钉0，1533在RHS早退rate0。前者是单边p≤0语义，后者是零压Dirichlet。

FSType固定墙自身为Boundary（GPUker819–824）；fluid的2/3仅由邻域缺损/法向/umbrella检测，fluid与fixed都参与（842–881、936–978），没有明确的wall-contact排除；type3不走type2的umbrella剔除。因此不能逻辑保证所有2/3都远离固墙，也不能把2/3等同接触标签。

只读已有6帧spatial CSV：每帧149个FS2/3，均为type2；各仅1个z<dp（ID7010，右下自由边/床角）、1个x<dp（ID2109，左上角）。前四选帧149/149为负p，末145/149为负p。近墙混合角点不是整片底床被判排水的证据，更不是NoPen实际反力/接触计数。

## 广域负p的现有证据和边界敏感性范围

全程最负保存态为Part20/ID7010/FSType2，p=−20204.3203125Pa、κ=.0538373、J=1.0014349、θ_last=+.0166912s−1。整窗已有44135次FS2/3负p观测。此处负p确被现有单边策略保留，但论文也采用p≤0；所以不能据此断言实现错了。

初始参数的有限Kw扩散尺度 D=Kw k/(nγw)约58.27m²/s，sqrt(D×.2s)约3.41m。局部剪胀负源可快速向宽域传播，广域负p不自动意味着广域塑性源。末态Jmean=.9996408而2699节点p<0，也不能用最终J>1单独归因全部压力历史。另须区分绝对p、固定P0差与论文extra pressure。

可以先研究独立release-only全FS零压边界候选，避免先引入TPI/β新方程；但这只能称边界敏感性试验，不是更忠实论文复现或全局负压clamp。最小私有host路线是在 JSphGpu::IsHydroMechDrainageActive()1347–1355原首guard前，仅当独立准入的实际handoff且GravityPreloadReleased时返回true，保持XML/成员HydroMechDrainage=false。由已有调用链统一启用RHS、pre/cor压力更新及FS的p/rate零压，不只是事后改保存值。PRE/import/材料历史和现有CUDA算式保持，需独立policy证据及全FS逐帧原生p=0审核；源不重算。

不能直接改XML Drainage1：JSph.cpp617–625/3837、Gpu.cpp1954及私有HG guard（GpuSingle.cpp725）均拒绝该container组合。核实GetGravityPreloadContract1/2（JSph.cpp3741–3775）未序列化Drainage/FreeSeepage，主要阻断是当前准入，不宜误称一定由契约字符串不一致拒绝。私有host干预仍需根明确准入、原有效路径短回归、实际程序/策略说明；本审计不授权任何新build或solver。

低成本下一步可先做纯制造检验：总θ=0与给定均匀J膨胀时的有限存储解析式 p−p0=−Kw ln[(J−s0)/(J0−s0)]；同一trial的DP返回Δκ/Δε_v^p符号；常量/线性压力零Laplacian；FS正/负/零三值、fixed-wall不投影、仅release后激活的原边界核语义。若考虑β型正则化，再单独核完整有限存储残差/时间记忆/量纲与负压连续性，β0须回到原方程。不能先借β或零压边界掩盖σ/J/压力耦合错误，原NoPen ReactionClosed=false限制也未消失。

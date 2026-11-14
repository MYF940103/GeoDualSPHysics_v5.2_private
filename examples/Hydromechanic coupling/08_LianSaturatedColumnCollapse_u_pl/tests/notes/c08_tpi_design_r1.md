# C08 TPI + negative-pressure stabilisation: design r1

作者推导稿，2026-11-14。只新增本note；没有物理源码、构建、solver、native、VTK、Git或SHA动作。本文供root审阅后决定是否实现小代数组件，不准入GPU/CPU物理窗、half或完整Tv计算。

## 1. 已核文献与记号边界

已按PDF技能目视核对原src/papers/PDF/Lian 2023 u-pl.pdf打印6–11页，使用已封存outputs/c08_tpi_reference_r1/page-06..11.png；对应MD为src/papers/u-pw/Lian 2023 u-pl.md，Eq23/25约309–350行，Eq29–39约395–478，Eq40–47约484–608。PDF是公式排列/因子依据，MD仅供定位。当前原源是outputs/c08_preload_schema2_source_r1/full_source.zip；当前AS03实际program/PRE绑定见已通过full3/run和pressure_feedback_r3收据，不换成旧keep5/schema1源码。

严格区分三层：

- **论文原式P**：Eq23/33–39/47，含其LF时间安排、Ci-only核校正及成对平均k。
- **连续一致式C**：从Eq29整理、使用真实body gravity的量纲/静水平衡表达；并非声称所有印刷离散项已完全等价。
- **拟议扩展X**：保持现Symplectic固体、增加一个显式默认Off压力方案。它不是论文LF的原样实现，也不先宣称二阶、无条件稳定、物理修复或提速。

下文p为论文pl/实际总孔压，不是固定参考P0或p−P0。σ′为有效应力；总应力仍σ′−pI，AS定义/本构/材料历史本轮不改。K_w为Pa，hydraulic conductivity k为m/s，γ_ref=ρ_w g_ref为Pa/m；代码g_ref=9.80665与实际body vector g_b=(0,0,−9.81)必须保持区别。

## 2. Eq23的方向与二阶空间定义P

实现位置差为d_ij=x_i−x_j；论文r_ji=x_j−x_i=−d_ij。原径向核梯度g_ij=∇_i W_ij=F_ij d_ij，支撑内F通常为负，所以g指向邻点。定义G_ij=C_i g_ij，对应论文的修正梯度。于是

\[
G_i f=\sum_j V_j(f_j-f_i)G_{ij},\quad
\widetilde F_{ij}=\frac{r_{ji}\cdot G_{ij}}{|r_{ji}|^2}
=-\frac{d_{ij}\cdot C_i g_{ij}}{|d_{ij}|^2}.
\]

不能因代码用d而把这个负号丢掉。Eq23在二维为

\[
D_{ij}^{mn}=4\frac{r_{ji}^m r_{ji}^n}{r^2}-\delta^{mn},\qquad
H_i^{mn}(f)=\sum_jV_j(f_j-f_i)D^{mn}\widetilde F
-(G_i f)_{m'}\sum_jV_jr_{ji}^{m'}D^{mn}\widetilde F .
\]

第二项是Taylor defect修正，不是可选的压力耗散。对仿射f，用同一解析梯度和相同全部soil+fixed/ghost场可代数消掉第一项的线性贡献。C1矩阵只保证一阶矩，不保证任意无序云上的全部二次矩精确；不能把一般二次场误差设为零门。

**4是2D系数，不直接用于3D。** 由各向同性连续角向二次/四次矩可推得候选d维形式D=(d+2)eeᵀ−I；因此3D候选系数为5，需独立制造场核验后才可支持。此推广是数学推导，不是本论文已验证的3D公式。3D盲用4会给出Hhat=.8H−.1tr(H)I及lap=.5tr(H)，不是小误差。平面应变虽保存6分量应力，其空间维数仍2。

对各向同性k，二维trace(D)=2；Ci=Cj=I、恒k且无正则时，压力Lap项可与熟悉的−2V_j k F_ij对应。核、权和顺序仍须从当前Wendland字面源定义，不把论文Cubic/H1.2偷偷合入当前H1.8。

## 3. Eq33–39的A、E、B及正负号P

设kbar_ij^{mn}=(k_i^{mn}+k_j^{mn})/2，

\[
A_{ij}=V_j\bar k_{ij}^{mn}D_{ij}^{mn}\widetilde F_{ij},\quad
T_i^{mnm'}=\sum_j V_jr_{ji}^{m'}D_{ij}^{mn}\widetilde F_{ij},\quad
E_i(q)=k_i^{mn}(G_iq)_{m'}T_i^{mnm'} .
\]

注意E用k_i而非把kbar再次塞进同一误差项。定义S_i=Σ_jA_ij、N_i(q)=Σ_jA_ij q_j，则Eq32的压力空间算子为

\[
P_i(q)=N_i(q)-S_iq_i-E_i(q).
\]

这里q_j−q_i与当前LP里的p_i−p_j相反，A的符号也相反；不能只替换差值却保留旧w号。Ei一般依赖已知压力梯度；将其放入B是一个明确的lag/source选择，不能又把同一E全部并入矩阵而重复计数。空间算子的制造场应使用同一q算GP与E；时间外推时N和E是否来自同一q另行声明，不混成一个证明。

论文Eq34–36，在其g_b=−g e_z且γ_l=ρ_l g的标量重力记号下：

\[
B_i=-\gamma_l\theta_i+\gamma_l\,[\nabla\cdot(k\nabla z)]_i
+\rho_l\,[\nabla\cdot(k a_{true})]_i-E_i,
\quad S_ip_i^{n+1}=B_i+N_i(p^{n+1}).
\]

论文写B_ij但这是接收点i的一个source，不能误作每邻点重复加一次。Eq37正文说两个右侧项已知于t，故先将B标为B_i^{known}：θ、k、E的压力梯度及a都必须注明真实已知来源。Fig1在新pressure之后才算新σ/a，不能把B中的a悄悄当成同一新pressure产生的新a；纸面并未给出足够的LF子层实现细节。原文小组件对照先把B全部作为明确给定的旧source（含E(p_n)）；若刷新E到pα，那是另一个声明的离散选择。Eq37把右侧邻压取p^n；Eq38/39则用

\[
p_j^\alpha=p_j^n+\alpha(p_j^n-p_j^{n-1}),\qquad
p_i^{n+1}=\frac{B_i+N_i(p^\alpha)}{S_i} .
\]

这是一次已知source/邻压外推的局部更新，不是求解全局矩阵。α=1仍只使用两份旧历史，**不等于真正求解Eq35的隐式系统**。不采用文字中“α1即完全隐式/无条件稳定”的强说法；论文下一页本身也说明TPI仍受稳定条件约束。

一个最小条件检验是固定行/无source的邻域特征数μ：z²−(1+α)μz+αμ=0。对实μ，严格衰减域为−1/(1+2α)<μ<1；μ=1的常量根是1。这只验证该简单递推，不能当当前全耦合系统谱。α=.5并不自动稳定任意离散压力行。

## 4. 量纲、β与finite-Kw分支

以d维V[m^d]和W[m^−d]计，Ftilde[m^−d−2]，故A/S单位1/(m s)，E/B/N(p)单位Pa/(m s)。有限储水项按连续式为

\[
M_i\dot p_i=B_i+N_i(p)-S_i p_i,\qquad
M_i=\gamma_{ref} n_i/K_w\ [1/m].
\]

论文TPI在Eq29→30明确令n/K_w→0，之后才作Eq35–39。它不是当前有限Kw显式midpoint的另一个等价写回。默认必须保留：原u-pw选择不变；已开的u-pl默认仍走现finite-Kw显式压力方案。新增incompressible TPI只显式选择时生效，默认Off；Eq47也独立默认Off，其真实逐点/时层资格未定义前不得准入。最先隔离β0的TPI-incompressible兼容，不选physical β。不要无声把M保留再加β而仍称原论文TPI；那是另一个待推导hybrid。

Eq47对p_i^n<0的行增加

\[
p_i^{n+1}=\frac{B_i+N_i(p^\alpha)+(\beta_i/\Delta t)p_i^\alpha}
{S_i+\beta_i/\Delta t} .
\]

β=0应严格退化Eq38；β项是以p_i^α为锚的负压pseudo-storage，不是β乘当前R，更不是负压裁零，亦不是β/KernelH。按上面SI未缩放行，β需为1/m。论文只给数值.04而未在该页定义单位/行归一化；**.04m^−1只能作为明确声明的同SI纸面兼容性样本**，不构成当前physical参数选择，也不能宣称论文已证明它无量纲。若用无量纲βbar，必须给出固定参考长度L*和β=βbar/L*；L*不能暗设为KernelH，否则改分辨率就变了模型。此处需root审定推导约定后才实现组件；.04m^−1仅是纸面同SI样本，不是已经适合当前惯性系统的正式参数。

任意整行乘正数c时，A、B、E及β必须一同乘c；除γ_ref后β也除γ_ref，才能保持同一结果。不能只归一化S/N而把裸.04加到分母。对S=0、未定义/非有限分母或严重病态行，记录真实行及原因；不加epsilon、不删邻点、不用β掩盖空间退化。

**固定负支的连续极限风险不能隐藏。** 由(S+β/h)(p_new−pα)=F(source,pα)，在固定空间离散、光滑解、固定步长且负支不切换时，p_new−pα=(1−α)h p_dot+O(h²)。若A/S和已知force source不含1/h，则领先伪容量为M_eff=β(1−α)，并有O(h)S/空间source多时层修正；它不会随h→0消失。X0的endpoint真force及θ/E时间偏移在该光滑限定下仅O(h)，没有另一个领先有限容量。若以后把a由速度差/h消元进压力矩阵，则行本身可能含1/h，必须重新推导，不能沿用这个结论。α=1是退化的另外极限，也不因此成为真implicit。

按SI β=.04m^−1、α=.5约定，M_eff=.02m^−1；用γ_ref n/M_eff解释的等效Kw约.172MPa，远小于原1GPa。若不分资格把它加给弹性负压点，这是负压动力响应的大改动，不能称“既不改物理又只消噪”。下面弹性coupled toy给出可能失去衰减域的**兼容性反例**；它不直接否定论文只在塑性情形下使用β。真实塑性切线、活动资格、AV/离散时层都不同，不能凭这个弹性反例宣称paper整体错误，也不能凭“稳定化”名称预先接受。

Eq47正文明确只在考虑塑性变形时使用，但没有给出完整逐点/时层活动算法。因此不能用整个case的MaterialTypePlastic、累计κ>0、仅ψ角或float Δκ>0来一刀切资格。当前ψ0 Smooth剪切流动没有塑性剪胀；出现负压或曾经塑化，不等于该节点当前需要Eq47。张拉面/apex的体积返回也不能未经解释自动当成论文剪切势的dilation。

若未来准入Eq47，需先定义真实ReturnMaterial fullcommit status/连续λ及相应塑性体积增量的资格和来源时层，区分Smooth剪胀、弹性体积变化及tension/apex处理。现有native累计κ不能提供该信息，float history还可能不变；该资格目前是明确缺口，不自动承诺新增status数组。最先以β0检验TPI-incompressible兼容性，未选任何physical β。

在**纯代数、已明确冻结负支/资格**的公式检验中，以p_n<0选择Eq47、p_n>0用Eq38，p_n=0取β0只是需声明的tie约定，不是原文明示。真实Dirichlet优先。不得把判据换成p−P0、预测压力符号或事后拟合阈值。生产方案的资格必须另行解决，不能拿这个代数branch当完整物理策略。

## 5. 连续一致起点C与原印刷式的两个空间疑义

当前native Ace只存非重力力加速度：JSphCpu.cpp1742清零，3489–3491/3624–3626更新速度时才加Gravity。因此令A_native=a_true−g_b，不能将它当a_true后再重复减重力。

由Eq29用真实向量重力写成

\[
M_i\dot p_i=-\gamma_{ref}\theta_i+
\nabla\cdot\{k[\nabla p+\rho_w(a_{true}-g_b)]\}_i .
\]

等价定义头势Φ=p−ρ_w g_b·x，则右侧为−γ_ref θ+P_k(Φ)+ρ_w D_k(a_true)。这样γ_ref与ρ|g_b|无需假设相等。静水制造场是p=ρ_w g_b·x+const、a_true=0、A_native=−g_b；Φ常量，应在任意合法k场和畸变支撑上给出相容零水力项。

需要显式区分，而不直接宣布论文错误：

1. 原PDF6页Eq25的pressure Taylor Ei项只写∂p；gravity z_ji二阶项未显式带同一−grad(z)·moment。在恒k畸变支撑，LPp+γLPz可能先相消而单独Ei留下残差。该页pressure-defect项也未显式写与第一压力项相同的1/γ因子；按SI量纲存在排版/约定疑义。因此先以Eq29、32–36整理量纲一致式，再把**逐字Eq25**作为独立数学对照。不能照搬一个破坏已验证静水参考的字面行而不报告。
2. Eq25最后的kbar_ij(a_j−a_i)·G_ij对常量a、变k给0；完整div(k a)应有a·grad(k)。当前链式k′(J)gradJ·a正是这一部分，不能为接近论文删除它。

拟议连续一致空间候选X先用**同一个**P_k算子作用Φ，含Φ的梯度defect；加速度项保留完整product或等价保守flux散度，包括常a/变k项。一个清楚的候选是D_k(a)=k_i Div_C(a)+[k′_i G_iJ]·a_i，它保留当前chain语义。它与逐字pair-kbar加速度行并不相同，需分别列误差，不能混称“论文原式实现”。

若仍想将Φ式转换回native Ace式，必须推导P_k(ρg_b·x)和D_k(g_b)使用的匹配矩，先验证两者离散消重力。不能只在不同算子中形式上相消常量g_b，尤其γ_ref=ρ9.80665而body g为9.81。

## 6. 与当前空间算子的关系：不能一次悄悄合并

当前RHS的已审字面式使用d=x_i−x_j、Gi=C_i g、Gj=C_j g：

\[
w_{ij}=V_j\frac{d\cdot(G_i+G_j)}{r^2+\eta^2},\quad
LP=\sum_jw_{ij}(p_i-p_j),\quad
Lx=\sum_jw_{ij}d,\quad gp=\sum_jV_j(p_j-p_i)G_i.
\]

压力/加速度项为k_i[LP−(1−FS)gp·Lx+ρ(Da+FS A_native·Lx)]，再加k′gradJ·(gp+ρ A_native)。其SymC、η²、k_i乘积法则、raw-FS Taylor分支，与论文Ci-only、裸r²、kbar及E_i不同。只有特定恒k/完整矩/η0条件可代数重合；不把当前LP直接改名Aij后称完整Eq33。

已完成的η0、private FS-normal、old residual-viscosity及Shepard试验均保留，未证明修复。空间算子选择与TPI时域选择必须分别标注；首小组件应同时输出论文literal与连续一致候选，不在一次真实轨迹里同时调整核/H/AS/AV/FS/本构。当前J→n ledger与论文Eq24 donor(1−n_j)离散也不是逐字相同，本阶段不改变J积分或另加塑性体积source。

## 7. 真实history与Symplectic接口：扩展候选X，不冒充论文LF

论文Eq27及Fig1把n,p,σ′,v作为半时层变量，先θ/pressure，再应变/材料与a。现代码则JSphCpuSingle.cpp897–925：force_n→原predictor→排序→force_h→原corrector；原压力在JSphCpu.cpp3346/3365按p_n+.5hR_n、p_n+hR_h写回。PorePressPrec保存本步完整p_n，3727–3731会释放；它不是前一完整步p_{n−1}。

只把上述两个p+=hR改成两次Eq38，或半步旋转history，均不是等价TPI。特别B_h/θ_h/半几何上得到的压力不能不加论证就标为完整p_{n+1}。单纯冻结旧baseline a之后评价一行也不是匹配全耦合TPI。

**一个明确但尚未接受、也不是root已选定接口的Symplectic-endpoint扩展候选X0：**

1. 持有真实完整提交的p_n、p_{n−1}及前步dt/valid flag，按ID随全部排序/压缩搬运。第一小组件先限constant dt。机械predictor压力使用声明的ph=p_n+.5(p_n−p_{n−1})；TPI邻压独立定义pα=p_n+α(p_n−p_{n−1})，不可偷换含义。它们在α=.5时数值相同，但概念不混同。
2. 固体仍按原Symplectic两个真实force、材料、J、位置/速度更新，不加第三次材料返回。它们实际使用p_n/ph；新分支不再把有限Kw R积分到压力，亦不和TPI双重写回。
3. 在真正endpoint几何/J/v/σ′上，以已知pα重建合法ghost、C、θ，并取得新source acceleration。X0明确取E=E_endpoint(Φα)，将梯度defect与本次空间压力场匹配；这不同于Eq37正文的旧B解释，是新扩展的显式选择，不伪称论文指定。最清楚的初始实现候选是**额外一次真实force pass**，用当前完整σ′及pα得到a_source，再构造endpoint A/E/B；a_source是实际新force，不是原轨迹的冻结a。它仍是已知邻压/压力依赖AS的lagged source，不等于a(p_new)的非线性隐式闭合。
4. 在endpoint行用Eq38/47得到唯一p_new，执行已声明的完整步边界投影，再一次性提交pressure/history。固体不追加速度kick；下步开始才使用已提交p_new。该压力-固体交错是**新扩展**，须coupled manufacture/稳定性证明，不能以纯row通过就声称论文LF或二阶一致。

这条X0不是零成本：原每步2force变3force，至少多一遍endpoint邻域/FS/墙及压力行计算。endpoint force产生的Rσ只作派生量，不再推进σ或κ；J积分仍用原固体stage θ_h，不得无声用endpoint θ覆盖其历史。输出需区分θ用于J与θ用于TPI row。endpoint邻域重建不能对临时pα偷偷执行新的half-stage ponding/Shepard；必须先设计“几何/ghost评价”与“真实pressure提交边界”的接口，否则暂不实施X0。

另一条可能节省完整force的方案是endpoint独立kinematics pass，source a用同一步2a_h−a_n外推：要额外捕获a_n/a_h并按ID随排序保存，明确它是外推而非endpoint实测。若只用a_h，则source时间落后半步。此方案阶数/AS非光滑/接触适配尚未证明，不作为默认选择；它不是可隐藏的免费替换。若改走真正论文LF，则需另一个固体积分路径，其材料/边界/历史资格更大，当前不准入。

由此可见，完整可用TPI首先是时间层接口问题，不是将beta.04塞入现RHS的局部补丁。

## 8. history、撤墙、cold start、native/restart的必须合同

- p_history保存**完成所有真实完整步投影之后**的提交p；每成功完整步仅旋转一次。预测/额外force/row/保存/重复cap不能旋转，失败stage不提交。P0永不被用作前步压力。当前float压力可继续以float存历史，外推/行求和用double再一次真实float提交，dtype/舍入需明示。
- 排序/periodic/扩容/压缩均需对应history生命周期；首范围先无periodic、固定ID、无新生删除soil，不能以数组槽当永久ID。C08 retire255只删原固定墙，5000soil历史原样继承；ghost历史应从对应soil pα重建，不外推未定义旧固定墙压力。
- 原schema2 PRE只有当前p/σ′/κ/J等，并不包含相隔一个积分步的p_{n−1}/dt_prev。不能拿Part999与1000（保存间隔.01s）冒充5us history。若使用旧PRE，必须声明**新cold start零斜率**：p_prev=p_n、dt_prev=dt、historyColdStart=true；它不是完整TPI restart或真实前步数据。若需要真实长程历史，则新PRE也必须走同一TPI并输出所需history，不能重命名旧PRE来认证。
- true restart必须输出/验证pressure scheme、完整步pn−1、其真实clock/step/dt、history-valid/cold标记、α/β及单位/模型、已提交边界状态/材料law/kernel契约。历史缺失应拒绝exact restart或进入明确新cold start，不静默构造。
- 零时间撤墙/开排水会改变边界资格；其是否重置history必须作为显式事件合同。真正Dirichlet压力在相应实际时层强制，不允许历史外推生成违反已施加Dirichlet的值。C08原completed-only正压FS投影保持，不把TPI顺手改为已拒绝的half-ponding策略。
- 不透水墙的连续目标是normal·[grad p+ρ(a_true−g_b)]=0，等价normal·[grad Φ+ρa_true]=0；不能把static velocity无穿透当成已闭合Darcy反力。free-seepage互补条件、原raw-FS closure与NoPen ReactionClosed=false仍是独立限制。Eq47不是排水边界条件，也不闭合接触反力。模型有塑性不等于每个负压节点一定在发生塑性剪胀。

## 9. 最少验证次序与停止条件

本note只允许后续root审后实现小组件，不准入下面未来solver：

1. **纯代数/制造场组件**：实际d/G符号；常量/仿射和二次场；2D/3D角矩；全部soil+fixed解析字段而非固定墙置零；constant/variable k、常a非零的a·gradk；p=ρg_b·x、a_true0且γ_ref≠ρ|g_b|的静水平衡；逐字Eq25与一致head候选各自保留。C1-only不能把无序二次误差强设零。
2. 同组件核Eq35小系统真解、Eq37、Eq38/39历史递推、α0/α1、β0/负压记忆/零压tie、整行缩放、无定义分母；以两个/三个未知的已知例即可，不创建大CSR/Eigen/全谱框架。检验cold-start、真实history、重排/retire及失败不提交的生命周期。

   **先加一个小coupled Fourier/oscillator代数参考**，再谈solver。取g=0、k常量、q≠0、σ′=H e、ρ>ρ_w，有edot=iqv，ρa=iq(He−p)，M pdot=−γ iqv−kq²p+ρ_w k iq a。M=0消元给 eddot+[γ/(k(ρ−ρ_w))]edot+[Hq²/(ρ−ρ_w)]e=0。对有限M，特征式为Mρλ³+k(ρ−ρ_w)q²λ²+(MH+γ)q²λ+kHq⁴=0；正H/k/M且ρ>ρ_w的衰减域还要求(ρ−ρ_w)γ>Mρ_w H。以H约29.6MPa、当前初始ρ2072.5kg/m³计，M_eff=.02明显超出该域；这是**弹性H、不含AV/AS、固定负支**的兼容性参考，不直接当完整C08谱或否定paper的塑性β资格。必须同时验证M=0与M=β(1−α)两种连续参考，以及真实X0离散递推而非只算一个row。该小系统可独立比较放大因子、压力/位移相位与收敛误差，明确检验不同ph来源；不把纯row根域或α=1直接当耦合稳定性。它只是常系数参考，不能替代C08非线性/自由面的实际验收。
3. **一个小1D弹性耦合测试**：先默认Off对保留分支原字段一致，再新方案的已声明初始/边界/理论。无完整Tv、无新增half链；incompressible参考与finiteKw参考分开，不以5Pa强迫跨模型相等。先原保守dt，不夹带增步/材料/核变化。必须检查压力与固体耦合相位，不能只有一个纯pressure row。
4. CPU步骤/边界/history合同通过且有科学收益后，才考虑GPU短实施比较与memcheck，再决定是否一个有界C08 ψ0窗。不得由row通过直接启动GPU长窗/其他ψ/新PRE。其他ψ仍未解锁。

原必要dt、有限/IDs/clock/J/n/ρ/k/P0/κ/墙和本构门保持。TPI-specific稳定步长与论文R放大系数需另推导/验证；不能删除现pore/wave必要界就宣称大步稳定。当前先保守沿原dt门只为实施资格，不由此承诺提速。

若上述空间/时间层/单位无法闭合，先停在明确可证伪的代数组件结果；不再无边界扫AS/阻尼/β参数。TPI与Eq47也不保证消除非关联DP的材料局部化，后续是否需要有限转角塑性HG或场一致PST由新的真实证据决定。

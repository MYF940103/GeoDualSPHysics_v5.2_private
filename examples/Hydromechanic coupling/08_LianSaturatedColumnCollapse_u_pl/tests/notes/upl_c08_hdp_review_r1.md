# C08 h/dp 1.2 与 1.5：只读数值审阅

本记录仅含源码、现有配置及核函数代数核对；未改变源码/输入、运行程序或重算任何已完成证据。h/dp=1.5 是可检验候选，不是已证明能消除团聚的设置。当前 C08、服务器包、PRE 及活动构建均保持原状。

## 实际核与人工应力距离乘子

`source/FunSphKernel.h:47,51–81,88–132` 与 `FunSphKernel_iker.h:36–85`：二维 Cubic 为 W=10/(7πh²) w(q)，q=r/h；w=1−1.5q²+.75q³ (0≤q≤1)，w=.25(2−q)³ (1<q<2)，支持半径 R=2h。令 a=h/dp、s=r/dp，则 W(r)/W(dp)=w(s/a)/w(1/a)。

当前 Bui AS 使用**实际** W(dp)：`JSphGpu_ker.cu:2212–2213,1881,1890`。其距离乘子 F(s)=.2[W(r)/W(dp)]³；raw R 张量已含 ε。它不是实际加速度或力：还须乘谱张量、原始核梯度及 Vj/rho_i，r=0 的梯度为零。`FunSphKernel.h:57–59,72–74` 的 legacy 固定 deltap=1/1.5 及 `od_wdeltap` 不属于此 Bui AS 归一化路径。

下表为名义实数 h/dp 的可复现代数值，不宣称 CUDA float/fast-math/packed 距离逐位重放。w 是去掉归一常数的核形状，R_w=W(r)/W(dp)。

|s=r/dp|w, a=1.2|w, a=1.5|R_w, a=1.2|R_w, a=1.5|F, a=1.2|F, a=1.5|
|---:|---:|---:|---:|---:|---:|---:|
|.32|.90755556|.93901511|2.3130619|1.6902272|2.4750945|.9657512|
|.425|.84516737|.89664236|2.1540549|1.6139562|1.9989425|.84082433|
|.5|.79383681|.86111111|2.0232301|1.55|1.6564023|.744775|
|.7|.63845486|.74955556|1.6272124|1.3492|.86171315|.49120072|
|1|.39236111|.55555556|1|1|.2|.2|
|1.5|.10546875|.25|.26880531|.45|.0038845751|.018225|
|2|.0092592593|.074074074|.02359882|.13333333|2.6284569e−6|.00047407407|

因此 s=.32/.425/.5 的 AS 距离乘子下降约61.0%/57.9%/55.0%，s=1 不变，远尾增大；不能据此独立判定实际 pair force。dp=.04 m 时 h=.048→.060 m、R=.096→.120 m；二维连续均匀邻域面积由18.0956 dp²增至28.2743 dp²，比例1.5625（+56.25%），不是实测成本承诺。理想二维方格排除 self 后正 W 邻居20→24；新 R=3dp 上另4个轴向点 W=0，不能算有效核支持。实际变形、墙、FS 与浮点截断必须另报。

## 代表配置与文献口径

以下均为正式 Def 的少量抽查，不能将 Wendland 较大 h 的成功直接当作 Cubic h1.5 验证。

|Hydromechanic coupling 下的配置|Kernel|直接 hdp|
|---|---|---:|
|03_RetrogressiveSlopeFailure_u_pw/CaseRetroSlope8m_u_pw_prestress_Def.xml 与 failure_Def.xml|2 Wendland|1.5|
|03_RetrogressiveSlopeFailure_u_pw/CaseRetroSlope_u_pw_failure_Def.xml|2 Wendland|2.16|
|04_CryerProblem_PR/CaseCryerProblem_u_pl_nu030_r1_Def.xml|2 Wendland|1.8|
|05_LianFlexibleStrip2D_PR/CaseLianFlexibleStrip2D_PR_release_Def.xml|2 Wendland|1.8|
|07_Selborne3D_u_pw/CaseSelborne3D_u_pw_prestress_Def.xml 与 failure_Def.xml|2 Wendland|1.5|
|08_LianSaturatedColumnCollapse_u_pl/CaseLianSaturatedColumnCollapse_psi0_shared_r6_Def.xml|1 Cubic|1.2|

`JCaseCtes.cpp:126–132,291`：hdp 与 coefh 不能同时指定；h/dp=coefh√dim。因此 coefh=1.5 实际为二维 h/dp≈2.1213、三维≈2.5981，不能直接归类为 hdp1.5。`JSph.cpp:1932–1933` 日志分别输出两者。

本地 `papers/u-pw/Lian 2023 u-pl.md:285–293`（printed p5 §3.1 Eq21）明确 hsml=1.2dx；其 Cubic 写法与上式归一等价。`papers/elastoplastic basic/Bui 2021-CG.md:261–262,386–387` 有 Cubic h=1.3dx 示例；§2.3/Fig7（约423–430、507–514行）区分 pairing 与 tensile，并展示更大邻域的 pairing 风险；§2.4 建议 Cubic h/dx 1.0–1.5。这些支持尝试1.5的合理性，不证明 C08 一定改善，也不证明1.5必然 pairing。

## PRE 兼容性及最小合法诊断

`JSph.cpp:3731–3737` 的 GetGravityPreloadContract 包含实际 KernelH 和 kernel 枚举；`JGravityPreloadState.h:111–113` 对合同字符串精确比较，`JSph.cpp:3764` 用当前合同 Load。因此旧 h=.048 PRE 不能合法接到 h=.060；绕过合同会混用空间算子与平衡状态，不能称为同一预载控制。KernelH 本身为 float（`JSph.cpp:724`），不要按名义小数伪造相等。

最低成本顺序：先用已封口几何作 h1.2/h1.5 冻结邻域/近对/FS-halo诊断，明确重建 C 或几何 shadow 不是原生 rate 重放。若需真实执行，先做 fresh h1.5 的受限短重力启动（无 StateFile，保留 dt2.5us、原物理参数和所有必要守卫；可用现有 -nsteps 限制，实际帧数据输出），只查新支持域的 force/FS/MLS/稳定性，不能据短启动宣称10s平衡或 collapse 合格。

受控 collapse 比较仍需要一份**同 h1.5 的 fresh certified elastic 10s PRE**，再用同 h 接收；现有 NoPen/keepbed release-only 路径按已准入 handoff 使用，不能假设 fresh NoPen1 连续源也获准。保持 Cubic、ε=.2/n3、dp、dt、CompletedOnly、材料及接触政策其余均不变。现程序已支持 runtime h；新 native profile 应单独明确 h=.06，不能放宽旧 h=.048 reader。

h 同时改变机械/梯度 C、Darcy、FS、mDBC/MLS 支持和随 h 的 Eta²，不只是平滑邻居；更大 R 也可能激活更多深墙点。全部 finite、J 饱和、det≥1e−3、FS/P0/ledger/κ 与必要 dt 门须保留，不能同时调大 dt 或另开 shifting/HG/SPR。依据实际近对、FS gap、压力/应力/体积/速度与运动形态评估，不能只看图更平滑。后续执行次序由 root 审阅决定，本 note 不启动任何任务。

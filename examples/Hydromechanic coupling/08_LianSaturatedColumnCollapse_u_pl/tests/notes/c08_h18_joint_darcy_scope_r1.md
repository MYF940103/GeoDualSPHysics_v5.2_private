# C08：二阶空间算子证据与联合Darcy制造场的最小范围

2026-11-15。本文仅整理已读原文、绑定归档、既有检查和数学范围；仅新增本note。没有编写/执行新fixture、求解器、native读取器、VTK、构建、half、Git、SHA扫描或修改源码/输入/PRE/旧记录。所有候选均未获本文物理准入，其他psi保持原有独立资格要求。

## 1. Lian原二阶式与当前实现不是一个开关

原文为 `src/papers/u-pw/Lian 2023 u-pl.md:294–350`，原PDF打印6页Eq22–25。Eq23来自其Ref36：Lian et al., *A general SPH framework for transient seepage flows through unsaturated porous media considering anisotropic features of diffusion*, CMAME387 (2021)114169，DOI `10.1016/j.cma.2021.114169`。本地原PDF为 `src/papers/PDF/Lian 2021 seepage flow unsaturated porous media.pdf`；既有原页审计在 `upl_lian_second_derivative_scope_r2.md` 定位打印13页Eq49–52、15页Eq54–57。它是带一阶Taylor缺陷消除的通用二阶SPH近似，文中说明与Español–Revenga形式相近，不是材料返回算法的Taylor导数，也不自动保证任意失序云二次精确/二阶收敛。

令r_ji=x_j-x_i、g_ij=grad_i W、G_ij=C_i*g_ij、G_i p=sum V_j(p_j-p_i)G_ij，则二维原式为

    Ftilde_ij = r_ji dot G_ij / r_ji^2
    D_ij^(mn) = 4*r_ji^m*r_ji^n/r_ji^2 - delta_mn
    H_i^(mn)p = sum V_j[(p_j-p_i) - G_i p dot r_ji] D_ij^(mn) Ftilde_ij

二维trace(D)=2；在同邻域/体积/核、接收点Ci、裸r^2且不替换边界梯度时，其迹可与标量Lstar代数一致。系数4不能不经资格直接用于3D。完整Hessian存储本身不改变恒定各向同性k所需的迹。

当前物理归档为 `tests/outputs/c08_preload_schema2_source_r1/full_source.zip`，不以当前可编辑public源码替代。该归档 `src/source/JSphGpu_ker.cu:1551–1600` 使用d=xi-xj：

    w_ij = V_j*d dot[(Ci+Cj)gradW]/(r^2+Eta^2)
    LP = sum w_ij*(p_i-p_j)
    Lx = sum w_ij*d
    Gp = sum V_j*(p_j-p_i)*(Ci*gradW)
    Da = sum V_j*(Ace_j-Ace_i) dot(Ci*gradW)
    interior_hydraulic = k_i*(LP-Gp dot Lx+rho_w*Da)
    free_seepage_FS_hydraulic = k_i*[LP+rho_w*(Ace_i dot Lx+Da)]
    variable_k_chain = k'_i(J)*(GJ dot[ Gp+rho_w*Ace_i ])

体积为V0*Jj。当前Ace=a_s-b，b为真实body gravity；gamma_ref=rho_w*9.80665与body g=9.81的角色不同，不得重复加/减重力。Eq25另采用pair-mean k而接收点k乘压力缺陷；当前为product-rule链。原印刷Eq25的gamma重复因子、gravity缺陷与常a/变k离散疑义已在 `c08_tpi_design_r1.md:110–144` 单列，不由本文判定作者程序错误或删除现有链项。成对Ci/Cj、Eta、k处理、Da、FS与墙延拓须分别审查；只去Eta不能称完整移植Eq23/25。

## 2. 已完成的比较不重复

| 既有封闭证据 | 已测范围 | 不能据此扩大认领 |
|---|---|---|
| C02 `logs/upl_lian_eq23_root_review_r1.check.json` passed | 独立全Hessian/标量迹、规则/失序/截断支撑与矩阵谱 | 非真实NoSlip墙、完整Darcy或耦合轨迹验收 |
| C02 `logs/upl_lian_scalar_kernel_r4.review.json` passed | Ci/Cavg、bare/Eta、Cubic/Wendland、float/double压力的分项比较 | 非统一最优或实际墙/变k/耦合稳定性 |
| C02 `notes/upl_lian_variable_root_r1.json` | 1536压力-only变k响应；768 trace、576恒k退化、192常量零响应；pair-k无统一优势 | 无a、gravity、真实墙/FS；不能称完整Eq25 |
| C08 snapshot81及 `upl_lian_c08_scalar_trace_review_r1.md` | 81点小变形几何，native-soil/解析墙延拓两oracle、全Hessian与标量迹 | 解析ghost不等于真实mDBC墙C/Ace；无成套零通量 |
| C08 `upl_lian_c08_darcy_zero_review_r1.md` | 真实force/墙闭合后Darcy原Eta->0->原Eta，全部5000 rate恢复；实际FS分支和trace算术核对 | 是新CPU瞬时评价，非旧native rate重放或解析精度 |
| C02 `upl_darcy_eta_wave_review_r1.md` | 规则周期弱波全257态，Eta0最大pRMS误差7.5160->8.2367Pa | 非墙/失序/变k；已决定保留生产Eta |
| C08 `upl_c08_darcy_eta0_decision_r1.md` | 旧Cubic/H1.2短物理窗完整90态；Eta0压力RMS等恶化，候选拒绝 | 不能当当前H1.8单因子结论，更非完整Lian模型 |
| C08 `c08_h18_quadratic_decision_r1.md` | 真实变形Part60、5000点、7基函数+native p、40000响应、1805墙记录；literal Eq23迹恒等检查 | p二次/混合基函数shadow明确排除Da、变k链和实际raw-FS完整率 |

真实Part60内点4389点的Laplacian RMS并无统一赢家：x2/2的pairC/Eta2、receiverC/Eta2、receiverC/bare分别约.02424/.02286/.01751；xz为.01809/.01632/.01671，(x2-z2)/2为.03635/.03709/.03716。不同误差分量的得失保留，不能因一项变小替换生产算子。这关闭了已做的有界空间选型问题，并不关闭下面联合一致性缺口。

旧CPU `support/upl_p3_actual_r3.cpp:79–115` 和复制它的perm组件确有名为quadratic_zero_flux的二次p/线性Ace。代码只对affine_equilibrium、constant_flux设置连续近零门；quadratic_zero_flux只是与同离散O(N^2)参考一致，不能改称连续零通量已通过。GPU `support/upl_gpu_darcy_component_r3.cpp:126–146` 只有affine_balance及quadratic_affine_acceleration，亦无真实NoSlip墙。旧variable-k墙波为两面FreeSlip；NoSlip已有非零XYZ affine Ace重构资格，但不等于非线性cross的完整RHS解析测试。

因此未找到可追证的“p三次含cross、a与p成套配平、真实NoSlip近床/当前墙Ace闭合”的完整制造场；不应以已有P2/去Eta/affine重构扩大认领。

## 3. 首个最小联合制造场：常J、常k、连续零drive

这只是未来范围设计，不创建新fixture。首范围限2D固定水平底z=0、远离侧角与自由面干扰的近床接收点；瞬时v=0、theta=0，J为声明的合法常量，k为常量。原h/dp、核、体积/C、原半径过滤、边界角色及必要数值门均必须明确绑定。给定a的Darcy制造场与真实force生成a的保存态诊断是两类任务，不能相互冒充。

设b=(0,0,-g_b)、X=x-x_c，A为单位Pa/m^3的固定制造系数，p_star为声明的常量压力偏置：

    p_1 = A*X*z^2
    p = p_star - rho_w*g_b*z + p_1
    a_s = -grad(p_1)/rho_w
        = (-A*z^2/rho_w, 0, -2*A*X*z/rho_w)
    Ace = a_s - b
        = (-A*z^2/rho_w, 0, g_b-2*A*X*z/rho_w)

连续物理域有grad(p)+rho_w*Ace=0，因此Darcy q=-(k/gamma_ref)*(grad(p)+rho_w*Ace)=0，theta=0时压力率也为0。床面z=0处a_s=0，与静止NoSlip的瞬时加速度条件兼容。它包含三次压力和二次cross加速度，能检验二阶压力与一阶Da的联合截断，不是由离散Gp反算a、进而强行制造机器零。

该场只是一个合法瞬时空间测试，不是已解出的全程动量/材料/自由面初边值问题；p_star、A、原点和单位必须事先声明，不拟合C08数据。左壁x=0的FreeSlip法向条件不一般与该cross同时兼容，因此不能把平床范围无声扩到左底角。若未来要测角部，需另构兼容场并单独审阅；不由本文自动扩阶/扩域。

先不同时加入变k、TPI、Eq47、新AS/AV/RV或shift。连续零drive虽形式上对任意k也成立，变k的压力链、加速度链及实际J/体积/墙合同仍需后续逐项测量，不能因常k通过直接认领变k完整资格。

## 4. 必须分开的两种墙oracle

第一种是**解析ghost延拓**：在声明的全扩展域使用同一解析场、当前核与同一quadrature，测纯空间离散的LP/Taylor/Da残差。第二种是**真实墙闭合**：从同一物理半空间字段走现实际wall pressure/J/C/Ace重构，所有已有NoSlip/FreeSlip角色及正常支持保持不变，再评价完整Darcy。解析延拓正确不能替代实际MLS/墙C/Ace证明，实际结果较小也不能不计原截断与FS/角条件就称物理精确。

本次同时阅读 `notes/c08_h18_hydraulic_accel_reflection_audit_r1.md`。当前静止NoSlip导数速度为full odd镜像，但hydraulic总加速度采用几何反射Q=I-2nn^T：

    Ace_wall = Q*(Ace_mirror+b) - b.

结合pressure-head的even延拓，驱动h=grad(p)+rho_w*(a_s-b)按Q反射，具有不可渗flux延拓的明确动机。对上述p_1=A*X*z^2，p_1为z-even，a_s的切向分量为z-even、法向分量为z-odd；在理想解析延拓中，Q配合even压力仍保持全扩展域zero-drive。实际MLS只是一阶重构时可能有二次截断；需要测量而非事先给它零误差证书。

不能只因速度odd就将NoSlip切向Ace翻号。若v^o(x,t)=-v(Qx,t)，在固定反射上其partial_t为odd，但材料加速度还含对流项。L=grad(v)、P_t=(I+Q)/2时：

    a_s^o = -a_s + 2*L*P_t*v.

仅v=0或对流修正为0时才可简化全odd；真实移动粒子MLS几何/权重时间变化也未由单保存态完整观察。partial_t v与D_t v不混用，当前Q是一种水力flux延拓，不是声称它等于NoSlip速度延拓的任意材料导数。

peer note给出的互补场还应保留为**另一种问题**，不得与zero-drive混称。g=0时取a_s=(A_a*x*z,0,B_a*z)、p=p_star-rho_w*A_a*z^3/6-rho_w*B_a*z^2/2，则Delta p+rho_w*div(a_s)=0、床面法向flux为0，但drive本身一般不为0。Q/even延拓给a_x=A_a*x*abs(z)、a_z=B_a*z及对应abs(z)^3压力，连续扩展域仍配平。若单独改全odd a而保留even p，墙外会留下假源。因此单项Da更接近点值不代表完整率更一致；未来若要采用该互补场，需另行声明而非本note自动新增执行范围。

## 5. 未来组件资格与解释边界

原IDs/真实时钟/22数组/P0/ledger及绑定数据不能被制造场试验改写。若未来采用真实保存几何，必须清楚区分其原J场与专门声明的常J制造quadrature，不把改过的J叫原轨迹；同理不能将给定解析a称原GPU保存的finished Ace。旧typed22没有CorrMat或finished total Ace，HydroMechLoadAce也不是它。

最小有用输出应保留原LP、Taylor、Da、FS receiver-Ace和完整率，分别列压力与加速度非空贡献、常量/affine退化、解析field量化/float存储误差、墙支持和conditioning；错误符号/不配平a的反例可用于避免一个全零实现自证。实际实现与独立全支持参考的一致性可用原算术预算核对；连续零值的偏差是**待观察的截断/重构结果**，不设任意5Pa等价门、不把同离散一致改称连续零通量已证，也不通过删除近墙/负压/异常点改善结果。

FS若不满足该制造场的自由渗出资格，应单列或留在首范围之外，不能把普遍Taylor shadow冒充当前raw-FS完整率；角部同理。变k链随后才逐项加入并保持pressure/Ace/source的符号和重力合同。全部局部/整体守恒、能量、材料返回、接触反力和真实轨迹精度仍需自己的证据，zero-drive制造场不能代替它们。

本范围不选择翻转NoSlip tangential Ace、不移除Eta或pair-C、不切换为论文literal Eq25/TPI、不改变dt或原阈值。已有算子比较均保留，下一步仅在独立审阅后才能决定是否值得一个封闭的零推进组件；没有新的solver、PRE、half或其他psi准入。

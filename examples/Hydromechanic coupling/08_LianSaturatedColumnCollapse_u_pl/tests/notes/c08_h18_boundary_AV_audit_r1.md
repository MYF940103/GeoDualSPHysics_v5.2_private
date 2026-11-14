# C08 H1.8：冻结边界速度与人工黏性审查

本记录保存2026-11-14已完成的只读审查。没有修改公共C++/CUDA、XML/BAT、程序、PRE或结果；没有执行候选、构建、求解、原生读取、VTK或Git，没有SHA扫描。保存本文不准入任何新的组件/物理窗口，也不解锁其他ψ。后续执行仍由根线程独立审阅和准入。

审查背景：原AS.3/n2.55的3 s结果已完成运行/原生/离线审查，孔压与形态较AS.5改善，但根线程报告后期最小NN约.063dp、69对r<.7dp、7对r<.5dp、最长材料对连续263帧，团聚尚未解决。这些数值来自根线程最新审查，本只读任务没有重复分析该轨迹；“263”是连续保存数量，不是材料ID。本文不将小间距本身直接等同于经典张拉不稳定的唯一证明。

## 1. 实际审查对象及已核绑定

使用的收据是`tests/logs/c08_preload_schema2_Release_r1.build.json`，其`passed=true`、configuration=`Release`。以下三个文件实际长度和mtime均与该收据一致；核验只读stat，不计算SHA：

| 项 | bytes | mtime_ns（收据及实际匹配） |
|---|---:|---:|
| GPU程序 | 28874752 | 1794223127069913800 |
| full_source.json | 48353 | 1794222843364623500 |
| full_source.zip | 1082321 | 1794222843308768900 |

对应绝对路径为：

- 程序：`D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b/examples/Hydromechanic coupling/08_LianSaturatedColumnCollapse_u_pl/tests/outputs/c08_preload_schema2_Release_r1/DualSPHysics5.2_GEO_win64.exe`。
- capture：同case下`tests/outputs/c08_preload_schema2_source_r1/full_source.json`。
- **实际读取归档**：同case下`tests/outputs/c08_preload_schema2_source_r1/full_source.zip`，即`D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b/examples/Hydromechanic coupling/08_LianSaturatedColumnCollapse_u_pl/tests/outputs/c08_preload_schema2_source_r1/full_source.zip`。

以下C++/CUDA行号均为该ZIP中`src/source/`成员的行号，不以当前public文件或另一私有程序替代。该stat核对不声称重新证明整个历史构建链；原对象/链接及源码归档资格沿用已有构建收据，没有重扫历史对象或原始BI4。

实际AS.3/n2.55 `Run.out`另外核对到：Wendland Kernel2，dp=.04m，H=.072m，support=.144m，Visco=.1、ViscoBoundFactor=1、Cs0=119.5748520184038m/s、FixedDt=5us。没有以启动文字代替某个私有override的运行政策；本次对象是原macro-off schema2 Release，不含旧AV15、residual-viscosity或FS-normal私有实现。

## 2. SPR开关不能直接用于当前C08，但镜像导数速度已经存在

`SoilBoundaryDerivativeSPR=1`在这个程序里不是当前C08可直接打开的已验证组合：

- CPU `JSphCpuSingle.cpp:120–136`、GPU `JSphGpuSingle.cpp:155–171`的`ConfigDomain()`拒绝SPR与StrainSoftening、ArtificialStress组合。虽然per-mk NoSlip/FreeSlip和轴向NoPen在一般弹性SPR准入中存在，不能据此跨越材料和动态容器限制。
- `JSph.cpp:3829–3844`的`IsDynamicPoreContainerConfig()`明确要求`!SoilBoundaryDerivativeSPR`；`IsDynamicPorePlasticConfig()`在`:3850–3857`依赖该容器资格。强行打开SPR还会失去当前塑性容器/NoPen的适用资格。
- CPU `JSphCpu.cpp:3122–3125`的porosity初始化仅放行loaded-column的动态SPR。
- CPU动态墙初始化`JSphCpu_mdbc.cpp:1051–1063`、GPU `JSphGpu_mdbc.cpp:146–160`也只允许loaded-column的SPR组合。

不能只删上述guard后称“已经完成C08 SPR接入”。更关键的是，**当前C08不是在用零墙速度计算全部导数**：

1. `HydroMechDynamicSeepage`在CPU `JSphCpuSingle.cpp:105–109`、GPU `JSphGpuSingle.cpp:140–144`自动启用`DynamicPoreWall`。
2. CPU `JSphCpu_mdbc.cpp:312–314`、GPU `JSphGpu_mdbc.cpp:135–140`的普通`ComputeBoundaryDerivativeVelocity()`遇`DynamicPoreWall`即返回。动态墙拥有权优先，不叠加第二次SPR拟合。
3. 每个真实force阶段的FS入口先调用动态墙状态：CPU `JSphCpu.cpp:1170–1178`、GPU `JSphGpu.cpp:1329–1340`。
4. 动态镜像拟合使用当前`V_j=(MassFluid/RhopZero)*J_j`：CPU `JSphCpu_mdbc.cpp:183–194`，GPU `JSphGpu_mdbc_ker.cuh:114–120`；不是普通旧SPR中的被动`mass/rhop`权重。
5. 固定底面NoSlip输出`v_deriv=-v_mirror`；FreeSlip侧面输出`v_deriv=(I-2nn^T)v_mirror`。CPU `JSphCpu_mdbc.cpp:1172–1186`、GPU `JSphGpu_mdbc_ker.cuh:157–175`均处理全部XYZ分量；真实固定墙`Velrhop.xyz`仍写为零。

因此，仅把XML中SPR从0改1，不会给这个动态墙再增加一套此前缺失的镜像导数速度。若guard被绕开，普通SPR重构仍被动态墙优先返回；若强行让两套重构都执行，又可能用不匹配的权重覆盖当前same-stage J墙值。这既不是低成本的已知修复，也不是当前授权可直接发起的参数试验。

## 3. 三条速度路径及其数值后果

CPU `JSphCpu.cpp:2392–2441`、GPU `JSphGpu_ker.cu:1917–1966`保留不同用途：

- `dv_rhop`来自实际粒子/固定墙存储速度。
- `dv_visc`对于mDBC墙使用`TangenVel`：它只含墙拟合镜像速度的切向部分；用于人工黏性。
- `dv_rhop_deriv`对于活动固定供体使用`BoundDerivativeVel`的完整镜像向量；`dv_grad_deriv`选取该向量，进入应力速度梯度和体积率。

体积率采用当前J体积及接收粒子校正梯度，累加至`PoroTheta`；应力梯度在邻域求和后再乘原校正矩阵：CPU `JSphCpu.cpp:2611–2620`、GPU `JSphGpu_ker.cu:2260–2269`。J/孔压体积源和应力率因此已经消费动态墙导数速度。密度在J反馈下为账本派生量，不应把旧连续性数组的存在误读为另一套独立密度积分。

这三条路径不应为了名字一致而直接合并。底面NoSlip的导数速度含镜像法向，AV沿原mDBC的切向速度处理；FreeSlip侧面的切向速度被保留而法向导数反射。修改其中一条会改变近墙应变/耗散/孔压反馈，必须单独解释和验证，不能声称只是重命名或“打开原SPR”。

固定平面`FixedPlaneStageProjectionReleaseOnly`的NoPen位置/速度投影是另一个处理。其`ReactionClosed=false`限制仍在，动态镜像导数速度并不会自动补齐同阶段Darcy所需的接触反力闭合。

## 4. Lian的alpha=.5更正与实际AV定义

**Lian2023 Table1中的稳定系数alpha=.5不是人工黏性系数。** 本地`src/papers/u-pw/Lian 2023 u-pl.md:460–473`明确把它用于Eq39的TPI压力历史外推；`:879`是Table1相同alpha。`:360–363`则说人工黏性/人工应力沿用Bui[11,18]的形式及推荐参数，并采用[18]的土体声速。不能从该表把当前Visco=.1解释成“比论文AV小五倍”。

本地Bui2008 MD（`src/papers/elastoplastic basic/Num Anal Meth Geomechanics - 2008 - Bui - Lagrangian meshfree particles method  SPH  for large deformation and failure.md`）§4.2、`:831–839`记录多数计算的线性与二次AV系数约为.1；Eq60–62位于`:790–815`。该MD有OCR符号/长空白问题，结合其上下文区分AV系数、人工应力系数和TPI系数，不能互相替代。

当前归档只保留Monaghan线性AV分量。对接近粒子对，写成：

`mu_ij = h*(dv_visc dot r_ij)/(r_ij^2+Eta2)`，

`pi_ij = -Visco*c0*mu_ij/rho_bar`，

`a_i_AV = -sum_j (V_j*rho_j)*pi_ij*gradW_ij`。

门是`dv_visc dot r_ij<0`。当前没有Bui式中的二次`beta_Pi*mu^2`项，因此不声称与完整Bui AV公式完全相同。原源码位置为CPU `JSphCpu.cpp:2547–2572`、GPU `JSphGpu_ker.cu:2072–2097`。

动态分支实际使用当前J派生混合密度`rho_j=rho_w+(rho0-rho_w)/J_j`、质量型权重`V_j*rho_j`和两端平均混合密度，没有再次用被动legacy rhop作分母。固定墙的此值是镜像求积惯性，不是移动墙的真实质量。

声速也不是同一数字定义：当前`JSph.cpp:4309–4317`采用`c0=sqrt((K+4G/3)/rho0)`，本case实际119.574852m/s。本地Bui2013 `src/papers/elastoplastic basic/Bui 2013.md:269–277` Eq17为`sqrt(E/rho)`；Lian §3.2引用该声速规则。比较AV强度须连同声速、密度语义、核函数和h审阅，不能只比较Visco数字，也不能未经确认把论文rho直接替换为代码的某个密度。

AV先进入混合动量加速度，随后该真实same-stage Ace及重构wall Ace用于动态Darcy：`JSphGpuSingle.cpp:671–687`、`JSphGpu.cpp:2073–2088`。因此增大AV不仅减速，也会改变孔压加速度项。机械耗散更强不自动代表完整u-pl稳定或压力噪声更小。

## 5. 旧AV15/residual结果不能直接外推

保留结论为`notes/upl_c08_av15_decision_r1.md`、`notes/upl_c08_rvisc90_decision_r1.md`。旧AV=.15测试使用Cubic/hdp1.2、AS.2/n3、dt2.5us、旧r2 PRE与keep5；它只将首个r<.7dp的保存时刻从.15延至.16s，未消除团聚，负压极值略差。旧residual-viscosity是额外数值算子，不是现有AV开关；其.90s候选在原必要pore-step门下失败，最后保存态孔压/近对恶化。

这些结果不能证明当前Wendland/hdp1.8、AS.3/n2.55、dt5us、新schema2 PRE/bed-last下必然同样失败。反之，也不能因工况变化就忽略“加速度先进入Darcy”的耦合风险，或以论文TPI alpha=.5为理由直接启动AV=.5。

## 6. 近距极限及最低成本下一步

归档`FunSphKernel.h:206–231`的Wendland核满足：当r>0趋零，fac趋有限，`gradW=fac*r=O(r)`。AS的`[W(r)/W(dp)]^n`也趋有限；在应力/密度有界的条件下，成对AS排斥仍为`O(r)`，不是硬核排斥。不能由“指数更大”推断已经很近的粒子一定分开。

对固定径向相对速度和有界密度，原AV中`mu=O(r)`，与`gradW=O(r)`相乘后的成对AV力为`O(r^2)`。静止或分离时其门为零。所以增大Visco可加强接近过程耗散，却不能提供静态分离力。实际η=.1h，而本H=.072m；r很小时正则分母更主导。原`ALMOSTZERO=1e-18f`定义于归档`DualSphDef.h:132`，完全重合还会被原pair排除。以上是冻结有界系数的极限推导，不是对已经出现的每个近对的实际力定量结论，也不证明核函数本身有实现错误。

当前不优先新增参数窗口，更不强开SPR。建议根线程从AS.3已审301帧中选择持续近对的**初生、加剧、最小间距**三个真实保存态，按固定材料ID做低成本原CPU零推进机制检查：

1. 分别记录有效应力、孔压力、AS、AV对相对径向加速度/功的贡献；同时保留该对和全部邻域合力，避免只看一条近对而忽略其他粒子的持续挤压。
2. 保留r/dp、r/η、W及gradW、AV接近门、相对径向速度、AS所消费的实际总应力谱；不能把有效应力单独当作当前总应力AS的输入。
3. 标记FS、距侧/底墙距离、NoPen活动及实际same-stage Darcy压力率，区分内部近对和墙投影/水力反馈。

这可区分排斥不足、邻域持续压缩和压力/接触反馈，再决定是否值得一个新的短窗。零推进CPU重算不是未保存GPU子阶段逐位重演，也不是完整轨迹因果证明。未找到明确机制前，不承诺新的AV值、SPR/HG/shifting、材料政策或TPI能够修复。原所有有限、ledger、P0、κ、时钟、FS、几何与必要步长门保持，其他ψ仍需各自独立准入。

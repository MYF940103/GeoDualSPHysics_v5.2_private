# C08 H1.8 radial residual candidate: private GPU author scope r1

状态：仅作者资产，尚未 prepare、编译、运行、原生读取或物理准入。根线程须完整审阅后分别准入；本文件不能自动启动任何任务。公共源码、正式 XML、原 schema2 PRE、旧成功/失败资产均不改。

## 文件及边界

- support/c08_h18_rv_radial_gpu_r1.h：私有 API、45 数值指标、主87列/MFG57列定义。
- support/c08_h18_rv_radial_gpu_r1.cu：独立 GPU 邻居/LS/径向算子/证书/制造与标量 fixture。
- support/c08_h18_rv_radial_gpu_prepare_r1.py：仅生成一个可逆 JSphGpuSingle.cpp host overlay、上述 CU/header 副本、host.diff/source.json 和 prepare 收据，不编译或运行。
- support/c08_h18_rv_radial_gpu_r1_build.py：由另一作者独立准备和根审阅，采用既有权威 MSVC/NVCC/link 配方；本 note 不执行它。

未来 prepare 入口为 python -B support/c08_h18_rv_radial_gpu_prepare_r1.py --execution-authorized；只有根独立准入才可使用。生成专属 outputs/c08_h18_rv_radial_gpu_r1_source，已有完整/partial 输出或收据时拒绝。source.json 包含 private_sources={host,CUDA,header}:stat、source_archive、baseline_source_capture、baseline_builds、prior_vector_RV_builds、host_diff、exact_reverse_original_host_bytes、policy_schema=3、operator、alpha=.1、main_columns=87、manufactured_columns=57、fixture_columns=6、112/2/114 构成。只用必要 size/mtime 绑定，不扫描 SHA。

基底为已封存 c08_preload_schema2_source_r1/full_source.zip 的 src/source/JSphGpuSingle.cpp。三个唯一锚点：原 include 后加私有 host；原 ComputeDynamicPorePressureRateGpu(dynamicridpg) 之前加 RV；原 JSph::SaveData(...) 后记录最新 Pre/Cor。prepare 逆替换必须精确恢复全部原 host bytes。原物理 CUDA 源和112个物理对象保留；两个私有对象为新 host 和独立新 CU，不采用旧 vector-RV host/CU。新 CU 的最终独立 NVCC 标志必须为 --fmad=false，原物理 CUDA flags 不变。无公共类、CTE、material、typed22 或 BI4 ABI 改动。

新环境变量 C08_RV_RADIAL_H18 缺席时所有私有调用/文件初始化均不进入，无 RV 分配、kernel、常量上传或侧车。仅显式值1允许候选路径，其他非空值报错。OFF 源范围不是未经运行的二进制位回归；旧 Debug 也不代替新 Release 数值证据。

## 固定物理资格和力调用点

仅当前 ψ0 已认证 schema2 same-material Wendland 接收：H=.072f/dp=.04/hdp1.8，原5us、AS total .3/n2.55、AV .1、SPR/HG/Shepard/阻尼 off、G1 on、原 variable-k Model1/Ck2、原 original-TimeStep 两阶段 source-clock。完整原 r2-style Wendland PRE 保留 σ、κ、J、p、P0；连续 bed-last retirement255/keepfalse，6805=5000土+1805固定，原5000材料 IDs[2060,7060)。NoPen 固定平面 release-only 且 ReactionClosed=false；不引入墙 RV bond。host 保留原契约的详细 material/geometry/mode/time-step/BC 守门。

调用位置为真实力/AS/AV/Ace 已形成后、原完整动态 Darcy 之前。新 RV 只提交土 Ace 的三个 float 分量，随后原 Darcy 照常读取更新 Ace。不会增加真实力、材料返回、J、x、v 或压力时间积分次数。下一次原 necessary-dt 仍由原求解器检查；私有 dt-degree 门只证明冻结 RV Euler 充分条件，不取代 coupled necessary dt。

## 径向算子和 canonical 双向实现

对每个实际正 Wendland 权重土-土邻居，采用当前体积 V=V0 J、密度 rho=rhow+(rho0-rhow)/J、tau=H/sqrt(G/rho)。原未限 LS 权重 wi=G*(taui+tauj)/2 * Vj * (-Fac)；对称 beta=G*(taui+tauj)/2 * Vlo * Vhi * (-Fac)。所有 support/Fac、cell 范围、rank 检查沿原独立 RV；没有 ridge 或缺秩跳过。

按 native ID lo<hi 定向 d=xlo-xhi，n=d/|d|，dv=vlo-vhi，s=dv·n，q=[dv-.5*(Llo*d+Lhi*d)]·n。a=min((-s)+,(-q)+)，c=(alpha*beta)*a，Flo=c*n，Fhi=-Flo，alpha=.1。必须先检查 s/q finite；非活动分支显式返回 +0，只规范私有 limiter 的零，不碰 signed native clock/dterror。s<0,q>0 明确关闭，s<0,q<0 才制动；不能保证全部 all-neighbor 净力向外或所有 pair 分离。

Canonical 是 __noinline__ device helper，它从原数组重新按 lo/hi 加载两端 x/v/J/L，不能传入 caller 先算后 swap 的 residual。每次实际 directed edge 又以 j,i 调同一 helper，beta/s/q/c 以及施力的 unary-minus 逐 bit 重现必须通过；误差预算为0。Fit 另检查真实反向 cell membership。即使这样，GPU 当前图/舍入也不是 CPU bittruth；CPU 的50制造/8 fixture通过只能作数学参考。

## GPU 独立证书和预算

设 Ed 为实际 directed 边数，E=Ed/2，N=5000，dmax 为最大邻居数，u=DBL_EPSILON/2，Gamma(k)=ku/(1-ku)。权重、computed c/n 是机械恒等式的输入；LS、synthetic input 和 normalization 独立约束。所有测量、预算和分母必须 finite；无 Inf budget 虚通过，也不提高物理容差。

- 同一 canonical D_e=c*(-s)>=0、pair torque=d_z*Flo_x-d_x*Flo_z、central budget 在每向记录，最终 directed 总和乘.5。pair-power/torque-map 的 unique-edge scale 同样减半。节点功 P=sum vi·Fi、节点 torque/net 和 sum_directed |Fi_edge|1 不减半。
- 新 net Gamma(dmax+N)，预算为该系数乘 directed force-L1 scale，并用 1-Gamma(4Ed+N+1) 校正正数归约误差。
- 新 power Gamma(16Ed+7N+1)，检查 |P+D| 及 P<=budget。16/有向邻居保守覆盖 dv 三项形成、s dot五项、力三项、D乘法一项、两分量/正数累加及局部 D；7N+1覆盖节点 dot/全局 D、乘.5归约。分母1-Gamma 保留，不能套旧 vector work+2form 或 contraction identity。
- 新 torque Gamma(16Ed+6N+1)，覆盖 d 形成、F、cross、directed gather/positive scale、全局节点及 pair torque/half 归约。canonical central budget 是 Gamma16*c*(|dz nx|+|dx nz|) 的 half-sum，再校正1-Gamma(8Ed+N+1)。分别检查 pair torque、node-minus-pair reduction 和总 node torque；不能把旧 vector torque-defect 当新证明。
- normalization |n·n-1|<=Gamma16。LS 直接以四个 computed L*M-N 分量检查 Gamma20 的消去前 |L|*|M|+|N|，不是 |computed LM|；scaled determinant 原门保持。inverseUpper 分母1-Gamma12*(1+condition)必须正且 finite。
- 正加权 degree 为 alpha*sum(beta)/(rho V)，不是邻居数。乘 Gamma2 系数形成修正、Gamma16 normal 修正、1/(1-Gamma(actual degree count)) 正和修正。lambda_upper=2degree_upper，dt*degree_upper<=1。
- 冻结 RV Euler DeltaE=dt*P+.5dt² sum(|F|²/m)。预算包含 dt*power_budget 及 Gamma(7N+8) 的实际表达式归约项。只适用于本次冻结 RV/质量的 Euler，不是完整固-液 pre/cor 能量证明。
- 提交前真实 float candidate 为 float(double(Ace_old)+F/m)。Fc=m*(Ace_candidate-Ace_old)，每节点误差 bi=2 FLT_EPS*m*(||Ace_old||+||F/m||)。检查 ||Fc-F||<=bi，net/power/torque分别额外 sum bi、sum |v|bi、sum |x|bi；冻结 Euler 增加 dt sum |v|bi+.5dt²sum(2|F|bi+bi²)/m 及实际表达式 roundoff。全部节点接受后唯一 cudaMemcpy2D 提交，无先写后拒绝。

这些是当前 double gather/reduce 布局的独立证书，不能把 CPU 单次 canonical ±scatter Gamma 原封不动套来。实现采用同实际图 LS、两邻居 kernel、两 serial O(N) summary，局部五个临时 buffer 在 Add 返回前释放，cudaDeviceReset 后没有全局析构 cudaFree。每次 Add 两个 D2H summary 同步；canonical reverse 双调用有额外读取/计算。112旧物理对象保留不意味着候选无性能成本，实际开销未知，禁止从 CPU 或旧 vector GPU 耗时推断。

## 首 force 制造及标量资格

真正释放后第一个 predictor 的实际 cell graph，先执行5个 scratch-only double velocity 场：translation；包含压缩/剪切的 full affine；isotropic compression；pure shear；rigid rotation。v=A*x+b 的生成 Gamma4 和 dv/d 的形成误差显式进入 forward bound；M/N 正和误差 Gamma(3degree)、target 正和 Gamma(8degree)、scaled inverse 和 solve 残差均计入。q 界用消去前 ProductScale=|L|*|d|，不是抵消后 |Ld|。每边 q 和合成 node-force/LS forward 界 finite 且通过才是 affine-null 资格，不能直接把双精度合成场当严格无误差实数仿射。

同一 device Limiter 的8个 scalar fixture 覆盖 s/q 四种符号、两种 tiny 阈值及两个零，检查 expected double bits、amplitude cap 和 a*s<=0。它们不形成真实 stage calls。必须先5制造+8 fixture全部通过，才允许真实 mode0 的 Ace commit。

MFG Add(mode,false) 仍计算 hypothetical float-Ace candidate 及 committed_* 数值作为反事实证书；它们不是实际提交，r.committed=false，不计 Pre/Cor commits。真实 mode0 的所有成功 stage 都内部检查并更新各 phase running maxima；CSV 每 Save 只写最新 Pre/Cor，不可由182快照声称重建180000个内部 stage。

## 精确侧车接口

Policy: C08H18RadialResidualPolicy.json，schema3，operator=compression_only_radial_residual_limiter，main_schema=C08H18Radial87-r1，main_columns87、manufactured_columns57、fixture_columns6、manufactured_mode_count5、limiter_fixture_count8。其余 clock/physical scope 为真实原 source 配置，native_22_schema_changed=false。

Main: C08H18RadialResidual.csv，26个通用阶段计数/时钟字段 + directed_edges/reverse_memberships + header 宏定义的45指标 +14个 running ratios。原26前缀的 last/running lambda 是新 radial lambda_upper，不能称旧 vector contraction；force_stage_time 为真实原 TimeStep，两阶段一致。

Manufacture: C08H18RadialManufactured.csv，5前缀+2图计数+45指标+5状态=57列，正好5行。Fixture: C08H18RadialLimiterFixtures.csv，fixture,s_m_s,q_m_s,a_m_s,expected_a_m_s,pair_power_unit_beta_alpha，8行。OFF 四文件均不存在。未来 Debug2:4 main+5 MFG+8 fixtures；未来91保存窗:182 main+5+8，最后 Pre/Cor calls/commits各180000。任何窗口都需根后续独立准入，本资产不包含 owner/求解器/读取器或自动接其他 ψ。

## 限制与下一决策

旧 CPU ten-state 结果为 mixed：末态6918/6967更少向内，但首 P42 6964/7012 all-neighbor rddot 可能变差；本 GPU 迁移不因此证明修复。实际 AS 保持 dynamic caller rhop=1 的 raw-Pa 张量，不重标单位。没有压力 filter/clip、beta/TPI、材料/接触/边界改变、α扫描、PRE重新计算或自动全程；需要实际 OFF/Debug/Release实施证据和根独立物理判断后，才可能考虑单条新的受控轨迹。

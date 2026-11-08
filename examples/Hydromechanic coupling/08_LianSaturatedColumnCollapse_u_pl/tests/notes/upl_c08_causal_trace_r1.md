# C08 n3 causal stage observer（源码作者稿，未构建/执行）

仅改 `src/source/C08StageTrace.h`、`JSphGpu.cpp`、`JSphGpu_ker.cu`、`JSphGpuSimple_ker.cu` 与本说明。新 note 事前不存在且精确 git ls-files 为空。没有修改物理公式、ReturnMaterial 参数、任何 XML/public flag、积分/接触政策、旧程序、PRE、reader 或输出。观察失败抛异常；原 MaterialError/J/finite 检查先后保留，新增阶段观测异常会先释放借用的 mov scratch。

所有新增代码嵌套在 `C08_STAGE_TRACE` 与 `C08_CAUSAL_TRACE` 同开条件内。关闭新宏时，旧57列、IDs5809/4956/4959、.66采样与旧 `C08StageTrace.csv` 写出分支保持原文；正常构建不产生新接口或数值运算。新宏只用于独立测试构建，不是公开 XML 算法选择。

## 固定观察范围与两CSV

三ID固定顺序为 **7017,5944,6814**。范围为实际 global step `[4000000,4360000)`；每40step输出，另在 `[4316000,4324000)` 和 `[4332000,4340000)` 每步输出，共24600个window采样step。时钟始终来自真实 TimeStep，dt来自实际调用，不用 n×dt 或整数10代替。dense区约对应τ.79–.81/.83–.85，但实际τ必须减同一PRE实际时钟。

`C08CausalTrace.csv` 是新97列：原57列作为前缀；追加材料 status/commit、实际 Ibase/Itrial/Ireturned、κold/candidate/saved、迹运算预算、实际K、trial更新恒等式/预算；实际Σrate六分量与迹；Jbase/Jhalf/Jnew/θstage/p_n；plane前后 move/v 及x/z命中和负法向速度清零标志。Σrate顺序统一 **xx,yy,zz,xy,yz,xz**。RHS从真实 `tsymatrix3f *Rsigmag` 命名成员读取；Simple原float2布局显式映射为 `sa.x,sb.y,sc.y,sa.y,sc.x,sb.x`，不reinterpret成另一张量布局。SOILSCTE.ModulusK/CTE.modulus_K记录实际float值（本例19607844Pa），不代入理想E/ν重新计算。

保留原 RHS=1、UPDATE=2、PONDING=3，新增 MATERIAL=4、PLANE=5。新材料事件分别来自真实Pre/Cor ReturnMaterial调用；plane事件来自原ProjectLowerPlane前后实际变量。各事件三行、各ID hits=1；不适用字段留空。正常每采样step共9events×3IDs，真实额外leading/trailing ponding保留，不能凭估计行数删除。旧57列checker不可直接使用新CSV。

`C08CausalTotals.csv` 是新56列的小累计表，只在原 `ParticlesDataDown` 下载点读取三ID累计快照；count未改变不重复写，文件已存在时拒绝覆盖。关键字段：`completed_step,native_id,last_step_start_s,last_operator_dt_s,sum_cor_dt_s,material_pre_count,material_cor_count,plane_pre_count,plane_cor_count,errors`。另保存Pre/Cor各8个status计数、x/z投影与速度清零次数、投影Δv累计、下面的Cor积分及预算。step_start是最后真实Cor调用起始时钟，绝不冒充完成时钟；`sum_cor_dt_s`逐次actual dt相加。

Debug10更新/final1frame应使每ID四种count均10；Release.90/90frames末应为360000，completed分别4000010/4360000。完整window最后未被主CSV采样的步骤仍计入Totals。观察器校验各ID四count/status总数一致、pending顺序/真实step对应、最大360000和errors0；后续独立run/check必须要求其计划的最终10或360000，不能拿中间累计前缀冒充完整证据。所有97列数据及累计数值目前都尚未执行产生。

## 全阶段累计与J真实链接

Simple TU有独立 `__constant__` context、三record、三累计对象；不跨TU调用device函数，不复制CTE，不新增Np数组/cudaMalloc。第一次step4000000的Pre MATERIAL开始时清零累计一次。每个范围内Pre/Cor与plane调用均启动context；稀疏输出条件仅控制record/下载，不控制累计。每阶段清record不会清累计；Pre不会重置Cor的sum或budget。

Cor材料调用前读取实际sigmapre三个对角形成Ibase。第一次Cor保存initial_I，每次保存last_returned_I；另计相邻Cor Ibase与上次返回迹不相同的 `base_trace_changes`，该计数只描述是否存在未观测的迹改变，不据此修改状态。

每次实际Cor累加：`sum(dt*trace(Rsigma))`、`sum(Itrial-Ireturned)`、绝对drop、局部迹运算预算、actual dt、trial更新恒等式及其预算。Pre仍记录返回κcandidate，但随后独立在原 `kplastic[p]=kplasticnew` 保存点读取实际κsaved，明确证明旧κ恢复；Cor同样从原保存点记录κsaved。没有重复调用ReturnMaterial或从κ猜塑性体积。

Cor MATERIAL读取真实 `PoroJPreg`(Jbase)、`PoroJg`(Jhalf)和θh，保存在按ID索引的三slot pending中。原 `ComputeSymplecticPorosity(true)` 完成并释放PoroJPreg后，Cor PLANE读取当时真实PoroJg(Jnew)，按同step/dt链接累计 `log(Jnew/Jbase)` 与 `dt*θh`。不在旧pointer释放后读Jbase，不另算Jnew，不借ρ缓存反推。Pre plane不进入Cor体积累计。

plane记录基于原 `pos+move<=plane` 和原负法向v清零条件，原两次ProjectLowerPlane调用与所有写回原文保持。Δv仅是投影前后速度差及累计，**不是已闭合接触反力**，不反馈Ace、Darcy、J、σ或压力。

## 运算预算与科学解释

令u=DBL_EPSILON/2、γm=mu/(1−mu)。局部 `trace_drop_roundoff_budget_Pa=γ5*(Σ|trial_diag|+Σ|returned_diag|)`只覆盖两次三项迹与一次相减的算术；不代表整个材料返回/root residual误差。局部trial更新预算取 `γ16*(Σ|base_diag|+|dt|Σ|Rsigma_diag|)`，涵盖三个实际trial multiply/add、各迹、dt×迹与恒等式相减；同时保存 `(Itrial−Ibase)−dt*trace(Rsigma)`。这些是事前运算数/绝对scale预算，不按运行结果放宽。

Totals保存上述局部预算之和，并加γN绝对累计误差；endpoint检查量为 `sum(dt*trace(Rsigma))−sum(Itrial−Ireturned)−(Iend−Iinitial)`。其预算还包括最终几次加减的γ4项。若base_trace_changes非0，不能把该endpoint差全部解释为舍入。预算仅输出、不作为新的物理拒绝阈值。累计logJ与累计dtθ不必逐bit相同：原J更新是既有显式离散，不是指数精确积分。

ψ0下Smooth在实数数学中保迹，TensionRepair可产生体积返回；其 `Δεv^p=(Itrial−Ireturned)/(3K)` 是材料迹变化，不是压力RHS新增源。压力/J仍由总θ与既有Darcy率推进，不能再把该塑性体积加进J。原57项继续区分compression、LP/Taylor或FS-Ace、divAce及grad-k链项；Σrate迹与doubleθ的差包含原float梯度/应力率与自旋舍入，不先宣称bug。

该observer只证明三ID实际阶段序列和累计闭合。它不能独自得到所有邻居的约束反力散度、全场因果或压力谱，也不能凭负p/近对直接区分tensile与kernel pairing。原ReactionClosed=false、CompletedOnly、AS.2/n3与物理未验收状态保持。构建、Debug10内存检查、Release.90求解、native与CSV检查均须由root另行实际执行；本轮未执行任何一项。

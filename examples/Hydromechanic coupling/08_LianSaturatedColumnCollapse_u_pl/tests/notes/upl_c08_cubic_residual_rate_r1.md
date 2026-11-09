# Cubic非嵌套LS残差：瞬时力率影子（作者稿）

本稿生成时未执行。只新增 `support/upl_c08_cubic_residual_rate_r1.py`；未来只读已通过 true causal90 原生导出的 part13/14，各一次，不读BI4或trace，不调用force/材料/过滤器，不改生产源码、PRE、正式输入或保存态。

参考封存 `upl_c08_bedkeep_source_r1/source.zip` 内 `JSphHourglassCpu.cpp:127–159,199–214` 的匹配LS与非嵌套残差数学，不调用旧HG类。对全部5000土粒，以2h大小bucket及完整相邻3×3 bucket枚举每条 `i<j,r<2h` 边一次，无trial cutoff、自由面删点或固定墙伪速度。h来自真实生成XML，G来自冻结真实Run.out的float Shear Modulus（7518796.5Pa）。使用正Cubic权 `w=-W'(r)/r` 的解析式（零距离有有限极限），不是W，也不换Wendland。

对每点构造 `M_i=ΣV_j w d dᵀ`、`B_i=ΣV_j w dv dᵀ`、`L_i=B_i M_i⁻¹`，d=xi−xj，dv=vi−vj；无截距。保存所有点的SVD奇异值、数值秩、条件数及法方程缺陷；不按条件数删点、不正则化。精确零奇异值无法无正则求逆时明确失败并保留原因，不静默跳过。与前次带截距、W权的soil-only localfit不同，不能借用它的L。

unit xi=1：`β=G V_i V_j w`，`r_i=dv−L_i d`、`r_j=dv−L_j d`，`ḟ_ij=−β(r_i+r_j)/2`；对两端等量反向累加，`ȧ_i=ḟ_i/(ρ_i V_i)`。V数值为2D单位厚度面积（原生字段名仍volume），m′=ρV为kg/m，ḟ为N/(m·s)，ȧ为m/s³；`Σv·ḟ`及form为J/(m·s²)，不是实际耗散功率。保留原生实际V/rho，不能猜dp²或把旧HG的M0归一化当本影子的当前惯性。

匹配LS下冻结几何的恒等式为 `P=−2E`，`E=.25Σ_edges β(|r_i|²+|r_j|²)`。有限精度显式报告 `D=Σ_i G V_i L_i:N_i`、`N_i=Σ_j V_j w r_i dᵀ`，因此 `P+2E=−D/2`（加累加舍入）。脚本预先固定操作数包络 `k=64(N+edges+maxdegree+1)`、`γk=k eps/(1−k eps)`，以未抵消的配对功率/能量项构造累加预算，并把实测LS法方程缺陷D/2单列，不能把它隐藏为物理容差或冒称完整SVD误差定理。保留原始P+2E及法方程相对缺陷；内部代数失败不改预算重试。

配对力率不是逐边中心力。完整匹配图的法方程亦使总力矩率消失；脚本实际报告原点总力矩、配对力矩、净力及相应浮点/法方程证书，不凭逐边中心性假定角动量守恒。这里2D力矩定义为Σ(x ḟ_z−z ḟ_x)，物理y分量为其负值。若以后改变pair G/塑性γ、删边或遮罩，必须同步进入匹配LS权重，否则本功率/力矩证明失效。这里G完整弹性、无实际塑性γ，仅是瞬时弹性上界影子；没有历史积分、有限旋转、体积/质量变化导数或实际GNOG实现。

报告保守冻结刚度上下文 `λ_bound=max_i 2Σ_jβ/m′_i` 与τ=1/√λ；xi=.2只作线性缩放的假设τ和原dt/τ，不作为耦合步长通过门。常量、一般仿射、刚体旋转速度在同实际几何上作制造检查，精确数学预期力率为零，数值误差仅描述，不设5Pa/物理阈值。

输出浅路径四CSV：`_summary`2态、`_particles`10000点（LS/应变/力率及真实p/σ/κ/J/n/k/FS）、`_pairs`四条全邻域相对径向jerk、`_manufactures`6行；`_rates.png`为两态×首对/控制对局部位置及全图共用标尺的力率/jerk箭头，实际孔压共用色标。独立 `logs/upl_c08_cubic_residual_rate_r1.check.json`；拒绝覆盖，不自动下一步。根全文审后才可一次运行：`D:/anaconda3/python.exe -B tests/support/upl_c08_cubic_residual_rate_r1.py --execution-authorized`。

# Cryer：延迟排水前的封闭Darcy离线核查

## 范围与产物

仅新增 `tests/support/cryer_darcy_closed_r1.py` 与本说明，先供主代理全读，不运行。默认help；显式 `--run` 才生成新的 `tests/logs/cryer_darcy_closed_r1.check.json` 和 `tests/figures/cryer_darcy_closed_r1_metrics.csv`。拒绝覆盖，不启动GenCase/求解器，不改生产源码、正式输入、原始输出或Git。`physical_acceptance`始终false。

只用已封 `cryer_grad_peak_r1` Part0的double位置、原生rho/mass/h及37173个土粒子，排水inactive、重力0，全部土粒子均为压力率接收点。不使用更改布局，也不把初始FSType2/3孔压强置0。dummy8远在支持域外，当前球无外部水力ghost交换对；这并不自行证明连续零通量或流体总量守恒。

## 矩阵和常数先决审查

生产CPU `ComputeFreeSurfaceTracking` 调用3D `ComputeFSParticlesFreeSurface`（JSphCpu.cpp:1151），构造 `M_i=-sum V_j d_ij outer g_ij`（:724–739）并取inverse（:639–656）。GPU同定义见JSphGpu_ker.cu:834–862。孔压率直接使用该CorrMat（CPU:2318、GPU:2033）；它不是 `SoilStressRateGradCorr` 的另一种矩阵，也不由这个开关启闭。旧helper `correction` 正是同一数学定义；当前几何矩阵非奇异，umbrella只改FSType、不改矩阵。两者不声称实际生产float舍入/求和0ULP。

复用旧helper的批次和correction，不修改它。生产常量为 `bwen=float(-2.08891/h^4)`（FunSphKernel.h:198–199）、`Eta2=float((h*.1)^2)`（JSph.cpp:1632），h为原生float提升到double的值。helper原梯度是double `-2.08891/h^5`；新脚本施加统一常数比例s，使梯度使用真实bwen。另生产 `vol2=double(MassFluid/rho_float)` 的除法先在float中完成，本均匀rho/质量球的算子体积与double `m/rho` 差一个统一比例sv。因此使用 `C_helper/(s*sv)`，即 `M_real=s*sv*M_helper`，Darcy累加也使用相同float除法体积。体积积分指标仍按double native `m/rho`，两种体积及比例并列记录。不是把不同算子的矩阵硬拼在一起。sqrt、qq、poscell及邻居次序仍按离线double，不称作生产位级回放。

材料Kw、n、k、rho_w从绑定XML读取并按float存储。CPU使用 `double(Kw)/double(n)` 及零重力替代g=9.80665；GPU的Kwn和g先存float再提升到double（JSphGpu.cpp:770、773）。因此两组标量因子分别记录，但不冒充实际CPU/GPU程序对照。无重力水头项。

## 公式、反向符号和制造场

按CPU:2478–2487、GPU:1827–1836，定义：

```text
H_i,ij = d_ij dot (C_i g_ij)/(r_ij²+Eta2)
pdot_D,i = c sum_j V_j (p_i-p_j) H_i,ij
c = (Kw/n)*2k/(rho_w*g)
```

交换端点时d和g都反号，所以 `H_j,ji=d_ij dot(C_j g_ij)/(r²+Eta2)`；压力差另反号。无序对给j的贡献为 `-c V_i (p_i-p_j) H_j,ji`，不是把接收点Ci复用于两端。若体积定义一致，体积加权对合量为 `c Vi Vj (pi-pj)(Hi-Hj)`，一般不必抵消；本脚本为同时保留native积分权重与真实float算子体积，逐对使用一般式 `c (pi-pj)(Vnative_i Vop_j Hi-Vnative_j Vop_i Hj)`。均匀体积舍入比例只带来公共sv，不破坏raw/symmetric对的抵消。Ci不等于Cj并不保证其收缩一定非零，必须计算真实结果。

制造场为常数10000 Pa，以及 `p=P(1-r²/R²)^2`（P=10000 Pa）、该四次场整体加10000 Pa。四次场在r=R的径向导数 `-4Pr/R²(1-r²/R²)` 为0，连续laplacian为 `-12P/R²+20Pr²/R^4`，其理想球体积积分为0。常值场也实际逐对累加，不能硬赋0；加常量用于零点不变性诊断，不是新的力学加载状态。

同一几何/孔压/参数下对比当前接收点Ci、raw I以及对称 `(Ci+Cj)/2`。后两者只作离线代数反例，不标为生产候选通过；平均矩阵是放在每条pair的同一H上，保持两端系数相同。

## 指标和解释

逐组记录 `sum Vi pdot`、`sum Vi abs(pdot)`（Pa·m³/s）、归一体积平均率/RMS/范围（Pa/s）、有符号及绝对relative drift。独立记录逐对预期积分及与实际节点累加的差，不把任一积分预置0。压力二次泛函 `F=1/2 sum Vi p²`（Pa²·m³）及变化 `sum Vi p pdot` 分别列出；除以Kwn后给孔隙压力储能J和变化W。所有体积是固定初态 `m/rho`，不是耦合流体质量或总能量。

恒压null、基线平移和反向符号是实现核查；守恒、耗散、局部误差和连续边界一致性是不同问题。不能凭对称/原始算子净漂移小就自动合入，也不将接收点漂移直接称作真实外流。该阶段结果先供审阅，再决定是否可做连续fresh的ramp持载开排水短窗。

```powershell
D:/Anaconda3/python.exe -B tests/support/cryer_darcy_closed_r1.py --run
```

脚本绑定新文件和说明、已封radial初态/依赖清单、当前相关源码、程序、原文及reader，检查前后哈希。仅输出小JSON/CSV，无大逐粒子文件或图，不推进旧弱阻尼峰窗或任何后续流程。

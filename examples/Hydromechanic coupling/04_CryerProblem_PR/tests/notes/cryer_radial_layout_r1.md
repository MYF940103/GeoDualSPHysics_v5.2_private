# Cryer：原A离散的零阶项与初始布局对照

## 范围及文件

仅新增 `tests/support/cryer_radial_layout_r1.py` 和本说明，先审阅，不默认执行。显式 `--run` 才读取原生数据，生成新的 `tests/logs/cryer_radial_layout_r1.check.json` 与 `tests/figures/cryer_radial_layout_r1_metrics.csv`；拒绝覆盖。没有物理求解、编译、源码/正式输入修改、旧结果改写或Git操作。

前置为已完成的 `cryer_radial_patch_r1` 离线记录。复用该脚本的解析球对称场及旧配对helper，沿用并复核其所有程序、源码、PDF/MD、reader、Part0和配置身份哈希，不修改已封文件。q固定10000 Pa、P/q固定1.2，R=.05 m、dp=.0025 m及同一初始均匀rho=2100 kg/m³。不是调P或q以匹配输出。

## A的精确代数拆分

在等密度下，定义 `Ttilde_i=S_i+(q-p_i)I`、`V_j=m_j/rho`，当前A可写为：

```text
a_i = (1/rho) sum_j V_j (Ttilde_i+Ttilde_j) g_ij
    = z_i+d_i
z_i = (2/rho) Ttilde_i sum_j V_j g_ij
d_i = (1/rho) sum_j V_j (Ttilde_j-Ttilde_i) g_ij
```

脚本保留原helper的应力、外载、孔压三个数组分别累加，独立计算z、d，再核对 `z+d` 与原A总和仅有双精度求和舍入差；另核对z与单独累加的核分区梯度 `sum(V_j g_ij)` 构造值。代数舍入预算明确以机器epsilon、邻居数及项幅值计算，不是放松力精度门槛。三者不预先硬赋0。

每一无序邻居对若 `g=g_ij`，对j的z贡献为 `-2 V_i Ttilde_j g/rho`，d贡献为 `+V_i(Ttilde_j-Ttilde_i)g/rho`。符号分别保留，不将差分项错误处理为反对称配对。差分项单独通常不守恒；其净力由零阶项抵消后，完整A才恢复原配对守恒。

统计中心、完整支持内区 `r<R-2h`、外壳和全体；FrDraw另统计真实初始FSType2/3，不为虚拟布局伪造FSType。每区给出原A、z、d及重组的RMS/max，z·d交叉项、抵消程度、核分区梯度、邻居数及半径范围。JSON保留每项净力/矩和几何/native体积仿射功归一化。零阶项与差分项可能很大且抵消，不把它们各自RMS称作可相加的误差贡献比例。

## 虚拟Cartesian截球

只生成内存中的原点居中整数网格 `x=dp*(ix,iy,iz)`，保留 `|x|<=R+1e-12 m`。R、dp、h、单粒子质量和rho与原生初态相同，不做总质量或体积缩放。保留实际节点数、`sum(m/rho)`相对几何球体积、几何表面节点数和内外区节点数。两布局的中心均按同一物理 `r<=dp+1e-12 m` 选取；FrDraw是已有18个ID，无r=0节点，而Cartesian包含原点且节点数可能不同。脚本明确报告这些观测差别。

该虚拟布局不是新GenCase输入、不是动态轨迹，也不与FrDraw一一材料点等价。它同时改变节点数、体积求积、中心采样和表面支持截断，不能仅凭RMS变化就证明“粒子无序”是唯一因果。初始表面支持截断也不是随时间产生的无序；本阶段不重新运行shifting或任何积分。

差分力能消去常值场响应，但在截断邻域中也删去共同应力关联的边界牵引，通常还失去成对线动量守恒。不能把 `difference_only_diagnostic` 当作可以直接合入生产的修复；需要与边界通量及内力梯度成套一致的独立设计和验证。

## 审阅后执行

```powershell
D:/Anaconda3/python.exe -B tests/support/cryer_radial_layout_r1.py --run
```

本阶段仅输出小JSON/CSV，不生成每粒子文件或图。`analysis_checks_passed`仅指身份、制造场及拆分实现检查，`physical_acceptance`始终为false；不会自动启动后续求解。

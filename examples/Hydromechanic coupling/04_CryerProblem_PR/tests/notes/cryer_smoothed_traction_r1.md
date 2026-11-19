# Cryer 球面的守恒应力积分对照

在相同的 37,173 个材料点上，用排水后 42.96875 ms 的解析孔压和有效应力，测量将两者代入动量方程后剩余的离散加速度。时间取自服务器保存的峰值帧 Part 416，球心指标沿用初始半径 2.5 mm 的 18 个材料点，所有结果均除以原生粒子质量。

| 空间离散 | 中心 RMS (m/s²) | 整球 RMS (m/s²) | 排水面 RMS (m/s²) |
|---|---:|---:|---:|
| 现有核梯度 | 91.405 | 10.147 | 13.247 |
| 原成对修正力学试验 | 76.181 | 10.713 | 20.902 |
| 球壳子域积分，面上用局部线性插值 | 0.030 | 2.372 | 1.365 |
| 球壳子域积分，外面只用三角形顶点 | 0.030 | 3.352 | 2.831 |
| 独立线性四面体与表面牵引 | 0.180 | 0.234 | 0.504 |

两种球壳积分在中心的残余最小，四面体在整球和排水面表现更好。因而保留四面体作耦合对照具有独立依据。在三种已计算的时刻，球壳积分的较大残余集中在外部几层。[材料壳层及三个时刻](../figures/cryer_smoothed_traction_r1_shells.csv) · [同尺度对比图](../figures/cryer_smoothed_traction_r1.png) · [仅用表面节点的逐壳结果](../figures/cryer_smoothed_traction_r1_surface_nodes_shells.csv) · [四面体的独立核验](cryer_tet_weak_force_r1.md)

## 做功与体积

用实际外层粒子的 5,153 个方向构造闭合三角面，向内划分 20 层，共 206,040 个积分子域。每个子域的应力由原始粒子插值得到。取子域应力与真实定向面面积相乘，在共享面合并相邻子域的贡献，再用和速度插值相同的权重转回材料点。于是应变功和节点力功互为伴随。积分应力取有效应力减孔压，加上恒定围压对应的各向同性项；独立恒应力测试还显式加入了表面牵引。

对包含二次项的非均匀虚速度，独立计算的内力功与材料点力功最大差为 4.71×10⁻¹⁴ W。两种外面插值给出相同的仿射荷载功 313.805216 W。当规定外球面虚速度严格为零时，整体插值把外力分配给 17,646 个节点，得到 −0.671086 W；仅向面片顶点分配后，恰好 5,153 个节点受力，面功为零。这个对照采用几何牵引与规定速度，数值为虚功率。[表面独立试验](../logs/cryer_smoothed_traction_r1.surface.json) · [原核载荷的独立检查](c04_surface_work_r1.md)

球壳几何积分体积为 0.00052300869 m³，原生粒子体积和为 0.00058082810 m³。所有节点几何积分权都为正，几何权与原生粒子体积的比值介于 0.601 和 0.986。转入力学或水力方程时需要明确区分惯性质量、应变功体积和储水体积。这里测的是给定解析场的空间平衡；瞬态精度仍由独立的耦合峰值检验判定。[守恒与积分权记录](../logs/cryer_smoothed_traction_r1.check.json) · [严格表面牵引记录](../logs/cryer_smoothed_traction_r1_surface_nodes.check.json)

## 复现

在 C04 根目录运行。第二个命令单独检查外面虚功，第三个命令将试函数和节点外力一起限制到外壳顶点。

```powershell
$serverOutput = 'CaseCryer_TPI_P3_nu030_peak_r1_GPU_out/CaseCryer_TPI_P3_nu030_peak_r1_GPU_out'
& 'D:/anaconda3/python.exe' -B tests/support/cryer_smoothed_traction.py $serverOutput
& 'D:/anaconda3/python.exe' -B tests/support/cryer_smoothed_traction.py $serverOutput --exterior-work
& 'D:/anaconda3/python.exe' -B tests/support/cryer_smoothed_traction.py $serverOutput --boundary-nodes
```

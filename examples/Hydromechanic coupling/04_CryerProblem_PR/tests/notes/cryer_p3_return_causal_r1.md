# Cryer P3 服务器峰窗的压力与力学诊断

真实数据来自 RTX A6000、固定步长 1.9073486328125 µs 的 ν=.30 三轮 TPI 峰窗。原生与方法审查通过，模型幅值低估 1.5177%，峰时滞后 2.4955%；原有全程准入要求这两项分别达到 1% 和 2%。中心固定 18 个材料点，球半径 50 mm，外表面施加围压 10 kPa。[峰值曲线、逐帧数据与原验收](../../figures/cryer_tpi_p3_nu030_peak.md)

## 同时钟的压力、应力与体积

在真实 TPI 峰值帧 416，排水已开 42.96875 ms。TPI 比显式 u-pl 的中心孔压高 35.73 Pa，两个参考解 M0 与有限 Kw 在此时本身即相差 39.02 Pa，因此两种方法相对各自解析解的误差只相差 −3.29 Pa。相同 475 个 Mandel 窗口时刻，两条模拟曲线之间 RMS 为 33.99 Pa；各自对理论的 RMS 为 190.12 Pa（TPI）和 186.71 Pa（显式）。[同钟中心 CSV](../figures/cryer_p3_server_peak_actual_r1/physical/matched_center_diagnosis.csv)

TPI 中心原生 J−1 为 +0.035258%，相同 18 点包围体积缩小 0.035258%。从内向外第 3–6 个闭合材料壳的体积变化依次为 +0.0820%、−0.0741%、+0.0698%、−0.0830%。用相同 37173 个初始位置、相同材料 ID、相同三角面重新计算显式 A，对应为 +0.0802%、−0.0755%、+0.0681%、−0.0843%。三帧只选取必要的实际位置、应力、压力和 J 列作补充空间诊断；峰窗本身已用原资格程序完整读取一次。[同壳形变图](../figures/cryer_p3_server_peak_actual_r1/physical/matched_material_shells.png) · [逐壳数据](../figures/cryer_p3_server_peak_actual_r1/physical/matched_material_shells.csv)

## 同一粒子状态下，只替换驱动骨架的孔压

从保存的当前位置、双精度有效应力、J 导出的体积和密度重建三项力。核为原 Wendland，支持半径 2H。对一对土粒子，合力为

`Fij = Vi Vj [(σ′i + σ′j) + (2q − pi − pj) I] ∇iWij`。

原模型的有效应力进入动量算子时先投影到 float。实际原生三项剪应力按 xy、yz、xz 保存，r2 的独立基矢试验核验了全部九个矩阵分量。先用原生孔压重建，再只将内力公式中的 pi、pj 替换为同一保存时刻、同一初始材料半径的球对称 M0 解析孔压。表面激活排水时解析和数值孔压均为零。成对等大反向力、端点材料质量和外载保持原定义。此处计算保存时刻的应力、孔压和围压合成加速度；粘性、阻尼及未保存的预测/校正子步没有纳入。

| 保存状态 | 原生孔压下中心矢量 RMS（m/s²） | 换 M0 后中心矢量 RMS（m/s²） | 换压引起的中心平均向心加速度变化（m/s²） |
|---|---:|---:|---:|
| 开排水前，Part64 | 0.1042 | 0.0639 | +0.0369 |
| 峰前，Part139 | 0.1345 | 13.8132 | −12.3462 |
| 峰值，Part416 | 0.0301 | 8.7429 | −7.8099 |

峰值时全体矢量 RMS 由 0.0825 增至 1.7698 m/s²，内十壳的交替分量 RMS 由 0.0198 增至 0.4672 m/s²；负向心表示向外。交替分量用相邻三壳的中心二阶差分计算，先消去局部常数和线性径向趋势。三帧的成对压力替换净力均小于 3.54×10⁻¹⁵ N，净力矩小于 2.8×10⁻¹⁸ N·m。重建围压与原生 LoadAce 的矢量 RMS 差为 0.00036–0.00038 m/s²，原生量级为 585–586 m/s²。双精度距离与按无序粒子对累加使此观测具有明确的数值重建误差。[壳均加速度图](../figures/cryer_peak_momentum_shadow_r2.png) · [区域 RMS](../figures/cryer_peak_momentum_shadow_r2_regions.csv) · [固定 18 个 ID 的 XYZ 力和径向分量](../figures/cryer_peak_momentum_shadow_r2_center18.csv) · [20 层径向与交替分量](../figures/cryer_peak_momentum_shadow_r2_shells.csv)

这些数据表明，压力和应力均偏离连续参照时，二者与围压在当前离散力中仍接近平衡。只提高峰值附近的孔压会在原应力场上产生清楚可辨的向外力。真实积分会允许骨架应力继续响应，因此这些冻结帧不能给出下一次耦合计算的峰值或误差改善量。旧 r1 分解误读了剪应力存储顺序，其指标已单独作废。[r2 核验](../logs/cryer_peak_momentum_shadow_r2.check.json) · [r1 作废说明](../logs/cryer_peak_momentum_shadow_r1.rejected.json)

## 下一项对照的取舍

下列离线复现命令在 C04 根目录执行。两个参数依次为服务器原始输出根目录和此前完成的原生峰值审查目录。脚本保护已存在的同名图表；复现时在独立工作副本中生成。

```powershell
$serverOutput = 'CaseCryer_TPI_P3_nu030_peak_r1_GPU_out/CaseCryer_TPI_P3_nu030_peak_r1_GPU_out'
$peakReview = 'tests/figures/cryer_p3_server_peak_actual_r1'
& 'D:/anaconda3/python.exe' -B tests/support/cryer_peak_momentum_shadow.py $serverOutput $peakReview
& 'D:/anaconda3/python.exe' -B tests/support/cryer_peak_paired_manufactured.py $serverOutput $peakReview
```

- 原质量和球半径不变，将内部 19509 个粒子作最多 0.25dp 的确定性径向交错，同时保留中心 18 点、最外四层以及逐壳总质量、平均半径和质心。在内十壳的 2dp 制造场上，梯度响应由 −0.0404 变为 +0.0072，仍近乎为零。最小间距从 0.765dp 降至 0.528dp。这个布局不值得直接送长算。[布局对照](../figures/cryer_shell_stagger_r1.csv)
- 保留原粒子布置，仅在相同制造场的梯度计算中将 H 从 1.8dp 减至 1.5dp。16dp 波长响应从 0.8953 提高到 0.9243，但 2dp 交替场的反号响应由 −0.0404 加剧至 −0.2476。此项没有改变真实 Darcy、边界、核或积分步长，现阶段也不能推为正式设置。[支持半径对照](../figures/cryer_shell_h15_r1.csv)
- 下一项有区分力的服务器试验是单一峰窗的诊断性单向耦合。保留同一压力演化、10 kPa 外载、粒子分布、质量、材料和输出计划，只在开排水后的骨架动量计算中读取对应力阶段准确时钟的 M0 压力，单独保留内生 P3 压力及其三轮记录。先检验关闭此旁路时逐字段回归，检查开排水前原状态、第一开排水步与所有真实排水接收点。若已知压力驱动下壳层交替与 J/形体差异仍存在，说明力学空间离散足以产生该现象；若明显缩小，则需追踪压力反馈通路。指定的压力只可用于区分原因，该次结果不能替代求解孔压的正式验收。

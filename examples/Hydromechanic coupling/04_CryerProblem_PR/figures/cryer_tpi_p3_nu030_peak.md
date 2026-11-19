# Cryer ν = 0.30 三轮 TPI 峰值对比

RTX A6000 实算覆盖排水前加载至排水后 62.5 ms。577 帧、37,181 个原生 ID、22 个数组、3 轮压力与 5 阶段步长检查通过。Mandel 窗口含 475 个实际保存时刻，中心取初始半径 2.5 mm 的固定 18 个材料点。

| 方法 | 模拟峰值（Pa） | 各自理论峰值（Pa） | 幅值误差 | 开排水至模拟峰值（ms） | 峰时误差 | 窗口 RMS（Pa） |
|---|---:|---:|---:|---:|---:|---:|
| 三轮 TPI，M0 参照 | 12,289.15 | 12,478.53 | −1.5177% | 42.969 | +2.4955% | 190.12 |
| 显式 u-pl，有限 Kw 参照 | 12,253.45 | 12,439.18 | −1.4931% | 43.091 | +2.4708% | 186.71 |

TPI 的时间采样和相对显式 A 的幅值比较通过。峰值幅度未达 1% 门槛，峰时偏差 1.0462 ms，超过既定 0.8385 ms 上限。本次审查保留峰窗拒绝记录，1 Tv 全程仍待后续候选通过峰窗。

| 图与核查内容 | 数据 |
|---|---|
| [中心孔压对数坐标图及启动段](../tests/figures/cryer_p3_server_peak_actual_r1/physical/cryer_center18.png) | [577 帧中心孔压、解析值、应力、位移与排水记录](../tests/figures/cryer_p3_server_peak_actual_r1/physical/native_and_theory.csv) |
| [径向孔压和首个开排水保存帧](../tests/figures/cryer_p3_server_peak_actual_r1/physical/radial_pressure.png) | [按初始材料半径分箱的孔压及实际自由表面状态](../tests/figures/cryer_p3_server_peak_actual_r1/physical/radial_pressure.csv) |
| [显式与 TPI 的同钟壳层孔压误差和真实形变](../tests/figures/cryer_p3_server_peak_actual_r1/physical/matched_material_shells.png) | [20 壳固定材料 ID 与闭合表面体积](../tests/figures/cryer_p3_server_peak_actual_r1/physical/matched_material_shells.csv) · [513 个共同保存时刻的中心数据](../tests/figures/cryer_p3_server_peak_actual_r1/physical/matched_center_diagnosis.csv) |
| [同一保存帧只替换孔压后的加速度](../tests/figures/cryer_peak_momentum_shadow_r2.png) | [中心、内十壳、全体与表面数据](../tests/figures/cryer_peak_momentum_shadow_r2_regions.csv) · [单因素分析及数据范围](../tests/notes/cryer_p3_return_causal_r1.md) |
| [孔压和有效应力一同施加解析场后的合力残差](../tests/figures/cryer_peak_paired_manufactured_r1.png) | [两种几何的四个分区](../tests/figures/cryer_peak_paired_manufactured_r1_regions.csv) · [20 个壳面的径向分量及 RMS](../tests/figures/cryer_peak_paired_manufactured_r1_shells.csv) |
| [离散残差的内核与表面来源](../tests/notes/cryer_p3_return_causal_r1.md) | [常张量项与邻点梯度项的分区分解](../tests/figures/cryer_peak_force_moments_r1_regions.csv) · [各壳的方向与协方差](../tests/figures/cryer_peak_force_moments_r1_shells.csv) |
| [原生、方法和峰值判定](../tests/figures/cryer_p3_server_peak_actual_r1/peak_rejected.json) | [三轮五阶段审查](../tests/figures/cryer_p3_server_peak_actual_r1/sidecar_review.json) · [连续和同步采样的理论峰值](../tests/figures/cryer_p3_server_peak_actual_r1/physical/physical_review.json) |

在 TPI 的峰值帧，两个方法的中心孔压相差 35.73 Pa，对应解析解本身相差 39.02 Pa。用各自参照比较，同钟压力误差仅相差 3.29 Pa。TPI 峰值帧中心 18 个粒子保存的平均 J−1 为 +0.035258%，这些粒子围成的真实材料体积却缩小 0.035258%。从第 3 壳到第 6 壳依次出现膨胀、收缩、膨胀、收缩，两种时间积分均出现相同的空间特征。[空间诊断与制造解](../tests/notes/cryer_shell_equilibrium_r1.md)

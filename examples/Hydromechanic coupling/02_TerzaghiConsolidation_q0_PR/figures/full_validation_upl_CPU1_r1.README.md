# u-pl 完整 2Tv 对比图与数据

计算：k=1e-4 m/s、dp=0.01 m、CPU1、dt=6.250143051147461 µs。实际终点72.88428689946836 s，Tv=2.0000000262。共1682个保存状态，全部原生数据和旧结果保留。

| 查看内容 | 图片 | 相应数据 |
|---|---|---|
| 孔压剖面、平均孔压、顶部材料沉降合图 | [总览](full_validation_upl_CPU1_r1_overview.png) | [剖面](full_validation_upl_CPU1_r1_profiles.csv)、[历史](full_validation_upl_CPU1_r1_comparison_history.csv) |
| 10个Tv剖面及后期放大，含1.5和2.0 | [孔压剖面](full_validation_upl_CPU1_r1_profiles.png) | [剖面](full_validation_upl_CPU1_r1_profiles.csv)、[实际取样时刻](full_validation_upl_CPU1_r1_profile_times.csv) |
| 完整孔压、顶部/底部材料沉降及后期误差 | [全程历史](full_validation_upl_CPU1_r1_history.png) | [当前历史](full_validation_upl_CPU1_r1_history.csv)、[参考](full_validation_upl_CPU1_r1_theory.csv)、[新旧对比](full_validation_upl_CPU1_r1_comparison_history.csv) |
| 启动段0–0.1 s | [启动段](full_validation_upl_CPU1_r1_startup.png) | 同上完整历史数据，没有平滑或删除振荡 |
| 应力、Q、交替X列模态、J、孔隙率和实际密度 | [诊断](full_validation_upl_CPU1_r1_diagnostics.png) | [误差历史](full_validation_upl_CPU1_r1_focus_history.csv)、[终点应力](full_validation_upl_CPU1_r1_final_stress.csv)、[完整100材料层历史](full_validation_upl_CPU1_r1_layers.csv) |
| 与旧u-pw逐Tv孔压剖面对比 | [新旧剖面对比](full_validation_upl_CPU1_r1_qualified_upw_profiles.png) | [对比剖面](full_validation_upl_CPU1_r1_comparison_profiles.csv)、[两组实际时刻](full_validation_upl_CPU1_r1_comparison_profile_times.csv) |
| 各参考下的终点误差与逐Tv剖面误差 | — | [终点汇总](full_validation_upl_CPU1_r1_summary.csv)、[逐Tv汇总](full_validation_upl_CPU1_r1_profile_summary.csv) |

H=1有限Kw参考下，终点同节点平均孔压58.6651 Pa，参考59.2253 Pa；原生节点孔压剖面RMS误差0.570510 Pa。顶部材料沉降3.683854 mm，参考3.673717 mm，相差+0.2759%；底部沉降绝对误差2.3409 µm，相对误差12.72%。逐Tv表采用100层均值的RMS，与1000个原生土粒子的RMS分别标识。Tv≈0.005时层均值RMS为114.615 Pa，之后逐渐降低，并非所有时刻均优于旧版。

Tv≥1的201个保存状态中平均孔压严格逐次下降，未出现本时窗内的晚期平台。仍保留底层总应力问题：最大误差110.576 Pa，226个t≥0.1 s状态超过旧正式版100 Pa精度标准。终点Q为18.8783 Pa，旧结果为10.1081 Pa。出图和原生检查通过不等于无条件物理验收。

理论曲线使用实际保存时刻，未拟合、插值或调整时钟。H=.995仅为独立敏感性参考。有限Kw及经典参考均不精确复现本轮动态惯性、斜坡与归一化2h外载带。旧u-pw为GPU/Vel0/dt=10 µs，本轮为CPU/FreeSlip/dt=6.250143 µs，框架、边界及排水事件时间也不同；新旧对比不能作单因素归因。

顶部外载的“模式5”是枚举值，不是固定五层粒子：实际规则为z>当前zmax−2h，初始覆盖四层。早期结论记录中的层数笔误已单独更正，没有改动计算、源码或保存状态。

生成脚本：[plot_upl_full2tv_r1.py](../support/plot_upl_full2tv_r1.py)。运行方式：在case根目录执行 `D:/anaconda3/python.exe -B support/plot_upl_full2tv_r1.py`。脚本保护现有目标文件；已生成结果请直接使用，不要重复执行或删除原始数据。六张图与十二份CSV的哈希及来源见[生成记录](full_validation_upl_CPU1_r1.check.json)。大型完整材料层CSV和原生二进制原位保留，不声称已上传云端Git；必要图表、摘要和脚本选择性备份。

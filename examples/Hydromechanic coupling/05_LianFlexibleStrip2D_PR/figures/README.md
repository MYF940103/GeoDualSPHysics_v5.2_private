# Lian 100秒正式结果

## 最新r3：SPH/FEM论文曲线加密（2026-10-28）

只重新采集论文可见笔画，不重算或改变本方模拟数据。原论文PDF第18页Fig11/12为嵌入栅格图，
已直接取点并保存原始像素位置、实际栅格时间、单位、来源SHA、分支可辨性和笔画误差范围。

| 最新对比 | 图片 | 数据 |
| --- | --- | --- |
| Fig11：A/B孔压，SPH各64点、FEM各48点 | [r3孔压](lian_hgspr100_r3_fig11_compare.png) | [730行论文取点](lian_hgspr100_r3_reference.csv)、[640行逐点比较](lian_hgspr100_r3_comparison.csv) |
| Fig12：A/B沉降，SPH各77点、FEM各67点；100 s剖面SPH22点/FEM106点 | [r3沉降与剖面](lian_hgspr100_r3_fig12_compare.png) | 同上两张CSV；本方[历史](lian_hgspr100_r2_history.csv)和[材料线剖面](lian_hgspr100_r1_horizontal_profile.csv)未变 |

730行含额外90个晚期孔压重叠色带观察，不将其伪拆成A/B，也不纳入640行逐点比较。
FEM密集标记用可见包络的近似中心和完整范围表示；峰值附近无法辨识的FEM段、
SPH水平位移下部被遮挡段留缺失，不以插值补线。相邻像素并非独立数值实验，误差棒也不是统计置信区间。
两张CSV的`value`及`current_value`单位由`units`列指定：孔压kPa、沉降/水平位移m。
时间/高程不确定性和本方对该坐标偏差的敏感量分列保存；只对本方原生结果做时空插值以比较原图坐标，
没有对论文稀疏点插值或调整时间原点。图中沉降和水平位移统一以mm显示。
本方A/B仍为固定初始材料点，剖面仍为初始x0=1.25 m材料线；论文未明确剖面是材料线还是当前空间线。

复现脚本：`../support/plot_lian_dense_r3.py`；像素覆盖核对图：
`../tests/figures/lian_hgspr100_r3_fig11_overlay.png`和`..._fig12_overlay.png`。
读图核查记录：`../tests/logs/lian_hgspr100_r3.final_review.json`。
旧25点以及r1/r2图片/数据均保留。Cryer求解器、输入和监测未修改/重启。

## 保留的r2：0–1 s按0.01 s保存

下表保留原r2图及最新原生历史数据。早期101帧来自相同物理/程序的RTX 3050补算，
1 s之后1980帧仍为原A6000的100 s结果，共2081行；21个共有实际时间/步号状态的
34个物理字段全部0 ULP。每行保留来源、原生帧号和SHA，未插值制造原生时间点。
末态和所有晚期数值未变，早期加密不是物理精度改进或新的时间步收敛证据。

| 最新内容 | 图片 | 对应数据 |
| --- | --- | --- |
| 完整历史、载荷和晚期耗散 | [r2历史图](lian_hgspr100_r2_history.png) | [2081行历史](lian_hgspr100_r2_history.csv) |
| 论文Fig11，A/B孔压历史 | [r2对比图](lian_hgspr100_r2_fig11_compare.png) | [历史](lian_hgspr100_r2_history.csv)、[25个论文稀疏点](lian_hgspr100_r2_paper_points.csv) |
| 论文Fig12，沉降和原100 s剖面 | [r2对比图](lian_hgspr100_r2_fig12_compare.png) | 同上历史/稀疏点；[原剖面](lian_hgspr100_r1_horizontal_profile.csv)未变 |

原生101帧补算位于 `../tests/outputs/lian_hgspr_early_r1`；
`../tests/logs/lian_hgspr_early_r1.final_review.json`记录核查与视读结果。
补算末帧的加载源时钟仍小于1 s，因此没有活跃排水帧，不把它称为排水复验。
Fig10四时刻云图、应力/近墙图及原VTK序列继续使用下列r1文件，不重复生成。
下面的r1说明与原0.05 s采样限制保留作历史记录；最新早期观察应以r2为准。

## 保留的r1正式分析

数据来源：根目录 `CaseLianFlexibleStrip2D_PR_release_HGSPR_out`，RTX A6000，
HG=.1、SPR=1、应力率梯度修正=1、dt=10 μs。所有图由原生BI4生成，原始结果未重算或改写。

| 查看内容 | 图片 | 对应数据 |
| --- | --- | --- |
| 论文Fig10孔压云图，0.5/1/3/50 s | [对比图](lian_hgspr100_r1_fig10_compare.png) | `lian_hgspr100_r1_field_*.csv`，`lian_hgspr100_r1_fig10_scales.csv` |
| 论文Fig11，A/B孔压历史 | [对比图](lian_hgspr100_r1_fig11_compare.png) | [全时程](lian_hgspr100_r1_history.csv)，[论文稀疏点对比](lian_hgspr100_r1_paper_points.csv) |
| 论文Fig12，A/B沉降及100 s水平位移剖面 | [对比图](lian_hgspr100_r1_fig12_compare.png) | [有符号剖面](lian_hgspr100_r1_horizontal_profile.csv)，同上全时程/稀疏点 |
| 原生历史、载荷与晚期耗散 | [历史图](lian_hgspr100_r1_history.png) | [全时程](lian_hgspr100_r1_history.csv) |
| 总竖向应力、速度及近墙土层位移 | [应力和边界响应](lian_hgspr100_r1_stress_boundary.png) | 同上全时程 |

## 主要结果

100 s时A/B孔压为0.168874/0.199475 Pa，沉降为1.832605/1.110029 mm；
全域最大孔压由50 s的27.5700 Pa继续降到100 s的0.749146 Pa，没有出现此前量级的晚期平台。
全2001帧未见负孔压、塑性或粒子排除；原先角点1744失载/排水切换未复发。
真实载荷保持原13节点求积，最大结果误差0.000619 N/m。

论文可辨识SPH稀疏点在约50 s给出A/B沉降1.8078/1.1303 mm，
当前同实际图像时刻的差约+1.04%/−2.31%。100 s剖面在高程2–8 m处与
论文FEM稀疏点差约1.1–2.4%；顶部负向位移为−0.1961 mm，论文约−0.2091 mm，
幅值约低6.2%。早期A点孔压在约0.1/0.5 s比论文SPH稀疏点低约11.0%/9.3%，
B点低约4.9%/5.3%，应保留这些误差，不将结果称为精确复现。

## 比较定义与限制

A=(0,10)，固定native ID1744；B=(1.25,8.75)，由四个初始相邻ID固定双线性权重得到。
沉降为z0−z，水平位移为x−x0；剖面是初始x0=1.25 m材料线，纵轴为初始高程，非绝对位移。
`paper_points.csv`的25点来自原论文栅格图，记录像素位置、单位、误差和实际图像时刻。
它不是论文原始数据，不支持完整曲线或全场RMSE。沉降读图约±0.0195 mm，
水平位移约±0.00218 mm；时间像素误差也已在来源记录中保留。

输出间隔0.05 s，因此不补造论文0.01–0.05 s数据。图10保持原四行色限
0–5、0–5、0–1.75、0–0.06 kPa；场数据未平滑、截值或缩放。13节点载荷仍有+4%理想宽度求积差。
本次没有100 s独立半步，组合方案3 s半步按用户要求取消；全程稳定不等于完整时间收敛或通用边界验收。

`particles/PartFluid.vtk.series`与`PartBound.vtk.series`在正式输出目录内，按
[ParaView官方序列格式](https://docs.paraview.org/en/latest/UsersGuide/dataIngestion.html)记录实际时间；
已核对2001项时间/文件映射，未在本次任务中操作ParaView GUI。
VTK用于显示，原生BI4用于精度分析，二者未混用。

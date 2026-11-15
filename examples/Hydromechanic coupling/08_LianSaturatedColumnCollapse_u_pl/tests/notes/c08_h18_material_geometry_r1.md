# C08 old AS03/Lstar：固定材料局部几何，author-only r1

仅新增本记录和 `support/c08_h18_material_geometry_r1.py`。未运行/import该脚本、未读新 pair-C/bare 的任何原生体、未求解/构建/解码/VTK/更改参数。脚本只供根独立完整审阅及一次授权执行；不自动开始后续任务。

输入只取已通过 `logs/c08_h18_lstar_window_review_r1.check.json` 所封的 old AS03/Lstar 各91帧原生导出，以及其5000行 `figures/c08_h18_lstar_window_review_r1_cohorts.csv`。所有原生 body/layout/clocks 先按该 check 的 consumed stat 绑定；cohorts 按其 files 原 seal 绑定。透明复用既有 `c08_h18_storage_review_r2.typed` 和 `c08_h18_compare_r2.read22` 纯读取原语，不调用旧分析入口、decoder 或 API，也不扫描旧大CSV/重新数字化论文。源码解析依赖、旧输入均作前后 stat 保护，无 SHA。

拓扑完全来自 cohorts 的真实初始 x/z、initial_layer 和原材料ID，而非ID差推断：要求50×100、一格一粒、平面y=0。几何参考取实际PRE末态坐标；仅 memmap 原源第1000帧核对同ID/PRE坐标并读取正的 J_PRE，不访问源前1000帧。后续比较 J(t)/J_PRE，而非把塌陷阶段面积比与绝对J混为一谈。原生实际保存clock/step、signed dterror 门及全部22数组/ID读取门保留；所有91时刻原样使用，无插值或重写时钟。

固定局部范围为6817、6866各自初始3×3土邻居的union，另选一个相邻3×3 patch：从6817格点依次尝试(层差0,列差−3)、(0,+3)、(−3,0)、(+3,0)，仅根据初始网格选第一个不重叠、完整的patch。它标为 `adjacent_descriptive`，不是未受影响真值或统计对照。不得根据后续变形/NN重新挑点。床/侧边允许截断的土邻域，不加入固定墙作为连续土体材料。固定范围不会覆盖全场所有团聚或滑动带。

每个完整初始quad按 `[左下,右下,右上,左上]` 建主对角线两三角；同时保留另一对角线的两三角作连接选择敏感性观察。每个三角用实际PRE边矩阵X和当前边矩阵Y计算 `F=Y X^-1`，记录两个真实有符号面积、detF、s_min/s_max、条件数，以及四顶点J比的min/median/max。每个quad四个三角符号是否分歧原样记录。参考rank不足、当前零奇异值保留行和标记，相关不可定义量留空；不加正则化或物理容差来隐藏退化。数值rank仅采用NumPy标准机器精度规则。

三个固定中心还以其原3×3土邻居做最小二乘：`F*=argmin Σ||dx-F dX||²`，平移已消去，刚体转动和仿射剪切可由F吸收。记录 `Dmin²/dp²=Σ||dx-F*dX||²/(N dp²)`、F行列式/奇异值/条件数、中心J比，以及6817/6866实际距离和两个中心拟合预测的距离及向量残差。目标另一粒属于拟合邻域，预测是 **in-sample描述**，不是独立预测误差或新的物理真值。

当det与J比接近1、s_min小/s_max大而Dmin小，近邻缩短可能主要是近体积保持仿射剪切；Dmin增加或两对角线符号分歧则提示非仿射变化/后建连接跨越不连续。但这些三角不是求解器网格/控制体；负面积不能称存储J<0或绝对物理错误。真实软化局部化、滑移、分离及接触都可能使固定邻接不再代表光滑连续体。J由粒子div积分，面积是有限尺度线性插值，二者不要求精确一致，也不设任意5Pa/间距/面积物理验收门。图像不能单独确证“张拉不稳定已修复”。

新输出仅 `tests/figures/c08_h18_material_geometry_r1_triangles.csv`、`_local_fit.csv` 和一张3×2历史PNG；匹配全2×91实际时刻，保留全部局部三角/中心的符号和退化标记。PNG展示实际/拟合pair距离、Dmin、主三角det/J比、最小/最大奇异值和条件数；右轴点线为主/反对角三角符号分歧的quad数，不是接触或失稳计数。CSV保留所有对角线数据，不只保留图中极值。输出及 `logs/c08_h18_material_geometry_r1.check.json` 均 exclusive；旧/partial 路径阻止覆盖，分析失败只记录新派生失败，不重跑物理解码。check 明确 physical_acceptance=false、visual_QA_pending=true、new_pair_body_read=false。

根独立授权后的唯一离线调用：

`D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_material_geometry_r1.py --execution-authorized`

作者只做静态自审；实际CSV数值、图可读性、文件绑定和科学结论均待根审阅/执行后确认。

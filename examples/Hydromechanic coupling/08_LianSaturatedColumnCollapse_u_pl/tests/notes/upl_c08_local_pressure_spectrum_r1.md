# C08局部冻结压力子算子谱（仅作者准备，未执行）

只读取已封口r5的300×6805×22 typed导出及既有passed `upl_c08_r5_pressure_probe_r2.check.json`，复用该脚本的正确标量shape加载器、原Cloud、Mechanical和probe。新文件只有本note和同名support脚本；不改helper、正式数据/图、源码、阈值或时步，不启动BI4读取器、求解器、构建或通知。新输出名称已查不存在/未被Git跟踪，运行时仍拒绝已有完整/部分输出。

选原生part60/61/62/63（实际tau约.61/.62/.63/.64，保留真实clock）。两个focus组为5809及4956+4959；每组取这四个保存态中各focus的2R土粒ID并集，作为跨时刻固定材料变量/行集合，共8块。每行仍使用完整全云C矩阵、Darcy邻域、raw动量压力self项及二跳压力依赖，绝不在2R patch边界截断物理stencil；2R仅选诊断变量。任一所需行触发原WallStencil，整块记录未评估，不能删掉该点或墙后继续求谱。

本轮仅两种矩阵：direct压力项，以及direct+pressure→rawAce→Darcy。AS1在原物理运行中真实开启，但本轮ASJac、AV、有效应力/速度/θ/J等响应不入矩阵。每种同时计算全patch变量块及FS0主子块，其他压力扰动固定0。记录max Reλ、对应Imλ、最大|Imλ|、原dt2.5us下midpoint多项式 `R=1+dtλ+.5(dtλ)^2` 的谱半径；后者只是冻结压力模型的显式中点映射，不是完整Symplectic积分器的谱。保留矩阵完整stencil的常量响应、块常量响应及被固定外部压力列的耦合量，不强制行和为0。

额外计算 `sym(W^.5 A W^-.5)` 最大特征值，`W=nV/Kw`。它对应当前冻结压力储能范数；不是完整多相系统能量，不据其正值增加任何物理验收门。原始C条件与代数展开roundoff仅在row表描述，不加PSD、谱正负或拟合阈值。所有eigenvalue/mode均保留数值事实；主模态只旋转复相位并归一到最大幅值1Pa，未拟合实际孔压。

每块保存一个NPZ：真实target/完整压力列IDs、位置/FS/p/storage W、完整矩形direct/rawAce行及两种patch方阵。summary/modes/row_geometry/patch_IDs为小CSV；若有WallStencil另写not_evaluated。没有新图；预计几十至百余维的8块，CPU1/BLAS1成本为几十秒至数分钟级，取决于实际patch与Python/库启动，远小于重做物理窗口；本稿尚未执行计时。

局限：保存态并非脉冲的每个真实force substage，C/float cutoff为既有重建代理，不是packed GPU坐标/FMA的逐位AD；外部扰动固定后的主子块可与全系统谱不同。FS2/3零压正向投影非光滑，本轮不对其求导，因此另给FS0子块。正实部只能证明该冻结局部代理有增长方向，不能单独认定实际脉冲原因；没有正实部也排除不了非正规瞬态、FS/geometry切换、遗漏的全机械耦合或AS响应。不得据此自动改物理门、时步、源码、解锁其他ψ组或开启新求解。

root全文审阅后，唯一离线调用：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_local_pressure_spectrum_r1.py --execution-authorized
```

新结果前缀为 `tests/figures/upl_c08_local_pressure_spectrum_r1`，check在 `tests/logs/upl_c08_local_pressure_spectrum_r1.check.json`。passed仅表示分析按原输入/数学完成；矩阵不可评估块单列，physical_acceptance始终false。

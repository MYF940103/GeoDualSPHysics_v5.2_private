# 首近对瞬时局部仿射拟合（作者稿）

本稿生成时未执行。仅新增 `support/upl_c08_pair_localfit_r1.py`；未来从已通过的 true causal90 typed22 原始90帧头中 seek part13/14，两条原生导出记录各读一次，不读取BI4或大trace。四focus固定为7011/7012/6230/6231，共8次拟合；接收已通过 pair_gradient 的混合土/墙实际应力率梯度输出，不新增force/积分/构建。

拟合明确为 **soil-only**：每focus取实际所有5000土粒中距离 `r<2h` 的完整邻域，包含自身。h取真实生成XML并转为原float KernelH（约.048m，支撑约.096m），不另裁减邻域。非负 Cubic W形状乘实际 `PoroCurrentVolume` 作权；共同正归一化常数不影响拟合与归一指标。带自由截距，设计矩阵为 `[1,(x-xi)/h,(z-zi)/h]`，拟合两速度分量后除h恢复L单位s⁻¹。NumPy SVD最小二乘仅用 `eps*max(A.shape)` 的数值秩约定；报告全部奇异值、缩放设计条件数、秩及有效加权样本数，不设物理验收阈值，不按残差删点。若秩不足保留最小范数解并标记非唯一，不把它宣称可靠完整梯度。

输出浅路径 `tests/figures/upl_c08_pair_localfit_r1_{fits,neighbors,pairs}.csv` 和 `_residuals.png`；独立 `logs/upl_c08_pair_localfit_r1.check.json`。fits8行包含自由截距、中心残差、邻域加权RMS、最大残差、中心与最大单点加权SSE占比，以及最近邻边的负残差内积分数/加权方向对齐。最近邻边由每个局部邻居的最近另一土粒构成并去重，无人为距离阈值；这只是描述空间交替，不证明数值零能模式。零残差使相关分母为零时写空值，不冒填相关系数。

neighbors完整保留所选每个土粒ID、坐标/速度、拟合预测/残差、p、κ、J、k、保存FS、有效应力六分量和总应力迹。pairs对7011/7012及6230/6231分别导出土粒拟合的 `dv-.5(Li+Lj)rij`、方向收缩率，与实际SPH混合支撑梯度方向值并列。另在i与j各自同一拟合内列出中心/伙伴残差及内积，结合单点SSE占比判断较共享的速度偏离还是单点突出，不预造二元结论。

图为2态×4focus，所有面板同物理窗口/等比坐标、同箭头尺度；残差箭头与真实保存孔压共用全图数据范围，中心绿色圈，实际固定点灰色方块仅显示位置。固定墙的真实导数镜像速度不在现有导出里，**不参与拟合、不设为零、不补造**。因此soil-only拟合L与实际SPH（含墙导数速度、float累加和C修正）并非同一个算子，差异不能直接用来判错或证明hourglass。

根全文审阅后独立运行一次：`D:/anaconda3/python.exe -B tests/support/upl_c08_pair_localfit_r1.py --execution-authorized`。只需已安装NumPy/Matplotlib，不引入SciPy、安装依赖或自动下一阶段。新输出拒覆盖；所有实际ID/clock与被消费收据/stat保持绑定。rank、条件数和交替性不是新物理门，也不把.01s保存采样解释为未保存阶段的完整因果。

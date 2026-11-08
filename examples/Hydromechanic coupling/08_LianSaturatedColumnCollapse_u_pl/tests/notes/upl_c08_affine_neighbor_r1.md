# 保存态材料邻域的局部仿射诊断（作者稿，未执行）

只新增本note及同名support。复用已封口r5/AS.5原生收据与22 schema；两组各读first保存态part0作各自reference（实际τ≈.01，已4000步，明确不是PRE/t0），再读ε.2 part65/119/299及ε.5 part65，共6个真实records，不扫366态。每个目标态保留原5000材料ID和无效拟合点，不选ROI、不重映射ρ/p/J/n等原生场。

reference邻居为其他soil IDs的r0<2h，权重沿已审Cubic W0×native reference V（即V0Jref）。令ΔX=Xj−Xi、Δx=xj−xi，M=ΣwΔX⊗ΔX，A=ΣwΔx⊗ΔX，F=A M^-1。每点输出邻居数、正权重数、Kish有效数、M rank/cond。rank以2eps×最大奇异值定义数值秩，不设新的物理cond门；rank不足/逆失败/非有限保留status，缺拟合值留空，cond无穷明确保留。F负det也只记录，不删除。

报告detF与原native J/Jref、reference material bonds的加权非仿射RMS/dp。当前最近邻若也是reference邻居，才给r/||FΔX||；否则单列new-neighbor接触，不伪造原bond比值；预测长度为零另记。固定κ阈值.1f分层，全部分位数保留无效数/有限样本数。若NN小但比值接近1，可以由大剪切仿射压缩解释；大非仿射也可能是物理滑移/邻接交换，均不能证明张拉根因。

输出 `tests/figures/upl_c08_affine_neighbor_r1_points.csv`（四态×5000点）与12行summary CSV，暂不绘图；check在同名logs。无新reader/solver/VTK/build/SHA，不改旧文件。root全文审后唯一调用（本稿未import/运行）：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_affine_neighbor_r1.py --execution-authorized
```

# C08配套压力算子的局部纯离线A/B（作者稿，未执行）

只新增同名support脚本和本note，先读 `upl_c08_pressure_adjoint_candidate_r1.md`。输入仍为已封口r5 typed导出和此前8块raw/AS NPZ；沿四态、两个47/62材料patch、全变量/FS0主子块及原storage W。current矩阵、direct Lstar/FS/gradk和同一ASJac增量从现成NPZ读取，不重算/覆盖baseline。无solver、BI4 reader、构建、half、新公共接口、源码或阈值修改；CPU与BLAS均1。

A1仅改压力到动量系数：`Bad_i p=-sum_j Vj(pi Ci+pj Cj)graw_ij/rho_i`，保留原Mechanical float delta/rr²/gradient/cutoff，原raw.row仍先核完整force stencil；所需Cj来自各自完整moment。经原Darcy divAce/FS-Ace/kgrad传播，仅取Ace增量，加回封口direct及ASJac。准确名称为C-weighted/adjoint-inspired mechanical候选；它与Darcy的double-position D不严格adjoint。当前θ/σ导数亦走packed-float几何，与Darcy D仅数学形式相同，不能偷换成同一浮点矩阵。

数学control另选同一个Darcy-double divergence `D_i v=sum_j Vj(vj-vi)·Ci gij`，显式构造完整加权转置 `Gadj_j,l=-(Vl/Vj)D_l,j`，核每条真实邻接双向存在，再算 `A_pair=B D diag[k/gamma*(1-rhow/rho)] Gadj`，B=Kw/n。这里两侧严格复用同一个D，不用近似公式冒充转置；随后分别不含/加回同一已保存ASJac。它是压力储能耗散的数学对照，不是生产替换建议，也未保留现有FS原始分支/显式gradk拆分，因此不能把改善归为单项实现修复。

每个候选先形成完整物理stencil的行，再限制到原patch/FS0变量。若新算子压力列扩展，取旧列和所有新列的union，旧矩阵补零延展、AS增量不丢列，记录新增列数。Bad/transpose需要邻居C，完整moment可要求三几何hop；任一原WallStencil拒绝整块，不能删墙/邻点/C行继续。现有22/ledger资格沿旧加载器；没有新的C/PSD/谱正负物理门。

输出8个NPZ保留真实target/pressure IDs、完整行、patch方阵、W和实际时钟；summary含max Reλ/Imλ、midpoint R谱半径、W对称部max特征值及对current变化，另有row_geometry与常量/affine x/affine z/hydrostatic响应CSV。hydrostatic测试固定为gamma*(2−z)，2m来自原水位；报告压力算子作用与块外扰动为零的作用两者。它未加入重力/有效应力独立源，绝不称为完整水静力平衡残差。常量响应不强制为零；adjoint也不保证一致性、常压nullspace或无checkerboard。

所有限域继续：局部outside-held主子块不是全耦合谱，J/n/k/σeff/θ/速度/FS冻结；零压FS投影未求导；AS仅连续谱代理，不是CUDA量化AD或AS非线性力；W=nV/Kw仅压力储能范数。无AS的完全匹配数学control在其正系数条件下应呈耗散，但图/谱改善仍非实际脉冲因果证明。若生产将来改动量，还需σeff−pI全应力、Cryer外载、边界/AS/AV等一致性，不由本脚本自动启动。

root全文审后唯一离线调用：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_pressure_pairing_ab_r1.py --execution-authorized
```

新输出前缀 `tests/figures/upl_c08_pressure_pairing_ab_r1`，check在 `tests/logs/upl_c08_pressure_pairing_ab_r1.check.json`。passed仅分析完成，未评估块单列，physical_acceptance=false；本作者稿未import或运行。

# C08局部压力谱的ASJac增量（作者稿，未执行）

仅新增同名support脚本及本note。原raw局部谱已实际完成8块；本版直接读取其八个NPZ与summary，保留原direct/raw方阵及谱数值，不重算或修改baseline。使用相同四保存态、两个固定材料patch（47及62个变量）、真实clock/IDs/完整压力列、storage W及all/FS0主子块。本轮不绘图、不引入新solver、BI4 reader、构建、half或新物理门。

只新增AS-only pressure→Ace导数，再经原完整Darcy的divAce、FS-Ace·lx、kgrad-Ace三个通道传播，加到保留的direct+rawAce矩阵。复用既有 `SpectralAS` 和 `ace.probe`：后者为AS-only provider内部计算的direct row不使用，baseline仍只来自封口NPZ；原raw Mechanical.row仅为AS每个实际force stencil提供原float-cutoff/WallStencil guard。没有截断邻域、C、self项或二跳依赖；AS压力列若超出原完整二跳列集会报告错误，不能删列。任一WallStencil导致整块未评估，不删行继续求谱。

AS张量代理与已通过r5 probe一致：对原double有效应力减实际绝对孔压I后cast float32，再double eigh；`R=-εΣ_positive`，`dR/dp=εP_positive`，ε=.2f、权重指数2.55f及W/Wdp均沿原provider。固定σeff时各主应力随p统一平移，不能将AS非线性力误写为Jacobian乘p。本轮只计算连续谱代理的局部压力导数，不声称float量化、CUDA迭代eig、累加/FMA的逐位AD。

每块独立记录所需全部AS节点的positive rank、exact-zero主应力数、kink节点数、最小绝对主应力及ID、源应力float cast和输出R cast差。exact zero不引入拟合容差；仍按旧provider的λ>0 projector约定，但明确这不是唯一经典导数。即使exact zero为零，也不能据此认证GPU分支或跨越较大孔压扰动的导数有效性。

第三矩阵复用原spectral函数，报告max Reλ/Imλ、midpoint R谱半径、`nV/Kw`对称部max特征值及相对raw的差；原direct/raw值从summary照读。保存第三矩阵及AS增量的8个NPZ，输出summary/modes/AS_spectra小CSV，不覆盖旧文件。预估单CPU/BLAS1约10秒量级，实际以root唯一运行计时为准。

限制全部延续：块外扰动固定；非完整耦合谱；真实r5中AS1开启而本轮只是冻结ASJac代理；geometry/J/n/k/σeff/θ/速度/FS固定；零压FS正向投影未线性化，另给FS0主子块；pressure-storage范数不是全状态能量。正实部可能改变筛查方向，不能单独确定实际高频脉冲原因；谱无正实部也不能排除非正规瞬态、真实stage/FS切换或遗漏的全机械响应。

root全文审后单次离线调用：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_local_pressure_spectrum_as_r1.py --execution-authorized
```

新输出前缀 `tests/figures/upl_c08_local_pressure_spectrum_as_r1`，check在 `tests/logs/upl_c08_local_pressure_spectrum_as_r1.check.json`。passed仅表示按保留输入完成该诊断，physical_acceptance=false，不自动更改代码、参数、时步或解锁其他ψ组。

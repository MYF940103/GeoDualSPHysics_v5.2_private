# 单次 frozen-geometry shifting 部件（author-only）

只新增同名support脚本及本note，先查新名不存在/git ls-files为空；未执行组件/现有owner、solver/build/native/VTK或hash。目标是检查现有位移形式是否值得继续接入，不预设改善，不改变保留的坐标/状态、生产guard或输入。

## 数据与一帧一次的定义

复用已审 `upl_c08_clustering_r1.formal()` 的实际r5完整300帧native资格、post/reader退出、6805/22/layout/ID/源stat；不调用它的main或AS05载入。不读BI4、不解码PRE、不扫描所有300payload。按clocks的completed Step4120000/4264000/4480000/5200000唯一定位名义tau .30/.66/1.2/3，只seek读取这4个原record，调用现有inspect核该帧全部22数组有限、5000soil IDs、实际clock/Step/signed。CSV和图保留真实time/tau，名义标签不代替scalar clock；旧12B头6805/22/300不改。

采用dp=.04、实际float h=.048、dt2.5us、ShiftCoef=-2、保存的float速度范数，形成一次`delta=dt*coef*h*|v|*sum(Vj gradW)`，按旧实现每分量float cap=.1dp限幅。主proposal体积为实际V0*J；另同一梯度/求和精度比较m0/native_Rhop权重，明确它是legacy体积的snapshot诊断、不是旧CUDA逐bit执行。native fixed的导出CurrentVolume=0是marker，绝不用它作wall体积。

复用已核wall_geometry.cubic的float32 fac模式和非零/支持cutoff；native double差先cast分量float，缺packed PosCell/FMA/cell遍历，double稳定ID顺序求和。因此是当前几何上的proposal，不冒充真实生产shift/rate replay。KDTree只作broad phase，最终按原float rr²<=kernelsize²且>=ALMOSTZERO筛选。全土proposal纳入同R所有saved fixed的V0J，因22中无BoundMode而明确为**saved-wall inclusion proxy**。完整内部子集逐stencil排除任何fixed或FS2/3邻居，所以其结果不依赖该墙proxy。

为隔离位移本身，raw全土采用ShiftTFS0（无额外scalar衰减）；不是把它当安全自由面政策。受限proposal将真实FS2/3及半径2h halo、fixed邻带、旧clustering低支持代理（1.5dp内土邻居<4）和非正/非有限moment最小特征值点全部冻结；membership在move前确定，两个权重共用它。没有反复shift、重新筛选有利cohort、放大dt、调系数或将新proposal送回solver。所谓完整内部是明确的几何/支持资格，不是已证明不存在物理孔洞或自由面的全域判定。

## 输出和解释

每态×两权重×全土/受限方案报拟移动数/范数、固定mask cohort的NN（邻居来自全5000土）、严格r<.5dp/.7dp的全域及cohort-both唯一pair数、native FS法向位移、FS到非FS最近距离以及预计越x0/z0平面数量。after只在独立临时坐标copy加一次delta，原fixed坐标和原状态不写回；不会调用NoPen替它裁位移。FSNormal用保存值归一化；无有效normal者独立计数、不假造0。native FS可能含内侧面，FS间距代理不自动等于外轮廓gap/断裂。

只作解析制造场运输尺度，不猜保存场梯度：常量p/J/sigma/kappa均应delta0；静水affine p的梯度(0,-gamma_w)，unit-J affine梯度(1,0)/m，三对角相同的affine sigma各梯度(1,0)Pa/m，affine kappa梯度(1,1)/m。统计精确`grad(f).delta`（sigma用Frobenius），这些是携值移动缺少的Taylor项尺度，不是实际孔压误差、塑性新增量、材料更新或已实现运输守恒。即使NN改善，也不能据此接受position-only u-pl重排。

fresh输出前缀`tests/figures/upl_c08_shift_frozen_r1`：summary CSV16行、proposals CSV40000行、weight_difference CSV8行、单张2×2数值图与小check。点表保留原ID/xz/J/速度、资格/支持计数和raw/interior delta；无大型逐时全场导出。4个状态独立，图线只连接这4个诊断点，不表示它们之间实际积分。全部旧结果拒绝覆盖，失败保留不自动重试。

root全文审后才可单次离线运行（目前未执行）：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_shift_frozen_r1.py --execution-authorized
```

无新数值验收阈值、物理solver、native decoder、guard解禁、场运输、其他psi或自动后续；physical_acceptance=false。不以更规整的点图或少量近对减少保证后续动态自由面/接触/渗流稳定。

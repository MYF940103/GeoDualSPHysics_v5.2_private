# C08 H1.8预载失败的主应力谱观察

本轮只作者 `tests/support/c08_h18_loss_spectrum_r1.py` 和本说明。未导入执行分析、读取原生数值载荷、解码、绘图、启动求解器、构建、Git或SHA扫描。根线程完整审阅后，才可显式运行一次：

```text
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_loss_spectrum_r1.py --manifest tests/configs/c08_h18_loss_review_r1.json --execution-authorized
```

只复用已完成的 `c08_h18_plastic_psi0_pre_r1/native_loss_r1`：533个完整7060-ID状态，加真实第533号7059-ID稀疏终态，共534个实际时刻。调用已审 `c08_h18_loss_review_r1.load`，保留原source/native实际退出、程序/输入/材料CSV/完整1001调度计划、22数组、ledger、P0、κ、标量时钟与signed必要时步预算。终态缺3060，不能补零、改排序、插值、删掉后声称全程通过或改变真实534/533/7059头。程序对完整前缀逐态使用原 `read22`，稀疏终态额外保留全部22有限、原ID/P0/excess/κ及其原生收据约束。

计算只使用完整双精度 `SigmaState_kk=(xx,yy,zz)`、`SigmaState_ij=(xy,yz,xz)`，组成三维对称有效应力张量，再减实际孔压 `p I`，通过 `numpy.linalg.eigvalsh` 求全部三个主应力。**不以σzz代替主张拉、不使用旧float显示应力、不忽略σyy或非平面剪应力、不采用二维捷径。**同时记录xy/yz剪应力最大绝对值。这里的双精度数学谱是事后观察，不是既有float人工应力核的逐位回放，更不是实际人工应力力；本PRE的AS实际为OFF。

每一实际时刻分别统计soil、fixed及全部present原始ID三个人群。主指标为最大主总应力、对应原ID、signed最大主应力RMS、positive最大主应力RMS、三正谱Frobenius RMS、λmax>0和>100Pa的粒子数及正主应力模式数。RMS分母始终是真实present人群；终态soil是4999，不能把缺失3060当0加进5000分母。0/100Pa是同时公开的固定观察档，均不是新接受阈值、物理门或可以放宽的数值预算。纯yy正谱也不自动证明二维面内人工应力力会显著起效。

邻域从**实际typed0**按Idp读取3060的完整初始xyz，再取原5000土点中初始x/z距离最近的8个邻居；距离相同时保留原ID稳定顺序，不根据ID猜层数或假设它本来就在床边。所有534态输出这9个固定材料点的坐标、κ、J、p、速度、最近土距离、三个主总应力和正谱范数。3060在最后一态的字段留空且present=false，不能将缺失解释为速度或张拉归零。

另对**全部5000原始土ID**记录首次保存观察到κ>0、z<0、最近土距<.7dp、λmax>0Pa、>100Pa的part和实际时间，并列出每类全域最早保存时刻的所有对应ID、其真实初始坐标及该态κ/J/λmax/NN。因此诊断不会只盯晚期丢失的3060而漏掉更早穿底的其他ID。.7dp只是延续既有几何观察档；每个当前近邻距离由全部present土点的x/z KDTree计算，Y=0原生限制仍检查。首次保存事件附上前一保存时刻；**同一保存时刻只能视为并列，不能据此推断步内先后或伪造未保存的真实首次穿越时间。**直到最后未观察到的事件保持空白；3060只观测到其最后present保存态。

新产物统一为 `tests/figures/c08_h18_loss_spectrum_r1_*`：population/focus/geometry/clocks、所有材料first-events、initial-focus及global-first快照CSV，以及history/focus两张PNG；检查记录为 `tests/logs/c08_h18_loss_spectrum_r1.check.json`。每张图保留全534个实际时刻，标明终态人群不完整；绘图不平滑、拟合或重写数据。所有原native文件、收据、物理程序与输入只读；重复/部分分析输出禁止覆盖。图生成后仍需根线程视觉核验。

此观察只用于判断“张拉谱是否先于塑性历史、近对和穿底增长”等问题；即使总张拉存在，也不能单凭谱判定AS是根因或保证增大ε能修复。正常分析完成不等于预载、平衡、塌陷或论文精度验收，不自动启动任何AS候选、另两组ψ、half、PRE或正式计算。

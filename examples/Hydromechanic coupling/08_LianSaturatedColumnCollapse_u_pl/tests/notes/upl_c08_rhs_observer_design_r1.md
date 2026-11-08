# C08真实force-stage RHS测试观测器：只读设计

本稿不实现/构建/运行。若保存态分项仍不足，最多一次从原r2认证弹性PRE全新接收至τ≤.66s，物理/材料/6805床修复/AS/AV/NoPen/dt2.5us均沿r5，不加载后期PART、不重做10s、不追加half。仅追踪5809/4956/4959，首轮**不拆AS/AV/σ力核**，记录实际finishedAce已包含这些贡献。

## 最小隔离改动

只需private source overlay的 `JSphGpu.cpp`、`JSphGpu_ker.cu` 加一个test-only POD/header；默认编译宏 `UPL_C08_RHS_TRACE` 不定义时连字段、缓冲、分支和符号都不存在。无需公共XML/新CTE字段、StInterParms改动、JSph类成员或GPU Single修改；不触碰r5正式runtime。沿已验证的MSBuild overlay/source-capture方案生成独立程序，继续权威VS项目，不建新编译系统。

- GPU.cpp1822真实 `ComputeDynamicPorePressureRateGpu` 已有Nstep/TimeStep/InterStep/Idpg；在原wall-Ace closure1833和rate调用1835前设置test-only device context（实际ID指针、全步起点clock、Nstep、predictor/corrector、actual dt、写入缓冲）。context用独立测试device symbol/new free function传递，避免修改原rate/主力函数ABI。
- GPU ker1472–1555直接在原计算末端将**已有局部量**写入专用记录：Pos/Vel、FS/normal/PosDiv、当前C九项、J/n/θ/ki、finishedAce（不含gravity）、LP=lp、Lx=lx、Gp=gp、Gp*=gpcorr、GJ=gjstate、divAce=da、active FS/interior分支、lap、chain、最终double value和真实存储float rate。原+=顺序、数学表达式/强制转换/覆盖rate完全保留；不能另跑第二邻域循环重算后冒充原RHS。可顺带在已接受邻域中为三receiver计fluid/bound数、weight正负/极值及主导贡献邻居ID，但首版非必需。
- 真正压力更新在GPU ker1315–1323（由GPU.cpp1582及1659调用）：记录原poreold、输入float rate、实际dt、porepressnew；区分half预测和full校正，不把当前PorePressg误作full-step旧p。
- 正孔压截断只在完成几何的GPU.cpp1250–1253/ker1071–1072；记录该次最新FSType、投影前/后p、是否实际截断及rate前后（该ponding策略不清rate）。中间预测PorePressPreg非空时不会作此positive-only投影。记录前必须刷新context当前Idpg：完成步RunCellDivide会排序/交换数组，不能沿用RHS时旧的ID指针。

## 记录的实际算子与阶段含义

令A为传入rate核的实际finishedAce，原算式为：内部L=LP−Gp*·Lx+ρw divAce；当前free-seepage FS分支L=LP+ρw(A_i·Lx+divAce)。变k项chain=ki/((1−n0)Ck) GJ·(Gp*+ρw A_i)，最终R=Kw/n[−θ+(ki/γw)L+chain/γw]。诊断可离线拆LP/Taylor/da/chain，但关联重排不保证逐bit求和，必须保留原value和ratefloat作事实，不能用分项和替代原值。Ccond在离线算，核内不增加求逆或重评任何状态。

Host TimeStep在predictor/corrector两次RHS均仍是**全步起点**；corrector用预测半步几何。记录Nstep、实际TimeStep、InterStep、实际pressure-update dt与phase标签，禁止用n×dt或把概念半步时间伪称已前进clock。完成投影发生在主循环TimeStep+=stepdt之前；标签可有completed_step=Nstep+1，但绝不重写clock。记录FS_at_RHS和FS_at_completed_projection，避免把保存态FS错当驱动RHS的FS。

## 缓冲、复用与限制

以编译期global step区间[4240000,4264000)选取.6～.66附近的实际24000次更新，范围仅决定记录槽位，真实clock仍直接取成员。按step/phase/三个native ID唯一槽位写GPU缓冲，使用valid/命中次数，不用device printf、全局追加原子或每步D2H。保留所有缺失/重复事件；不可用默认零填充冒充观测。约几十MB缓冲，末次完成投影后一次D2H/落盘；错误路径在cudaDeviceReset之前尽力封口已有有效记录，标partial，不推算失败未保存状态。不得调用会reset interval的dterror getter或干预原BI4间隔统计。额外原生66帧须以明确新profile核验，不能硬套60/300旧reader或截断原PART目录伪匹配。

已有 `PorosityObserver` 提供真实J/θ，不是RHS日志。C08 observer_r2是仅初始化wall查询，darcy_zero_CPU是保存态零步重评，pressure_ace_jac是冻结场Jacobian；这些都不能冒充原GPU真实force stage，可复用其ownership/输出约定与离线公式检查。CPU若以后需要可在ComputeDynamicPorePressureRateCpuT3174/ApplyPorePressureBoundaries1633对称加只写slot；首轮不因此另起CPU长程或后端/half链。

**不能承诺无数值扰动。** 即使不改原算式，新增kernel store/寄存器live range也可能改变CUDA寄存器分配、spill/FMA及执行时序。须用这唯一新窗的真实前60帧对保留r5同dt/cadence逐字段与signed clock核对；不预设0ULP。若不一致，诚实作为instrumented trajectory量化脉冲复现程度，不能宣称精确重放原失败。物理守卫/clock/IDs/原22数组预算都不变，不用新half补“证明”。若首轮仍不够，后续AS/AV可记录原加法块before/after实际增量；原σeff−p的combined一次cast不能在浮点上无损拆成独立σ/p力，需保留舍入闭合残差，当前不扩此范围。

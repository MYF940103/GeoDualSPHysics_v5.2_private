# C08 H1.8：独立GPU累计storage观察器（作者阶段）

作者文件为`support/c08_h18_storage_trace_r1.h`、`.cu`、`_prepare.py`及本文。本阶段没有导入/运行prepare，没有生成私有source输出，没有编译、程序调用、solver、native读取、VTK、Git或SHA扫描。另由同线程作者准备的GPU builder只是后续独立动作；本prepare不构建、不启动任务。

目标只补真实时间历程的信息：AS03 Parts38/76的原CPU两点RHS均给正的全域瞬时加权率，不能由它们解释持续负压历史。本观察器保留当前原AS.3/n2.55、Wendland H/dp1.8、5us、schema2同材料PRE及CompletedOnly，不把旧H1.2三ID的CausalTotals当作本轮历史，也不引入TPI、clip、滤波、修改AS/AV、其他ψ或新预载。

## 隔离与准备合同

唯一物理源码基线是已闭合`logs/c08_preload_schema2_Release_r1.build.json`所指`outputs/c08_preload_schema2_source_r1/full_source.zip`。prepare只对原`JSphGpu.cpp`插入`#ifdef C08_STORAGE_TRACE`保护的独立调用/输出代码，另外添加`C08StorageTrace.h`、`C08StorageTrace.cu`。没有改动`JSphGpu_ker.cu`、simple CU、原CUDA对象、任何生产方程/原表达式/22数组/类布局。去掉插入片段后原host字节必须完全恢复，ZIP其余原成员逐byte保持；写ZIP使用`copy.copy(ZipInfo)`，不修改原读取器CRC对象。

prepare唯一新目录`outputs/c08_h18_storage_trace_source_r1`包含完整`source.zip`、`source.json`、`source.patch`和三份私有源，唯一准备收据`logs/c08_h18_storage_trace_r1.prepare.json`。source JSON声明一个modified原member和两个added members、原baseline build/capture/archive、宏、逆向证明、其他成员字节不变及必要stat。没有反复哈希扫描。

后续私有GPU Debug/Release builder分别只重编`JSphGpu.obj`及新增独立observer CUDA对象；其余112原对象（包括所有原物理CUDA对象）保留，总链接114对象。宏只用于这两个新对象；旧stage/causal宏关闭。公共源和canonical程序不变。新CU只读原指针；其所有写均落在自己的device记录/导出缓冲，没有写原数组的API参数。

## 实际插入点和首个cap

行号指原ZIP的`src/source/JSphGpu.cpp`和`JSphGpuSingle.cpp`：

- Single1079关预载阻尼/Shepard，1080调用`RunCellDivide(true)`，1085才设置`GravityPreloadReleased=true`。Single567–581已完成退墙/排序及Np/Npb更新，随后调用`ApplyPorePressureBoundaries`。
- 因此初始化在GPU.cpp1424函数入口、`ComputeFreeSurfaceTracking`和cap之前：原handoff、Nstep=2000000、Np6805/Npb1805、retire[1805,2060)、keepfalse、无预测数组及全部当前参数窄门。此时允许Released仍false，接触资格检查其底层`NoPenetration/HydroMechDynamicSeepage/GravityPreload/Handoff`配置，不调用还要求Released=true的`UseDynamicPorePlaneContact()`；释放后在原RHS成功出口再核该active谓词。抓到的是原PRE继承土体p/J。旧handoff7060重建不会触发。释放新露FS的首cap单列release phase，不归入首corrector。
- 原GPU.cpp2060–2105成功完成原动态RHS、必要检查和速率保护后，只在真实`InterStep==INTERSTEP_SymCorrector`调用独立capture kernel；从此刻尚有效的PoroJPreg/PorePressPreg复制真实Jn/pn以及Jh、theta_h、stored float Rh为值。不能将这些指针留至更新后，因为1871更新J、2005释放PoroJPreg，1894才更新p。
- 原GPU.cpp1894压力更新原调用之后、预测p释放之前，独立update kernel读取真实praw/Jnew和仍有效pn并登记accepted corrector。它不调用原更新、不覆盖结果。
- 原GPU.cpp1433及1455的真实positive-FS cap调用前后各插独立kernel。Shepard在当前窄门中为OFF，但两个实际writer入口都覆盖。cap before保存实际p/J，after只登记实际差；重复cap的Δp=0仅增加调用数，不重复计算corrector。release cap/普通completed cap单独计数，新增FS第一次真实截断包含在内。预测期间原政策不执行positive cap，不记成额外时间增量。
- 原`ParticlesDataDown`1042入口在真实保存时读取独立累计行；没有每步CPU下载。重复相同累计count的保存不再写sidecar。

原Nstep为零基更新序号。每ID记录真实force_h step/time/dt；accepted corrector后completed=Nstep+1、time取原当前scalar time+实际dt，与外循环`TimeStep+=stepdt`同一标量操作。下一force_h要求真实pn/Jn和last accepted值逐bit连续、实际time相等。没有`n*dt`替代原时钟。cap计数使用显式before/after与release标志，不靠旧InterStep标签猜是否新corrector。clock/signed dterror等原native门仍由后续独立读取保持，storage预算不替代时钟门。

## 预注册分区与精确含义

对每个原soil ID（2060–7059），取原ledger的`w(J)=(1−solid0/J)*(V0*J)/Kw=nV/Kw`；S=w p是条件storage proxy，**不是流体质量**。每个真实corrector的恒等式为：

```
S_aftercap−S_n = wn*(praw−pn) + praw*(wnew−wn) + wnew*(paftercap−praw)
```

令`comp_h=(Kw/n_h)*(-theta_h)`、`Darcy_remainder=Rh_float−comp_h`。累计分区为：

- compression：`wn*dt*comp_h`。
- Darcy remainder：`wn*dt*(Rh_float−comp_h)`，**含原RHS最终float率量化及原Darcy各项；不是观测到的原double Darcy净率**。
- source split roundoff：`wn*dt*[Rh_float−(comp_h+Darcy_remainder)]`。
- pressure commit roundoff：`wn*[(praw−pn)−dt*Rh_float]`，由真实写回前后测得。
- weight change：`praw*(wnew−wn)`。
- cap change：每一次实际completed/release截断的`wcurrent*(pafter−pbefore)`。

另保存实际`wn*(praw−pn)`累计作交叉记录。这里选wn容量，不能把compression冒称`−V0 dt Jh theta_h`的体积压缩；若另作该图必须显式报告容量差。源最终double rate没有读到，量化只给独立**非signed bound列**：`Σ|wn dt|*(FLT_EPSILON*|Rh_float|+FLT_MIN)`，FLT_MIN覆盖潜在FTZ/下溢；它不作为一个实测signed项加入storage恒等式，不是物理epsilon/clip。

每次更新/截断保留原实际端点并累计绝对分区和局部预算。预先取double单位舍入u=0.5 DBL_EPSILON，更新局部`gamma128`乘参与乘/差/端点的绝对量和，cap局部用`gamma64`；累计预算再加`gamma_(16 updates+8 cap_calls+128)*(sumabs+|S_initial|+|S_last|)`。没有根据结果调容限、矩阵正则或物理门。每保存行检查`(S_last−S_initial)−Σ六分区`处于此算术预算。全域分析还须加入host归并预算，不能单用总和抵消局部错误。

## 连续身份、计数和成本

独立device记录按`native_id−2060`索引，排序不改变归属；固定墙不计入土storage。初始化每ID恰1次，真实corrector RHS pending与update一一对应；下一force_h不允许未消费pending，更新核检查原pn、复制的Jn/Jh及其真实clock。cap before/after也成对，不能覆盖未关闭观察。原始fixed/periodic或丢失/重复ID会触发观察错误，不放宽物理排除门。实测cap若改变p，要求原before>0、after=0及真实FS2/3，负压不改。

每步增加至多一个force_h capture、一个p-update后观察及每真实cap两个独立轻核；无额外邻域遍历、GPU全域规约或每步同步下载。device记录/导出行约数MB，实际大小由build后`sizeof`和memcheck再核；每保存下载5000条约150B行，91输出窗约70MB量级，额外CSV有相应磁盘成本。不能预称零开销，Debug验证与Release短窗应测实际loop时间；旧1.2/hardware/其他AV计时不外推。

device记录及导出区是独立CU静态`__device__`符号，生命周期归CUDA context；没有cudaMalloc指针、进程静态析构释放或cudaDeviceReset之后的cudaFree调用，不重现此前GaugeSystem退出清理问题。

sidecar`C08StorageTrace.csv`每个新累计保存状态写全部5000 ID，保留初始化、RHS、update、cap/release-cap计数、真实保存time/completed step、初末S、sum_dt、signed分区、sumabs/局部预算、量化bound和端点residual/budget。`sum_dt`仅逐次累加的诊断，不替代原实际时间。sidecar不添加到原22数组，原BI4/NBI4/保存计划不变。

下一步需要根全文审阅prepare/header/CU/builder，独立准入Debug build和短memcheck，然后Release最初3个同cadence原生保存与原AS03 .90s对应actual step/time/layout/22数组/signed clock逐byte0ULP并比较实际timing。Debug不是Release bit truth。全部通过后根才另决定唯一.90s观察。没有owner/reader/通知器在本作者文件中，没有自动下一solver、PRE重算、half链或其他ψ。

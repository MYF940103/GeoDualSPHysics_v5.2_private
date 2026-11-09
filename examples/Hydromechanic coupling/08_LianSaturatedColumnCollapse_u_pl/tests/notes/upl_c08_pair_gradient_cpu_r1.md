# 首近对完整速度梯度：CPU零步作者稿

生成本稿时未构建、未运行。新增 `support/upl_c08_pair_gradient_cpu_r1.cpp`、`_build.py`、`_run.py` 及 `outputs/upl_c08_pair_gradient_cpu_r1_source/`。原程序/源文件、PRE、BI4、旧组件和结果不改。只用已通过的 true causal90 原生导出 part13/14（实际τ≈.14/.15），不重解码、不积分、不调用材料返回或过滤器。

私有 `JSphCpu.cpp` 来自封存 bedkeep source.zip。原2611–2616行三个局部 float 梯度行完成 `ApplyGradCorr` 后、2618行 `GetStrainSpinRateTensor_sym` 前，加一个 `C08_PAIR_GRADIENT_OBSERVER` 宏下的只读 callback；另加同宏下外部函数声明。四个目标 ID为7011/7012/6230/6231，无类字段/公开接口/数组索引/物理算式变更；默认宏未定义时两块均不编入。`gradient_observer.patch`、`source.json` 和完整私有 ZIP 保存两个新增块及逐字节逆复原证明，其他归档成员不变。

原力核分别处理 fluid 与 bound 邻居，每组各自修正梯度、形成并累加应力率。callback因此分别复制每ID的两组9个实际float分量，每组要求一次命中，不能把最后一组当完整梯度。`focus.csv` 同时保存两组与其double和（`L_fluid_* / L_bound_* / L_sum_*`，行=速度分量、列=空间方向）。这个和是从原局部值形成的诊断，不是原程序另存的完整float矩阵，可能与逐float应力率累加存在舍入差。θ仍直接导出原数组，不用梯度迹替代它，也不从θ/应力率反演梯度。

helper沿旧 pair_force 的初始化、真实认证PRE导入、keep5释放一次、按ID恢复/分区/再次恢复、固定墙normal/NoSlip角色及全5000主场/ledger位检查。只做两次 baseline `Interaction_Forces(SymCorrector)`，各含真实完整邻域、动态墙响应和一次Darcy；保持 AS.2/n3、AV.1，无参数开关变体。原 `DtVariable(false)` 和必要步长界照常检查，不推进时间。清理force临时场后恢复输入及本次baseline压力率；不是GPU逐位重放或完整重启。

输出：`calls.csv`2行、`soil_force.csv`10000行、`focus.csv`8行、原7011/7012 `pairs.csv`2行，以及两对7011/7012、6230/6231的 `gradient_pairs.csv`4行。后者使用同次真实位置/速度和上述修正梯度，记录 `dv−.5(Li+Lj)rij`、`rdot/r`、`nᵀsym(Li)n`、`nᵀsym(Lj)n`和平均方向值；`nᵀLn=nᵀsym(L)n`，不另改物理应变率。长度/速度残差单位为m、m/s，方向速率为s⁻¹。这是非仿射/离散方向诊断，不是新的材料或张拉验收门。

构建重放权威 bedkeep DebugCPU `JSphCpu.cpp` tlog旗标，只为该私有TU开启宏；helper沿已通过 pair_force 的实际CL/link参数与同归档headers。排除旧main和旧JSphCpu.obj，链接85个封存物理对象＋私有JSphCpu.obj＋helper.obj，总87对象；2CL＋1link，不重编CUDA/项目/生产程序，复制原4个Debug运行依赖。原header/材料/接收合同均沿封存闭包。

运行wrapper仍核true causal90、原r6全22/clock/signed前缀证明、实际run/native调用和输入/PRE绑定。新输出独立 `outputs/upl_c08_pair_gradient_cpu_r1`，收据 `logs/upl_c08_pair_gradient_cpu_r1.check.json`。对旧 pair_force 两态 baseline 的10000土粒共同字段、四条重合focus记录作逐字段精确f64读回位比较；旧全5000 CSV没有应力率，因此只对旧7011/7012 focus的六应力率分量作精确对照，不能宣称旧全场Rsigma已有比较。新全场六应力率另完整导出。若重新编译影响上游float结果，保留差异摘要并失败，不改容差或旧记录。

根全文审阅后才可分别执行，互不自动接续：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_pair_gradient_cpu_r1_build.py --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_pair_gradient_cpu_r1_run.py --execution-authorized
```

这里只观察已保存态上的新CPU完整力算子；没有原GPU未保存阶段、实际接触冲量、稳定谱或完整历史重建。callback不作物理回写，原5000主场位守卫、实际FS变化与所有原必要数值门保留；不启动后续求解或自动新候选。

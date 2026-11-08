# 私有 effective-AS 单定义干预（作者稿，未构建/未运行）

仅新增同名support CPP/build.py/run.py、本note和浅 `outputs/upl_c08_as_effective_cpu_r1_source/` 作者归档。生产源码、VS项目、根XML、runtime_r6、原r2 PRE、旧CPU/GPU对象/程序/结果均不动。不是新鲜撤墙物理验收，也不改变其他ψ锁定状态。

来源：总应力AS适配由 `1d4268b` 引入，理由是匹配当前混合物总应力动量和J体积/惯性权重；legacy只将存储Sigma传入谱函数。此试验只比较谱输入，**不回滚legacy rho⁻²/质量形式**：从同封口 bedkeep source.zip 提取JSphCpu.cpp，仅在 PrepareArtificialStress删除 `const double pressure=PorePressc[p];` 和三对角相减那一行，得到 `Rraw=−epsilon positive(float(sigma_eff))`、rho=1，raw Pa、J pair、ε=.2/n4、时序与其他方程不变。PRE AS=0 early return完全保留。

同函数 omp for之后只加7行output-only探针：`Nstep==4260000 && InterStep==SymPredictor` 时读取4 native IDs7013/7015/6963/7014的原double σeff六分量、absolute float p及**实际已写AS数组**六分量，Log输出4行。条件在真实首次predictor中命中一次，不在4000步循环持续输出、不新增force/数组/主场写入。组件顺序 `(xx,yy,zz,xy,yz,xz)`；p/epsilon/R用9位float可回读格式，σeff用17位double格式。

浅归档含私有JSphCpu.cpp、effective_AS.patch、source.zip、source.json。移除探针并精确补回两条物理行，可逐字节重建原archive成员；legacy helper、pair body及其他生产函数未变。source.zip仅保存私有CPU CPP、新helper和diff，不复制旧大archive/对象，不做SHA。source.json将原capture/archive与私有源/新helper/patch/zip各stat明确分开。

构建恰好2次CL+1次link：

- 物理TU使用实际 `Temp/upl_c08_bedkeep_r1/DebugCPU/int/DualSPHysics.tlog/CL.command.1.tlog` 的JSphCpu.cpp命令，Windows真实参数解析；只换私有源/Fo/Fd并加冻结头include/sourceDependencies。保留项目 `/Zi /Od /RTC1 /MTd /GS /fp:precise /openmp /Gd /TP` 和原宏，不用helper的C++17参数代替物理TU。无PCH、LTCG或CUDA编译，MSVC14.36不变。
- 新helper由通过的coupled_r1机械更名编一次；原积分器和4000步循环不变。link逐项替换**唯一**旧JSphCpu.obj，复用其余85非main物理对象，加新helper.obj，共87对象。两个TU都必须消费同一归档类头；旧DLL/config只copy2到新helper目录。

helper首次VisuConfig后明确打印override：继承的公共“total stress”日志不适用于此私有definition；不为改日志而另编JSph.cpp。正常/failure JSON的新stage与 `AS_stress_space=effective_test_only` 明示，不能仅凭新标签认定生效。

run在实际target终态后独立NumPy double-eigh校验4行探针：分别以float32(σeff)和float32(doubleσeff−absolute pI)作谱输入，`R=−float(epsilon)Q max(lambda,0)Q^T`、rho=1。恢复探针float位型后，actual必须匹配effective参考；预算沿既有AS unit预声明 `32*FLT_EPS*max(1,maxabs(input stress))`，无结果后调宽。至少1ID要求effective/total参考差大于两预算之和且actual不在total预算内；否则不证明消费了新定义。AS_probe.json保存实际值、两个独立参考、误差/预算及原log stat。解析或probe失败不自动重算4000步；若物理已完成，保留完成数据，只修派生诊断。

唯一物理调用仍从原n4 part64恢复一次，原2.5us/4000updates、6805/5000/1805、keep5/退休255、AS.2/n4、CompletedOnly、固定平面政策、原所有finite/J/P0/κ/FS/clock/signed/必要dt门不变，无额外baseline、half、PRE/GenCase、reader或VTK。目标失败时保持实际exit/失败phase/最后完成CSV，不读失败后已释放scratch。

成功4000步后只读持久主场一次导出 `endpoint_soil.csv`：5000原ID升序，21列 id/pos3/vel3/p/κ/J/n/rho/k/σeff6/P0/FS；不额外force/分类或改变primary，无BI4/VTK。原62列states与23列focus完整保留。可用旧GPU part65全22作跨后端描述；旧CPU_total只有4focus/global，**不可声称全5000 same-backend点值对照**。

run仅对保留CPU_total已完成的原行做same step/time前缀的描述性比较，报告末全局指标与4focus差，不设5Pa/.005mm或新的物理通过线。换AS输入会同时改变R幅度和对p的直接依赖；即便压力脉冲减小，也只说明该定义敏感性，不单独证明旧total选择错误、论文唯一正确、团聚已解决或其他ψ可运行。正式公共参数/metadata仍不扩展。

所有新路径fresh且拒覆盖/重试。根完整审阅后才能分别单次执行；当前作者只做AST、差异/还原静态核查，无编译或运行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_as_effective_cpu_r1_build.py --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_as_effective_cpu_r1_run.py --execution-authorized
```

新helper `outputs/upl_c08_as_effective_cpu_r1_helper/component.exe`；物理输出 `outputs/upl_c08_as_effective_cpu_r1`，收据 `logs/upl_c08_as_effective_cpu_r1.build.json/.check.json`。不安装正式runtime，不自动后续计算。

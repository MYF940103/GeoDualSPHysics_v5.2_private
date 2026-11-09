# 全土粒速度方向的一步映射诊断（作者稿）

本文件生成时只完成作者准备与静态检查；尚未构建或执行。新增同 stem 的 CPP、`_build.py`、`_run.py`，未改生产源码、正式输入、旧组件或输出。根全文审阅后分别决定是否构建、调用；无通知器或自动后续。

输入只允许已通过的 `upl_c08_causal_window_GPU_r1/native` 原 90 帧 typed22 中 part71：真实保存时刻约 10.72s、completed=4288000。它是原 total-AS ε=.2/n3、Shepard OFF、damping OFF、CompletedOnly、keep5/fixed-plane 的轨迹；不使用失败 Shepard72 或 n4 保存态。消费实际 run/native 收据及 `upl_c08_causal_prefix90_r1.check.json`，后者已证明全部22数组、实际时钟和 signed clock 对原 r6 前90记录逐字节相同。保留原90/300头，组件只 seek 一条原生记录，不重新解码 BI4。Causal 的观测源码/程序身份与 CPU bedkeep 闭包不同，来源分开绑定，不以 same-binary 为门。

另在实际认证 `RunGravityPreloadHandoffCpu` 导入后、唯一 `RunGravityPreloadRelease` 前，零更新输出 `pre_yield.csv` 全5000 soil ID。它读取导入的 double 六应力、κ、p/P0/J 与实际源 clock；材料使用冻结 `FunSoilMaterial.h::EvaluateMaterial` 的原 trigger/cohesion/residual/Material 构造和 float-radian 常量，经同一 `UpdateDPvars`、`GetInvariants` 得到实际 DP fit、系数、I/q 及 `f=q+DP_phi*I−DP_kc`。材料参数以17位有效数字记录，不从显示角度反算。completion 记录 fmax/ID、`f>=1e−5` 数量和参数；wrapper 只核出处、finite、5000 ID、clock/常量和摘要一致性，**不对 f 的大小设置通过门**。无材料返回、修改、额外 force 或原生解码；这不恢复历史未保存 trial，也不证明10s平衡或旧 law1 每步在 law2 返回下皆 Elastic。

构建机械复用已通过的 stepmap 配方：同封存 bedkeep DebugCPU 的86个 non-main 物理对象加新 helper，合计87；读取同归档头、原 MSVC14.36 flags 与4个 runtime 文件。不重编物理对象。源程序使用原认证 r2GPU PRE 完整导入并唯一释放，产生真实6805角色（1805 fixed、5000 soil、保留5床角的向上法向/NoSlip）；随后逐 ID 恢复所选22字段的主状态和所需缓存，真实 cell sort 后再次恢复、核 ledger/主字段位及墙角色。没有 GenCase、正式 Run 或 GPU restart/replay。

唯一 h=2.5μs。5条互相独立 clone 为 baseline 和 η=+.001、−.001、+.0005、−.0005，对全部5000 soil 原 float 速度的每分量实施 `float(double(v)*(1+η))`；固定墙不动。压力、有效应力、J、κ、P0、位置和其他输入不扰动。每条使用原 protected `ComputeStep_Sym`，即实际 Pre/Cor 两次 force；随后原外层的 cell divide、scalar `TimeStep+=h`、LastDt 与 Nstep 更新。共5个真实积分更新、10次 force；不是零步，也不是一条5步轨迹。局部 RAII FixedDt 恢复原指针，保留原 DtMin/necessary DtVariable 两阶段守卫，设置 SymplecticDtPre/LastDt 与真实 h 一致。不清 bound 或跳异常；失败保留首因及最后完成 clone，不读取未完成子阶段指针。

输入范数直接使用逐分量实际 float 扰动，不用 η² 近似实际输入能量。输出相对同 h baseline，权重始终固定在保存态：

`Qp=Σ V n/Kw (δp)²`；`Qv=Σ V ρ |δv|²`；`Qσ=Σ V[(tr δσ)²/(9K)+dev δσ:dev δσ/(2G)]`。

应力为完整3D有效应力，含 yy，Frobenius 的非对角项乘2；三项一致无1/2。记录输出总二次量/实际输入 Qv 及平方根。它只是指定方向/状态/单步的加权扰动范数，不是总能量定理、全耦合稳定谱、互易性或论文精度。幅度/正负一致性以名义 η 作方向导数分母，float 后并不存在全域唯一精确相对幅度，因此同时导出实际每 ID 的输入 δv、相对 ηv 的误差与加权误差，以及输入方向本身的正负/幅度不一致。

输出 `tests/outputs/upl_c08_velocity_stepmap_r1`：`pre_yield.csv` 5000行、`maps.csv` 5行、`differences.csv` 4×5000行、`consistency.csv` 1行和 completion/Run.out；新 check 为 `tests/logs/upl_c08_velocity_stepmap_r1.check.json`。每行记录实际源/末 clock、初始 δp=0、压力/速度/κ/J范围、FS变化、端点 plane membership变化。`T=trσ_end−trσ_in−3Kh θ_mid` 使用实际 Cor 缓存 θ，仅观察塑性/积分偏差，不设新门、不反推材料 status、λ 或接触反力。端点贴面不能当真实 hit/clamp 次数；ReactionClosed 仍为 false。原 P0位、κ非减、ledger/cache、固定墙位置/角色、完成态 FS2/3 `p<=0`、plane容差与 finite 等门不变。

根可审后分别调用：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_velocity_stepmap_r1_build.py --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_velocity_stepmap_r1_run.py --execution-authorized
```

两个入口均拒绝已有完整或 partial 输出，不重试、不覆盖、不启动求解长窗/half/VTK/native、其他 ψ 或下一任务。结果需独立审查，`physical_acceptance=false`。

Root pre-build lifecycle correction: PRE observation checks the actual imported TimeStep/TimeStepIni/TimeStepM1 clock set by RestoreGravityPreloadClock. GravityPreloadActualTime is a release-event field and remains zero until RunGravityPreloadRelease; it is neither read as a PRE clock nor set early. No physical check or update changed.

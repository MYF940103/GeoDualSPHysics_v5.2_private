# AV15 CPU两帧实施smoke与两个normal native profile（作者稿）

本说明生成时5个新作者文件尚未执行：`upl_c08_av15_smoke_CPU_r1.py` 与 `upl_c08_av15_native_r1.cpp/_build.py/_run.py` 及本说明。已通过的private CAP/build/note/程序、root输入、旧PRE与结果均不修改。无额外GPU Debug、half、物理参数或自动任务。

CPU driver仅两个显式动作：prepare只由原r6 ψ0 Def派生时长/输出与绝对原r2GPU PRE路径，XML `Visco=.1`、AS `.2/n3`、材料/几何不变；raw文本读写保留CRLF。创建fresh tests/configs Def及output/planned_steps.csv，无GenCase/solver。run独立要求根admission与通过的DebugCPU build receipt（路径由CLI传），实际program/runtime均取其Entry；一次GenCase、一次CPU1thread程序，`-nsteps:4000080`。真实TimeMax10.0002/TimeOut.0001，80新更新、2帧step4000040/4000080。原Loader认证.1，私有release后.15由source/log说明；启动Config仍.1，typed .15另由native验证，不称run已通过原生门。

CPU实际调用沿旧e.invoke，保留Win32/Popen/child creation/exe/argv/parent；物理0出口立即标solver_completed，后输出检查失败不重跑。成功run收据 `logs/upl_c08_av15_smoke_CPU_r1.run.json` 含passed/solver_completed/exits0、实际steps/frames/Hardware/summary及program/build/source/PRE/input/seed/plan/GenCase_call/actual_call/consumed绑定；actual CPU call为 `.solver.call.json` child协议，不假造GPU target协议或backend/preparation字段。无queue/native/VTK/window后续。根向GPU owner显式提供两个roles：`cpu_smoke_run` 为该run Entry，`cpu_smoke_native` 为下面的native Entry；不猜未来review文件。

一个reader只允许 CPU2/end4000080/cadence40 与 GPU30/end4120000/cadence4000 两个normal profile。source实际scalar clock来自原PRE并逐步+=2.5μs，part0是post40或4000更新，不是t0；原90/300数据不混入。builder沿已通过causal generic6805派生，仅stage/profile adapter变化；CSV正确保持 left `AS_Bui2008(0.2`、right `3)`、full marker `AS_Bui2008(0.2;3)`，并做原3-anchor逆向相等证明。仍封口6个Release utility objects+main，不编物理程序。每frame原22/6805、5000soil/1805fixed、P0/κ/J/n/V/rho/k/cache/FS/plane/clock/signed/normalRun.csv/计划原门不变；AS.2/n3、CompletedOnly双键缺失、Shepard/damping OFF均保持。

新增且严格要求的typed target头：`DynamicArtificialViscosityPolicy` text=`ReleaseOnly`、`DynamicArtificialViscosityOverrideActive` bool=true、`DynamicArtificialViscosityCoef` float `.15f`。adapter仅lazy头扫，数值数组由core一次读取；原source PRE没有这三键，不套target gate。不存在第23数组。SourceBackend由真实privateprogram/directargv/Hardware证明，reader只记录传入backend，不冒称库能独立证明硬件。

reader将来program `outputs/upl_c08_av15_native_r1_build/C08AV15Native_win64.exe`，build receipt `logs/upl_c08_av15_native_r1.build.json`。CLI沿11参数：`--read psi0 CPU|GPU DATA PRE END SAMPLES 1 PLAN FRESHOUT`。completion stage `upl_c08_av15_native_r1`、metadata同stage加`.metadata`、leaf `bedkeep_metadata.json`，新增AV_policy/AV_override_active_expected/AV_coefficient_float_reference/AV_override_headers；profile smoke或window，二者smoke_final_only=false。CPU ledger/cache/κ各10000、fixed3610、P013610、planes20000、signed2；GPU各150000、fixed54150、P0204150、planes300000、signed30。

native wrapper要求根显式提供真实 `--run-check`，不调用owner/solver或猜旧failed/adoption记录。CPU用其真实invoke child协议，GPU用HG owner的direct owned协议；核原program/build/capture/PRE/input/seed/plan/实际出口与无active/existing native后一次读，normalRun.csv实际end/count仍由core硬核。输出各job的 `native_r1`，收据 `logs/<job>.native_r1.json`，标准passed/source_run/actual_call/completion/metadata/original_native_guards_passed/outputs/consumed_stats_unchanged；失败保留partial，不重复、不自动下一阶段。

根全文审后可分别决定（本作者任务均未执行）：

```powershell
python -B tests/support/upl_c08_av15_smoke_CPU_r1.py prepare --build-check <实际DebugCPU.build.json> --execution-authorized
python -B tests/support/upl_c08_av15_smoke_CPU_r1.py run --build-check <同receipt> --admission <根准入JSON> --execution-authorized
python -B tests/support/upl_c08_av15_native_r1_build.py --execution-authorized
python -B tests/support/upl_c08_av15_native_r1_run.py smoke --run-check <实际CPU.run.json> --execution-authorized
python -B tests/support/upl_c08_av15_native_r1_run.py window --run-check <未来真实GPU.run.json> --execution-authorized
```

这只是AV release override实施核验及后续窗口的原生读资格，不是物理验收、半步误差、TPI或接触/材料闭合证明；`physical_acceptance=false`。

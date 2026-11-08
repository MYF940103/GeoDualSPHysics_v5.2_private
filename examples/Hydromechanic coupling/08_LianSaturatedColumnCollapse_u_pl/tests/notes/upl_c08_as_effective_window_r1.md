# 条件性GPU fresh-release effective-AS/n3窗口：作者准备

仅新增同名jobs Python和本说明，事前确认不存在且未跟踪。生成时未执行/import，未生成XML/BAT/计划/owner，未调用GenCase、solver、reader、构建或queue。旧root XML、原PRE、runtime与结果均只读。

只有根审完CPU effective实际终态与私有GPU build后，手工准入这**唯一**TAG `upl_c08_as_effective_window_GPU_r1`。两动作显式独立，prepare不物理计算，run不自动native/VTK/下一作业：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_as_effective_window_r1.py prepare --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_as_effective_window_r1.py run --execution-authorized --notify
```

prepare从根r6 Def原文本只替换原r2GPU Part1000绝对PRE与TimeMax10.90及相应说明；原ε.2/n3、Cubic hdp1.2、dt2.5µs/TimeOut.01、keep5/plane/CompletedOnly、材料和Ck2等不改。生成仅tests/configs中新Def/BAT/90行plan和logs prepare收据。没有将n4 part64或其它塑性保存态当PRE，也不重算10s。

run要求根 `logs/TAG.admission.json`：passed/allowed_job、AS_stress_space=effective_test_only、ArtificialStressCoef=.2/Exp3、FreeSeepagePondingPolicy=CompletedOnly、planned_global_end4360000/expected_saved_frames90、cpu_effective_result_reviewed=true、cpu_effective_result真实Entry、source_build真实Entry绑定下述新GPU build收据；notify另需root_thread_id等于**启动时实际**CODEX_THREAD_ID。CPU结果允许真实exit0/1，由根判断其科学结果，但必须有实际定义probe通过，不让脚本凭预期认定CPU成功。

新GPU程序只取 `logs/upl_c08_as_effective_gpu_r2.build.json` 的实际通过program：私有单CU编译+112保留对象/113link、trace宏off、source capture的exact_porepress_branch_only与逆还原proof。目标 `outputs/upl_c08_as_effective_gpu_r2_build/DualSPHysics5.2_GEO_win64.exe`，7个DLL/config由build复制并匹配runtime_r6 stat；GenCase使用原r6官方程序。r1仅编译失败、无link/物理运行，其证据原样保留；r2仍绑定同一已封口r1私有source，物理patch未改。**不以build stage标签、旧公共total-AS日志或旧native AS metadata声称effective定义被运行时直接证明**；定义证据来自根已审私有源码、真实编译/链接/program绑定及CPU独立谱probe。此变体不新增公共XML/metadata。

fresh OUT创建后复制原准备plan，实际GenCase一次生成新seed三伴随文件，再通过原 `base.owned` 等待唯一真实GPU solver并持Win32句柄：每30秒status/原始最后PART、原start/call/owner_admission、PID创建时间/exe/argv/parent、真实双出口与冻结stat保留。目标360000新updates/global4360000/90帧至实际τ约.90。退出0先记solver_completed，后检查normal Run.csv/实际Hardware、原7060注册/无排除、一次255退休/五床保留和真实PRE clock，再标native pending。若纯输出审查失败，保留已完成求解，不重跑。

只在封存run且实际solver call存在后，沿原机制向owner启动时冻结的root线程尝试一次45秒queue；失败/超时不重发、不重挂旧watcher、不做连通自测。此owner无其它完成机制。失败保留真实首因、partial和最后原始console行，不推未保存时间或补造actual steps。

90帧原生审查将由根另行准入：可以复用已通过causal90 n3读器**本体**的22/6805/5000soil/1805fixed/P0/J/κ/FS/ledger/keep/plane/clock/signed数学；不要要求不存在的causal trace文件，读器stage也不是AS定义的物理证明。本轮不启动读器、不另编适配器。结果只是同原PRE重新撤墙的单定义敏感性，不是物理/论文精度验收，也不自动放行其他ψ。

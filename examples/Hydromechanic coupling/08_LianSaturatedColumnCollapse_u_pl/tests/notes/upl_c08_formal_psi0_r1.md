# ψ=0° 根目录正式 GPU 计算 owner（author-only）

本文件及 `support/upl_c08_formal_psi0_r1.py` 已准备，尚未运行。该 owner 必须调用真实根目录 `xCaseLianSaturatedColumnCollapse_psi0_shared_r3_win64_GPU.bat --unattended`；由 BAT 原有流程产生唯一一对 GenCase 和 solver，不另行 prepare-full、不重复 GenCase、不改源码/正式输入/现有源输出。输出为根目录 `CaseLianSaturatedColumnCollapse_psi0_shared_r3_GPU_out`。

前置：新 ψ0 short run 已实际达到 global4040000且其独立原生检查通过；同短窗的postprocess_r3.json必须已通过native、PartFluid、PartBound和图CSV实测，实际三份post-tool call及输入输出stat一并绑定。原source是服务器复制回来的r2 GPU `data/Part_1000.bi4`，不重跑10s，不使用post-plastic PART。根 BAT 已显式设置 C08_PRELOAD_SOURCE 指向该r2源，shared r3 launcher执行现有CSV调度检查，再由原生loader核完整contract/state。runtime_r3和其mDBC Release build/所有必要输入用stat绑定，不做SHA。

根线程完整阅读并核实 `codex queue --help` 后，唯一启动命令（从case08根目录）：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_formal_psi0_r1.py --short-native-check tests/logs/upl_c08_resume_r1_psi0_GPU_short_native_r1.check.json --execution-authorized --notify
```

拒绝已有正式out、任一同名owner/日志/收据或其它活动GPU solver，不停止别的进程。CMD wrapper直接Popen持有真实句柄；其递归子进程中仅按runtime_r3的真实完整exe识别GenCase与solver，分别在退出前OpenProcess保存句柄、真实PID/创建时刻/exe/argv/parent及最终Win32 exit。要求仅一对真实子程序且确切参数/parent匹配。若wrapper先退出而owned target仍活跃，记录异常并继续观察原handle，不启动其他进程、不自动修复/重试。solver退出而wrapper仍在后处理时状态标为solver_completed_postprocessing；状态每30s只记录Run.out最后一个完整PART原行，不把截断报告或Run.csv六位小数称为精确原生时刻。

实际wrapper/GenCase/solver退出首先封口到 `tests/logs/upl_c08_formal_psi0_r1.call.json`，随后检查Run.csv global5200000、原注册7060/2060、零排除、legacy MR1 ElasticV1导入、一次260退墙、实际源scalarclock与4Mcompleted。run.json的 `actual_exit/actual_Win32_exit` 指真实solver handle出口，并另存wrapper出口；`input_xml`为正式out实际执行的case.xml，满足后续reader相同schema。真实BAT完成solver后还会调用正式后处理，owner等待整个wrapper并检查postprocess_r3.json、native completion、三份真实post-tool call、完整Fluid/Bound与五个时刻PNG/CSV。成功记录native已完成一次、physical_plot_review_pending=true和physical_acceptance=false，仍需人工/根线程物理图与论文比较；不重复调用reader/VTK，不启动其它ψ。若solver0而post失败，仍记录solver_completed=true及实际全局步数/时钟，failed_stage=postprocess，只修后处理，不重跑solver。

最终run.json封口后，如启用--notify，仅向已验证的同一个 CODEX_THREAD_ID=01a07683-bc64-7463-8db7-9ee6243967d8 调用固定旧路径codex.exe的queue一次、45s超时。attempt在调用前保存，成功/失败/不确定均保存结果；不重发、不重新布防、无连通性自测。消息说明本次正式ψ0已经由BAT完成一次native/VTK/图CSV，待物理图审，禁止重复解码；其余ψ组依用户原授权在根线程审查后另行推进，不据通知直接自动启动solver。

可另传 --pipeline-check 指定根线程的已通过短窗pipeline check并绑定；不会要求尚未写出的新check。实际已通过短窗postprocess_r3.json为必需准入。本轮仅新增此owner与note；无需新构建，旧程序/ZIP和服务器/本机源保持原样。正常计算的所有证据保留；失败不虚构未保存停止时刻，禁覆盖/重复计算。后续ψ+2.5/−5正式组将用独立job标签安排，不能为等待通用多组框架推迟本组已准入任务。

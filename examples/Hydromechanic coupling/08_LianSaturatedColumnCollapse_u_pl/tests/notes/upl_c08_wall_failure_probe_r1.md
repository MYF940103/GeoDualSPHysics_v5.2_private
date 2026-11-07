# C08 动态墙失败的一次error-only诊断复现（author-only）

新增owner `support/upl_c08_wall_failure_probe_r1.py`、本note和新config；尚未创建runtime/output、GenCase或运行solver。新config `configs/upl_c08_wall_failure_probe_r1_Def.xml` 是原失败root实际已解析 `CaseLianSaturatedColumnCollapse_psi0_shared_r3.xml` 的完整字节复制，不改材料、边界、PRE路径、TimeMax13或任何物理值。

本次只使用根线程新建、数学未改而异常处增加日志的新GPU Release程序。默认build receipt为 `logs/upl_c08_wall_diag_Release_r1.build.json`，必须实际passed且真实wait/Win32 exit0。旧runtime_r3程序及源捕获不改；新程序与原runtime必要DLL/config/GenCase复制到全新浅目录 `outputs/upl_c08_wall_failure_probe_runtime_r1`。新求解数据仅放 `outputs/upl_c08_wall_failure_probe_r1`，旧formal失败输出原样保留。

根线程完整阅读并确认new Release build通过后，唯一命令（case08根目录）：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_wall_failure_probe_r1.py --build-check tests/logs/upl_c08_wall_diag_Release_r1.build.json --execution-authorized
```

owner一次真实GenCase，再一次真实GPU target，复用原r2 10s Part1000专用PRE，不重算预载、不从post-plastic PART重启。仍2.5µs/TimeOut.01s、TimeMax13，唯一CLI全局 `-nsteps:4048000` 将本次最多限制为48,000个新updates（0.12s）。这不是另一次完整3s尝试，更没有half或后续自动扩展。

复用已审 `mdbc_partition_components_r3.invoke` 的真实Popen/Win32句柄和身份逻辑：GenCase仅接受0；solver的0和1分别如实处理。原helper在rc1封口真实call后抛出的异常可被本调用者接住，再读真实sealed call，绝不伪造0或LASTEXITCODE。`start.json`记录真实owner预调用准入，子程序的真实创建时刻/exe/argv/parent/出口保留在各自不可覆盖call中，而不是捏造一个提前取得的子PID。

solver rc0必须真到global4048000且正常无排除，表示本次短窗未复现；rc1必须原墙错误和恰好一条新诊断行，表示已捕获本次错误。两者都可成为closed diagnostic observation，但不等于物理pass。诊断字段为stage、sorted_slot、native_id、step_start、step、B和normal，raw原行完整保存。stage0=state、stage1=C；不把借用invalidg的stage2路径冒称已观测。step_start/step是本次force阶段的实际TimeStep/Nstep，不当作post完成时间，不改写旧formal错误时刻。

必要源/配置/程序仅stat绑定，不扫SHA。拒绝已有runtime/output/owner/call或其它活动GPU；失败保留原始日志、actual exits及最后完整PART原行。最后console时间仍标为截断报告，绝不是未保存原生失败时刻。本工具不调用native decoder/PartVTK、队列、watcher或后续solver；无重复、重试、覆盖或自动清理。root审后才能执行。

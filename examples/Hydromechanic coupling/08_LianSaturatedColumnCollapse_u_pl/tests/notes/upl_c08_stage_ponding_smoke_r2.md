# 2 ms smoke 启动日志检查修复与 CPU 离线采用

新增同名 support Python / 本说明，事前查两个目标不存在且未跟踪；原 r1 owner / note / run / call / 输出保留原字节。此次未执行、import、GenCase、solver、reader 或 queue，不改仍在构建的源码 / capture / r2 build 依赖。

实际 CPUdebug r1 的 Popen / Win32 / target 都为0，两帧完成；原后检查误要求启动日志已显示 ReleasedSubstages。真实 Run.out 第72行仍为唯一旧 completed-only 文本，第88行才出现 GravityPreload requested，证明该启动说明发生在容器配置前。它不能证明 released runtime policy 开关状态；不得据此推断新数值分支未启用。

`normal_output` 只修这一启动说明判据：仍核正常结束、AS、NoPen、一次 keep5 / retire255、实际源时钟、实际 end / count / registry / no exclusions；另明确要求唯一已知旧 FreeSeepagePolicy 行先于唯一 GravityPreload requested 行，并记录 `startup_precedes_gravity_config=true`、`startup_policy_proves_released_substages=false`、`released_policy_native_and_trace_review_pending=true`。真正 ReleasedSubstages 的 typed per-PART 元数据和 half 事件留给已构建 reader / 新 trace checker 独立审阅，其余物理 / 时间 / 参数不变。

future `GPUdebug` / `Release` 只改新 job tag 后缀 `_r2` 及 owner/note 绑定，仍使用本轮 `stage_ponding_{Debug,Release}_r2.build.json`；800更新 / 两帧 / 原 PRE / AS .2 / n3 / GPU Debug memcheck 全部原样。r2 没有 CPUdebug run 选项，避免重新求解已完成 CPU。每次 root 只选一个 action，无自动连锁：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_stage_ponding_smoke_r2.py adoptCPU --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_stage_ponding_smoke_r2.py GPUdebug --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_stage_ponding_smoke_r2.py Release --execution-authorized
```

`adoptCPU` 仅消费原 CPU r1 已失败的 run / actual call / start / admission / 真0出口和实际 program / build / input / PRE / plan / 两 PART 绑定，确认首因恰为旧错误日志门、无原 solver 活动，以修后的只读后检查封新 `logs/upl_c08_stage_ponding_CPU_adopt_r1.json`。新记录保留 `original_run`、原 passed=false / 首因 / 原调用1次；本次 solver / GenCase / reader 调用均0。重新核已消费 stat，但不回填或改写旧完成记录、不宣称原 r1 已通过。正常采用仍 native/trace pending、physical=false，不触发 reader 或下一阶段。无 SHA、重跑或新物理阈值。

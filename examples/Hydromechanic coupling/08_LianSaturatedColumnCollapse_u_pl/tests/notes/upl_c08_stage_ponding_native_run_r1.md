# ReleasedSubstages 2 ms 独立 native wrapper

仅新增同名 support Python 和本说明；事前查不存在 / 未跟踪。未启动 reader、solver、构建、VTK、后处理或 queue。只允许选择 `CPUdebug` / `GPUdebug` / `Release` 中一组，未知 window owner 不猜测也不接入。

GPU 消费新 `upl_c08_stage_ponding_smoke_<选项>_r2` 的正常 run；CPU 只消费独立 `upl_c08_stage_ponding_CPU_adopt_r1.json`，保留并核其指向的原 CPUdebug r1 safe-solver / failed-startup-log-postcheck，绝不改原 run 或重跑。三组均核真实 call / start 及 actual call 指向的 admission、Popen / Win32 出口、PID / creation / exe / argv / parent、program / 新 r2 build / source_r2 / 原 r2 GPU PRE、生成输入和两帧原 plan。GPU Debug 还核 memcheck 零错误 / 零泄漏及真实 target 记录。复用新 r2 owner 的只读输入和后检查；其旧启动文本仅表示发生于重力容器解析前，ReleasedSubstages 实际行为由 native header / trace 独立证明，不重复扫描 trace。CPU 跨后端接收原 GPU PRE 的事实保留。

只有正常有效 run、无活动同 program / DATA consumer，且 fresh native / call / log / receipt 均不存在，才通过既有 `mdbc_partition_components_r3.invoke` 调用一次：

```text
C08StagePondingNative_win64.exe --read psi0 BACKEND DATA PRE 4000800 2 1 PLAN FRESHnative
```

独立 reader 使用已闭合六 utility 对象；原22数组 / 6805 ID / 10000 ledger / 13610 P0 / 3610 fixed / 20000 plane / 两个非空 signed 区间及实际 scalar 时钟门不变。每帧核 keep5 / retire255、AS=.2f / 指数3f / ReleaseOnly、新 ReleasedSubstages / Active 元数据。旧 PRE 保持 legacy1，目标为 MaterialLawVersion2；所有数值预算及单次唯一数组解码不变，不把 backend CLI 当 reader 独立证明。

root 全文审阅且对应 run 真正封口后，独立选择一次：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_stage_ponding_native_run_r1.py CPUdebug --execution-authorized
```

另两选项同式。输出为该实际 smoke 目录下 `native`；唯一收据 `logs/<smoke-tag>.native.json`，含 source_run / actual_call / completion / metadata / outputs / consumed 绑定。失败或部分 native 保留，不覆盖、重解码或重新求解。trace 仍须另用新 checker 的 smoke2ms profile；normal native 通过不自动准入 .66s 或物理验收。原正式 runtime / outputs / canonical / 旧工具不变，无 SHA。

# ε=.25/n3 的30帧原生读器（作者稿）

本说明生成时只完成作者准备，尚未构建、读取或运行物理程序。只新增 `support/upl_c08_as025_native_r1.cpp`、`_build.py`、`_run.py` 与本说明；旧 core/reader、生产源码、runtime、正式输入与全部结果不改。

只准入正常完成的 ψ0/GPU job `upl_c08_as025_window_GPU_r1`：同原 r2GPU `Part_1000.bi4` 认证弹性 PRE、total-AS ε=.25f/n3、CompletedOnly、keep5/fixed-plane、Shepard/damping OFF。源actual clock取PRE，原 dt2.5μs，120000新更新/global4120000、30保存态，计划为 `4000000+(part+1)*4000`；part0是τ≈.01，不是t0。原 normal Run.csv 必须确认实际 end/count，无失败partial分支。

adapter 从已通过 causal reader 机械派生，仅限制为30/4120000、改变 typed AS coefficient 为 `.25f` 和输出stage。每帧严格核 ReleaseOnly/Active、float `.25f`/`3.f`、keep5/retired255精确元数据，CompletedOnly 两个实验ponding键都必须不存在。源 PRE 不套 target AS gate。原核心每帧仍核 typed `SoilDampingActive=false`、`PoreShepardActive=false`、NoPen fixed-plane/ReactionClosed=false、原7060 registry与6805非连续活动ID、5000土/1805 fixed，以及22数组/P0/κ/FS/geometry/ledger/cache/实际clock/signed interval全部原预算。

builder 复用封口6个 Release BI4 utilities（无 JSph对象）+本main，沿原 MSVC14.36 `/O2 /MT /fp:precise /GL-`。在新build目录生成 core：先调用已审 generic6805 派生，再只将严格 Run.csv AS片段改为 `AS_Bui2008(0.25;3)`、stage改为本tag；通过逆向替换与 generic6805 core 全文相等，保留实际 diff/derivation/stat。它修读表期望，不改原CSV或通用宽度门，不改任何物理/numericguard。无第二次数组 decode；adapter 仅扫懒加载头，PRE只由core读一次。

未来构建位置：`tests/outputs/upl_c08_as025_native_r1_build/C08AS025Native_win64.exe`；收据 `tests/logs/upl_c08_as025_native_r1.build.json`。原11参数接口：

```text
C08AS025Native_win64.exe --read psi0 GPU DATA PRE 4120000 30 1 PLANNED_STEPS_CSV FRESHOUT
```

wrapper 只在根独立授权、实际 run/start/call 封口且所有 Popen/Win32/ownership/argv/PRE/input/build/runtime/PART/plan绑定通过后一次调用。输入 fixed job，输出 `tests/outputs/upl_c08_as025_window_GPU_r1/native_r1`；收据 `tests/logs/upl_c08_as025_window_GPU_r1.native_r1.json`。保护 native/native_r1、既有call/log/check及活动exact程序/DATA consumer，不停止任何进程、覆盖partial或重复读。物理程序绑定原 `upl_c08_bedkeep_Release_r1.build.json` 的实际program bytes/mtime与source，允许有来源绑定的copy2隔离副本；不依赖 causal trace文件或 build tag冒充物理证明。actual XML的 special/parameters 与原 r6 比较，仅允许声明的 ε、TimeMax10.3/TimeOut.01及注释差异。

新normal completion stage为 `upl_c08_as025_native_r1`，metadata为同stage加`.metadata`，leaf仍 `bedkeep_metadata.json`。原 typed22布局212B/particle、6805/22/30原头不变；ledger/rho/κ检查各150000，fixed54150，P0 204150，planes300000，signed30。顶层成功收据沿 `passed/source_run/actual_call/completion/metadata/original_native_guards_passed/outputs/consumed/consumed_stats_unchanged/decoder_invocations=1`。

作者阶段不要求未来run已存在；实际执行时缺任何必要证据即拒读。预期owner最小接口沿既有causal窗口：run含 passed/exits/steps/frames、program/source_build/source_capture/source_archive/PRE/input_xml/seed/plan/GenCase_call/actual_call/Run_csv/Run_out/PARTs/consumed；start/call/admission绑定唯一direct Release solver；root admission明确 allowed_job、ε=.25/n3/CompletedOnly。wrapper不启动GenCase/solver/VTK、不自动分析、下一job、queue或其他ψ。参数对照不是half/理论误差、旧PRE的同算子合同或物理验收。

根全文审后可分别决定：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_as025_native_r1_build.py --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_as025_native_r1_run.py --execution-authorized
```

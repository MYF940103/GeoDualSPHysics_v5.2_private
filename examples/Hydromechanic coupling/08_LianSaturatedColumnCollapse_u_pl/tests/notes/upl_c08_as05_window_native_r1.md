# C08 AS=.5 / n=2.55 窗口原生读取器（author-only）

仅新增同 stem 的 `.cpp`、`_build.py` 和本 note；同名不存在且 exact git ls-files 为空后作者。旧 window reader/helpers、所有 source/输入/结果均不改。只做 Python AST 与内存派生文本核验，**没有 build、reader、solver 或 decode 执行**。

新 tag `upl_c08_as05_window_native_r1`；目标为同一个已封口 Release trace 程序的单因素 ε=.5、指数2.55 窗口，264000 次新更新/global4264000/66 帧，6805=1805 固定+5000 土、22 数组。这里只准备读取实现，不声称未来 run/native 已通过，也不证明后端或物理精度。

## 精确机械差异

- 新 adapter 从 `upl_c08_stage_trace_window_native_r1.cpp` 机械派生：`.2f`→`.5f` **2 处**（typed header coefficient Bits、metadata float reference）；include leaf **1 处**改为 `as05_window_core_r1.cpp`，metadata stage **1 处**改为新 tag，首行说明 **1 处**。指数 `2.55f`、66/4264000/CLI/所有 keep/NoPen header 条件均不变。
- 新 builder 的 derive_core 直接调用旧 `window.derive_core(raw)`，不修改或 monkeypatch 旧模块。完整阅读的旧链为 window→formal→bedkeep→AS CSV repair→plane core。
- 相对旧**已派生 window core**仅 **3 个各出现1次的锚**：`left="AS_Bui2008(0.2",rightpart="2.55)"` 改0.5；`marker="AS_Bui2008(0.2;2.55)"` 改0.5；completion stage 旧 window tag 改新 tag。前两处属于同一已知内嵌分号片段，右片段/唯一 Configuration/宽度+1/Nbound-Nfixed 位置/仅一次 marker 等检查保留，不泛化 CSV 修复、不改 raw Run.csv。
- 新 build 才会在 fresh builddir 生成原 plane→AS05 完整 diff、旧 window派生core→AS05 三锚 diff 和 core_derivation.json；严格计数并反向归一化验证仅这三锚有差异。字段数组解码仍仅原 core 一次，adapter只 lazy header scan。

## 全部保留的数值资格

原66帧 profile：首 completed4004000、末4264000/零基 saved Step4263999；PRE source MaterialLawVersion1/2 原资格；标量 clock 从实际 certified.Time 逐次 `+=2.5e-6`（不写死10.66），原 `<=1e-14` 时钟与 signed dterror 单边门、不允许空区间；原 P0 bits、J/n/rho/k ledger5e-13、rho cache bits、κ有限/非回退、非空FS2/3 p<=0、4e-8m固定平面门、exact ID/keep5/实际退休255/原目标260、22-array布局/所有有限检查不变。不会把 AS=.2 数据当作 AS=.5：每帧 typed coefficient 必须 `.5f` 且 exponent `2.55f`。

## root 审阅后的独立单次 build / read 接口（此处未执行）

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_as05_window_native_r1_build.py --execution-authorized
```

构建复用 `logs/mdbc_partition_ReleaseCPU_r1.build.json` 的6个封口 Release utility objects：JPartDataBi4/JPartDataHead/JBinaryData/JObject/JException/Functions，加新 main 共7；从同 source capture archive 取头。MSVC14.36，C++17，`/O2 /MT /fp:precise /GL-`，wmainCRTStartup。没有 JSph object、CUDA、全工程/solver build、Debug CRT 或 SHA 扫描。

新程序 `tests/outputs/upl_c08_as05_window_native_r1_build/C08AS05WindowNative_win64.exe`，新收据 `tests/logs/upl_c08_as05_window_native_r1.build.json`。reader CLI保持8参：

```text
C08AS05WindowNative_win64.exe --read psi0 CPU|GPU DATA CERTIFIED_PRE 4264000 FRESHOUT
```

FRESHOUT必须不存在，失败保留不覆盖/不重试。未来 read 由独立 owner 绑定真实同job程序/正常Run.csv/实际退出/输入/ε=.5；`backend_proven_by_reader=false`保留。输出叶名与旧实现相同 typed22.bin/typed22_layout.csv/clocks.csv/history.csv/plane_gaps.csv/completion.json/bedkeep_metadata.json；stage为新tag及`.metadata`。NoPen policy仍FixedPlaneStageProjectionReleaseOnly、ReactionClosed=false，AS仍ReleaseOnly/Active；physical_acceptance=false。

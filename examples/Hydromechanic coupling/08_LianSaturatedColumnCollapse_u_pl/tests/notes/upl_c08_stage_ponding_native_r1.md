# ReleasedSubstages smoke/window native adapter（仅作者，尚未构建或读取）

新文件为 `support/upl_c08_stage_ponding_native_r1.cpp`、`support/upl_c08_stage_ponding_native_r1_build.py` 和本说明。原 generic bedkeep、固定66 n3 adapter、现有程序与结果均不修改。

预期程序为 `outputs/upl_c08_stage_ponding_native_r1_build/C08StagePondingNative_win64.exe`，构建收据为 `logs/upl_c08_stage_ponding_native_r1.build.json`。本轮只有 Python AST 与纯文本派生核验，未执行 build、reader、solver、VTK 或任何 owner。

调用保持 generic bedkeep 的 **11 argc**，明确 plannedCSV、END 和 SAMPLES：

```text
C08StagePondingNative_win64.exe --read psi0 CPU|GPU DATA PRE END SAMPLES 1 PLAN FRESHOUT
```

仅支持两种独立 profile：smoke 为 `END=4000800 / SAMPLES=2`，PLAN 两行为 `0,4000400`、`1,4000800`；window 为 `END=4264000 / SAMPLES=66`，PLAN 为 part0..65 对应 completed step4004000..4264000、步距4000。两者 CSV 首行均须为 `part,completed_step`，adapter 在任何数组读取前核对全部精确步数，随后原内核再次核对实际 savedStep+1、Run.csv 及实际文件数。只接受 NoPen 参数 `1`、psi0，CPU/GPU 标签不自行证明执行后端。

每帧额外扫描 lazy metadata：`FreeSeepagePondingPolicy` 必须 typed text `ReleasedSubstages`，`FreeSeepagePondingActive` 必须 typed bool true；AS 必须 `ReleaseOnly`、Active true、epsilon 与 `.2f` 位相同、exponent 与 `3.f` 位相同。KeepBedOverlap、五个明确 ID1800/1852/1904/1956/2008、原 target260/实际退休255 均沿原严格门。该层不读数组、不另载 PRE、不调用其他 reader。

`derive_core` 先完整调用原 `upl_c08_bedkeep_native_r1_build.derive_core`。相对于其 generic 派生 core，只有三个精确文本替换，各 **1 次**：

1. `rightpart="2.55)"` → `rightpart="3)"`。
2. `marker="AS_Bui2008(0.2;2.55)"` → `marker="AS_Bui2008(0.2;3)"`。
3. stage `upl_c08_bedkeep_native_r1` → `upl_c08_stage_ponding_native_r1`。

前两项只识别 Run.csv Configuration 中已知 AS 内嵌分号片段；原宽度、唯一 marker、右侧列锚点和数字检查保留，原 CSV 不写回。builder 会反向替换并要求与 generic bedkeep 派生文本逐字相同，保存全派生 diff、仅三项 diff 和 `core_derivation.json`。generic 11参数 main、Planned、22字段/6805 IDs、固定1805/土5000、P0、J/n/rho/k ledger/cache、κ非回退、FS2/3 p≤0、plane gap、scalar逐步 `+=dt`、savedStep/真实时钟和原 signed dterror≤1e−14 数值门均不变。没有按结果修改预算。

输出沿原 `typed22.bin`、`typed22_layout.csv`、`clocks.csv`、`history.csv`、`plane_gaps.csv`、`completion.json`；completion stage 为新 tag。另保留叶名 `bedkeep_metadata.json`，其 stage 为 `upl_c08_stage_ponding_native_r1.metadata`，记录 profile/cadence、AS .2f/3.f、ReleasedSubstages/Active 及扫描计数。核心数组只解码一次，source PRE 只由原内核认证一次。缺元数据、旧 completed-only 程序、其他保存计划或已存在/部分输出均拒绝；失败保留，不重读或自动重试。

构建仅复用 `logs/mdbc_partition_ReleaseCPU_r1.build.json` 封口的六个 utility 对象：JPartDataBi4、JPartDataHead、JBinaryData、JObject、JException、Functions，并使用同一 source capture/archive 的头文件。当前三CPP修补无需进入该纯 BI4 工具 closure。新编译 adapter 一个对象，总链接七对象；MSVC14.36.32532、`/O2 /MT /fp:precise /GL- /std:c++17 /D_HAS_STD_BYTE=0`，link `/ENTRY:wmainCRTStartup /SUBSYSTEM:CONSOLE /MACHINE:X64`。无 JSph/GPU/Debug 对象混入，无全工程构建。root 全文审查后，独立一次 builder 命令为 `python -B support/upl_c08_stage_ponding_native_r1_build.py --execution-authorized`；本说明不宣称已执行。

这是保存状态与元数据验证，不观测未保存半步，不证明压力投影质量闭合、张拉稳定或物理精度；ReactionClosed 仍为 false。任何后续读取均由 root 按已完成的对应 run 单独安排，不自动启动下一阶段。

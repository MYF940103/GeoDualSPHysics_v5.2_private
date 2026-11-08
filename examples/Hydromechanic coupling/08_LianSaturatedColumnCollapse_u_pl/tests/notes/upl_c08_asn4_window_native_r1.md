# ε=.2 / n4 / CompletedOnly：90帧原生适配作者稿

仅新增同stem的 `.cpp`、`_build.py`、`_run.py` 及本note，均未构建/调用reader/求解。新增前已确认文件不存在且精确 git ls-files 为空。旧 n3、AS05、causal、formal readers、helper、源代码、r2 PRE和所有已消费收据/输出保持不变。本组件不是物理验收，也不准入其他ψ、半步链、新smoke或新PRE。

## 固定范围及CLI

- Job：`upl_c08_asn4_window_GPU_r1`；宏关闭的 `support/runtime_r6/DualSPHysics5.2_GEO_win64.exe`，绑定 `logs/upl_c08_bedkeep_Release_r1.build.json` 及已封口runtime复制记录；不要求stage/causal CSV。
- 原r2 GPU认证Elastic/law1 PRE `CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4`，global4M实际时钟；目标law2 ψ0、ε=.2f、exp4f，CompletedOnly。source未重算。
- 唯一profile：360000更新、90帧、global end4360000；计划为 `4004000,4008000,...,4360000`，每个part依真实 `planned_steps.csv` 核查。实际时间仍由原core从certified.Time逐次scalar+=dt，绝不以整数10或n*dt代替。
- Reader CLI：`C08ASN4WindowNative_win64.exe --read psi0 GPU DATA PRE 4360000 90 1 PLAN FRESHOUT`。
- 构建候选：`python -B tests/support/upl_c08_asn4_window_native_r1_build.py --execution-authorized`，程序写全新 `tests/outputs/upl_c08_asn4_window_native_r1_build/C08ASN4WindowNative_win64.exe`，build收据 `tests/logs/upl_c08_asn4_window_native_r1.build.json`。
- 唯一读候选：`python -B tests/support/upl_c08_asn4_window_native_r1_run.py --execution-authorized`；仅在root全文审阅、正常run封口后单独调用。fresh输出 `tests/outputs/upl_c08_asn4_window_GPU_r1/native_r1`，check `tests/logs/upl_c08_asn4_window_GPU_r1.native_r1.json`。失败保留call、日志和partial，不覆盖、不重试，不自动VTK/图/solver。

## 派生证明与数值守卫

与既有n3相同的6805数值基础来自 `upl_c08_bedkeep_native_r1_build.derive_core`，保留通用11参数/Planned，而不是把旧固定66帧main改成另一套时钟。新core在该通用基础上只做三处各1次精确替换：`rightpart="2.55)"`→`rightpart="4)"`、`marker="AS_Bui2008(0.2;2.55)"`→`marker="AS_Bui2008(0.2;4)"`、原bedkeep completion stage→新stem。构建时逐anchor计数、反向归一化必须逐字等于原通用core，并保存两份diff和core_derivation.json。只修已知内嵌AS分号的解析期待，不写Run.csv。

adapter另逐PART作lazy typed metadata scan：KeepBedOverlap/5 IDs/255退休、ReleaseOnly Active、float ε=.2/exp4、两实验ponding-policy键必须缺失；不读取field数组或另读PRE。之后原core唯一一次导出22数组。6805=1805 fixed+5000 soil，原registry仍7060/2060，原target260；不连续实际退休255、保留1800/1852/1904/1956/2008。FixedPlaneStageProjectionReleaseOnly/Active=true/ReactionClosed=false保持。

全部finite、typed layout/count、原ID集合、P0 bits、floatρcache、κ非回退、J/n/V/rho/k ledger、真FS2/3 p≤0、非空signed dterror≤1e−14、clock≤1e−14、plane几何门保留。`k=K0*std::exp((J−1)/((1−N0)*Ck))` 原表达式不动；不使用误写pow10。全窗应有450000 ledger/cache/κ检查、162450 fixed检查、612450 P0检查、900000 plane检查和90非空signed区间；不强制κ必须非零。

## 构建与run绑定

仅编reader `/std:c++17 /O2 /MT /fp:precise /GL-`，MSVC14.36.32532、wmainCRTStartup；从已封口 `mdbc_partition_ReleaseCPU_r1.build.json` 复用 JPartDataBi4/JPartDataHead/JBinaryData/JObject/JException/Functions 六个Release utility对象，共7 link inputs。header来自同归档；不含JSph对象、JAppInfo unused global、Debug CRT或任何solver build。

run wrapper只绑定正常同tag run/start/call/owner/root admission、实际Popen/Win32/solver0、creation/parent/argv、原PRE、生成XML、runtime_r6复制记录、sealed PARTs/Run.csv/Run.out及本reader build；进程检查拒绝已有/活动读取及部分输出。新owner沿原schema提供 actual_steps/saved_frames/program/source_build/source_pre_file/input_xml/GenCase_call/Run_csv/Run_out/PARTs/actual_source_time_from_loader、consumed及身份记录；owner_admission提供root_admission/planned_steps/planned_new_updates360000/planned_global_end4360000/expected_saved_frames90。无需trace_rows、trace_file或causal计数。输入对照已完成rootr6的special/parameters，只允许本次TimeMax10.9、TimeOut.01、ASexp4和说明注释不同。

本轮仅AST与内存文本派生/反向归一化核验；没有编译、运行任何reader或读取原BI4。独立native通过只证明这些实现/安全门，不证明n4修复张拉/团聚、平衡、收敛或完整collapse物理正确。

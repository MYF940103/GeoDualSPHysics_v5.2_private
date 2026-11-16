# C04 CPU A/B/C：独立 128 更新 owner

作者稿，只新增 `support/upl_tpi_cryer_cpu_run_r1.py` 与本 note。一次 root admission 仅运行 A、B 或 C 中的一个新标签；不自动串下一方案，不构建、GenCase、help、native、VTK、half、PRE 或正式 full。

## 原实际控制与精确范围

原 `upl_cryer_freebody_smoke128_CPU_r1.call.json` 记录 DebugCPU、CPU8、`-stable`、原 seed、`-nsteps:128`，direct exit0。实际原 native completion 是 **2 帧**：初始0；completed128、native saved Step127、实际 t=.0001220703125=2^-13。它恰好跨越原第一个普通 TimeOut target，不把它先验说成强制终帧。旧 CPU128 没有独立 run/start 文件；只使用实际存在的 call/native call、Run.out/CSV、原 clock CSV 和 completion，不追认新记录。

新三方案仍 source-zero fresh cold start，复用 `outputs/upl_cryer_freebody_short_r1_seed/upl_cryer_freebody_short_r1.xml/.bi4` 两文件；原 seed 无 Normals 文件，不调用 GenCase。原 XML 不改，`DtFixed=DtIni=2^-20`、TimeOut2^-13、TimeMax.00830078125。CLI 除新输出路径外沿用原参数：

```text
-cpu -ompthreads:8 -stable PREFIX FRESH_OUT -dirdataout data -svres -nsteps:128
```

不加 TimeMax 覆盖，不改变计算 dt。独立计划逐次 binary64 `time+=dt` 重放 128 更新并与真实旧两帧计划核对；不用 n*dt 替代时钟。ramp2^-8、drain2^-7 的原 source-clock/fixed-grid 策略不动；本窗只有早期 ramp/pre-open，**没有 post-drain、峰值或完整周期覆盖**。

原 37181 IDs=8 fixed+37173 soil、XYZ/freebody、远端 inactive DBC、Wendland H1.8、恒 k1e-5、n0.3/Kw2e8、grad1、SPR0/HG0/AS0、AV.1、η.00004 保留。B/C 的窄资格由已冻结真实 overlay 检查；A 保留默认有限 Kw 路径。B/C 与 A 的差异不是 5 Pa 等价或 half 误差。

## completed-build 独立采用

原 `upl_tpi_cryer_cpu_DebugCPU_r1.build.json` 必须继续 passed=false，精确原因为 `Actual CL source or dependency argument malformed`：真实 MSBuild 全86编译/链接已经完成，仅后审误拆 tlog 中未引号的含空格源码末尾。不得重编或伪改旧 receipt。

本 runner 只采用根独立审阅通过的 `upl_tpi_cryer_cpu_DebugCPU_r1.build_review_r2.json`，要求明确 `adopted_completed_build=true`、`original_build_passed=false`、全86 flags/deps/libs 与实际原两工具 Popen/Win32 退出均0。消费其 `original_failed_build`、`prepared`、`source_program`、`program`、`runtime` 和真实 tool calls。

新 program 是原已链接 EXE 的独立逐字节副本，`program_copied=true/program_copy_byte_equal=true/program_relinked=false`。五个 runtime（DsphConfig.xml、ChronoEngine.dll、dsphchrono.dll、vcomp140.dll、vcomp140d.dll）与 EXE 在新 `review_r2/runtime` 同目录。实际源 `JCfgRunBase.cpp` 从 AppInfo.ProgramPath 读取 DsphConfig，换 cwd 不能替代程序同目录配置；本次因此绑定真实新 copy package，保留旧 EXE/out 不写。没有新 link，也不依赖临时 PATH 旁路。

## 单 job admission 与原始 owner

`stage=upl_tpi_cryer_cpu_run_r1.run_admission,passed=true,one_job_only=true,inputs=[stat...]`。

job 为 `configuration=DebugCPU,window=startup128,scheme=A|B|C,tag=upl_tpi_cryer_cpu_DebugCPU_<scheme>_startup128_rN,source_build_review=stat`。inputs 包含两作者稿、纯 helper 的 build_r1.py/Python/psutil、实际新 review/failed build/两工具 call/源 prepare与diff、新 program及source_program、五runtime source/destination、原 seed两文件、原 CPU128 call/nativecall/clock/completion/Run.out/CSV及旧 program stat。

只设置本进程环境 `UPL_TPI_CPU_R1=A/B/C`，移除其 GPU selector，记录实际值；不改变其他进程。绝对路径 Popen 新 program，原参数，private package cwd，stdout/stderr到新日志，无 shell、无窗口。

启动后核真实 PID/parent/完整 exe/argv、psutil创建时间及原始句柄 FILETIME；DuplicateHandle 在等待前持有原进程句柄。分别封存真实 Popen wait 与 Win32 exit。不会把 call、正常结束文字或该 wrapper 通过说成原生/物理验收，不推断未保存故障时刻。失败封存原首因、最后原样已保存 PART 行和 partial，不停止/重启其他任务，不重试，不挂 watcher。

每 job 独立新 `outputs/<tag>` 与 `logs/<tag>.clock.csv/.start.json/.call.json/.run.json/.status.json/.log`；任一已有即拒绝。计划为旧 5 列 `part,time_s,completed_step,saved_step,dt_s`。新标签的 native/admission 不由本脚本创建。

## wrapper 完成门与后续

只核真实 completion、128 更新、零排除、CPU/8 threads 的原实际 RunMode、全37181数量和2个原生文件存在；RunMode 来自旧真实 CPU Run.csv，不能用输出 SavePosDouble 推断其他 backend 内部模式。A 必须没有 TPI三个sidecars。B/C完成summary必须scheme/alpha/beta正确、128次commit/endpoint、`7*37173*128` core bit检查、HG snapshot0、真实结束时钟正确。

**全部22 typed arrays、IDs、finite/elastic/P0/FS、J/n/V/rho/k ledger、原必要步长与 signed dterror、实际保存时钟仍待独立唯一 native read/review**。本脚本不解码、不放宽原门、不计算新理论精度。A 对保留 CPU128 只在真实共同 time/Step/ID 比较，导出 common26/clock 相等不冒称全22 raw数组 bit证明。B/C是另一时间算子，不套与 A 逐位或 5 Pa 等价门；后续 native与科学结论由 root 单独准入。

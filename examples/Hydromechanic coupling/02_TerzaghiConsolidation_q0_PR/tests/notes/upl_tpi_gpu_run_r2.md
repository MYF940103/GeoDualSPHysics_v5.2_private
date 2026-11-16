# P1 GPU 单 job owner 作者稿

本脚本只执行根线程单独准入的一次短求解并封存真实退出；不构建、不调用 GenCase、原生读取器、VTK、下一方案、half 或 full。作者稿尚不代表任一 GPU 物理结果。CPU 已冻结文件与暂停的 C08 保持原样。

新增文件为 `support/upl_tpi_gpu_run_r2.py` 与本 note。既有 CPU runner 仅导入纯 stat、标量时钟和 Win32/进程身份函数；不调用 CPU main、不改 CPU globals 或文件。

## 允许范围

| configuration | scheme | window | 更新数 | 原生帧 | 实际 scalar 终点 s |
|---|---|---|---:|---:|---:|
| Debug | B | debug2steps | 2 | 2 | 0.000012500286102294922 |
| Release | A/B/C 中的单独一个 | startup015 | 24000 | 344 | 0.1500034332275618 |

每一项须新标签、新 root admission；一次调用绝不自动运行表中下一项。标签格式 `upl_tpi_gpu_<configuration>_<scheme>_<window>_rN`。Debug 的初始帧与第 2 update 强制终帧是两个真实保存态，最终原生 Step=1；不是 2 ms。Release 与 CPU 同算法短窗使用相同 dt、初始 seed 和输出计划。

## 真实输入、CLI 与时钟

只读复用完整源零时刻 seed：`outputs/upl_bigstep_full_r1_seed/upl_bigstep_2tv_CPU1_r1` 的 XML/BI4/Normals 三文件及原 full receipt。无 PART restart，无预载或额外 GenCase。

真实 `DtFixed=DtIni=6.250143051147461e-6`，初始固定 40、土体 1000，x-periodic、mDBC FreeSlip、SPR1、HG .1、AV .1、原 band/ramp/drain 与恒 k 全保留。脚本不更改 XML。

共同 CLI 为 `-gpu -stable -mdbc_freeslip PREFIX OUT -dirdataout data -svres -tmax:0.14999999 -nsteps:N`。真实二进制32 cap 提升 double 为 `0.14999999105930328`。Debug 由 `-nsteps:2` 提前停止，Release 24000 更新跨越 cap。它不是调整物理 dt。Run.out TimeMax 使用原 16 位有效数字 formatter，核对 `parse(format(cap,'.16g'))`，日志末位舍入不能替代原生时钟证据。

原输出 special cadence 原样；计划独立逐次 `time += dt`，不以 `n*dt` 取代真实时钟。event completed1600 仍 pre-open，1601 起真实排水。Release 344 帧中 226 个 post-open 保存态，原生阶段须逐帧核 2260 个 true FS2/3 接收者；Debug 无开排水态。强制终帧按真实 next target 记录，不改头或 native Step。

## 新 r2 source/build 绑定

admission.job 指明实际新通过 `source_build` 和 `source_prepare` stat，而不是硬限 r1 路径。拒绝没有 `base_prepare` 的旧 r1 preparation。新 source 必须 `host_h_API_and_other_268_files_byte_identical=true` 并保留原 base 的无 class/virtual ABI 和公共 kernel 签名变化声明。实际 build 的 `source_prepare` 或 `prepared` 必须绑定同一新 preparation，program/runtime 必须来自该真实 passed receipt。

r2 只修 source/role guard；初始 device fixture 在 B/C 真实 Init 独立 scratch 上传后执行。它使用 `fprintf(stdout)`，不进入 solver Log。完整 marker 必须在本次真实 fresh console `.log` **恰好一次**：

```text
UplTpiGpuSourceRoleFixtureR2: source_cases=8 owner_role_cases=8 device_cases_checked=16 device_kernel_completed=true private_error_bits=0
```

A 不走该分支，marker 必须不存在。构建、源码文本或 preparation 的 passed 不证明该 fixture 运行通过。

## root admission 接口

`stage=upl_tpi_gpu_run_r2.run_admission, passed=true, one_job_only=true`；`inputs` 为全部消费文件的现有 stat。包含本脚本、note、CPU helper、Python、psutil、原 seed/provenance、新 build/preparation 链/source_diff/相关源、新 program/runtime、所有前置 review。job：

```text
configuration: Debug | Release
scheme: A | B | C
window: debug2steps | startup015
tag: 独立新标签
source_build: stat
source_prepare: stat
memcheck_program: stat（Debug 必须）
required_runtime_markers: 可选的额外精确文本
```

`required_passed_checks` 必须非空且实际 passed。A 另绑定原 `upl_gpu_stabilizers_release_short_r1.run.json`，但 owner 不执行离线 prefix 比较。`allowed_paused_gpu_processes` 只能逐个准确列明真正已暂停的 GPU PID/创建时间/exe/argv；检查 status STOPPED，绝不操作它们。未获识别或活动 GPU 使本 job 拒绝，不终止其他任务。

## 真实 owner 和出口

Release 直接 Popen solver；Debug 只 Popen 一次 `compute-sanitizer --tool memcheck --error-exitcode 86 --leak-check full --target-processes all --log-file FRESH_LOG PROGRAM ARGS`。stdout 定向新文件，无 shell、无窗口。

持有原 Popen tool handle 的 DuplicateHandle；Debug 在 child 活着时核其 exe/完整 argv/创建时间/父链并 OpenProcess 保留目标 handle。分别封存 tool Popen wait、tool Win32 exit、真实 solver Win32 exit；不把 sanitizer 的退出冒充 solver 出口。目标没捕获时失败并保留实际可得 tool 证据，不重启。所有程序退出必须为 0；Debug 实际 memcheck 必须出现 zero-error summary。

首次 created tool/start/call/run/status/clock.csv 均新建写入；旧 output、partial 或同名记录使启动前拒绝。失败保留真实首因、最后原始 console PART/Run.out 行、所有 partial；不推断未保存停止时间。脚本不终止、不重试、不新增 watcher。

## owner 完成门与后续分离

owner 检查真实 GPU normal finish、原 update 数、1040 数量、零排除、帧存在、Run.csv GPU hardware、HG 原 logical/cache counts、必要 `dt/tau<=.2` 与 spin<.01；这些仍不是全部 native 或物理验收。后续根线程才单独准入一次原生读取及科学比较。B/C sidecar 和 22 typed arrays 由独立原生/离线阶段审查。

每 job 封存 `logs/<tag>.clock.csv/.tool.start.json/.start.json/.call.json/.run.json/.status.json/.log`，Debug 另 `.memcheck.log`；物理解仍在 `outputs/<tag>`。正常退出不等于 TPI/完整固结/理论/重启验收。

GPU A 与原 GPU150 控制按真实时间和 saved Step 交集比较，不能预定末帧共享数；五 binary exports 的相等只是所导出字段证明，不是全部 22 原始数组 bit 证明。B/C 只对同算法 CPU .15 逐帧应用 5 Pa RMS 与 .005 mm 每材料 XYZ 差门；不对 A/B/C 不同算子使用该等价门。

## r2 的唯一检查修正

本版本由冻结 r1 runner 原文复制；除了本版 note、admission/run stage
身份，只将 `check_output` 的实际后端模式改为
`RunMode="Stable - Pos-Cell - Single-GPU"`。GPU cell-position 内部存储与
`SavePosDouble` 输出位置精度是不同概念。原始实际 GPU 基座也报告该 Pos-Cell 模式。
求解参数、所有权/句柄出口、时钟计划、HG/csv/fixture/memcheck 门不变。

旧 Debug B 两更新的 r1 结果保留 `passed=false` / `failed_preserved`。
不得为了这条派生检查错误重跑求解器。本脚本只供另获准入的未来新标签使用；
已完成旧数据由独立 `upl_tpi_gpu_completed_run_audit_r1.py` 离线审查，
再由 `upl_tpi_gpu_native_r2.py` 按单独 read/review 准入消费。此稿未执行。

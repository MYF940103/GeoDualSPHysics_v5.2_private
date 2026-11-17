# P1 staged-load 单次 owner r1

作者稿；根完整审阅后才可逐项独立准入。本稿不生成 admission、seed 或 plan，不执行 build/help/solver/native/VTK/Git。

新增脚本 `tests/support/upl_tpi_p1_loadclock_run_r1.py`。只使用新 host-only staged-load build；原 M0 程序、输入、计划、收据及所有已停长算均保留。

## 唯一 job 与不可变输入

| mode | configuration / scheme | 原输入与时钟来源 tag | 更新 / 帧 |
|---|---|---|---|
| `cpu_debug2ms` | DebugCPU / B | `upl_tpi_m0_dt_Bdebug2ms_CPU_r1` | 200 / 18 |
| `debug2` | Debug / B | `upl_tpi_m0_dt_Bdebug2_GPU_r1` | 2 / 2；compute-sanitizer |
| `Acontrol` | Release / A | `upl_tpi_m0_dt_Acontrol_GPU_r1` | 320 / 18 |
| `window2s` | Release / B | `upl_tpi_m0_dt_B10us_window2s_GPU_r1` | 199996 / 1263 |

三个 short 是实现资格，不是新细步长物理 reference。B 为原 `tD/1000=1.0000228881835938e-5 s`；A 保留原 `6.250143051147461e-6 s`。B 2s 的实际 scalar 终点仍为 `2.00000577545594 s`。原排水事件和 8 列 `+=dt` plan 不改。没有 B .15 profile、half、新 reference 或自动 full。

不复制/改写 seed 和 plan；新程序直接读取各自已 passed 原 run 绑定的 XML/BI4/NBI4，并在前后核 stat。新 argv 与原 argv 仅 output directory 不同；程序由新 build 给出。输入文件内容不重写、不重 hash，不调用 GenCase。

## 真实准入与运行接口

入口：`D:/anaconda3/python.exe -B tests/support/upl_tpi_p1_loadclock_run_r1.py --admission PATH --execution-authorized`。仅独立 2s 可另给 `--notify-admission PATH`。

run admission 的 `stage` 必须为 `upl_tpi_p1_loadclock_run_r1.run_admission`，`passed=true, one_job_only=true`；`job={tag,mode,configuration,scheme,build}`，Debug GPU 另含 `memcheck_program`。`tag` 必须为全新 `upl_tpi_p1_loadclock_..._rN`。

build 必须实际 passed、`stage=upl_tpi_p1_loadclock_build_r1`、configuration 匹配。使用其实际 `source_prepare` 或 `prepared` 字段、program 和 runtime.destination；source prepare 必须为 `upl_tpi_p1_loadclock_r1.prepare`，CPU/GPU backend 匹配，原 pressure/HG/J/M0/CUDA/public ABI 保留证据通过。该 schema 供根后续 build 作者对齐，不能把旧 build 改名伪装。

`inputs` 是去重三字段 stat 列表（path/bytes/mtime_ns），包括新 runner/note、原 runner/shared ownership helpers、实际新 build/preparation/header/program/runtime、实际原 reference run/native review/plan/三 seed、required checks，以及实际 psutil 模块。GPU Debug 包含 compute-sanitizer。无需扫描原 BI4 或 objects SHA。

`required_passed_checks` 至少含根实际 build/source review；顺序额外强制：GPU Debug 之前有新 CPU native review；A 之前有新 CPU/GPU Debug native review；2s 之前有全部三个新 short native review。新 native review stage 为 `upl_tpi_p1_loadclock_native_r1.review`，mode 从其 job 读取。

实际 child 环境由本 owner 构造并完整记录到 start/call/run：CPU/GPU 两个 TPI selectors、M0 selector、loadclock selector，以及 OMP 两项。B 为 TPI=B、`UPL_TPI_M0_DT_R1=EQ40_RH1`、`UPL_TPI_P1_LOADCLOCK_R1=STAGED`；另一 backend TPI selector 为 absent。A 为 GPU TPI=A、M0/loadclock absent，不分配新历史、无额外 force、无新 sidecar。CPU 固定 OMP=1/FALSE；GPU OMP 仅记录实际继承值。

## 所有权与终态

CPU 和 GPU ownership 使用已真实通过的两个 owner 函数的显式局部副本；唯一环境差异为上述完整选择器构造/记录，没有运行期 monkeypatch。保留真实 Popen handle、Win32 创建 FILETIME、PID/exe/argv/parent、wait 与出口。GPU Debug 同时捕获真实 sanitizer/tool 与 solver target 句柄；Release tool 即 solver。任何审计异常也只等待已启动的原 child，不终止、不替换或重新启动。原暂停 GPU 只能在 admission 精确允许的 stopped identity 列表中原样存在。

输出为全新 `tests/outputs/<tag>`；收据为 `logs/<tag>.start/.tool.start/.call/.run/.status.json` 和原始 `.log`，GPU Debug 另有 `.memcheck.log`。既有路径、partial、terminal/queue attempt 均拒绝覆盖。所有输入前后 stat 保留；只原样报告最后已保存 console/Run.out PART 和首因，不构造未保存状态。

终态先封存 run/status，才可由同一 direct owner 可选 queue 一次。复用已验证 `codex queue --thread ROOT --message` 协议、45 秒 timeout 和实际旧成功 proof。notify admission 独立绑定当前 root ID、实际 Codex.exe 和已成功 queue 的 attempt/result；没有连通性测试或额外 watcher。timeout 表示可能已送达，绝不重发或重新布防。该机制不会执行读取器、下个 solver 或 Git。

正常退出仅是待原生审查；原 Run metadata、1040 帧存在、HG lifecycle/cache/finite/dt/spin、GPU 16-case once fixture、memcheck 0 门保持。新 sidecar 的全部 44 列由独立 native review 审核，owner 不把正常 summary 当物理验收。

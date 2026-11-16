# C04 GPU DebugB2：独立实际 memcheck 运行作者稿

尚未执行。只新增同名 support Python 和本文，根全读并独立准入一次才可
运行。此首稿仅 Debug/B/2 updates；Release128/native/review须另行作者与准入。
无自动 solver 链、native/VTK、half、峰窗、PRE、构建、Git/hash 或通知器。

## 输入与窄 profile

必须先有 passed `logs/upl_tpi_cryer_gpu_r2.prepare.json` 和实际 passed
`logs/upl_tpi_cryer_gpu_Debug_r1.build.json`：新完整111对象，97CL/14CUDA，
旧对象复用0、输入stat未变、真实 Debug主程序及同目录必要runtime。
输入原 certified fresh `upl_cryer_freebody_short_r1_seed` XML+BI4，引用真实
旧 GPU128 call 确认该 seed和原 `-gpu -stable` 参数来源，不重建/改输入。

tag 仅允许 `upl_tpi_cryer_gpu_Debug_B_debug2steps_rN`。真实参数只有
`-gpu -stable PREFIX FRESH_OUT -dirdataout data -svres -nsteps:2`。
不加 mDBC flag、不覆盖 TimeMax；原非周期3D sphere、37181=8fixed+
37173soil、dt2^-20、HG0/SPR0、原原始外载/材料/AV/阻尼与 guard 均保留。

计划为原五列：initial(part0/time0/completed0/saved0)与强制终态
(part1/time2^-19/completed2/saved1)。真实 clock用 scalar +=dt生成，
原 TimeOut=2^-13，所以第二帧由既有nsteps终止保存，不伪称普通输出事件。
没有排水后帧；原 tD=2^-7尚未到达。

## 真正工具和 target 所有权

只复用 C02 已审 `upl_tpi_gpu_run_r3.run_owned` 的通用工具/target所有权
实现，不调用其 C02 context、schedule、HG check_output 或 main。
新 context和输出门是本 C04独立定义；通用 helper用绝对 ctx paths写C04
start/call/run，不把C02的1040/HG条件套过来。

实际 compute-sanitizer 命令使用原 memcheck、error-exitcode86、leak-check
full、target-processes all；必须在 target活着时捕获原工具与真正 solver
句柄。核 PID/creation/exe/argv/parent、工具Popen/Win32及target Win32出口。
没有 target捕获则保留实际证据并failed，不补造LASTEXITCODE或自动重跑。

启动前通用 owner检查已有GPU solver；仅允许root精确绑定且实际stopped的
旧暂停GPU，其他活动/未知GPU则拒绝。不停止、恢复或触碰旧owner/GPU。
CPU计算可并行存在。所有新目录/计划/start/call/log等已存在即拒绝覆盖。

## 真正 device fixture 与运行后门

build不证明fixture执行。实际 console必须恰有一次：

`UplTpiCryerGpuSourceRoleFixtureR1: source_cases=8 owner_role_cases=8 device_cases_checked=16 device_kernel_completed=true private_error_bits=0`

这来自原私有 scratch device fixtures，覆盖真实source-role predicate及
正0/负0/非零 source状态，不是新物理相或额外solver。实际 memcheck log
必须有0 errors；必须真正2 updates/2原生帧/零排除/正确GPU counts。

真实 policy/summary必须为C04 B α=.5/β0/M0/37181/37173，2个
commit/endpoint、520422个 core7 checks、HG checks0及真实末态。
不要求/伪造HG force/cache/readonly检查；HG0应不存在HG force summary。
只检查原生presence；22 arrays/所有IDs/原几何/ledger/P0/J/κ/FS/clock/
signed和逐材料压力history仍等待独立唯一reader+review，不由exit0代替。

后续 reviewer应使用真实CUDA策略处理FTZ/FMA，不从Debug代码猜Release
算序，不把压力负值滤掉。现C04 helper保留原 use_fast_math 和显式RN
pressure row，需以真正所编译代码/原策略作精确复现；不增加ULP容差或
放宽任何物理门。此次 runner不解码、不独立判定该数学/物理精度。

## root admission 和产物

stage=`upl_tpi_cryer_gpu_debug2_run_r1.run_admission`，passed=true、
one_job_only=true，job含精确tag/configuration Debug/scheme B/window
debug2steps及实际memcheck_program stat；required_passed_checks列根选的
真实已完成前置审查；allowed_paused_gpu_processes提供原暂停GPU精确身份。

inputs绑定script/note、C02两个实际ownership/stat helper、Python/psutil、
本source prepare/build、相关3TU/diff/两个helper、真实新program/runtime、
原GPU128 call、seed XML+BI4、memcheck工具及前置checks。不扫原BI4或旧
源码/object SHA；新 clock是本次独立生成文件，在启动前seal为stat。

新日志为 `<tag>.start/.tool.start/.call/.run/.status/.log/.memcheck.log`
和 `.clock.csv`，原始输出 `tests/outputs/<tag>`。失败保留真实第一原因及
最后原样PART行，不推断未保存故障时间，不重算source/重挂worker。
成功仅 pending_unique_native_review，无自动后续或物理验收。

# 私有GPU residual viscosity：三个独立作业作者稿

本稿生成时未prepare、未GenCase/构建/solver/native/VTK或queue。新增 `support/upl_c08_rvisc_jobs_r1.py` 和 `configs/upl_c08_rvisc_admission_r1.template.json`。原formal/PRE/runtime/源代码及旧结果不写。实际build与source由已审 `upl_c08_residual_visc_gpu_r1` 私有捕获/构建器提供，owner不构建、不复制程序、不回退旧程序。

三个root逐个选的独立profile，脚本不会串联：

|profile / job tag|private build profile|新更新/global end|输出|
|---|---|---|---|
|off / upl_c08_rvisc_off_GPU_r1|Release_alpha0，alpha0|4000 / 4004000|.01s，一帧，.01s节拍|
|debug / upl_c08_rvisc_debug_GPU_r1|Debug，alpha.1|800 / 4000800|.002s，两帧，.001s节拍；memcheck|
|window / upl_c08_rvisc_window_GPU_r1|Release，alpha.1|120000 / 4120000|.30s，30帧，.01s节拍|

全部用原r2GPU实际10s PRE、固定2.5us、Cubic hdp1.2、原AS total.2/n3、XML AV.1、keep5/1805fixed+5000soil、fixed-plane/CompletedOnly、撤墙后damping/Shepard OFF。新的alpha是私有程序编译常量，既不是XML Visco，也不写入BI4第23数组。原22数组/接收资格与所有数值门仍由独立native核验，normal出口不等于验收。

`prepare --profile ... --execution-authorized` 未来只写该profile的新 `_Def.xml`、自定位BAT和 `.prepared.json`。从root r6原文本按字节decode保持CRLF；只换新comment、PRE绝对绑定、TimeMax/TimeOut及唯一geometryfile的CaseName标签。BAT有唯一 `CASE=<jobtag>`，Def名为`<CASE>_Def.xml`；真实GenCase输出prefix固定`tests/outputs/<CASE>/<CASE>`，seed三文件是`<CASE>.xml/.bi4/_Normals.nbi4`。VTK命名token显式替为同CASE，避免旧标签/输出stem误拒；所有几何/材料/边界/时间步参数不变。现在没有生成这些输入。

根全文审阅、实际build通过后，从模板复制一个profile对象到 `logs/<TAG>.admission.json`，填真实build、preparedXML/BAT/工具/owner和preparation receipt的stat Entries，显式写`reviewed_prior_results=true,passed=true`。模板本身passed=false，不能启动。Debug要求已通过OFF run/native且其完整一帧22/time/layout/signed prefix逐byte一致；Window要求同OFF证据及Debug run/native和实际memcheck0errors/0leaks。根审后的该job admission是最终独立准入，不增加自动review/额外solver链。

`run --profile ... --execution-authorized` 只做该profile一次GenCase＋一次真实owned solver，拒既有输出/owner/partial和活动GPU。沿旧 `base.owned` 的Popen/真实Win32句柄、parent/creation/exe/argv、30s原始PART状态发布与退出封口；Debug由compute-sanitizer包裹同一真实solver，分别保存outer/target实际出口。solver真0后立即记`solver_completed=true`再做输出/侧车审核；后检查失败不重跑solver。失败保留原日志、实际最后PART行、磁盘PART stat与侧车，未保存失败时刻不伪造。正常Run.csv核original7060/2060注册、无exclusions、真实global终点与实际帧数；原加载器仍是PRE资格依据。

候选证据独立于BI4：`C08ResidualViscosityPolicy.json`须typed schema1/ReleaseOnly、真实alpha/active、BI4_metadata/native_22_schema_changed/PRE_contract_changed均false。`C08ResidualViscosity.csv`精确26列，normal ON每save有Pre/Cor两行，实际calls/commits各等已完成新更新，step_start=completed−1，Pre实际t_n、Cor实际t_n+dt/2、save_time为外层原scalar+=dt后时钟；只用原source actualclock逐次加dt核验，不用n*dt重写事实。OFF只有每save一行OFF、计数0，stage时间/dt零及UINT_MAX step是inapplicable占位，不是虚构force调用。真实失败行不能通过normal审核，原isolated dt*lambda/2<=1及原base必要界不放宽。

owner把该独立审核封为 `logs/<TAG>.sidecar.json`，含实际call/program/build/input/plan/两侧车Entry、真实计数/时钟、passed；run用`telemetry_review`/`policy_file`/`meter_file`绑定。receipt先于run封口，避免循环source_run。native wrapper只绑定这份侧证与真实run/call；BI4 reader不冒称从原22字段证明新的数值算子。Debug不作Release逐位等价；OFF一帧对true causal90首帧的22/layout/真实time/signed逐byte比较由新native wrapper独立做，保留1/90原头。ON只有原数值门，参数/算子差不是5Pa、half或理论误差。

成功run保留actual_exit/Win32、actual_steps/saved_frames/summary/Hardware、program/source_build/source_capture/source_archive/private_sources/runtime、source_pre_file/input_xml/seed/planned_steps、GenCase_call/actual_call/owner_admission和consumed/stat闭合。native四稿由HG独立作者：`upl_c08_rvisc_native_r1`，未来 `outputs/upl_c08_rvisc_native_r1_build/C08RViscNative_win64.exe`，job输出`native_r1`、收据`logs/<TAG>.native_r1.json`。owner不会调用它或其他后处理。

Off/Debug无notifier。只有Window run须`--notify`，要求实际root环境`CODEX_THREAD_ID=01a07683-bc64-7463-8db7-9ee6243967d8`及既定CLI路径存在；终态run封口后仅一次45s `codex queue`。失败/超时不重发、不rearm、不测试连接、不新增watcher；消息仅报告本次具体结果并交root审查，无自动native/后续solver。Window BAT同样要求root环境和真实admission，不是无审核的一键三阶段入口。

示例均为未来单独动作，不能直接批量执行：`D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_rvisc_jobs_r1.py prepare --profile off --execution-authorized`；根填实际admission后再独立`run --profile off`。Debug用相同显式profile；Window run另外加`--notify`。无SHA、任意PART restart、新PRE、half、其他psi或长窗自动准入。

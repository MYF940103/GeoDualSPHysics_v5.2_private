# AS + fixed-plane 单job owner（author-only）

仅新增`support/upl_c08_asplane_run_r1.py`和本说明，未import/AST/执行，不改任何旧owner、source、根配置、PRE、程序或原数据。机械派生已验证的`upl_c08_plane_run_r1.py`：真实outer/solver Win32句柄、Popen wait、异常后仍等待已owned目标、30 s status/原样完整console PART行、memcheck和一次终态notify逻辑保持。

每次必须显式选择一个action，根逐项审查/执行；没有自动矩阵或后继物理任务。NoPen恒1，policy恒FixedPlaneStageProjectionReleaseOnly/ReactionClosed=false。SPECS tuple为`(stem,conf,backend,nopen,ason,updates,cadence,end,tout,memcheck)`，与reader作者已直接对齐：

|action|输出tag（outputs下）|配置|AS|新增updates|保存间隔steps|帧数|TimeMax / TimeOut(s)|memcheck|
|---|---|---|---:|---:|---:|---:|---|---|
|CPUdebug|upl_c08_asplane_smoke_CPU_r1|DebugCPU|1|40|40|1|10.0001 / .0001|否|
|GPUdebug|upl_c08_asplane_smoke_GPU_r1|Debug|1|40|40|1|10.0001 / .0001|唯一sanitized target|
|OFF|upl_c08_asplane_off_GPU_r1|Release|0|8000|4000|2|10.02 / .01|否|
|SHORT|upl_c08_asplane_short_GPU_r1|Release|1|12000|4000|3|10.03 / .01|否|
|WINDOW|upl_c08_asplane_window_GPU_r1|Release|1|240000|4000|60|10.6 / .01|否|

全动作dt=2.5us、原r2 GPU认证PRE1000、source global4000000/实际10秒时钟，不重算PRE、不加half。CPUdebug是明确的GPU源→CPU短调用，不据此声称该CPU正式预载已跑。每个solver CLI固定`-stable -mdbc_freeslip:1`，CPU8或GPU0、dirdataout data/svres/global-nsteps；初始P0/J/应力/κ及原真实时钟由生产加载器认证，owner不伪造native t0。

输入复制根r4 ψ0 Def，只改statefile为原PRE绝对路径、TimeMax/TimeOut、AS0/1并显式固定epsilon=.2、exponent2.55、NoPen1。已有系数节点只替换；恰好这两个默认节点缺失时才单独新增，拒绝重复，不更改根模板。原材料、Cubic、SoilStressRateGradCorr1/PoreCompressionGradCorr1、Ck2/free-seepage及原必要dt/域门不放宽。

程序只取`logs/upl_c08_asplane_<conf>_r1.build.json`实际passed、相应configuration/87CPU或113GPU对象、新source capture与AS ReleaseOnly/固定面policy闭合的program。只将已知7份runtime文件缺项从runtime_r4复制到该新program目录；已有文件必须size/mtime相同，不覆盖、不复制旧exe当fallback。没有object扫描/重构/哈希。

fresh保护拒绝已有out/config及任何实际owner/invocation记录。根若已预写同tag`.admission.json`，它保留并绑定stat，不视为已调用；本owner将另写`.owner_admission.json`作为真实PID/argv/计划准入记录，call/start引用真实所选Entry。其他既有partial不自动恢复。`planned_steps.csv`在solver前写且只有`part,completed_step`两列，最终global为source+updates；实际Run必须核原7060/2060registry、0普通排除、真实Step/frame/连续PART。未解码的原console行只称控制台进度，不当精确native停止时刻。

真实Run.out核NoPen=True、AS0为None、AS1为Bui2008及Coef/Exp按原float值回读，唯一260退休、damping/Shepard关闭/FreeSeepage保持，以及唯一原源导入。新build记录AS ReleaseOnly；日志没有独立AS Policy/ActualActive行，owner不编造，逐帧typed ReleaseOnly/Active=true/.2f/2.55f留给已审新AS adapter。AS0也需其显式EXPECT_AS0校验。

GPUdebug只有一次compute-sanitizer包裹target，不先unsanitized；真实tool/target均0且memcheck errors/leaks零才runpass。各action正常完成只表示runtime闭合，native/物理待审；本owner不自动调用reader、VTK或绘图。未来reader CLI由独立adapter提供，原core completion stage不改，AS元数据另写，不在本owner中猜最终native通过。

仅WINDOW可带`--notify`，要求原根thread环境与已确认CLI；终态先写queue_attempt、只一次45 s调用，失败/超时delivery uncertain不得重发，不建watcher或连通性测试。不会自动读取、重试solver或启动下一组。示例（本稿未执行）：`python tests/support/upl_c08_asplane_run_r1.py WINDOW --execution-authorized --notify`。

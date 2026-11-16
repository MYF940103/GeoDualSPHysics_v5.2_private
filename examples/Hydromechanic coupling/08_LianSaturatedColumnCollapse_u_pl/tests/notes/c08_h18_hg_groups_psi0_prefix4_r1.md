# C08 三组准入程序：ψ0 四帧实施回归

本轮只新增 support/c08_h18_hg_groups_psi0_prefix4_r1.py 与本说明；未 prepare、import、build、启动求解器/reader/VTK、Git 或 hash。脚本机械复制已通过的 c08_h18_wall_c_retry_prefix4_GPU_r1.py，原 direct owner、实际 Popen/Win32 身份/出口、独占输出/封存、native 和全字节比较流程保留；无全局 monkeypatch，无新框架。

本项只验证新程序放行三组材料的 host guard 对原 ψ0 路径无回归。新程序来源 logs/c08_h18_hg_groups_build_r1.build.json，根审查为同名前缀 .root_review_r1.json，独立材料 probe 为 logs/c08_h18_hg_material_groups_probe_r1.check.json。实际闭包为114对象、只编一个 JSphGpuSingle host TU、其余113对象保留；C质量retry CUDA、HG Node、材料算法与捕获host原对象不变。build准入采用其实际字段，不假定新build重新编译CUDA；CPU21点仅验证材料公式，未调用GPU/HG producer，不能代替本次实际ψ0实施回归，也不能据此接受新两组GPU dispatch或物理结果。

紧邻对照采用原 c08_h18_wall_c_retry_prefix4_GPU_r1 的 run/prepare/check，三份收据均按其真实schema读取：所有权在run、原PRE/profile等在prepare。局部字典合并只读取其值，不改写旧模块或收据。该对照check的consumed对completion.json有两条完全相同的stat（原bound+take），其余五个比较文件各一条；新脚本显式核对这一实际计数和同一身份，不假设整个列表无重复。

原ψ0完整Wendland schema2同材料PRE原样采用，不运行PRE或GenCase。seed XML/BI4/NBI4、17-key native profile和四帧计划都从紧邻已通过准备结果逐字节复制，旧资料不改名/重写。dt=0.000005 s，cold HG e0；source实际9.9999999997060076 s。6001个新更新，global cap2006001。实际保存completed steps为2000001/2002001/2004001/2006001，saved_step各减一，对应真实标量时钟10.000004999706007/10.010004999705629/10.02000499970525/10.030004999704872 s，不以n*dt替换。

argv保留 -gpu:0 -stable -mdbc_freeslip:1、-nsteps:2006001；环境仅显式启用 C08_HG_OPT_H18=1。运行前检查任何活动DualSPHysics GPU物理解算器，有则停止本新启动而不终止/修改现有进程。本项无时间步、材料、AS/HG/NoPen/孔压物理改动；candidate_is_numerical_change=false、material_guard_only=true。原程序已有的物理候选性质和局限并未因此消失。

prepare/run/native/review四个phase必须分别获得根准入，不自动执行下一phase。根准入位于 logs/TAG.root_PHASE_admission.json，TAG=c08_h18_hg_groups_psi0_prefix4_r1。沿用 authorized/allowed_stage/phase/execution_script/note/source_build/build_review/retained_run/retained_review/root_thread_id、automatic_next_job=false/automatic_native=false/watcher=false；原component_review键在本新schema明确替换为 material_probe（指向CPU21 check）。非prepare还需preparation stat。只允许当前根线程01a07683-bc64-7463-8db7-9ee6243967d8。无通知程序、queue、watcher、half、参考链、其他ψ、PRE或后续solver。

native单独采用现有 logs/c08_h18_hg_opt4_native_r1.build.json 所绑定的已完成short4 reader，不重新编译；CLI为 --receiver short4 psi0 DATA PRE PLAN PROFILE FRESH。必须保留全部6805 IDs/22 typed数组、原ledger20000、P0位检查27220、fixed marker7220、4个非空signed区间及clock/dterror≤1e−14、不改原生字段；也必须无 WallFaultCaptureHostR1 目录。

review必须与紧邻旧own-prefix4逐字节相同：typed22.bin完整头和全部四记录、typed22_layout.csv、clocks.csv（含实际时间和signed dterror）、全部8行60列 C08OptPlasticHG.csv 及完整policy JSON。保留原头、原布局，不删字段、不改时间/阈值、不对HG行拟合；还需出现真实塑性保存阶段。失败保留首因和partial，已完成solver之后只修新离线分析，不重复求解/解码或覆盖。成功只说明原ψ0短路径的实施等价，不能证明其他组GPU材料dispatch、完整3 s准确性、耦合能量闭合或论文验收。

根完整阅读并分别准入后，case根可使用（这里只列命令，不构成执行准入）：

    D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_hg_groups_psi0_prefix4_r1.py prepare --execution-authorized
    D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_hg_groups_psi0_prefix4_r1.py run --execution-authorized
    D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_hg_groups_psi0_prefix4_r1.py native --execution-authorized
    D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_hg_groups_psi0_prefix4_r1.py review --execution-authorized

所有新文件仅位于tests既有浅层目录。只核消费的核心stat，不扫描276源码/113对象/全部旧BI4或SHA。


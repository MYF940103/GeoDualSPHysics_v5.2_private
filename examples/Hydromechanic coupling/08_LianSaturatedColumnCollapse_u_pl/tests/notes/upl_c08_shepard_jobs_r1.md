# ReleaseShepard 单因素 GPU jobs（作者稿，未执行）

只新增 `tests/support/upl_c08_shepard_jobs_r1.py` 与本说明；当前不生成XML/BAT/plan、不调用任何程序。既有r6、PRE、正式输入、total/effective失败、native及旧owner全部保护。

两个独立profile：

|profile|tag|build|new updates/global end|output|实际滤波次数|
|---|---|---|---|---|---|
|smoke|upl_c08_shepard_smoke_GPU_r1|Debug + memcheck|80 / 4000080|.0001s；2帧，40/80|必须CSV真实2次|
|window|upl_c08_shepard_window_GPU_r1|Release|360000 / 4360000|.01s；90帧|必须CSV真实9000次|

`prepare smoke|window` 仅在根单独调用后生成对应 `tests/configs/<tag>_Def.xml`、极短BAT和两列part/completed_step计划；`run smoke|window` 是另一个显式调用。每run要求各自 `logs/<tag>.admission.json`，绝不由prepare/build自动串联。window rootAD还绑定实际passed smoke_run/smoke_native/smoke_review，smoke必须真实target/tool出口0、80步/2帧、2次滤波和memcheck0 errors/0leaks。native仍由根独立调用，owner不自动读取。

输入从原rootr6 ψ0完整Def机械派生，仅PRE绝对路径、TimeMax/TimeOut及注释可不同。AS谱必须原total，ε.2/n3/Cubic1.2/dt2.5us、原r2 law1 certified PRE→law2接收、KeepBedOverlap/6805、FixedPlane/CompletedOnly全保留。原XML已是Shepard1/40和preload damping1/.02；**不改这些数字**。私有host-TU程序只在release保留loaded Shepard flag，damping仍OFF。不是把effective-AS失败程序拿来比较，不重新生成PRE，不自动半步/其他ψ。

私有build收据为 `logs/upl_c08_shepard_release_{Debug,Release}_r1.build.json`；程序分别位于对应outputs同stem目录，Debug `DualSPHysics5.2_win64_debug.exe`、Release `DualSPHysics5.2_GEO_win64.exe`；共享capture `outputs/upl_c08_shepard_release_r1_source/source.json/source.zip`。build作者与本owner已直接对齐。rootAD必有passed/allowed_job/source_build、AS_stress_space=`total`、ArtificialStressCoef=.2/Exp=3、PoreShepardRegularization=true/Interval40、FreeSeepagePondingPolicy=`CompletedOnly`、planned_global_end/expected_saved_frames。window另有三个smoke Entry；notify仅window且root_thread_id指向根线程。

复用封口 `base.owned` 的真实进程/创建时间/exe/argv/parent/工具与target Win32句柄捕获；异常也等待并封存原target，不丢活进程。每run原start/call/owner_admission/status/run独立，已存在完整或部分输出拒绝覆盖/重试。GenCase每job一次，用新配置真实生成同几何seed；实际solver一次，不先普通运行再san replay。smoke只compute-sanitizer memcheck这一目标，无queue；window可显式--notify尝试一次45s同线程终态提醒，投递不确定不得重发。它不是未来solver自动队列。

计量CSV为输出根 `C08ReleaseShepard.csv`：owner按真实19列核call连续、completed_step%40、Nstep=completed−1、step_start_time_s为outer `TimeStep+=dt`前真实clock、operator_dt_s=实际2.5us、soil5000/interval40。clock按源loader实际时间逐步scalar+=dt，不用n*dt/减整数10；2/9000只作为正常运行实际CSV必检的预期，不伪填实际次数。前18列数值有限；最后primary_bitcheck_passed首行必须true、后行空，primary_bitcheck_performed首1后0，如实仅首次检查P0/J/κ bits。滤波前后S与差值只封存，**S=Σ(nV/Kw·p)不是fluidmass**，计量含同wrapper的FS正压投影，因此不以S相等伪造守恒门。

正常Run仍核原registry7060/2060、实际2/90 PART、零排除、原PRE唯一import、一次retire255/kept5、真实ShepardON interval40/dampingOFF日志、total-AS .2/n3严格Run.csv解析。原22/P0/J/κ/FS/ledger/6805/plane/clock/signed数值门由新native后续独立核，不由owner冒称；滤波通过不等于准确性或完整collapse验收。若solver正常而派生检查失败，保留实际0和原输出，修派生不能重算物理。

根完整阅读后逐条选择执行；当前仅作者与AST静态检查：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_shepard_jobs_r1.py prepare smoke --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_shepard_jobs_r1.py run smoke --execution-authorized
# window 的 prepare/run 也各自独立，且先有真实smoke完整准入；不自动运行。
```

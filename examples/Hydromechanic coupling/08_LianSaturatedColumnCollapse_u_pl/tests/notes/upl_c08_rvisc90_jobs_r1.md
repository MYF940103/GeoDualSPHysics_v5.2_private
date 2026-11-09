# Residual viscosity：同参数单一.90s延长窗（作者稿）

生成本稿时未prepare、GenCase、solver、reader或queue。仅新增 `support/upl_c08_rvisc90_jobs_r1.py`、本说明和 `configs/upl_c08_rvisc90_admission_r1.template.json`（passed=false）。旧jobs/程序/source/物理输入、原PRE、原30结果和正式目录不写。

这是唯一新作业 `upl_c08_rvisc90_GPU_r1`，单profile=`window90`：360000新更新、global4360000、90个.01s保存、固定2.5us、TimeMax10.90。直接绑定已通过的 `upl_c08_residual_visc_gpu_Release_r1.build.json` 及其原程序、CAP/运行依赖，要求与已完成.30作业这些Entries完全相同；不新构建或修改编译常量。原r2GPU真实10s PRE、alpha.1、AS total.2/n3、AV.1、Cubic hdp1.2、keep5/6805、fixed-plane、CompletedOnly、释放后Shepard/damping OFF均保持。实际末钟由原source scalar逐步+=dt获得，约10.90000000066，不强写10.9或伪造t0。

仅两个显式动作：`prepare --execution-authorized` 未来生成该新CASE的Def/BAT/prepare receipt；`run --execution-authorized --notify` 未来在真实root环境和root实际admission下启动一次GenCase和一次solver。没有profile选择、smoke/half、PRE重算、3s、其他psi或自动阶段。prepare复用旧已审纯`expected/check_input`，保留原文本CRLF；只换CaseName标签、PRE绑定、TimeMax/TimeOut/comment。新CASE、Def与真实GenCase输出stem完全一致，不沿旧VTK标签。当前未生成这些文件。

admission由根填真实build/prepare/tool/owner Entries，另只含四个前置receipt Entries：`prerequisites.prior30_run/prior30_native/prior30_analysis/prior30_visual`。要求原30run/native/分析真passed、native绑定同一run、分析确实消费该native；visual直接绑定已存在 `logs/upl_c08_rvisc_review_r1.visual.json`，须为root实际passed审图并包含原分析两图，且已审可读诊断。只绑定这四份前置收据，不要求新增调用/图片caller-stats链；原分析作者态`visual_QA_pending`不改写。根已记录的科学决定为 `notes/upl_c08_rvisc_decision_r1.md`；先前.30改善和恶化混合，仅支持这一次受控延长，不是修复已获确认。

原owned机制保持：fresh拒已有owner/output/partial，活动GPU不启动，Popen/Win32真实句柄、creation/exe/argv/parent、30s最后原始PART行和独立实际出口。solver真0立即封`solver_completed=true`，其后输出/侧车问题不重跑solver。失败保留首因、Run.out、原lastPART、磁盘PART与侧车stat；未保存状态/失败时刻不重构。

侧车数值/计数审核从旧rvisc任务机械派生，仅换固定90帧scope：typed `C08ResidualViscosityPolicy.json`为ReleaseOnly/active/alpha.1，明确非BI4 metadata；CSV精确26列、正常180行，每保存Pre/Cor各一行，实际calls/commits各到360000。step_start、Pre/Cor实际force clock、SaveData completed与外层scalar钟按同一原循环核验，原dt*lambda/2<=1与base必要步长界不放宽，不用frames推造stage调用。独立 `logs/<TAG>.sidecar.json` 和run的telemetry_review/policy_file/meter_file Entries与旧30接口一致。

只有原90 reader及新独立wrapper在根后续审核后才可读取一次，owner不自动调用。全部90原生数值门仍须通过；之后保留90/30原头，前30全部22数组、真实time、layout和含signed clocks须对原同参数30计算逐byte核无反馈。此证明在run收据中标pending，不提前冒称通过。新90与保留truecausal90的物理差异另作描述，不是5Pa/half/理论精度门。

单次同线程通知沿旧45s `codex queue`，仅在本次terminal run封口后尝试一次；要求真实`CODEX_THREAD_ID`为既定root线程，CLI路径存在。失败/超时不重发、不rearm、不新增watcher或连接测试。消息指明本次具体run/90计划、原30混合结论及后续唯一native/prefix审核，不自动新求解。

根全文审后才可分别执行：`D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_rvisc90_jobs_r1.py prepare --execution-authorized`；根填实际admission后另行`run --execution-authorized --notify`。无SHA/旧对象扫描/源代码patch；不把正常出口或.90s结果当作完整物理验收或后期停滞已修复。

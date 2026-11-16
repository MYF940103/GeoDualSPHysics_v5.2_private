# C08 ψ+2.5°：独立完整3 s HG物理比较作者资产

本轮仅新增 support/c08_h18_hg_psi2p5_full3_r1.py 与本说明，标签固定 c08_h18_hg_psi2p5_full3_r1。未 import、prepare、build、solver、reader、GenCase、VTK、Git 或通知自测。只支持 prepare/run 两phase，每phase必须根线程另行准入；不泛化matrix，不改旧模块全局，不触及ψ−5或正式根XML/BAT。

直接owner/真实子进程身份与Popen/Win32出口/完成封存/失败partial保留/一次终态queue，机械复用 c08_h18_wall_c_retry_full3_GPU_r2.py。纯helper复用当前 c08_h18_hg_groups_psi0_prefix4_r1.py、原clock_plan和已审host summary/copy/capture工具。没有新增求解算法或半步链。数值计算只会在新run显式准入后启动一次，根工具无需另挂watcher。

程序为新groups build/root_review_r1；独立CPU21材料制造解与本次groups ψ0 prefix4真实全22/clock/signed/HG8×60/policy逐字节回归须先通过。guard只放行精确三tuple；本driver仅选ψ+2.5°，不会自动选择其他组。旧GPU短材料实施、CPU21和ψ0 GPU回归属于实施证据；新组完整3 s是首次该材料的物理比较，正常退出也不代表最终精度验收。

源固定为 outputs/c08_h18_wend_branches_psi2p5_pre_r1/data/Part_1000.bi4，真实完成run、logs/c08_h18_wend_psi2p5_native_r2.check.json及native_r2/completion.json。原native r1为预检0-reader失败，绝不混作数据。必须1001帧/7060 IDs/22数组、schema2/law2同材料证书、bedroles、实际末时钟9.9999999997060076 s等原门；实际κ/J/p/应力历史继承，不把ψ0 PRE改标签，不清零κ。source material精确为coh5000 Pa、dlt+2.5°、DilationDecay0.2、φ/φr25°、coh_r1000、n_coh5、n_phi0、E20 MPa、ν.33；角度按XML float→TORAD→float，不以度值直接比较弧度。

源native证书不能代替平衡。另要求即将完成的源physical check的 analysis_complete/source_native_qualified/consumed_stats_unchanged及同组/源run/native绑定；不假定一个 passed 就接受。根source_root_review必须显式 accepted_for_bounded_release_comparison=true，并逐一绑定 source_run、source_native_check、source_native_completion、source_physical_review、source_pre_file。这是允许从已审源做有界撤墙比较，不要求也不宣称精确静力平衡。物理review/rootreview/physical_decision都由每phase根准入明确stat指定，不自写准入。

prepare采用已完成AS03/n2.55 full3的generated seed三件，使用新副本，绝不重新GenCase/PRE。新副本XML只做3项可逆字节替换：runtime soils dlt0→2.5、DilationDecay0→0.2、gravitypreload.statefile→新ψ+2.5° PRE。原casedef/constants、execution/constants及全部其他参数保持原字节；GenCase BI4和Normals/NBI4完整字节复制，原标签文件保留。旧seed basename仅是封存几何的标签，不能拿它证明材料；真正材料由新XML/新PRE证书绑定。旧注释也原样保留以便严格逆证，这份测试副本不是正式发行版文档。

native profile从旧17-key派生，仅group/dlt/DilationDecay变化；其余15项源材料按真实native_r2 material_values逐一float32对照，AS.3/n2.55仍作为第16/17项。原301行计划整文件复制并以原source实际末时钟逐次 +=5us 验证，绝不n*dt或拟合时间。只有source实际时钟精确一致时本窄driver可用；不一致则失败保留，不能默改计划。600000新更新/global2600000，TimeMax13 s/TimeOut.01 s，实际计划末12.999999999592434 s；前300保存2000001+2000×part，末2600000。

全部其他物理保持WendlandH1.8/H=.072/dp=.04/fixed5us、AS.3/n2.55/AV.1、NoPen固定平面release-only、keepfalse/retire255、CompletedOnly正自由面投影、冷HG e0/xi.1、撤墙后阻尼OFF/ShepardOFF。HG初始零记忆不是完整HG PART restart，NoPen ReactionClosed=false已知限制不被消除。新组与旧ψ0为跨材料描述比较，不设0ULP/5Pa跨材料等价门，也不增加half/空间参考求解。

根准入路径为 logs/TAG.root_prepare_admission.json 与 TAG.root_run_admission.json。公共键 authorized、allowed_stage、phase、execution_script、note、source_build、build_review、material_probe、new_prefix4_review、group='psi2p5'、source_run、source_pre_file、source_native_check、source_native_completion、source_physical_review、source_root_review、physical_decision、root_thread_id、single_full3_only=true、terminal_queue_once=true、watcher=false、automatic_native=false、automatic_next_job=false、codex；run另需preparation。stat一律绑定实际文件；root线程固定01a07683-bc64-7463-8db7-9ee6243967d8和已有current Codex stat。源码/对象/旧BI4不做全扫描或SHA。

run重核新准备、源接受与实施门、复制seed/runtime9 stat、XML三项逆证，然后启动唯一物理目标。任何活动DualSPHysics GPU目标均阻止本新启动，不停止别人。环境仅 C08_HG_OPT_H18=1，argv仍 -gpu:0 -stable -mdbc_freeslip:1 ... -nsteps:2600000。真实完成先封solver_completed，再审Run.csv/301帧；Run.csv显示物理时间有舍入，实际native时钟仍待独立读取。实际子进程启动后只在终态尝试一次当前thread queue，45 s超时可能已投递，不重发、不watcher、不重新布防。

本owner不解码/VTK/执行其他ψ/PRE/half或下一任务。完成后根另准入一次现有AS255 full reader：--receiver formal psi2p5 DATA NEW_PRE PLAN NEW17PROFILE FRESH，保留22/6805/P0/J/κ/FS/ledger/plane/实际clock/signed全部原门，并审真实HG phase/work/history及全程孔压、运动、间距、塑性与论文结果。首保存是PRE后1个更新，不能捏造接收前原生保存帧，也不能要求其新应力/J与PRE bit相等。失败保留真实首因/实际退出/原console最后保存行，不能重建未保存故障状态；solver完成后派生失败只离线修分析。

根完整读并分别准入后可用（这里只列命令，不构成执行准入）：

    D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_hg_psi2p5_full3_r1.py prepare --execution-authorized
    D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_hg_psi2p5_full3_r1.py run --execution-authorized


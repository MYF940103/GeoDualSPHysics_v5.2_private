# C08 后两组同材料 Wendland 预加载：作者资产

本轮只新增 support/c08_h18_wend_branches_pre_r1.py 和本说明。未运行 import、prepare、GenCase、build、solver、reader、VTK、Git 或通知测试。两个 group 各有独占标签，不会自动串联；根线程先单独审查、准入 psi2p5，不能据此自动运行 psim5 或任一 collapse。

| group | 初始黏聚力 Pa | 剪胀角（XML 度） | DilationDecay |
| --- | ---: | ---: | ---: |
| psi2p5 | 5000 | +2.5 | 0.2 |
| psim5 | 7500 | −5 | 0.2 |

共有材料保持 φ=φr=25°、n_phi=0、coh_r=1000 Pa、n_coh=5、E=20 MPa、ν=0.33。未显式引入 SoilTriggerFos，沿用原 XML/程序默认 1.65；完整原 special/parameters 签名保留，后续 loader/native 仍必须独立核对实际序列化材料、软化、触发与张拉契约。expected_material_storage 仅记录 JSph.cpp 的 ReadElementFloat→TORAD→float 预期角度/衰减存储值，不是原生证书。程序来源为已封存 c08_preload_schema2_Release_r1 generic schema2/law2，绝不使用当前 ψ0 私有 HG 程序。

固定 Wendland Kernel2、hdp=1.8、dp=0.04、H=0.072 m、dt=0.000005 s、阻尼系数 0.03、Shepard=ON/40、原水力模型1/Ck2。预加载阶段 AS/HG/NoPen/SPR/shifting 均关闭，elastic_source=false、keep_bed_overlap=false；由零应力/原初始化孔压从头重力加载，不直接赋地应力，不导入 ψ0 PRE，不清零或重置塑性历史。有效 Smooth/Apex/TensionRepair 返回可按原门提交。几何沿用 bed-last 优先级：MK0 [0,255)、MK1 [255,1805)、MK2 [1805,2060)，soil [2060,7060)。这两份源必须分别保有各自材料形成的真实 κ/J/p/应力历史，不能把 ψ0 PRE 改标签借用。

事件为10 s、TimeMax=13 s，实际本次只用 -nsteps:2000000 截至源末态，预计1001帧，不执行撤墙。原标量 +=dt 计划从 configs/c08_h18_pre_r2.steps.csv 复制到新标签；prepare 验证全部1001时刻对应逐次 binary64 累加，非 n*dt。末计划实际时钟9.999999999706008 s，非初始保存 Step=completed_step−1。owner 的 Run.csv/Run.out/帧数审核不替代原生实际时钟、22数组、所有 IDs、P0/J/κ/FS/ledger/signed dterror 或平衡验收。

prepare 与 run 各要求独立根准入，不自行创建准入。所有准入均需 authorized=true、allowed_action、allowed_job、group、single_source_only=true、terminal_queue_once=true，以及脚本 root_admission() 列出的精确材料/数值/事件契约。通用冻结 stat 键是 script、note、template、source_build、program、source_capture、source_archive、source_plan 和 runtime（九个 destination stat 的原顺序）；run 另需 preparation、input_xml、planned_steps、test_BAT。准入 schema 使用 authorized，不假定旧结果具有 passed。

命名：c08_h18_wend_branches_GROUP_pre_r1。prepare 准入为 logs/TAG.prepare_admission.json，run 准入为 logs/TAG.admission.json。prepare 仅写 configs/TAG_Def.xml、TAG_GPU.bat、TAG.steps.csv 和 logs/TAG.prepare.json；无程序调用，也不寻找/检查通知程序。BAT 是单组测试入口，依赖根线程已写入的 run 准入，不是当前正式三组发行包。

run 原样复用已审 upl_c08_bedkeep_run_r1 的 direct owner/Win32 句柄身份、原始 start/call、等待/状态/错误封存；参数为 -gpu:0 -stable -mdbc_freeslip（无 :1）和 -nsteps:2000000。检查当前活动 GPU 求解器，若已有则报错且不停止任何进程。运行输出、种子、日志/所有权记录独占新标签；先封 solver_completed.json，再执行八项选定 VTK 导出：名义0/1/5/10 s 分别 PartFluid5000、PartBound2060，并记录对应实际计划时刻。VTK 位置为浮点可视化值，不作为 native double 证据。若求解完成后导出失败，已完成 BI4 仍被封存；只能离线修派生，绝不重新求解。

仅 run --notify 检查实际环境 CODEX_THREAD_ID=01a07683-bc64-7463-8db7-9ee6243967d8、根准入 root_thread_id 及 notification_program stat；当前绑定路径为 C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1106.51428-win32-x64/bin/windows-x86_64/codex.exe。只在新 run 终态之后尝试一次 queue，45 s 超时也可能已送达，不重发、不 watcher、不重新布防、不连通性自测。无 --notify 时不依赖 Codex 路径/环境。prepare 不依赖通知工具。

只核验消费的程序/build/source capture/archive/runtime9/辅助脚本/输入/计划 stat；不扫描276源/114对象/旧BI4，也无 SHA 操作。失败保留真实实际出口、首因、原始最后完整 PART 行、已保存 partial；不推断未保存故障时刻。正常求解或导出不是 PRE 证书、10 s 平衡、塌陷精度或其他 ψ 的准入。

根线程完整审阅后可分别执行（本说明不构成执行准入）：

    D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_wend_branches_pre_r1.py prepare --group psi2p5 --execution-authorized
    D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_wend_branches_pre_r1.py run --group psi2p5 --execution-authorized --notify

psim5 只能在该组独立 prepare/run 准入后用同一 CLI 显式选择。该 owner 不解码、不运行 receiver/collapse、half、其他组或下一个求解器；是否可作后续源与平衡仍由根线程对真实 native 数据独立审查决定。ψ0 完整3 s 的负孔压脉冲和团聚/早停问题仍未被这两份 PRE 准备所解决或豁免。

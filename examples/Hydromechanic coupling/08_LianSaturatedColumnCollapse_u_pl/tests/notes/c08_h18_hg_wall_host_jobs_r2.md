? r2 ?????????? fresh .review_r2.check.json???????????r2??????????CSV????r1?????????Debug2????native??r1 owner????????????????????????/??/???Release4?replay??prepare/run??r2???????????????????/???

# C08 host-only墙故障捕获：独立短回归与有限重放作者稿

仅新增 `tests/support/c08_h18_hg_wall_host_jobs_r2.py` 与本文，从已审 `wall_observe_jobs_r1` 机械派生。作者不import/prepare/run/build/native/VTK/Git/SHA；root须再完整审阅，对每个prepare/run分别准入。原CUDA observer r1/r2、失败3s、PRE及全部旧输出保留；新脚本不接受原r2构建，亦不重挂其owner。

唯一新builder为 `support/c08_h18_hg_wall_host_capture_r2_build.py`，只接受 `logs/c08_h18_hg_wall_host_capture_r2_{Debug,Release}.build.json`。构建必须证明110个原物理对象（**含全部原CUDA**）+原opt3个私有host/HG对象+1个新 `JSphGpu_mdbc` host对象=114，一次MSVC cl和一次link、零CUDA编译；不是114个对象全部原字节保留。仅原host异常分支插入捕获，修改/新增成员严格为 `JSphGpu_mdbc.cpp` 和 `c08_h18_hg_wall_host_capture_r2.hpp`，可逆恢复原mdbc源。原opt HG producer/consumer、积分和物理CUDA不重编译，正式/公共源码不改。新jobs同时记录真实新程序/source/archive和原opt来源，不用旧CUDA observer的receipt冒充它。

三个closed profile均HG ON且只一个求解器：`debug2`→`c08_h18_hg_wall_host_debug2_r1`，新2更新/2帧、实际memcheck；`prefix4`→`c08_h18_hg_wall_host_prefix4_r1`，6001更新/4帧（2000001/2002001/2004001/2006001）；`replay`→`c08_h18_hg_wall_host_replay_GPU_r1`，196680新更新、cap2196680、最多100计划保存。仍用Wendland/H1.8、dp.04、5us、AS.3/n2.55、AV.1、keepfalse、固定平面NoPen/ReactionClosed=false、CompletedOnly、原同材料schema2 ψ0 PRE及cold-zero HG。没有物理参数、half、其他ψ、PRE或时间积分修改。

复制原已生成输入字节，不运行GenCase：短窗来自原AS03 TimeMax10.9，replay来自原HG0 full3 TimeMax13。新config/steps在tests/configs，seed与未来输出在tests/outputs独立tag，真实admission/start/call/seal/run/status/日志在tests/logs。时钟逐步+=5us；replay新100计划前99行与原failed full301完全相同，Part98 completed2196001/actual10.980004999668907，最后cap2196680仅实际完成才保存。原301与新100计划保持不同路径，不改旧头/clock或插值。

replay必须先通过**新host候选自己的**Debug2和Release4真实退出、唯一native22/6805IDs、完整clock/layout/signed逐byte回归；Debug还核零memcheck错误泄漏、四行60列HG、907392字节first-n与配置，Release核八行HG及实际塑性阶段；HG policy参数明确一致。正常短窗还必须没有 `WallFaultCaptureHostR1` 目录，任何意外产生均拒绝replay。缓存位检查只是coherence，独立首力参考来自保留整快照传递，不新增CPU求解。

owner/Win32/Popen/目标创建时间/argv/parent、独立正常solver seal、内嵌AS分号Run.csv解析、原错误首因与最后真实console PART沿用旧脚本。预期重现仍是求解器失败，不得标passed；正常到cap100也不是物理修复、完整3s或论文验收。各run不存在覆盖/重试路径，完成solver但派生失败仅可离线修派生。

不再解析GPUprintf或要求其存在。故障后helper可能创建独立 `WallFaultCaptureHostR1/schema.json` 和数组CSV。jobs只记录该目录、文件stat和小JSON原内容；不重算数组、拟合/矩阵或补造rejected fitted C，不将JSON声明自动认作独立完成证明。缺目录/不完整捕获/JSON解析错误只如实记录，不能授权重试。它是原device故障后host捕获的实际输入，**不是已保存native态，亦未存储被拒绝的fitted C**；root需另核真实faultpacket/typed数组、clock、各copy status和科学含义。

命令为 `python -X utf8 -B tests/support/c08_h18_hg_wall_host_jobs_r2.py prepare|run --profile debug2|prefix4|replay --execution-authorized`，每次独立当前root准入。debug2/prefix4不通知；只有replay直接owner在真实终态run/status封存后尝试一次45s当前线程queue。超时delivery_uncertain不重发/重布防，不挂watcher。无自动reader/native/VTK、下一solver、PRE、half或其他ψ；新的100计划若需原生读取仍由root独立选择failed99_obs或cap100，旧failed99_hg/301工具不能冒用。

?????????host-capture r1 ?????? Windows max ??? C2589 ?????????????????????? jobs ????? r2 ???????????/header?????????????

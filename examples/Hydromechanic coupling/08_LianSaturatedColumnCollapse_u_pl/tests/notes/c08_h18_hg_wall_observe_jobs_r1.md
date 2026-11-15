# C08 动态墙原因观测：两项实施短回归与一个有限重现

仅作者阶段，新增 `support/c08_h18_hg_wall_observe_jobs_r1.py` 和本文。机械派生自冻结的 opt jobs owner/seal/error/clock代码。本轮不import、不prepare、不build、不执行求解器、reader、VTK、Git或哈希扫描；不新增PRE或其他ψ任务。root完整审阅后对每个profile的prepare/run分别准入。原失败3s、r1构建失败、旧Raw/cached/opt全部程序与数据保持原样。

本脚本只接受新 `c08_h18_hg_wall_observe_r2_{Debug|Release}.build.json`。r1 Debug因原 `-ccbin` HostX86与PATH中HostX64的cl不一致，真实NVCC Popen/Win32均为1，未运行GPU程序；不能当作已通过构建。r2是环境修复的新标签，观测helper和所有原物理语句不变。实际新构建须证明110原物理对象+3原opt私有host/HG对象+1插桩物理CUDA=114，只有1次NVCC和1次link，原opt材料producer/consumer/HG对象保留、门槛和正常路径未改、两个物理源可逆恢复，并绑定实际程序/runtime/source。归一化的job契约同时保存原opt与新observer来源，不伪造新的构建事实。

| profile | 新运行标签 | 上限和保存 |
| --- | --- | --- |
| debug2 | `c08_h18_hg_wall_observe_debug2_r1` | Debug，2次新更新，completed2000001/2000002，两帧，实际compute-sanitizer |
| prefix4 | `c08_h18_hg_wall_observe_prefix4_r1` | Release，6001次新更新，completed2000001/2002001/2004001/2006001，四帧 |
| replay | `c08_h18_hg_wall_observe_replay_GPU_r1` | Release，cap2196680，196680次新更新，最多100计划保存 |

所有profile均显式 `C08_HG_OPT_H18=1`，原Wendland H/dp1.8、dp.04、固定5us、AS.3/n2.55、AV.1、材料/动态渗流、keepfalse、固定平面NoPen、CompletedOnly保持；ReactionClosed=false。HG使用原同材料schema2 Wendland ψ0 PRE，开始时刻 `9.9999999997060076`、global2000000，冷启动HG历史为零，不是HG PART重启。P0、σ、κ、J等物理历史不重置。

两项短回归从已通过原 `c08_h18_as03_n255_r1` 的TimeMax10.9生成三件套复制，保持原basename和XML/BI4/Normals/Profile17字节；replay从已完成且原生审查通过的原 `c08_h18_as03n255_full3_r1` TimeMax13.0三件套复制。无GenCase、XML数值修改、PRE求解或half链。输出目录为 `tests/outputs/<tag>/`；新定义与计划在 `tests/configs/<tag>_Def.xml`、`<tag>.steps.csv`；admission/start/call/seal/run/status/日志均在 `tests/logs/<tag>.*`。已有partial或完成拒绝覆盖/重跑。

时钟逐步 `clock += .000005`，不以n×dt替代。短回归分别绑定保留opt Debug2/Prefix4的真实保存态；debug2第二帧是绝对cap的真实强制末保存，不冒充原91计划第二行。replay保留原full301基准表与新100表两个独立路径：新前99行与full301的Part0000–0098完全匹配，Part0098是completed2196001、实际时刻 `10.980004999668907`；新Part0099仅在正常达到cap时保存completed2196680/saved2196679，其实际时刻仍由连续累加计算。原失败full3的301计划不被改成100；旧失败99帧不被改成完整301或100。

replay prepare/run都须独立绑定并通过本候选自己的Debug2和prefix4 `.run.json/.check.json`：真实Win32/Popen/所有权正常、唯一原生调用/22数组/6805IDs/时钟/layout/signed完整一致；Debug还须memcheck零错误泄漏、四行60列HG、907392字节first-n及配置一致；Release须八行60列HG一致且保存了真实塑性阶段。policy要求root明确审阅同一模型参数，允许检查器以 `policy_equal` 或通用 `policy_only_family_label_changed` 字段表达；本插桩本身没有改变HG family。缓存检查是一致性，首力参考是完整原快照传递，不新增独立CPU材料返回或力学求解。

replay的比较参考是原真实失败 `c08_h18_hg_opt_full3_GPU_r1`，其Win32/Popen=1、observed99、所有权正常必须保留为失败。失败wrapper没有正常完成PARTs封存，所以脚本只在prepare时明确记录现存99文件stat，不编造旧收据或已通过状态。它只作为之后实际相同保存step/time的无反馈前缀来源，原始99帧头和所有signed行均保留。新reader以后必须单独适配本100计划下的partial99或正常100，不能直接套用绑定旧301计划的failed99 reader。本jobs从不自动调用reader。

owner/实际工具与目标Win32句柄、创建时间/exe/argv/parent、独立solver_completed封存、Run.csv内嵌分号解析、原异常首因及最后原始console PART行的处理沿用旧opt jobs。Debug实际由compute-sanitizer包裹，目标身份独立核对。正常0且100帧只表示到达新有限cap、待原生及观测审查，不是故障重现或物理验收。预期stage1墙异常若发生仍记真实solver失败；绝不因“预期”而改passed=true或填造未保存故障时刻。

失败后只从原console日志描述性整理 `C08_HG_WALL_OBS` 的reason1–7、目标B/stage1的FIT/M、actual C/raw C、donor三类行/末标记和B距离并集观测。reason2的M不完整，reason4余下v未初始化，不能补齐。每个目标donor index必须完整连续，DONOR/C/W行数须与唯一末标记数量相同；没有末标记或计数不全只能说观测不完整。日志中的donor身份只是实际sorted slot，不是native ID。run/status记录结构性覆盖及数值解释待审，不把计数齐全当作数学或物理修复。原实际矩阵/donor值仍留在原日志，root需单独分析其含义及与原99真实保存态的全部字节/HG前缀关系。

每个phase要求当前root线程 `01a07683-bc64-7463-8db7-9ee6243967d8`，绑定本script/note、新r2 build及明确profile。run另绑定准备收据。Debug2/prefix4不投递终态队列。replay两个admission还要求 `single_bounded_replay_only=true`、`terminal_queue_once=true`、原已核验Codex EXE stat及root物理决策收据；仅其真实调用终态并写好run/status后，同一直接owner尝试一次45s同线程queue。超时记delivery_uncertain，不重发/重布防，也不并挂watcher。prepare从不投递。

将来仅在独立准入后使用：`python -X utf8 -B tests/support/c08_h18_hg_wall_observe_jobs_r1.py prepare|run --profile debug2|prefix4|replay --execution-authorized`。replay估算须参考旧约110分47秒实际成本，不把它说成秒级探针。任何profile都不自动启动下一求解器、其他ψ、PRE、half、VTK或正式发布；completed-solver派生失败只能修离线派生。安全门、负孔压和失败partial全部保留。

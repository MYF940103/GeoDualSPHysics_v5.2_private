# C08 host-only墙异常捕获：实施通过，有限重放运行中

原optimized-HG完整3s试验仍是失败：最后保存99帧至实际10.980004999668907s；原日志报告stage1/wall894在source10.983389999668779s拒绝。报告的异常时刻不是已保存native态。原失败、PRE和99帧数据保持原样，当前没有物理或论文精度验收。

host-capture r1的实际Debug/Release编译均Popen=Win32=2，原因是既有Windows max宏展开numeric_limits::max()。未链接或运行该程序。新r2只给新增helper四处max调用加局部括号，保留原宏/flags/数值；其Debug/Release实际CL和link均0，113个原对象及次序保持，仅替换mDBC host对象。全部原物理CUDA和三个opt私有对象均保留。原代码/公开XML无修改，SHA扫描0。

新Debug2和Release6001步各只求解一次、原生读取一次。两项均通过原22数组、6805 IDs及原时钟/ledger/FS/P0/J/plane/signed门；完整typed22、全部layout/clock/signed行、HG四行或八行、policy与原opt控制逐byte一致。Debug实际memcheck0错误/0泄漏，完整907392字节first-n CSV及配置相同；Release含真实塑性阶段。缓存检查仍只是coherence，不是独立材料返回，短窗不是half或物理验收。

第一次离线对照误将该CSV写成.bin叶名，原分析失败check和脚本保留；fresh short_review_r2只修文件名和新检查输出，未重跑求解器/reader、未放宽或屏蔽任何字段。已执行jobs_r1也保留；后续jobs_r2仅改说明路径和指向fresh review_r2检查，直接采用真实Debug2。

已独立准入并启动唯一c08_h18_hg_wall_host_replay_GPU_r1：本地RTX3050、owner48700、solver3620（创建时间/argv/parent见launch_review），复用原同材料schema2 PRE、cold-zero HG；最多196680次新更新、cap2196680、新100行计划，实际cap时钟10.983399999668778。前99计划与原full301共同时刻保持；原99/301头不修改。约110分钟成本为历史估计，不是隔离性能结果。

只有原GPU异常后才尽力捕获WallFaultCaptureHostR1输入；未保存的拟合M/C寄存器不可恢复。缺失或不完整捕获不自动重试。future fault_review和100计划native工具仅为已审作者稿，尚未构建/执行，其独立解析、原生prefix和图审仍待真实终态。

本次直接owner是唯一完成机制，终态只尝试一次45s同线程queue；没有watcher、重挂、half、PRE重算或其他ψ任务。所有物理参数/原门保持，NoPen仍ReactionClosed=false。完成后独立判断真实支撑与C外推原因，再决定必要修复；正常cap完成也不等于物理修复。

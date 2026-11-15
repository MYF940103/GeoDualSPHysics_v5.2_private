# C08 原墙异常真实重现与99帧审查

本次host-only重放仍失败，solver/tool的Popen和Win32均为1、身份无错误；原工具会话也返回1。没有存活的原owner/solver。原错误为stage1、sorted slot690、native894、reported source10.983389999668779、step2196678，与旧full3相同。最后真实保存为Part98/completed2196001、actual10.980004999668907；source故障时刻不是保存态。新100计划与旧base301分开保存，未达到的新cap2196680没有被当作完成。

原console PART98与capture stderr发生串接，两份原文都在终态audit原样保留；Run.out的完整最后PART行也单列，未改写历史日志。本直接owner仅一次终态队列，已投递；没有重挂、重试或其他物理求解。

新100计划专用工具只独立读取一次实际99帧。原22数组/6805 IDs、495000 ledger、178695 fixed markers、673695 P0 bits、990000 plane gaps及99条signed interval检查通过；completion仍passed=false/partial=true/saved_prefix_native_passed=true，整个试验不通过。完整99个typed记录（142824132记录字节，另有原12字节头）、layout/clock/signed全部字节及198行HG，与旧full3失败99帧完全相同。两个99头和100/301计划均未改写；不是与旧.9s强制末帧混比。

异常后实际捕获11份数组：Np6805、Npb1805、NpbOk940，实际fluid cell table608项。CSV保留原sorted顺序和raw hex。它们是新重放失败子阶段输入，不是committed native，也不是旧未保存状态的恢复；失败墙CorrMat输入为零，不是被拒绝的fitted C。

独立源码顺序复算得到：原镜像17个donor，J最小.9985493263，donor C的对称部分最小特征值至少.9774653145、最小xz行列式1.1612953524，未发现其本身失效。主MLS detM=.0010000250304429627，仅比原.001门高2.5030443e-8；外推C xz行列式约−.0252207263、对称部分最小特征值−.0139037474。17个anchored系数有13个负值、L1=5.7270055。线性外推不保持矩阵正定/正定向，是主要候选机制。

上述M/C为CPU独立重算，不是GPU寄存器；原fastmath/FMA在几何门附近仍存在不确定。因此下一步仅准备原已编译Release GPU核的冻结输入组件：A原实际C须先复现invalid690，B只把fluid C改成常量I作归因反事实。I不是拟用于物理计算的修复。另准备单次nearest重拟合的离线候选；不改原门、不增加第三次fallback或阈值拟合。此处尚未运行上述组件或采用候选。

原生、捕获和图的审查相互独立。NoPen仍为FixedPlaneStageProjectionReleaseOnly/ReactionClosed=false，HG仍cold-zero从同材料PRE起算。没有完整3s/论文精度/耦合能量或其他ψ验收，原BI4/PRE/程序与全部失败数据保持原样。生产源码、正式XML/BAT未改，SHA扫描0。

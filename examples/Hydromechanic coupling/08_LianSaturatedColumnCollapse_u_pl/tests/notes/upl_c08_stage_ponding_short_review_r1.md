# C08：撤墙后半步正压投影的短实现检查

这是未获完整物理验收的候选。沿用 AS epsilon=.2 / exponent3、Cubic h/dp1.2、dt2.5us、原r2 GPU10s PRE、keep5和固定平面接触；只改变撤墙后自由渗流边界的投影时序。其他psi仍锁定，正式runtime/XML/BAT和历史结果没有替换。

## 源码与构建

JSphCpu.cpp / JSphGpu.cpp 的 ApplyPorePressureBoundaries 新增窄门：原completed投影保持，动态反馈重力容器释放后也投影当前half压力。仍只清normal-native FS2/3的有限正压，不写负压、rate、P0、J、sigma、kappa或保存的p_n。下一force已有wall-state刷新；没有新增墙/FS/force遍历。JSph.cpp添加typed策略/active标记；XML指南只同步说明，默认FreeSeepage=0不变，没有新增输入参数。

首个CPU Debug构建因JSph基类不可见PorosityFeedback而实际exit1，r1源码归档/调用/失败记录均保留。两处基类说明资格改用公开HydroMechDynamicSeepage；子类实际数值门仍要求PorosityFeedback。新source_r2下CPU Debug、GPU Debug、GPU Release均实际构建通过，canonical四程序、runtime_r5和PRE保持不变。GPU Debug/Release启用既有输出型C08_STAGE_TRACE；CPU Debug不启用。

构建没有剩余错误；警告包括隔离Temp目录的MSB8029、Debug旧Gm选项D9035，以及第三方Debug库缺PDB的LNK4099。未为消除这些既有配置/调试信息警告修改项目或数值代码。

## 真实短计算及检查

三组各800次新增更新，到global4000800，实际保存两帧completed4000400/4000800。CPU Debug直接复用已完成r1求解；其后检查误要求新启动说明，但实际solver/Popen/Win32均0。新CPU_adopt收据只离线修复这一后检查，原passed=false记录保留，未重复CPU求解。GPU Debug/Release为独立新r2任务，各只一次求解。

已知日志缺陷：InitSoilParameters打印说明早于gravitypreload解析，因此当前已构建程序启动时仍打印旧completed-only说明。它不能证明运行时策略关闭。发布前应修复说明的打印时序/措辞；本轮不改正在消费的程序或source_r2归档。真实每帧typed ReleasedSubstages/Active标记由专用reader独立验证。

三组native各唯一读取一次：每组2帧、6805 IDs、22数组，原P0/ledger/rho/J/n/k/塑性历史/FS/plane/scalar clock/signed-dterror门全部通过。GPU Debug memcheck实际0 errors /0 leaks。两份GPU trace均通过新smoke2ms检查：363行、20个真实half ponding事件；half FS与下一force匹配，pressure/rate接续和保存p_n基值逐位门保留。Debug记录中40个half FS2/3观测、28个负压原样保留、17次有限正压被清零；没有把启动说明当实际行为证据。

CPU Debug对GPU Debug及GPU Release，两时刻共4行功能比较通过：孔压RMS最大差0.00416621Pa，材料XYZ位移差最大2.17952e-7mm，clock差0。原功能screen预算为5Pa/.005mm/1e-14s；这不是half、0ULP或物理理论误差验收。

## 后续窗口与保护

首次窗口owner在防重复preflight被根写入的同job前缀launch.json拦住；GenCase/solver均0，没有输入或物理输出。原r1不重启，原启动/stderr/audit保留。新r2只改job/note/BAT身份，launcher记录改用独立owner_r2前缀。

新 upl_c08_stage_ponding_window_GPU_r2 已真实启动：owner21840、GPU目标60968，264000更新/66帧/0.66s，采用同一已短验Release_r2程序和原PRE。一个直接owner仅一次终态通知；不自动解码、VTK、下一solver、其他psi或额外half。正常退出仍须完整native与物理比较。

补充离线结果：同长窗口内最小近对的native-double谱估算为净排斥，不能把每个小粒距都称张拉吸引；四个保存态的一次shifting proposal最大约4um，raw方案存在约2um的FS法向RMS位移，冻结FS/邻带可消除该法向位移，但单次近对数不变。两者均非动态稳定性证明，不据此打开未对齐输运的shifting或继续盲增AS。

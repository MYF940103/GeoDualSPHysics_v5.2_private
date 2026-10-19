# GPU 向量SPR与固定格点事件同步

## 制造场及关闭路径通过

CPU Debug/Release、GPU Debug/Release构建均退出0；GPU Release无新编译警告，Debug保留既有第三方PDB/运行库警告。`mdbc_gpu_vector_rel_r1`和`mdbc_gpu_vector_dbg_r1`各18组通过，最大镜像速度绝对误差5.62006e-8 m/s。独立CSV重算与三后端图审查见`logs/mdbc_gpu_vector_review_r1.check.json`、`.visual.json`及`figures/mdbc_gpu_vector_review_r1.png`，最大误差/原容差为0.117861172。S/P还通过符合边界的仿射解析梯度检查；R的公共墙速度0 ULP接线证明仅针对土粒子，全部原生粒子的R另作MLS/解析辅助速度对照，不混称墙粒子0 ULP证明。

关闭SPR的四组GPU回归（Debug/Release各HG开/关）全部21帧原生字段逐位一致：`gpu_spr_off_rel_r2.check.json`及`gpu_spr_off_dbg_r1.check.json`。初次`gpu_spr_off_rel_r1`采用了旧r1读取器，其旧保存步号约定导致离线元数据拒绝；原记录保留。r2采用上一阶段实际使用的r2读取器复核已有HG关闭结果，仅新跑尚未执行的HG开启组，没有重跑已完成solver。原孔压MLS三函数文本6749字符与G3基线一致。

以上是制造场与实现回归，尚非耦合长程验收。接续事件谓词同步和短窗。

事件补丁只修改`JSphGpu.cpp::IsHydroMechDrainageActive()`，逐式采用CPU已验证的固定格点舍入条件；`JSph.cpp`移除GPU专属禁用，保留现有输入格点校验。`gpu_drainage_event_r1.check.json`记录Debug/Release各3318个实际累计时间样本，粗/半步与0/.001/.01 s事件CPU/GPU判断一致，各两次只纠正名义事件步的累计舍入。开关关闭、提前一步、非舍入时间滞后及禁用水力过程的检查通过。对应CPU Debug和GPU Debug/Release增量构建退出0。

## 生产修改位置

以下行号对应本轮源码；G1/G2/G3此前修改不重复计入本轮新增。

| 文件与位置 | 修改功能和目的 |
| --- | --- |
| `src/source/JSphGpu.h:155,300` | 导数专用float3临时墙速度与重构入口，区别于真实墙速度和黏性切向速度。 |
| `src/source/JSphGpu.cpp:157,385,1381,1421` | 初始化、数组池计数、每阶段分配/释放；开关关闭不分配。 |
| `src/source/JSphGpu.cpp:1196` | 明确速度参数的GPU重构调用，不复用孔压物理入口。 |
| `src/source/JSphGpu.cpp:1104` | 与CPU相同的排水事件固定格点舍入谓词，关闭选项保留原时间判断。 |
| `src/source/JSphGpuSingle.cpp:147,262` | 与CPU同范围的选项和固定平面几何检查，避免把一维测试推广成复杂边界支持。 |
| `src/source/JSphGpuSingle.cpp:630,665` | 每次力阶段mDBC之后重构，传入真实交互；即使跳过mDBC校正，也重算当前导数速度。 |
| `src/source/JSphGpu_ker.h:166,212,255,300` | 交互参数及速度重构CUDA接口；旧调用默认空指针。 |
| `src/source/JSphGpu_ker.cu:1443,1527` | 三分量共享MLS矩阵及按SlipMode映射；CPU一致的double几何/累加、有效性和零阶/无支持回退。原标量孔压MLS不修改。 |
| `src/source/JSphGpu_ker.cu:438,468,492,512` | 墙—土连续方程使用辅助墙速度，黏性估计继续原速度。 |
| `src/source/JSphGpu_ker.cu:1651,1772,1800,1820,1905` | 土—墙的R、P压缩源和S梯度接线；Darcy、黏性、动量和外载保留原数据。 |
| `src/source/JSphGpu_ker.cu:1958,2056,2381,2405,2447,2457` | 核参数逐层传递、occupancy指针类型同步；只在SPR开启时补齐CPU已有墙密度率遍历。 |
| `src/source/JSph.cpp:597`附近 | 移除已移植功能的GPU专属禁用；现有参数值及固定格点合法性检查保留。 |
| `doc/xml_format/_FmtXML_ElastoplasticSoil.xml:55,96,103` | 同步GPU事件/向量SPR已验范围及长程尚待验证状态。 |

CPU默认Debug构建、CPU Release及GPU Debug/Release均实际完成。新增支持程序位于`tests/support`：`mdbc_gpu_vector_test.cpp`为制造场，`gpu_fixture_build.ps1`链接真实工程对象，`mdbc_gpu_vector_run.py`运行，`mdbc_gpu_vector_review.py`独立CSV复核绘图，`gpu_spr_off_run.py`关闭路径回归，`gpu_drainage_event_test.cpp`/`gpu_event_run.py`为事件检查；它们均不加入求解器工程。

`gpu_coupled_test.cpp`仅复用真实GPU积分器并按整数步采样，`gpu_coupled_run.py`准备标准XML/BAT并运行，`gpu_coupled_compare.py`以固定原生材料ID/实际时间逐帧复核和绘图，`gpu_spr_sequence.py`为下一长阶段单次接续。最初的GPU测试伴随程序r1因引用仅存在于`.cpp`内部的自由面辅助函数而编译失败；r2用相同枚举判断修正，仅改测试程序，日志保留。无生产编译失败、无物理公式调整。

## 已完成耦合短窗

Debug `gpu_spr_dbg03_r1`完成3000步，实际0.029999999999998948 s、31个样本，HG四阶段及缓存计数完整。相对CPU同时间前缀孔压RMS最大差0.00884051 Pa，顶部材料沉降最大差2.96750e-8 mm；对比图已查看。这是不同后端的精度对照，不称为0 ULP。

Release `gpu_spr_015_c_r1`完成15000步，实际0.15000000000000924 s、151个样本。相对CPU孔压RMS最大差0.01131572 Pa、顶部材料沉降差4.26041e-8 mm。离线包含0.1 s舍入邻域的完整原安全门通过：最大层总应力残差73.3650 Pa、顶部层间差84.98494 Pa；载荷、排水、几何、无穿墙、HG步长/小转动/虚功均通过，图已查看。半步长尚待成对验收。

运行时快速检查只负责有限值/原生集合及应力/顶部差；离线检查复核全部原安全门，后继阶段须以离线收据为准。0.1 s判断的累计舍入差由离线`>=.1-1e-7`覆盖，不能把快速检查遗漏该单帧的数值写成完整最大值。

Release半步`gpu_spr_015_h_r1`亦通过，30000步、151样本，实际0.15000000000007963 s；相对CPU同dt的最大孔压RMS差0.01803005 Pa、顶部材料沉降差2.43546e-8 mm。GPU粗/半步151样本的最大孔压RMS差4.17837449 Pa、顶部材料沉降差9.345127e-5 mm，原5 Pa/0.005 mm门通过。两条完整轨迹的载荷、排水、几何、无穿墙、0.1 s后100 Pa应力/顶部差，以及HG时序、步长、小转动和虚功门均通过。三张图已查看，收据`gpu_spr_short_r1.visual.json`绑定对应检查和图。未宣称新的2Tv验收。

本轮粗/半步主循环为191.63/241.72 s，粗步期间CPU重编译有重叠，不能据此作受控CPU/GPU速度结论。下一步单独计时，随后15 s粗/半步；只以真实完成的长窗收据准入完整2Tv。`mdbc_snapshot.ps1`扩大GPU支持脚本匹配到`gpu_*`，使本轮新增伴随程序/运行器也能随短窗基线保存；不移动旧结果。

## 短窗保存、独立计时和长窗启动

短窗通过版本保存为`outputs/gpu_spr_short_verified`，741个源文件/工程/对象/程序/支持文件的源与副本哈希见`logs/gpu_spr_short_verified.snapshot.json`。该快照还保存运行器旧版，便于复核短窗收据；保存不等于长程验收。

随后只改`support/gpu_coupled_run.py`的监测：把原离线已通过的几何、无穿墙、载荷和排水条件加入运行时检查，0.1 s采用与原关卡相同的`>=.1-1e-7`，状态轮询改为5 s。没有改C++、XML物理参数、积分或输出采样。`support/gpu_safety_test.py`的11个异常样本均被拒绝，保留CPU151样本重放精确恢复73.3648629 Pa/84.9843864 Pa原最大值，见`logs/gpu_safety_r1.check.json`。

`support/gpu_delivery_bench.py`用正式CPU/GPU Release程序、同一配置、3000步、无粒子场输出，先各预热一次，再3组交替顺序计时；两端主线程均限逻辑CPU0，CPU为1线程，未修改系统亲和性。结果`logs/gpu_delivery_bench_r1.check.json`：CPU中位25.597725 s（24.528858–25.628939），GPU中位19.152983 s（18.926250–19.709873），CPU/GPU耗时比1.33649，GPU耗时减少约25.18%。各程序正常退出、1040原生粒子、3000步及HG阶段计数通过。没有场输出，不声称本次计时另作逐位精度验证；也不是完整2Tv或大粒子规模加速率。

已启动唯一`gpu_spr_15_r1`接续worker，PID8312，当前线程绑定及启动收据为`logs/gpu_spr_15_r1.launch.json`。计划只新跑`gpu_spr_15_c_r1`（dt=1e-5）和`gpu_spr_15_h_r1`（dt=5e-6），各15001样本；每条完成后先核对已验GPU短窗的状态/HG字节前缀，再与保留CPU同dt的15 s轨迹比较，最后执行原5 Pa/0.005 mm半步门。全部原安全门保持，不因旧局部Q趋势阻塞用户已暂时接受的交付，也不绕过新增GPU实现检查。

启动后核验：worker8312→运行器24920→GPU52036，只有这一条物理运行。粗步已实际到0.21100000000007024 s/212样本，原安全门通过；前0.15 s的`state.csv`（41396661字节）与`hourglass.csv`（59446字节）相对已验短窗的对应前缀逐字节一致。这只是启动/前缀检查，尚非15 s完成。实时进度读`logs/gpu_spr_15_c_r1.run.json`的`safety.last_time_s`及序列`stage`；序列顶层`status`在终态前沿用初始化标签，不能据该标签误判没有开始计算。

该worker只在终态调用一次已核对帮助的`codex queue --thread 当前线程`，不发连通性自测、不重启旧通知器。完成/失败后同会话复核并接续完整CPU/GPU2Tv、Git、三组正式输入/计算/绘图及最终整理。新增`support/gpu_prefix_check.py`只读比较已保存前缀，`gpu_spr_sequence.py`负责门控和一次性接续；正式XML/BAT和Git尚未改动。

实际积分短窗将新增`support/gpu_coupled_test.cpp`、`gpu_coupled_run.py`和对比脚本，复用原`hg_release_run.py`的XML渲染/准备规则和保留粒子。保持k=1e-4、xi=.1、eta=.04、mode5、应力率修正、SPR及固定事件开启；dt=1e-5/5e-6。GPU测试调用真实`ComputeStep_Sym()`，只按整数步采样，与既有CPU测试的采样时间层一致；不复制积分公式。原5 Pa/0.005 mm半步及0.1 s后100 Pa层总应力/顶部层间差要求继续使用。

2026-10-18接续：G3已保存到`outputs/gpu_g3_verified`，729个文件哈希见`logs/gpu_g3_verified.snapshot.json`。

本轮只移植已通过的CPU固定平面导数重构。`JSphGpu.h/.cpp`新增阶段临时`BoundDerivativeVelg`及入口；`JSphGpuSingle.cpp`每次mDBC之后重构，并采用与CPU相同的固定平面检查；`JSphGpu_ker.h/.cu`新增三分量MLS，分别按Vel0/NoSlip/FreeSlip映射，并接到应力率、孔压压缩源项及连续方程。旧孔压MLS函数不修改，不再以孔压参数名传递速度。

GPU原墙—土连续方程遍历被`if(0)`禁用，而CPU实际执行该遍历。只在SPR开启时启用带辅助速度的墙密度率，以同步CPU；关闭SPR时保留原路径。真实墙速度、动量/黏性、Darcy和外载继续使用原数据。此项是实现差异，须验证，不能仅凭重构速度正确就验收。

测试新增`support/mdbc_gpu_vector_test.cpp`、`gpu_fixture_build.ps1`和`mdbc_gpu_vector_run.py`，程序及制造场结果在`outputs/mdbc_gpu_*`，收据/构建日志在`logs`。复用既有`mdbc_plane_r2`的18组普通GenCase输入，不重跑GenCase。验收在运行前沿用CPU原标准：墙速度`32*FLT_EPSILON*max(.125,abs(reference))`；实际S/P/R与解析辅助速度替换的生产算子对照采用原20 Pa/s、2000 Pa/s、.02 kg/m3/s加`2e-5*abs(reference)`；连续方程接线参考检查覆盖土粒子及墙粒子。符合边界的仿射场S/P还须满足解析梯度。检查三种SlipMode、二维/三维、水平/竖直/倾斜墙、禁用墙回退和无有效支持回退。

通过制造场后才做同后端关闭路径回归、事件时序和耦合短窗/半步/长窗。正式输入、Git及完整2Tv尚未执行。固定格点事件当前仍由原GPU保护阻止，另作小补丁和测试。

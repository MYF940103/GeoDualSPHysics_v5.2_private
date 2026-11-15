# C08 优化 HG：动态墙终态原因观测构建

仅作者阶段，新增 `tests/support/c08_h18_hg_wall_observe_r1_build.py` 和本文。不 import 测试脚本、不准备或构建、不运行 help/求解器/reader/VTK、不操作 Git、不扫描哈希。不新增 jobs、watcher 或队列。root 完整审阅后须对每个构建配置独立准入；当前文本不是执行许可。

原 `c08_h18_hg_opt_full3_GPU_r1` 已真实失败，Win32/Popen均为1。保留99个真实保存态，Part0098实际时刻 `10.980004999668907`、completed2196001。原日志报告 stage1、wall native894/sorted690、B=`(4.9000000000000004,0,-0.019999999999999962)`、normal约`(0,0,.04)`、source time=`10.983389999668779`、step2196678；这是未保存阶段的错误报告，不能冒充保存的原生状态。新构建不能覆盖或重新启动该失败任务。

通用 host 报错将多个拒绝分支合并：raw donor J无效、MLS几何/参与/正权重失败、拟合值非有限，以及 stage1 重构 C 的 xz 行列式非正。`atomicMin` 选择最低 sorted slot，不证明它是唯一失败点或最早发生的物理错误。99帧的22原生数组不含 CorrMat、BoundMode、PosCell，不能据此精确重建该未保存分支。

本候选仅输出已有拒绝分支的实际局部数据，沿用旧 `c08_h18_wall_fail_gpu_r1_build.py` 的私有单TU构建模式，但基线改为实际 `c08_h18_hg_opt_{Debug|Release}_r1.build.json` 的114对象程序。只替换一个原始 `JSphGpu_ker.cu.obj`：保留110个原物理对象及两个 opt host 和一个 opt HG对象，另编译一个插桩物理 CUDA TU，仍链接114个对象。HG Node、两个缓存材料积分消费者及其 host 不重新编译。不是完整VS重编译，也不是CPU/GPU算法变更。

| 原有失败位置 | reason | 观测范围 |
| --- | --- | --- |
| 接收墙身份/法向无效 | 1 | code、fixed、B、法向、法向长度；M尚不存在，明确不完整 |
| 支撑 donor J非有限或不大于solid0 | 2 | 真实 donor sorted slot/J、此时部分 M和参与和；`incomplete_M=1` |
| 原一次最近真实点重试已耗尽或不合资格 | 3 | 完整 M9/原行列式、参与和、最近点、G、累计shift、attempt |
| 任一拟合分量非有限 | 4 | 原field下标/value/nearest/sum/梯度和完整几何；其余拟合v未初始化，不转储它们 |
| 原stage0 J/压力/速度域拒绝 | 5 | 原J、压力、dv/tv和完整拟合几何 |
| 原stage1 C行列式非有限或非正 | 6 | 真正Q奇偶映射后的C9、原determinant变量、对称缺陷；另记映射前完整v9 |
| 原stage2加速度非有限 | 7 | 原加速度及拟合几何 |

只有上表既有 `atomicMin(invalid,p1);return;` 之前调用新观测。原正常路径的算式、临时量、先后顺序、门槛、最近点重试、物理数组写回和返回语句均保持原样。新增辅助函数的距离、W/V、矩阵诊断和邻域循环只在失败分支进入。生成时逐条唯一替换；逆序删除新增helper/调用/stdio include必须恢复两个实际冻结源文件的全部原字节，原 atomicMin/return数量也必须一致。这个源码证明不代替新机器码的真实无反馈检查。

所有失败点可记录基础原因与已有M，但完整 donor 转储仅限 stage1 且B精确等于上述原墙存储坐标，避免为大量无关墙产生海量日志；这只是观测选择器，不改变参与规则。失败helper在当前G复用同一cell遍历、`CODE_IsFluid`、原float距离支撑判断，输出每个真实 donor 的sorted slot/code/xyz/J、C9、核W/fac、V、WV与梯度WV，末尾输出实际数量及最近sorted slot。没有Idp参数，绝不伪造 donor native ID。不能缺省截断 donor 数量；root后续必须检查末标记和完整计数，CUDA printf缓冲丢失时只能判观测不完整。

该目标还在失败后只读重查当前物理B支撑，记录double坐标、PosCell xz与实际force xyz三种距离的inside计数/并集/最小距离以及当前BoundMode。此重查不赋值BoundMode，遍历完整候选集合而非原stage0的找到一个即停止，因此是独立原因观测；不能谎称它保存了stage0当时的搜索顺序。辅助函数不改变J、压力、C、κ、坐标、边界或任何其他物理状态。

构建配置只有 `Debug` 和 `Release`，单次调用只构建一个。每项需 `tests/logs/c08_h18_hg_wall_observe_r1_<Configuration>.root_build_admission.json`，字段包括 `authorized`、相同 `allowed_stage`、`configuration`、本脚本/本文stat、实际 opt `source_build` stat、同root线程、`build_only=true`、`automatic_solver=false`、`automatic_reader=false`。没有自由输入/目标程序/物理参数路径。

未来私有源码副本与zip/diff/capture位于 `tests/outputs/c08_h18_hg_wall_observe_r1_<Configuration>_source/`，完整冻结include闭包和程序/runtime位于对应 `_build/`。中间文件位于无空格 `%TEMP%/c08_h18_hg_wall_observe_r1/<Configuration>`。真实compile/link call、日志和完成检查位于 `tests/logs/c08_h18_hg_wall_observe_r1_<Configuration>.*`。任意已有partial或完成均拒绝；没有自动重试、删除或覆盖。

使用原实际 NVCC 物理TU recipe，保持 CUDA11.7/MSVC14.36/sm86、原Debug或Release编译设置、fast-math、宏和静态CUDA runtime；只重新定位源、obj、PDB、keep和include闭包。链接消费原opt实际child argv及顺序，替换唯一物理CUDA对象和输出路径。拷贝原opt完整冻结源与九文件runtime，保护原PRE/程序/对象/source统计绑定；不依赖当前可变生产源构造新算法。一次配置只有一次NVCC和一次link，不运行生成后的程序。

如root之后认为确需约τ=.9834s的独立原因观测，必须先另行完成新Debug程序实际两帧memcheck/22原生数组/时钟/layout/signed/HG行/first-n快照检查，并做新Release与保留opt的四帧6001步同时间步全字节与八行HG比较，包含真实塑性阶段。该四帧回归足够作为实现准入，不新增物理half链。随后是否从同一认证PRE、冷HG重新做一个有限cap的新标签由root决定；没有精确HG PART重启捷径。原失败约110分47秒的成本须计入决策；绝不自动启动新物理窗、其他ψ或PRE。

后续命令仅在独立准入后使用：`python -X utf8 -B tests/support/c08_h18_hg_wall_observe_r1_build.py --configuration Debug|Release --execution-authorized`。构建/短回归/正常退出均不是墙算法修复、HG正确性或完整塌陷物理验收。原 det门槛、参与规则、饱和域、negative pressure和其余全部安全门保持不变。

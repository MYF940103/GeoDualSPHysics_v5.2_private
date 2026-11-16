# Cryer GPU 启动实施资格根审查摘要

本稿汇总已实际完成的 C04 GPU source267、Debug/Release各full111构建、Debug B2 memcheck/native以及Release A/B/C128启动审查，已由根线程结合实际构建、运行及独立原生审查复核。只新增本说明与配套JSON，不改任何原收据，不给物理/峰值通过结论。当前C02唯一fresh B full2Tv及暂停C08不属于本摘要动作，未修改、停止、恢复或重启其任何依赖。

完整私有源为265个恢复基线文件＋两个C04 helper。只有 JSphGpu.cpp、JSphGpuSingle.cpp、JSphGpu_ker.cu 三个TU挂接；保留原三维XYZ Rγ/S、sphere中心/半径guard、raw confinement/ramp/drain、原力学/材料/J推进。B为α=.5/β0，C为α0/β0，采用材料ID拥有的history；S是leading-LP正预条件的一次defect correction，并非完整Jacobi/迭代隐式求解或已证二阶TPI。A默认不进入新分支；公共源码/正式XML及空间核、η、AV不改。此C04限定HG0/SPR0，不把C02 HG适配器套入Cryer。

原prepare_r1在写source输出前错误地把旧CUDA tlog唯一VS项目metadata当成源码路径，首因 `Old GPU local dependency path is absent from complete C04 source`。原失败740B收据保留，不重跑。新prepare_r2只把257个source/header依赖与1个项目metadata明确分开；helpers和18处hooks原样。其passed不被追认为旧111对象的历史完整源码捕获。

Debug和Release各自从权威恢复GPU SLN/project完整新编97CL+14CUDA=111对象，含两个 `.h.obj`，旧对象复用0。真实SDK10.0.22000.0、CUDA11.7、MSVC14.36；CL/NVCC实际flags与各自旧GPU recipe相符，依赖只读私有source及系统头。Debug27库/runtime5、Release26库/runtime4各自闭包通过；没有把Debug对象或库混给Release。实际owned MSBuild的Popen/Win32出口为0，内部cl/nvcc/link未逐个持句柄，不虚构其独立Win32退出码。FMA/FTZ/use_fast_math原策略保留。

Debug B2实际只运行一次，2更新、dt2^-20、强制末态2^-19 s、2帧。真实compute-sanitizer工具与target句柄出口均0，memcheck零错误，独立scratch device source/role fixture真实16cases恰一次。其唯一native读取与公式审查通过：22typed数组、37181 IDs、两帧74346侧车行、37173末态row公式、520422 core7检查、HG snapshot0；没有CPU两步参考或物理精度宣称。

Release A/B/C各自独立准入并只运行一次；硬前置为上述实际DebugB2 native/formula passed。原seed XML/BI4、dt=2^-20=9.5367431640625e−7 s、-nsteps128均不变。原TimeOut2^-13，因此真正两个保存态为t0/Step0与t2^-13=.0001220703125 s/Step127（completed128），不是128个逐ID保存态，也不是新half/ref窗口。原ramp2^-8和drain2^-7均未到达；三个post-open计数均0，排水/峰值/后期消散尚未覆盖。

| Release方案 | 同算法CPU128末态孔压RMS差（Pa） | 同算法CPU128材料XYZ最大差（mm） | 观测Simulation Runtime（s） | Total Runtime（s） |
|---|---:|---:|---:|---:|
| A 原有限Kw | 保留旧GPU128 common26/IDs/全clock逐字节相同 | 同左；不是CPU/GPU位相等 | 27.598143 | 27.656263 |
| B α=.5 β0 | 1.5862366883711e−5 | 3.086061849959357e−12 | 42.072620 | 42.511326 |
| C α0 β0 | 1.751450709640772e−5 | 5.15228731904838e−12 | 41.887569 | 42.317455 |

A无fixture和policy/csv/summary，新分支确实untaken。其全部common26、IDs、含原初始及非初始signed诊断的clock与保留真实旧GPU128精确相同；common26不含完整22原始数组，故不宣称raw22全数组位证明。22数组读取/安全通过与跨程序全部raw数组相同是不同结论。

B/C的同算法CPU对照均在两个真实保存时刻/同材料IDs上满足原5Pa/.005mm界限。末态有效应力Frobenius RMS差分别8.418282406744254e−8/1.2100327770687884e−7 Pa，最大J差1.0547118733938987e−13/1.5876189252139739e−13。FSNormal只要求自身有限，不作CPU/GPU逐bit门；signed dterror各自保留原门，不把跨后端差值另设新条件。这些是同算法短窗实施对照，不是B/C相对A的理论精度或跨模型5Pa等价。

所有Release solver Popen/Win32/target出口、独立reader Popen/Win32出口实际均0，start/call/run的target身份与argv一致，每组reader恰一次，review不重解码。37181全部IDs=37173soil+8fixed，22typed数组，原finite/elastic/no-out/geometry、P0/float excess、J/n/V/rho/恒k ledger、fixed marker及真实clock/Step/dt/signed检查均通过。每组ledger74346次、fixed marker16次、最大ledger相对误差0，最大半径.05000000000000002m。唯一非初始signed值A/B/C为−6.404499390309602e−7/−6.404513776629343e−7/−6.404512098568532e−7s，原符号保留，均满足<=1e−14；初始实际0未重写为空interval。

B/C各两帧74346侧车材料行、37173末态压力row对照，全部128commit/endpoint与33307008 core7检查及HG0通过。J按真正原GPU乘法/FMA的合法路径精确重算，B/C两种路径均各匹配37173点；ULP或绝对容差新增0。不声称独立观察了全部未保存逐ID状态，也不把cache/core coherence当新的独立物理求解。native PorePressRate仍为旧Kw/n缩放residual，不是B/C实际dp/dt。

实际硬件来自Run.csv为本机RTX3050。上述TSimul/TTotal包括当前Debug/Release设置和观测输出开销；同期工作及计时条件未控制，不把这些短窗数字当严格效率benchmark或对服务器A6000的性能预测。native saved-J质量乘LoadAce仍为proxy，未独立重算原力阶段.001预算。

选择性Git建议由配套JSON列精确相对路径，分完整267源码文本及项目/manifest、3TU+2helper最小子集、所有作者/说明、原prepare_r1失败、prepare_r2、两full111构建真实call、Debug memcheck/native、三组run/native/review/admission、原生小表与policy/summary。可按根判断去重已提交文件；本稿不执行Git/status/check-ignore。267源码文本可完整保存以免依赖本地快照，原始BI4/程序/大native导出不被称为云端Git备份。

排除EXE/DLL/LIB/OBJ/PDB/ILK/iobj/binlog、BI4/NBI4/重启链、VTK、common26.bin/clock.bin、全native_ids.csv和大型逐材料侧车。原路径本地保留、不删除。接下来仍需Cryer到达开排水/Mandel峰/消散的真实窗口、正确M0/finiteKw参考以及1%精度审查；本启动结果不自动准入新solver，不发布公共XML，不宣称完整状态重启或完整TPI物理验收。

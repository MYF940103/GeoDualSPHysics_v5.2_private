# 三组正式固结交付（2026-10-20）

前置CPU/GPU完整2Tv已审阅通过，结论见`gpu_release_result.md`；源码备份本地/远端均为`e8e6fabbab9517e1a72b411e0017f5edfc6cea67`，核验记录`logs/gpu_release_git_r1.json`。不再恢复KEEP或因旧Q趋势无限阻塞交付。

## 本轮修改位置

- 根目录`CaseTerzaghiConsolidation_q0_PR_full_k1em3_Def.xml`、`...k1em4_Def.xml`更新，新增`...k1em5_Def.xml`：沿既有XML结构，TopKernelBand、应力率修正、HG=.1、SPR、固定格点排水、阻尼=.04及SavePosDouble=1；孔压仍float，常n/k，无u-pl/TPI。只有一个TimeOut，无special/timeout重复配置。
- 相应三组根目录`x..._win64_CPU.bat`/`_GPU.bat`共六个入口：沿原声明及错误标签风格，生成→Release求解→particles→正式图。新`_release_CPU_out`/`_release_GPU_out`输出，移除自动删除/force覆盖；`-postprocess`可后处理已有完整数据。CPU一线程，与对照一致。
- 根目录README更新入口、状态、旧结果保护、程序/后处理依赖和限制。旧k1e-2及precision/double入口/输出不改。旧k1e-3/k1e-4的XML/CPU BAT及README五文件复制保护于`tests/outputs/formal_inputs_base_r1`。
- `support/read_hm_part.cpp`/`build_read_hm_part.ps1`：只读生产BI4；原生ID、double位置/应力、float孔压/密度/塑性历史。构建r2及六帧0 ULP检查见`logs/read_hm_part_r2.build.json`、`release_reader_r1.check.json`；运行程序在`bin/windows/ReadHydroMechPart_win64.exe`。CPU的外载数组未保存，明确load_available=0，不把占位零当测量。
- `support/release_case.py`：真正保存时间和固定材料ID的正式孔压剖面/沉降/应力/Q图与CSV；读取native double应力/位置，不由VTK回写。材料沉降公式已与既有参考在两个材料高度、四个时刻独立比对。原100 Pa应力/顶部差、几何、排水、GPU合力、弹性/无丢失等门保留；新组正常完成仍须审图，不自动变成物理验收。
- `tests/support/formal_release_prepare.py`只生成受检apply_patch，根目录文件实际由apply_patch更新。`formal_release_sequence.py`是唯一新阶段，只做正式程序短窗等价→发布已验k1e-4→正式k1e-3完整BAT；终态一次当前会话接续，不重启旧worker。

正式入口检查发现原CPU/GPU主循环只在TimePartNext或粒子损失停止时SaveData，终时不整除TimeOut时可能遗漏末帧。仅修改`src/source/JSphCpuSingle.cpp:1305`、`JSphGpuSingle.cpp:1100`的保存条件，补TimeMax或NstepsBreak末步；不移动、不增加力计算，不改dt、积分或边界闭合，且最后输出之后没有下一次物理步。对应CPU/GPU Debug/Release四次构建记录为`logs/formal_end_*_r1.build.log`。修改前两份源码、两份Release对象和两份Release程序在`tests/outputs/formal_end_output_base_r1`复制核验保护；旧完整2Tv来源仍为e8e6fab版本，不改写其哈希。

## 时长/步长（运行前固定）

| k (m/s) | dt (s) | 2Tv终时 (s) | 步数上限 | TimeOut (s) |
|---|---:|---:|---:|---:|
| 1e-3 | 1e-6 | 7.297429 | 7297429 | .001 |
| 1e-4 | 1e-5 | 72.88429 | 7288429 | .01 |
| 1e-5 | 1e-5 | 728.75286 | 72875286 | .1 |

终时按每组Cv求2Tv，再以Decimal上取整到固定dt；BAT的nsteps上限与之相同，分析仍取实际时间。不会把仅二进制元数据舍入当作物理失败。k1e-3扩散更快，使用原正式1e-6步；k1e-5不擅自放大未经检查的时间步，因此其长算可能约需数天。此处未开发TPI或放宽稳定条件。

## 顺序与准入

先用正式Release CPU/GPU与新GenCase输入各跑0.15 s、TimeOut=0.1 s，故意构成非整除末帧，保留于`tests/configs`和`tests/outputs/formal_program_cpu|gpu_r1`；临时gate只记录，不设第二个通知器。要求恰有初始、中间0.1 s和末尾0.15 s三帧，并对实际匹配的初末态要求物理字段0 ULP，不谎称全部不同采样时刻0 ULP。通过后保存新节点，唯一`formal_release_k3_r1`只采用已完成且源/程序/输入/输出哈希一致的两条短窗，不重复运行；任何短窗失败不启动新正式长算。

该检查已于2026-10-20 07:27 JST完成：CPU/GPU各3帧、实际末时0.15 s附近，初末位置、速度、密度、孔压、六个应力分量及塑性历史均与已验同端参照0 ULP；四个GenCase/求解子进程均退出0。原始证据为`logs/formal_program_gate_r1.status.json`及`formal_program_cpu_r1.check.json`、`formal_program_gpu_r1.check.json`。这仅验收正式入口/末帧保存等价，不把0.15 s当作新的完整物理验收。

两端通过后，把已验GPU k1e-4的data、HG及完成/运行记录复制发布到根目录新输出，逐文件核对哈希；原测试数据不搬走、不覆盖。单独`release_provenance.json`说明它来自已经验收的生产积分伴随程序，并非又执行了完整正式BAT。复制原始生成XML供参数与实际时间分析，来源清单不改名伪造。正式图仍由新只读PART处理器重算。

随后调用真正根目录k1e-3 GPU BAT，监控已封闭PART的native安全门，正常退出后执行完整原生分析和绘图。完成/失败仅队列通知一次，回到本会话审图并主动报告，继续k1e-5、三组图汇总、后续复杂边界与依赖清理和最终Git备份。k1e-5此阶段不提前启动；不依赖用户再询问。

不覆盖任何原始结果，不增加阻尼，不改原数值门，不从普通PART精确续算HG。范围仍是弹性、小转动、固定平面；没有塑性、大旋转、复杂边界或全周期半步验收。PartVTK是可视化显示字段，正式量化用原生double状态；PART仍不保存可用于精确HG重启的完整H/R历史。

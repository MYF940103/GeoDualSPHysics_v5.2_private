# 02 外载 1D 固结：入口与文件索引

更新日期：2026-10-21。孔压/孔压率仍为原生 float u-pw PR，无高低位补偿、无 double 孔压状态或KEEP密度补偿；持久应力及其历史为double。当前一维正式配置采用应力率梯度修正、归一化核支持带加载、xi=0.1弹性HG、固定平面SPR和固定格点排水事件，阻尼0.04。k=1e-4 CPU/GPU完整2Tv及k=1e-3正式GPU完整2Tv已按约定的一维范围验收，不能推广为塑性、复杂边界或大旋转验收。

## 当前正式图与数据

前两组完整2Tv的新图与配套数据统一从[figures/README.md](figures/README.md)进入：`full_validation_latest_history.png`、两组`full_validation_latest_profiles_k1em*.png`、新增`full_validation_latest_late_profiles.png`及残差诊断图。历史发布数据每组恢复按目标ΔTv=.005整理401个真实原生帧，保留目标/实际Tv、实际时刻和PART编号，未插值或重算。1.5Tv和2Tv原本已有，新晚期图将Tv=1、1.5、2拆成独立面板，避免全尺度下难以分辨。k=1e-5未完成，不混入正式对比。旧`full_validation_q0_*`与冻结验收图保留；旧`k5em4`是5e-4，不能当作本次1e-5。

XML的TimeOut始终以秒为单位。根目录三份正式XML现已恢复ΔTv=.005，对应k=1e-3/1e-4/1e-5的TimeOut分别为.0182185714285714/.182185714285714/1.82185714285714 s，CPU/GPU BAT均读取同一份XML，无须修改BAT。积分dt、TimeMax及其他物理/数值参数未变。k=1e-3和1e-4已完成，不为改变保存间隔重跑；其保留结果仍分别为.001/.01 s密采样，生成XML和图表来源记录不改写。正在运行的k5使用独立tests配置，本轮不改变其保存频率。旧401帧对应ΔTv≈.005，上一版发布误写为.01现已修正；旧发布已保存快照，完整定义见上述索引。

单设TimeOut恢复的是间隔，并非将每帧锚定于排水后的Tv=0：默认保存网格从物理t=0起算，而Tv=Cv(t-.01)/H²；实际保存还受积分步长落点影响。没有为此新增special/timeout，比较仍用实际时刻计算Tv，不将帧号当精确Tv。加载/排水初期安全门继续以保留的密采样诊断为依据，不用新的稀疏发行输出替代。

“固定格点排水”指固定时间步网格上的排水开启时刻对齐，只在tD恰落于N*dt且存在累计舍入误差时避免晚开一步，不是空间网格，不改变排水位置/p=0或输出频率。

## 当前正式入口

| 渗透系数 | XML文件末段 | CPU/GPU BAT文件末段 | 固定dt (s) | 2Tv终时 (s) |
|---|---|---|---:|---:|
| k=1e-3 m/s | `full_k1em3_Def.xml` | `full_k1em3_win64_CPU.bat` / `full_k1em3_win64_GPU.bat` | 0.000001 | 7.297429 |
| k=1e-4 m/s | `full_k1em4_Def.xml` | `full_k1em4_win64_CPU.bat` / `full_k1em4_win64_GPU.bat` | 0.00001 | 72.88429 |
| k=1e-5 m/s | `full_k1em5_Def.xml` | `full_k1em5_win64_CPU.bat` / `full_k1em5_win64_GPU.bat` | 0.00001 | 728.75286 |

XML完整前缀为`CaseTerzaghiConsolidation_q0_PR_`，BAT前缀为`xCaseTerzaghiConsolidation_q0_PR_`，均在本目录。CPU使用单线程，保持与验收配置一致。三组终时按各自Cv计算，再向上取整到固定步长；不复制k=1e-4终时到其他k，也不重复添加`special/timeout`。

正式CPU/GPU主循环已补末步保存条件：TimeMax或nsteps结束时，即使不整除TimeOut也保存原生末帧。这只是输出策略修复，不改步长或物理积分。

双击对应BAT：GenCase → 正式CPU/GPU Release求解器 → PartVTK生成`particles` → `support/release_case.py`读取原生double应力/位置和float孔压，正式图/CSV/检查结果保存在`figures/full_validation_release_k1em*_CPU|GPU*`。需要带numpy/pandas/matplotlib的Python，当前优先使用`D:\Anaconda3\python.exe`；只读PART工具为`bin/windows/ReadHydroMechPart_win64.exe`，其源码和构建脚本在本case的`support`。

新输出使用`CaseTerzaghiConsolidation_q0_PR_full_k1em*_release_CPU_out`或`_release_GPU_out`，不会覆盖旧`*_out`。已有新输出也不自动删除、不接受`-force`清除；可用同一BAT的`-postprocess`只做后处理，需新计算时明确选择另一个输出名。HG只支持新鲜启动，没有精确历史重启；长算中途关机不能拿普通PART精确续接本HG。

k=1e-4已复制发布本轮已验完整数据；正式CPU/GPU程序短窗与伴随程序初末态逐位一致，`release_provenance.json`明确记录来源，不谎称又通过BAT重算过一轮。k=1e-3已由根目录GPU BAT完成新计算：实际7.297429000666115 s、7297429步、7299帧，末期剖面RMSE 2.42883 Pa、顶部材料沉降3.657380 mm（解析误差-0.45405%）。k=1e-4相应为0.88109 Pa、3.658754 mm（-0.41667%）。两组正式`particles`及`figures/full_validation_release_k1em3_GPU*`、`k1em4_GPU*`均已生成并审阅；残余Q约10 Pa并未消失。去重21950文件哈希和原生抽样复核见`tests/logs/formal_release_k34_r1.review.json`。

k=1e-5必须单独完成2Tv，不能由前两组代替验收。原`formal_release_k5_r1`采用dt=1e-5、72875286步，曾估计约4天，但已被下述安全门停止，该估计不能用于后续细网格。旧worker及部分输出保持冻结；当前诊断见下段，不擅自从普通PART精确续接HG。旧k=1e-2输入/入口仍保留历史配置，本轮不修改、不代表新组合已验收。

**k=1e-5上述原网格长算已于0.10001 s触发原100 Pa安全门而停止，最后完整保存为0.20000 s，不是2Tv完成，也没有正式完整图。旧worker不重启，根目录部分输出保留。** CPU对照复现了这一早期排水面误差，单独减半dt不能解决；细化到dp=.003125后，已经完成全宽.15 s/1 s的5/2.5微秒检查，以及宽.025 m周期单元的同窗等价检查。缩窄单元只适用于一维均匀周期场，主循环短测实测快约2.4倍，尚不能直接替代长程验收。

2026-10-20进一步尝试8/4微秒：5 ms采样的1 s孔压半步最大差4.65046 Pa曾通过，但1 ms加密短窗在约.011 s发现9.66059 Pa差异，超过原5 Pa限值，因此拒绝该候选，不放宽门、不再搜dt。2026-10-21原5/2.5微秒的`k5_long5_r1`已完成15 s并审阅三图：15001对最大孔压半步差3.79523 Pa、沉降差.00023918 mm；两条各201个1 s共同前缀0 ULP，末时剖面RMSE6.760/7.290 Pa，材料沉降解析误差+.909%/+.880%。30448个记录哈希核对一致，底层材料仍有约.000025 mm额外偏差。15 s仅Tv=.041，不是晚期2Tv验收。

据此曾准入`tests/configs/k5_full_r1_Def.xml`及GPU BAT完整周期，输出在`tests/outputs/k5_full_r1`；dp=.003125、宽.025、固定5微秒、145750572步，原参数/安全门保持。该GPU运行已于2026-10-21为用户授权的加速试验主动结束：最后可读PART6056、实际6.055999999855318 s，不是2Tv，也非物理失败；原始输出全保留，审计为`tests/logs/k5_full_r1_acceleration_stop.json`，旧通知器已退役，不重启。

用户随后明确停止后端/步长比较，指定用CPU从头重跑1e-5。新入口为`tests/configs/k5_cpu_full_r1_Def.xml`和`xk5_cpu_full_r1_win64_CPU.bat`，输出`tests/outputs/k5_cpu_full_r1`，采用8线程、同一细网格/宽度和5微秒，不增大dt。该验证计算沿用前15 s原生1 ms、之后.1 s诊断采样，读取既有GPU15 s数据作5 Pa/.005 mm同物理前缀检查，不启动新GPU对照求解器；根目录发行XML的ΔTv=.005设置不变，正式图仍按实际Tv选帧。仅末帧生成particles；常规PART不能精确续接HG，必须新鲜启动。

CPU仅补齐已有加载加速度的原生输出`HydroMechLoadAce`，不改力/积分；.03 s、31帧旧物理字段逐位一致，总外力诊断误差最大6.12e-5 N/m（等效.1 m宽）。CPU Debug/Release构建通过。新CPU短测主循环37.076771 s/6000步，长程耗时仍为天级外推，不是完成承诺。具体改动、控制与自动终态接续见`tests/notes/k5_cpu_full_r1.md`及`tests/logs/k5_cpu_full_r1.status.json`。未启动的6.25微秒候选已撤出活动目录，归档于`tests/outputs/k5_dt625_notrun_r1`，不是验证通过的配置。

单元缩窄仍只具均匀一维短窗等价证据，不推广为一般滑坡/长横向波长验证。只有完整复核通过后才另行发布新k5，根目录原失败输出不覆盖。原准入证据见`tests/notes/formal_release_r1.md`及`logs/k5_full_admission_r1.json`，原短窗图在`tests/figures/k5_long5_r1_{history,profiles,half}.png`。

根目录历史XML和所有`*_out`保持原位，包括网格细化、precision和double历史输出。用户于2026-10-21授权清理后，仅将旧k1e-2、precision、double三个退役CPU BAT原样移至`tests/outputs/retired_root_inputs_r1`，避免根目录误点；不是删除结果。三个旧XML有历史生成脚本/恢复依赖或配对记录，暂不移动。归档BAT相对路径仍按原case根设计，不应在归档目录双击；用途与恢复说明见该目录README。当前三组正式XML及六份CPU/GPU BAT仍在根目录。更新前的两组正式XML/CPU BAT及本索引已另存`tests/outputs/formal_inputs_base_r1`；历史数据以各自`Run.out`、生成XML和版本记录确定来源，不能用当前更新后的根目录XML解释旧结果。

**当前三组CPU/GPU BAT没有删除路径。含覆盖确认/`-force`的旧k=1e-2 BAT已移出根目录原样归档，不要用它试跑或覆盖保留结果。临时验证仍放在`tests`分类目录。**

## 原位退役的精度试验

| 分组 | 状态及处理 |
|---|---|
| `full_k1em4_precision` | 高低位孔压累计补偿的历史完整2Tv结果；已退役。XML/out仍在根目录，BAT原样归档至`tests/outputs/retired_root_inputs_r1` |
| `full_k1em4_double` | double状态历史部分结果；停止于Part84、15.303610 s、1,530,361步，不是完整2Tv。XML/out仍在根目录，BAT同上归档 |
| `tests` 中 `pore_double_stage1` / `pore_double_vel0` | 历史短程迁移和步长敏感性检查，不能证明完整固结精度提高；严格压力审查曾有未通过项 |
| `tests` 中 `upw_float_restore` | 当前 float 回退验收证据，保留为基线，不归为 double 退役输出 |

precision完整结果仍有晚期孔压平台，详见[对比报告](figures/precision_q0_k1em4_report.md)。double未完成，不能据此宣称完整过程改善或有效加速。归档double BAT自带冻结程序/源码检查；当前float程序不满足它的运行条件。本次仅移动BAT、不改其字节，也不把double/补偿检查点交给float续算。归档BAT不能在新目录直接运行，恢复说明见归档README。

历史 [precision 运行说明](support/precision_q0_k1em4.md) 保留原文，其中“正式入口”等表述对应当时版本；当前状态以本索引为准。回退范围及验收见 [upw_float_restore.md](tests/notes/upw_float_restore.md)。

## 文件位置和依赖

- 根目录：正式 XML/BAT 和正式 `_out`；`figures`：正式图表；`support`：正式后处理及运行来源记录。沿用现有 `figures` 名称，不另外建立 `figure`。
- `tests`：临时配置、运行、日志、图和结论，见 [tests/README.md](tests/README.md)。
- `support/compare_double_q0.py`、`run_double_q0.py` 依赖 `tests/outputs/pore_double_vel0/reader/export_state.exe`、对应 build 日志及 `tests/outputs/pore_double_2tv/baseline_native`。这些支持链原位保留，不单独搬走。
- 历史自重迁移测试跨算例读取 01 的 `tests/outputs/CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out` 输入和 `CaseSWSt1_MLSDirect_GPU_out/data` 的 Part56。整理 01 时必须保留这些依赖。
- `tests/notes/upw_float_restore_before.zip`、`pore_double_stage1_baseline_sources.zip` 是历史源码/程序恢复档案，不是待清理的缓存。

今后的正式版本只有通过验收后才在根目录增加或更新对应 XML/BAT；测试文件不占根目录，原始输出和历史正式图不得被自动覆盖。

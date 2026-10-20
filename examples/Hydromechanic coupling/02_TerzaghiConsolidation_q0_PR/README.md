# 02 外载 1D 固结：入口与文件索引

更新日期：2026-10-20。孔压/孔压率仍为原生 float u-pw PR，无高低位补偿、无 double 孔压状态或KEEP密度补偿；持久应力及其历史为double。当前一维正式配置采用应力率梯度修正、归一化核支持带加载、xi=0.1弹性HG、固定平面SPR和固定格点排水事件，阻尼0.04。k=1e-4 CPU/GPU完整2Tv及k=1e-3正式GPU完整2Tv已按约定的一维范围验收，不能推广为塑性、复杂边界或大旋转验收。

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

2026-10-20进一步尝试8/4微秒：5 ms采样的1 s孔压半步最大差4.65046 Pa曾通过，但1 ms加密短窗在约.011 s发现9.66059 Pa差异，超过原5 Pa限值，因此拒绝该长窗候选，不放宽门。原5/2.5微秒基线的151对加密样本最大差3.79523 Pa/.00005326 mm，原门及原生0 ULP检查通过且已审图，现仅准入`tests/logs/k5_long5_r1.status.json`对应的新鲜15 s粗/半验证；完整2Tv仍未准入，正式XML/BAT未改。15 s两条预计合计约13–15小时，完成/失败自动回到同会话复核，普通PART不可精确续接HG。全宽细网格约三周、缩窄5微秒约9天的2Tv耗时只是短跑线性估计，原约4天估计不适用于该配置。详情与最新图表索引见`tests/notes/formal_release_r1.md`；原失败对比图`tests/figures/k5_failure_review_r1.png`保留。

根目录所有既有输入位置和历史`*_out`保持原位，包括网格细化、precision和double历史输出。更新前的两组正式XML/CPU BAT及本索引已另存`tests/outputs/formal_inputs_base_r1`；历史数据以各自`Run.out`、生成XML和版本记录确定来源，不能用当前更新后的根目录XML解释旧结果。

**本次更新的三组CPU/GPU BAT没有删除路径。旧k=1e-2等未更新历史BAT可能仍含覆盖确认或`-force`，不要用它们试跑或覆盖保留结果。临时验证仍放在`tests`分类目录。**

## 原位退役的精度试验

| 分组 | 状态及处理 |
|---|---|
| 根目录 `full_k1em4_precision` XML/BAT/out | 高低位孔压累计补偿的历史完整 2Tv 结果；已退役。BAT 禁止新计算，仅保留 `-postprocess` 后处理入口 |
| 根目录 `full_k1em4_double` XML/BAT/out | double 状态历史部分结果；停止于 Part84、15.303610 s、1,530,361 步，不是完整 2Tv |
| `tests` 中 `pore_double_stage1` / `pore_double_vel0` | 历史短程迁移和步长敏感性检查，不能证明完整固结精度提高；严格压力审查曾有未通过项 |
| `tests` 中 `upw_float_restore` | 当前 float 回退验收证据，保留为基线，不归为 double 退役输出 |

precision 完整结果仍有晚期孔压平台，详见 [对比报告](figures/precision_q0_k1em4_report.md)。double 未完成，不能据此宣称完整过程改善或有效加速。现有 double BAT 自带冻结程序/源码检查；当前 float 程序不满足它的运行条件。本次不修改该 BAT，也不把 double/补偿检查点交给 float 续算。

历史 [precision 运行说明](support/precision_q0_k1em4.md) 保留原文，其中“正式入口”等表述对应当时版本；当前状态以本索引为准。回退范围及验收见 [upw_float_restore.md](tests/notes/upw_float_restore.md)。

## 文件位置和依赖

- 根目录：正式 XML/BAT 和正式 `_out`；`figures`：正式图表；`support`：正式后处理及运行来源记录。沿用现有 `figures` 名称，不另外建立 `figure`。
- `tests`：临时配置、运行、日志、图和结论，见 [tests/README.md](tests/README.md)。
- `support/compare_double_q0.py`、`run_double_q0.py` 依赖 `tests/outputs/pore_double_vel0/reader/export_state.exe`、对应 build 日志及 `tests/outputs/pore_double_2tv/baseline_native`。这些支持链原位保留，不单独搬走。
- 历史自重迁移测试跨算例读取 01 的 `tests/outputs/CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out` 输入和 `CaseSWSt1_MLSDirect_GPU_out/data` 的 Part56。整理 01 时必须保留这些依赖。
- `tests/notes/upw_float_restore_before.zip`、`pore_double_stage1_baseline_sources.zip` 是历史源码/程序恢复档案，不是待清理的缓存。

今后的正式版本只有通过验收后才在根目录增加或更新对应 XML/BAT；测试文件不占根目录，原始输出和历史正式图不得被自动覆盖。

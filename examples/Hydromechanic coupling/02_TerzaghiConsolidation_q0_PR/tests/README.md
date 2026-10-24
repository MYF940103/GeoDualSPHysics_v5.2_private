# 02 测试文件索引

## 2026-10-24 CPU/GPU多面SPR有界候选（尚非正式通用边界验收）

- [补丁、失败来源与短窗结论](notes/spr_planes_r1.md)，[汇总收据](logs/spr_planes_review_r2.check.json)，[角点图](figures/spr_planes_review_r2_corner.png)、[算子/半步图](figures/spr_planes_review_r2_checks.png)及同前缀CSV。
- 三个CPU源文件实现每mk静止平面及角点MLS中心内移/原ghost求值；18多面制造场、18既有单面场及八条2-ms脉动半步对通过。既有一维SPR关/开短轨迹0 ULP，未改正式输入/数据。
- [GPU移植及源码位置](notes/spr_gpu_planes_r1.md)：18多面、36旧单面制造场，八个2-ms半步对和四条31帧旧路径0 ULP通过；当前Debug 3D棱边memcheck为0 errors。GPU脉动[PNG](figures/spr_gpu_delivery_r1_pulse.png)/[CSV](figures/spr_gpu_delivery_r1_pulse.csv)/[收据](logs/spr_gpu_delivery_r1.check.json)。
- 轴对齐NoPen+NoSlip/FreeSlip在CPU/GPU各两个脉动半步对通过。原NoPen在斜墙纯切向流下不旋转一致，未改其动量公式；斜NoPen、曲面/运动墙及有限墙端仍非已验收能力。当前GPU六个预期拒绝见`spr_gpu_scope_r1.check.json`。
- 当前八个源码/四个程序的本地快照`outputs/spr_planes_cpu_gpu_short_verified`，不是新云端Git备份。Yao CPU/GPU .1 s均通过数值/半步准入，case06新GPU .3 s检查加载后响应；不把制造场或启动短窗等同于二维理论/长程验收。正式三组数据不动；下方旧保护测试是扩展前基线。

## 2026-10-24 当前交付（以下旧日期状态仅作历史）

- 三组正式2Tv已按用户一维弹性验收范围通过：k=1e-3、1e-4、5e-5；全部dp=0.01 m、宽0.1 m。前两组GPU、xi=0.1，第三组CPU8、xi=0.05；不是只改变k的严格受控对比。
- 当前入口：[交付记录](notes/three_delivery_r1.md)、[第三组完整复核](logs/k5em5_hg05_full_cpu_r1.review.json)、[三组正式图](../figures/README.md)。三组图和CSV在case根figures，包含Tv=1.5/2；旧结果不覆盖。
- 第三组原始数据快照在`outputs/k5em5_uniform_2tv_verified_r1.zip`，880文件逐项校验，见`logs/k5em5_uniform_2tv_snapshot_r1.json`。这是本地同盘快照，不是云端原始数据备份，也不是HG重启文件。
- 复杂边界准入保护复核见`logs/spr_boundary_admission_final_r1.json`：36项实际CPU/GPU检查（20个一步对照、16个预期拒绝）通过；**不表示墙角、曲面、运动/旋转墙或NoPen已能开启SPR**。首轮曲面法向不完整记录保留，r2补齐内外两侧法向，不改源码。
- 目前没有长算或通知器需要重启。KEEP、密度/Darcy原型、细网格k1e-5和早期失败worker均退役；原数据/哈希/失败记录有依赖，原位保留。下一次试验不得启动这些旧入口。

整理日期：2026-10-08。本索引区分当前 float 回退基线和退役精度实验；不改历史数值记录，不迁移原始结果。

## 2026-10-18 GPU接续

- [G3设备沙漏](notes/gpu_g3_r1.md)的算子、五次真实20步及场量审图已通过，冻结为`outputs/gpu_g3_verified`。
- [GPU向量SPR/事件同步](notes/gpu_spr_r1.md)已完成生产代码移植：两个GPU配置各18组制造场、SPR关闭时HG开/关四组逐位回归、两配置各3318个CPU/GPU事件判断样本通过。
- Debug 0.03 s及Release 0.15 s粗/半步与CPU对照通过；GPU半步门为4.17837 Pa/0.0000934513 mm，三张短窗对比图已查看。新图为`figures/mdbc_gpu_vector_review_r1.png`及`figures/gpu_spr_015_*_review_r1.png`。15 s、完整CPU/GPU2Tv及独立计时、Git和三组正式计算仍待后续关卡。
- 短窗冻结在`outputs/gpu_spr_short_verified`（741文件）。独立3组交替计时为CPU单核25.60 s、GPU19.15 s，短程约1.336倍；非完整2Tv/大规模收益。
- 测试XML/BAT在`configs`，结果在`outputs/gpu_spr_*`，日志在`logs`，入口`support/gpu_coupled_run.py`。唯一15 s粗/半步序列已启动，实时读`logs/gpu_spr_15_r1.status.json`的`stage`和`logs/gpu_spr_15_c_r1.run.json`，终态自动接续同会话；不得重复启动旧worker。正式XML/BAT及既有正式输出保持原样。

## 2026-10-17 交付接续状态

- 用户已暂时接受现有一维孔压/沉降精度，继续合入、CPU效率、GPU同步、Git及三组正式计算；不重启旧KEEP或边界诊断序列。下方旧日期状态均保留作历史。
- CPU正式合入及15 s粗/半轨迹等价已通过，见`logs/hg_release_continue_r2.status.json`；固定事件的显示标记例外不涉及物理场。CPU固定平面全向量SPR的范围及验证见[记录](notes/mdbc_vector_r1.md)，不把制造场验收等同于通用二维/三维长程验收。
- [GPU G1](notes/gpu_g1_r1.md)：double应力状态链、设备算子及PART往返通过，冻结基线为`outputs/gpu_g1_verified`。
- [GPU G2](notes/gpu_g2_r1.md)：核支持带加载的旧模式0–4输出逐位回归及真实mode5三次20步生命周期/场对照通过，准入G3开发；跨后端近零raw的首轮`64 eps`失败和另行记录的来源/空间力差审查均保留。尚不是耦合长程验收。
- [GPU G3](notes/gpu_g3_r1.md)设备HG的Debug/Release各42项独立算子检查通过，正在接入真实短轨迹；G2冻结在`outputs/gpu_g2_verified`。SPR/固定事件同步、CPU/GPU耦合精度与计时、Git和三组正式2Tv仍按[发布计划](notes/hg_release_plan.md)继续。未改正式XML/BAT，勿据测试正常退出发布结果。

## 2026-10-12 当前执行顺序

- [完整验收与正式发布计划](notes/hg_release_plan.md)：本轮2Tv验收 → CPU沙漏效率优化 → GPU功能及完整周期对照 → 三组渗透系数正式2Tv → 归档清理。用户已授权按此顺序推进，物理验收失败时不得跳过关卡发布。
- `hg_merge_15_x01` 与 `hg_merge_15_half` 已通过15 s合并/半步长关卡，见 `logs/hg_merge_gate.check.json`。`hg_merge_2tv` 正在运行，实际状态只读 `logs/hg_merge_sequence.status.json`；既有完成通知器状态在 `logs/hg_merge_followup.status.json`，不重复启动或另建通知器。
- 当前生产CPU已合入应力double状态、应力率/旋转修正、归一化核支持带加载与弹性HG；孔压仍为float。GPU尚缺应力double状态、核支持带加载与HG。以下按日期保留的记录只描述当时状态，不代表当前代码仍未合并。

## 2026-10-12 沙漏 15 s 对照结果

- `hg_window_x01`（xi=0.1、dt=1e-5 s）已完成15 s，仅至Tv=0.4114；没有启动15 s半步长或2Tv。对照为相同顶部核支持带加载、应力率修正但无沙漏的保留轨迹；旧float/double单层加载结果只作背景。
- 同一14.6 s（Tv=0.4004）：平均孔压对经典解析误差从−4.5865%降至−0.1943%，初始材料层孔压剖面RMSE从146.72降至6.89 Pa；顶部材料点沉降对理想有限Kw参考误差从+4.5303%降至+0.5546%。15 s仍保留约+0.56%沉降误差，不能认为完全解决。
- 15 s横向最大周期位移从3.3373 mm降至0.00000404 mm；最大层均Cauchy总应力误差仅27.46→26.39 Pa，顶部两层应力差7.21→9.63 Pa，不能宣称所有应力指标改善。总应力指标不含HG附加相互作用力。
- [孔压多Tv剖面](figures/hg_window_compare_r1_pressure.png)、[历史对比](figures/hg_window_compare_r1_history.png)、[15 s沉降/应力剖面](figures/hg_window_compare_r1_mechanics.png)、[同刻数值表](figures/hg_window_compare_r1_comparison.csv)、[来源哈希及检查记录](logs/hg_window_compare_r1.check.json)。后处理入口：`support/hourglass_compare.py`；不运行求解器。绘图数据同前缀位于`figures`，原始输出不移动、不覆盖。
- 本次只新增后处理与上述图表记录并更新本索引；生产源码、正式XML/BAT未改。建议下一步同长度半步长检查通过后再考虑完整2Tv；不能用先前0.1 s半步长代替15 s验证。

## 2026-10-11 中期孔压排查

- [弹性 GNOG 沙漏试验](notes/hourglass_elastic.md)：冻结检查、关闭逐字节回归及xi=0.1的0.1 s短窗/半步长通过；xi=1、4因顶部应力失败。只准进入15 s风险窗口，不代表中期或2Tv验收。[短窗历史](figures/hg_soft_r2_history.png)、[应力剖面](figures/hg_soft_r2_stress.png)、[检查清单](logs/hg_soft_r2.check.json)。
- [空间算子候选筛选](notes/spatial_candidates.md)：功共轭一阶力、差分力、同权一次/二次重构的冻结对照；P2在压应力下改善双方向切线，但常应力/边界未通过，未启动候选短窗或长程。[候选图](figures/candidate_r2.png)、[真实几何图](figures/candidate_native_r1.png)。
- [横向伪应变的空间离散来源](notes/lateral_origin.md)：全 double 空间算子及 18 组 CPU 生产核零步对照确认，非仿射等体积剪切会产生伪体积源；没有合入修复或重启长程。[空间谱图](figures/lateral_r1.png)、[生产核对照图](figures/lateral_patch_r1.png)。
- [中期孔压偏差与横向交错](notes/pore_mid.md)：长程按用户要求停在报告时刻 55.8 s（约 1.531Tv），未完成 2Tv；保留全部结果，不再挂接通知器。
- [历史窗口](figures/pore_mid_r1_history.png)、[冻结算子](figures/pore_mid_r1_operator.png)、[0.1 s 短窗反事实](figures/pore_mid_r1_window.png)：支持横向伪应变造成额外耗散，强制一维运动仅作诊断，尚未形成可合入的通用修复。
- 本轮变更限于测试支持程序、构建/运行/审核入口和证据记录；生产源码、正式 XML/BAT 和旧结果未改。全部入口与目的见沙漏试验记录末节。下方 10-10 顺序入口与状态保留作历史，**不要据此重启旧长流程**。

## 2026-10-10 当前排查入口

- [顶部载荷/梯度修正及12 s长程准入](notes/traction_long.md)：四组合1 s及修复前半步长对照已完成，修复后半步长和修复前后12 s轨迹仍在检查；尚未放行完整2Tv。
- [应力旋转项符号修复](notes/rotation_r2.md)：CPU/GPU各六个J分量的局部修复、旋转解析验证及02/03/05短回归。没有新增沙漏控制；不能据此宣布晚期交错已解决。
- [1 s沉降和几何对照图](figures/traction_m1_history.png)、[剖面对照](figures/traction_m1_profiles.png)、[旋转反例修复前后](figures/rotation_r2.png)。
- [1 s半步长对照](figures/traction_h1_history.png)、[剩余沉降差分解](figures/traction_residual_r1.png)、[旧新版几何拉平判别](figures/background_flat.png)；方法和限制见上述长程记录及 [双方向记录](notes/mode_direction.md)。
- 本地顺序入口：`support/traction_sequence.ps1`；当前状态：`logs/traction_sequence.status.json`。12 s及修复后半dt满足预定准入条件才启动 `traction_2tv_r2_normalized_g1`，否则停止并留存原因；完整方法见长程记录末节。不得并发重复运行此入口。

本轮沿用的状态是CPU固体应力double、孔压/孔压率float；不要把下面历史“float回退”的记录误解为本轮又重新开展孔压double实验。脚本在 `support`，结果在 `outputs`，图在 `figures`，运行证据在 `logs`，不增加日期/轮次的深层目录。

## 浅层分类约定

| 位置 | 用途 |
|---|---|
| `tests/` | 主测试 BAT 和索引 |
| `configs/<试验族>/` | 测试 XML；既有非主入口 BAT 保留在配置组中 |
| `support/<试验族>/` | 必要辅助脚本/源码，小型单脚本可直接放 `support` |
| `outputs/<试验族>/` | 独立测试输出；不要再叠加多层 run/date/debug 目录 |
| `logs/<试验族>/` | 构建/运行日志及可核查的指标表 |
| `figures/<试验族>/` | 测试图、图源数据和自检图 |
| `notes/` | 结论、来源、清理记录及恢复档案 |

沿用 [已有布局约定](notes/test_artifact_layout_20260714.md)，每轮开始前确定名称及输入/输出位置。复制同类已有 XML/BAT 作最小修改，书写规范参考仓库 `doc/xml_format/_FmtXML_ElastoplasticSoil.xml`。根目录 `figures` 仅用于经确认的正式图件；试验图先放这里的 `figures`。

## 分组状态

| 分组 | 当前用途 |
|---|---|
| `upw_float_restore` | 2026-09-09 无补偿 float 回退的有效短程一致性证据，保留；不宣称解决孔压平台 |
| `formal_validation`、`gpu_validation`、`resolution`、`load_ramp` | 历史 PR 参数、后端、网格和加载比较，按各自 `notes` 判断结论；名称含 formal 也不自动升级为根目录正式发行版本 |
| `precision_k1em4_smoke`、`precision_k1em4_early`、`precision_selfcheck_20260908_*` | 退役高低位补偿的短测/抽查/后处理自检，不是当前 float 的新结果 |
| `pore_double_stage1` | 退役状态迁移测试；构建/结构检查与数值精度验收是不同结论，原严格压力审查有未通过项 |
| `pore_double_vel0` | 退役正式边界短程/事件采样对比，不能代替完整 2Tv 验证 |
| `pore_double_2tv` | 历史启动来源、原生读取和自检；完整计算被停止，不得标为已完成 |
| `pore_double_baseline` | 当时高低位补偿版本的冻结程序，不是无补偿 float 基线 |

`pore_double_*` 配置、支持脚本、日志、输出和既有正式图成组原位保留。历史脚本中的 `current` 指当时 double 版本，不能用今天的 `bin/windows` 程序重新解释；不要直接重跑旧脚本生成含混结果。根 precision BAT 已禁止新计算，double BAT 保留原有冻结版本检查。

## 不可拆开的依赖

- 根 `support/compare_double_q0.py`、`run_double_q0.py` 使用 `outputs/pore_double_vel0/reader/export_state.exe`、`logs/pore_double_vel0/reader.build.json`、`outputs/pore_double_2tv/baseline_native` 等路径。
- `support/pore_double_stage1/run_regression.py` 使用兄弟算例 01 的 MLSDirect 生成输入及 Stage1 Part56，还引用水土耦合公共目录 `validation/tpi_cleanup_release_20260906/compare_particle_fields.py`。
- `notes/upw_float_restore_before.zip` 和 `notes/pore_double_stage1_baseline_sources.zip` 保留；两者对应不同历史版本，不能混作原始 float。

关键结论入口：[float 回退](notes/upw_float_restore.md)、[double 阶段 1](notes/pore_double_stage1_acceptance.md)、[Vel0 短测](notes/pore_double_vel0_acceptance.md)。旧记录中的下一步建议仅代表当时计划，后续回退状态以根 [README](../README.md) 为准。

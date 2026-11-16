# C08 当前排查与数据索引

更新：2026-11-16。当前使用 Wendland Kernel2、hdp1.8、dp=.04、5us；释放候选为AS.3/n2.55、私有塑性HG。以下状态以各真实收据为准，正常求解/native/HG检查通过不等于论文物理精度验收。

| 数据或阶段 | 当前状态 | 主要记录／位置 |
|---|---|---|
| ψ0，C-quality修复+塑性HG，3s | 已完成原生/HG/全程图CSV及Fluid/Bound。翻转显著改善，但局部负压脉冲与早停仍记录，未物理验收 | [结果](notes/c08_h18_wall_c_retry_full3_outcome_r1.md)，outputs/c08_h18_wall_c_retry_full3_GPU_r2 |
| ψ+2.5°，独立同材料10s源 | 唯一native_r2及近静止审查通过，可作有限撤墙比较；压力尾段仍缓慢变化，不宣称精确平衡 | logs/c08_h18_wend_psi2p5_source_root_review_r1.json |
| ψ+2.5°，塑性HG，3s | 已完成301帧/22数组/HG602记录和图CSV、Fluid/Bound。无明显近对/翻转，但前缘只前进17.2mm，论文精度未通过 | [结果](notes/c08_h18_hg_psi2p5_outcome_r1.md)，[论文对照](figures/c08_h18_hg_psi2p5_paper_board_r1_fig16.png) |
| ψ−5°，同材料10s源 | 当前唯一GPU物理运行；coh7500、ψ−5、sf.2，尚非源资格/平衡或collapse验收 | outputs/c08_h18_wend_branches_psim5_pre_r1；同标签logs/start/owner_admission/status/run（终态后） |
| ψ+2.5° HG/cache-OFF .30s | 仅配置/31帧计划与离线读取器已准备；未启动。OFF同时切换缓存材料路径，不是纯HG力唯一差异 | [限定及下一步](notes/c08_h18_psi2p5_next_diagnosis_r1.md)，logs/c08_h18_psi2p5_hg0_w03_r1.prepare.json |
| 压力与FS审计 | Eq19、有限Kw基础解析验证可复用。Eq47是TPI修正；p<=0与纸文一致。旧normal-Taylor候选实际窗未改善，未采用 | [压力/边界](notes/c08_h18_psi2p5_pressure_bc_audit_r1.md)，[实际FS闭合](notes/c08_h18_psi2p5_fs_closure_scope_r1.md) |

## 数据保留和清理

本轮可恢复清理已完成：83个无依赖绑定的旧ILK缓存经ZIP归档、完整CRC/长度验证后删除，扣除恢复包后的文件流占用净减少2,621,927,424 B（约2.62 GB，不计小型清单，非精确卷空闲增量）。[结果与恢复说明](notes/c08_cache_cleanup_outcome_r1.md)，[独立检查](logs/c08_cache_cleanup_r2.final_review.json)。8个已绑定及146个证据不足缓存保留。原始BI4/NBI4、typed22/真实clock/signed、PRE/重启链、程序/PDB/对象/源码归档、正式输入输出、图和CSV及全部Fluid/Bound VTK保持保护。活动ψ−5计算及全部依赖未更改。

旧构建的ILK仅在无引用/已关闭/不属于活动或快照目录且实际白名单通过后，先ZIP归档、验证CRC及长度再删除原文件；恢复方法与清单另记。不改写历史通过/失败收据，不把本次清理记作数值验收。活动ψ−5程序和全部依赖保持原状。

## 历史排查索引（截至2026-11-09，以下“当前／活动”属于历史记录）

更新：2026-11-09。当前按用户要求比较 Cubic h/dp=1.8、人工应力系数 .3/.5/.7，选型后完成三组 ψ 的正式 3 s 计算。原 `c08_h18_pre_r2` 最后保存 .620005 s 后被弹性源资格拒绝，partial 已独立解码与成图；当前活动源为 `c08_h18_bedroles_pre_r1`，仅统一右下 5 点从预载开始的床归属，粒子坐标及材料不变。仍用 5 μs、阻尼 .03、Shepard40，从零预载至 10 s，源码及程序不变。完成原生状态和平衡趋势审查后才进入撤墙比较。根目录 ψ0/r6 的旧 3 s 结果仍为保留诊断结果。原 r2 GPU 10 s PRE 和旧失败保留；其他两组 ψ 尚未启动。

| 检查或候选 | 当前结论 | 记录 |
|---|---|---|
| h/dp=1.8、ε=.3/.5/.7 | 新 bed-last 10 s PRE 运行中；旧角点 PRE 最后保存 .620005 s 后拒绝。旧 keep5 矩阵尚未运行，新几何须相应适配。共用指数 3.825，必要时再比较 3/5；不能把过早停滞当改善 | [本轮计划](notes/c08_h18_plan_r1.md)、[失败与角点比较](notes/c08_h18_pre_decision_r1.md)、[活动预载](notes/c08_h18_bedroles_pre_r1.md) |
| 原人工应力、W(dp) 与指数实现 | 未找到遗漏；晚期近粒子对并非全由持续张力吸引驱动 | [粒子对诊断](notes/upl_c08_pair_mechanism_decision_r1.md) |
| ε=.5/n2.55 与 ε=.2/n4 | 前者延迟首次团聚但明显过早停滞；后者未延迟首次团聚，并在 .66 s 后触发必要孔压步长保护 | [早期比较](notes/upl_c08_early_as_decision_r1.md) |
| h/dp=1.5 | 新预载约 .51 s 触发原弹性源保护；没有合格的 h1.5 撤墙状态 | [预载审查](notes/upl_c08_hdp_preload_review_r1.md) |
| 撤墙后保留 Shepard | 未达到修复要求 | [加速度与滤波审计](notes/upl_c08_darcy_acceleration_audit_r1.md) |
| Darcy 分母去除正则项 | .90 s 负孔压极值、压力 RMS 和应力 RMS 均恶化，不采纳 | [Eta0 结论](notes/upl_c08_darcy_eta0_decision_r1.md) |
| PRE 继承与真实 n3 状态扰动 | 导入应力位于新屈服面内；已采样速度方向及 41 自由度压力子块未显示正增长模态，不代表全系统稳定性证明 | [响应审查](notes/upl_c08_velocity_pressure_review_r1.md) |
| ε=.25/n3，.30 s | 窗口负压极值和最小间距改善，但末态近粒子对 25→28；尚不能采纳为修复 | [AS025 结论](notes/upl_c08_as025_decision_r1.md) |
| 完整邻域 CPU 力分量 | AS 和 AV 都在减缓首个团聚对的闭合；六次冻结状态评估不是轨迹预测或 GPU 逐位复现 | [力分量结论](notes/upl_c08_pair_force_decision_r1.md) |
| 撤墙后 AV=.15，.30 s | 首次近对 .15→.16 s、窗口最小间距改善，但末态近对 25→26、窗口最低孔压略差；不作为修复采纳 | [AV15 结论](notes/upl_c08_av15_decision_r1.md) |
| 首团聚点 output-only，.30 s | 全30帧22数组/时间/signed前缀无反馈；三点全120000步自身平面命中为0，启动负压早于自身cap；材料/孔压时序已成图 | [首对观测结论](notes/upl_c08_pairtrace_review_r1.md) |
| 实际梯度与局部拟合 | 首近对闭合明显强于邻域梯度；支撑土粒较少且残差局部反向，尚非沙漏因果证明 | [梯度与通量结论](notes/upl_c08_gradient_flux_decision_r1.md) |
| 变k成对通量影子 | 当前率重构、常压零场和常k退化通过；制造场无一致改善，不合入正式算子 | [梯度与通量结论](notes/upl_c08_gradient_flux_decision_r1.md) |
| Cubic残差恢复率影子 | 首对恢复方向、冻结图功率/净力/力矩及仿射零场检查通过；没有施加到轨迹 | [残差候选结论](notes/upl_c08_residual_visc_decision_r1.md) |
| 残差黏性CPU零步/GPU数学组件 | CPU OFF 210264字段0ULP；ON实际Darcy响应已审；GPU八组数学及memcheck通过 | [残差候选结论](notes/upl_c08_residual_visc_decision_r1.md) |
| 私有GPU主循环候选 | 三构建、关闭逐字节回归、Debug2ms memcheck及原生门通过；Release .30s/30帧已完成并解码审查一次。首近对.15→.17s、窗口极值改善，但.30s近对25→26且局部压力/应力恶化，尚非修复 | [实际短窗结论](notes/upl_c08_rvisc_decision_r1.md) |
| Lian表1的alpha=.5 | 确认为TPI Eq39系数，不是AV；当前Visco=.1仅线性AV，参考二次项/声速存在定义差异，未证明为团聚原因，本轮未改动 | [参数审计](notes/upl_c08_av_parameter_audit_r1.md) |
| Bui2008人工应力epsilon=.5 | 原文明确推荐Cubic h/dp1.2、n2.55、epsilon.5，当前C08也是同核同比例；既有单epsilon .66s对照改善间距但负孔压与过早停止加重，不能仅凭末态0近对验收 | [原文与既有对照审计](notes/upl_c08_bui_as_audit_r1.md) |
| 残差黏性延长窗口 .90s | 实际失败，最后保存.53s；同时间孔压RMS10.64→104.12kPa、近对47→156，不采纳。53帧原门及原30帧完整字节前缀通过；三张图和匹配CSV已审阅，fields使用显式真实刻度r2图 | [失败与部分结果结论](notes/upl_c08_rvisc90_decision_r1.md) |
| 失败前冻结状态的六次力/Darcy | 原控制310536字段完全相同。新力经加速度通道显著改变压力率，但响应随状态改变：原.52状态max rate 1.224→30.527MPa/s，候选.52状态201.594→24.938MPa/s。零积分，不等于失稳根因已确定 | [RHS定位与下一项取舍](notes/upl_c08_rvisc_failure_rhs_decision_r1.md) |

上一轮已结束：`upl_c08_rvisc90_GPU_r1` 已失败并保留，真实工具/求解器退出均为1，目标.90s没有完成。最后完整保存为Part0052/global4212000，真实tau=.53000000016822923s；后续未保存状态在step4212949触发原孔压必要步长保护，不能重构其物理状态或精确故障时刻。一次专用partial读取已核53帧6805IDs/22数组及原始账本、排水、几何和signed时钟门；前30帧全部数组/真实time/layout/signed逐字节等于原.30s结果，53/30原始头未改写。侧车仅106行Pre/Cor保存记录，不是180行或完整360000更新。已有保存态出现局部压力、J和速度显著恶化，候选不作为稳定性修复、不合入正式源码；53帧离线审查及六次冻结RHS检查已完成。后续优先级已由用户调整为上表 h1.8 参数比较；该试验不启用残差黏性。AS025旧.90s准备继续保留且不启动。

配置在 configs，原始和解码输出在 outputs，图与匹配 CSV 在 figures，调用及检查收据在 logs，结论在 notes，再生工具在 support。不覆盖正式 XML/BAT、PRE、失败记录或旧结果。Git 保存输入、工具、结论及必要图表；BI4、typed 二进制和执行程序仍由本地保留，不称为云端备份。

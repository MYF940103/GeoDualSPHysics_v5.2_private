# C08 当前排查索引

更新：2026-11-09。当前主要排查 ψ=0° 的粒子团聚和过早停滞。根目录 ψ0/r6 的 3 s 结果是保留的诊断结果，尚未通过论文精度验收。原 r2 GPU 10 s PRE 保留不变；其他两组 ψ 尚未准入。

| 检查或候选 | 当前结论 | 记录 |
|---|---|---|
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
| 私有GPU主循环候选 | Debug/Release/alpha0三构建通过；alpha0首帧全22/布局/真实时钟/signed与保留causal90逐字节一致；Debug 2ms实际memcheck正在运行，尚未物理验收 | [集成审查](notes/upl_c08_rvisc_root_review_r1.md) |

当前：首对观测、梯度/局部拟合、成对通量、Cubic恢复率及残差黏性零步检查已完成。私有GPU集成已构建、关闭回归已通过，正在做开启候选的2ms Debug/memcheck，不修改正式源码或输入。α=.1的新增机械耗散与原AV量级相当，真实压力率也明显变化；仍须新的短窗观察压力、团聚和提前停滞，不能凭负机械功验收。没有新的长程物理计算。AS025 的 .90 s 准备文件仅保留，未准入、未运行；其他 ψ 尚未准入。

配置在 configs，原始和解码输出在 outputs，图与匹配 CSV 在 figures，调用及检查收据在 logs，结论在 notes，再生工具在 support。不覆盖正式 XML/BAT、PRE、失败记录或旧结果。Git 保存输入、工具、结论及必要图表；BI4、typed 二进制和执行程序仍由本地保留，不称为云端备份。

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

下一项：原 PRE 和 XML 粘性系数 .10 保持不变，私有程序仅在成功撤墙后改用 AV=.15；AS 保持 ε=.2/n3。CPU Debug 与 GPU Release 已构建，先做 80 更新、两帧 CPU 启动/原生检查，再决定一次 .30 s GPU 窗口。[构建说明](notes/upl_c08_av15_release_r1.md)，[窗口说明](notes/upl_c08_av15_window_r1.md)。AS025 的 .90 s 准备文件仅保留，未准入、未运行。

配置在 configs，原始和解码输出在 outputs，图与匹配 CSV 在 figures，调用及检查收据在 logs，结论在 notes，再生工具在 support。不覆盖正式 XML/BAT、PRE、失败记录或旧结果。Git 保存输入、工具、结论及必要图表；BI4、typed 二进制和执行程序仍由本地保留，不称为云端备份。

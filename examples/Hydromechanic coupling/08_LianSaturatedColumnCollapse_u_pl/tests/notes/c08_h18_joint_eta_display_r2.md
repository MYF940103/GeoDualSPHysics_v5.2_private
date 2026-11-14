# C08四权重图：仅刻度与布局修订r2

作者仅新增同名support脚本及本文；没有import、执行、重做分析/数字化、读取240000条本地body、solver/native/组件/构建/Git/SHA或改旧记录。根全文审阅后才能单次执行，物理结论与原数据不变。

唯一数据输入为已通过 `logs/c08_h18_joint_eta_shadow_r1.check.json` 中files绑定的144行 `figures/c08_h18_joint_eta_shadow_r1_metrics.csv`。脚本要求原passed/analysis_complete、12组和144行，保留同2parts×3fields×2oracles×3cohorts×4weights完整键与原始数值；不重新计算rate、delta、RMS、cohort或误差预算。原两PNG也以其原check.files绑定，始末stat保护，没有重新封存替代历史证据。

重绘仍为3x3 rates和3x2 deltas：

- H使用线性轴，MaxNLocator提供可读十进制刻度并明确显示零；不再让窄symlog区间产生无刻度/只有端点的图。
- N/X使用symlog（linthresh=1Pa/s），显式0、正/负十进制幂刻度；RMS轴从0起，signed delta对称范围，不删零、不裁剪负均值。
- 所有纵轴保留Pa/s；rates四曲线、deltas三weight的signedmean和RMS完全复用原CSV。H轴与N/X变换不同而单位相同，不能按跨panel线条坡度比较效果。
- 使用明确画布边距、独立上下标题/图例/脚注空间；保存到新PNG，原r1图与检查不覆盖。视觉QA留根实际目检，脚本完成不自动声称排版或物理通过。

新目标为 `figures/c08_h18_joint_eta_display_r2_rates.png`、`_deltas.png` 和 `logs/c08_h18_joint_eta_display_r2.check.json`，均fresh拒绝覆盖。失败只保留新派生与首因，不重跑原分析或物理程序。没有新增CSV。

根独立准入后的唯一命令：

`D:/anaconda3/python.exe -B tests/support/c08_h18_joint_eta_display_r2.py --execution-authorized`

这是显示修订，不改变原全域X非兼容IBVP、原5us/原算术门、去Eta/receiver-C仅条件shadow及其他psi未准入等限定。

# C08 HG history r2：只调整已封存CSV的绘图排版

本脚本为AUTHOR ONLY，根线程全读后才可用 `--execution-authorized` 单独运行。它不复算HG、能量、预算、原生prefix或物理指标；不启动solver/reader/构建/Git，不计算SHA，不改原图、原check或CSV。

输入仅为已通过的 `c08_h18_wall_c_retry_full3_hg_review_r1.check.json` 及其封存 `_phases.csv`、`_extrema.csv`，按原收据stat绑定并在绘图后再次确认。保留原9组全部Pre/Cor series、原实际tau、线型及两条参考线；空诊断比仍作为空值绘制，不替换为零。extrema仅读取用于确认输入存在，不据其重新计算或挑选数据。

唯一变化是9个短英文标题、短legend、轴单位，以及18×15英寸的较高画布/constrained layout，避免右下标题越界。力与能量单位沿原二维单位宽度量纲标注，不做数值换算。新文件为 `figures/c08_h18_wall_c_retry_full3_hg_visual_r2.png` 和同tag的新 `logs/*.check.json`；任何既有目标都禁止覆盖。根线程还须实际查看新PNG，脚本本身不声称视觉QA通过。

原实现/能量审查结论全部由原check提供，本次只绘图；不增加物理、论文、coupled-energy或独立旧material solve验收结论。所有原source/runtime/typed/native结果保持原状。

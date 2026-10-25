# 根目录五组旧输出退役归档

2026-10-25，用户确认按分类整理；基线b18fd84。目的为根目录整洁，不将旧结果冒充当前正式验证。生产源码、方程、VS工程不改。

## 本轮精确范围

以下五个直接位于case根目录的输出，先完整写入tests/outputs/root_legacy_r1.zip，逐文件解压核对SHA-256后才移除原目录：

- CaseTerzaghiConsolidation_q0_PR_full_k1em2_out：旧k=1e-2结果。
- CaseTerzaghiConsolidation_q0_PR_full_k1em3_out：旧k=1e-3结果，不是当前release_GPU结果。
- CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp0005_dt2em6_out：旧网格对照，目录名／内部生成名原样保留，不按名字改写当时dt。
- CaseTerzaghiConsolidation_q0_PR_full_k1em4_precision_out：已退役的孔压高低位补偿完整结果。
- CaseTerzaghiConsolidation_q0_PR_full_k1em4_double_out：已退役的孔压double部分计算，不是完整2Tv。

CaseTerzaghiConsolidation_q0_PR_full_k1em4_out保留原位，是平台修复前的float应力基线，多个历史算子／回归／对照脚本仍直接引用。所有带release的正式或部分输出不在本轮范围；当前三组正式XML和CPU/GPU BAT不动。图、图表CSV、原始分析和历史哈希记录不改。

## 旧XML和BAT

旧k1em2、precision、double三份XML留在根目录，不改字节。make_stage1_q0_tests.py／make_stage2_q0_tests.py及旧double来源检查仍引用它们，直接移动会打断依赖。它们属于退役输入，不是当前正式三组；本轮将其快照纳入ZIP的retired_inputs子目录。

对应三个CPU BAT此前已原样移到tests/outputs/retired_root_inputs_r1，本轮不重复移动或改写；ZIP也包含其副本。归档BAT的相对路径仍按原case根设计，不要在归档目录双击，更不能让当前float孔压程序续算旧double检查点。当前孔压仍float、持久应力double；旧孔压double试验不是当前应力精度修正。

## 恢复与依赖

ZIP内五个输出的顶层文件夹名与原case根目录相同。需要重查旧precision／double／旧网格分析时，将所需的整个文件夹从ZIP解压回case根，禁止覆盖已有同名结果；随后可用archive.json中的逐文件SHA核对。只解压希望查看的文件夹，不必恢复全部。retired_inputs仅是输入和整理前README快照，不能覆盖当前正式XML/BAT。

旧分析脚本、历史清单保持原路径／原哈希，不在本轮重写为新路径。因此未恢复时，涉及这五组的旧分析会报告原路径缺失；这是归档状态，不是求解失败。旧full_k1em4_out及当前正式后处理链仍可原位使用。不能把普通PART恢复当作精确HG历史重启。

ZIP完整解压流SHA校验覆盖全部原始输出文件和输入快照；归档是标准ZIP，可用资源管理器打开。原目录移除不经回收站，恢复来源是该ZIP。ZIP只在本地，Git保存清单／工具／说明，不表示原始数据已有云备份。

## 修改位置

- tests/support/root_retire_r1.ps1：精确五组归档、逐成员SHA校验、移除前重验源文件，以及受保护基线／XML／BAT检查。
- tests/outputs/root_legacy_r1.zip：上述完整旧结果、旧输入／BAT及整理前README快照。
- tests/logs/root_retire_r1.archive.json、status.json：实际成员、路径、哈希、移除结果，不能把计划当完成。
- 根README和tests/README：当前正式入口／退役输出／依赖与恢复路径。
- tests/.gitignore：仅追加本地大ZIP的精确忽略项。

根README整理前已有未提交的边界说明，本轮原文保留，仅将本次新增归档说明加入提交，不顺带提交该旧差异。生产代码不改；默认CPU Debug收尾构建，日志在tests/logs。最终结果和Git节点见root_retire_r1.final.json、root_retire_r1.git_complete.json。

## 完成结果

五个原目录共3889个输出文件、390159009字节，已从根目录移除；ZIP包含这3889项及7份输入／BAT／README快照，共3896个文件成员，另保留目录条目。全部成员完整解压流SHA-256与原文件一致；移除前再次核验原文件，未放宽校验。

ZIP大小187283817字节（178.61 MiB），相对五个原目录净减少202875192字节（193.48 MiB）。这次主要是根目录整理，不是大规模空间释放。归档SHA-256为E523D7074661C72FFCE54EF8BAE8EDB3A4C91C68109A3AF1C0F75D50191C17ED。

1239个受保护文件（旧full_k1em4_out完整基线和根XML/BAT）前后SHA逐项不变；全部release目录不在删除名单。默认CPU Debug构建通过，增量构建无错误或警告。三个旧XML和已有退役BAT原样保留，不增加可误点的旧计算入口。

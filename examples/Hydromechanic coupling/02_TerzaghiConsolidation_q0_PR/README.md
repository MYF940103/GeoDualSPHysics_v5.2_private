# 02 外载 1D 固结：入口与文件索引

整理日期：2026-10-08。当前求解器采用无孔压精度补偿的 float u-pw PR。高低位补偿和 double 孔压状态已于 2026-09-09 回退；此次不修改物理配置，也不恢复旧精度模型。

## 当前正式入口

| 渗透系数 | 根目录 XML | 根目录 CPU BAT |
|---|---|---|
| k=1e-4 m/s | `CaseTerzaghiConsolidation_q0_PR_full_k1em4_Def.xml` | `xCaseTerzaghiConsolidation_q0_PR_full_k1em4_win64_CPU.bat` |
| k=1e-3 m/s | `CaseTerzaghiConsolidation_q0_PR_full_k1em3_Def.xml` | `xCaseTerzaghiConsolidation_q0_PR_full_k1em3_win64_CPU.bat` |
| k=1e-2 m/s | `CaseTerzaghiConsolidation_q0_PR_full_k1em2_Def.xml` | `xCaseTerzaghiConsolidation_q0_PR_full_k1em2_win64_CPU.bat` |

根目录所有既有 XML/BAT 和 `_out` 保持原位，包括网格细化、precision 和 double 历史输出。历史结果以各自 `Run.out`、生成 XML 和版本记录确定来源；当前程序不能自动代表旧计算版本。

**重跑前注意：既有 float BAT 的覆盖确认或 `-force` 可以删除同名输出。不要用正式入口试跑，也不要覆盖已保留的正式结果。新验证使用 `tests` 下独立输入和输出。**

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

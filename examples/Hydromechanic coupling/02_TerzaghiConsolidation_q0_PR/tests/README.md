# 02 测试文件索引

整理日期：2026-10-08。本索引区分当前 float 回退基线和退役精度实验；不改历史数值记录，不迁移原始结果。

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

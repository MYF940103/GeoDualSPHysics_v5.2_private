# Cryer 正式入口统一命名 · 2026-11-28

四组正式结果均为 u-pw + symC。每组根目录的 XML、GPU BAT 和 `_out` 使用同一个主名。只改外层结果目录名，原生状态、求解日志、生成时的内部文件名及正式图表均保留。四份 XML 的内容与改名前一致。根目录另外保留公共显式 u-pl 和公共 TPI 两个入口，见[速查表](../../README.md#配置与结果速查)。

| 原主名 | 统一主名 |
| --- | --- |
| `CaseCryerProblem_PR_release_nu010_r1` | `CaseCryerProblem_u_pw_symc_nu010` |
| `CaseCryerProblem_PR_release_nu020_r1` | `CaseCryerProblem_u_pw_symc_nu020` |
| `CaseCryerProblem_PR_symc_nu030` | `CaseCryerProblem_u_pw_symc_nu030` |
| `CaseCryerProblem_PR_release_nu045_r1` | `CaseCryerProblem_u_pw_symc_nu045` |

正式 BAT 通过冻结清单读取原封存 ZIP 和成员名。以后在新副本运行时，冻结入口完成后将实际输出放到统一命名的根目录 `_out`。已存在的输出受保护。分析脚本从统一命名的外层目录读取原成员。迁移期间未启动任何求解器。

退役的 u-pw r2 复现版、冻结显式 u-pl r1、冻结 TPI/P3 峰窗和全程共四对 XML/BAT 迁入 `tests/configs/retired_frozen_20261128/`，原 P3 说明随同归档。三份配套 ZIP 和校验单迁入 `tests/outputs/retired_frozen_20261128/`。已有的显式 u-pl 和 P3 峰窗原生数据保留在其测试输出目录，供既有比较和公共 TPI 打包校验使用。

退役的外层 BAT 使用迁移前的根目录布局。复核历史入口时使用提交 `66dc3e2` 的独立副本，按原 `support/server_packages/` 路径放置归档包。已封存的一次性核验仍按原始路径和原始版本解读。

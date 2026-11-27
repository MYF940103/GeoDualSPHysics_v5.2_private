# Cryer 配置、结果与服务器包整理 · 2026-11-28

[根目录速查表](../../README.md#配置与结果速查)按方法、泊松比、XML、BAT 和实际结果逐一配对。四组正式约 1 Tv 的结果均为 u-pw + symC，已核对输入中的 `HydroMechModel=0`、`PoreDarcySymmetricCorr=1` 以及各组 `Run.out` 中的 `SymmetricSoilPair`。显式 u-pl 的记录为单独的 ν=0.30 峰窗。物理与方法对比见[峰窗审查](upl_cryer_freebody_peak_root_r1.md)。

## 路径调整

| 原根目录项目 | 现位置 | 组成 |
| --- | --- | --- |
| 五个 Windows 服务器 ZIP | `support/server_packages/` | `Cryer_release_nu010_020_045_r1_…`、`Cryer_release_r2_…`、`Cryer_symC_nu030_…`、`Cryer_upl_nu030_…` 和 `Cryer_TPI_P3_nu030_…`，以及已有四份校验单 |
| 加入 symC 前的 BAT、XML 与原生输出 | `olddata/` | 原粒距四组、`dp002_rampclosed` 四组，共九个 BAT、八个 Def.xml 和八个 `_out`。九个 BAT 来自上一轮 `tests/configs/retired_root_20261128/` 归档。 |
| 六月短测和视频 | `olddata/` | `CaseCryerProblem_PR_afterfix_short_out/` 和 `videos/` |
| 六月加密与参数试验 | `olddata/refinement/` | 原 `refinement/` 目录，包括其说明、输入和输出 |
| 三轮 TPI/P3 服务器峰窗 | `tests/outputs/` | `CaseCryer_TPI_P3_nu030_peak_r1_GPU_out/`，含原内层同名目录 |

共移出 29 个根目录条目，并将上轮已归档的九个 BAT 并入 `olddata/`。每项保留原名和相对内部布局。移动后核对原根路径不存在且归档路径存在。ZIP 内容及封存 SHA 仍与原件绑定。此为同卷归档，无永久删除和磁盘空间回收。

仍可从根目录直接使用正式 XML 和 BAT。冻结入口的清单改为指向 `support/server_packages/`，包内启动方式仍按各自的原始说明。六月绘图和分析脚本改用 `olddata/`。旧六月 BAT 保留原有相对路径和已有输出删除菜单，如需复现，先在单独的复现副本中把 BAT 和对应 XML 恢复到 case 根目录。过去归档的 `support.zip` 和孤立校验单见[上一次归档记录](cryer_root_retirement_20261128.md)。旧一次性清理工具及其记录保持历史路径，此次未再次运行。

四组正式 u-pw 原生结果、正式图和 CSV 在原来的位置。Git 记录入口索引、路径变更、八份旧输入和已有校验单。原生数据、视频和服务器 ZIP 依旧是本地归档资产。

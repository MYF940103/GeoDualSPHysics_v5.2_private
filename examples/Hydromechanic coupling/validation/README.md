# 水土耦合验证与整理记录

本目录保存跨 case 的回归和文件整理证据。新的算例测试应放回所属编号 case 的 `tests/`，按上级 [文件约定](../AGENTS.md) 管理。

## 当前位置（2026-10-08）

- [tpi_cleanup_release_20260906](tpi_cleanup_release_20260906/README.md)：早期 TPI 临时代码清理后的 u-pw 回归证据，原位保留。不是当前版本的新 TPI 验收。
- 原 `u_pl_stage_ab_20260907`、`u_pl_time_accuracy_perf_20260907` 等 u-pl 试验已在后续回退时归档至 [00_upl_records](../00_upl_records/测试记录归档说明.md)，不再是本目录内可直接运行的工程。记录 ZIP 为 `upl_test_records_20260908_r1.zip`，按 `stage_ab / time_accuracy / cde / followup / fix / precision` 分组；内容范围与限制以该目录归档说明及 manifest 为准。
- [cleanup_20261008.json](cleanup_20261008.json)：前一轮清理清单，17 个可重建缓存和 72 个已逐文件核对的重复 VTK 移入回收站。
- [organization_20261008.json](organization_20261008.json)：本轮 Git/数据备份、正式输入输出保护检查及测试派生文件整理结果。

## 历史迁移证据（2026-09-07，不是当前目录清单）

当时从仓库根 `validation/` 迁入以下三个目录；其后 u-pl 材料又经历归档。保留原迁移清单，不能用旧清单推断文件仍在旧位置。

| 当时目录 | 当时文件数 | 当时总字节数 |
|---|---:|---:|
| `tpi_cleanup_release_20260906` | 503 | 87200800 |
| `u_pl_stage_ab_20260907` | 1352 | 159659614 |
| `u_pl_time_accuracy_perf_20260907` | 484 | 129396903 |

- [迁移前清单](migration_20260907_before.json)：2339 个文件的相对路径、字节数、SHA256 和旧/新根路径。
- [纯移动核验](migration_20260907_move_verified.json)：当次移动后、适配脚本前的文件哈希和目录树核验。
- [最终适配核验](migration_20260907_final_verified.json)：当次脚本/README 路径适配后的核验。
- [运行时重定位助手](relocated_evidence.py)：保留的旧迁移辅助方法；映射路径并不保证后续已归档/删除的原始粒子数据仍存在，也不会把旧结果变成当前版本验收。

历史 JSON、日志和 Markdown 内的命令、时间戳、源码/程序/数据哈希、旧路径保留原文。不要批量替换这些字段。旧生成源码副本不能与当前生产头文件/对象混用并声称复现原试验；历史版本检查拒绝当前程序时，不应改写历史哈希绕过它。

Git 忽略的程序、原生 BI4/VTK 和大文件需另行备份。本地存在不代表已经上传远端。2026-10-08 整理前的小文件检查点为 `d2c15a3`；后续整理记录与原始数值证据分开保存。

# Cryer 六月历史 VTK 整理

2026-11-27 只整理八组已经结束的六月根目录输出。删除对象为直接位于各组 particles 下的旧 Fluid VTK。完整 BI4、运行日志、输入、曲线、表格、短时启动诊断和 refinement 保留原位。当前四组正式 u-pw、公共 TPI、weak-full 服务器包也保留。

从八组原生 BI4 各选初始、峰值附近、末期三帧，使用仓库 PartVTK 按旧字段重导，24 帧均和原 VTK 逐字节一致。每组保留 6 个原位 VTK，即初始两帧、峰值附近三个连续帧、最后一帧。复现整条历史曲线时可直接用现有全量 CSV。粒子空间场由对应 BI4 重新导出。[重导核验](../logs/cryer_june_vtk_reexport_20261127.check.json) · [范围和数量](../logs/cryer_june_vtk_cleanup_20261127.check.json)

| 范围 | 数量 |
|---|---:|
| 保留原位 BI4 数据帧 | 8,021 |
| 保留原位代表 Fluid VTK | 48 |
| 已清理旧 Fluid VTK | 7,973 |

逐文件记录在本地 `tests/logs/cryer_june_vtk_cleanup_20261127.removed.jsonl`。八组的旧 VTK 在 11 月 3 日已压缩。本次实际路径和长度、修改时间与当时压缩清单核对；文件级空间按当时记录的压缩占用计量。按历史逐文件记录，已删文件的压缩占用合计 40,631,730,176 B。D 盘可用空间在清理前后分别为 56,793,878,528 B 和 97,415,688,192 B。卷空闲量变化与持续计算及其他写入并行。

## 从原生帧恢复

以下从 C04 根目录运行，将重导结果放在空的新目录。选择对应的根案例目录。需要部分帧时附加 `-files:0,49,1000` 等实际编号。全量旧脚本重画前，恢复它所读的整组 VTK，并沿用该次旧计算的几何、加载排水时钟和孔压采样设置。

```powershell
$family = 'CaseCryerProblem_PR_out'
$converter = '..\..\..\bin\windows\PartVTK_win64.exe'
$destination = 'tests\outputs\cryer_june_vtk_restored'
if (Test-Path -LiteralPath $destination) { throw "Choose a fresh destination" }
New-Item -ItemType Directory -Path $destination
$variables = '-vars:-all,+idp,+vel,+rhop,+press,+type,+mk,+excessporepress,+fsnormal,+fstype,+hydromechloadace,+kplastic,+porepress,+porepress0,+sigma_ij,+sigma_kk'
& $converter -dirin "$family\data" -savevtk "$destination\PartFluid" '-onlytype:-all,fluid' $variables
```

旧六月根诊断仍依赖原生 Part，例如载荷和实际积分时钟审核会直接读取 `CaseCryerProblem_PR_out/data`。初始密集试验有常规帧中缺失的瞬态证据，继续保留。[载荷历史](cryer_load_pair_r1.md) · [实际积分时钟](cryer_dt_history_r1.md) · [初始密集试验](../../refinement/notes/k1e5_dp0025_full_20260622.md)

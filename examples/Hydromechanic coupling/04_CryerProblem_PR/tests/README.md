# Cryer 测试文件

此处保存临时计算与工具核验，不替代 case 根目录正式 XML/BAT 和正式输出。既有目录原位保留；新配置、支持脚本、输出、日志和图分别使用 `configs / support / outputs / logs / figures / notes` 中适用的浅层分类。

## VTK 再生检查（2026-10-08）

使用现有 PartVTK 从保留的 BI4 重导出，没有运行求解器。四组共 11 个首/中/末帧与旧 VTK 的字节数及 SHA256 全部一致，见 [核验报告](logs/vtk_reexport_20261008.json)。这是文件再生检查，不是 Cryer 物理模型精度验收。

| 组名 | `outputs/` 中的原结果 | 核验帧 |
|---|---|---|
| `batstyle_smoke` | `CaseCryerProblem_PR_dp002_rampclosed_nu030_batstyle_smoke_out` | 0、1 |
| `cpu_peak` | `cpu_release_peak/CaseCryerProblem_PR_cpu_rel_peak_out` | 0、31、61 |
| `cpu_peak_dp002` | `cpu_release_peak_dp002/CaseCryerProblem_PR_cpu_rel_peak_dp002_out` | 0、31、61 |
| `gpu_releasecheck` | `gpu_releasecheck/CaseCryerProblem_PR_gpu_releasecheck_nu030_out` | 0、500、1000 |

支持脚本：[verify_vtk_reexport.ps1](support/verify_vtk_reexport.ps1)。在 case 根目录运行，示例：

```powershell
powershell -NoProfile -File tests/support/verify_vtk_reexport.ps1 -Full -Group gpu_releasecheck -OutputDirectory tests/outputs/gpu_vtk_restored
```

它只写新目录，拒绝覆盖既有结果；`-Full` 再生该组全部帧，默认模式只核验表中样本。新文件带组名前缀；原命名方式和字段参数也保存在核验报告中。原 VTK 不在时，脚本不会声称已与旧文件再次完成字节比较。

首次导出遗漏了三个组的 `Mk` 字段，诊断报告和日志以 `.initial` 保存；修正后 11 帧全部通过。不要混淆首次不匹配与最终报告。样本目录为 `outputs/vtk_reexport_20261008`，首次诊断样本为同名 `_initial` 目录。

本轮已将表中四组的 1,127 个 `particles/PartFluid_*.vtk`（4,444,662,908 字节，约 4.14 GiB）移入回收站，未清空回收站。清理前逐文件核对了源文件与快照 SHA256；见 [逐文件清单](logs/vtk_cleanup_20261008.json) 和 [本轮整理记录](../../validation/organization_20261008.json)。BI4、PartInfo、输入、日志、CSV、图、根目录正式输出以及整个 `refinement` 均保留。移入回收站并不表示已释放相同大小的磁盘空间。

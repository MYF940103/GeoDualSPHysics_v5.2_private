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

## Darcy 对称矫正短窗（2026-10-29，短窗通过，未验收峰值）

`cryer_symc_short_r1` 依次计算原算子粗步、原算子半步、候选粗步、候选半步。每组独立从零开始，CPU 8 线程，终点 `0.00830078125 s`，69 个原生输出；不续算旧 PART。配置及 BAT 位于 `configs/`，输出位于 `outputs/cryer_symc_short_r1_*`，检查在 `logs/`，逐样本表在 `figures/`。目的和准入标准见 [本轮说明](notes/cryer_symc_short_r1.json)。

候选只将土粒子之间 Darcy 两点收缩中的接收端矫正矩阵改为两端矩阵的对称平均。压缩源、应力率、力学加速度、原始围压、材料、球体离散、排水和时间积分均不改。候选源码及 Release 程序隔离在 `outputs/cryer_symc_cpu_build_r1` 与 `outputs/cryer_symc_release_r1`，正式源码、程序及根目录 XML/BAT 保持原样。

采用已完成的 `cryer_symc_cpu_r1` 冻结场探针，不重跑：中心 Darcy 瞬时误差减少约 91%，总孔压率误差仅减少约 24%，压缩源误差仍大；这不能证明实际峰值改善。新冻结标量扩散充分步长上界约 `4.13e-6 s`，拟用粗步 `2^-21 s`，该结论不等于完整耦合稳定性。每组保留原安全检查及预载平衡检查；原算子先与同时间步的保留 GPU 轨迹比较，两套算子分别执行 `5 Pa / 0.005 mm` 独立半步检查。候选与原算子的差异只记录，不冒充半步误差。短窗通过也不自动准入峰值或正式长计算。

四组已全部完成。276 个 CPU 保存态、138 个保留 GPU 对照保存态和 414 个比较记录经独立复核，原安全、排水、预载五项平衡和比较门均通过；1033 个活动证据文件的 SHA/大小匹配。原算子、候选自身半步最大孔压场 RMS 分别 `0.579730 / 0.685040 Pa`，原算子跨端最大差 `0.000800 Pa`。候选与原算子最大差约 `168.506 Pa`，属于算子变化，不是误差或改善量。

完整启动及开排水放大图为 `figures/cryer_symc_short_review_r1_history.png`、`_opening.png`，对应数据沿用 `cryer_symc_short_r1_summary.csv` 和 `_comparisons.csv`，未平滑或删去启动点。末端半步候选相对原算子中心压力增加 `47.9082 Pa`、体积加权平均压力减少 `1.62662 Pa`、材料壳层内移均值增加 `0.000159438 mm`，不能据此判定哪套更准确：排水后仅 4 个点，距真实峰值窗口尚远。

新增 `cryer_compression_moments_r1` 纯离线分析：冻结理论峰场中心压缩源误差约 `466675 Pa/s`，双精度替代计算与真实融合结果仅差 `0.01895 Pa/s`；一次矩闭合正确，误差分解主要来自非仿射高阶余项。独立虚速度检查也确认原孔压力与修正散度不配套，但这不是动态峰误差的因果证明。原 raw 外载的常总应力平衡仍通过，不采用 load-only 矫正。下一步仅准备隔离 GPU 对称 Darcy 候选，须构建、内存检查和同物理短窗跨端验证后，再决定峰值窗口；正式源码和输入不变。

### 隔离 GPU 构建与短窗入口

`cryer_symc_gpu_build_r3` 的 Debug/Release 已编译和链接成功；候选 CUDA 仅增加私有邻域函数的矩阵指针、四个调用参数及土粒子间 Darcy 对称收缩，和已核验 CPU 候选代数一致。两版各自 779 个实际头依赖均在编译前绑定，2667 个受保护输入及正式程序/源码目录保持不变。Debug 有继承库的 LNK4098/4099 和清单选项 LNK4075 警告；Release 仅有 LNK4075。可执行程序仍是测试候选，不是正式发行或物理验收。

失败的 r1（NVCC 临时路径空格）和 r2（编译成功、实际头文件预绑定不全而阻止链接）原位保留，不重试、不采用它们的对象。r3 在新目录从相同 CUDA 字节重建，未放松依赖门。构建脚本、说明、计划和收据分别位于 `support/cryer_symc_gpu_build_r*.py`、`notes/cryer_symc_gpu_r*.json`、`logs/cryer_symc_gpu_build_r*`；程序和对象仅本地保留。

新入口 `support/cryer_symc_gpu_short_r1.py` 默认仅显示帮助；显式准备后，按 Debug 256 步零内存错误/零泄漏检查、Release 粗步 69 帧、独立半步 69 帧顺序准入。使用保留 CPU 对称候选作同时间步跨端对照，并记录保留 raw GPU 的选项差异；原 `5 Pa / 0.005 mm`、预载平衡、所有真实排水点和自然步长门保持不变。内存日志自检使用实际 CUDA 11.7 零错误/零泄漏摘要，旧日志仅作解析格式证据。每项通过才启动下一项，终止后只尝试一次同会话通知，不启动峰值或正式长算。

另核对初始原生分类：5153 个 FSType2 排水点全部在 `r=0.05 m` 球面；32020 个内部点最大半径 `0.0475 m`，没有被误设为排水的内层。因此目前不移动排水面。该几何检查不证明离散边界算子已具备连续体精度。

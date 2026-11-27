# Cryer 根目录归档和显式 u-pl 基准 · 2026-11-28

后续用户指定加入 symC 前的 BAT、XML 和输出统一放入 `olddata/`，下表记录的是第一次移动的位置。现行位置见[配置、结果与服务器包整理](cryer_case_organization_20261128.md)。

当前收尾基准是 `upl_cryer_freebody_peak_GPU_r1` 的 ν=0.30 显式 u-pl 峰窗。根目录保留配套的 `CaseCryerProblem_u_pl_nu030_r1_Def.xml`、GPU BAT 和冻结 ZIP，以及公共显式 u-pl 入口。原生数据、时序表、图和分析见[峰窗审查](upl_cryer_freebody_peak_root_r1.md)。本轮只整理文件，未启动求解或更改计算参数。

## 对称扩散的证据

旧 u-pw 的同配置 GPU 对照只改变土粒子对 Darcy 收缩的校正矩阵，从接收粒子的 \(C_i\) 改为 \((C_i+C_j)/2\)。在同一粗步峰窗，峰幅误差从 −2.453% 降至 −1.010%，峰时滞后从 +10.309% 降至 +3.922%，孔压 RMS 从 322.36 Pa 降至 149.96 Pa。半步对照也得到相同趋势。[峰值表](../figures/cryer_full_review_r1_peaks.csv)

选定的显式 u-pl 冻结程序在动态 Darcy 分支中直接使用 \((C_i+C_j)\nabla W\)。`PoreDarcySymmetricCorr=0` 关闭的是旧 u-pw 开关。显式 u-pl 同时采用 Taylor 一阶缺陷修正、加速度散度及随 \(J\) 变化的孔隙率与体积权重。现有实算未隔离这些项各自的收益。与旧正式 u-pw 的 ν=0.30 symC 结果相比，显式 u-pl 峰时误差从 +3.979% 变为 +2.471%，峰幅误差从 −1.034% 变为 −1.493%。显式 u-pl 数据覆盖峰窗至排水后 0.0625 s。[冻结源码归档](../outputs/upl_cryer_freebody_r1_source.zip) · [峰窗对比](upl_cryer_freebody_peak_root_r1.md)

## 从根目录移出的文件

以下 11 个文件共 42,851 字节，使用同卷移动。源文件名和内容保留，移动后逐项核对原路径不存在且目标文件长度一致。本轮整理未腾出磁盘空间。

| 原根目录文件 | 归档目录 | 大小 |
| --- | --- | ---: |
| `xCaseCryerProblem_PR_win64_CPU.bat`、`xCaseCryerProblem_PR_win64_GPU.bat` | `tests/configs/retired_root_20261128/` | 4,021 B |
| `xCaseCryerProblem_PR_nu010_win64_GPU.bat`、`xCaseCryerProblem_PR_nu020_win64_GPU.bat`、`xCaseCryerProblem_PR_nu045_win64_GPU.bat` | `tests/configs/retired_root_20261128/` | 6,051 B |
| `xCaseCryerProblem_PR_dp002_rampclosed_nu010_win64_GPU.bat`、`xCaseCryerProblem_PR_dp002_rampclosed_nu020_win64_GPU.bat`、`xCaseCryerProblem_PR_dp002_rampclosed_nu030_win64_GPU.bat`、`xCaseCryerProblem_PR_dp002_rampclosed_nu045_win64_GPU.bat` | `tests/configs/retired_root_20261128/` | 8,136 B |
| `Cryer_public_SPH_TPI_nu030_1Tv_Windows_RTXA6000.zip.sha256` | `tests/logs/retired_root_20261128/` | 119 B |
| `support.zip` | `tests/outputs/retired_root_20261128/` | 24,524 B |

旧 BAT 的相对路径从 case 根目录解析。如需复现，先把相应 BAT 按原名复制到新的复现副本的 case 根目录。旧 BAT 含已有结果的删除菜单，运行前应检查副本目标路径。原 XML 和结果路径仍供旧 Poisson 绘图和审查脚本读取。

根目录五个服务器 ZIP 均是现有冻结入口的运行依赖，入口按 `support/hydro_frozen_plan_r2.json` 读取各自的 ZIP。旧 `support.zip` 含七份脚本，其中四份与当前散放副本不同。用户指定保留的 `tests/outputs/cryer_weak_full_server_r1.zip` 仍在原处。旧输出、正式图及对应数据表保留。本轮 Git 归档包含 BAT、校验单和说明，旧脚本 ZIP 保存在本地。此前 VTK 空间回收另见[六月数据清理记录](cryer_june_vtk_cleanup_20261127.md)。

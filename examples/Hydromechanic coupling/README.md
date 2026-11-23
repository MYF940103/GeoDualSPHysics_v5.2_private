# 水土耦合算例索引

公共源码在 `execution/special/hydromechanics` 中读取 `HydroMechModel`。打开 `HydroMech` 后，缺省或 0 使用 u-pw，1 使用有限水体积模量的显式 u-pl，2 使用零储水的三轮 TPI u-pl。旧配置中 `HydroMechDynamicSeepage` 的 false/0 和 true/1 分别迁至模型 0 和 1。复现历史计算时使用原 BAT 配套的程序与 XML。

模型 2 采用 α=0.5、β=0。`HydroMechTpiR` 缺省为 1，仅对模型 2 的水力步长上限生效。首次预测以初始孔压作为上一时刻压力，各轮在施加边界后的压力场上重算端点力和渗流残差。公共实现覆盖从头计算的 C02 周期弹性柱和 C04 均布围压球体，采用恒渗透率、固定步长、Wendland 核和固定步数排水。C08 撤墙接续、自由渗流、变渗透率与一般 PART 重启的适用范围见发布说明。Cryer 的真实四面体表面积分使用独立研究程序。[公共 TPI 的验证与限制](validation/public_tpi_release_r1.md) · [R 的选取与实测](validation/upl_tpi_r_selection_r1.md)

模型 2 每个非初始 PART 的 `TpiPressureHistory` 按材料 ID 保存预测器实际使用的上一整步源孔压及其时钟。首次开启排水时，受控表面点的源压力已经归零，而上一闭态 PART 仍可有非零压力。两次常规输出之间可能包含多个积分步。

新程序可在 `execution/special` 中单独指定外载，例如 `<externalload mode="FlexibleConfinement" q0="10000" ramptime="0.00390625" />` 表示在 0.00390625 s 内将球面围压加至 10 kPa。省略该节点表示无外载。旧配置的 `HydroMechTopLoadMode`、`HydroMechTopLoadQ0`、`HydroMechTopLoadRampTime` 分别迁至 `mode`、`q0`、`ramptime`。

排水边界也单独置于 `execution/special`。省略 `<drainage>` 等同于 `<drainage mode="drained" start="0" clock="time" />`。常规排水将符合算例边界条件的自由表面粒子孔压置零。延迟排水可写 `<drainage start="0.01" clock="fixedStep" />`，时间单位为秒。固定步数时钟要求从头计算、步长固定且开放时刻落在整步上；它只校正开排水时刻的累计舍入误差，输出频率仍由 `TimeOut` 决定。

`<drainage mode="off" />` 关闭上述规定孔压边界。`<drainage mode="freeSeepage" />` 用于当前支持的二维动态渗流重力容器，采用相应的表面渗流离散，完整步末将表面正孔压置零并保留负孔压。这两种模式均不填写 `start` 或 `clock`。复现历史结果时请成套使用对应的输入、BAT 和可执行程序。

[正式 XML、BAT 和复现检查](validation/hydro_frozen_entry_release_r2.md) · [排水迁移与逐算例验证](validation/drainage_xml_review.md) · [XML 格式](../../doc/xml_format/_FmtXML_ElastoplasticSoil.xml) · [已回传的私有 TPI 峰窗](04_CryerProblem_PR/figures/cryer_tpi_p3_nu030_peak.md)

### Cryer ν=0.30 服务器入口

| 目的 | 输入和运行方式 | 回传目录 |
|---|---|---|
| 用公共 GeoDualSPHysics 计算 SPH/TPI 至 1 Tv | [标准服务器包说明](04_CryerProblem_PR/README_Cryer_TPI_nu030_1Tv.md)。BAT 从 Def.xml 运行 GenCase、GPU Release 和 PartVTK。 | `CaseCryer_TPI_nu030_1Tv_GPU_out` |
| 检验改用固定参考四面体弱式后，峰值改善能否保持到晚期 | [独立研究包](04_CryerProblem_PR/tests/outputs/cryer_weak_full_server_r1.zip)。先运行 `CHECK_GPU.bat`，再运行 `RUN_FULL.bat`。独立程序读取预先组装的几何、离散矩阵和检查点。 | `cryer_weak_full_out` |

两种方法的[同一批材料点峰窗比较](04_CryerProblem_PR/tests/notes/cryer_weak_3d_peak_r1.md)和[旧四组泊松比的正式结果](04_CryerProblem_PR/figures/formal_validation/cryer_formal_four_nu_r2_log.png)可直接查看。两个新入口分别使用独立输出目录。

## 算例

| 目录 | 用途与保留范围 |
|---|---|
| [01_SelfWeightConsolidation_PR](01_SelfWeightConsolidation_PR/README.md) | 自重固结；正式两阶段输入和重启数据保留，MLSDirect/TPI 历史试验按状态登记 |
| [02_TerzaghiConsolidation_q0_PR](02_TerzaghiConsolidation_q0_PR/README.md) | 外载一维固结；保留 k=1e-4/1e-3/1e-2 正式结果及 precision/double 历史对照 |
| [03_RetrogressiveSlopeFailure_u_pw](03_RetrogressiveSlopeFailure_u_pw/README.md) | 后退式滑坡；保留 5 m、8 m 两阶段入口、预应力/失稳结果、ZIP 和视频 |
| [04_CryerProblem_PR](04_CryerProblem_PR/README.md) | Cryer 问题；正式输出全部保留，tests 和 refinement 的探索结果不得当作已通过解析验收 |
| [05_LianFlexibleStrip2D_PR](05_LianFlexibleStrip2D_PR/README.md) | 柔性条带加载；正式结果及 plastic-off 对照保留 |
| [06_Yao2DConsolidation_PR](06_Yao2DConsolidation_PR/README.md) | 二维固结；保留默认/阻尼分支入口，现用参考数据仍在 tests/outputs |

## 固定布局

每个 case 的正式 XML、BAT 和正式 `*_out` 留在根目录；正式图在 `figures/`，正式支持文件在 `support/`。测试集中在 `tests/`，按 `configs / support / outputs / logs / figures / notes` 浅层分类，不要求创建空目录。详见 [AGENTS.md](AGENTS.md)。

05/06 已有的 `tests/scripts/` 原位沿用，不搬迁或另建同用途目录。

已有 BAT 可能含同名输出覆盖或 `-force` 删除流程。本次整理不运行这些入口，也不重写正式 XML；新测试必须使用独立输入和输出标签。完成计算不等于允许删除数据。

## 历史材料与备份

- [00_upl_records](00_upl_records/测试记录归档说明.md)：已回退 u-pl 开发记录、恢复档案和旧精度补丁证据，原位保留；这里的历史“保留精度补丁”说明不能替代当前 float 回退状态。
- [validation](validation/README.md)：跨 case 的回归、迁移和本轮清理记录，不放新的编号 case 正式输出。
- `CFC2027_abstract/`、各 case 的 PPTX/TIFF/独有图以及 `03` 的 ZIP/视频属于保护材料。本轮不整理其内容或按重复名称删除。
- `01_SelfWeightConsolidation_PR/figures/figures/` 是历史混合材料，存在与 `02` 同名但内容不同的文件；暂不搬动，归属待确认。
- 整理前 Git 检查点：`d2c15a3`（2026-10-08，已推送并核对 `origin/u-pw`）。Git 保存代码、输入、脚本和选定记录；大型原生结果另行备份，不能把“Git 已推送”理解为全部数据已上云。
- 本轮整理与完整性检查以 [organization_20261008.json](validation/organization_20261008.json) 为准；前一轮可恢复清理见 [cleanup_20261008.json](validation/cleanup_20261008.json)。
- 本轮仅将 Cryer 四组测试中已核对备份的 1,127 个派生 VTK（约 4.14 GiB）移入回收站；原生 BI4、正式输出和历史模型记录保留。再生方法和逐文件清单见 [Cryer tests](04_CryerProblem_PR/tests/README.md)。

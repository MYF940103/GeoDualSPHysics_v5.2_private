# 水土耦合算例索引

当前公共源码在 `execution/special/hydromechanics` 中读取 `HydroMechModel`。打开 `HydroMech` 后，缺省或 0 使用 u-pw，1 使用显式 u-pl。旧配置中的 `HydroMechDynamicSeepage` 需要迁移，false/0 对应模型 0，true/1 对应模型 1。2 为 TPI u-pl，当前由 Cryer 验证程序执行，公共程序请求该值时会报错。运行既有算例请使用其 BAT 配套的程序和 XML。

新程序可在 `execution/special` 中单独指定外载，例如 `<externalload mode="FlexibleConfinement" q0="10000" ramptime="0.00390625" />` 表示在 0.00390625 s 内将球面围压加至 10 kPa。省略该节点表示无外载。旧配置的 `HydroMechTopLoadMode`、`HydroMechTopLoadQ0`、`HydroMechTopLoadRampTime` 分别迁至 `mode`、`q0`、`ramptime`。孔压排水和开放时刻仍在 `hydromechanics` 中配置。[XML 格式](../../doc/xml_format/_FmtXML_ElastoplasticSoil.xml) · [TPI 验证包说明](04_CryerProblem_PR/README_Cryer_TPI_P3_nu030_r1.md)

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

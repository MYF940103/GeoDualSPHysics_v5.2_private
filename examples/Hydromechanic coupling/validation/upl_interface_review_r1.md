# 水力接口精简清单

按用户要求，在 case08 基础兼容完成后、正式输入与服务器打包前逐项决定接口去留。
本轮只清点与整理说明，不删除接口、不改变默认值或方程。参数指导文件只放用途、默认值和必要限制；测试过程留在各 case 的 tests/notes 与 logs。

以下默认值来自 `JSph::InitSoilParameters`。根目录输入统计覆盖38份 Def XML，含历史与候选，不能把数量当作验收或实际启用次数；未显式填写也不代表未使用默认值。

| 参数 | 省略时默认 | 后续审计重点 |
|---|---|---|
| HydroMech | 0 | 保留耦合总开关 |
| HydroMechDynamicSeepage | 0 | 保留 u-pw/u-pl 物理框架选择，内部观察器/反馈开关不应重复公开 |
| PoreWaterRho | 1000 | 保留水相物性 |
| PoreWaterBulkModulus | 0 | 保留物性；耦合时必须正值 |
| Porosity | 0 | 保留初始孔隙率；耦合时必须在(0,1) |
| HydraulicConductivity | 0 | 保留初始渗透系数 |
| HydroMechConductivityModel | 0 | 与 Ck 成套审计；常数/演化是物理选择，不由非零参数暗中切换 |
| HydroMechConductivityCk | 0 | 仅指数模型需要显式正值；不是通用默认0.01 |
| HydroMechInitMode | None | 保留必要初态；检查算例专属初始化是否该归入初始化模块 |
| HydroMechInitZ | 0 | 仅 ConstantZ 使用，且该模式要求显式填写 |
| HydroMechTopLoadMode | None | 模式3/4含算例专属几何，评估迁入统一外载接口 |
| HydroMechTopLoadQ0 | 0 | 保留荷载量；与统一外载配置一起整理 |
| HydroMechTopLoadRampTime | 0 | 保留加载历时；避免水力模块重复拥有通用加载逻辑 |
| HydroMechDrainage | 1 | 保留有明确物理含义的边界条件 |
| HydroMechDrainageStartTime | 0 | 保留边界开启时间 |
| HydroMechDrainageFixedGrid | 0 | 审核能否内化为统一事件时钟；先保证旧结果的时序可复现 |
| HydroMechFreeSeepage | 0 | 与零压排水一起审核边界策略，保持各自物理含义及互斥关系 |
| PoreDtSafety | 0.1 | 保留显式积分安全系数 |
| PoreShepardRegularization | 0 | 动态框架禁用；审核是否仅保留兼容/诊断入口 |
| PoreShepardInterval | 30 | 随正则化一起决定去留，避免孤立无效配置 |
| PoreMdbcInterpolationMode | 0 | 动态墙已用独立重构；审核旧模式是否应内化或退役 |
| PoreCompressionSourceMode | PairDivergence | 动态框架固定为成对散度，审核替代诊断路径的必要性 |
| PoreCompressionGradCorr | 1 | 动态框架要求开启，审核是否可成为该框架的内部固定条件 |
| PoreDarcySymmetricCorr | 0 | 已有 Cryer 输入用1；不能在迁移前删除，需明确旧 u-pw 与动态算子的关系 |

现有38份根目录输入中，Shepard 开启出现5次、对称 Darcy 开启出现5次、固定格点事件出现10次。因此退役前须检查对应输入、实际消费者及保留程序；用同一旧输入对照确认迁移行为，不能静默改物理模型或令旧键被忽略。

材料配置仍位于 `<soils>`：`MaterialReturn` 是返回算法，固定强度也适用；`DilationDecay` 是剪胀演化，和 `n_coh` 不同。两者不放入 hydromechanics，也不放入 `if(StrainSoftening)`，以保留仅剪胀演化或无强度软化的一致返回。当前只调整读取分组，结构体字段、XML路径与默认值不变。

每个接口的最终决定按“保留物理选择／合并通用模块／内化已固定条件／显式退役诊断入口”记录；先检查兼容和数值影响，再迁移正式输入。本清单不是已完成的删参或兼容性验收。

# 正式根输入、配套程序和迁移边界

检查范围为 C01–C08 各案例根目录的 53 份 `*_Def.xml` 和 76 个 BAT。当前有 32 份使用公共格式（含依默认值运行的 XML），这些根 XML 中没有原动态开关、顶载、开排水或自由渗流旧键。另有 21 份根 XML 仍属于冻结程序或以前的回传包。这 21 份使用的旧标签有 HydroMechDrainage 21 份、HydroMechDynamicSeepage 14 份、HydroMechFreeSeepage 11 份、HydroMechDrainageStartTime 10 份、HydroMechDrainageFixedGrid 8 份、HydroMechTopLoadMode 20 份、Q0 和 RampTime 各 9 份。

| 案例 | 公共 / 原程序绑定 | 根 BAT、程序和输入现况 |
|---|---:|---|
| C01 自重 | 3 / 1 | Stage1 与 Scenario1/2 使用仓库 CPU/GPU；FreshPR 绑定 `support/bin`、原生解析器和接收 `--config` 的后处理。只有以转换后实际求解 XML 作为后处理输入，并对生成、物理场及正式基准重做短回归时，才适合在新入口转换。 |
| C02 一维固结 | 7 / 0 | 公共 CPU/GPU。正式后处理 `support/release_case.py` 及比较脚本读取原输出/保存配置。新旧解析曾针对七份根输入、三份既有结果合核；应继续保留输出内真实 XML。 |
| C03 退行滑坡 | 4 / 0 | 新旧两组几何均由公共程序分两段运行；失败段依赖真实预载。原未被求解器读取的旧地表排水拼写不应在迁移中被解释成新的活动边界。 |
| C04 Cryer | 10 / 8 | 新增 `CaseCryer_TPI_nu030_1Tv_Def.xml` 已走公共 schema，BAT 优先包内 `bin`，无 GenCase 时回退仓库 `bin/windows`。8 份专用输入为两份 P3 峰窗/全程，三份 `release_nu*_r1`、`release_r2`、`symc_nu030`、`u_pl_nu030_r1`。分别依赖 `support/bin_cryer_tpi_p3_r1`、`support/bin`、`support/bin_upl_r1`。其中有清单校验程序、XML 与种子的服务器包，只生成语义等效但字节不同的旧 XML 可能直接破坏清单。保留包的原始文件与已回传结果，公共入口可独立使用。 |
| C05 Lian 条带 | 1 / 1 | 公共输入另有一套冻结正式服务器 GPU，后者绑定 `support/bin`。若将来补新入口，比较两种渲染输出的分组滑移、条带节点荷载、排水边界与同实际保存时刻原生字段，再独立形成新发布。 |
| C06 Yao | 5 / 0 | 均使用公共程序；保持原来的条带加载、滑移与排水模式。 |
| C07 Selborne | 2 / 0 | 两份输入仅通过几何生成资格；真正的预应力/破坏 BAT 仍主动以代码 2 退出，另有几何检查 BAT。更换 XML 不使其获得物理运行资格。 |
| C08 饱和柱塌陷 | 0 / 11 | 根 BAT 递归调用不同版本 `support/run_lian_collapse_shared_r*_win64.bat`。真实程序位于 `support/runtime_r3..r6`；r3/r4 配 CPU/GPU，r5/r6 配 GPU。R5/R6 后处理指名核对旧动态开关、自由渗流、无常规排水等；预载还需与接收端同材料合同、原 MK/ID、事件时间、边界切换和原生解释器相符。原 10 s PRE、发布包、生成 XML 和已有接收结果应保留原样。 |

**转换策略。** 新入口以公共字段作为唯一源。若必须调用有旧解析器的程序，可在独立暂存目录生成一份供该次运行使用的旧输入，记录原定义、实际发给 GenCase 的定义、实际执行程序和输出目录，不覆盖旧发布文件。仅有旧 `HydroMechDynamicSeepage` 的程序通常能表达 0/1；是否支持 2 须由该专用程序证明，绝不能把公共 TPI 的 2 直接降为旧开关 1。还需逐一对齐默认排水、none、freeSeepage、fixed-step 与时间触发，外载模式/q0/ramptime 及可选属性。未知项或缺少旧表示应拒绝生成。C04 冻结签名/清单、C08 全状态交接与后处理是风险最高的两处；C01/C05 也需要具体版本的前处理、求解和后处理短验。仅 GenCase 接受 XML 不足以证明旧求解器读取了新 sibling。基于目前证据，直接重写 21 个现有绑定入口没有依据；公共程序无需为它们恢复旧字段解析。

**记录与空间。** 全量逐文件键、根 BAT 及其引用脚本内的程序定位/调用行记录在 [结构化清单](hydro_root_bindings_review_r1.json)，包含随时间变化的文件统计。2026-11-23 本轮统计的 10 个 C08 私有构建目录内，OBJ、PDB、IOBJ、IPDB、ILK 共 229,527,433 逻辑字节，按 NTFS 文件句柄读取的 AllocationSize 合计 229,617,664 字节（约 218.98 MiB），已按同一 inode 去重。公共对象和运行中链接的 C08 对象仍是依赖；原生 BI4、可执行文件、源码归档、正式图及数据不在候选内。本次回收 0 字节。

[历史 52 个根输入检查](../04_CryerProblem_PR/tests/logs/drainage_public_roots_r1.check.json) · [正式后处理取参记录](../04_CryerProblem_PR/tests/logs/drainage_workflows_r2.check.json) · [历史模型与外载迁移](hydro_single_xml_r1.md) · [复查脚本](hydro_root_bindings_review_r1.py)

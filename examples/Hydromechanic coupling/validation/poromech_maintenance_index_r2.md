# 水力耦合工作与维护分类索引 r2

日期：2026-11-18（Asia/Tokyo，日本时区）。本索引帮助定位当前工作与保留证据，维护结果以本轮实际检查为准。旧 README 中带日期的阶段记录仍是历史，不据旧的“运行中/下一步”文字重启任务。

## 当前工作边界

| 分类 | 当前定位与结论边界 |
|---|---|
| C02，一维 TPI 完整周期 | 活跃标签 `upl_tpi_p3_B10us_full2tv_GPU_r1`；计划 dt=`1.0000228881835938e-5 s`、7288262 更新、1653 帧、目标实际标量终点 `72.88428815806371 s`。这些是已审核计划，不是已经达到的状态。新 B/P3 full2Tv 尚未完成原生/物理验收；保留当前程序、源/对象闭包、准入输入及 owner 的一次终态机制。 |
| C08，ψ−5° | 原重力预载暂停，最后原始报告约 `9.660005 s`，未完成 10s PRE，不能称预载资格/平衡已通过。暂停请求/结果为 `08_LianSaturatedColumnCollapse_u_pl/tests/logs/c08_psim5_user_pause_r1.*.json`。不恢复、不重启、不重算、不重挂旧 worker；保留原内存状态依赖和原输出。 |
| C04，Cryer | 旧四泊松比正式计算及分析已完成，保留 `04_CryerProblem_PR/figures/formal_validation/` 的图和 CSV。新 TPI 的 CPU/GPU A/B/C128 是启动实施资格，尚未到开排水/Mandel 峰值物理验收；旧正式结果不是新 TPI 峰值已经通过的证明，也不因此重跑四组。 |

C02 全程来源入口为 `02_TerzaghiConsolidation_q0_PR/tests/logs/upl_tpi_p3_full_plan_r1.prepare.json`、`upl_tpi_p3_B10us_full2tv_GPU_r1.run_admission.json` 及对应原 start/call/run/status；只有真实产出的收据才作证据，尚不存在的最终 run/native/科学检查不能预填。新 Cryer 实施范围见其 `tests/notes/upl_tpi_cryer_gpu_startup_root_r1.md`；TPI 总计划见本目录 `upl_tpi_three_scheme_plan_r1.md`。

## 目录用途

| 位置 | 用途 |
|---|---|
| 各 case 根目录 | 正式 XML/BAT、正式输入/输出及发行入口；不以测试目录整理为由覆盖。 |
| `tests/configs/` | 独立测试 XML、profile 等配置；冻结后按收据原位保留。 |
| `tests/support/` | 测试、私有构建、读取、离线分析工具；作者稿不等于执行或验收。 |
| `tests/outputs/` | 原生结果、私有程序/源码/对象及派生输出；不是可整目录删除的缓存区。 |
| `tests/logs/` | 准入、所有权/真实出口、clock、build/read/review、失败及维护日志。保留历史原文和绑定清单。 |
| `tests/figures/`、根 `figures/` | 前者放阶段诊断，后者放正式图；匹配 CSV、指标、误差及限定条件与图一起保留。 |
| `tests/notes/` | 设计、结论、拒绝理由和复现说明；依实际最新检查解释，不重复复制完整测试流水。 |

## 本轮维护范围与证据状态

明确白名单由本目录 `poromech_maintenance_r2.py` 及配套说明维护，不按 `old/r1/failed` 名称推断可删。已清除 **7 个未绑定旧 ILK 与 3 个 pyc**，并对 **9 个已完成测试派生目录中的 2479 个 VTK** 作 NTFS 透明压缩。VTK 的逻辑总大小仍为 **1,133,812,757 B**；原路径、长度和修改时间保持不变，可视化直接读取原路径即可。

本轮计划、逐项日志、终检及独立复核分别为 `poromech_maintenance_r2.plan.json`、`poromech_maintenance_r2.apply.journal.jsonl`、`poromech_maintenance_r2.apply.check.json`、`poromech_maintenance_r2.root_review.json`，均已真实生成并通过。缓存删除的 NTFS API 计量为 **320,769,016 B**；VTK 存储计量从 **1,133,812,757 B** 降至 **680,583,168 B**，减少 **453,229,589 B**。两项合计 **773,998,605 B（约 0.721 GiB）**；这是文件存储计量，不将卷空闲变化全部归因于清理。未扫描原始数据 SHA；透明性 fixture 检查和逐文件元数据记录不冒称所有 VTK 的整文件逐位证明。

维护前浅层盘点为 193 个 ILK、合计 7,526,426,496 逻辑字节，**不是整批删除白名单**。除上述七个外，其余缓存保留；后续按具体构建和复现依赖判断。已压缩过的旧 Cryer VTK不重复处理；正式根输出及当前 P3 full/C08 暂停依赖不进入本轮压缩范围。

## 原位保护与复现

保留全部原 BI4/NBI4、PRE/重启链、程序/源码快照和恢复 ZIP、OBJ/PDB、正式与必要诊断 PNG/CSV、唯一结论、原日志/失败、原哈希清单。只清名单内无运行依赖的增量链接缓存/pyc；保留其真实 link 配方、程序、对象与收据。已完成 VTK 保留原 data 和 PartVTK/BAT 再生入口，本轮只作透明压缩，不删物理结果，不重跑求解来“复现”。任何已完成求解的派生失败只修离线派生。

当前 `_FmtXML_ElastoplasticSoil.xml` 的整理范围仅精简批注，参数 values 不改变；它与清理程序不构成数值模型修改或新验收。各有效阶段继续选择性本地/远端 Git 备份工具、轻量收据、结论和必要图表；原始二进制在本地保留，不把 Git 称为原始计算数据备份。

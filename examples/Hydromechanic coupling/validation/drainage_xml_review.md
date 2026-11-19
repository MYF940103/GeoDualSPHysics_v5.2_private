# 排水边界 XML 迁移核对

对照版本为 `7965df7d7cabb1d1ba42f131c4873ea01a242f46`。新入口在 `execution/special/drainage`。普通排水的默认值为 `mode="drained"`、`start="0"` 秒和 `clock="time"`。使用说明及算例索引见[水土耦合目录](../README.md)。

8 个目录共 52 份根 XML。30 份公共输入迁移，1 份沿用默认排水，21 份保留其专用程序与原 XML。[逐算例说明](../04_CryerProblem_PR/tests/notes/drainage_public_cases_r1.md)

30 份已迁移输入各运行一次旧、新 GenCase，共比较 1,007,657 个初始粒子。两版有效排水设置、粒子 ID 和导出的初始字段均一致。目录外另外检查了 130 份现有、受 Git 管理的示例定义。逐文件结果见[根输入清单](../04_CryerProblem_PR/tests/logs/drainage_public_roots_r1.check.json)。七份一维固结配置、四个泊松比的 Cryer 服务器输入及其绘图取参结果见[生成和后处理检查](../04_CryerProblem_PR/tests/logs/drainage_workflows_r2.check.json)。

CPU Debug 12 个短窗共 59 帧，GPU Release 11 个短窗共 55 帧。同一后端逐材料 ID 比较新旧版本，全部原生数组（依算例为 15 或 22 个）、实际步号、时间及有符号时间诊断逐位一致。CPU Release 另作固定步数开排水及撤墙对照。20 份错误配置均在首帧前被拒绝。[CPU 回归](drain_xml_r1_cpu_new.json) · [GPU 回归](drain_xml_r1_gpu_new.json) · [C03 预应力](drain_xml_r1_cpu_retro_new.json) · [CPU 撤墙](drain_xml_r1_cpu_preload_new.json) · [GPU 撤墙](drain_xml_r1_gpu_preload_new.json) · [CPU Release](drain_xml_r1_release_cpu.json) · [错误输入](drain_xml_r1_cpu_negative.json)

Cryer 私有 CPU/GPU 程序另行验证了模型 0、1、2 和缺省模型。显式 u-pl 的跨事件短窗在开排水时刻仍可读到上一更新留下的表面孔压，随后两次保存各有 5,153 个表面粒子为零。TPI 短窗验证了三轮孔压更新，该短窗的两个更新均处于排水开启前。[私有 Cryer 验证记录](../04_CryerProblem_PR/tests/notes/cryer_drain_schema_r1.md)

复现已保存的长程结果时，使用该次保存的生成 XML、配套程序、输入或重启数据。公共旧版 Release 的本机副本放在 `04_CryerProblem_PR/tests/outputs/drainage_public_previous_7965df7`，配套 DLL 在 `bin/windows`。新的公共 XML 应与本次公共程序配套使用，早期程序可能忽略新的独立节点。正式历史数据与服务器包按原版本保留。本次验证范围为配置迁移、初态、事件和短窗原生输出。[公共程序版本记录](drain_xml_r1_programs.json)

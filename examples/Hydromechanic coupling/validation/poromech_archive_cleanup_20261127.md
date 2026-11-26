# 2026-11-27 归档与清理

本轮按[归档策略](poromech_archive_policy.md)审查 01–08 的正式与测试路径。开始时 D 盘可用 12,463,460,352 B。C08 正式三组继续使用原预载、运行器和根目录输出。

## 已核验的操作

| 操作 | 数量及大小 | 保留与恢复 |
|---|---:|---|
| C04 服务器 Cryer 峰窗传输 ZIP 迁至 C 盘独立磁盘 | 1 个，3,429,948,105 B | D 盘原解包目录内的 597 个文件路径与长度对应，解包结果未动。迁移时验证 ZIP 副本 SHA-256 与源一致。需恢复传输包时，从收据中的 archive 复制回 source，恢复前检查目标是否已存在。 |
| C07 四组已否决几何的重复 VTK | 32 个，46,868,171 逻辑 B | 同组另一阶段 VTK 与被删副本逐字节一致，保留原始 BI4/NBI4、失败收据和通过的几何。逐文件恢复对应项见收据的 preserved 和 source。 |
| C08 早期误命名绘图副本 | 5 个，1,394,277 逻辑 B | 图、CSV 及来源逐项等同 Git 中保留的对应物。收据的 retained 指向修正版，removed 给出原别名。 |
| C08 旧测试原生解码副本原位压缩 | 本次记录已核实的首个文件减少 737,429,604 B | 原路径、文件标识、长度和修改时间不变。清单按文件追加；批次最终值以后续实际终检为准。 |

[峰窗 ZIP 迁移收据](cryer_peak_zip_archive_20261127_r1.check.json) · [Selborne 去重收据](../07_Selborne3D_u_pw/tests/logs/selborne_geometry_duplicates_20261127_r1.check.json) · [C08 图表去重收据](../08_LianSaturatedColumnCollapse_u_pl/tests/logs/c08_disk_duplicate_figures_20261127_r1.check.json) · [C08 原位压缩逐文件记录](../08_LianSaturatedColumnCollapse_u_pl/tests/logs/c08_disk_compact_20261127_r1.files.jsonl)

## 余下的大宗对象

- C02 的旧 k=1e−5 CPU、GPU 两套退役测试共 9,221,837,700 逻辑 B。两组是主动停止的轨迹，分别保留至 Part15978 和 Part6056，仍有原始状态价值。适合按整组冷归档，连同归档目录和恢复入口登记。正式三组、发布引用和完整 TPI 对照不进入这个批次。[CPU 退役](../02_TerzaghiConsolidation_q0_PR/tests/logs/k5_cpu_retire_r1.json) · [GPU 退役](../02_TerzaghiConsolidation_q0_PR/tests/logs/k5_full_r1_acceleration_stop.json)
- C02 完整 P3 的三轮迭代 CSV 合计 2,025,721,358 逻辑 B。只保存末态 BI4 无法重建轮次表，应无损压缩或冷归档。已压缩的逐粒子 CSV 历史档和 Cryer 旧 VTK不重复计入。
- C01 的 FreshPR 403 帧以及 02 使用的旧 MLSDirect Part56、C03 两端共用的预载 Part50/PartExtra50 都有确切用途。较小的旧 TPI 失败输出保留首因和测试来源，暂缓机械清扫。[自重固结](../01_SelfWeightConsolidation_PR/README.md) · [Retrogressive slope](../03_RetrogressiveSlopeFailure_u_pw/README.md)
- C04 峰窗 P3 虽未通过物理标准，仍被开排水诊断使用。C05 保留正式 HGSPR 100 s/2001 帧及对应论文图表。C06 暂停新增研究，保留已取得的 10 s 自由滑移对照和 SPR 边界历史。[Cryer 开排水诊断](../04_CryerProblem_PR/tests/notes/c04_opening_recovery_r1.md) · [Lian](../05_LianFlexibleStrip2D_PR/README.md) · [Yao](../06_Yao2DConsolidation_PR/README.md)

历史归档的数量和当时状态以对应收据为准。上述保留与候选不构成新的计算验收。

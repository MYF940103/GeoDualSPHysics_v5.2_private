# C08 测试文件索引

[当前任务、文件分类与维护范围](../../validation/poromech_maintenance_index_r2.md)（2026-11-18）。

- ψ−5° 的原预载仍暂停，最后报告约 9.660005 s，未完成 10 s PRE；见 [暂停记录](logs/c08_psim5_user_pause_r1.result.json)。
- 当前先验证 TPI，再评估负孔压正则化，随后完成三组最终塌陷计算。已存 HG 轨迹保留作历史比较；当前大变形方案按用户要求关闭 HG。
- `configs/` 放测试配置，`support/` 放工具，`outputs/` 保留原生数据及私有程序/源码，`logs/` 放原始收据，`figures/` 与 `notes/` 放对应图表和结论。
- 原 PRE、BI4/NBI4、程序/源码/对象、图 CSV 和失败证据原位保护。维护只按跨 case 的明确白名单执行；不把 `outputs/` 整体当作缓存，也不重跑旧 worker。
- 正式发行入口与正式结果在 case 根目录；测试正常退出不等于正式物理验收。

# 2026-11-23　C02／Cryer 旧编译文件整理清单

已于 2026-11-24 在 C08 与 C02 的数值比较结束后完成原位 NTFS 压缩。89 个目标的路径、文件身份、长度、最后修改时间和内容摘要全部通过复核。实际分配空间从 454,942,720 字节降至 213,671,936 字节，回收 **241,270,784 字节（230.09 MiB）**。逐文件结果见[执行日志](compact_closed_objects_r1.executed.jsonl)。

| 范围 | 已列名文件 | 逻辑字节 | NTFS 已分配字节 |
|---|---:|---:|---:|
| C02 十五个旧 CPU 编译配置，位于 `src/VS/Intermediate` | 74 | 224,325,067 | 224,473,088 |
| C04 六个历史编译目录，位于 `04_CryerProblem_PR/tests/outputs` | 15 | 230,441,144 | 230,469,632 |
| 合计 | 89 | 454,766,211 | 454,942,720 |

`compact_closed_objects_r1.targets.json` 给出每个文件的相对路径、大小、最后写入时刻、卷和文件 ID，以及对应构建／实现检查收据。只纳入至少 1 MiB 的普通、单硬链、尚未压缩的 .obj 或 .ilk；文件均原位保留。C02 的原 MSBuild 编译记录位于 `02_TerzaghiConsolidation_q0_PR/tests/logs/<配置>.build.json`。C04 的原编译记录为 `cryer_darcy_switch_build_r1_{DebugCPU,ReleaseCPU}.build.json`、`cryer_darcy_switch_build_r2_Debug.build.json` 和 `cryer_symc_gpu_build_r3_{Debug,Release}.build.json`；后续实现证据为 `cryer_darcy_switch_native_r1.check.json`。这些均保留在 C04 的 `tests/logs`。

在本目录运行，第一条仅读取文件元数据。第二条才开始无损 NTFS 压缩。

```powershell
D:/anaconda3/python.exe -B compact_closed_objects_r1.py verify-plan
D:/anaconda3/python.exe -B compact_closed_objects_r1.py execute
```

执行前再次核对完整清单和相关活动进程。按文件和目录复查绝对路径、重解析点、硬链接及身份，记录压缩前后 SHA256、大小、最后修改时刻和 NTFS 分配空间。执行日志为 `compact_closed_objects_r1.executed.jsonl`。遇到内容、身份或执行错误，保留日志和原文件，停止剩余操作。已有执行日志时拒绝覆盖或重复执行。实际回收量以最终核验的逐文件分配字节差为准。无需解压便可继续链接原对象。

此次盘点时 C08 owner PID 23024 存活，相关 TPI 编译也在进行，执行前的活动依赖检查已实际拒绝操作。C08 的全部目录、TPI 工作树和当前公共对象、程序与 DLL、源码快照、项目 PDB、VS 缓存、BI4／NBI4、PRE／重启链、正式包、图与 CSV 都在清单范围之外。VS 正打开本解决方案；其 20 个 IntelliSense 缓存合计 1,409,155,072 逻辑字节，仅作库存记录。

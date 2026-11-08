# C08 阶段观测器短窗结果

本轮只验证默认关闭的 `C08_STAGE_TRACE` 观测器，不改变物理方程、参数、r2 PRE 或正式 `runtime_r5`。

| 项目 | GPU Debug | GPU Release |
|---|---:|---:|
| 新计算更新数 | 40 | 12000 |
| 撤墙后终点 | 0.0001 s | 0.03 s |
| 原生保存帧 | 1 | 3 |
| 每帧原生 ID / 数组 | 6805 / 22 | 6805 / 22 |
| 对保留同配置对照的数组及实际时间载荷 | 逐字节相同 | 逐字节相同 |
| 带符号 clock/dterror CSV | 逐字节相同 | 逐字节相同 |
| 阶段 CSV 行数 | 18 | 4503 |
| 压力 UPDATE / PONDING / RHS rate 位检查数 | 6 / 6 / 6 | 1800 / 903 / 1800 |

两次求解器的实际 Popen/Win32 出口均为 0；Debug compute-sanitizer 为零错误、零泄漏。Debug 对照为已封存同配置短窗，Release 对照为根目录 r5 的前三个实际保存帧。完整原生 ID、P0、J/体积/密度 ledger、不可穿透平面、AS/KeepBed 元数据及既有数值安全门通过。新输出头保持真实的 1/3 帧，对照的 1/300 帧头未改写。

CSV 检查保留初始化额外的 PONDING 事件，不以强制行数删记录。Release 实际 scalar 时钟重放误差为 0；lap、chain、RHS value 最大绝对重算差分别为 8.73115e-11、1.08420e-19、3.72529e-9，均在原浮点舍入预算内。所选 C 的 XZ 无穷范数条件数最大 1.58788，仅为短窗描述指标，不是新增准入阈值。

首次 Debug native 预检在任何读取器启动前对 Windows `Registry` 伪进程路径调用 `samefile` 而失败。原失败收据保留，decoder_invocations=0。新 `smoke_r2.py` 仅修正进程路径比较和新的读取/审查入口；两次实际读取器各执行一次，没有重跑求解器。对应 `.native_r2.json`、`.review.json` 和 `.trace.check.json` 均已通过。

这证明上述短窗中观测器没有改变保存结果，不证明 0.63/0.64 s 压力脉冲已解决，也不是半步长、论文精度或完整塌陷验收。下一项是另行审查一个到撤墙后 0.66 s 的相同物理诊断窗，在 0.60–0.66 s 逐步记录真实 RHS/UPDATE/PONDING；不重跑 10 s PRE，不启动其他剪胀角、半步长或正式长程。原全程结果及所有失败历史不动。本轮 SHA 扫描次数为 0。

原始证据：`tests/logs/upl_c08_stage_trace_smoke_{Debug,Release}_r1.*`；原生数据与阶段 CSV：`tests/outputs/upl_c08_stage_trace_smoke_{Debug,Release}_r1/`。原始 BI4、二进制、程序与源码归档仍在本地保护范围，Git 备份不包含它们。

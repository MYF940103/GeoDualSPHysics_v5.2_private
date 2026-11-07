# 正式NoPen程序的一次0.15秒回归

程序使用正式 `support/runtime_r4` 的新GPU Release，不使用隔离诊断程序。输入来自根目录ψ0 r4模板，绑定同一原r2 PRE；仅以global4060000上限结束短窗，保护正式完整输出路径。NoPen1、AS0、dt2.5us/.01s输出与前次NoPen0.15完全一致。

本轮只有一次相同时间步回归，不新增half或物理参数候选。求解成功后采用新r4实际后处理完成native及独立Fluid/Bound粒子和图CSV；全部15条time+22数组与完整signed-clock记录须逐字节复现 `outputs/upl_c08_nopen_native_r1`，新正式policy元数据单独核。旧结果/元数据不重写，正式输出不被短窗占用。

保护原输入、原PRE、程序和全部原生门。只有该回归通过后，才由原授权执行根目录正式ψ0 GPU BAT，TimeMax13完成撤墙后3秒。该长计算的正常退出与物理精度验收分开记录。

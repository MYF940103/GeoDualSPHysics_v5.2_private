# n4失败窗口：66个真实保存态的独立只读检查

只新增 `support/upl_c08_asn4_partial_r1.cpp`、同名 `_build.py`、`_run.py`及本说明；事前确认四路径不存在且未跟踪。作者不构建、解码、运行求解器或修改原90帧读取器、原90分析、plan、输入、BI4与既有收据。

实际源为 `upl_c08_asn4_window_GPU_r1`：原owner/目标是真实失败exit1、无ownership errors。第一引擎异常是必要孔压时步上限被固定2.5µs超过，日志报告step4265004；原90帧计划未完成。最后原样console行为Part0065/10.660000/completed4264000，实际磁盘连续Part0000..0065共66。**不从报告step推算未保存失败时间、位置或状态。**失败目录没有正常Run.csv，不制作或修改它。

根全文审阅后，分开各一次：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_asn4_partial_r1_build.py --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_asn4_partial_r1_run.py --execution-authorized
```

构建从已封口 `upl_c08_asn4_window_native_r1.build.json` 的实际 generated core 派生，只改三锚点：成功Run.csv调用改为固定失败66/4264000且读取**原90行/4360000**计划；stage新tag；completion明确partial而非完整运行。原 `Planned` 函数不改，仍拒额外/缺少行；完整验证90行后使用真实前66。旧core61–99的PRE认证、五保留点几何、22 typed/原ID、P0/κ/ledger/FS、signed dterror、实际scalar+=dt、plane与末覆盖检查逐字保留。builder生成diff、三锚点逆归一化全等证明及61–99局部字面一致记录。只链接原同六utility对象和一个新main，无JSph/solver对象。

新程序 `outputs/upl_c08_asn4_partial_r1_build/C08ASN4Partial_win64.exe` 的固定CLI为：

```text
--read psi0 GPU DATA PRE 4264000 66 1 ORIGINAL90PLAN FRESHOUT
```

薄adapter只另扫66个头，严格AS `.2f/4.f`、ReleaseOnly/Active、CompletedOnly两试验key缺席、KeepBedOverlap/五ID/退役255。数组只有core一次读取，源真实r2GPU Part1000只Load一次。原BIO/PRE认证数据不改。导出typed22.bin的真实检查输出头为6805/22/66，**不把原BI4头、原90行plan或300/90旧导出重写为66**。

运行wrapper优先消费原owner admission的真实program/build/source/PRE/input/seed/原plan绑定，并与失败run/start/call的原PID创建时间、parent、exe、argv及Win32出口交叉核对。原失败exit1与本次独立reader期望exit0分开记录，不能把失败run当reader工具失败或正常完成。核原异常/最后原始PART行、66文件、无活动同target/reader/数据消费者及既有解码后，才允许一次读取；拒任何既有正常/partial输出、call或check，不停止、不重试。无SHA。

新输出为原失败job内 `outputs/upl_c08_asn4_window_GPU_r1/native_partial_r1`；检查为 `logs/upl_c08_asn4_window_GPU_r1.native_partial_r1.json`。成功仅指66个已保存状态的原门通过：330000 ledger/κ/ρ缓存、119130 fixed、449130 P0、660000 plane、66 signed区间；正常Run.csv未检查且不存在。completion明确partial=true/runtime_success_claimed=false，completed_steps/new_updates仅计至最后已保存状态。`source_run`继续绑定passed=false原运行；物理验收、未保存状态重构均false。比较绘图需另行授权，不能用原90分析硬读。

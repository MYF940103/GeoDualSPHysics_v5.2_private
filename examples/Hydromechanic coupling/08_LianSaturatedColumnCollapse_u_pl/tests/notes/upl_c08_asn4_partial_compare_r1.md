# n4失败保存态与n3真实前66帧的离线对照

仅新增同名Python和本说明，事前已确认不存在且未跟踪；从已提交90帧 `upl_c08_asn4_compare_r1.py` 最小派生，不修改原文件。作者只做AST/静态接口检查，不执行、import、读取typed/BI4或启动任何工具。

根全文审阅后单次执行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_asn4_partial_compare_r1.py --execution-authorized
```

新 `load_n4` 明确要求原 `JOB.run.json` 为真实solver exit1/未完整完成，以及 `JOB.native_partial_r1.json` 对66个**已保存**状态独立检查成功；不要求、不制作正常Run.csv。消费其completion/metadata绑定的 `outputs/upl_c08_asn4_window_GPU_r1/native_partial_r1`，严格66/6805/22、AS .2f/4f、CompletedOnly、保留5床点和原数值覆盖：330000 ledger/κ/ρ缓存、119130 fixed、449130 P0、660000 plane及66 signed区间。原90行计划/4360000的剩余部分未完成；reported failure step4265004只作原日志描述，不当保存态或计算失败时间。

n3仍由根r6真实已完成300帧/post收据定位，原300头不动，只顺序读前66。n4为真实66输出头。每组所需payload各顺序读一次，沿用原 `c.inspect/quantities`、`cluster.measures/summarize`、固定ID5944/5945/7017/6814、6805完整ID/22有限字段、实际time/tau/Step逐条精确匹配和P0全字段bits门。原90版科学计算与图表逻辑不改，只有载入失败scope、循环/header/覆盖数量及形态布局缩为3时刻。

新浅前缀 `tests/figures/upl_c08_asn4_partial_compare_r1_*` 输出原相同三类PNG和五份CSV：overview整体p/J/n/k/κ/速度/总应力/前缘/真实PRE平均沉降；spacing_material邻距近对与固定材料轨迹；morphology两组实际part49/57/65（约τ=.50/.58/.66）的原5000粒子κ散点及固定边界。去除不存在的.8/.9，仍共享实际全范围色标/物理坐标窗口，不插值、滤波或时间拟合。固定点位移是各自第一保存态τ≈.01基准，非PRE/t0；全域平均沉降仍取原native真实PRE基准history。

检查写 `logs/upl_c08_asn4_partial_compare_r1.check.json`，拒绝任何既有派生产物；必要stat结束复核，无SHA。source失败与分析成功明确区分，`n4_runtime_success=false`、`physical_acceptance=false`。这是参数响应，非半步/5Pa/论文精度验收；最近邻/压缩proxy不证明张拉根因或解决，0.01s保存峰也不等于稠密观测峰。无新的solver/native/VTK/其他ψ或自动重试。

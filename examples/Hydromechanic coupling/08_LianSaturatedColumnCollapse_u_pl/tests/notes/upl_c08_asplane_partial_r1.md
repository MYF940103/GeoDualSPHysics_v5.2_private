# AS＋固定平面53帧失败窗口的原生诊断

本组只读 `upl_c08_asplane_window_GPU_r1` 已保存的 Part0000–0052，最后保存 completed4212000 / saved Step4211999；实际时间由 BI4 读取，不由 console10.53代替。原求解器真实退出1，stage0/native828/step4212817 的 MLS错误是未保存阶段报告，不能重构该故障状态。没有正常 Run.csv 也不能伪造成功运行。

工具新增三个文件，未执行：`support/upl_c08_asplane_partial_r1.cpp` 为逐帧 AS 元数据薄适配器；`_build.py` 从冻结的 `upl_c08_plane_partial_r1.cpp` 在新 builddir 机械生成 core；`_run.py` 消费 `logs/upl_c08_asplane_failure_audit_r1.json`、原 run/call/start/status、实际 call 指定 admission 和全部53个 PART 的 stat。无 SHA、无 solver、无 queue。

派生 core 仅变更54→53的目标作用域、4216000→4212000、最后 saved Step4215999→4211999和新 stage；保存实际 unified diff、baseline/generated/diff stat。原60行启动计划仍完整检查为 `Planned(plan,60,4240000)`，只消费其真实前53行，不能写成53行计划。22数组、6800 IDs、P0、κ、ledger、FS、真实 scalar clock、signed dterror 和固定平面4e−8m几何门均不变。链接只有六个已封口 Release utility objects 加自身 main。

AS薄适配器只经 LoadFilePart 的 lazy结构读取53次元数据，不调用 GetArray/GetDataCopy；每帧须 typed ReleaseOnly / Active=true / float(.2) / float(2.55)。只有 core 执行一次22数组解码。其 completion stage 是 `upl_c08_asplane_partial_r1`，AS_metadata.json stage 是 `upl_c08_asplane_partial_r1.AS`；二者保留 diagnostic_partial=true、runtime_success_claimed=false、physical_acceptance=false。

经根全文审核后，分别单次执行：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_asplane_partial_r1_build.py --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_asplane_partial_r1_run.py --execution-authorized
```

输出独立 `tests/outputs/upl_c08_asplane_partial_r1`，检查为同名 `tests/logs/*.check.json`；已有或部分输出、活动同程序、已有 decode 时拒绝。失败只保留诊断，不自动重读或重跑。后续 AS0/AS1 是不同算子的描述性对照，不是半步门、理论验收或反力/J/Darcy闭合证明。

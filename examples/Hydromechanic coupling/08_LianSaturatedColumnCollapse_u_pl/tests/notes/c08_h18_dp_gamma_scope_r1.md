# 塑性HG返回因子：已有真实单步的数据范围

2026-11-15。仅离线读取已有 `c08_h18_as03_step_r1_p38` 与 `_p76` 的已封存 `material_shadow.csv`，各10000行。读取前核原组件check、真实call出口和CSV seal，读取后stat不变；没有再次求解、调用材料函数或推进一步。

原组件已将同函数shadow的六应力/历史提交与实际CPU单步逐位匹配，status标签来自shadow，不能改称原程序额外插桩观测的status。它们是已有CPU保存态的一步，不是原GPU完整历程或当前待建HG的输入认证。

|源Part|half/full各阶段|Elastic|Smooth|TensionRepair|Apex|
|---|---|---:|---:|---:|---:|
|38|各5000土材料|3817|1125|58|0|
|76|各5000土材料|2345|2480|175|0|

对每行实际 `q_trial>0` 才计算 `q_committed/q_trial`，未裁剪、未用epsilon分母、未由kappa代算。本次20000行的q_trial均非零；没有负、非有限或大于1的比率。

- Elastic均为1。
- TensionRepair均为0，并有非零lambda_tension。
- P38 Smooth：half最小 .0210245310、full最小 .00730306975；最大分别 .9999994370、.9999988803。
- P76 Smooth：half最小 .3179751327、full最小 .1893549276；最大分别 .9999998780、.9999997637。

这支持未来制造场包含非均匀的0/1权重，**不证明**任意DP返回都可直接使用该标量。该比率是偏应力范数的割线比例，不是完整一致切线，也不重现张拉修复的全部方向变化。纯静水q_trial=0、Apex、其他状态以及失败路径在本数据中没有覆盖；必须按真正同阶段Result另作明确定义，不能拿此表补齐。

当前没有向CPU/GPU ReturnMaterial接口接入gamma，也没有删除原HG塑性/转动/秩/时步门。首个HG代数组件只用预设权重；其冻结半正定证明也不能替代历史卸载、变权重、邻域和Darcy反馈的资格。统计在 `logs/c08_h18_dp_gamma_scope_r1.check.json`，原20000行和所有PRE/native/程序归档原位保护。

# 速度一步映射的纯离线结果审阅（作者稿）

本说明生成时脚本尚未执行。只新增 `support/upl_c08_velocity_stepmap_review_r1.py` 和本说明，不改已完成组件或任何输入/输出。根全文审后单次运行：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_velocity_stepmap_review_r1.py --execution-authorized
```

只消费已 passed 的 `upl_c08_velocity_stepmap_r1.check.json`、completion、maps/pre_yield/differences/consistency CSV 及其绑定，复用原 native/初始化守卫，不再次读取 typed22/BI4、不调用组件、solver、reader、build、VTK 或 queue。输出新 `logs/upl_c08_velocity_stepmap_review_r1.check.json` 与 `figures/upl_c08_velocity_stepmap_review_r1_extrema.csv`（4个扰动各一行），已存在或 partial 结果均不覆盖。五个点及多量纲字段更适合小表，本轮不另画复杂图。

从5行摘要复核 `(Qp+Qv+Qsigma)/实际float输入Qv` 及平方根；从一致性表复核幅度方向差的相对范数，最多8个 binary64 ulp 仅用于这些已导出标量的少量加减乘除/sqrt读回运算。它不是生产误差预算或物理通过门，也不重新从 native 积分5000权重。各扰动20,000行只用于实际 δp、δv模、完整3D δσ Frobenius模/trace、δJ、δκ、位置差、原/扰动 T 和 δT、float 输入速度与缩放误差的最大值及 ID，保留 FS 变化/κ差异 ID数及端点贴面变化。Frobenius 含 yy，非对角项乘2；不把端点 membership 当投影 hit、反力或耗散闭合。

PRE 表另汇总实际源 scalar clock、law2评估的实际float-radian材料与 DP fit、5000 κ范围、double六有效应力范围、I/q/f、p/P0/J范围、fmax/ID 与 `f>=1e−5` 数量。这里只核摘要代数一致，f大小不是验收门。旧 law1 认证源κ0与当前 κ0屈服面观测，不证明历史未保存 trial、10s静力平衡或旧程序每步均满足新返回路径。

源仍为真实 total-AS/n3、Shepard OFF、CompletedOnly、keep5/fixed-plane 的 causal90 part71，实际 τ≈.72s；与失败 Shepard/n4态分开。该组件是同一保存态附近全土粒速度缩放方向的5条独立CPU一步轨迹，h固定2.5μs、总5次更新/10 force。Qv使用实际float扰动；一致性使用名义η，实际输入量化方向误差另报。接近1的范数比或当前方向未放大不证明任意扰动/全轨迹稳定，不是互易性、总能量定理、稳定谱、GPU精确重启/重放或团聚根因；`physical_acceptance=false`。

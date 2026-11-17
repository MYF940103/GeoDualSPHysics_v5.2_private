# P1 2s 顶部误差来源小表算术审查 r1

作者稿；尚未执行。仅新增 `tests/support/upl_tpi_p1_error_sources_r1.py` 和本说明，不改任何既有脚本/输入/结果，不解码或启动 solver。

## 输入与选择

只读现有 `figures/upl_tpi_p1_loadclock_window_review_r1.history.csv/profiles.csv/targets.csv`、旧 causal 的 `history.csv/targets.csv/metrics.json` 以及这两次科学 check.json。没有 raw BI4、native binary、ledger、大 layers CSV 或 A 大表输入。标准库即可执行，不需要 NumPy，也不调用旧 main。

主三组是 A finite-Kw、原 B10 M0、staged-load B10 M0；每组选择四个真实状态，共 12 行：

- 真正 preopen：A completed1600、B completed1000；保持各自实际 scalar 时刻。
- 各自最接近 .15s 的真实保存态，明示仅 nearest 描述，不插值。
- legacy Tv=.005/.05 对应的各自原最近保存态，与既有 profiles/targets 绑定。

新/旧 B 在这四点仍要求真实 time bits/step 相同。A/原 B10 的关键沉降和积分量逐项与旧 causal 小表相同；不重新计算旧 A 历史。没有新 half/reference/全程或额外物理测试。

## 分解和参照

由已保存的固定材料顶/底十点沉降得到：

`top_error = bottom_error + native_span - reference_span`。

进一步保持原 Mc、材料中心梯形权重（内层 .01m、两端 .005m，总跨度 .99m），拆成：

`top_error = bottom_translation + (native_span-J_integral) + (J_integral-stress_pressure_integral) + total_stress_integral_bias + pressure_integral_bias + reference_quadrature_residual`。

实际 total/pressure/J 积分直接取既有 history 的原诊断字段。参考总压应力为原 q0 的均匀压缩；参考压力积分由原 H=1m/512 模态计算。正 pressure_integral_bias_mm 表示模拟压力积分低于其参考，在该小应变分解中增加压缩；另以 Pa·m 给出实际减参考的压力积分和总压缩应力积分。不能仅由正负项断言某个离散项必然有误。

近 .15s 和两个排水 targets：A 用原 finite-Kw 容量，两个 B 用 M0，在各自真实时刻求原未拟合伴随解；100 个原 z0 从既有 profile 读取。两个 target 同时复核其现存 pressure/settlement 参考和实际 pressure 剖面积分，防止公式/字段/时刻误接。

preopen 仍未开排水，**不用排水级数在 tau=0 的有限截断冒充闭边界真解**。该行另列理想 uniform undrained end-load 伴随：A `p=capacity*q0`，B `p=q0`，对应线性弹性沉降；它不是有限 ramp、惯性和核带外载过程的动态真值。原 q0/H/Cv/起点/时钟均不拟合，也不把载荷重新归一化来逼近模拟。

材料中心梯形不是外表面完整积分，J-1 也只是体积小应变诊断。因此 `native-J`、`J-stress/pressure` 分项只区分可观测残差，不是精确的应变、质量、能量或外力守恒证书，更不是单独的因果证明。

浮点算术闭合误差要求 <=5e-12mm，target 原参考复算采用2e-8Pa/2e-10mm的算术对接尺度；这些是小表算术一致性检查，不是放宽或新增物理误差预算。原 target 通过/失败记录完整保留，不重新判为物理成功。

## 独立一次执行与产品

入口：`D:/anaconda3/python.exe -B tests/support/upl_tpi_p1_error_sources_r1.py --admission PATH --execution-authorized`。根须先完整审阅；admission `stage=upl_tpi_p1_error_sources_r1.admission, passed=true, small_tables_only=true`，inputs 去重绑定实际消费的 10 个 stat（脚本、本说明和 FILES 的八份既有小表/检查）。

只有一次根准入后的算术执行。新生成 `notes/upl_tpi_p1_error_sources_r1_result.md`，嵌入12行分解表；完整未圆整数值、四点新减旧分项、原预算状态及消费 stat 存于 `logs/upl_tpi_p1_error_sources_r1.check.json`。既有/partial 产品拒绝覆盖。不另写 CSV、大表或图，不修改任何输入，不 hash 扫描，不运行 build/native/solver/queue/Git。

`passed/analysis_complete` 只表示算术审查完整；始终 `physical_acceptance=false`、`causal_mechanism_proven=false`。完成后根结合完整结果和先前图表解释主导偏差，再决定下一项因果诊断；本稿不准入完整周期。

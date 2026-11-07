# C08 legacy NoPen：短窗有效性与耦合审计

本次 `upl_c08_nopen_short_r2` 的0.15 s GPU诊断及唯一15帧原生读取均已通过：global4060000，实际末时刻10.150000000421869 s，6800 IDs、22数组及原时钟/FS/P0/κ/J-ledger门均保持；15个保存状态没有土粒z<0。τ≈.11时最低z由OFF的−24.776 mm变为+10.0004 mm，7010的vz由−1.03916变为+.00200283 m/s，全场maxspeed由1.45419降至.450831 m/s。全场孔压RMS为9369.131 Pa，对照9343.723 Pa。完整数值及实际run/native绑定见 [结果记录](upl_c08_nopen_result_r1.md)。这是截断原穿透失稳链的明确短窗证据，不能据此否定结果，也不能据此证明完整耦合或3 s塌陷精度。

## 实际阶段顺序

1. 每个force阶段先重构当前墙J/p/应力/速度与C，计算速度梯度、体积变化率θ、应力率及力。既有NoPen在同一邻居循环另存速度修正到16 B/粒子的临时`NoPenShift`；它不把该修正写进`Ace`。GPU：`JSphGpu_ker.cu:1970–1993,2195–2200`；CPU：`JSphCpu.cpp:2519–2540,2620–2628`。
2. **完成力的Ace先进入完整Darcy率**，之后才进行运动积分。GPU `JSphGpuSingle.cpp:670–687`先汇总力，再调用`ComputeDynamicPorePressureRateGpu`；`JSphGpu.cpp:1828–1836`由该Ace构造墙加速度并计算孔压率。当前NoPen没有显式约束反力/冲量项加入这份Ace。
3. Predictor按原力、θ和孔压率推进半步；GPU predictor接口没有NoPenShift参数（`JSphGpu.cpp:1584–1608`），CPU亦未在predictor施加该投影。随后用半步状态再算force/θ/应力率/Darcy率。
4. Corrector先由原Ace计算自由速度与梯形位移，再用NoPenShift覆盖选中的速度分量，并把该方向位移改成`v_projected*dt`。GPU `JSphGpuSimple_ker.cu:552–573`；CPU `JSphCpu.cpp:3635–3651`。这是已有速度/位移政策，不是直接把z设成10 mm，也不是严格几何gap约束。
5. σ/κ仍按此前force阶段的应力率作材料返回；GPU该计算在投影代码之后（同核`582–600`），CPU在投影之前（`3621–3633`），但两者均**没有因最终投影重新计算应变率**。J继续使用此前θ做显式中点更新，孔压使用此前Darcy率；GPU host `JSphGpu.cpp:1648–1656`，CPU `3713–3714`。J更新公式为`Jnew=Jn+dt*Jhalf*theta_half`（`JSphGpu_ker.cu:1352–1355`、`JSphCpu.cpp:3313–3317`）。

投影后的速度与位置会影响**下一次**邻域、梯度和力，所以不能说它与水力或本构完全无反馈。准确限制是：本步投影引入的额外运动/冲量，没有在同一阶段明确反映到finished Ace、θ和应力率中。原生ledger证明n/V/ρ/k与所保存J代数一致；它没有单独证明该J与投影造成的运动学改变量一致。现22数组也没有保存每步NoPenShift、触发次数、接触反力或投影功，不能从15帧反推其大小或判定误差已可忽略。

## 当前用途及最小后续步骤

本候选可保留为明确标记的`LegacyProjectionDiagnostic / ReactionClosed=false`实验结果；目前不宜直接替换正式u-pl闭合算法，或把三组完整塌陷称为已完成该耦合验证。NoPen对保留左FreeSlip墙及底NoSlip墙的法向均生效，切向政策不变。原AS0/NoPen0弹性PRE仍受保护；目标只在handoff准入中显式承认算子改变，不是通用PART重启。

- **先测缺口大小，不先改整套墙模型：**在后续获准的最小诊断中记录投影前后速度/位移、实际触发和每步等效冲量`m*(v_projected-v_free)`及其做功；同时观察θ/J、σ/κ与Darcy率的局部改变量。不能把`NoPenShift`直接当作相对自由速度的增量，也不能凭“没有穿透”声称反力闭合。
- **若需要一致性实现：**把法向约束作为明确的阶段操作，确定predictor/corrector的接触状态、反力/冲量和功；用于Darcy的finished Ace应对应受约束的固相运动，J/应变/孔压所用阶段运动也应一致。仅在corrector补一次`Δv/dt`到Ace、却不处理其余阶段，仍不足以完成闭合。可以复用当前固定轴平面与既有NoSlip切向政策，无需顺带重构压力、外载、材料或全部mDBC。
- **最小验证范围：**无接触静水/恒定及仿射制造场保持既有精度；单次接近固定床面的受约束运动核对反力、功和impermeable-wall水力闭合，再检验现C08局部前缘的短窗CPU/GPU对应。保留原finite/IDs/ledger/必要步长门，不增加半步长链，不自动延长或启动三组求解。本记录不实施、构建或运行这些步骤。

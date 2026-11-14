# AS03 两个实际单步的离线材料/体积归因 r1

仅新增 `support/c08_h18_as03_step_review_r1.py` 及本说明。作者阶段不执行/import脚本，不构建、运行组件、求解器、native reader、VTK或Git；根线程全文审阅并独立准入后才可执行：

```powershell
D:/anaconda3/python.exe -B tests/support/c08_h18_as03_step_review_r1.py --execution-authorized
```

输入为有效的 `logs/c08_h18_as03_step_r1_p38.check.json`、`p76.check.json` 和各自原绑定 `material_shadow.csv`、`trace_balance.csv`、`balance.csv`、`summary.csv`。只检查这些已完成组件和派生表；不重新读取全部native、不重新验证旧对象或扫描SHA。每态原组件已经做了一次5µs CPU步、两次原force/Darcy，以及之后10000次无反馈同输入材料shadow。此次分析本身推进零步。

真实初始/结束时刻取原completion。Part38的源completed step为2076001，Part76为2152001；各自只增一步。材料half/full的 `stage_width_s` 为2.5/5µs，是原CPU阶段宽度，不是新增GPU保存时刻。源tau、原全局time、source/next completed step必须保留；不得把该CPU诊断连接成两个保存态之间的新GPU轨迹。

## 符号与材料历史

按原 `c08_h18_tension_volume_audit_r1.md`，这里定义

```
Dret = I_trial - I_committed = -return_deltaI_Pa                 [Pa]
return_equivalent_volumetric_strain = Dret/(3K)                   [-]
```

这不是另一个native体积或孔隙率变量。对于当前单独张拉面，理论上 `Dret=9K*lambda_tension`，所以等效小应变体积分量为 `3*lambda_tension`。脚本保留Dret的正负原值，不截断接近零的舍入值，不将该量重复加入J或p。三维/一般非零剪胀角条件下，不能把所有返回trace变化都硬归给张拉面。

状态名称和reason取原build归档的 `FunSoilMaterial.h`。仅Elastic/Smooth/Apex/TensionRepair为已接受状态；名称来自事后同输入、全六应力和历史策略逐bit相符的shadow，不是原物理调用内的状态hook。half按原策略保存κ_n，即使shadow连续返回历史增加也不写入半步历史；full才写其返回float历史。`continuous_positive_but_shadow_float_unchanged`只比较连续κ与shadow float，不把predictor故意保留κ_n误称float丢失。

## 输出、误差与图

新目录 `tests/figures/c08_h18_as03_step_review_r1` 中两图、两CSV，检查为 `tests/logs/c08_h18_as03_step_review_r1.check.json`。已有失败或完整目录/检查均拒绝覆盖。

- `summary.csv` 为紧凑长表：两Part的half/full各状态计数；全5000与TensionRepair子集的Dret、Dret/(3K)、λ_tension、连续/float/实际保存κ增量均值、RMS、最小/最大/最大绝对值及原ID；完整阶段五个trace项的均值/极值/RMS、原closure和原budget；pressure/J closure占原预算比例；实际Δp与cap贡献；全部八个接触位置/速度差的极值及原ID。
- `focus.csv` 每Part四ID4953/4954/6767/6865各一行，共八行；保留其half/full原材料全部列（前缀区分）、状态/reason文字、Dret及等效量、full trace和原pressure/J/contact记录。源时间只对应已经保存的原GPU状态，之后是一个CPU计算增量。
- `summary.png` 显示half/full状态数量、返回等效体积应变均值、完整trace五项RMS，以及一步平均孔压和completed-cap变化。对称对数显示的线性区分别为1e−15/1e−19，仅服务可读性，不参与数值门。
- `focus.png` 显示上述四材料ID的half/full Dret及原p_n、CPU raw full p、completed-cap p；不平滑、不拟合、不删负压或未更新点。

五项使用原CSV定义：

```
logJ_minus_elastic_trace
  = kinematic_log_quadrature
  - rate_trace_minus_3Ktheta_equivalent
  - trial_addition_roundoff_equivalent
  + return_trace_equivalent
```

它们分别是原记录的总失配、运动学log求积、应力率trace与3Kθ差、trial加法舍入及材料返回量。只重核原声明 `abs(closure)<=closure_budget`、原pressure/J及aggregate同类门，不新加物理容限或更宽预算。不以当前两个5µs的均值拟合/积分到0.9或3s。

接触八分量是与未投影速度/位移公式的差，原模型仍 `reaction_closed=false`；不能将差分直接称为闭合接触反力/功。分析建议以实际统计判断张拉面是否在所选AS03形成阶段活动，并与独立storage历史对照。即使出现明显Dret，也不能据此删除张拉返回、改J源项、或认定其解释了全程负压/团聚；两快照各一步仍缺完整历程因果信息。

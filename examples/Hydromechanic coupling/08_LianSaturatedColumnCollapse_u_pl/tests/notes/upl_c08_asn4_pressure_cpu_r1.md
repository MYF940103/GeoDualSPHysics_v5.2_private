# 真实 CPU 近床冻结压力响应（作者稿，未构建/未执行）

仅新增本 note 及同名 `.cpp/_build.py/_run.py`，旧 zeroCPU r1失败、r2通过的程序/输入/CSV/收据不动，无生产源码或公共参数修改。机械继承已通过 r2 的合法 `-svres` 初始化、冻结 bedkeep DebugCPU对象/头文件、真实 PRE 加载/keep5释放、Restore/cell重建、完整force及cleanup、5000主场bit守卫和五项Sum。

范围只为已封口 n4 `native_partial_r1` **part64（τ≈.65，completed4260000）**。沿 r2 原 Select，固定41个土体native IDs及顺序；四个显式focus7013/7015/6963/7014保留。run预检查绑定已通过r2收据与该part的41行，源p必须全小于−32 Pa；CPP再次检查。根已核范围约[−23917.6133,−12632.0537] Pa，±32不跨零；不因此改变负压政策。

同一保存输入、同一几何/J/σ/vel/κ/P0/clock，两指数AS4/AS3各165次真实评估：baseline一次；41列 × h={16,32} Pa × sign={+1,−1}，合计 **330 force/Darcy calls**，2baseline＋328扰动，164个(column,h,AS)双符号组。循环顺序AS4后AS3，每个baseline后按原41 ID顺序、h16再32、+再−。全部5000土参与生产邻居循环；41只是受限压力行/列和输出大小。

每次从原 `Snapshot base` 完整复制，唯一赋值为 `incoming.p[ById[column]]=float(double(base.p[...])+sign*h)`。原P0、FS/θ历史、J、σ、vel、κ及其余保存列不伪改。`SoilUnchanged(incoming)`检查该明确扰动输入的全部5000主场bits；非扰动土p也保持原值。然后真实 `Interaction_Forces(INTERSTEP_SymCorrector)` 重新生成wallState→FS/C→wallC→AS→ct→finished wallAce→Darcy，导出后真实 `PosInteraction_Forces`。不调用积分器/ReturnMaterial/接触投影，0物理步。

两指数各自的baseline保留全部5000实际FSType；328扰动逐个检查全部5000与其baseline一致，共1,640,000比较。saved FS与重算FS差异照实写call，不将它们混为原GPU阶段。真实BoundNormal/Slip/Code仍来自seed＋实际keep5释放；不从FSNormal构造墙。

`calls.csv` 22列/330行，逐call记录实际time/globalstep/AS/column/h/sign、原与扰动后的**float p和uint32 bits**、double(actual−base) δ、全场有限rate/FS变化/主场bits及算术预算比。baseline列ID=−1，列p/bits四字段为空（不适用），h/sign/δ为0。

`rates.csv` 25列/**13,530行**：每call固定41行，实际float pressure rate、实际输入p/J、重算FS/θ/Ace，以及原五项compression/LP/defect/divAce/chain和测试侧sum/传播预算。原Sum函数文本、原k(J)的exp与Eta²均未改；分项按这次实际C/Ace求和，不是手写wallJac。实际墙压力/C/Ace每call正常响应，不能把它们固定后冒称同算子。有限差分后续应使用 `(rate_plus−rate_minus)/(actual_float_p_plus−actual_float_p_minus)`，不盲用名义2h。

本程序只采集两套有限幅响应，**不计算谱、不分析16/32收敛、不按误差筛掉列或私设物理门槛**。run只核绑定、330/41/双符号覆盖、actual float扰动及各行有限/原算术Sum预算。AS正谱分段以及最终float rate量化会影响差分，不能把h16/32差异直接叫物理误差；原Sum预算只证明分项算术一致，不是完整FD导数误差预算。

所得是41土压力自由度、区外**土压力扰动固定为零**的局部条件Jacobian响应；墙不固定而由真实闭合重建。σ/vel/J/κ不演化，没有材料切线、θ的时间反馈、接触投影或全场边界模态，不是full coupled谱、原GPU packed/FMA/未保存半步复演，也不构成物理验收或其他ψ准入。

构建脚本只TAG机械派生r2：同 source_capture/archive 的 bedkeep DebugCPU86非main＋helper=87；匹配归档头与MSVC14.36 /Od /MTd /fp:precise；不用旧mdbcPartition物理对象、不全项目build。保留合法cfg输出标志/argv `-svres` 满足PRE合同，但不调用SaveData，未生成新的物理PART/VTK。

根全文审后才能分别单次调用；当前只作者及AST/文本静态检查：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_asn4_pressure_cpu_r1_build.py --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_asn4_pressure_cpu_r1_run.py --execution-authorized
```

新helper `tests/outputs/upl_c08_asn4_pressure_cpu_r1_helper/component.exe`；新结果 `tests/outputs/upl_c08_asn4_pressure_cpu_r1/{rates,calls}.csv/completion.json`；对应logs `.build.json/.check.json` 及CL/link/run独立typed-handle call。拒已有/部分输出，不覆盖、不重试、不solver/GenCase/native/VTK/队列/SHA。

# C08 Lstar：ψ0 材料与 Lian 2023 的只读交叉核对

2026-11-15。本次只新增本记录；未修改源码、物理参数、输入、原生数据或旧审查，未构建、求解、解码、执行分析或扫描 SHA。结论是没有发现 ψ0 的峰值/残余黏聚力或软化开关错配，不代表返回算法与论文逐步等价，也不把 Lstar 判为物理修复。

## 原文和实际实现

- 原文：`src/papers/u-pw/Lian 2023 u-pl.md`，对应 `src/papers/PDF/Lian 2023 u-pl.pdf`。打印第5页 Eq18，MD262–267：`c=cr+(cp-cr)exp(-η εeqp)`，历史量为累计等效塑性应变。打印第19页 Table1，MD873–878：ψ0 组 φp/φr=25°/25°，cp/cr=5/1 kPa，η=5，ψ0=0°，剪胀衰减 sf 不适用。打印第4页 Eq13（MD231–238）的历史导数含 `sqrt((2/3)*(∂g/∂s):(∂g/∂s))`。
- 实际 baseline 定义：`tests/configs/c08_h18_as03_n255_r1_Def.xml:115–124`；实际生成输入：`tests/outputs/c08_h18_as03_n255_r1/c08_h18_as03_n255_r1.xml:114–123`；同目录 `native_profile.csv` 的17键合同均给出 coh=5000、coh_r=1000、n_coh=5、φ=φr=25、n_phi=0、dlt=0、DilationDecay=0。因此不是常5 kPa模型。
- 实际绑定代码归档：`tests/outputs/c08_preload_schema2_source_r1/full_source.zip` 内 `FunSoilMaterial.h:49–58`，按 `c=1000+4000 exp(-5κ)` 更新，并采用 plane-strain DP 系数。`:105–109` 的光滑径向返回使用 `κ=κold+λ/√3`。对 `g=ξψ I1+sqrt(J2)`，偏应力梯度的平方范数为1/2，因此 Eq13 的对应历史导数为1/√3；ψ0 没有塑性体积应变引出的额外历史歧义。这是公式对应，不是时间离散逐步等价证明。
- 同一归档 `FunSoilMaterial.h:223–234`：只有 trigger=true 时才将峰值黏聚力除以 SoilTriggerFos。实际 native profile 为 `fresh_trigger_active=0`，源原生完成记录也为 false；故虽保留 SoilTriggerFos≈1.65，并未把本组5 kPa暗降为约3.03 kPa。

## 继承与已保存历史

真实绑定入口为 `tests/logs/c08_h18_as03_n255_r1.run.json` 的 input_xml/native_profile/source_native/source_archive/source_capture。源：`tests/outputs/c08_h18_wend_psi0_pre_r2/native_r1/completion.json`，schema2、same_material_plastic_PRE=true、2,000,000步/1001帧，law2合同，不是旧 schema1/弹性重置源。接收：`tests/outputs/c08_h18_as03_n255_r1/native_r1/completion.json`，源/目标 law2，实际91帧、6805 IDs、5000土粒，455000次从PRE起累计κ单调检查；full material contract 由求解器 loader 强制，reader 的 `full_material_contract_independently_reconstructed=false` 限制仍须保留。来源和程序依据既有 run/build/capture 绑定，不冒称只靠读器就证明全部材料实现。

本次读取已通过的 `tests/logs/c08_h18_lstar_window_review_r1.check.json` 及其 `_history.csv`：baseline 末态3847/5000土粒 κ>0，κmax=6.2731747627、κmedian=0.00104313431、κ95=1.5682903826。可见体域中仍有近峰值区，剪带尾部也已基本达到1 kPa残余区。不能把 `c(mean κ)` 称为平均黏聚力，亦不能把累计κ>0直接称为当前正在塑性流动。

Lstar 只改变 LP/Lx 的压力权重，材料实现、PRE及历史合同不变。其末孔压RMS由12.952降至12.418 kPa，同时全窗最小孔压由−58.414降至−74.039 kPa，近邻/团聚未改善；这些事实不支持以材料调参解释或掩盖该候选结果。下一步对称 pair-C/bare 单因素隔离不需要改 cp/cr/η/触发或另做一个PRE。

当前返回采用非线性一致更新，归档 `FunSoilMaterial.h:126–150` 仍有明确的 apex/tension-face 策略；论文 Eq13 的半隐式应力返回不自动等同这些有限步细节。未发现参数错配，不等于已经排除一切本构离散差异。这里不扩展新的本构验证链或物理参数搜索。

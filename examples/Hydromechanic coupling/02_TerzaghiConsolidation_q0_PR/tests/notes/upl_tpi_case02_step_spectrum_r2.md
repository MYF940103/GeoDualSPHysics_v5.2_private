# C02 TPI B nominal谱代数检查 r2：仅修h0检查右式的相消

仅新增 `support/upl_tpi_case02_step_spectrum_r2.py` 和本note。未执行。
完整数学方案、36邻居构造、120模式来源、共同符号限制、物性与原P1 map，均沿用
`notes/upl_tpi_case02_step_spectrum_r1.md`。原r1脚本/note/admission/失败check保持原样，
不把原失败改写为通过，也不调用或重跑旧组件main。

## 与r1的全部脚本差异

1. `TAG`由`upl_tpi_case02_step_spectrum_r1`改为`upl_tpi_case02_step_spectrum_r2`，
   因而note、输出目录、check、准入stage均独立新标签；不覆盖旧路径。
2. 只把h0恒等式checker的右式
   `expected=(1-m)*(P@y)+m*guess`
   写为相同实数恒等式的稳定等价表达：
   `r=rhow/rho; delta=(1-r)*(1-mu); m_stable=mu+r*(1-mu);`
   `expected=delta*(P@y)+m_stable*guess`。

没有修改其他脚本行。特别保留：原完整step函数体、实际float材料/原gamma、
所有120个q与mu的定义、三个dt、360矩阵/1440根、原256eps恒等式预算、
4096eps特征残差预算、全部输出字段及“非actualSPH全谱/非时步准入”的结论范围。
没有新增2tau硬门、论文R、物理拟合、beta/AS/HG或任何调参。

## 已查明的r1首因（不是新增物理观察）

原r1check记录 `P1 h0 pressure-constraint identity differs`，且没有输出目录或物理求解。
根授权的只读单模式表达式复现定位为mode0：
q_eff=1.5598852253535331，mu=.9998570674346052，m=.9999251305609836。
`1-m`为7.486943901635623e-5，而稳定乘积为7.486943901630865e-5；
该约6.36e-13相对消减误差乘上较大的P*y，导致旧左右差1.805240237e-9，
超过原3.230490853e-10预算。四状态map和实数恒等式并没有因此被证明错误。
相同单模式只改稳定右式，原预算不动时左右差约4.687428402e-13。
这些是已完成的单模式诊断数字，不代表新r2全组件已运行或通过。

## 唯一新代数执行

根全读后才能以 `stage=upl_tpi_case02_step_spectrum_r2.admission,passed=true,algebra_only=true`
以及原样的inputs stat规则单次准入。未来输出是
`tests/outputs/upl_tpi_case02_step_spectrum_r2/{neighbors.csv,nominal_modes.csv,matrices.csv,roots.csv,summary.json}`
和`tests/logs/upl_tpi_case02_step_spectrum_r2.check.json`，任一已有/partial仍拒绝。
原r1 note和失败check可以同时放入根准入inputs作历史记录；不会重写或重算它们。

作者仅做静态AST解析和完整文本diff；不import/main、不执行代数矩阵或任何solver、native、
build、hash、Git、half/reference。根审完完整diff再自行决定唯一新执行。

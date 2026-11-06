# Lian材料律与共享radial candidate只读复核

本记录只整理原文和代码含义，不构成材料或空间物理验收；没有新增测试、生产补丁、构建、求解器、Git或SHA操作。

## 原文定义与当前选择

[Lian 2023原PDF](<D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b/src/papers/PDF/Lian 2023 u-pl.pdf>)印刷p4 Eq12–13及p5 Eq14–19已直接看原页；对应[本地MD](<D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b/src/papers/u-pw/Lian 2023 u-pl.md>)232–267行。

- Eq13的等效塑性应变因子使用偏应力导数`∂g0/∂s`。对`q=sqrt(J2)`，该导数的Frobenius范数为`1/sqrt(2)`，所以所选dev历史增量为`Δκ=λ/sqrt(3)`；它不含`3β`的塑性体积部分。塑性体变仍由流动势决定，不能把两种历史范数当作精度等价替换。
- Eq18为`c=cr+(cp-cr)exp(-ηκ)`；Eq19为`ψ=ψ0 exp(-sf κ)`。`sf`独立于黏聚力的`n_coh`：现有`n_coh`映射η，不能拿它代替sf。`n_phi`控制摩擦角软化；当前共享核只覆盖固定φ，未实现一般摩擦软化。
- Table1（印刷p19）中φp=φr=25°，cr=1kPa、η=5；ψ0分别0/+2.5/−5°，对应cp=5/5/7.5kPa；sf为N/A/.2/.2。ψ0=0时sf对ψ没有作用。材料参数继续float，角度在共享核中为float弧度。

[共享candidate](../support/upl_material_shared_candidate_r1.h)采用连续endpoint `κ=κold+λ/sqrt(3)`评价c和ψ，并求解

`F(λ)=qtrial-Gλ+α[Itrial-9Kβ(κ)λ]-kc(κ)=0`。

因此`Fλ=-G-9Kα(β+λ βκ/sqrt(3))+fκ/sqrt(3)`，其中固定φ时`fκ=-dkc/dκ>=0`；代码的正一致性量为`-Fλ`。`βκ=(-sf ψ)*9 sec²ψ/(9+12 tan²ψ)^(3/2)`符号一致。

这是与所声明材料律一致的**所选隐式endpoint返回算法**，不是已证明逐字复现论文Eq13半隐式算法。原页Eq13显示的分母符号约定与上述直接求导应分开表述，本记录不把印刷式裁定成笔误。静态点对照只能检验所选核的数学/实现一致性，不能代替空间收敛、材料标定或崩塌验证。

## 已有代码边界

[JSph.cpp](<D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b/src/source/JSph.cpp>)3765–3784行读取dlt/n_coh/n_phi，并据软化参数设置`StrainSoftening`；当前没有把n_coh当sf。旧[CPU UpdateDPvars](<D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b/src/source/JSphCpu.cpp:3801>)和GPU对应函数只直接使用传入ψ，未实现Eq19的独立sf。

当前dynamic容器仍要求InitNone且拒绝StrainSoftening（JSph.cpp:616、3626–3629；JSphCpu.cpp:4463；JSphGpu.cpp:1750–1754），CPU corrector还拒绝非零κ（JSphCpu.cpp:4671）。共享核没有修改这些限制。以后接入时应保留旧fast默认，使用独立材料selector，并令`ApexNeeded`、非正一致性或未收敛明确停止；不得无声套用旧cap或elastic fallback。float保存κ造成的历史小增量丢失及saved-κ屈服残差，仍须与连续root残差分开报告。

## 以后可选的最小空间检查

若另行完成并审阅radial selector及窄准入，可考虑**一个小型零重力、轴向周期、平滑初速度剪切波patch**：fresh σ/p/κ=0，固定φ、ψ0=0、cp5/cr1/η5，有限更新数；使用真正周期平滑速度，不用跨周期跳变的affine速度。它避免重力预平衡与墙/自由渗流解释负担，可观察真实force→Pre/Cor→κ commit的radial塑性；任何apex/非正一致性仍停止，不预先保证不会出现。具体输入、步数与预算尚未作者或准入。

该建议不是当前阶段阻塞项，也不是C08撤墙/塑性崩塌验收；正负ψ、变量k、负压稳定、预应力与撤墙仍各有后续物理问题，不能由共享核可用性自动解锁。

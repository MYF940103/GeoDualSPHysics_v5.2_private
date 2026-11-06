# 实验材料返回接口 r1

2026-11-06。实验接口及已验证范围；不修改既有正式案例XML/BAT。两端Debug构建、已定义的Pre/Cor调用、默认回归及GPU显式开关弹性启动已通过，详见[接线审查](upl_material_integration_root_r1.md)；不构成空间塑性或塌陷验收。

位置为`case/execution/special/soils`，角度仍按既有XML格式输入degrees、内部保存float弧度：

```xml
<MaterialReturn value="0" comment="0=LegacyFast (default), 1=experimental ConsistentDev" />
<DilationDecay value="0" comment="Independent dilation softening sf>=0; nonzero requires mode1" />
```

- `MaterialReturn=0`为省略时默认值，要求保留旧fast分支原算术；不从Hydro或dynamic开关推断材料选择。本记录不声称生产默认路径回归已经完成。
- `MaterialReturn=1`为显式实验选择，要求fresh二维DP_PS、Symplectic、固定摩擦角（`n_phi=0`）、有限正K/G、有效固定φ、有限`coh>=coh_r>=0`与`n_coh>=0`，以及有限`|dlt|<90°`。不开放一般MC/3D、摩擦角演化或PART重启。
- `DilationDecay`为独立、有限、非负sf，内部`StSoilCte::psiDecay`仍为float。非零sf要求mode1；mode0加非零sf必须拒绝。sf0为恒定ψ，正sf按连续endpoint κ评价`ψ=ψ0 exp(-sf κ)`。它不是`n_coh`，不能把论文sf=.2填成黏聚力软化η=5，亦不增加孔压源项。

ConsistentDev采用`Δκ=λ/sqrt(3)`、endpoint黏聚力与ψ的局部一致返回。系数、求根及张量临时运算为double；材料常数和持久κ保持float，不新增全double材料数组。连续root残差与最终float κ的屈服残差不同，必须分开报告。它是与所声明材料律一致的endpoint数值选择，不宣称逐字复现论文Eq13，定义依据见 [材料律审查](upl_material_law_review_r1.md)。

独立CPU/CUDA共享核各71点已真实执行：18 Elastic、36 Radial、12 ApexNeeded、5 Invalid，以及6个常强度闭式控制；该集合没有自然NonConverged见证。GPU内存检查零错误、零泄漏，同输入应力/连续κ/λ/保存κ差为0。见 [封口材料点记录](upl_material_shared_root_r1.md)。这些结果不等于生产caller、空间离散、真实时间积分、材料标定或物理通过。

生产适配必须按张量成员映射，不混用native/POD布局；保持predictor恢复旧κ、corrector提交新κ的原顺序。ApexNeeded、无效输入、非正局部一致性或未收敛应明确失败并报告阶段及状态掩码；当前没有逐粒子错误ID。不得偷偷调用旧cap、弹性fallback或夹取参数。局部返回失败不提交该材料结果，但整阶段不提供事务回滚，不能将失败阶段的部分数组当成有效续算初态。

当前dynamic容器的软化及非零κ限制仍关闭。材料开关独立并不等于可与所有Hydro组合；本接口不自动准入塑性u-pl、C08重力预平衡、变量k、负压稳定、撤墙或崩塌，也不修改任何原dt/J/有限性/域保护。上述构建、实际调用与默认兼容检查已完成；下一步为有界的常强度周期塑性短程验证，不新增半步链。

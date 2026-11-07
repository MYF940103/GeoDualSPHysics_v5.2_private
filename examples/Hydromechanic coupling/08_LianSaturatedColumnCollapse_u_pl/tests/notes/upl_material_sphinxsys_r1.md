# SPHinXsys 土体材料实现核查（只读，2026-11-07）

固定官方节点：`Xiangyu-Hu/SPHinXsys@1612330e44c8947406f24b6756449e80dcd7158e`。通过 GitHub 只读工具读取真实源码；本次仅新增这份说明，没有复制实现、修改生产、构建或运行。不能把未来变化的主分支名称当成此次固定证据。

结论：这个节点确有二维黏性土破坏和三维休止角算例，但其 `PlasticContinuum` 采用**应力率塑性减项＋Bui 型 trace 修正/偏应力比例缩放**，不是已解决变φ/c/ψ、累计κ与一致 apex 的完整隐式返回。它适合借鉴 SPH 组织、边界与稳定技术；不能直接作为我们统一 DP 材料算法的全域真值。

## 实际调用链

| 固定源码 | 已核实的行为 |
|---|---|
| [cohesive_soil_failure.cpp:20–54](https://github.com/Xiangyu-Hu/SPHinXsys/blob/1612330e44c8947406f24b6756449e80dcd7158e/tests/2d_examples/test_2d_cohesive_soil_failure/cohesive_soil_failure.cpp#L20-L54) | 土体确实实例化 `PlasticContinuum`，调用两段 PlasticIntegration；并开启密度求和、应力扩散、表面识别、输运速度位置修正及梯度修正。 |
| [continuum_integration.hpp:175–186](https://github.com/Xiangyu-Hu/SPHinXsys/blob/1612330e44c8947406f24b6756449e80dcd7158e/src/shared/particle_dynamics/continuum_dynamics/continuum_integration.hpp#L175-L186) | 从速度梯度求塑性应力率，将其乘 dt 累加到应力，然后显式调用 ReturnMapping；总应变另行积分。 |
| [general_continuum.cpp:65–86](https://github.com/Xiangyu-Hu/SPHinXsys/blob/1612330e44c8947406f24b6756449e80dcd7158e/src/shared/materials/general_continuum.cpp#L65-L86) | 基于应变率与旋转率形成弹性客观应力率，若当前 f 超过小阈值，则减去用当前应力计算的非关联塑性率。此段不是求解新κ下隐式一致方程。 |
| [general_continuum.cpp:89–103](https://github.com/Xiangyu-Hu/SPHinXsys/blob/1612330e44c8947406f24b6756449e80dcd7158e/src/shared/materials/general_continuum.cpp#L89-L103) | 首先将超顶点的 trace 平移到 kc/α，再保留 trace 对偏应力进行比例缩放。没有 apex 乘子/次梯度/κ分支，也没有独立张拉屈服面的活动集。 |
| [general_continuum.hpp:60–104](https://github.com/Xiangyu-Hu/SPHinXsys/blob/1612330e44c8947406f24b6756449e80dcd7158e/src/shared/materials/general_continuum.hpp#L60-L104) | 计算 kernel 路径同样采用上述率形式与两步应力修复；部分 q 分母加 TinyReal，不等于补齐严格 apex 物理闭合。 |

## 系数、剪胀、软化与κ

[PlasticContinuum 的声明](https://github.com/Xiangyu-Hu/SPHinXsys/blob/1612330e44c8947406f24b6756449e80dcd7158e/src/shared/materials/general_continuum.h#L86-L124)保存常数 c、φ、ψ，ψ默认0；应力维数固定为3。其[系数函数](https://github.com/Xiangyu-Hu/SPHinXsys/blob/1612330e44c8947406f24b6756449e80dcd7158e/src/shared/materials/general_continuum.cpp#L45-L63)使用

\[
\alpha=\tan\phi/\sqrt{9+12\tan^2\phi},\quad k_c=3c/\sqrt{9+12\tan^2\phi},
\]

即本项目 PS 系数；塑性势系数通过同一函数作用于 ψ。此类及上述算例路径没有 φ/c 指数软化、ψ 随κ衰减、κ反馈强度的实现。相同文件中的 `J2Plasticity` 具有另外的硬化/损伤功能，不能混作 DP 土体已有这些能力的证据。

名字为 `AccDeviatoricPlasticStrain` 的量，[实际计算](https://github.com/Xiangyu-Hu/SPHinXsys/blob/1612330e44c8947406f24b6756449e80dcd7158e/src/shared/particle_dynamics/continuum_dynamics/continuum_dynamics_variable.cpp#L36-L54)是从**当前总应变−弹性应变**反算一个塑性应变张量，再取其偏量范数。它没有逐步累加每次偏塑性增量，也未在此材料类中参与强度更新。一般非比例加载下，当前塑性张量的范数不等于我们累计的 `κold+√(2/3 Δepdev:Δepdev)`。

另外，该派生量代码把三维张量的 trace 用空间 `Dimensions` 做偏量扣除，二维编译时是1/2而非三维嵌入应力应使用的1/3；其体积弹性应变系数也应按实际 p/I 定义进一步核对。这里仅标为需审计之处，未运行验证、更没有将其当作本项目κ参考。

## 顶点及三维范围

- ReturnMapping 的 trace 上限和缩放，与本地 Bui 2008 的两步修复相似；不能据此认为它实现了我们所需的 `κA=κold+qtr/(√3G)`、apex λ可行条件或塑性功一致性。
- 经典应力率路径在 q=0 且 f>阈值时仍含除 q 项；kernel 路径加入小量只处理部分除零。未经单点验证，不应将这类实现作为静水张拉/负剪胀顶点的鲁棒真值。
- 官方[三维休止角算例](https://github.com/Xiangyu-Hu/SPHinXsys/blob/1612330e44c8947406f24b6756449e80dcd7158e/tests/3d_examples/test_3d_repose_angle/repose_angle.cpp#L87-L89)确实使用同一个 PlasticContinuum，且[调用相同积分器](https://github.com/Xiangyu-Hu/SPHinXsys/blob/1612330e44c8947406f24b6756449e80dcd7158e/tests/3d_examples/test_3d_repose_angle/repose_angle.cpp#L161-L164)。因此不能说它“没有三维粒子或三维张量支持”。但这里仍是同一组 PS 拟合系数，没有本项目 DP_C/DP_MC 的独立三维 MC 映射分支；这不是我们三种系数映射和软化导数已验证的替代证据。

## 与当前 C08 的可比性

这个二维例子给定 E=1.8MPa、ν=.3、ρ=1850、c=5kPa、φ=25°，ψ用默认0；它是单相土体例子，不含本项目 u-pl 的孔压、J/n/k耦合。它还[直接赋初始应力](https://github.com/Xiangyu-Hu/SPHinXsys/blob/1612330e44c8947406f24b6756449e80dcd7158e/tests/2d_examples/test_2d_cohesive_soil_failure/cohesive_soil_failure.h#L65-L84)，没有我们的真实10s重力预载；不能把两者出图相似度当作预载/饱和塌陷材料验收。

优先可借鉴：清楚划分 constitutive rate 与应力修复、内邻域/墙接触积分、位置输运修正与表面投影、单点材料测试和算例组织。移植任何一项仍需独立检查守恒、边界和历史一致性，不应整体替换当前已验收的水土耦合路径。

## 许可与证据范围

该固定节点的[LICENSE](https://github.com/Xiangyu-Hu/SPHinXsys/blob/1612330e44c8947406f24b6756449e80dcd7158e/LICENSE)是 Apache-2.0。本次只做数学与流程分析，不复制实现；未来若实际采用代码，仍需保留相应许可、归属及修改说明，检查涉及的独立第三方文件。未读取/运行整个库的所有材料模型，结论严格限于以上固定节点、PlasticContinuum 及所列二维/三维土体路径。

关键文件 blob（GitHub 返回身份，非本地反复哈希扫描）：
- general_continuum.cpp：`1e6c066e2cf9f8cbf9e57870f1d078e3c3d43baf`
- general_continuum.h：`02363be87b60595d99bde4579b99abe7d71c71cf`
- general_continuum.hpp：`c4655fb980099d5f87df5f88b2f691a59257f789`
- continuum_integration.hpp：`37ba0411295a245fdeac71233ba50ce2759f6524`
- continuum_dynamics_variable.cpp：`3d3875b7293de8c243c8986588e821e35cae6e16`

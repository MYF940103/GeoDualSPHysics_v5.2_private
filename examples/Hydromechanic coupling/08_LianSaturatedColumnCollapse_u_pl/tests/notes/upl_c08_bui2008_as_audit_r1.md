# Bui 人工应力：原文与当前 CPU/CUDA 的只读核对

范围：读取 Hydro AGENTS、原 PDF/同名 MD、`src/papers/bui2008_elastoplastic_sph_implementation_notes.md`、当前实算源码和既有 AS unit 收据。只新增本 note 及 `tests/outputs/upl_c08_as_paper_r1/` 十一张原文页 PNG；没有修改源/输入/旧证据，没有构建、求解、解码或扫描旧哈希。原文页均已视觉检查。结论：当前获准 C08 路径未发现可确认的 AS 符号、张量槽位、重复密度归一化或准备时序错误；参数和耦合稳定性仍有明确未证范围。

## 文献原式与参数

本地原始 PDF 位于 `src/papers/PDF/`；以下页码为打印页码，非 PDF 零基索引。

| 文献 | 原式与可确认含义 |
|---|---|
| Bui et al. 2008, *Lagrangian meshfree particles method (SPH) for large deformation and failure flows of geomaterial*, pp.1552–1553 | Eq.(63): 在动量式加入 `Σ m_j f_ij^n (R_i+R_j)∇_iW`。Eq.(64): `f_ij=W(r_ij,h)/W(dp,h)`，分母用初始粒距；固定 h 时为常量。Eq.(69): 对拉伸为正的每个主应力，`R'_a=−ε σ'_a/ρ²` if `σ'_a>0`，否则零。Eq.(65)–(71) 将主轴张量旋回参考坐标。 |
| 同文 p.1563（对应 Fig.8 参数试验的讨论） | Cubic、h=1.2dp 条件下，作者推荐 ε=.5、n=2.55；ε=.3 仅减弱其试验的断裂，.5/.7 消除。n=4 在该组弹塑性算例会导致过强排斥。ε 是强度系数，n 是距离增强指数；不是物理黏性或耗散系数。 |
| Bui et al. 2011, *Slope stability analysis and discontinuous slope failure simulation…*, p.566 Eq.(4)–(6) | 稳定项含 AV 和 AS，AS 沿用 2008；该文改变的是 AV 声速计算。此页明确应力压缩取负，且其孔压符号约定不能未经转换直接移植到当前正压水压变量。 |
| Bui & Nguyen 2021（本地 `Bui 2021-CG.pdf`）, pp.25–26 Eq.(116)–(119) | 重述核比、主轴 AS 和旋回流程，ε=.5/n≈2.55 针对 Cubic、h=1.2dp；不同核/影响域需独立参数研究。说明谱流程原则上可用于 2D/3D；各向同性 artificial pressure 是不同且可能较弱的替代项，不能与完整人工应力混称。 |
| Lian et al. 2023（本地 `Lian 2023 u-pl.pdf`）, p.6 Eq.(26) | 混合物动量明确使用 total stress 及 `V_j/ρ_i^t` 型权重，稳定项含 AV/AS，引用 2008/2013 的形式与推荐参数；正文未在此给出另一套完整展开的 u-pl AS 密度变换公式。 |
| 同文 p.11 §3.5.3 Eq.(47) | 另有针对塑性剪胀负孔压增长的稳定式，β=.04，作者要求按三轴试验校准，且仅用于塑性变形。它不是 ε 或 n，也不是 AS。p.5 Eq.(19) 是 `ψ=ψ0 exp(−sf εp_eq)`，不是负孔压截断/人工应力式。 |

**Lian 的数值归属**：全文未见 AS ε=.2 或独立 n=2.55 的显式赋值；p.6 以沿用 [11]/[18] 的推荐参数建立引用链，支持回查 Bui2008 的 .5/2.55，但不能改述成 Lian 逐字写了 ε=.5。p.19 Table 1 的“Stabilisation coefficient α=.5”对应 p.8 Eq.(38)–(39) 的 TPI 中间压力外推系数；不是 AS ε。表中的 sf=.2 是 ψ 衰减系数。当前 AS ε=.2 来自本仓库 `JSph.cpp` 默认值，不能借这两项 .5/.2 当作论文直接依据。

两点不能从纸文机械照抄：(1) 2008 原 PDF Eq.(66) 的第二项确实重复印为 R′xx；标准旋回应使用另一个主值 R′yy。当前谱分解重构没有照抄该排版错误。(2) 2021 Eq.(117) 使用 Macaulay 简写，其邻近负压/负应力叙述存在符号约定歧义；当前代码的可核依据是 2008 Eq.(69) 明确的条件式，而非仅凭简写负号判断正误。2008 p.1552 所说“正常流动无影响”也不能解释成硬加 `r<dp` 门：Eq.(63)–(64) 在 dp≤r<2h 时仍一般非零，只是衰减；现实现按公式全支持域计算。

## 当前实际路径

不存在独立 `FunSoilStress.h` 实现：CPU 函数为 `src/source/JSphCpu.cpp` 的 static helper，CUDA 对应 `JSphGpu_ker.cu`。

| 位置（当前行号） | 核验结果 |
|---|---|
| CPU 2028–2094；CUDA 626–694 | 对完整对称 3×3 张量作 Jacobi 特征分解，再构造 `Q diag(−ε max(λ,0)/ρ²) Qᵀ`。CPU/CUDA 的 xx,yy,zz,xy,yz,xz 映射与 CUDA packed `(xx,xy),(xz,yy),(yz,zz)` 一致。不是只按均值压力开关，也不是逐个全局对角元截断。16 次旋转和相对阈值是 float 近似，并非精确旋转不变量证明。 |
| CPU 2100–2121；GPU.cpp 1511；CUDA 712–714 | legacy 路径以当前 stress 和 legacy rho 预存 rho⁻² 归一化 R，再在 pair 乘 m_j；保留旧操作。legacy u-pw 中 AS 不额外看孔压，这不等于当前 u-pl total-stress 路径，也不能冒称所有旧耦合范围都已补齐。 |
| CPU 2132–2141；CUDA 707–710 | u-pl 使用 `S=σ_eff−p_l I`，先 double 相减后 cast float，调用谱 helper 时传 rho=1，得到 raw Pa `R=−ε S_+`。使用真实绝对 PorePress，既不减 P0，也不把 excess pressure 当 total stress。负水压可以把原压缩有效应力变为拉伸 total stress，当前输入方向正确。 |
| CPU 2195–2197、2346–2386；CUDA 1772、1817、1865–1899、2183、2199–2201 | u-pl 的 AS pair 系数为 `(V0 J_j/ρ_i^t) [W(r)/W(dp)]^n`，乘 raw `(R_i+R_j)∇W`；`ρ_i^t=ρ_w+(ρ0−ρ_w)/J_i`。没有在 raw R 和 pair 再各除一次 rho²。它与 u-pl 主 total-stress pair 使用相同 J 体积/混合密度权重，量纲相容。变 J 时不代数等于 2008 的 fixed-mass/rho² 离散；这是有意适配，不能冒称 paper 字面同算子。在参考态 J=1、ρ_i=ρ_j=ρ0、m_j=ρ0V0 时可还原其质量形式。 |
| CPU 2196；CUDA 2200 | 分母是相同核的初始粒距处 W。CPU `float(Dp*Dp)` 与 GPU `CTE.dp*CTE.dp` 有不同的先舍入顺序；不能承诺跨后端新算术逐位相同，但未见错用 h、r 或 rho。 |
| CPU Single 695–704；GPU Single 631–639 | 同阶段 wall/FS/C 重构之后执行当前压力政策，再 Prepare AS，然后进入 main force；不是在旧 wall state 更新前保留一份 stale R。这并不表示半步正孔压也被清零：当前 full-only 政策和实际 trace 中的正半步输入仍存在，不能用正确调用顺序声称整个子阶段已满足自由面符号约束。 |
| CPU 2123–2126；GPU.cpp 1528–1533；JSph.cpp 2989–2994；JGravityPreloadState.h 114–116 | 本项目 `ReleaseOnly`：未释放预载清零 AS scratch，释放后重新计算；元数据明确记录 policy/active/ε/n，认证 PRE 拒绝 active=true。它是保留原 AS0 PRE 的显式算子阶段切换，不是 Bui 文献要求。 |
| JSph.cpp 211–214、782–791、1759–1763、3808–3818 | 总开关默认 OFF；ε 默认 .2、n 默认 2.55。所谓 Auto 实际是 DefaultFixed=2.55，不是核的色散分析自适应。当前动态重力容器还要求有限 ε∈[0,1]、有限 n>0 等原有窄范围，没有因此开放一般动态 3D。 |

将负 R 加到拉伸为正的 total stress pair，在通常径向核梯度下产生抵抗吸引的作用，符号正确。AS 不是速度阻尼；在纯拉伸同向 pair，合成项随 `1−ε f^n` 改变，粒子更接近时可反向为排斥，也会改变局部刚度/频率。因此“ε 越大越稳定”没有普遍依据。现 .2 小于论文该试验 .5 的推荐，只能判为尚未针对当前 u-pl/塑性/自由面/边界验证其适用性，不能据此直接提高参数贴合轮廓或认定它是现脉冲首因。

## 已证范围和最低成本缺口

既有 `tests/logs/upl_c08_as_unit_r1.check.json` 为真实 CPU/GPU 通过：每后端 144 scalar rows，含压缩 R=0、ε=0、负水压 total-stress 张拉、xz 45° 解析旋转、legacy normalized R 和 preload clear；GPU memcheck 零错/泄漏。CPU/GPU 最大分量差 9.1553e−5 Pa，按原 float 舍入预算检查，并非旧新 legacy runtime 0ULP。该收据明确 `actual_force_pair_tested=false`；不能拿它认领 pair 加速、一般 3D 旋转或耦合稳定性。

若继续，优先一个小零步 actual-force 组件：两个真实 native source，选两个不同合法 J，分别做压缩零输出/已知谱纯拉伸；核对方向、ε=0、当前 V_j/ρ_i 权重及瞬时惯性质量 `ρ_i^t V_i` 权重下的 reciprocal force，不把它混称固定 MassFluid 下的全局守恒证明。再加一个已知三维 Q、三个不同主值、六个分量均参与的解析旋转张量，补现有单 xz 旋转覆盖。参考应由声明的主值/正交矩阵及一对核力直接得出，不复制 Jacobi 或仅把生产公式抄回测试。不需要新的长场景、半步链或 ε 扫描；没有执行/实现这些建议。

AS 无法替代 Lian Eq.(47) 的负孔压演化机制，亦不能由三条 stage trace 独立判定首因。当前发现不足以支持改变 ε/n、负压裁剪或其他生产公式。

若先复用既有 `local_pressure_spectrum_as_r1` 固定态 NPZ，数学 proxy 中 ε=.2→.5 只需将 AS 独立 action/Jac 块乘 2.5，其他 raw/压力/材料/几何块保持；不能把整体复合 Jacobian 乘 2.5，也不能把 `Jac*p` 当真实非线性 AS 力。若按源程序 float 参数比较，比例应取 `float32(.5)/float32(.2)`（约 2.49999996275），并披露保存 R 和 pair 累加的 float 舍入，不能称 literal CUDA 逐位重放。固定应力/压力后谱投影也固定，零特征值的原单侧导数约定仍须保留。该离线对照可以筛查冻结局部算子的变化，不能认领轨迹、物理精度或实际稳定性；本审计没有执行它。

视觉页索引（全部相对本 case）：`tests/outputs/upl_c08_as_paper_r1/` 下 `bui2008_p1552.png`、`bui2008_p1553.png`、`bui2008_p1563.png`、`bui2011_p566.png`、`bui2021_p25.png`、`bui2021_p26.png`、`lian2023_p5.png`、`lian2023_p6.png`、`lian2023_p8.png`、`lian2023_p11.png`、`lian2023_p19.png`。PNG 仅为论文页渲染，无模拟数据加工。

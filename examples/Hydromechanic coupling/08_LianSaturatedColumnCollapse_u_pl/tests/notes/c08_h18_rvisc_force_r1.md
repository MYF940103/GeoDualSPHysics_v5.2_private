# C08 当前H1.8残差黏性：仅固定力阶段可行性

作者态，2026-11-14。新增 `support/c08_h18_rvisc_force_r1.cpp`、`_build.py` 和本说明。新输出仅为 `outputs/c08_h18_rvisc_force_r1_build` / `outputs/c08_h18_rvisc_force_r1` 及同标签 logs；均排斥已有/部分/失败输出。root须全文审阅并分别准入构建、唯一组件。作者没有执行/import工具、构建、force、reader、solver、GPU、Git、hash或新PRE。

## 有界问题及反证保留

仅在已完成AS.3/n2.55、Wendland/H1.8/5us同材料PRE的两个保存态Parts38/76，试算一次旧alpha=.1的瞬时、soil-only、匹配LS残差黏性力，量化它对原same-stage Darcy的实际影响。此轮不选参数、不推进一步、不加材料shadow、half、谱链或长窗，也不是塑性GNOG/history实现。旧H1.2/Cubic residual-viscosity .90请求实际失败，记录及 `upl_c08_rvisc90_decision_r1.md` 原样保护；旧机械耗散通过并未防止耦合孔压失败，不能把此次重用当已验证修复。

原3秒AS03已通过的typed22/clock/ledger提供Parts38/76；共6805原ID，5000soil和1805fixed。旧完整3秒和其他psi不重跑。原5000材料的p/P0/J/κ/ρ/速度/位置保持，现FS、theta、六应力率、C、AS张量与合法墙闭合也不得被候选改写。既有普通HG为null/off，塑性/转角限制不被移除。

## 原数学重用

从 `upl_c08_residual_visc_cpu_r2.cpp` 原样生成 `rvisc_math.inc`：Alpha=.1、Mat2、Graph::Prepare/Fit、Evaluate、全部声明的normal-equation/work/net-force/torque浮点预算。`rvisc_members.inc` 原样保留一次per-node float提交、预算和constant/full-affine/rigid-rotation三个制造场。MakeGraph只把Cubic核权替换为Wendland核权及对应错误文字；当前H=.072f、Vi和ρi由原J-ledger读取，mi=Viρi。没有ridge、跳节点、γ、塑性历史缩放或 新增数学容差。

令dij=xi−xj，wi j=−kernel_fac(r²)>0，etaij=G/2[H/sqrt(G/ρi)+H/sqrt(G/ρj)]，betaij=etaij Vi Vj wij。各节点用匹配权etaij Vj wij拟合完整二维速度梯度Li，rij,i=(vi−vj)−Li dij；成对力增量为−alpha betaij/2(rij,i+rij,j)，对i加、对j减。冻结几何时，原LS正交预算核验功率=−2form、合力及力矩；常量/仿射/刚体速度残差应只剩声明舍入界。这是瞬时耗散，机械非正功不代表完整u-pl稳定或预言形态会更好。

理想da=fi/mi，只在原Ace上每节点一次float加法得到实际提交差，分别保留double数学和float提交误差预算。`ideal/committed_dv` 列为5us乘以上述加速度差的条件增量，不是新增实际速度更新。原isolated `alpha*dt*dmax<=1` 必须通过，且候选后仍调用真实 `DtVariable(false)` 核原动态force/wave/pore/k-gradient必要界，不能靠该孤立界替代原耦合门。candidateAceMax以原reduction重算。

## 无hook重复Darcy及计数

使用原AS03 RHS的state lifecycle、原soil-only内区掩码、原七项literal/expanded字面预算；只以protected access复用原Probe，不重编译或替换JSphCpuSingle，不插before-Darcy hook。每态：

1. 一次完整原 `Interaction_Forces`（内含一次原Darcy），5000 Ace/六Rσ/theta/FS/R位匹配已封存AS03 RHS。
2. **不改任何输入**重新调用完整 `ComputeDynamicPorePressureRateCpu`；全部5000 R和合法有效wallAce须逐bit相同。原wrapper每次清零DynamicConductivitySpeedMax、以soil现Ace重建wallAce、从头覆盖R；非周期此例不需要periodic副本。全primary/C/theta/Rσ/FS/AS均保护。
3. 制造场只在本地数学Graph运算；随后一次加入候选Ace，再调用完整原Darcy。其wallAce、Da、FS receiver项及变k chain全部走原wrapper，不能只手补一个receiver项。

故总计是 **2force / 6Darcy / 4额外Darcy / 4真实DtVariable(false)**，非2force/4Darcy。全部三次R分别执行原literal/expanded预算，共30000行算术检查。Rsigmac不重算、不重新提交p/J/κ/位置；无filter或PONDING调用。失败在zero-change门时不得继续解释候选数值。

墙scratch严格限i<NpbOk且mode=MDBC2；该前缀mode只能1/2。i>=NpbOk的原mode根本不读取，使用255描述sentinel；OFF/ignored的C、derivative、tangent及Ace均不读取。全1805墙已定义的primary、有效前缀每ID模式及所有真正active scratch仍受保护。候选后wallAce应随原重构合法改变。SpeedMax是重算派生限值：仅zero-change/sameAce要求位同，candidate保留finite>=0及原necessary dt门，并导出base/candidate值，不能谎称它是不可改变primary。

## 输出与解释

- `soil.csv`：10000行，真实ID/时间、p/P0/J/n/V/ρ/k、原/候选Ace/R、ideal/committed da/dv、dt deltaR与w p deltaR；w=nV/Kw。no_fixed邻域为receiver标签，donors从未删去。
- `pairs.csv`：4行，两个真实固定材料对4953/4954及6767/6865的距离、rdot、原/候选法向相对加速度和rddot，含真实横向速度曲率。重力在相对加速度中相消，未重复加入。
- `metrics.csv`：两态，R最大/RMS和差、sum(w p deltaR)、真实dt各界、wall计数和旧完整机械预算。
- `manufactured.csv`：6行，原三个制造场每态各一次。

这些只是冻结输入下的条件响应；sum(w p deltaR)不是流体质量收支或完整耦合能量，某个pair rddot改善也不是长窗团聚已解决。没有新物理正负符号验收门，全部数值/必要步长门原样。只有root审完这些结果，才决定是否值得一个唯一新GPU窗口；本入口和builder均不会启动它。

## 构建及未来成本边界

构建只一个新DebugCPU入口+86原schema2物理对象、160冻结头、7runtime，原MSVC14.36/VS配方；依赖只要求实际JSph/CPU/Single/FunSphKernel和本6个include，不再误要求未调用的材料头。原始source/runtime/PRE/stat绑定保护，SHA扫描0。builder只CL和LINK，不调用程序/help。

这个小组件保留旧O(N²)soil pair Graph，用于5000节点、两个冻结状态及制造场的有限计算，**不能据此接受每个真实step都all-pairs的物理窗成本**。旧私有GPU真实集成已使用现成cell-neighbor search（旧build的source proof标注true_cell_neighbor_search）；standalone GPU math harness的all-pairs只供数学比较。若以后选定当前Wendland物理候选，可审旧cell-neighbor入口和匹配moment/fit/gather三阶段，不需新建邻居系统；但当前权重/排序、原budget、CPU/GPU差异和实际loop代价仍须重新审，不能继承旧Cubic的时间或称零开销。本作者不生成GPU源码、物理run、读取器、VTK或新长算链。

# C08近床梯度只读组件 r1

仅作者资产：support/c08_h18_bed_gradient_probe_r1.cpp、_build.py及本note。未prepare/build/运行/解码/求解/通知/Git。根须完整审阅后另行准入构建和组件；build只编译/链接，不自动执行。旧成功及失败、原物理TU/PRE/输入/公开头和已封includes完全不改。

## 唯一闭scope

原AS03与新radial真实91帧轨迹，各仅Part28–34七态，共14态；completed steps2056001/2058001/2060001/2062001/2064001/2066001/2068001。读取已有typed22/6805 IDs/实际11列clock、signed dterror<=1e-14、源ledger，不新reader，不改91头、初始或signed记录。核心源为已过c08_h18_rv_radial_candidate_r1.cpp和其6封存片段；新shared只改AppInfo及Parts/Steps，Samples91和原212bytes/ID布局不改。

1个新entry TU+86个原DebugCPU物理对象=87个链接对象，160私有冻结头/7运行库及权威CL/link配方复用；不编译JSphCpu/Single/mdbc、无NVCC/公共类或ABI变化。builder生成6个复制/机械窄改片段及4个新source-literal片段，位置outputs/c08_h18_bed_gradient_probe_r1_build，已有partial/日志即拒绝。仅必要stat绑定、无SHA。新原生文件的预期stat来自已通过radial物理review consumed，不把当前文件新seal当原历史证明。

未来根可准入build命令：python -B support/c08_h18_bed_gradient_probe_r1_build.py --execution-authorized。组件未来参数为 --check -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 原AS03短seed 独占outputs/c08_h18_bed_gradient_probe_r1，不在本文件自动运行。只加载一次原Part1000作为已认证初始化资产，然后按ID Restore真实保存态；不重算10s，也不将末态当新PRE重启求解。

每态1次原 Interaction_Forces(SymCorrector)，包含真实dynamic-wall/full-image/AS/AV及完整Darcy；再施加同已过CPU radial静态算子、另1次完整Darcy。总14force、28Darcy、28 DtVariable(false)，无时间/位置/速度/J/压力/材料积分、无MaterialReturn或filter。原5us necessary bounds和radial独立证书保留。梯度literal只读，不写原scratch/primaries。所有5000土σ/v/x/J/κ/p/P0仍必须逐bit原样；墙ghost允许原force合法重建，force之后到radial/Darcy的墙/土冻结门原封保留。ignored尾部不读未定义mode/scratch。

## 梯度源及可证伪检查

唯一源为base build已绑定schema2 full_source.zip内JSphCpu.cpp。builder从源机械提取并保留表达式和先后顺序：

- ApplyGradCorr（704–709）；GetStrainSpinRateTensor_sym及GetStressRateTensor_Elastic（1958–2023），置于私有bedlit namespace，避免与原对象的global符号重复；不重写物理公式。
- dv_rhop/visc/deriv真实选择（2393–2410）。C08虽SPR0，但DynamicPoreWall真实分配并写BoundDerivativeVel；不得用native fixed-v=0替代full镜像。原NoSlip/FreeSlip tangent和full导数分支分开。
- 原float体积/9grad累加（2553–2556），逐fluid pass然后bound pass，每pass最后用同CorrMatc修正（2611–2620）。原float sigma及float K/G，Jaumann/spin和原应力率helper不改。
- 原double孔隙θ逐对源（2417–2440）：double(floatdr)重算prr2，原二次support、GetKernel_Fac(float(prr2))、Ci*grad、V0Jj、相同dv_grad_deriv。输出literalθ。该片段保留唯一原support-if开括号及invalid-J分支；CPP不再另包support-if，观察语句在原pfac/divv作用域内并闭合它。普通函数显式constexpr tker=Wendland，每pass以porosity_thetap1别名绑定该pass的o.theta，仍是local求和后再加全局。

要求每态全5000 literalθ与实际PoroThetac逐bit一致，共70000；source-literal每fluid/bound pass弹性Rσ相加与原Rsigmac六分量逐bit一致，共420000。无既存P28–34 CPU外部控制，明确external_CPU_reference_bit_rows=0；新literal通过是同原源码求值复现，不冒称14态对旧CPU程序或GPU stage的0ULP。若literal不符，保留实际part/ID/分量首因，先诊断新观察器，不放宽或自造容差吞差。

G1与θ在连续表达上同dv_grad_deriv、V0J、Ci，但G1先float(-V)、float Fac/grad累计，之后double C乘再转float；θdouble逐对先乘Ci grad再累计。Fac参数及边缘support也可能因float rr2与double重算不同。跨路径差（gradTrace−theta、tr(Rσ)/(3K)−theta）全部描述性输出，不设物理相等门、更不假定Jbug。tr(Rσ)=3K theta仅是实数弹性/Jaumann trace关系；实际float刚度组合、trace求和和spin抵消均保留。

源force clock设为已保存actual time/completed_step，当前完整σ/v/x/J等场重建真实CPU瞬时力；不是恢复原GPU此前半阶段。saved native theta是此前真实stage诊断，另列 saved_prior_stage_theta，不把它当当前梯度真值。Rsigmac是本次弹性客观应力率，不含之后塑性返回或cap的trace变化。

## 数据

- gradient.csv：70000行、87列。原始/新鲜FS、saved prior θ、fresh θ、literal θ、G1 corrected trace、elastic trace/(3K)、Rσ六分量/trace、真实floatK、Ci九分量；各fluid/bound pass支持数、θ二次support拒绝数、Fac float位差数、体积cast绝对误差和full-vs-tangent位差数、θ及9raw/9corrected grad。没有推断缺失stage。
- walls.csv：仅四局部土ID6961/6962/7011/7012的真实有效床/墙支持记录，31列，保留actual wall ID/index/NpbOk、mode/slip、dr/V/Fac/两种rr2、真实法向、wall ghost物理v、full derivative v、tangent v及wall Ace。modeOFF原样跳过，不读其scratch；所有土的边界支持计数仍在gradient表。
- soil.csv/metrics.csv延续原受力/Darcy七渠道+数值余项、实际necessary dt；无旧非存在的bare bit-control，计数改为observed bare CPU soil rows70000。
- pairs.csv/focus.csv：四材料ID的全部6 unordered pairs×14态=84条真实pair-state；即使非直接邻居仍保留距离/全邻居投影，direct=false则direct force0；168个端点记录对应56个unique focus-state。保留s/q/limiter、direct/all-neighbor、曲率、AS raw-Pa谱/投影和真实σ/p等，不声称CPU是GPU力位真。
- selected_clocks.csv：14行完整原始11列clock另带case。completion明确14/28、70000θ/420000Rσ、无时间步/返回/过滤、physical_acceptance=false。

旧10态组件实际81.48s仅作成本参照；新14态及一遍只读梯度预计分钟量级，未作性能基准或实际耗时承诺。结果用于判断近床算子/舍入/局部非仿射形变，不能用J≈1或四角材料连线面积直接重设J，也不自动承诺新的physical trajectory、参数扫描、其他ψ或正式验收。

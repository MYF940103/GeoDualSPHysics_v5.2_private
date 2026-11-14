# C08 Lian2023 plastic-history consistency audit r1

2026-11-15。只读文献及已冻结材料实现，本轮只新增本说明；不改活动windowR2的程序、输入、PRE或源码，不运行材料试验、求解器、reader、构建、Git、SHA或queue。复用 notes/upl_material_law_review_r1.md 的原PDF直接核读和 notes/c08_h18_tension_volume_audit_r1.md 的既有返回机制证据；较早 lian_material_baseline_review_r1.md 描述的旧fast软化算法不能当作当前law2实现。

## 绑定参考与定义

文献：src/papers/u-pw/Lian 2023 u-pl.md，221–267行（原PDF印刷4–5页，Eq11–19）；Table1在860–878行（印刷19页）。此前upl_material_law_review_r1已直接核过原PDF Eq13，不在本轮重新渲染/数字化。

代码：tests/outputs/c08_preload_schema2_source_r1/full_source.zip 内 src/source/FunSoilMaterial.h、DualSphDef.h、JSph.cpp、JSphCpu.cpp、JSphGpuSimple_ker.cu。当前私有RV候选保留原物理材料CUDA对象；新RV独立CU不重定义材料律。StSoilCte实际在DualSphDef.h:297–316，不在TypesDef.h。这里的代码历史变量kappa不是论文Eq14的DP锥强度常数κc；后者对应代码DP_kc。

## 等效塑性历史归一化：Smooth支路确实一致

论文Eq12–15：g=ξψ I+q，q=√J2；Eq13历史因子使用偏应力导数∂g/∂s。对三维偏张量，s:s=2q²，∂g/∂s=s/(2q)，故其Frobenius范数平方为1/2。因而

Δεeq_p=√[(2/3)Δεp_dev:Δεp_dev]=Δλ/√3。

当前FunSoilMaterial.h:42–45的q²=(对角差平方和)/6+xy²+yz²+xz²，正是s:s/2；完整张量范数的剪切项有2倍，不能再额外乘2或只保留xx/zz/xz。平面应变不表示塑性yy分量消失，代码仍保存六个应力分量。

EvaluateRadial:105–109和常系数Smooth:172明确用kappa_old+λ/√3，且不把体积流动3ξψλ加入该历史。这一因子对ψ=0、+2.5、−5都相同；ψ改变塑性体变和一致性方程，但不改变这个偏等效历史的定义。与旧fast软化曾采用完整流动范数的差异已在旧baseline记录，不能据旧写法认定当前少了2/3。

## Eq17–19及Table1参数映射

FunSoilMaterial.h:49–68实际计算：

φ=φr+(φp−φr)exp(−n_phi·kappa)，
c=cr+(cp−cr)exp(−n_coh·kappa)，
ψ=ψ0 exp(−psiDecay·kappa)。

对应导数也在53行按同一历史求取。JSph.cpp:4082–4104把XML角度从度转float弧度，分别读取n_phi、n_coh、DilationDecay；psiDecay不是n_coh的别名。指数内kappa无单位，衰减参数单位是每单位等效塑性应变。角度先转弧度不改变指数律的物理意义。

| 项目 | Table1 | 当前/已准备同材料映射 |
|---|---|---|
| φp=φr |25°/25°|phi=phi_r=25，n_phi=0；即使paperη=5，角差为0仍是同一常φ|
| c，ψ0=0/+2.5 |5→1kPa|coh=5000、coh_r=1000Pa，n_coh=5|
| c，ψ0=−5 |7.5→1kPa|coh=7500、coh_r=1000Pa，n_coh=5|
| ψ0=0 |sf=N/A|dlt=0、DilationDecay=0；ψ恒0与任意有限sf下的ψ0=0等价|
| ψ0=+2.5/−5 |sf=.2|dlt=2.5/−5度，DilationDecay=.2|

当前实际AS03的17-key材料CSV（由既有run.native_profile绑定）为psi0/DP_PS3、coh5000/coh_r1000/n_coh5、phi=phi_r25/n_phi0、dlt0/Decay0、fresh_trigger_active0；原XML同值。另两组映射来自 support/c08_h18_plastic_pre_r1.py:12、20、30的封闭组定义，不表示它们已经完成或获准运行。所有材料参数和保存kappa仍为float；中间应力/系数/连续root历史用double。这是表示精度限制，不是η或sf定义换算。

SoilTriggerFos虽记为1.65，EvaluateMaterial:228–231仅在trigger且强度软化时除峰值cohesion。当前fresh_trigger_active=0，PRE是gravitypreload合同而非PartBegin软化restart，所以不应把当前cp误报成5000/1.65；以后若改变trigger，便不是原Table1同一峰值参数。

## 已证明一致不等于逐字相同返回算法

law2用新连续kappa上的c/φ/ψ求隐式endpoint返回（105–109、181–207），不是论文Eq13单次半隐式线性化的逐字复刻。Eq13分母/软化模量的符号约定与当前对F(λ)直接求导已在旧law review区分；本轮不凭参数映射宣称两种时间离散精度等价。

q趋0的锥顶处，论文Smooth梯度公式本身不能直接外推。当前ReturnApex:125–150先使偏应力耗尽，以kappa_tip=kappa_old+qtrial/(G√3)评价强度；后续锥顶体积乘子或独立g_t=I张拉面不增加偏等效kappa。故lambda_shear在Apex记录中不一定等于√3Δkappa（代码24行也明确声明），且ψ0的TensionRepair仍可能降低应力trace而不产生额外偏历史。必要张拉/顶点政策与paper未显式列出的实现细节仍是潜在模型差异，不能简单改为全塑性范数，也不能把此差异自动认作团聚根因。

保存floatκ会舍入连续增量（Commit:115–123），是既有审计限制。CPU predictor在3503–3506返回半步应力后恢复旧κ，corrector3638及3697才提交完整历史；GPU JSphGpuSimple_ker.cu:559–566同样保留predictor旧κ，762–768及803–804在corrector提交。不存在因有Pre/Cor两次材料调用便必然双加历史的证据。该调用/静态证据不是每个GPU全历史乘子的新增实测。

schema2合同JSph.cpp:3768–3774明确law2、trigger policy、JointExistingApexCap及KappaDeviatoric；3781–3800要求同材料合同并声明保留σ/κ/J/p。本轮沿用已通过的真实PRE认证和继承证据，不把撤墙当κ=0重开。文献887–888行也先施重力取得地应力再撤墙，但并未给出其全部预载塑性历史和顶点实现，不能由图反推两者初态κ相同。

结论：当前Smooth历史归一化与Eq13偏历史定义、Eq17–19指数律及Table1 η/sf映射有直接公式证据，没有发现可通过换一个2/3因子或把sf换成η修复的明确遗漏。仍需保留endpoint返回、张拉面/锥顶政策、float历史以及实际预载塑性路径的比较限制；它们是模型/离散差异或未给定信息，不是本轮已证明的物理错误。此审计不解锁其他ψ、不改变活动RV候选，也不构成塌陷或论文精度验收。

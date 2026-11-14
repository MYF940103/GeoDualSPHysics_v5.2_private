# C08 H1.8 RV coupling: bounded mathematical/code audit r1

2026-11-15。本轮仅新增本说明，不修改源码、程序、输入、PRE、成功原生/图CSV或失败记录；不执行probe、分析脚本、solver、reader、构建、Git、SHA或queue。它整理已经只读完成的数学/代码审查，供后续根线程独立取舍；不自动准入3s、其他ψ或新物理窗口。

## 实际依据与边界

- 私有独立TU：support/c08_h18_rv_gpu_r1.cu；当前Release_r3只对该新增TU显式使用--fmad=false，原112物理对象及原物理CUDA标志保留。旧Release windowR1制造场证书失败继续保留；新windowR2的成功不把旧失败改成成功。
- 私有host：outputs/c08_h18_rv_gpu_r1_source/JSphGpuSingle.cpp；物理原件：outputs/c08_preload_schema2_source_r1/full_source.zip 内 src/source/JSphGpu.cpp、JSphGpu_ker.cu、JSphGpuSimple_ker.cu。下列行号分别指这些实际文本，不混用私有插入后与原件行号。
- 科学结果沿用已通过 logs/c08_h18_rv_window_review_r1.check.json 及对应history/matched/spatial/timing CSV/PNG。原AS03与RV有91个实际同step/time、相同5000材料ID；差异是新算子响应，不是half误差或理论误差。p−固定P0不是论文定义的塑性超孔压。
- 复用既有 c08_h18_rvisc_force_decision_r1、material_tangent_decision_r1、work_decision_r1、pressure_feedback_decision_r1、seepage_complementarity_audit_r1、contact_reaction_scope_r1。没有重复其材料或空间试验。

## 仿射零响应为何不保证粒子间距

令d=x_i−x_j，dv=v_i−v_j，n=d/|d|。CU54–68按实际soil邻域构造权重；70–94求每点无ridge完整2×2 LS梯度L_i。其实际残差和力在125–128为：

r_i=dv−L_i d，r_j=dv−L_j d，
rbar=(r_i+r_j)/2=dv−[(L_i+L_j)/2]d，
F_ij_RV=−alpha·beta_ij·rbar，alpha=.1，beta_ij>0。

因此即使真实dv·n<0（靠拢），若rbar·n>0，即真实靠拢比拟合的局部仿射压缩慢，F_ij_RV·n仍为负：该直接pair力会促进靠拢。示意dv_n=−1、拟合仿射部分=−2，则残差+1、RV径向力向内。这是公式本身允许的条件，不是已经测得当前新团聚对恰有该符号。

完整仿射压缩、剪切和刚体运动的残差均为0；所以affine-null不能同时保证抑制真实局部剪切/压缩或塑性局部化。CU58–60只拒绝完全重合/处理support，rank门86–92保证拟合可计算，dtλ/2门105–108是额外算子孤立显式界；这些都不是最小距离、无倒置或粒子质量保持门。现有材料切线审计还发现部分Smooth非关联骨架方向有负实特征值，冻结强度后仍存在；那是条件局部化信号，不证明完整u-pl失稳或当前聚集全部由该信号造成。

不能把一个directpair力当成两点全部相对加速度。实际rddot含全邻域(a_i−a_j)·n及速度曲率；此前固定态pair审计已显示强烈抵消。后续必须同时保留directpair与all-neighbor增量，不能只展示有利的一项。

## 全局机械证书的范围

CU129、137–145累计D_i=sum_j beta_ij r_i⊗d、局部normal方程缺陷、功与力矩；159–184汇总成对预算，217–229先通过全部证书/制造场门，230–233才一次提交候选float Ace。实数恒等式为：

P_RV+2Phi=−alpha/2 sum_i L_i:D_i。

精确LS时D_i=0，故全局P_RV=−2Phi<=0；实际实现保留其原浮点normal/work/torque/floatcommit预算。这不要求每一pair、每一材料点的物理速度功都非正，也不要求每个靠拢对都受分离力。舍入受控的全局机械耗散可以与少数径向向内力、局部压缩和更严重NN尾部共存。

这套证书只覆盖额外RV的soil–soil机械算子。它不覆盖全部固体材料能、软化耗能、AS、孔压容量、Darcy相对流、正FS投影、NoPen后投影或外边界工作；不能将负机械功与某个storage代理直接相加作总能量。新CSV只保存每次Save的最新Pre/Cor和内部running maxima，不能从182行稀疏功重建360000个阶段的精确累积能量。

## RV→完整Darcy→p→total-AS：明确但尚未归因的通道

私有host758先完成原force，759–774保留原阻尼/加载/HG/2D路径；815提交RV Ace后，823才调用完整ComputeDynamicPorePressureRateGpu。原JSphGpu.cpp2073–2088先扩展必要owner、2074重新拟合wall Ace，再用当前Ace/J/theta/p/FS进入原Darcy。RV本身不改本stage已经形成的theta、Rsigma、p、J或κ；但它改变这次Darcy实际读取的加速度。

在固定几何、p/J/k/FS、速度及其他原场的条件下，原bulk/FS式可写为：

R=(Kw/n)/gamma * [−gamma·theta + k_i L + grad(k)_i·(g_p+rho_w a_i)]，
L_bulk=Lp−g_p·Lx+rho_w Da，
L_FS=Lp+rho_w(a_i·Lx+Da)。

故仅由RV加速度引起的条件增量为：

deltaR=(Kw/n)/gamma * rho_w * {k_i[deltaDa+I_FS(delta a_i·Lx)]+grad(k)_i·delta a_i}。

这里deltaDa必须含真实全部供体加速度差及重建的墙Ace，不只receiver项；原率float量化/源顺序余项应独立保留。公式为固定stage条件展开，不是新轨迹积分或一般稳定谱。先前原AS03 Part38/76的实际零推进RV组件已测到混合甚至恶化的局部deltaR/相对加速度，说明不能从机械负功推断孔压单调改善。不得为压低deltaR而无声从Darcy删除RV Ace：那会更改当前采用的混合加速度耦合，需要另定义模型及一致性依据。

真实下一stage的p变化还会进入total-AS。原JSphGpu_ker.cu713–714在水力反馈分支以float(sigma_effective−p I)构造Bui人工应力谱。固定sigma_effective时，每个total主值恰向−delta p方向移动；若suction减轻（delta p>0），其total主值更偏压缩，可能使正主值谱及AS排斥减少。这是“末态孔压较平缓/运动继续，但少数粒子聚得更紧”的一个条件闭环假说，不是当前已证明因果，也不是重启已拒绝effective-AS参数窗的理由。

## 边界与接触：保留缺口，不凭标签归因

CU40只接受normal fluid，邻域76–78、120–123只取cellfluid；该新增RV没有soil–wall pair、独立墙反力或墙端口功。原mDBC/AV仍提供其原墙作用，这里不能把RV当成具完整NoSlip壁面牵引的物理粘性模型。简单把fixed点加入RV图会同时改变LS、反力和功证书，不能作为未推导的小补丁。

NoPen仍为FixedPlaneStageProjectionReleaseOnly、ReactionClosed=false；原力阶段Darcy早于后续位置/速度投影，现有总体接触闭合限制真实存在。但 c08_h18_contact_reaction_scope_r1 已用原AS03两个真实单步证明：P38/P76的四个force状态无静止贴墙候选，两个完整步的8项原pre/corr投影增量在全部5000ID上均恰0。其最小床gap约.004456/.003929m，真实plane约7.15e−9m。不能因为粒子接近床、或ReactionClosed=false文字就推断这些状态受遗漏反力驱动；也不能扩大原接触门制造触发。该零事件证据不推广到新RV全历史；新轨迹若确有真实投影，再按实际时间层重审。

原free-seepage是FS2/3的Taylor-defect分支及completed正压cap，不直接强制每个阶段的零法向综合Darcy通量；保留负p也不等于任意负压都是数值错误。上述已审边界限制不能由RV证书或p<=0本身关闭。

## 两个低额外求解成本的可证伪方向

1. 先用正在准备的近对轨迹定位P40–43新增团聚对，随后复用现有LS/RV固定态数学，在这些真实保存状态报告dv_n、Lbar d_n、rbar_n、directpair RV力及ALL-neighbor delta(a_i−a_j)·n，并保留原曲率。若向内净效应主要属于仿射部分且RV残差接近0，则排除“只要加强affine-null RV便会排斥”的预期；若rbar_n>0且RV净增量向内，则确认该条件机制。若符号反而分离，必须继续找其他力而非硬归因RV。无需新PRE、时间积分或alpha扫描；此处不重复轨迹作者工作，也未运行组件。
2. 对同一已选状态，复用已通过的原force/RV/完整Darcy七渠道+数值余项组件作零推进ON/OFF条件差分；核真实wall重建、deltaR来源和局部total-AS正谱。若deltaR/AS变化不支持上述闭环，则否定该假说，不以图相关替代。若支持，也只说明下一项应修订的耦合/正则化合同，不能自动删除加速度项、裁负p或更换AS定义。实际调用及新标签仍由根单独审阅准入。

这两项旨在把已观察的P43以后尾部反转定位到可辨别通道，而非继续报告或盲扫参数。目前没有新的证据证明材料历史归一化、RV符号或既有原动量实现存在可直接修改的bug。若主导的是允许的仿射压缩/非关联局部化，保持affine-null的瞬时RV本身便不是空间局部化正则；那时才需要明确比较粒子质量修正或塑性/有限转角正则的功能与成本，不能放宽HG保护门冒充已实现。

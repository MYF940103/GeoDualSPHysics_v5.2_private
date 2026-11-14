# C08 AS03：两保存态原RHS分区与自由表面法向目标

仅作者新增`support/c08_h18_as03_rhs_r1.cpp`、`support/c08_h18_as03_rhs_r1_build.py`及本文；未导入/执行、构建、求解、解码、VTK、Git或SHA扫描。原源、程序、PRE、输入和所有旧失败保持。根完整审阅后分别决定一次build及一次零推进组件；没有后续solver或其他ψ自动准入。

已有`as03_pair_force`只保存actual rate/θ/Ace，work工具没有七项Darcy分解。旧`storage_rhs_r2`为AS05/91帧Parts30/60/90，`late_rhs_r1`为AS05/301帧Parts200/250/300，均不能冒充本AS03早期状态。本工具只补AS03完整301已解码的Parts38/76，completed2076001/2152001；实际scalar clock从原clocks.csv与typed22读取，不拟合或重写元数据。

## 最小适配和原门

以已经成功的`c08_h18_late_rhs_r1.cpp`为主体。原typed22/6805 IDs（5000soil/1805fixed）、bed-last roles、Copy/Restore/Map/Roles、J/n/V/rho/k ledger、cell排序和soil primary不变检查保持。`Sums/Assemble`和literal/expanded七项的源运算顺序逐字保留。只把输入目录改AS03 full301、两状态及AS guard改.3；原Kernel2/H1.8/5us/keepfalse/retire255/同材料schema2/原FS policy不变。

每保存态调用一次原`Interaction_Forces(INTERSTEP_SymCorrector)`，共2次真实CPU force/Darcy；不是两次新时间窗、GPU子步回放或独立half。真实重建C、wall、FS、Ace、θ后分解原率。`c08_h18_late_rhs_r1.build.json`提供已封存86原DebugCPU对象、160归档头及真实CL/link配方；只编译一个entry并链接87对象，不重编physical objects、Single或CUDA。源码archive与原AS03 GPU实际程序的schema2 archive闭合，current public不参与。

两个原门保持：每材料literal源式最后float提交必须与实际`PorePressRatec`逐bit相同，误差处于原float量化预算；七项double展开、donor分区及全局有符号Q必须在原`RoundoffGamma`算术预算内。没有新Pa/位移物理门、拟合、epsilon夹紧、滤波或边界改变。原宏安全`(std::max)(...)`写法保留。

## 七项与新增接收标签

令B=Kw/n、γ=rho_w·9.80665、k取原J派生场、dk=k/[(1−n0)Ck]，全部使用原fresh CPU状态。七项顺序为：

1. compression：`−B θ`。
2. LP：`B k LP/γ`。
3. Taylor_pressure：内部`−B k gradp·Lx/γ`；原FS支路为0。
4. Da：`B k rho_w Da/γ`。
5. FS_Ace_Lx：原FS支路`B k rho_w Ace_i·Lx/γ`；内部为0。
6. chain_pressure：`B dk gradJ·gradp/γ`。
7. chain_Ace：`B dk rho_w gradJ·Ace_i/γ`。

原soil、wall donor积分采用同一个完整gradp和Ace，分区是加性记录，不是重跑counterfactual。压缩源只记all行，不能把三个donor行直接相加重复压缩。每项保留Pa/s及权重`w=nV/Kw`后的Q；signed与absQ沿旧summary，不是流体质量。

新`receiver_cohort`为互斥描述标签：原`IsFreeSurfaceParticle`真则`FS`；否则实际fixed_donors.count>0为`wall_adjacent`；其余`interior`。同时保存原fresh FSType和独立`fresh_is_FS`布尔，**不强制saved_FS=fresh_FS**。不以拟合距离取墙层。原summary接收类仍是all、interior（全部non-FS）、FS三类；它的interior与新标签排除墙层后的interior不同，后处理须按soil标签另作cohort汇总，不能改旧summary含义。

## 法向目标是观察，不是新边界

在每soil输出`H=原corrected gradp+rho_w*原Ace_i`及`H_dot_n=H·原FSNormal`、`normal_norm`、`normal_valid=(norm>0)`。保持真实方向与近单位float长度，不重新法向拟合。zero normal的原点积代数上为0，但flag=false，**不能计为满足零通量边界**。也保留非保守局部影子`q_n_local_shadow=−k/γ H_dot_n`；它不是粒子间守恒通量、阶段/时间积分质量流失或完整饱和模型的边界验收。原Ace不含gravity，此处不额外加g。

全部FS/内部/墙邻接的H均可描述，但仅FS处对应本轮要审的自由表面目标。source raw-FS率是完整`gradp+rho_w Ace`缺陷的离散支路，不能仅凭单一法向残差认定该边界正确/错误，也不重启已拒绝的normal-Taylor候选。

## 保留baseline和输出

旧`outputs/c08_h18_as03_pair_force_r1/soil_force.csv`由其实际12-call完成收据绑定。新工具一次读取原60000记录，选这两个part的10000条baseline；相同native ID、实际time bits与completed_step为硬身份要求。新增Ace三分量、rate、θ差及FS相等标志仅为描述复核，不新增物理阈值或强制逐bit相等门，不运行旧OFF模式。旧baseline/source/native/PRE及本次程序runtime按必要stat保护，不重扫对象或BI4哈希。

唯一新build目录`outputs/c08_h18_as03_rhs_r1_build`，program`C08H18As03RhsR1.exe`，build收据`logs/c08_h18_as03_rhs_r1.build.json`。唯一组件新目录`outputs/c08_h18_as03_rhs_r1`输出：

- `soil_rhs.csv`10000行：旧完整接收字段后加cohort、FS/normal flag、H/法向点积/局部flux shadow、baseline描述差。
- `terms.csv`30000行：每soil×all/fluid_donors/fixed_donors，原七项Pa/s与Q。
- `summary.csv`18行：2状态×3donor组×3旧receiver组，原signed/absQ和global budget。
- `walls.csv`3610行：2×1805真实重建wall字段，原active标志、P/P0/J、ghostv/derivv/Ace/C/normal/slip。
- `completion.json`实际actual_force_calls/actual_Darcy_calls=2、literal_final_float_bits_matched=10000；physical_steps/material_return_calls/filter_calls/extra_Darcy_calls=0，physical_acceptance=false。

本审计观察已保存completed GPU状态上的新原CPU重评估，不能恢复未保存GPU predictor/corrector或瞬时wall/FS通量；不能将S=sum(nVp/Kw)称流体质量或将负孔压直接剪零。它不改变物理、不代替接触/团聚验收。失败保留首因、partial和旧结果，不自动重复组件、solver或decoder。

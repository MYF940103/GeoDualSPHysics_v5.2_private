# ψ+2.5°早停：下一步最小诊断顺序

3秒原生/HG/几何安全通过，结果保留但论文精度未验收。当前同材料粒子几乎不塌，必须区分物理吸力反馈、离散负压过预测及HG的影响，不能从稳定、无团聚或视觉相似直接认定根因。论文Fig16右列与当前形态相似是观察；原文未直接称其冻结，也不是当前因果证明。源与新结果的原生时钟、塑性和体积历史均保持原样。

基础公式验证不重复：case02历史 upl_p2_feedback_r2.check.json（DebugCPU/ReleaseCPU真实调用）已覆盖有限Kw均匀theta与p–J解析，最大压力误差.00608933Pa；upl_porosity_operator_r1.check.json覆盖(1−n)theta与压力总theta；upl_lian_scalar_kernel_r4.run/review覆盖常/线性Lp/trace/Eq23；upl_p3_perm_actual_DebugCPU/ReleaseCPU_r2与upl_lian_variable_scalar_r1覆盖变k链项/加速度Darcy项。它们是历史实施证据，不代替本次GPU塑性耦合或Eq47兼容验证。已有GPU列组件只有真正正p排水调用，负/零值曾是poison不能误报负/零自由渗出测试。

已静态确认groups程序只有在独立子进程环境中删除C08_HG_OPT_H18才关闭private HG；值0会报错。关闭同时切回原非cached材料积分路径，因此后续短.30s同材料HG0对照是HG/缓存实施路径联合诊断，不能将差异一概归因纯HG力。其余本组PRE/AS.3n2.55/5us/原p<=0边界不变，与已完成HG1全程仅在实际共享时刻描述比较；这不是新增半步/收敛参考链。旧OFF1只覆盖旧ψ0首步，不能借作本组材料路径全程bit证明。现已构建独立window31读取入口，保持22/6805/clock/signed/ledger原门及真实31头；当前不启动第二个GPU物理计算，不插值末帧或伪造HG602审查。

若关闭HG后仍早停，再集中检查压力稳定化与有限储存/体积耦合。原论文C08明确p<=0，不把全自由面Dirichlet0包装成边界修复。Eq47为取n/Kw=0后的TPI压力行附加项，beta=.04无明确单位，不能直接乘当前显式rate、只改塑性源或裁切负压。兼容候选需有明确残差/量纲/时间记忆与beta0恢复原方程的性质；改变物理响应的人工储存需明确披露。审计中的Kw*k/(n*gamma)是固定theta压力子算子尺度，不是已验证的完整耦合固结扩散率，不能用sqrt(Dt)单独证明实际场传播原因。

ψ−5°独立同材料源已获准运行：coh7500、psi−5、衰减.2，WendlandH1.8/5us/10s cap，阻尼.03/Shepard40，源AS/HG/NoPenOFF。其原程序/归档/PRE生成依赖保持冻结，源完成仍须独立native/平衡审查，不自动启动撤墙。源计算期间允许纯离线/私有准备，不启动第二GPU物理求解器，不变更其依赖。原direct owner仅一次完成通知，无watcher或重布防。

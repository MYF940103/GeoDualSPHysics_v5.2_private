# C08 撤墙后人工应力候选

本候选不是底面接触约束，也未证明能解决穿透。现有正式XML/BAT/runtime保持原样；只在tests开展关闭/开启比较。

u-pl使用总应力 `Σ=σeff−pI`（绝对孔压），谱分解后 `Rraw=−εΣpositive`，单位Pa。成对加速度采用 `(Vj/ρti)*(W/Wdp)^n*(Ri+Rj)·gradW`，与当前混合物动量方程的体积和惯性权重配套。旧u-pw仍按有效应力、ρ^-2归一化人工应力和质量权重计算，原数学与计算时点保留。没有新增持久数组、邻居遍历或公共参数。

新u-pl路径在当前墙状态、FS和压力投影后准备人工应力，避免使用上一阶段墙值。范围仅现有二维固定重力gravitypreload容器；HG、NoPen、额外SPR及其他未验证组合不放开。`ArtificialStress`默认0；候选沿用已有ε=.2、指数2.55，不称为论文参数。

阶段策略明确为ReleaseOnly：认证预载期间AS数组清零，撤墙后才启用。PRE合同不因无作用的AS参数变化而改变；新增BI4字段记录Policy、Active、Coef和Exp，加载器拒绝Active=true的PRE。旧AS0认证弹性PRE仍可使用，但这是“相同预载算子，撤墙后新增稳定项”，不是全程同一算子或任意塑性重启。

CPU Debug、GPU Debug和GPU Release权威VS构建通过，旧程序、runtime及对象均未覆盖。CPU/GPU真实Prepare组件各检查144个分量（6张量×4模式×6分量），包括全压缩严格零、单轴及旋转拉伸、有效压缩但负p引起总应力拉伸、浮体排除、ε=0、预载清零和旧归一化路径。GPU memcheck为0错误/0泄漏。使用32*FLT_EPS*应力尺度预算，两后端最大分量差9.1552734375e−5，均在事先声明的预算内。

CPU最初的测试夹具因C++17的std::byte与生产byte别名冲突，未运行。仅测试编译命令追加 `/D_HAS_STD_BYTE=0`，在全新CPU helper目录恢复；未改生产代码、张量输入或计算公式。原失败记录保留，修复的真实CL/link/run命令分别在 `logs/upl_c08_as_unit_cpu_repair_r1.*.call.json`，结果在同前缀check.json。生产CPU Debug构建本身已正常通过。GPU使用原组件及唯一memcheck调用。

这些组件没有验证完整两粒子force路径或真实接触，也不是旧新完整u-pw的0ULP证明；相关限制保留在completion中。后续唯一序列为ASoff到τ=.11s（与原失败保存的11帧全22数组/clock逐字节相同后才准入ON），ASon到τ=.30s；无额外半步链。序列结束后根据实际孔压、应力、沉降、穿透和ledger结果决定下一步，不据正常退出自动准入3s全程。

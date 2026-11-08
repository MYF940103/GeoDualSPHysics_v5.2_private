# C08 PRE孔压继承只读代码审计

本次只读代码/已有记录，未运行solver、reader、构建或BI4解码，未改原始数据。下文C为case08根、T为tests；真实源为 `C/CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4`，原时钟10.000000000374257、completed4000000。

可直接复用源的 `particles/PartFluid_1000.vtk`（5000土粒）和 `PartBound_1000.vtk`（2060墙），已有 `T/logs/upl_preload_r2_GPU_particles_separate_r2.check.json` passed。实际legacy BINARY VTK按big-endian读；Idp/FSType为uint32，p/P0/excess/Vel/κ为float32，J/n/V/rho/k/θ及SigmaState六分量为float64，POINTS仅float32。须按Idp而非tuple顺序比较；坐标不能充当原Posd逐位证据。未发现这份真实r2GPU PRE的独立typed22导出，旧 `upl_prestress10_CPU_r1_native_r1` 和GPU .002s handoff导出分别属于其他控制，不能混作本源。

`source/JGravityPreloadState.h:173–239`读取全部22typed数组并建立唯一ById，校验p0/excess/σ显示/κ0/ledger/FS；保留原raw order。`JSphGpuSingle.cpp:1098–1175`先核新输入的P0/fixed坐标，再按source.Idp及ById拷贝Posd、VelRhop、六double σeff、κ、p、P0、J、θ、FS与PosDiv。为真实cell排序，临时关闭Shepard/free-seepage做divide，随后按新Idpg顺序再次copystate恢复主状态；最后只清重新计算的PorePressRate/KplasticDk，未清p/P0。静态wall属性来自新输入；keep5只在release时改法向/slip，不改土粒主状态。

`JSph.cpp:3781–3789`继承源实际clock/Step/dt。`JSphGpuSingle.cpp:1208–1213`明确handoff不保存重复初始PART；`r5/native/clocks.csv`首帧实际10.010000000377431、τ=.010000000003174137、completed4004000，因此Part0已有4000次新更新，不能把它与PRE的差当成导入失败。源码未提供这次真实r5“导入后、release/边界刷新前”的全ID独立观测；旧handoff11个共同post状态全部22+signed逐位相同证明过受测接续，不替代本次瞬间全状态实测。

release在 `JSphGpuSingle.cpp:1048–1093`关damping/Shepard后真正RunCellDivide；`RunCellDivide:580–581 → JSphGpu::ApplyPorePressureBoundaries:1296–1311`重新分类FS并在completed geometry上将FS2/3的正p投影为0、保留负p。新暴露右面因此可在下一次时间积分前改变p，属于本阶段边界作用，不是copy重置。真实trace已有t=10.000000000374257、step4000000的首次PONDING三点：5809/4959的p为0，4956为1209.60791015625Pa，pre/post均同；它只观测三ID且在release/FS路径上，不是全部5000土粒的import前后证明。

`JSphGpuSingle.cpp:1350–1356`保存ExcessPorePress=float(p−P0)。P0为固定初始材料参考，不是当前变形后的水静压力，也不是每阶段重置的零点；完整孔压p、P0和excess必须同变量、同单位、同色标比较。SigmaState是有效应力，机械总应力需另算σeff−pI；墙的重建/marker值不能混进5000土粒统计。r5 native为little-endian typed22、每帧按ID排序，6805=1805墙+5000土粒；源仍7060，直接按行减两个不同N/顺序会制造差异。

现有代码和资格/接续证据支持“有完整孔压继承路径”，尚不能凭代码审查宣称本次导入瞬间全字段已独立逐位实测。根线程将使用上述既有VTK与r5 typed数据作逐ID定量比较；若仍需真正import瞬间证明，应先明确这项观测缺口，不能重解已有BI4或用τ=.01代替τ=0。

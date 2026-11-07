# C08 ψ0 完整运行中断与动态墙诊断

根目录正式r3 GPU未完成：实际GenCase退出0、wrapper及solver退出1，所有权无异常，封口时70项输入/程序stat未变；无残存求解器。原始run/call/status位于tests/logs/upl_c08_formal_psi0_r1.*。旧owner及通知已退休，不重启、不重新布防。

保存11帧，末原生TimeStep=10.110000000409173，zero-based Step4043999/completed4044000。原失败的精确阶段时刻未保存。专用partial读取完成6800 IDs、22数组、11 signed intervals及原J/n/V/rho/k、P0/κ/FS守卫；前10帧同成功short的全部数组、时间和signed clock逐字节相同。没有改头部、插值或删记录。

原生double坐标显示ID7010在τ=.09s首次穿过底面z=0，末z=-.024776027m、vz=-1.03915930m/s、κ=.88994777、p=0、FS2；其他土点未穿透。τ=.08尚未穿底时，床ID787镜像邻域土体σ′zz约3.85..6.69kPa，墙外推64.89kPa（总σzz67.32kPa）。不能仅降低MLS阈值或放行矩阵来忽略底部力学异常。

离线11帧共3375个当前B支持代理样本，61次主拟合失败均被已有一次最近源重试修复，采用Jfit全在饱和域。缺少PosCell/C/Ace，不能声称GPU故障复演；图和CSV在tests/figures/upl_c08_wall_geometry_r1.*。

仅给JSphGpu_mdbc.cpp报错分支增加stage/ID/坐标日志，原数值不变；新隔离Release程序从原PRE作一次最多.12s复现，实际solver退出1，观察成功封口。实际stage0/state、ID791、B=(4.1,0,-.06)、完整normal=(0,0,.119999997)；本次step_start=10.111202500409554、Nstep4044481，不是C阶段，也未改写旧失败时刻。上个保存帧中791尚未激活，B/GP最近距离.09761266/.10360087m均超过R=.096m；随后已穿底的前缘靠近外侧床点，与新激活失败相符，不冒称读取了未保存的完整邻域。

失败原输出的particles已独立导出Fluid/Bound各11帧。历史、场图和CSV在tests/figures/upl_c08_formal_failed_prefix_r1；manifest明确diagnostic_partial=true、solver_completed=false。原始BI4和PRE不变。

下一候选是已有人工应力的u-pl一致适配：Σ=σeff−absolute pI，Rraw=-εΣpositive（Pa），按Vj/rhot_i加权；仅gravitypreload撤墙后启用，PRE仍AS0，旧u-pw/默认AS0保持原路径。ε=.2、指数2.55是源码默认，不冒称论文参数。离线反事实仅显示减弱吸引，不能保证阻止穿透。候选组件、OFF回归及ON短窗待验证，正式XML/BAT/runtime尚未切换，其他两组及完整计算保持待定。

Lian2023公式19为剪胀角衰减，负压稳定是公式47，不是简单截零。本次ψ0=0，不将其作为未经验证的穿透修复。10s预载的准静态残余判断与撤墙后的动态边界失败分开记录。

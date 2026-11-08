# r5 ψ0在0.6–1s停滞的开关与材料状态只读审计

依据实际根输出 `CaseLianSaturatedColumnCollapse_psi0_shared_r5_GPU_out` 的生成XML/Run.out/已封口native，以及真实 `logs/upl_c08_bedkeep_Release_r1.build.json` 指向的 `outputs/upl_c08_bedkeep_source_r1/source.zip`。没有执行solver/decoder/build、修改记录、扫SHA或引入新验收门。

- **预载阻尼/Shepard没有直接泄漏证据。** XML SoilDamping=1/Coef=.02、PoreShepard启用是共享PRE认证要求，初始化日志36.1976852s−1不代表全程活跃。冻结GPU Single1079在唯一释放事件执行 SoilDamping=false、PoreShepardRegularization=false、ConstantDataUp；JSphGpu.cpp780向CTE写实际flag，Single671有host条件，GPU kernel712也有CTE条件。Run.out明确phase released/damping OFF/Shepard OFF；已通过reader逐帧门检查300个post metadata均false。
- **AS不存在.6s后新开关。** 冻结JSphGpu.cpp1471–1475只在未release的PRE清AS scratch，release后每个force stage根据当时total stress计算。原生300帧AS ReleaseOnly/Active=true/.2f/2.55f门已过。人工黏性α=.1持续存在；本审计不能从未导出的力分项量化其与AS耗散。
- **没有全局/定时velocity reset。** 冻结GPU Simple kernel413–415、578–580对soil按v_old+(a+g)dt更新；corrector549的(0,0,0)只在p<npb固定墙分支。host传实际Npb，非原CaseNpb。固定平面模式host1636传MDBC2_Std绕过旧NoPenShift改速分支，然后仅在试算穿plane时投影incoming normal（fcontact12–18），不是全局清零。数据在τ=.6/.7/.8/.9/1/1.5/2/3s的5000土粒均没有XYZ速度同时精确零的ID；这支持非整片硬清零，但不能证明保存间隔内所有局部接触投影都未触发。
- **材料/软化参数与内部Σ闭合。** 实际StepAlgorithm=2是Symplectic，DPCtes=3是DP_PS，MaterialLawVersion2是统一DP；这些不是同一个mode。phi=phi_r25°、nphi0（无φ软化），psi0、sf0、cp5000/cr1000/ncoh5。冻结FunSoilMaterial49–68给c(κ)=1000+4000exp(−5κ)，ψ=0；每次Return重评系数，没有以旧source κ0固化strength。PartBegin=false，PRE专用通道只恢复实际clock，不激活默认FOS1.65折减。GPU predictor429–432返回Σ但保留κold，corrector622–660才累计κ；返回器只操作Σ/κ，不直接改v。

对全部300×5000 saved soil的 **effective SigmaState** 独立重算DP_PS f=q+αI−kc(κ)：φ取实际float32弧度，α=.13685771076688075，kc=.880476918518473 c(κ)。max正残差7.40531268e−5Pa（τ≈.44，ID5344），没有f>1e−4Pa者；小正值不能当成精确零，浮点κ存储/系数与终点舍入需区别。此结果没有kPa量级屈服不一致，不能用totalΣ减p后再去判断骨架屈服。它仅验证内部状态一致，不证明论文κ定义、塑性应变云图或软化率已等价。τ1s有效c分布min/median/max约1000/4930.36/5000Pa，高κ区域已到残余，大片低κ材料保持近峰值。

结论：没有发现预载阻尼误留、AS晚切换、soil整片清零或统一DP/κ分支明显错用的直接证据。急停不能据此宣称正确物理平衡；仍应低成本分项检查.62–.64s自由面附近的压力脉冲、压力–力–Darcy通道、人工黏性/AS与残余吸力对运动的影响，暂不放行另外两ψ。

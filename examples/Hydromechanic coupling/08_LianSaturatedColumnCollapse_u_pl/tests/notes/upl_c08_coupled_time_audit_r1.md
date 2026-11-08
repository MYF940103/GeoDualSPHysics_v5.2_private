# C08 耦合场时间离散：源码与冻结线性代数审计

新note名事前Test-Path为false、精确git ls-files为空。本次只读当前源码和数学推导，没有实现、solver、reader、频谱计算或旧文件hash。实际0.66 s trace的MPa脉冲不由本推导自动归因；完整实际耦合谱尚未测量。

## 实际阶段与相位

`JSphGpuSingle.cpp:807–836`：n态force→predictor→half几何divide→half态force→corrector；完成几何divide在1234，TimeStep+=dt在1235。同一stage里main force在670，AS/AV等已加入Ace，wall Ace闭合与Darcy在`JSphGpu.cpp:1906–1917`，不是沿用上一stage的Ace。

令h=dt/2，a=Ace+g，r为完整动态Darcy/压缩率。在无contact/projection/inout、线性弹性分支和固定dt下，忽略浮点舍入：

    v_h = v_n+h*a_n,             v_new = v_n+dt*a_h
    sigma_h = sigma_n+h*R_n,     sigma_new = sigma_n+dt*R_h
    p_h = p_n+h*r_n,             p_new* = p_n+dt*r_h
    J_h = J_n+h*J_n*theta_n,     J_new = J_n+dt*J_h*theta_h.

v/sigma：`JSphGpuSimple_ker.cu:401–427,577–584,615–623`；p：`JSphGpu.cpp:1638–1648,1722–1730`和`JSphGpu_ker.cu:1352–1364`；J：`JSphGpu.cpp:1823–1838`、`JSphGpu_ker.cu:1389–1400`。pressure先写、随后J/v/sigma写的host顺序不造成额外一阶段lag：各RHS在该阶段更新前已计算完。rho cache的half/full J预览与J提交同式（`JSphGpuSimple_ker.cu:348–360`），不是继续用J_n作half force惯性。

位置另用 x_h=x_n+h*v_n，x_new=x_n+h*(v_n+v_new)；因此**完整含位置映射不能笼统称普通显式中点RK2**。若加速度仅依位置，该位置/速度组合有drift-kick-drift的特殊结构；这不保证以独立应力/孔压场传递声波的子系统也有辛/无耗散性质。

TimeStep在两次force中仍是t_n，InterStep区分2/3，第二次几何/场是half态。C08撤墙后g和参数恒定，不因此构成时变forcing相位错误；一般时变加载不能仅凭这个流程声称已用t_n+h采样。UPDATE沿用其RHS的FS，完成几何PONDING才重分类并有限正压置0。它既不改J/sigma/rate，也不是压力求解的隐式校正。

## 冻结线性field子系统的稳定函数

冻结几何、C、体积/惯性系数、active/FS与材料弹性分支，field y=(v,sigma,p,delta-J)可写成 ydot=L*y+constant；Darcy包含同stage机械a(y)，仍是一个显式组合RHS。场更新满足

    y_h=y_n+(dt/2)*F(y_n),    y_new=y_n+dt*F(y_h),
    R(z)=1+z+z^2/2,          z=dt*lambda(L).

对于无耗散声学模lambda=±i*omega，

    |R(i*omega*dt)|^2 = (1−(omega*dt)^2/2)^2+(omega*dt)^2
                      = 1+(omega*dt)^4/4 > 1   (omega*dt != 0).

因此该field映射没有非零纯虚轴绝对稳定区，可产生数值反阻尼；每步小参数时幅度增长约(omega*dt)^4/8，是否足以解释本窗必须知道实际omega*dt和耗散。HG已纯代数独立复核此式。它不是对实际C08算子的特征频率/增长率拟合，也不证明本次脉冲由时间法单独造成。

有耗散lambda=−a+i*omega时须核

    [1−a*dt+((a*dt)^2−(omega*dt)^2)/2]^2
      +[(omega*dt)*(1−a*dt)]^2 <= 1.

纯负实轴稳定区z在[−2,0]，但分别满足一个波速CFL和一个标量扩散尺度不自动等价于所有复杂耦合模均满足上式；非正规矩阵还可能有暂态增长。当前raw动量与C修正导数不成伴随、AS谱切换、FS切换等也可能改变半离散谱，不能将所有增长都归为时间法。

实际r5含塑性/软化与接触：predictor material return后恢复kappa旧值（Simple_ker:428–432），corrector提交新history（621–660）；这不是上述线性弹性映射的完整通用证明。PONDING/固定平面/壁面重构及可变几何/系数使完整映射分段非线性。无需据本线性审计更改这些已明确的原政策。

## 现有必要dt包含什么

**没有遗漏水体积模量Kw/n。** `JSphGpu_ker.cu:1435–1448`令B=Kw/n、M=K+4G/3，计算cu^2=(M+B)/rho；也检查连续正k衰减域 rho*B/(M+B)−rho_w>64eps*max(rho,rho_w)，并取D=B*ki/gamma_w。

`JSphGpu.cpp:1940–1963`使用同stage本征标量上界：wave=h/[max(cu,10*Vmax)+h*ViscDtMax]，pore=PoreDtSafety*h^2/max(D)。`1970–2002`再与force尺度及CFL合并、检查locked dt，并在1982–1983加grad-k必要尺度。代码明确称它们necessary，不是变量系数稳定性证明。

这些门没有装配/测量完整离散L的耦合复杂谱，没有验证R(dt*L)的稳定区域、非正规增益、AS/FS/边界状态切换。不能把“必要门全过”解释成完整耦合时间稳定已经证明；也不能把上述数学风险直接当作本次MPa峰首因。当前仅给定位和公式，不建议自动调dt、改积分器、merge候选或启动新算例；仍以已得到的真实stage项先后和后续受控诊断为依据。

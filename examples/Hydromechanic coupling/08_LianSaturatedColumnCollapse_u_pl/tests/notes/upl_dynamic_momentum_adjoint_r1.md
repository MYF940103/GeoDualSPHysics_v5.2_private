# 动态 u-pl 接收点 C 速度梯度的离散伴随

纯代数/当前源码只读核对；新名先查不存在且精确 git ls-files 为空。没有实现、求解、图或新公共参数。本 note 不将伴随关系不匹配直接认定为 r5 压力峰的已证首因；主线仍是三ID真实stage观测。

令 d_ij=x_i−x_j，g_ij=grad_i W_ij（列向量，g_ji=−g_ij），V_i=V0*J_i；冻结 V、rho、C 与邻域，限定双向完整fluid–fluid pair。代码以每个速度分量为一行，所以

    L_i = sum_j V_j (v_j−v_i) tensor (C_i g_ij)
        = Lraw_i C_i^T,    theta_i = trace(L_i).

`JSphGpu_ker.cu:796–801` 对每一速度梯度行作 C_i*grad；2066–2069先累积raw行，2248–2257随后修正/构造应变旋转与应力率。theta的double路径在1929–1954直接用接收Ci乘核梯度；CPU对应`JSphCpu.cpp:2429–2444,2611–2621`。动态准入要求两项梯度修正开启；一般默认非动态路径不应据本推导改动。

设 T_i 为对称的功共轭应力，Pint=sum_i V_i T_i:L_i。对无序pair归并得到

    Pint = sum_(i<j) Vi Vj (vj−vi) dot [(Ti Ci+Tj Cj) gij].

以冻结阶段 m_i=rho_i V_i 为惯性权重，取

    a_i = sum_j Vj/rho_i (Ti Ci+Tj Cj) gij

才有 sum_i m_i vi dot ai = −Pint。**矩阵次序是 Ti Ci；没有额外转置，也不能交换为Ci Ti。** 若将梯度写成行向量g^T Ci^T，表面上的转置只是同一约定。上述不要求Ci对称；对称T使反对称spin不贡献内功。

`(Ti+Tj)(Ci+Cj)/2` 一般不是这个伴随：两者差为 `(Ti−Tj)(Ci−Cj)/2`，只有T或C相同等特例才相等。单独把平均C塞入现raw pair并不能由此宣称与当前Li功共轭。

实际J权重：V0=MassFluid/rho0（GPU1772），rho_i=rho_w+(rho0−rho_w)/Ji（2182–2184）；现动量1833–1842使用Vj/rho_i与raw `(sigma'_i+sigma'_j−(pi+pj)I)g`，CPU2313–2322同义。这里冻结mi并非声称MassFluid等于当前rho_i Vi，后者随J包含水相质量变化；本等式不是完整可变质量混合物/时间积分能量守恒证明。

对当前总应力 Ti=sigma'_i−pi I，功共轭pair必须整体为

    sigma'_i Ci + sigma'_j Cj − pi Ci − pj Cj.

压力对应 `−p_i theta_i`。在冻结n/Kw下，压缩源pdot=−Kw/n*theta给局部储水能量导数(n/Kw)*p*pdot=−p*theta，与总应力内功符号一致。只修压力或只修外载而留有效应力raw，不能获得同一个总应力伴随。当前stress-L用float累积再修正、theta用double，严格程序级恒等式还受实际舍入/支撑/边界差异限制。

## Cryer全常总应力与配套外压

当前FlexibleConfinement外压q的J pair为 `+2q Vj/rho_i gij`（GPU1853–1859；CPU2333–2339），与raw总应力T=−qI逐pair抵消。若总应力改成上述伴随力，配套外压也必须在同pair/权重/邻域上成为 `+q Vj/rho_i (Ci+Cj)gij`，才仍逐pair抵消。若有非零常有效应力而只改p/外压，raw有效应力留下的缺陷不会自动消失。TopKernelBand还存在独立选带/全局归一化（`JSphGpu.cpp:1282–1291`），不能把Cryer常量抵消直接推广为所有载荷正确。

## 限定

该流体pair公式保持冻结mi下线性动量pair反对称，但不是自动的逐pair中心力或全场角动量/自由面牵引证明。固定墙ghost不是独立自由度，NoSlip/FreeSlip image、MLS、外部反力与投影须计入对应边界功；不能把上式直接当完整mDBC/contact变分推导。AS/AV是额外稳定/耗散算子，其功不包含在sigma'材料内功里，若保持原式应明确作为独立项；不能为了本代数关系顺手改其数学。Darcy的Lstar/FS切换、可变k链项和时间层也不由本伴随关系自动证明稳定或配套。没有据此提出立即merge或新增算例。

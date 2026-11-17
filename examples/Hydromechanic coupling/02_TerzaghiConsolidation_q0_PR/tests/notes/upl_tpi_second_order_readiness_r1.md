# 二阶空间算子盘点与最小后续比较

2026-11-18。仅离线阅读本地文献、冻结源码及已有结论/收据；本轮只新增此说明。正在运行的 P3 full2Tv、暂停的 C08、全部原始输出及依赖均不改变。不构建、不求解、不解码、不扫 SHA；下述比较尚未准入或执行。

## 文献编号与当前离散

`src/papers/u-pw/Lian 2023 u-pl.md:259–267` 的 **Eq.(19) 是剪胀衰减** `psi=psi0*exp(-sf*kappa)`，不是孔压二阶空间导数。目标空间公式为 p.6 **Eq.(23)**；Eq.(22) 是 receiver-C 一阶梯度，Eq.(25) 才将扩散、加速度散度和变 k 项组合为孔压率。已有 `C08/tests/notes/upl_lian_second_derivative_scope_r2.md` 已据保留的 p.6 页面核过公式，无需再据 OCR 猜符号。Eq.(23) 来源为 Lian et al. 2021，CMAME 387, 114169，Eq.(49)–(52)；它消去 Taylor 一阶缺陷，不保证任意失序/截断支持上二次精确或全局二阶收敛。

以 `r=xj-xi`、`g_hat=Ci*grad_iW` 表示，二维原文为

`Gf=sum Vj*(fj-fi)*g_hat`；`Ftilde=(r·g_hat)/r²`；
`Hmn=sum Vj*[(fj-fi)-Gf·r]*(4*rm*rn/r²-delta_mn)*Ftilde`。

二维 `trace(D)=2`。在相同支持/体积/核、无边界梯度替换下，其迹等于 **receiver-C/bare** 的标量 `LP-Gp·Lx`，不是额外的二次精确矩阵。三维不能直接照搬系数 4：需先核维数推导，使迹及混合导数均与三维连续量一致；不可只删 2D qualifier 冒称 3D 原文实现。

冻结 `outputs/upl_tpi_m0_dt_CPU_r2_source/JSphCpu.cpp:4456–4501` 的当前动态离散为 `d=xi-xj`、`gi=Ci*g`、`gj=Cj*g`、`w=Vj*d·(gi+gj)/(r²+Eta²)`，同时累计 `LP=sum w*(pi-pj)`、`Lx=sum w*d`、receiver 梯度 `Gp` 和 `Da=sum Vj*(Aj-Ai)·gi`；完整 `lap=LP-Gp_corrected·Lx+rho_w*Da`。闭合自由面的 Neumann 梯度、真实墙延拓和变 k 链式项另保留。当前 P3 的时间反馈轮数没有替换此空间算子。

只在 Darcy 的 LP/Lx 一起去 Eta，不等于删除全局 force/AV 的 Eta。原 `r²<ALMOSTZERO` 排除仍须保留；核梯度为 `Fac(r)*r` 时正距离趋零的商可有界，但这不证明近重合浮点数、退化 C、缺邻域或耦合谱安全。原 LP 的 reciprocal pair-C 有条件的体积加权互易性；receiver-C 一般失去该身份，完整 Taylor/Da/边界/变 k 算子也不能只靠 LP 身份宣称耗散或守恒。

## 已测证据：不重复旧窗

| 已完成证据 | 结果与解释 |
|---|---|
| C02 `upl_lian_eq23_root_review_r1.check.json`、`upl_lian_scalar_kernel_r4.review.json` | 完整张量/标量、六个 64×64 谱及 receiver/pair × Eta/bare、核/float-double 已分开审查。literal x² 张量相对误差约 3.8044%；失序矩阵对称部分可有正特征值而全矩阵实部近零，不能混为同一稳定结论。 |
| C02 `notes/upl_lian_variable_root_r1.json` | 1536 个压力/变 k 响应未显示 pair-mean k 一贯优于现 product-rule；不再用更换 k 平均掩盖 C/分母差异。 |
| C02 `upl_darcy_eta_wave_review_r1.review.json` | 相同 512IDs/512 更新/257 状态的周期弱波：去 Eta 后连续参考最大压力 RMS **7.51603→8.23672 Pa（+9.5887%）**；端点压力幅值误差 1.4716%→1.6127%。保留原分母；这是有限 Kw、小扰动组件，不是 TPI/M0 或墙面准确度证明。 |
| C08 `c08_h18_joint_eta_decision_r1.md` | 相同实际失序快照、LP/Lx 同改的制造场：去 Eta 大幅降低曲率场残差；receiver/bare 绝对小残差的排序受算术预算限制。已有真实 H/N/X、墙/解析 ghost 对照，不重复同一四权重矩阵。 |
| C08 `c08_h18_lstar_window_outcome_r1.md` | H1.8 receiver-C/bare 的 .90s 窗口末态压力 RMS 降 4.1214%，但全窗最负压幅值增 26.75%，最小 NN .270834→.269218dp，近对缺陷仍在；**未选为修复**。 |
| C08 `c08_h18_paircbare_outcome_r1.md` | H1.8 pair-C/bare 末态压力 RMS 仅降 .4946%，最小 NN .270834→.256531dp，峰值近对 `<.5dp` 13→15、`<.3dp` 1→2；**未选为修复**。 |

旧 H1.2 Eta0 的强吸力反例，以及 `upl_c08_rvisc90_decision_r1.md` 的必要时步失败均保留。RV 是新增机械残差黏性，经真实加速度进入 Darcy，并不是 Eq.(23) 的另一实现；H1.8 零推进 RV 组件也出现早期率/局部吸引恶化，不能重复调黏性替代空间一致性。以上 .90s/组件结果不准入三组正式塌陷，不证明团聚唯一来源，也不否定所有二阶方法。

## 未覆盖处与最小有意义的下一项

**当前选择：保留 pair-C/Eta，不给活动全程加入改动。** 二维常标量 k 下再实现完整 Hessian 后取迹，主要会重复已测 receiver/bare；只有真实新覆盖才值得增加成本。未闭合的是维数一致 XYZ 完整张量、真实三维截断支持/近重合条件、各向异性 k 的混合项，以及修改后完整耦合轨迹的精度/稳定性；现有变 k 测试不是不连续界面保守通量验收。

后续最小组件可选**一份已保留的 Cryer 真实快照**，用该快照匹配的源码/ABI，固定 ID/J/当前体积/kernel/h/active-wall/FS 分类，至多 81 接收点一次建立全粒子支持。对 `1,x,y,z,x²,xy,xz,y²,yz,z²` 及一个光滑模式，比较现 pair-C/Eta、pair-C/bare、维数核准的 receiver/bare；输出六个 Hessian 分量、迹、误差及 C conditioning，完整/截断支持分别报告。旧二维平面算例不重做；各向异性张量收缩只列为制造场诊断，不同时开发新的 k 模型。

这份原生 typed22 没有 CorrMat/完整 Ace：纯几何重建只能叫离线离散诊断。若要实际完整率见证，须另准入**一次零推进组件**，先按原顺序刷新 C/FS、墙 state/C/Ace，再调用原 Darcy；不得把制造边界与不相容自由面强行比较，也不把制造 Ace 写回原物理真值。先核原实现回放/量纲/原 roundoff、finite、非空合法内点门，再比较误差和实际调用/内存/耗时；不预设亚秒收益，不先增加持久全场数组或第二次邻居遍历。

只有混合分量与光滑误差确有稳定收益、常量/仿射及静水驱动力抵消未退化、原必要界和实际冻结矩阵检查不出现新反例，才值得根线程决定下一有界耦合比较；误差只在不相容边界改善、近对权重恶化、或只改善制造场而不改善原物理预算时拒绝合入。完整物理仍沿原孔压/沉降/应力预算和实际时钟评价，无新 half/reference 链、无拟合半径/时间/荷载，也不从正常出口自动验收。

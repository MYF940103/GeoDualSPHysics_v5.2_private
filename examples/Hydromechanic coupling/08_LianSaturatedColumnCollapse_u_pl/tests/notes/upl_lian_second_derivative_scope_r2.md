# Lian 二阶空间导数与下一步最小核对

本轮只读原文及已闭合证据；仅新增此 note。没有修改生产/输入、构建、求解、解码、重跑旧算子或 SHA 扫描。材料支线 `d3c743b` 不因本文改变。

Lian 2023 的目标是 printed p.6 **Eq.(23)**，不是材料系数的 Taylor 返回。原文 `src/papers/PDF/Lian 2023 u-pl.pdf` p.6 已按已有整页 `validation/upl_refs_r1/lian_p06.png` 目视核对；对应 MD `src/papers/u-pw/Lian 2023 u-pl.md:294-320`。Eq.(22) 是接收粒子的归一化一阶梯度；令

\[
\mathbf r_{ji}=\mathbf x_j-\mathbf x_i,\quad
\widehat{\mathbf g}_{ij}=C_i\nabla_iW_{ij},\quad
\mathbf G_i f=\sum_j V_j(f_j-f_i)\widehat{\mathbf g}_{ij},\quad
\widetilde F_{ij}=\frac{\mathbf r_{ji}\cdot\widehat{\mathbf g}_{ij}}{r_{ji}^2},\quad
D^{mn}=4\frac{r_{ji}^m r_{ji}^n}{r_{ji}^2}-\delta^{mn}.
\]

则 Eq.(23) 可合并写成

\[
H_i^{mn}f=\sum_j V_j\big[(f_j-f_i)-(\mathbf G_i f)\cdot\mathbf r_{ji}\big]D^{mn}\widetilde F_{ij}.
\]

第二项消去 Taylor 空间展开的一阶缺陷；“求二阶空间导数”不等于任意失序/截断邻域二次精确，也不等于保证二阶收敛。这里的系数4来自该二维推导，不直接移植三维。

准确来源是文末 Ref.[36]（MD:1289-1291）：Lian et al., *A general SPH framework for transient seepage flows through unsaturated porous media considering anisotropic diffusion*, CMAME 387 (2021) 114169, DOI `10.1016/j.cma.2021.114169`。本地 `src/papers/PDF/Lian 2021 seepage flow unsaturated porous media.pdf` printed p.13 **Eq.(49)-(52)** 给出二维分量及同一 index 公式；p.15 **Eq.(54)-(57)** 将其用于变渗透率/总水头 `H=h+z`。2023 p.6 **Eq.(25)**（MD:334-351）才是孔压率的组合离散：pair-mean k 与 receiver-k 缺陷不同。其印刷压力缺陷前未重复显示 `1/gamma_l`，已有审查正确保留量纲歧义；不得照 OCR 漏掉单位因子或据此断言作者程序错误。2023 Eq.(26) 的 `C_ij` 是稳定项，非这里的归一化矩阵。

材料支线中 `src/source/FunSoilMaterial.h:49-70,105-109` 的 `dDP_phi/dkappa`、`dDP_kc/dkappa`、`dDP_psi/dkappa` 及 endpoint scalar-root 导数属于局部本构历史/返回算法；Taylor 比较法在 lambda=0 线性化同一局部残差。它们不计算 `partial²p/partial x_m partial x_n`，材料成本/收敛结果不能作为 Eq.(23) 的空间验证。

当前 CPU `src/source/JSphCpu.cpp:4285-4299,4304-4325` 已累计 `lp,lx,gp,div(Ace),grad(J)`，采用 `V_j=V0*J_j`、pair C、`r²+Eta²`、receiver-C 一阶梯度及独立 FS/墙策略。二维 `trace(D)=2`，仅在相同邻域/体积/核、pair 两端均代 receiver C、Eta²=0 且不替换边界梯度时，Eq.(23) 的迹可与 `L*p=Lp-Gp·Lx` 代数一致。现 symC 是互易/标量扩散选择；当前算子仍非原文完整 Hessian。FS raw-total-head 和墙延拓也不能随空间算子比较被悄悄改回。

既有证据已做，下一步不重跑同一矩阵：

- C02 `tests/logs/upl_lian_eq23_root_review_r1.check.json` 已闭合完整张量/标量/六个64x64谱检查；literal x² 的该次张量相对误差为 `.038043963290819945`。失序矩阵的全矩阵谱与对称部分谱结论不同，不能用常量零响应或标量迹证明耗散/守恒。
- `tests/logs/upl_lian_scalar_kernel_r4.review.json` 已分开 receiver/pair C 与 bare-r²/Eta²，Wendland/Cubic 及 float/double 压力；`tests/notes/upl_lian_variable_root_r1.json` 已闭合1536个压力/变k响应，未显示 pair-mean k 统一更优。它们不是实际变形墙/自由面或耦合轨迹验收。旧 symC startup 的安全/默认回归亦非 Eq.(23) 精度结论。

最小新增项应针对**未覆盖的真实失序/当前墙几何**：只用一份已封闭的 C08 变形/撤墙后快照（若尚无此快照就暂不冒称已覆盖），固定原 ID、J、当前体积、kernel/h、active-wall/FS 分类；至多81接收点一次 all-particle 支持枚举。制造 `1,x,z,x²,xz,z²` 加一个光滑模式，输出 `Hxx,Hxz,Hzz`、迹、conditioning，分真实完整/截断支持报告。`xz` 及 trace-zero 的 `x²-z²` 可区分张量问题与标量拉普拉斯；边界解析值与条件离散/真实镜像 oracle 分开，不能把不相容制造边界当误差门。保持当前静水总驱动力抵消及自由渗流正压策略，变k沿已测链式项另列，不把两种方程同时切换。原 forward-roundoff、finite 与非空内点门保留；二次/光滑误差只先量化，不新增拟合阈值。

代价仅是假设：81×7060约57万几何配对可一次建支持后复用各制造场；这不是实测秒数。常k只取迹时现有累计已具备对应结构，完整二维 Hessian 可增加局部三分量及一阶缺陷矩累计，不必先加持久全场数组或第二次邻居遍历。实际成本/收益需在同一冻结数据上另计时；旧 standalone 的亚秒结果不能外推整个 SPH 或 GPU。本文不启动新 benchmark、不改变 public gate，也不扩展 TPI。

CPU/GPU交叉定位：动态率入口为 `JSphCpu.cpp:4239` / `JSphGpu_ker.cu:1659`，成对压力权重及receiver梯度分别在4290–4300 / 1696–1716；变k另加 `k'(J) gradJ·(gp+rho_w Ace)`，并非保守界面通量。旧 `PoreDarcySymmetricCorr` 只控制u-pw soil-soil，dynamic在 `JSph.cpp:658–659` 明确拒绝该旧选项，不能据XML中旧开关为0认定dynamic没有symC。Wendland/Cubic分派为CPU4348 / GPU1762。

公开typed22没有 `CorrMat` 或总完成 `Ace`；`HydroMechLoadAce` 仅为外载加速度。离线重建矩阵/制造加速度只能叫离散诊断，不能宣称重放原生产完整率。若后续需要真实调用见证，应在同一固定快照执行一次零步 `FS/C -> 墙state/C/Ace -> Darcy rate`，保留原边界策略，不加时间积分、half链或长算。旧服务器case08 r2、当前已验收数据均不改变。

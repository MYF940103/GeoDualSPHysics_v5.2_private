# 固定强度 DP / apex 解析候选（作者说明，未执行）

文件：`tests/support/upl_material_apex_candidate_r1.h`；独立 namespace `fsoil_apex_candidate_r1`。未修改 general 候选、生产代码或旧已闭合文件；未构建或运行。用途是固定强度材料点的解析基准，不能把它当成已经完成的软化模型。

输入 `State` 为六个 double 应力和 float κ；`Material` 保留 float `ModulusK/ModulusG`，给定 double `DP_phi/DP_kc/DP_psi`。不带 CPU/GPU 主循环 adapter，不设置新的张拉强度/损伤参数。`Return(input,m)` 的失败结果保留原状态；`CommitAllowed` 明确区分可提交分支。

## 分支顺序

1. `ftrial=qtrial+DP_phi*Itrial−DP_kc≤0`：Elastic。这个解析基准使用数学 f≤0，不采用生产路径已有的1e−5弹性阈值。
2. φ系数严格为0：圆柱屈服 `q−kc`，不计算 kc/α。`qtrial=0` 时按 f≤0 自然弹性；需剪切返回时 λ=(qtrial−kc)/G，径向到 q=kc。保留输入的 β 塑性势：通常 J2 情形 β=0，但不静默把非零 β 改零。
3. α>0且合法光滑根存在：优先 λ=ftrial/(G+9Kαβ)，要求 λ非负、λ≤qtrial/G、qnew≥0。最终 κ增加 λ/√3；qnew=0端点标为 Apex/SmoothEndpoint（同一流动势的极限）。不把 D≤0 直接当非法材料：继续检查联合顶点/张拉分支。
4. 没有合法光滑根时，先尝试正β的原 g 纯 apex：IA=kc/α，λA=(Itr−IA)/(9Kβ)，且 λA≥qtr/G。σnew=IA/3 1，κ增加 qtr/(√3G)。`lambda_shear=lambda_apex=λA`，不能把这个总λ继续拿来算 κ。
5. 无合法前述分支时，按根明确要求保留既有上限 `It=kc/α` 的附加张拉流：取 λs=qtr/G，λt=(Itr−It)/(9K)−βλs；只有 λt≥0 才接受。最后 q=0、I=It、κ增加 qtr/(√3G)，状态显式为 **TensionRepair/JointExistingApexCap**。λs为剪切端点乘子、λt为附加张拉乘子，`lambda_apex=0`，`repair=true`。允许由于剪切收缩把 trace 推到顶点、从而 Itr≤It 但 λt≥0 的情况。
6. 其余状态为 NoAdmissibleFlow，有限输入却算出不可表示的输出会给 UnrepresentableState。这里没有 Newton 迭代，不能把物理不可达、浮点不可表示与迭代不收敛混为一谈。

此处保留的是旧张拉上限的含义，不声称新联合分支与旧 fast 的顺序投影逐字节或所有应力路径一致。没有加入独立张拉损伤历史。对负ψ也不承诺全域正塑性功；TensionRepair 不是原单一 g 的解。

## 供根独立测试的等式

以下外部诊断不埋入候选结果当成自证：

\[
q=\sqrt{\tfrac12s:s},\quad
\Delta e^p=(s^{tr}-s)/(2G),\quad
\Delta\varepsilon_v^p=(I^{tr}-I)/(3K),\quad
\Delta\kappa=\sqrt{2\Delta e^p:\Delta e^p/3}.
\]

- Smooth 与 pure Apex：`I=Itr−9K β λs`，且 smooth λs≤qtr/G；pure apex λs≥qtr/G，次梯度范数≤1/√2。
- TensionRepair：`I=Itr−9K(βλs+λt)`、λs,λt≥0、q=0、fs=ft=0；这是双流动势的联合分支。
- 同轴端点机械塑性功：`Wp=q(qtr−q)/G+I(Itr−I)/(9K)`。记录真实值，不能截负值再宣称物理耗散已证明。
- 所有分支用最终构造出的六个应力再次独立求 I/q/f，检查连续 κ 与 float保存 κ，并区分保存舍入。候选的 `returned_I/q` 来自最终应力，不伪造理想 q=0 元数据。
- 应力旋转前后应等变，κ、分支和不变量应一致；测试所有三个法向及三个剪切分量。

`GetInvariants` 对角应力使用成对差的等价 J2 式，避免相同三个正应力在求平均时造出非零 q；没有给 q 或 β 增加任意物理 epsilon。近端点若真实运算舍入导致不满足解析可行不等式，会如实拒绝，不通过 clip 把不合格状态强行提交。

下一步是根全文审查，再进行固定强度解析/原 g或联合流动/κ/功/旋转 CPU-GPU 材料点验证。随后一般软化模块必须使用 κA 上的现有强度系数及导数，并重新处理径向路径多根；不可直接把本候选冻结强度当成完整的软化积分。

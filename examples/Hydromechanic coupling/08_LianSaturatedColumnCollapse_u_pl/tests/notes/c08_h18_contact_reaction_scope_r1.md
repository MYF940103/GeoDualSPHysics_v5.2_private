# C08 固定平面反力：真实时间层与最小候选范围

2026-11-14，只读审计及本说明。未改源码、构建、调用 force、推进、native、VTK、PRE 或 Git；不选择/准入新物理模型。依据当前原 schema2 `outputs/c08_preload_schema2_source_r1/full_source.zip` 内六个原文件，直接读取归档文本而非扫描 SHA。以下行号均为该归档，不是新 observer 的行号。

## 现有实际更新

`JSphCpuSingle.cpp:897` / `JSphGpuSingle.cpp:807` 每全步以既有 `SymplecticDtPre` 为 Δ，先 n 态 force，后 predictor；cell divide 后以预测态再 force，再 corrector。`DtVariable` 为随后步长提供限值，不在当前 force 后重新改变本步 Δ。令 h=Δ/2，a_n/a_h 表示原 Ace（不含 Gravity），g 为 Gravity，round_f 为代码实际 float 提交。C08 无 shifting/inout/floating，单个左/床法向分量为：

```
predictor:
  x_h* = x_n + h v_n
  v_h* = round_f[v_n + h(a_n+g)]
  p_h* = round_f[p_n + h R_n]
  J_h  = J_n + h J_n theta_n

corrector:
  v_f* = round_f[v_n + Δ(a_h+g)]
  x_f* = x_n + h(v_n+v_f*)
  p_f* = round_f[p_n + Δ R_h]
  J_f  = J_n + Δ J_h theta_h
```

这里 corrector 的 v_n/x_n 是保留的 Pre 数组，不是 v_h/x_h；更新 v 的系数是 Δ，不是 h，虽然力在预测态求值。GPU kernel 的 `dtm` 在 predictor、corrector 都传 h，但 corrector 只把它用于位置；速度、压力、应力和全 J 使用单独的 Δ。CPU/GPU 保留各自的实际浮点操作顺序，以上等式仅解释层次，不替代原生 bit 检查。

精确位置：CPU `JSphCpu.cpp:3417/3478/3571/3643`；GPU host `JSphGpu.cpp:1745/1836` 和 `JSphGpuSimple_ker.cu:489/671`。CPU predictor p/J 先更新，再材料/速度和投影。CPU corrector 先材料/速度/位置投影及位置提交，再 p/J；GPU corrector 全 J 在投影前、动态 p 在位置提交后。两者的 R_h 都已经在此前 force 求出，不能因 p 提交在投影后就称其含投影反力。材料应力率和 theta 也来自相应 force 的既有速度梯度；不应事后重写它们来制造一致。

## 现有投影不提供 force-stage 反力

`FunFixedPlaneContact.h:12`、CPU 两个 update 内调用、GPU `KerProjectFixedPlaneContact:445` / host `:1814/:1881` 使用同一规则：若 `x_n+move <= plane`，把 move 改为 `plane-x_n`；只有试算速度为负才清零法向速度。否则不改。其位置 move 已由清零前的速度算出，随后再单独夹到平面。

因此不能一般地把最终 `(v_projected-v_trial)/h` 当作某个 force-stage 的反力：

- predictor 的位置根本不含 a_n；仅改变 Ace 不会阻止当前 vn 导致的半步穿透。
- corrector 的速度基准是 vn，影响系数 Δ，而非 h；若把 predictor 的接触 impulse 又累计到 vn，便会双计。
- 对有限 gap 的新撞击，强行令最终 v=0 后，原梯形位置仍为 `x_n+h vn`，不一定等于 plane。想同时满足精确碰撞位置和入射/反弹速度，需额外的碰撞时刻/约束时间离散，不能靠一项常加速度普遍实现。
- 不应把事后位置修正除以 h²、把动量修正除错时长，或仅给 Darcy 增添巨大脉冲却保留旧固体更新。也不能再加一次 g。

现有实际 Darcy 在 CPU `JSphCpuSingle.cpp:749` / GPU `JSphGpuSingle.cpp:687` 于原力、AS/AV/阻尼/加载/HG 后求值，早于上述更新投影。其 `Da` 含邻域加速度差，FS 分支和变 k chain 还显式含 receiver Ace。若以后改 Ace，必须在所有土体反力加完后调用完整原 Darcy，不能只手补某个 receiver 的 `a·Lx`，漏掉邻居反力、chain 或原压缩项。

## 真正最小、但仅限已有静止支持的候选

供 root 后续取舍，不是实现许可或完整接触闭合。仅对一个静止下平面，内法向 e 为 +x 或 +z；接触门使用原精确 plane，不拟合新距离阈值。

Predictor 限定 `x_n=plane` 且 `e·v_n=0`。Corrector 额外要求原 n 态同样静止贴墙、当前预测态 `x_h=plane` 且 `e·v_h=0`；不能仅凭预测态刚被夹住就把它当成整全步静止支持。此时令：

```
lambda = max(0, -e·(a_free+g))
a_contact = lambda e
Ace = Ace_free + a_contact
```

该限定下向内自由加速度被抵消；两次原速度公式及原位置公式都给出法向静止，几何投影只是无改动保险。若自由加速度向外，lambda=0，应允许脱离，不能强制黏住。只改法向，不替代现有侧 FreeSlip/床 NoSlip 的切向 mDBC。静止两正交面逐分量独立；曲面、斜面、移动面及一般多接触不在此候选内。

最小插入位置是在 CPU/GPU `Interaction_Forces` 原 Ace 完成、原 Darcy 之前。读原/Pre 及当前阶段 x/v，计算并一次加入反力加速度，然后原 Darcy 和原实际 update 都读取这个同一 Ace。实际 update 仍只加一次 g；不在其后再补同一个 impulse。阶段反力的记账冲量分别是当前阶段真实质量 m_n lambda_n h 和 m_h lambda_h Δ；后者是 corrector 从 vn 出发的全步试算，不应再把 predictor 冲量加到最终动量。当前混合质量应取与该力阶段原惯性相同的 J/ρ/V 约定，不能拿 m0 与更新后 J 混用。

仅改加速度不会倒改当前 force 已用的 x/v/FS、theta、Rsigma；下一阶段自然重算。不存在为了该反力立即二次提交 kappa/J/p 或重跑材料的理由。需要保存真正使用的反力及门状态，报告“已有静止支持闭合”，而不是把总体 `ReactionClosed` 改 true：新撞击、非零 vn、有限 gap 情况仍沿旧投影，原缺口并未全部解决。

## 最少验证及取舍

先用原固定状态核真实活动量与压力敏感性；不为此另跑 PRE 或 half。候选若以后实现，先验证静止支持、向外脱离、两面角以及未激活路径原结果；控制只改法向且固体/墙冲量相反。在支持门内法向位移/速度零、无正接触功，静水原 Darcy 不出现新漂移；独立检查完整 Darcy 对两端反力的响应。OFF 及无接触路径应保持原精确结果。GPU 最后才需要其小窗/memcheck，不以 CPU 相同 exit 冒充 GPU 字段一致。

该 O(N) 候选比塑性大转角 HG 小，但既有近对“邻域含 fixed”不证明真实投影/反力发生。严重无 fixed 近对仍存在，它不能保证修复所有团聚。若当前固定状态压力反馈主要在无墙区域呈正，匹配力学/体积/Darcy 离散应优先。一般冲击/全接触闭合需另行设计时间层，不能由此说明直接扩大；本说明不解锁其他 psi，不降低原 native/步长/几何门，不作物理验收。

## 现成两个实际单步的触发量：均为零，不优先试跑

继续只读已经通过的 `outputs/c08_h18_as03_step_r1_p38` / `_p76`：各35000行 `stages.csv`、5000行 `balance.csv`，以及同次原初始化 `CfgInit_NormalsGhost.vtk`。后者存储完整 ghost boundnormal；`CfgInit_Normals.vtk` 仅画到 boundary limit，长度为一半，不能误作 runtime 的 raw normal。原 `JSph.cpp` 初始化先输出前者半长、将 raw normal 乘2、再输出 Ghost，并以 `x+raw*.5` 判平面。

由 Ghost 的原 double positions 与 float full normals、各面初始首样本，实际两个 plane 均为 `7.152557435219364e-9` m，全部样本的 location spread `8.493661884934056e-9` m，小于原 `1e-6*dp=4e-8` m 容差；这里没有把名义 XML plane=0 强制当实际二进制 plane。

|Part|force阶段|最小左面gap [m]|最小床面gap [m]|两面各自恰plane / 法向v=0支持 / eligible|
|---|---|---:|---:|---|
|38|n|.019190849488509888|.004455680154428479|0 / 0 / 0|
|38|h|.019190839276725494|.004455739713056605|0 / 0 / 0|
|76|n|.01826046999308049|.003929460254948298|0 / 0 / 0|
|76|h|.018260461197817362|.003929433029972659|0 / 0 / 0|

全四个 force 状态、每态两个法向均无候选，lambda 无可定义样本范围，不能报告为测得 lambda_max=0。两个完整实际单步的8个原 pre/corr contact Δx/Δz/Δvx/Δvz，全5000材料ID最大绝对值分别恰0，与上述不贴墙结果相容。只证明这些保存态和随后单步没有这类投影/支持事件，不推断全3秒 contact 从未激活。

根同时告知本轮固定状态压力组件的初始 altX 与两个 pair 扰动，all/no-fixed 的 Q/N 为负；constant 的全域正值改变自由表面牵引，不是 gauge-null。该组件的实际数值/原收据由根另行分析，不由本说明认证。这些有限方向不是全耦合谱，但当前不支持为了“ReactionClosed=false”的标签直接开接触修复物理窗。**窄 resting-support 候选在当前 onset 样本零触发，现阶段不优先实施或试跑。** 若以后完整轨迹确有 contact 事件，再基于其实际时间层重审；不扩大门到“接近墙”以人为制造触发。

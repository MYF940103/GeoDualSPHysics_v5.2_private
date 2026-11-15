# C08 H1.8 强人工应力与墙拟合失败审计

本轮只读既有封存日志、检查和源码，新增本说明；没有求解、解码、构建、哈希扫描、改阈值或实现新回退。范围是原始 Wendland H/dp=1.8、dt5us、psi0、同 schema2 PRE、原 AV.1/FS/固定平面 NoPen 的 AS 参数比较；不把 centroid、FS-normal、effective-AS、Shepard 或 RV 干预混作单 AS 对照。正常完成和原生安全通过均不等于塌陷物理验收。

## 已确证的 wall803 首因

`c08_h18_wall_fail_probe_GPU_r2` 的真实 solver/tool/Win32 出口为1。终端原文记录 `stage=0, native_id=803, step=2066541, step_start=10.332704999693412`；实际只保存34帧，最后 Part33/global2066001。它是 ε=.7、指数3.825 的输出型失败重放，与原失败34帧的22数组、实际 time/layout 和含 signed dterror 的时钟前缀逐字节一致，未重写头或重建未保存状态。

唯一可明确分类的终端分支为 `geometry_exhausted_or_ineligible`。最近真实供体重试后的原始 determinant 为 **0.00099994024237409817 < 0.001**；`active=1, incomplete=0, positive_sum=1, finite_det=1, nearestfinite=1, retried=1`，sumW=.23639364783602226。nearest J=1.0129547698751817，receiver J_before=1.0177093535167423，solid0=.65000000596046448。该次失败发生在几何准入之后的矩阵求逆、拟合字段及 stage0 J 域检查之前，故不能归因于已观测的无效供体 J、外推 J 非饱和或 material-return 拒绝。

**这是现有一阶镜像拟合的 determinant 安全门失败，未证明矩阵数学奇异或零秩。** determinant 有限且非零也不能证明其拟合误差、安全性或条件数合格，不能以略低于门槛为由降低 .001。原程序已经包含一次 nearest-real-source 重心移位重试；不是完全没有回退。打印的是最后一次重试的 moment，未提供全部原始/未保存粒子数组。多处相邻墙样本同时报告此分支，atomicMin 最终报告803，不能声称只有803异常。

stage0 联合拟合 J、去静水头孔压、全速度与六应力分量；stage1 为 C，stage2 为 Ace。因此这不是已经定位到 Darcy LP 分母、stage2 加速度反射或某一个孔压字段的单独错误。

证据：`logs/c08_h18_wall_fail_probe_GPU_r2.{solver.log,terminal_review_r1.json,prefix_r1.check.json}`；原门与分支位于 `outputs/c08_preload_schema2_source_r1/full_source.zip::src/source/JSphGpu_mdbc_ker.cuh`，终端 printf 版本为 `outputs/c08_h18_wall_fail_gpu_r1_build/frozen/src/source/JSphGpu_mdbc_ker.cuh`（geometry 约132–149行，之后才 inverse/字段/J 检查）。

## Centroid 为什么未选

候选在原 mirror 和 nearest 两次几何尝试失败后，额外使用正 W*V 供体质心重试。它会重新搜集/加权供体，属于物理重建干预，不是纯坐标平移，也不保证有效 MLS 权重正性、外推 J 域或接触/守恒闭合。原 .001/J 门保持不变。

`c08_h18_centroid_a07_GPU_r1` 越过原803，但仅多推进3052次更新（.01526s），随后 `wall808/stage0, step2069593, step_start10.347964999692834` 再失败；出口1，35帧，最后 Part34/global2068001、t10.340004999693136。新808只有通用异常，没有同级终端分支 printf，**不能外推为同一 determinant 原因**。前34帧全部原生/时钟字节保持原样，第35帧无旧对应态。

35帧窗最低孔压−123.244kPa、最大 pRMS43.505kPa、最小 NN=.338509dp；末保存112对 r<.7dp、2950/5000负压粒子，仍无物理修复证据。它既未完成.9s，也未形成可选的长期边界方案，因此被退役。公共 CPU/GPU mDBC 源已恢复到原 schema2 归档精确字节，恢复后的默认 DebugCPU 构建通过；候选 Git `1116bcba1c00de204549a0729440e2f699063586`、源码 ZIP、隔离程序及失败记录完整保留。

证据：`notes/c08_h18_centroid_rejected_r1.md`、`notes/c08_h18_wall_centroid_candidate_r2.md`；`logs/c08_h18_centroid_a07_GPU_r1.{terminal_review_r1.json,prefix_r1.check.json}`、`logs/c08_h18_centroid_partial_review_r1.check.json`、`logs/c08_h18_centroid_restore_r1.json`。

## 另一指数下的 .7 失败与 .5 取舍

ε=.7、指数2.55 的真实通用异常是 `wall808/stage0, step2065916, step_start10.32957999969353`，solver/Win32 出口1。实际33帧最后 Part32/global2064001、t10.320004999693893、tau=.32000499998788534；不能把异常报告时刻当已保存状态。该分支无 wall803 型 printf，具体几何/字段/J 原因仍未细分。最后保存 pRMS31.0804kPa、最小 NN=.438078dp、64对 r<.7dp。证据为 `logs/c08_h18_a07_n255_r1.solver.log` 与 `logs/c08_h18_a07_n255_partial_review_r1.check.json`。

已完成 .5 两个指数的 .90s 窗口有明确取舍，均非物理验收：

| .5 系数、原始物理分支 | 指数3.825 | 指数2.55 |
|---|---:|---:|
| 保存数 / 撤墙后末时长 | 91 / 约.90s | 91 / 约.90s |
| 末态 pRMS，kPa | 36.7548 | 31.0924 |
| 全窗最低绝对孔压，kPa | −85.4465 | −82.9904 |
| 全窗最小 NN/dp | .363086 | .333459 |
| r<.7dp 对数，峰值/末态 | 110/23 | 113/68 |
| 末态前缘相对 PRE 推进，m | .338313 | .469480 |
| .6–.9s 同材料位移 RMS，mm | 4.96054 | 14.94721 |

来源：`notes/c08_h18_n255_decision_r1.md`、`notes/c08_h18_wend_a05_decision_r1.md` 及其绑定 CSV。两个指数全部91实际 time/step 匹配；表内全窗最小 NN 不混作末态 NN。较少近距并不等于更准：3.825 末4074/5000负压粒子，最后约.3s前缘只增加约2.10mm，pRMS32.36→36.75kPa，存在广域负压/早停代价。

指数2.55 的 .5 已另完成3s/301帧诊断（`notes/c08_h18_n255_full3_decision_r1.md`）：实际末t12.999999999592434、tau2.999999999886427；末平均 p=−42.58081kPa、pRMS45.11378kPa、5000/5000负压、NN最小.411765dp、37近距对；论文1.2s可见前缘差约−1.10417m且后期继续负向漂移。该长窗也被明确拒绝为物理验收，不能用其正常完成为强 AS 背书。

## 当前判断和研究边界

继续增大 ε 前确有边界重建健壮性问题需要分清，但 wall803 的 determinant 门只解释该次停止，不能自动解释整片团聚或证明修好边界就能选 .7。完成的 .5 已表现压力/运动代价。应保留原门及失败证据，待保存态 AS 真实作用证据后，再研究具一致性与域约束的重建候选；不盲目降低 determinant 门、不丢活动墙、不截断 J，也不把已拒绝 centroid 再次包装为现成修复。本说明不准入任何新试验或其余 psi。

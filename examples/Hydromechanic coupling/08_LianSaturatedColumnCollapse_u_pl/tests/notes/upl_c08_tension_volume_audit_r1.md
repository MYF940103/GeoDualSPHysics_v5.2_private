# ψ0 的张拉返回、体积变化与 J：只读审计

结论：**ψ0 只使光滑 DP 锥面的塑性流动等体积；当前额外张拉面仍允许体积塑性。不能以 `3K log(J/Jref) != ΔI1eff` 单独判定 J 错误。** 本记录只读现有代码、已闭合点组件、两组各两个已保存帧；未运行求解器、构建、解码器或修改任何依赖。正在运行的 n3 不受影响。

## 返回核的实际政策

见 [FunSoilMaterial.h](../../../../../src/source/FunSoilMaterial.h) 105–109、125–152、154–208、211–234。令 `q=sqrt(J2)`、`α=DP_phi`、`β=DP_psi`，拉应力为正，`K>0,G>0`：

- 光滑返回：`Inew=Itr−9K β(κnew) λ`，`qnew=qtr−Gλ`，`κnew=κold+λ/√3`，所以 `Δεv^p=3βλ`。ψ0 的 β 严格为零，光滑 basic/soft 两入口都保持应力迹。
- 锥顶先令 `λ0=qtr/G`、`κtip=κold+λ0/√3`，并在这个连续 κ 上计算 `Itip=kc/α`。偏塑性增量已饱和，不继续按总顶点乘子增加 κ；纯静水 trial 的 `qtr=0` 因而可以 κ 不变。
- β>0 且 `λ=(Itr−Itip)/(9Kβ)>=λ0` 时提交单势 `Apex`，`Δεv^p=3βλ`。否则尝试明确分开的 `TensionRepair`：`λs=λ0`、`λt=(Itr−Itip)/(9K)−βλ0>=0`，`g_t=I`，故 `Δεv^p=3βλs+3λt`、`Itr−Inew=9K(βλs+λt)`。ψ0 下 `λt>0` 仍能降低应力迹，且其纯各向同性部分不进入 dev κ。
- `lambda_apex` 是同一顶点剪切乘子的诊断标签，不能再与 `lambda_shear` 相加计体变。φ0 是无有限锥顶的圆柱，代码避免除以 α。soft 分支须先通过区间单调性资格；未认证路径返回 `UnresolvedPath`，不会伪装成 apex。

basic 与 soft 共用此返回流程；soft 的 tip 系数由 `κtip` 更新 φ/c/ψ。当前 ψ0 组仍有 `cp5000/cr1000/ncoh5`，κ 会改变抗剪强度和张拉 tip。代码没有单独保存塑性体积应变或 λt 历史，κ 不是总塑性体积的代理。`TensionRepair` 是已声明附加面政策，不等同原单势 DP 顶点解，也未承诺所有 ψ 下塑性功非负。

现有 [69 点 GPU 组件收据](../logs/upl_material_unified_GPU_r1.check.json) 检验了应力顺应性体变与 `3(βλs+λt)` 的一致性：最大体变误差 `1.8974e−19`，host/GPU 应力与乘子差为零；这是局部实现检查，不证明本次指定粒子实际经历了多少修正。

## 应力迹与 J：同一运动量，但不是同一浮点表达式

应力使用 **effective** `SigmaState_kk` 的三分量迹；不能拿 `Ieff−3p` 总应力迹代替。即使二维平面应变，σyy 也在更新，仍应使用 `3K`。

- CPU [JSphCpu.cpp](../../../../../src/source/JSphCpu.cpp) 2402–2441 / 2553–2556 / 2611–2620；GPU [JSphGpu_ker.cu](../../../../../src/source/JSphGpu_ker.cu) 1915–1954 / 2066–2069 / 2248–2257：C08 的 `PoreCompressionGradCorr=1` 与 `SoilStressRateGradCorr=1` 使用同一 `CorrMat[i]`、同一 `V0*Jj`，也使用同一 `dv*_grad_deriv`。动态墙由同阶段 `BoundDerivativeVel` 提供镜像速度；这不是一个用静止物理墙速度、另一个用镜像速度的设计分叉。inactive 墙在两者之前都被跳过。
- 但 stress 先按 float 体积/核梯度/速度差累积 3×3 梯度，再乘 double C 后 cast float；θ 则逐 pair 用 double 体积与 C∇W 累加。CPU θ 还从 double 距离平方重新求 float 核因子；GPU J 路径复用实际 float pair `fac`。因此 `tr(Lstress)==θ` 只在实数同算子层面成立，不是 bit 恒等；失序/大 C 条件数可能放大差异，当前审计没有量化到这些点。
- 弹性 Jaumann rate 的实数迹为 `3K tr(Lstress)`，自旋交换子迹为零；实际 rate 为 float，σ存为 double（CPU 1979–2022，GPU 576–621）。当前输入 `DensityDT=0`，没有额外应力扩散项。
- CPU 3295–3324 / GPU 1389–1399 的 J 更新为 `Jh=Jn+(dt/2)Jn θn`、`Jn1=Jn+dt Jh θh`。σ corrector 从原 σn 加 `dt*Rσ,h` 后再返回。Pre 的 κ 恢复旧值、Cor 正式提交（CPU 3494–3506 / 3629–3640；[JSphGpuSimple_ker.cu](../../../../../src/source/JSphGpuSimple_ker.cu) 421–432 / 614–624）。所以不能把 Pre 和 Cor 的 λt 都累计成已提交体积历史。
- `log(Jn1/Jn)` 只是连续体诊断；并不逐步严格等于 `dt θh`。即使 θ常量，J 的倍率为 `1+a+a²/2` 而不是 `exp(a)`。闭合需分别评估返回修正、`tr(Lstress)−θ`、midpoint/log 差和浮点余项，不能把它们混成一个“J错”结论。
- 固定平面投影在应力返回之后更改位移/速度，并未同步纠正同一步 σ/J（CPU 3684–3686；GPU [JSphGpu.cpp](../../../../../src/source/JSphGpu.cpp) 1700–1719）。因此 J 是所实现散度演化的状态，不是另从已投影坐标重建的几何 detF；原 policy 也明确未闭合接触 reaction/J/Darcy。这不单独证明本次两点差额来自接触。

## 两个已有点：差额复核及其信息边界

只 seek ε.2 `upl_c08_stage_trace_window_GPU_r1/native` 与 ε.5 `upl_c08_as05_window_GPU_r1/native_r1` 的 part0/65，各读取一条真实 typed22 frame；时间为 `10.010000000377431 → 10.66000000058375 s`，不是 PRE→.66。使用问题指定 `K=20e6/[3(1−2*.33)]`；实际存储 Kfloat 为 19607844 Pa。

| 组/原ID | Jref → Jend | Ieff,ref → Ieff,end (Pa) | 3K log(J/Jref) (Pa) | `log(J/Jref)−ΔIeff/(3K)` |
|---|---|---|---:|---:|
| ε.2 / 5157 | .999956568919 → 1.043244570357 | −2554.825 → −198546.705 | +2492886.350 | .045710930 |
| ε.5 / 6960 | .999187405433 → 1.082216954650 | −47819.114 → +5094.337 | +4695564.579 | .078925069 |

两点的“缺少迹增量”分别为 2.689 / 4.643 MPa；最后一列若**额外假设**梯度/积分余项可忽略，才可解释为累计塑性体积应变。现记录不能作此假设。末态 κ分别 .288247764 / .339366704，q分别 17645.757 / 828.713 Pa；按已保存 κ计算的 tip 分别约 12523.09 / 11149.62 Pa，两点末态都不是 `q=0,I=Itip`。这不排除中途张拉 cap 后再受压/剪切，亦不能从末态反推修正次数。

最小可区分证据是同一实际 corrector 的 `(Itrial,Ireturned,qtrial,κold,κnew,status,λt)` 与 `(trLstress,θn,θh,Jn,Jh,Jnew)`：ψ0 下 smooth 的迹降应为零，TensionRepair 的迹降应为 `9Kλt`；将**仅 Cor** 的这些实际迹降累积后，剩余才属于梯度/积分/舍入等项。当前两个 ID 的 native 没有这些逐阶段量，既有三 ID 压力 trace 也没有返回乘子/应力梯度，无法在不新增记录的情况下完成唯一分解。可先用已有点组件验证机制；不可把保存态重构或 κ增量冒充实际阶段回放。本轮未新增诊断门或求解。

## 原文和旧实现并非没有张拉政策

[Bui 2008 原 PDF](../../../../../src/papers/PDF/Num%20Anal%20Meth%20Geomechanics%20-%202008%20-%20Bui%20-%20Lagrangian%20meshfree%20particles%20method%20%20SPH%20%20for%20large%20deformation%20and%20failure.pdf)：印刷 p1541 Eq9、12–13 是总应变=弹性+塑性及一般流动应力率；p1543 Eq20、23–24 的非关联势使 ψ0 光滑流动塑性不可压缩。**另外** p1545 §3.3.1 Eq29–30 明确在 `I>kc/α` 时减去各法向分量 `(I−kc/α)/3`，剪应力先不动；p1546 §3.3.2 再作 stress scaling。它没有把该额外平移推导成原 ψ0 单势的等体积返回，也没有本文 soft κ 记账。Bui Eq13 不是“所有后处理后仍应 I=3K logJ”的保证。Lian2023 印刷 p4 Eq13 的 dev 历史定义与 Bui2008 的 Eq13 不是同一公式。

只读已冻结 `upl_preload_handoff_ReleaseCPU_r2/source.zip` 内 `src/source/JSphCpu.cpp`：旧 basic 3930–3948 先由顺应性去体积计 dev κ，再在 3952–3969 平移 mean/缩放 dev；旧 soft 4031–4059 用 full-flow norm 更新 κ，再在 4062–4079 平移/缩放，额外修正均未一致回写 κ。旧代码因此已经允许 ψ0 下额外 mean 修正，但与新端点系数/饱和 dev κ/明确 status 的联合返回不能称完全等价。该旧文件与原收据未改。

[Lian2023](../../../../../src/papers/PDF/Lian%202023%20u-pl.pdf) 印刷 p11 §3.5.3 Eq47 则针对塑性剪胀诱发负孔压增长，引入 β=.04 减缓其增长，并说明仅塑性变形时采用；它不是上述材料张拉面或 AS ε，也不是把负孔压截为零。原文先讨论 ψ0 光滑流动无塑性体变，不能据此消除另行采用 tension cracking 政策的体积效应；同样不能用本次 J/应力残差倒推出已实现或必须打开 Eq47。本记录未建议移植或调参。

本审计确认了一个必须保留的材料政策解释和一个未量化的离散差异，**没有确认当前 J 大幅增长的唯一根因，也不据此选择修复或修改 AS 参数**。

# ψ=+2.5° 负孔压后的自由表面闭合范围审计

本轮只读既有源码/小型收据/旧结论；未运行测试、求解器、读取器或构建，未改依赖或扫描SHA。正在运行的ψ−5同材料预载保持原状。本记录供后续HG0对照的因果判断，不宣布当前负孔压或早停根因，也不准入新的物理窗。

## 当前实际链接的物理离散

定位链为 `logs/c08_h18_hg_groups_build_r1.build.json` →其 `base_build`=`c08_h18_wall_c_retry_GPU_r1.build.json` →该记录的 `replacement_physical_object`=`%TEMP%/c08_h18_wall_c_retry_GPU_r1/JSphGpu_ker.cu.obj`。groups实际 `c08_h18_hg_groups_build_r1.link.call.json` 确实链接该对象；原 `c08_h18_wall_c_retry_GPU_r1.compile.call.json` 的输入是 `outputs/c08_h18_wall_c_retry_GPU_r1_build/frozen/src/source/JSphGpu_ker.cu`。该TU包含新C-quality mDBC header，原build只更改该header；编译参数无FS-normal候选宏。因此结论来自实际compile/link链，不把新目录内同名frozen文件自行当作已链接证明。

该真实TU第1574–1600行，以 `gp=∇p`、`F=gp+ρw Ace` 记号，有：

```
L0   = LP - gp·Lx + ρw Da
Lraw = LP + ρw (Ace·Lx + Da) = L0 + F·Lx
```

当前free-seepage实际FS走 `Lraw`。原法向投影只在 `closedfs` 时执行；host实参为 `HydroMechDrainage && !IsHydroMechDrainageActive()`，本组HydroMechDrainage=0，所以此处gpcorr仍是gp。变k项随后使用 `gradJ·(gpcorr+ρw Ace)`，并未因raw FS的整向量缺陷省略而投影。Ace在这里不含体重力；NoPen后续投影冲量也不追溯写入该同阶段Darcy RHS。

这确实是Laplacian中省略**完整向量**Taylor缺陷的目标，不能只由 `n·F=0` 推出。不过代码没有显式把压力或F全部分量赋成零，不应把代数目标说成已强制实现完整物理零通量。

旧normal-Taylor试验改为：

```
gc      = gp - n (n·F)/|n|²
Lnormal = LP - gc·Lx + ρw Da
        = L0 + (n·F)(n·Lx)/|n|²
```

其变k链项也随之改为 `gradJ·(gc+ρw Ace)`。这是法向Taylor目标，仍不是严格守恒Neumann边界证书。保持原 `p<=0` 的自由渗流语义时，还需从原文和离散通量推导active-set：若外法向流出量记为qn，无入渗的互补候选通常要求p<0时qn=0，p=0时允许qn>=0；不能不分这两类就对所有FS同时指定零压或零法向通量。原负压不应为配色而裁剪，尚未验证这里哪种离散最合适。

## 可复用制造证据及边界

`notes/c08_fs_normal_taylor_r1.md`、`logs/c08_fs_normal_taylor_cpu_r1.review.json` 保留真实production FS/C的486行制造检查。平顶切向仿射驱动b=4Pa/m时：Wendland raw速率−0.0042378963Pa/s，normal约4.09198e−5Pa/s（原预算约6.25e−5）；Cubic从0.03736884降到0.00878336Pa/s，但仍不为零。真实法向有倾斜，故原结论明确 `true_flat_continuum_passed=false`；不能把公式对照通过改写成普遍仿射null。

`logs/c08_fs_normal_gpu_r1.review.json` 的Raw/Normal Debug实际GPU各1620 controls、162 nodes且memcheck零错。两者nodes与OFF二进制逐byte一致；ON-FS之外1300项bit一致，252个ON-FS rate发生真实改变，变k profile有32个非零FS chain witness。常负压场速率精确零、hydrostatic null按原传播预算通过；CPU/GPU tracking/rate差异仅描述。这些是既有实现/兼容证据，不是当前groups Release的长程0ULP、守恒或精度证明。

## 旧真实ψ0窗口为何未选

`notes/c08_fs_normal_window_decision_r1.md` 和 `logs/c08_fs_normal_window_review_r1.check.json` 对照了原raw与normal的91个实际匹配保存时刻：旧WendlandH1.8、ψ0、AS.5/n3.825、AV.1、同schema2 PRE、无新HG、在当前C-quality修复之前。其原生安全门通过，但raw→normal：最低压力−85.4465→−88.2433kPa；最大pRMS36.7548→36.5501kPa，仅改善约0.56%；最终r<.7dp近对23→27；Jmax1.040609→1.053473；最终前缘增量0.338313→0.337519m，早停仍在。最小间距由.363086改善至.377001dp，但不足以抵消其余指标。故保留私有证据、不合入、不选为修复方案。

HG0同材料对照之后，若仍显示压力反馈抑制，FS法向/切向一致性、actual normal误差、变k链项与上述active-set值得先审，优先于未经推导地强设全FS Dirichlet0或移植TPI/Eq47人工储存。但旧失败窗不能证明当前正ψ负压是数值伪影；真实剪胀也能产生负压，当前HG0开关还切换cached材料实施路径。需要先保留这些差异，再决定是否另作最窄兼容试验。

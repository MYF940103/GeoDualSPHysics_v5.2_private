# Actual gravity preload: damping and Shepard integration

The user corrected the route after the initial 0.03125 s observation: extend the actual gravity-loading stage and enable its existing damping/Shepard options, following case03. The prescribed-stress zero-step probe remains a descriptive diagnostic only. No new geostatic mode or effective-stress assignment was implemented. The initial native double stress in every new physical run is exactly zero.

The reference case03 prestress input uses gravity -9.81 m/s2, hydrostatic initial pore pressure, SoilDamping=1/coefficient0.02, Shepard every40 updates, TimeMax5 s and TimeOut0.1 s. Its materials, low k, legacy regularization volume and restart process are not copied as an unverified u-pl restart. The new case08 keeps its existing geometry, constant k, material return and mixed-slip walls, with explicit ConstantZ water surface2 m. Future non-Tv cases use regular decimal physical times; completed dyadic records are unchanged.

## Seven production source files

- `JSph.cpp`: narrow fixed-container admission for existing ConstantZ, damping and Shepard. Dynamic Shepard requires the explicit hydrostatic baseline; actual initial geometry checks the fully saturated flat top. No new public control was added.
- `JSphCpu.cpp` and `JSphGpu.cpp`: ConstantZ initializes pressure/p0 only; fixed-wall p0 extends the same affine hydrostatic field. The dynamic Shepard branch averages p-p0 with self/neighbor V0*J; the legacy arithmetic remains unchanged. After filtering, the existing current FS mask projects only finite positive surface pressure.
- `JSphCpuSingle.cpp` and `JSphGpuSingle.cpp`: only the new dynamic ConstantZ initialization applies the existing completed-state pressure policy. Scheduled Shepard uses the single-J wall reconstruction before and after filtering instead of the legacy pore-only wall routine. There is no extra FS/C neighbor traversal after filtering.
- `JSphGpu_ker.cu/.h`: the existing Shepard wrapper/kernel accepts one optional J pointer; NULL retains its old arithmetic. No new persistent array, constitutive equation or integration stage was introduced.

The existing dynamic damping is -cd*v with cd=36.1976852/s for this input, derived from the reference intrinsic solid density. The XML coefficient0.02 is not itself a rate. The regularizer is optional numerical smoothing, not a proof of exact fluid mass conservation or the paper's TPI/negative-pressure stabilization.

## Closed implementation evidence

All four authoritative configurations built: CPU Debug/Release86 objects and GPU Debug/Release111 objects, with actual tool exits0 and zero compiler errors. Isolated output/intermediate folders protected previous programs. The source/build archives remain local.

The actual CPU field component completed486 rows over81 slots. It passed160 exact constant-excess/baseline pressure checks,80 resolvable wrong-Mass/rho-weight witnesses (maximum reference difference1.403159 Pa),24 positive post-filter surface projections and all protected-state checks. The old u-pw branch's81-row CSV is byte-identical between the retained old85-object program and the new closure using the same compiled component main. These are operator/implementation observations, not equilibrium tests.

GPU Debug's one40-update memory screen captured both actual tool and solver Win32 exits0, with zero errors/leaks. Actual CPU Debug, CPU8 Release and GPU Release each completed one400-update run with11 frames to native time0.0010000000000000013 s. Each unique native read verified7060 IDs/22 arrays,55000 soil ledger/cache checks,22660 fixed-marker checks,77660 frozen-p0 checks and1100 true FS2/3 pressure-sign checks; initial effective stress is zero. Every original necessary signed-step and field guard remains.

Across all actual matched times, including the CPU Debug/Release and CPU/GPU comparisons, maximum pressure RMS difference is0.001916423 Pa, material XYZ displacement maximum difference1.825409e-8 mm and total-stress Frobenius RMS difference0.003593748 Pa. All original5 Pa/.005 mm implementation-comparison limits passed. This is a same-step comparison, not a half-step or theory-accuracy claim. The root inspected the matching four-panel PNG and CSVs.

Initial p0 is the immutable material hydrostatic baseline. The top surface's pressure is initially projected to0 while its p0 is about196.2 Pa; therefore its native excess is about-196.2 Pa. This is a discretized free-surface initialization consequence, not plastic dilation. The measured pressure and stress subsequently evolve from the actual gravity load.

## Next admitted run

One fresh CPU8 Release5 s gravity preload, dt2.5 microseconds,2,000,000 updates and physical output interval0.01 s. The short observed loop times were2.398547 s CPU8 and2.735856 s GPU on the actual local RTX3050, favoring CPU8 by about14.1% in that short comparison. Linear CPU extrapolation is roughly3.33 h before long-run load changes; it is not a controlled benchmark or promised finish time.

The long run is a diagnostic preload. Reaching5 s does not establish equilibrium: review velocity/kinetic decay, pore pressure, evolving effective/total stress, settlement, J/n/density and late-window drift. Keep p-p0 distinct from current hydrostatic excess, and use actual saved clocks. Do not impose the 1D uniform-stress gate, invent wall reactions from pressure, release a wall, or claim PART restart support from normal completion. If unfinished or failed, retain the actual exit, raw last reported line and original outputs; diagnose without relaxed thresholds, duplicated solvers or rewritten records.


## 已完成的接线验收与延长预载准入

四个Debug/Release实际构建通过，GPU40步memcheck零错误/泄漏；CPU Debug、CPU8 Release、GPU Release各400步的11个真实保存状态通过22数组和全部原生守卫。22组同时间比较的最大孔压RMS差0.001916423 Pa、材料XYZ位移差1.825409e-8 mm，总应力Frobenius RMS差0.003593748 Pa。旧u-pw Shepard81行实际CSV保持逐字节一致。此处不是半步长验证，也不是静力平衡验收。

短窗CPU8 Release循环2.398547 s，GPU Release2.735856 s；据此选择CPU8执行一次新的5 s重力预载，dt=2.5e-6 s、输出间隔0.01 s、共2000000步。短窗线性估算约3.33小时，不是保证时长。使用现有ConstantZ静水孔压初始化，骨架应力从0经重力形成，SoilDamping1/系数0.02，PoreShepardRegularization1/间隔40。不得因正常到达5 s而认定平衡，仍审查压力、速度、应力和晚窗变化。预载前保存本轮源码；运行程序和输入冻结，后续可独立审查撤墙实现但不修改活动依赖。

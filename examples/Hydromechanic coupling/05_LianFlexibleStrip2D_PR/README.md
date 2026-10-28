# Lian Flexible Strip 2D PR

## 早期加密输出与最新图表（2026-10-28，r2）

另行完成0–1 s补算：仅将测试XML的TimeMax/TimeOut改为1/0.01 s，积分步长仍为10 μs，
使用相同程序、材料、混合滑移边界及HG/SPR设置。RTX 3050完成101帧，原生安全检查通过；
与服务器100 s结果共有21个精确实际时间/步号状态，34个物理字段全部0 ULP，
输出间隔统计量dterror另按原阈值独立核对。补算末帧的源时钟尚未到排水开启时刻，
因此本轮不另称复测了排水；原100 s全帧检查仍有效。

最新 [图表索引](figures/README.md) 中的r2孔压/沉降历史合并了101个早期样本和
1980个原晚期样本，共2081行，每行记录来源和原生文件SHA。
100 s末态、Fig10云图、有符号水平位移剖面、VTK序列及所有r1证据均原样保留。
这不是新的物理方案或半步验证，也没有重新计算100 s；孔压与论文数值参考的差异未被消除。
复算绘图入口为 `support/plot_lian_hgspr_r2.py`，最终记录为
`tests/logs/lian_hgspr_early_r1.final_review.json`。

## 服务器100秒结果与分析（2026-10-28）

本次 `CaseLianFlexibleStrip2D_PR_release_HGSPR_out` 已由RTX A6000完成100 s、
1000万步和2001帧。全帧固定20301个土粒子的有限值、弹性、无排除、几何、
真实载荷、活跃FSType2/3排水及自然步长检查通过；单独孔压扩散步长检查也通过。
仍使用交付时的HG=.1、SPR=1、应力率梯度修正=1、侧壁FreeSlip和底面NoSlip，
正式XML/BAT及原生BI4均未改动。新结果不是下面已停止的旧100 s结果。

正式图与CSV索引见 [figures/README.md](figures/README.md)：论文Fig10全部四时刻，
Fig11的A/B孔压，Fig12沉降与100 s有符号水平位移剖面，以及晚期孔压、应力和近墙响应。
A/B使用初始材料坐标(0,10)/(1.25,8.75)的固定ID/双线性权重，不能与旧A=.1 m的
逐帧插值曲线混为一谈。100 s A/B孔压为0.169/0.199 Pa，沉降为1.833/1.110 mm。
变形总体接近论文；早期A孔压仍偏低，顶部水平位移亦有可见差异，未宣称精确复现。

可视化数据位于新正式输出的 `particles`，共2001土体帧及2001边界帧。
打开 `PartFluid.vtk.series` / `PartBound.vtk.series` 可使用实际保存时间映射。
孔压字段 `PorePress` / `ExcessPorePress` 单位Pa，塑性字段 `Kplastic`；本次保持弹性。
VTK坐标/显示应力为float兼容输出，精度分析仍以double位置/应力原生BI4为准。

复算分析入口为 `support/postprocess_lian_hgspr_r1.py analyze` 和
`support/plot_lian_hgspr_r1.py`，均拒绝覆盖已有同标签结果，不启动求解器。
最终证据为 `tests/logs/lian_server_return_r1.final_review.json`。
用户取消了组合方案3 s半步；本次没有100 s半步，也不把论文SPH/FEM当作解析真值。
原13节点载荷求积仍比理想1.25 m基础宽度高4%，未为拟合论文而缩放。

下面的等待服务器/旧入口段落保留作历史记录，以本节及交付配置为当前状态。

## 当前服务器入口（2026-10-27，替代下面旧入口说明）

用户取消新的HG+SPR 3 s半步，要求将100 s完整计算移交Windows/RTX A6000。
根目录 `CaseLianFlexibleStrip2D_PR_release_Def.xml` 和
`xCaseLianFlexibleStrip2D_PR_release_win64_GPU.bat` 现采用已完成3 s粗步的
HG=.1 / SPR=1 / 应力率梯度修正=1方案，保留侧壁FreeSlip、底面NoSlip、
三个显式平面法向、10 µs时间步和0.05 s原生保存。未改生产源码。

新输出固定为 `CaseLianFlexibleStrip2D_PR_release_HGSPR_out`，旧
`CaseLianFlexibleStrip2D_PR_release_out` 和旧50 s输出原位保留。BAT使用
`support/bin`，只负责GenCase/求解/原生保存；绘图在数据回拷后完成，
不再调用旧Python/VTK后处理。便携包为根目录
`Lian_HGSPR_Windows_RTXA6000.zip`；详见
[服务器说明](support/README_server.md) 和
[论文观测量定义](support/paper_observables.json)。

3 s半步任务已按用户要求停止，最后日志帧约0.15 s，不能视为通过。
历史status不改写，新停机记录为 `tests/logs/lian_hg3_half_r1.user_stop.json`。
组合的3 s粗步与HG的0.15 s半步证据不代表100 s/论文精度验收。
等待服务器结果期间主线先做Cryer，之后1D自重；不本地重启Lian长计算。

以下旧日期段落是历史进展；其中“HG3 s half next”、HG关闭的旧正式入口、
固定Python路径等已经被本节替代，不应用来启动本次服务器任务。

2026-10-27 bounded compatibility update: mixed-slip SPR passed an independent
3-s saved-output half pair (pressure RMS 0.016484 Pa, top material 0.00001354 mm).
It has not been shown to resolve the paper-field discrepancy. A separate
nonperiodic 2D HG candidate now uses real bounded neighbors, not artificial
periodicity; CPU/GPU operator/old-periodic/Debug-memory and frozen-geometry
oscillator checks passed. Actual Lian startup through .15 s also passed the
31-sample independent half pair (.009139 Pa / .000009084 mm); this does not
validate drainage after 1 s or paper/full-cycle accuracy. HG x SPR 3-s comparisons
now passed all saved-state safety checks; an independent HG+SPR 3-s half is next,
not automatic 100-s acceptance. See `tests/notes/lian_hg3_review_r1.md`,
`tests/notes/lian_spr_half_review_r1.md` and
`tests/notes/lian_hg_short_review_r1.md`.
Formal XML/BAT and the intentionally stopped 100-s dataset are unchanged.

The first HG x SPR 3-s worker was stopped by its checker at .10001 s:
physical/identity fields were exact, but it incorrectly compared `dterror`, a
since-last-output statistic, across 5-ms/50-ms output intervals. The new r2
checker preserves exact state equality and the original independent natural-step
safety limit; see `tests/notes/lian_hg3_r1_audit.md`. No production change or
completed 3-s result is implied by this checker repair.

2026-10-26 task-plan revision: Lian is the sole active 2-D consolidation
verification case; Yao is deferred with its evidence preserved. Finish the
running mirror-footprint 15-s coarse/half review first. If that review admits
the candidate, prepare and execute an independent formal 100-s run, then
compare pressure, material-point settlement and horizontal displacement with
the paper's Section4.3 SPH and ABAQUS FEM results. Those are numerical
references, not an analytical solution. See the
[current verification plan](../validation/poromech_next_r2.json).

This case uses the explicit u-pw pore-pressure-rate path for the Lian strip
footing geometry. It is a retained verification/diagnostic case, not a TPI
implementation or a claim that the late pore-pressure residual is resolved.

## Independent 100-s release entry (2026-10-26)

2026-10-27 user revision: this run was intentionally stopped, NOT completed,
before the requested controlled 3-s comparisons. Its 219 native frames through
10.90001 s remain protected in the root output. The integrated worker was
stopped before its owned solver; neither may be restarted. See
`tests/logs/lian_formal100_r1.user_stop.json` and
`tests/logs/lian_formal100_r1.user_stop_native.json`. First supported-option
tests are in `tests/notes/lian_opt3_r1.json`. Paper SPH/FEM is a numerical
reference, not an assumed exact truth; if a bounded comparison leaves a
discrepancy, select a justified stable baseline rather than tune only colors.
A new formal long run, if admitted later, must use fresh inputs/output names.

- Input: `CaseLianFlexibleStrip2D_PR_release_Def.xml`.
- GPU batch: `xCaseLianFlexibleStrip2D_PR_release_win64_GPU.bat`.
- New output: `CaseLianFlexibleStrip2D_PR_release_out`; refuses overwrite.
- Full duration 100 s, 10 us fixed step, 0.05 s native saves, double positions
  and stress, float pore pressure/rate. Original mixed mDBC, damping 0.04 and
  13-node load quadrature are retained; SPR/HG/stress-gradient correction off.
- BAT runs GenCase, actual GPU Release, PartVTK fluid/boundary, then
  `support/postprocess_lian_release.py`. Native figures AND matching CSVs go
  to root `figures/lian_release100_r1_*`. Python is configured as
  `D:\Anaconda3\python.exe`; retain the native reader at
  `tests/outputs/hydro_native_r1/ReadHydroNative.exe` and the checked-in
  `lian_release_r1.py` / `lian_mirror_review_r1.py` helpers during cleanup.
- Formal paper probes are A(0,10) and B(1.25,8.75), using initial material
  IDs/bilinear weights, not the historical nearest-node diagnostic probes.
  Native plots alone are not SPH/FEM acceptance; full reference review remains
  required. The new run is independent, not a relabeling of the 15-s pair.
- Sequence status: `tests/logs/lian_formal100_r1.status.json`; one integrated
  terminal notification, now retired by the explicit user stop. Do not restart a completed/interrupted worker or
  overwrite its output. The runtime/analysis may still be pending.

## Retained 50-s entry point

- Input: `CaseLianFlexibleStrip2D_PR_Def.xml`.
- Windows GPU batch: `xCaseLianFlexibleStrip2D_PR_win64_GPU.bat`.
- Output: `CaseLianFlexibleStrip2D_PR_out`.

The batch runs GenCase, the GPU solver, and fluid/boundary PartVTK conversion.
It does not run the analytical plotting scripts. If the output already
exists, option 1 deletes it; do not select that option for the retained run.

## Retained 50-s configuration

- Domain `20 m x 10 m`, `dp=0.1 m`, zero gravity.
- `HydroMechTopLoadMode=4`: strip `x=[0,1.25] m` at `z=10 m`.
- Load `10 kPa`, ramp `1 s`; open-top drainage outside the strip starts at
  `1 s`, while the strip contact remains impermeable.
- `k=1e-3 m/s`, `n=0.4`, `Kw=1e9 Pa`.
- mDBC: lateral walls `mkbound=0` free-slip; bottom `mkbound=1` no-slip.
  These are per-marker overrides of the free-slip default, not an all-wall
  free-slip setup.
- `DtFixed=1e-5 s`, `TimeMax=50 s`, `TimeOut=0.05 s`, damping `0.04`.
- Pore-pressure regularization and density/stress diffusion are disabled.

## Files to retain

Keep the root XML/BAT, the full-run native data and logs, and the
plasticity-off comparison listed in [tests/README.md](tests/README.md).
Test inputs, scripts, figures, logs, and dated conclusions remain in the
existing `tests/` categories. Existing comparison figures are under
`tests/figures/`; they are not automatically produced by the root BAT.

The dated notes describe different historical setups. The current mode-4
configuration above supersedes the earlier abandoned mode-3 Lian setup, but
does not invalidate or rewrite those experimental records. A successful
solver exit and a formal launcher are not accuracy acceptance criteria.

## Current mode-4 diagnostic (2026-10-26)

The current double-stress strict-footprint 15 s control completed, but is not
accepted as a physical release: native node1744 crosses x=0 near12.40 s,
loses its load and becomes drained, producing a1000 N/m force jump and
pressure/settlement transients. The legacy float-stress run has the same
mechanism near14.1 s; this is not evidence that stress double alone repairs it.
See `tests/figures/lian_late15_review_r1_history.png`, `_contact.png`,
`_fields.png` and their corresponding CSVs and check receipt.

A CPU/GPU source candidate mirrors the mode-4 footprint across the x=0
free-slip face (`abs(x)<=1.25`). Domain x>=0, q, the right contact edge,
original nodal force quadrature and all other modes are unchanged. This
candidate needed short/half/late-window verification; the retained strict
control program and raw data remain preserved under tests and the old output.

The candidate passed the independent2ms Debug/memcheck and .15s/3s GPU
coarse/half short review (`tests/logs/lian_mirror_review_r1.check.json`).
The3s half maxima are0.0112047Pa and0.0000128985mm; candidate loads retain13
nodes, with all active drainage nodes at0Pa. The figures and matching CSVs
are `tests/figures/lian_mirror_review_r1_*`.

The independent 15-s coarse/half review now also passed all 301 native pairs:
0.0153762 Pa / 0.0000128985 mm maxima. Node1744 contact transitions fall
from 12 to 0; post-ramp force stays 12999.99943 N/m rather than dropping
to 11999.99947 N/m. Minimum saved pressure changes from -3211.99 Pa to 0,
and maximum speed drops from 0.0750028 to 0.00194440 m/s. Both complete
61-frame 3-s same-dt prefixes are all-native-field 0 ULP. See the inspected
`tests/figures/lian_mirror15_review_r1_*` PNGs/CSVs and
`tests/notes/lian_mirror15_review_r1.md`. This accepts the scoped contact
repair and admits the new 100-s release, NOT full reference accuracy.
Original +4% load-width quadrature and remaining settlement/reference
differences must still be assessed; old formal data stand unchanged.

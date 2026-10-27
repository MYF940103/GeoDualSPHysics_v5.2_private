# Lian Flexible Strip 2D PR

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

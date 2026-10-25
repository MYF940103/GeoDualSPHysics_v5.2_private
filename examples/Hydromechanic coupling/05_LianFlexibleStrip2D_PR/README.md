# Lian Flexible Strip 2D PR

This case uses the explicit u-pw pore-pressure-rate path for the Lian strip
footing geometry. It is a retained verification/diagnostic case, not a TPI
implementation or a claim that the late pore-pressure residual is resolved.

## Current entry point

- Input: `CaseLianFlexibleStrip2D_PR_Def.xml`.
- Windows GPU batch: `xCaseLianFlexibleStrip2D_PR_win64_GPU.bat`.
- Output: `CaseLianFlexibleStrip2D_PR_out`.

The batch runs GenCase, the GPU solver, and fluid/boundary PartVTK conversion.
It does not run the analytical plotting scripts. If the output already
exists, option 1 deletes it; do not select that option for the retained run.

## Current configuration

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
candidate needs short/half/late-window verification; root formal inputs and
the retained control GPU program/data are not promoted or overwritten here.

The candidate passed the independent2ms Debug/memcheck and .15s/3s GPU
coarse/half short review (`tests/logs/lian_mirror_review_r1.check.json`).
The3s half maxima are0.0112047Pa and0.0000128985mm; candidate loads retain13
nodes, with all active drainage nodes at0Pa. The figures and matching CSVs
are `tests/figures/lian_mirror_review_r1_*`. This does not cover the old
late switching times: fresh15s coarse/half inputs are under
`tests/configs/xlian_mirror15_r1_{c,h}_win64.bat`. The formal100s root
calculation and FEM comparison are still pending; old formal data stand.

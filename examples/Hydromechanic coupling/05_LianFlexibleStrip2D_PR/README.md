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

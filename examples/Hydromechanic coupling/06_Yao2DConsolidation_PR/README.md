# Yao 2D Consolidation PR

This case retains the explicit u-pw verification setup and damping/boundary
comparisons. The historical results are comparison records, not a new
validation performed during file organization.

## Current entry points

- Default input: `CaseYao2DConsolidation_PR_Def.xml`.
- Default GPU batch: `xCaseYao2DConsolidation_PR_win64_GPU.bat`.
- Damping variants: the matching `CaseYao2DConsolidation_PR_damp000`,
  `CaseYao2DConsolidation_PR_damp001`, and `CaseYao2DConsolidation_PR_damp002`
  `_Def.xml` / `x..._win64_GPU.bat` pairs in this directory.

Each batch targets its own case-named `*_out` directory and runs GenCase,
the GPU solver, and fluid/boundary PartVTK conversion. It does not run the
comparison plotting scripts. If an output directory already exists, option
1 deletes it; do not use that option for retained results.

## Current default

- Domain `20 m x 10 m`, `dp=0.1 m`, zero gravity.
- `HydroMechTopLoadMode=3`: strip `x=[-3,3] m`, load `5 kPa`, ramp `0.1 s`.
- Open-top drainage outside the impermeable strip is active from `t=0`.
- `k=1e-3 m/s`, `n=0.3`, `Kw=1e8 Pa`.
- mDBC free-slip (`SlipMode=3`, batch option `-mdbc_freeslip`).
- `DtFixed=2e-5 s`, `TimeMax=10 s`, `TimeOut=0.05 s`, damping `0.01`.
- Density/stress diffusion and pore-pressure regularization are disabled.
  The three damping variants use `0`, `0.01`, and `0.02` respectively.

## Retained results

The current reference is under
`tests/outputs/CaseYao2DConsolidation_PR_gpu10s_dp01_damp001_nodiffusion_freeslip_out`,
not a root-level default output. Keep it and the damping, slip, and short
geometry comparisons identified in [tests/README.md](tests/README.md), with
their native BI4 data and supporting inputs/logs.

Existing comparison figures and numerical tables are in `tests/figures/`.
Preserve the dated notes and video assets as well. Earlier notes referring
to the sole retained 0.2 s/slip-mode-1 run describe a historical stage, not
the current set of results or the current default boundary setting.

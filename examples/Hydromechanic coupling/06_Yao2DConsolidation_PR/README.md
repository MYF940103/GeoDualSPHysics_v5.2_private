# Yao 2D Consolidation PR

2026-10-24 CPU SPR extension candidate: fresh, independently controlled tests
are under [tests/notes/spr_yao_r1.md](tests/notes/spr_yao_r1.md).
They preserve this root's formal XML/BAT and retained GPU data. Both CPU
integer-save windows (0.02 and 0.1 s) passed their whole-window half-step limits;
the 0.1-s maximum is 0.277975 Pa / 0.000287004 mm. Neither is a full 2-D
consolidation acceptance. The original nodal strip loads 59 interior top nodes
then 61 when its endpoints re-enter (5.9 to 6.1 m versus ideal 6 m); that existing
quadrature bias is recorded, not silently fixed under SPR. GPU synchronization
and independent .02/.1-s half checks now pass: .1-s GPU half maxima are
0.277974 Pa / 0.000287018 mm; CPU/GPU maxima are 0.001324 Pa / 0.000002845 mm.
The bounded .3-s GPU post-ramp window under tests also passed 301 half pairs;
CPU evidence for that off/on comparison ends at .1 s. The subsequent SPR-on
1-s CPU/GPU and independent GPU half window passed all 1001 pairs:
0.000630828 Pa / 0.00000196073 mm cross-backend, and
0.277974 Pa / 0.000287018 mm half-step. This is not full 2-D theory/long-cycle acceptance.
Current history/field PNGs AND matching CSVs are indexed in tests/README.md.

The subsequent GPU SPR off/on/half 10-s comparison is now reviewed:
all 1001 saved pairs pass (0.139152 Pa / 0.000136888 mm half maxima).
At 10 s, SPR reduces maximum bottom/side normal-displacement residuals
by 93.9% / 87.1%, but the loaded-band alternating stress remains about 13.6 Pa.
Pressure continues dissipating through 10 s; on/off pressure/settlement changes
are not independent theory errors. HG/NoPen are off, and no 10-s CPU control
exists. See [the bounded review](tests/notes/spr_yao_10s_review_r1.md) and its
native field/profile/corner PNGs with matching CSVs. Formal root inputs and
retained case02 results were not changed or rerun.

This case retains the explicit u-pw verification setup and damping/boundary
comparisons. The historical results are comparison records, not a new
validation performed during file organization.

## Current entry points

- Reviewed SPR configuration: `CaseYao2DConsolidation_PR_SPR_Def.xml` and
  `xCaseYao2DConsolidation_PR_SPR_win64_GPU.bat`. This separate entry uses the
  verified three-face normals, corrected stress/pore derivatives and SPR;
  HG/NoPen remain off. It targets its own root `CaseYao2DConsolidation_PR_SPR_out`,
  refuses overwrite, and runs GenCase, the real GPU Release program and PartVTK.
  It does not run analytical plotting. The new full 10-s entry has NOT been run;
  retained 10-s companion data are not relabeled as its output. Real-program
  off/on/half 0.02-s regression passed all 63 saved native states at 0 ULP.
  See [release readiness](tests/notes/spr_yao_release_smoke_r1.md).
- Default input: `CaseYao2DConsolidation_PR_Def.xml`.
- Default GPU batch: `xCaseYao2DConsolidation_PR_win64_GPU.bat`.
- Damping variants: the matching `CaseYao2DConsolidation_PR_damp000`,
  `CaseYao2DConsolidation_PR_damp001`, and `CaseYao2DConsolidation_PR_damp002`
  `_Def.xml` / `x..._win64_GPU.bat` pairs in this directory.

Each batch targets its own case-named `*_out` directory and runs GenCase,
the GPU solver, and fluid/boundary PartVTK conversion. It does not run the
comparison plotting scripts. If an output directory already exists, option
1 deletes it; do not use that option for retained results. The separate SPR
entry never offers deletion and does not fall back to a Debug executable.

## Current default

- Domain `20 m x 10 m`, `dp=0.1 m`, zero gravity.
- `HydroMechTopLoadMode=3`: strip `x=[-3,3] m`, load `5 kPa`, ramp `0.1 s`.
- Open-top drainage outside the impermeable strip is active from `t=0`.
- `k=1e-3 m/s`, `n=0.3`, `Kw=1e8 Pa`.
- mDBC free-slip (`SlipMode=3`, batch option `-mdbc_freeslip`).
- `DtFixed=2e-5 s`, `TimeMax=10 s`, `TimeOut=0.05 s`, damping `0.01`.
- Density/stress diffusion and pore-pressure regularization are disabled.
  The three damping variants use `0`, `0.01`, and `0.02` respectively.

## Boundary reference check (2026-10-25)

Yao et al. (2025), Section 5.2.3, pages 21-22 and Fig. 26, defines both the
side walls and the bottom as free-slip and impermeable. At the bottom the
conditions are `u_z=0`, `sigma'_xz=0`, and zero normal discharge; `u_x=0` is
not imposed. The current all-free-slip baseline is therefore retained.
This is different from Lian's strip test and Yao's Section 5.2.4 transient
wave test, which use a no-slip bottom.

Page 24's absorbing-boundary paragraph calls the original bottom "no-slip",
contradicting Section 5.2.3's opening, explicit conditions and roller support
in Fig. 26. This ambiguity is recorded, not silently resolved by changing
the benchmark. See [the boundary review](tests/notes/yao_boundary_r1.json).
Future inputs must explicitly identify each face and slip condition. A
no-slip-bottom sensitivity run, if needed, must have its own label and must
not be presented as the same physical reference or as an SPR-only change.
The current CPU/GPU SPR path rejects per-marker mixed slip; supporting that
combination requires separate implementation and tests, not a removed guard.

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

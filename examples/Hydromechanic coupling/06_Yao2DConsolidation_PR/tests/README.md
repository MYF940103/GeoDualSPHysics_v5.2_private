# Yao 2D Consolidation Test Data

This directory keeps retained validation and diagnostic assets separate
from the release XML/BAT files in the case root. See [the case README](../README.md)
for the current default and the damping-variant entry points.

- `outputs/`: GenCase, DualSPHysics, raw `data/`, VTK `particles/`, and per-run postprocessed figures.
- `logs/`: GenCase, solver, PartVTK, postprocess, batch stdout/stderr, and PID logs.
- `configs/`: generated variant XML files used by parameter sweeps.
- `figures/`: cross-run comparison plots and CSV summaries.
- `scripts/`: helper run and postprocess scripts.
- `notes/`: test conclusions and validation notes.

Current retained reference output:

- `outputs/CaseYao2DConsolidation_PR_gpu10s_dp01_damp001_nodiffusion_freeslip_out`

Retained output roles:

- Reference: `outputs/CaseYao2DConsolidation_PR_gpu10s_dp01_damp001_nodiffusion_freeslip_out`.
- Damping comparison: `outputs/CaseYao2DConsolidation_PR_gpu10s_dp01_damp000_nodiffusion_freeslip_out`, `outputs/CaseYao2DConsolidation_PR_gpu10s_dp01_damp001_nodiffusion_freeslip_out`, and `outputs/CaseYao2DConsolidation_PR_gpu10s_dp01_damp002_nodiffusion_slip3_out`.
- Slip comparison: `outputs/CaseYao2DConsolidation_PR_gpu10s_dp01_damp002_nodiffusion_out` and `outputs/CaseYao2DConsolidation_PR_gpu10s_dp01_damp002_nodiffusion_slip3_out`.
- Short geometry/boundary diagnostic: `outputs/CaseYao2DConsolidation_PR_gpu02s_dp01_damp002_geomfix_slip1_out`.

Current conclusion:

- `SlipMode=3` with `-mdbc_freeslip` is the retained boundary setting.
- `SoilDampingCoef=0.01` is retained because it suppresses early oscillation without visible loss against `0.02`.
- `DensityDT=0` is retained; DDT1/DDT3 diffusion tests were rejected because they produced particle exclusion or unstable pore-pressure histories.

## Current settings and retention

The current default XML uses `dp=0.1 m`, `DtFixed=2e-5 s`, `TimeMax=10 s`,
`TimeOut=0.05 s`, and `SoilDampingCoef=0.01`. The root also has separate
`damp000`, `damp001`, and `damp002` XML/BAT entry points. The retained reference
listed above is a test output; it is not a root-level `CaseYao2DConsolidation_PR_out`
run produced during this file organization.

Preserve the native data, inputs, logs, comparison figures/CSV, and notes for
all the retained roles above. The earlier
`notes/yao2d_test_conclusions_20260626.md` describes the 0.2 s, slip-mode-1
geometry check and its inventory at that time. The later free-slip/damping
comparisons, recorded in
`notes/yao2d_free_slip_damping_diffusion_conclusions_20260626.md`, determine
the current 10 s reference. Both records remain unchanged.

Normal completion is not, by itself, analytical validation. Retain the
particle-count and left/right boundary-symmetry checks described in the
notes when assessing a new run; do not delete comparison datasets merely
because a conclusion has already been written.

# Yao 2D Consolidation Test Data

This directory keeps temporary validation assets separate from the release XML/BAT files in the case root.

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

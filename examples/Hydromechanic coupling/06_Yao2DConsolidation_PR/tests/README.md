# Yao 2D Consolidation Test Data

## 2026-10-24 CPU/GPU multi-plane SPR candidate

- [Plan, scope and original nodal-load bias](notes/spr_yao_r1.md).
- `spr_yao_short_r1`: four real-program startup controls, original point sets;
  normal output times partly miss each other, so no whole-window half claim.
- `spr_yao_grid02_r1`: the production-step companion saves on integer steps;
  all 21 half pairs pass (0.0705734 Pa, 0.0000113772 mm), and shared original
  endpoints are native-field 0 ULP. PNG/CSV are in `figures` with this prefix.
- `spr_yao_grid10_r1`: fresh SPR off/on/half 0.1-s load-ramp diagnostic;
  completed and reviewed: 101 half pairs pass (0.277975 Pa / 0.000287004 mm),
  all 21 same-dt shorter prefixes are 0 ULP. The first analysis stopped on an
  invalid static-59-node load assumption; no solver rerun was required.
  See `logs/spr_yao_grid10_r1_review_r2.check.json`, `.audit_r3.json`, and
  `.visual.json`; PNG/CSV have the same prefix under `figures`.
- `spr_yao_gpu_load_grid10_r2`: completed .1-s GPU off/on/half; all 101 pairs
  pass (0.277974 Pa / 0.000287018 mm), all 21 same-dt short prefixes 0 ULP.
  CPU/GPU maximum pressure RMS is 0.001324 Pa, material displacement
  0.000002845 mm; native sampled loading agrees exactly. See its review/visual
  receipts, [history](figures/spr_yao_gpu_load_grid10_r2_history.png),
  [fields](figures/spr_yao_gpu_load_grid10_r2_fields_r2.png) and matching CSVs.
- Older GPU raw/grid .02 r1 physically completed, but load diagnostics were
  absent. The output-only repair is proved by r2 .02 non-load fields 0 ULP;
  historical r1 files and earlier GPU BATs with CPU-labelled names are retained
  for provenance, not recommended new entries. New .1/.3-s BATs say GPU.
- `spr_yao_gpu_post03_r1`: completed .3-s GPU post-ramp off/on/half, 1-ms output,
  same original geometry/load/dt and 301 pairs with the original 5-Pa/.005-mm
  limits. It must retain all 101 same-dt .1-s native prefixes exactly. CPU
  comparison remains limited to .1 s. All 301 half pairs pass
  (0.277974 Pa / 0.000287018 mm); post-ramp maxima 0.140043 Pa / 0.000182407 mm.
  [Mechanics](figures/spr_yao_gpu_post03_r1_mechanics_r1.png),
  [native fields](figures/spr_yao_gpu_post03_r1_fields_r1.png) and matching CSVs
  are reviewed; see its audit/visual receipts. The one-shot queued once and
  exited; never restart it. Not full 2-D theory acceptance.
- Each new variant has a matching XML/BAT under `configs`; double-click
  refuses retained output directories. Companion binaries/build records are
  under `outputs`/`logs`; helpers remain under existing `scripts`, not a second
  `support` directory. HG/NoPen remain off for this independent 2-D test.

- Completed bounded stage: [1-s CPU/GPU review](notes/spr_yao_1s_r1.md),
  `logs/spr_yao_cpu_gpu_1s_r1.status.json`. Only fresh SPR-on CPU8 coarse,
  GPU coarse/half, with complete single-run gates between stages and original
  all-1001-sample 5-Pa/.005-mm pair limits. One new one-shot waits for this
  sequence, not any old worker. All 1001 cross/half pairs passed:
  cross 0.000630828 Pa / 0.00000196073 mm; half 0.277974 Pa / 0.000287018 mm.
  [History](figures/spr_yao_cpu_gpu_1s_r1_history.png),
  [native fields](figures/spr_yao_cpu_gpu_1s_r1_fields_r1.png) and matching CSVs
  were inspected; audit and visual receipts are in logs. No 1-s SPR-off or
  full 2-D theory acceptance. The one-shot has exited and must not be restarted.
- Production candidate and evidence through .3 s were selectively committed
  and verified local/remote at `7fda9ff`; raw BI4/executables are not cloud
  backed up by that commit. New 1-s artifacts await their own later backup.

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

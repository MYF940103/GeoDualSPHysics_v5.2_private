# Self-weight consolidation tests cleanup, 2026-07-04

This cleanup keeps only complete/reference-value outputs and removes short-window or superseded runs whose conclusions have already been recorded in notes.

## Retained output groups

- `CaseSWStage1_TwoStage_Damp002_DrainShep40_t040_GPU_out`
  - Accepted two-stage Stage 1 baseline: `SoilDampingCoef=0.02`, drainage on, pore-pressure Shepard interval 40.
- `CaseSWScenario2_TwoStage_Damp002_DTv0005_from_p0060_GPU_out`
  - Accepted two-stage Scenario 2 baseline. This remains the main complete comparison group.
- `CaseSWSt1_HeadN_GPU_out`
  - Current Head-Neumann / MLS boundary Stage 1 group. Kept because it is the restart source for the latest boundary-consistency tests.
- `CaseSWSc2_HeadN_Tv2_from_p0056_GPU_out`
  - Latest Head-Neumann long run. It was intentionally stopped after the late platform was identified, but it is retained because it contains the platform-onset interval and restart snapshots around Tv 1.20-1.30.
- `CaseSWSt1_MLSg2_GPU_out` and `CaseSWSc2_MLSg2_Tv2_from_p0040_GPU_out`
  - MLS ghost/slip-mode comparison group. Kept as the main boundary-method comparison against the accepted two-stage baseline and the Head-Neumann branch.
- Diagnostic figure folders:
  - `mdbc_head_diff_direct_boundary_diag`
  - `mdbc_pore_mls_recovery`
  - `mdbc_pore_mls_recovery_neumann_ghost`

## Removed output groups

- `CaseSWSc2_HeadN_Tv01_from_p0056_GPU_out`
  - Superseded by the retained Head-Neumann Tv=2 run, which includes the early-time interval.
- `CaseSWSc2_HeadN_PlatformShort_from_p0180_GPU_out`
  - Short-window diagnostic only. Conclusion is preserved in the cleanup notes and the retained long run.
- `CaseSWSc2_MLSg2_PlatformShort_from_p0180_GPU_out`
  - Short-window diagnostic only. Superseded by the full MLSg2 Tv=2 group.
- `CaseSWSc2_MLSs2_Tv2_from_p0053_GPU_out` and `CaseSWSt1_MLSs2_GPU_out`
  - Older slip-mode/MLS variant. It did not improve the early accuracy or late platform behavior relative to the retained comparison groups.

Matching figure folders and XML configs for removed output groups were removed as well.

Transient root-level test runners/logs (`run_*.log`, `run_*.err.log`, and `xCase*.bat`) were removed from `tests` after conclusions were preserved. Reproducible state is kept through `configs`, `outputs`, `figures`, `support`, and this note set.

## Conclusions preserved

1. The accepted baseline remains the two-stage `damping=0.02 -> damping=0.02` Scenario 2 group.
2. Later `damping=0` checks showed the late bottom-pressure platform is not caused by soil damping smoothing.
3. MLS/Head-Neumann boundary treatments improve the boundary extrapolation consistency in linear-field diagnostics, but the late platform can still reappear after about Tv 1.2.
4. Short-window platform tests are useful as conclusions but not worth retaining as bulky output folders once the longer comparison groups are kept.

# Self-Weight Tests Cleanup

Date: 2026-07-06

## Kept Complete Output Groups

The following complete Stage 1 / Scenario 2 output groups were retained because they are still useful for comparison:

- `outputs/CaseSWStage1_TwoStage_Damp002_DrainShep40_t040_GPU_out`
- `outputs/CaseSWScenario2_TwoStage_Damp002_DTv0005_from_p0060_GPU_out`
- `outputs/CaseSWSt1_HeadN_GPU_out`
- `outputs/CaseSWSc2_HeadN_Tv2_from_p0056_GPU_out`
- `outputs/CaseSWSt1_MLSDirect_GPU_out`
- `outputs/CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out`
- `outputs/CaseSWSt1_HeadN_PairwiseOpt_GPU_out`
- `outputs/CaseSWSc2_HeadN_Tv2_PairwiseOpt_from_p0056_GPU_out`

The corresponding figure folders and active XML configs were also retained.

## Removed Diagnostic / Temporary Items

Removed output and figure folders from one-off diagnostics or superseded variants:

- `MLSDirect ... cmdmdbc_override`
- `MLSg2` Stage 1 and Scenario 2 variants
- `CaseSWSc2_HeadN_Tv120_130_support_diag`
- `mdbc_head_diff_direct_boundary_diag`
- `mdbc_pore_mls_recovery`
- `mdbc_pore_mls_recovery_neumann_ghost`

Removed superseded XML configs:

- `configs/CaseSWSc2_MLSg2_Tv2_Def.xml`
- `configs/CaseSWSt1_MLSg2_Def.xml`

## Current Conclusion

The retained data now represents the useful complete comparison families:

- zero-order/two-stage baseline;
- head-Neumann style runs;
- MLSDirect runs;
- pairwise optimized diagnostic full run.

Short-window and linear-recovery diagnostic outputs were removed after their conclusions had already been recorded in notes.

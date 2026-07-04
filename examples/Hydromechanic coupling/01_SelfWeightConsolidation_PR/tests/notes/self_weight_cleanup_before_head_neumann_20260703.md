# Self-weight scenario 2 cleanup before head-Neumann boundary test

Date: 2026-07-03

## Kept

- `outputs/CaseSWStage1_TwoStage_Damp002_DrainShep40_t040_GPU_out`
- `outputs/CaseSWScenario2_TwoStage_Damp002_DTv0005_from_p0060_GPU_out`
- `figures/CaseSWStage1_TwoStage_Damp002_DrainShep40_t040_GPU`
- `figures/CaseSWScenario2_TwoStage_Damp002_DTv0005_from_p0060_GPU`

These are the complete two-stage damping=0.02 reference outputs retained for comparison.

## Removed test-output families

- `CaseSWDiagPoreRate_Tv120_*`: temporary pore-pressure-rate diagnostic outputs.
- `CaseSWScenario2_Tv120_130_Noflux_GPU`: short-window zero-boundary-flux/exclusion diagnostic.
- `CaseSWScenario2_Tv120_130_NoBoundPoreRate_GPU`: short-window boundary-pore-rate exclusion diagnostic.
- `CaseSWScenario2_Tv120_130_Slip2_MDBCCorr0_GPU`: invalid short-window test because SlipMode was changed to 2 only after restarting from a SlipMode=1 state at `Part_0240`, producing an incompatible mechanical state jump.

## Conclusions before next test

1. Simple boundary diffusion exclusion is not a satisfactory long-term solution.
2. Boundary pore pressure should still participate in the seepage operator, but only through a pairwise hydraulic-head Neumann ghost.
3. A SlipMode=2 comparison must be run as a continuous long test, not by switching the mDBC mode in a late restart window.
4. Next valid source test: implement pairwise `h_ghost=h_i` in the `khyd>0` boundary-neighbor seepage branch, then run a late-window GPU check followed by a continuous long comparison if the short-window behavior is sane.

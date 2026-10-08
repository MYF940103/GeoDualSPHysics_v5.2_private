# Late pore-rate residual diagnostic, 2026-07-27

Purpose: isolate whether the late excess pore-pressure platform in Lian 2023 strip footing and 1D consolidation cases is caused mainly by the first-order correction matrix in the pore-pressure-rate compression/seepage terms.

Temporary solver switch:

- `DSPH_TMP_PORE_DIAG_CORR_MODE=0`: current implementation.
- `DSPH_TMP_PORE_DIAG_CORR_MODE=1`: disable first-order correction in the pore-pressure-rate term for all pairs.
- `DSPH_TMP_PORE_DIAG_CORR_MODE=2`: keep fluid-fluid corrected, disable correction only for fluid-bound pairs.
- `DSPH_TMP_PORE_DIAG_POREVEL_MODE=1`: diagnostic only, use raw boundary velocity difference in the pore-rate compression term instead of the mDBC tangential ghost velocity.

The values below are first-step restart diagnostics. They are mean rates per selected active pore-pressure particle, in Pa/s.

| Case/window | Mode | mean(comp) | mean(seep) | mean(total) | Interpretation |
|---|---:|---:|---:|---:|---|
| Lian t=3s, left-bottom x=[0,4], z=[0,2] | current | 15452.1 | -15463.1 | -11.1 | Clear late comp/seep cancellation. |
| Lian t=3s, left-bottom | no correction, all pairs | 15380.4 | -15391.4 | -11.0 | Almost unchanged, so the platform is not removed by disabling correction. |
| Lian t=3s, left-bottom | no correction, fluid-bound only | 15451.0 | -15461.3 | -10.3 | Also almost unchanged. |
| Lian t=3s, left-bottom | raw boundary velocity diagnostic | 15229.4 | -15463.1 | -233.8 | Boundary ghost/tangential velocity affects the residual direction and magnitude. |
| SelfWeight Part_0300 | current | 30151.2 | -27970.7 | 2180.5 | Positive late residual remains. |
| SelfWeight Part_0300 | no correction, all pairs | 52072.6 | -26635.1 | 25437.5 | Disabling correction greatly worsens the late residual. |
| SelfWeight Part_0300 | no correction, fluid-bound only | 30604.8 | -26374.4 | 4230.3 | Boundary-only no-correction also worsens the residual. |
| SelfWeight Part_0300 | raw boundary velocity diagnostic | 30151.2 | -27970.7 | 2180.5 | No observable effect in this case/window. |
| q0 k=1e-4 Part_0300 | current | 5929.7 | 5163.9 | 11093.6 | This restart state is still strongly positive; not a clean cancellation window. |
| q0 k=1e-4 Part_0300 | no correction, all pairs | 10295.5 | -17.0 | 10278.5 | Still positive, not solved by correction removal. |
| q0 k=1e-4 Part_0300 | no correction, fluid-bound only | 5945.6 | 5156.7 | 11102.3 | Almost unchanged from current. |
| Lian t=1s, strip x=[0,1.25], z=[8,10.1] | current | 448304.4 | -308121.9 | 140182.6 | Early loaded region is dominated by loading/compression. |
| Lian t=1s, strip | no correction, all pairs | 371033.8 | -301775.1 | 69258.8 | Disabling correction changes the early response substantially. |
| Lian t=1s, strip | no correction, fluid-bound only | 446970.3 | -307601.9 | 139368.3 | Boundary-only correction removal barely changes early response. |

Conclusion:

1. The late platform is not primarily caused by using the first-order correction matrix in the pore-pressure-rate term. Lian t=3s is almost unchanged when correction is disabled, while SelfWeight becomes worse.
2. The strongest current clue is the boundary velocity path in the pore-rate compression term. In Lian t=3s, replacing mDBC tangential ghost velocity by raw velocity difference changes the mean total rate from about -11 Pa/s to about -234 Pa/s.
3. The boundary correction matrix is not the dominant issue: hybrid fluid-bound no-correction barely affects Lian t=3s and early t=1s, and worsens SelfWeight.
4. Next formal debugging should focus on mDBC hydraulic/mechanical consistency for the compression term: wall ghost velocity construction, tangential/no-penetration velocity used in `div(v_s)`, and whether impermeable hydraulic ghost pressure is being paired with a mechanically appropriate solid velocity field.

Kept records:

- `late_corrdiag_firststep_combined.csv`
- `late_corrdiag_firststep_detail.csv`

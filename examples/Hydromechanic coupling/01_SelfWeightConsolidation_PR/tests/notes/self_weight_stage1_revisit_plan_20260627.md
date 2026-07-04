# Self-Weight Stage 1 Revisit Plan

Date: 2026-06-27

Purpose: rebuild the Stage 1 self-weight consolidation verification around a physically undrained loading phase before applying a drained top free-surface boundary in Scenario 1/2.

## Baseline Test

Case:

- `configs/CaseSWStage1_d02_ND_NS_Def.xml`
- `xCaseSWStage1_d02_ND_NS_win64_CPU.bat`

The short case name avoids old GenCase/VTK path-length failures in the deep
`Hydromechanic coupling/01_SelfWeightConsolidation_PR/tests` folder.

Key settings:

- `HydraulicConductivity=0`
- `HydroMechDrainage=0`
- `PoreShepardRegularization=0`
- `Visco=0.4`
- `SoilDampingCoef=0.02`
- `DtFixed=1e-6 s`
- `TimeMax=0.40 s`
- `TimeOut=0.005 s`

Rationale:

- The supporting material describes the top free surface as drained after the initial undrained response, so Stage 1 should not force `pw=0` on the free surface.
- The current GeoDualSPHysics damping formula differs from the paper notation, so the first revised test uses `SoilDampingCoef=0.02` instead of the paper's `xi=4e-5`.
- Shepard pore-pressure regularization is disabled in the baseline so that the unfiltered PR response can be evaluated first.

## Acceptance Checks

The postprocessor writes:

- `figures/<case>/<case>_stage1_metrics.csv`
- `figures/<case>/<case>_final_profile.csv`
- `figures/<case>/<case>_stage1_diagnostics.png`
- `figures/<case>/<case>_summary.txt`

Use these checks before moving to Scenario 1/2:

- final pore-pressure profile should match the undrained self-weight theory based on `RhopZero`;
- RMS pore-pressure error and high-frequency residual should decay or plateau at an acceptable level;
- maximum particle speed should become small enough that the profile is mechanically settled;
- `max_kplastic` should remain zero for this elastic verification.

## Next Comparisons

If the baseline still has visible checkerboarding or a high-frequency residual, add a second test with the same settings and `PoreShepardRegularization=1`, `PoreShepardInterval=40`.

If the baseline is smooth but not yet kinematically settled by `0.40 s`, extend only `TimeMax` and keep the same configuration.

## Results From Initial Revisit

Completed cases:

| case | drainage | Shepard | final time [s] | bottom error [kPa] | RMS pore error [kPa] | HF pore RMS [kPa] | max speed [m/s] | max Kplastic |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `CaseSWStage1_d02_ND_NS` | 0 | 0 | 0.40 | +0.755 | 0.416 | 0.612 | 2.29e-5 | 0 |
| `CaseSWStage1_d02_ND_SH40` | 0 | 1 / 40 | 0.40 | -0.860 | 0.190 | 0.0041 | 3.43e-5 | 0 |

Files:

- `figures/stage1_revisit_final_metrics_compare.csv`
- `figures/CaseSWStage1_d02_ND_NS/CaseSWStage1_d02_ND_NS_stage1_diagnostics.png`
- `figures/CaseSWStage1_d02_ND_SH40/CaseSWStage1_d02_ND_SH40_stage1_diagnostics.png`

Interpretation:

- Disabling drainage in Stage 1 is necessary and works as intended; `Run.out` reports `HydroMechDrainage="Disabled"`.
- With `SoilDampingCoef=0.02` and no Shepard filtering, the layer-averaged final profile is close to the undrained theory, but the final profile still has visible high-frequency/odd-even oscillation.
- Enabling Shepard every 40 steps almost eliminates the high-frequency residual while keeping the profile close to the theory. It slightly underestimates the bottom pore pressure by about `0.86 kPa`.
- Both tests remain elastic (`max Kplastic=0`) and the maximum particle speed is already small at `0.40 s`.

Recommended next step:

- Treat `CaseSWStage1_d02_ND_SH40` as the current best stable Stage 1 restart candidate.
- Before restarting Scenario 1/2, run one more longer `d02_ND_SH40` case only if stricter bottom-pressure matching is required; otherwise proceed to a restart/dissipation test and check whether the small bottom underestimation affects the early profile.

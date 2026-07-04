# Self-weight Scenario 2 support/composition diagnostic

Date: 2026-06-29

## Purpose

This diagnostic follows the retained Scenario 2 baseline windows and checks whether the mid/late pore-pressure deviation is caused by:

- poor corrected-gradient matrix quality near the bottom boundary;
- sudden changes in neighbor count or support-domain composition;
- sudden changes in fluid-vs-boundary neighbor contributions to the two large pore-rate terms, `-divv` and `lapw`.

No temporary C++/CUDA source changes were introduced for this pass. The analysis recomputes the bottom-row pore-rate interaction terms offline from saved `PartFluid` and `PartBound` VTK outputs.

## Inputs

- `tests/outputs/CaseSWScenario2_restart_p0060_D_ratecomp_Tv030_034_out`
- `tests/outputs/CaseSWScenario2_restart_p0100_D_ratecomp_Tv050_054_out`

Both windows use `PoreShepardRegularization=0`; Shepard regularization is not active in these diagnostics.

## Outputs

- `tests/support/diagnose_support_composition_offline.py`
- `tests/figures/CaseSWScenario2_restart_p0060_D_support_offline_Tv030_034/support_composition_timeseries.csv`
- `tests/figures/CaseSWScenario2_restart_p0060_D_support_offline_Tv030_034/support_composition_diagnostics.png`
- `tests/figures/CaseSWScenario2_restart_p0100_D_support_offline_Tv050_054/support_composition_timeseries.csv`
- `tests/figures/CaseSWScenario2_restart_p0100_D_support_offline_Tv050_054/support_composition_diagnostics.png`
- `tests/figures/self_weight_scenario2_support_offline_compare/support_composition_event_segments.csv`
- `tests/figures/self_weight_scenario2_support_offline_compare/support_composition_event_deltas.csv`
- `tests/figures/self_weight_scenario2_support_offline_compare/support_component_event_summary.png`
- `tests/figures/self_weight_scenario2_support_offline_compare/support_bottom_velocity_zcomp_summary.png`
- `tests/outputs/CaseSWScenario2_restart_p0100_D_ratecomp_Tv050_054_cpu_out`
- `tests/figures/self_weight_scenario2_cpu_gpu_Tv050_054_compare/cpu_gpu_support_vz_divv_compare.csv`
- `tests/figures/self_weight_scenario2_cpu_gpu_Tv050_054_compare/cpu_gpu_support_vz_divv_summary.csv`
- `tests/figures/self_weight_scenario2_cpu_gpu_Tv050_054_compare/cpu_gpu_bottom_vz_zdivv_compare.png`

## Quantitative findings

Segment averages around the two event windows:

| Window | Segment | Fluid nbrs | Bound nbrs | lcorr cond | comp fluid kPa/s | comp bound kPa/s | comp total kPa/s | lapw total kPa/s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Tv 0.30-0.34 | pre | 21.83 | 15.00 | 1.000789 | 276.4 | 526.2 | 802.7 | -814.7 |
| Tv 0.30-0.34 | event | 22.88 | 15.00 | 1.000798 | 252.5 | 388.2 | 640.7 | -652.7 |
| Tv 0.30-0.34 | post | 23.00 | 15.00 | 1.000806 | 257.7 | 367.0 | 624.8 | -637.0 |
| Tv 0.50-0.54 | pre | 23.00 | 15.00 | 1.000993 | 178.6 | 308.1 | 486.7 | -501.0 |
| Tv 0.50-0.54 | event | 23.00 | 15.00 | 1.000998 | 230.0 | 30.1 | 260.2 | -274.0 |
| Tv 0.50-0.54 | post | 23.00 | 15.00 | 1.001000 | 138.4 | 116.5 | 255.0 | -269.0 |

Main observations:

1. The bottom support domain is stable. Boundary-neighbor count stays exactly 15 in both windows; fluid-neighbor count is either constant or changes smoothly.
2. The corrected-gradient matrix is well-conditioned. The x-z correction condition number remains close to 1.001, with no event-scale jump.
3. The strongest event-scale change is in the boundary-neighbor contribution to the compression term `-divv`.
   - In the Tv 0.50-0.54 window, boundary compression drops from about 308 kPa/s to about 30 kPa/s during the event window.
   - The support metrics do not change at the same time, so this is unlikely to be a neighbor-list or corrected-gradient singularity problem.
4. The Darcy/lapw fluid and boundary sub-contributions are large and opposite in sign, but their total changes in the same direction as the compression total. This suggests the lapw term is responding to the same local state change rather than independently causing a global slow-diffusion bias.

Additional z-component check:

| Window | Segment | bottom mean vz m/s | comp bound x kPa/s | comp bound z kPa/s | bound top EPWP kPa |
| --- | ---: | ---: | ---: | ---: | ---: |
| Tv 0.30-0.34 | pre | -2.123e-05 | 0.0 | 526.2 | 4.102 |
| Tv 0.30-0.34 | event | -1.566e-05 | 0.0 | 388.2 | 4.018 |
| Tv 0.30-0.34 | post | -1.480e-05 | 0.0 | 367.0 | 3.951 |
| Tv 0.50-0.54 | pre | -1.243e-05 | 0.0 | 308.1 | 2.532 |
| Tv 0.50-0.54 | event | -1.215e-06 | 0.0 | 30.1 | 2.478 |
| Tv 0.50-0.54 | post | -4.699e-06 | 0.0 | 116.5 | 2.440 |

The boundary-neighbor compression change is essentially all in the z component. Boundary-top pore pressure decreases smoothly, and boundary velocities in the saved `PartBound` fields are zero. Therefore the event is better described as a bottom-fluid vertical-velocity / compression-state disturbance entering the boundary-neighbor `divv` contribution, not as a boundary pore-pressure discontinuity.

## Current interpretation

The mid/late deviation is not explained by Shepard filtering, neighbor-count loss, support-domain composition, or corrected-gradient matrix quality.

The most likely source is the vertical velocity/compression state of the bottom fluid row as seen through boundary-neighbor interactions in the pore-rate loop. The next targeted check should inspect the momentum/stress update that produces the bottom-fluid `vz` relaxation and rebound, plus mDBC predictor/corrector timing. If CPU and GPU differ in this bottom-fluid `vz` and z-compression state over the same windows, then a GPU-specific issue is justified; otherwise the issue is probably formulation/configuration-level rather than GPU precision.

## CPU/GPU short-window comparison

A CPU run was added for the same Tv 0.50-0.54 restart window:

- `tests/xCaseSWScenario2_restart_p0100_D_ratecomp_Tv050_054_win64_CPU.bat`
- restart source: `outputs/CaseSWScenario2_restart_p0060_D_DTv0005_out/data/Part_0100.bi4`
- `DtFixed=1e-6`, `TimeOut=0.00364371428`, `PoreShepardRegularization=0`

CPU and GPU are effectively identical in the targeted quantities:

| Field | max abs CPU-GPU |
| --- | ---: |
| bottom EPWP | 2.36e-4 kPa |
| bottom mean vz | 2.74e-7 m/s |
| boundary z compression | 6.80 kPa/s |
| fluid z compression | 4.74 kPa/s |
| total compression | 4.73 kPa/s |
| neighbor counts | 0 |
| lcorr condition number | 4.16e-8 |

The CPU/GPU overlap means the Tv 0.50-0.54 rebound is not a GPU-specific precision or CUDA branch issue. The next diagnosis should target common CPU/GPU formulation paths: bottom-fluid momentum/stress update, artificial viscosity/damping interaction, and mDBC predictor/corrector coupling to the bottom row.

## Bottom momentum decomposition

An offline momentum-term reconstruction was added without modifying solver source code:

- `tests/support/diagnose_bottom_momentum_terms_offline.py`
- `tests/figures/CaseSWScenario2_restart_p0060_D_momentum_offline_Tv030_034_gpu/bottom_momentum_terms_timeseries.csv`
- `tests/figures/CaseSWScenario2_restart_p0060_D_momentum_offline_Tv030_034_gpu/bottom_momentum_terms_diagnostics.png`
- `tests/figures/CaseSWScenario2_restart_p0100_D_momentum_offline_Tv050_054_gpu/bottom_momentum_terms_timeseries.csv`
- `tests/figures/CaseSWScenario2_restart_p0100_D_momentum_offline_Tv050_054_gpu/bottom_momentum_terms_diagnostics.png`
- `tests/figures/CaseSWScenario2_restart_p0100_D_momentum_offline_Tv050_054_cpu/bottom_momentum_terms_timeseries.csv`
- `tests/figures/CaseSWScenario2_restart_p0100_D_momentum_offline_Tv050_054_cpu/bottom_momentum_terms_diagnostics.png`
- `tests/figures/self_weight_scenario2_bottom_momentum_residual_compare.png`

The reconstruction mirrors the saved-output part of the momentum loop:

- total-stress z acceleration using `Sigma_kk[2]` as `sigma_zz` and `Sigma_ij[2]` as `sigma_xz` (`Sigma_ij=(xy,yz,xz)` in the VTK output)
- pore-pressure feedback acceleration using the same pairwise `-(pw1+pw2)/(rho1*rho2)` form
- Monaghan artificial viscosity with `Visco=0.4` and `Cs0=35.805744`
- Bui-Fukagawa soil damping with `SoilDampingCoef=4e-5`
- gravity

The main result is that bottom `vz` rebound is governed by a very small residual left after large cancellations:

| Window | Tv | vz m/s | fd dvz/dt m/s2 | stress m/s2 | pore m/s2 | artificial visc m/s2 | total reconstructed m/s2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.30-0.34 | 0.318 | -1.689e-5 | 3.76e-4 | 5.1819 | 4.6243 | 4.15e-3 | 4.19e-4 |
| 0.30-0.34 | 0.320 | -1.561e-5 | -5.39e-5 | 5.1832 | 4.6232 | 3.58e-3 | 6.50e-7 |
| 0.50-0.54 | 0.520 | -2.474e-6 | 5.89e-4 | 5.1992 | 4.6141 | -2.92e-3 | 4.63e-4 |
| 0.50-0.54 | 0.523 | -8.893e-7 | -1.41e-4 | 5.2037 | 4.6104 | -3.96e-3 | 1.19e-4 |

The individual fluid and boundary neighbor terms are much larger than the final totals. For example, at Tv=0.52:

- stress contribution: `-289.47 + 294.67 = 5.199 m/s2`
- pore-feedback contribution: `-428.87 + 433.49 = 4.614 m/s2`
- gravity: `-9.81 m/s2`
- artificial viscosity: `-2.92e-3 m/s2`

Therefore the observed bottom `vz` relaxation/rebound is not caused by a large isolated term. It is a near-equilibrium residual problem: smooth but large fluid/boundary stress and pore-feedback terms cancel, and artificial viscosity changes sign or magnitude as the local compression state changes. The mDBC boundary contributions are large and smooth, so current evidence does not support a sudden mDBC pore-pressure or stress discontinuity. Instead, mDBC makes the bottom-row momentum balance highly sensitive because boundary and fluid neighbor terms nearly cancel.

The CPU/GPU momentum decomposition over Tv 0.50-0.54 again overlaps closely:

| Field | max abs CPU-GPU |
| --- | ---: |
| bottom vz | 2.74e-7 m/s |
| fd dvz/dt | 1.33e-4 m/s2 |
| reconstructed total acceleration | 4.18e-3 m/s2 |
| stress acceleration | 4.51e-3 m/s2 |
| pore-feedback acceleration | 1.39e-4 m/s2 |
| artificial-viscosity acceleration | 1.88e-4 m/s2 |

This further supports a common formulation/configuration source rather than a CUDA-specific implementation issue.

Recommended next targeted tests:

1. Short-window Tv 0.50-0.54 restart with reduced or disabled artificial viscosity (`Visco=0` and/or `Visco=0.1`) while keeping all other settings fixed. This directly tests whether the artificial-viscosity switch controls the rebound phase.
2. If artificial viscosity is confirmed, test a smoother or smaller damping/viscosity setting rather than increasing soil damping, since previous `SoilDampingCoef=0.02` full-run comparison did not remove the late plateau.
3. Only if the viscosity test does not change the rebound, add a temporary solver diagnostic for bottom-row `Ace.z` and stress-rate terms, then remove it immediately after the window test.

## Artificial-viscosity short-window sweep

Two additional Tv 0.50-0.54 GPU windows were run from the same restart with only the artificial-viscosity coefficient changed:

- `tests/xCaseSWScenario2_restart_p0100_D_ratecomp_Tv050_054_visco0_win64_GPU.bat`
- `tests/xCaseSWScenario2_restart_p0100_D_ratecomp_Tv050_054_visco01_win64_GPU.bat`
- `tests/configs/CaseSWSc2_Tv050_054_v0_Def.xml`
- `tests/configs/CaseSWSc2_Tv050_054_v01_Def.xml`
- outputs: `tests/outputs/CaseSWSc2_Tv050_054_v0_out`
- outputs: `tests/outputs/CaseSWSc2_Tv050_054_v01_out`

Both runs used the same restart, `DtFixed=1e-6`, `PoreShepardRegularization=0`, `SlipMode=1`, and `mDBC-Corrector=True`. Both completed with zero excluded particles.

Comparison outputs:

- `tests/figures/self_weight_scenario2_visco_sweep_Tv050_054_compare/visco_sweep_Tv050_054_compare.png`
- `tests/figures/self_weight_scenario2_visco_sweep_Tv050_054_compare/visco_sweep_Tv050_054_summary.csv`
- `tests/figures/self_weight_scenario2_visco_sweep_Tv050_054_compare/visco_sweep_Tv050_054_timeseries.csv`

Key metrics:

| Case | max vz m/s | Tv at max vz | vz range m/s | bottom error end kPa | event mean bottom error kPa | max abs dvz/dt m/s2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Visco=0.4 baseline | -5.769e-7 | 0.522 | 1.559e-5 | 0.0915 | 0.0719 | 6.824e-4 |
| Visco=0.1 | 2.429e-7 | 0.521 | 2.408e-5 | 0.0904 | 0.0717 | 2.105e-3 |
| Visco=0 | 1.478e-6 | 0.519 | 3.369e-5 | 0.0854 | 0.0730 | 4.318e-3 |

Interpretation:

- Reducing or disabling artificial viscosity does not remove the Tv 0.50-0.54 bottom-row rebound.
- `Visco=0` makes the bottom `vz` oscillation substantially larger and introduces high-frequency swings in the boundary-neighbor z-compression term.
- `Visco=0.1` changes the phase and slightly lowers the late residual, but still produces a larger `vz` range than the baseline.
- The EPWP residual curves remain close over this short window, so the late full-run plateau is unlikely to be caused primarily by the Monaghan artificial-viscosity switch.

Updated conclusion: artificial viscosity modulates and damps an existing bottom support residual; it is not the primary source of the mid/late deviation. The next diagnosis should focus on the near-cancellation between stress, pore-pressure feedback, gravity, and bottom mDBC support terms, especially whether the total-stress and pore-feedback discretizations are exactly consistent with the intended u-pw effective/total stress split at mDBC boundaries.

## mDBC effective/total stress split check

An additional offline diagnostic was added:

- `tests/support/diagnose_mdbc_stress_pore_split_offline.py`
- GPU outputs: `tests/figures/CaseSWScenario2_restart_p0100_D_mdbc_split_Tv050_054_gpu`
- CPU outputs: `tests/figures/CaseSWScenario2_restart_p0100_D_mdbc_split_Tv050_054_cpu`
- compact summary: `tests/figures/self_weight_scenario2_mdbc_split_Tv050_054_summary.csv`

The source-code path is:

- `InitHydroMechState()` initializes `Sigma` as effective stress for analytical self-weight mode.
- The momentum loop adds the stress tensor term and then adds the u-pw pore-pressure feedback term separately.
- Therefore the equivalent tensile-positive total normal stress represented by the two terms is `sigma_total_zz = sigma_eff_zz - pw`.
- Strictly, the stress term uses `sigma_i/rho_i^2 + sigma_j/rho_j^2`, while the pore-feedback term uses `-(pw_i+pw_j)/(rho_i rho_j)`. In this diagnostic window the bottom fluid and inner mDBC boundary layers both have `Rhop=2100`, so the two-term form is equivalent to the combined `sigma' - pw I` total-stress form for this case.
- The mDBC correction extrapolates `sigma` from fluid stress and extrapolates pore pressure as `porepress0(bound) + weighted_excess_from_fluid`.

For the bottom inner boundary layer over Tv 0.50-0.54, the boundary-fluid interface split is smooth:

| Platform | bound-fluid sigma'_zz range kPa | bound-fluid pw range kPa | bound-fluid total zz range kPa | fluid total-theory range kPa |
| --- | ---: | ---: | ---: | ---: |
| GPU | 0.00202 | 0.00025 | 0.00222 | 0.00434 |
| CPU | 0.00202 | 0.00025 | 0.00221 | 0.00433 |

Selected GPU values:

| Tv | fluid sigma'_zz kPa | bound sigma'_zz kPa | fluid pw kPa | bound pw kPa | fluid total zz kPa | bound total zz kPa |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.500 | -7.989 | -8.316 | 12.251 | 12.545 | -20.240 | -20.861 |
| 0.520 | -8.137 | -8.465 | 12.101 | 12.395 | -20.238 | -20.860 |
| 0.523 | -8.154 | -8.483 | 12.083 | 12.377 | -20.236 | -20.859 |
| 0.540 | -8.234 | -8.562 | 12.003 | 12.297 | -20.237 | -20.860 |

Interpretation:

- The boundary layer has a stable offset relative to the first fluid layer, but it does not show a sudden jump or sign change at Tv around 0.52.
- The equivalent total normal stress `sigma'_zz - pw` is close to the self-weight total-stress line in both fluid and boundary layers, with only about 0.05 kPa residual over the window.
- CPU and GPU produce essentially the same mDBC split, so this is not a GPU-only boundary precision issue.
- The large momentum terms still cancel at the `m/s2` level: for example near Tv=0.52, effective-stress acceleration is about 5.199 m/s2, pore feedback about 4.614 m/s2, gravity -9.81 m/s2, and the remaining acceleration is O(1e-4) m/s2.

Updated conclusion: the current output evidence does not indicate an inconsistent effective/total stress split at the bottom mDBC boundary. The bottom support is numerically delicate because smooth fluid and boundary terms are individually hundreds of m/s2 before cancellation, but the boundary `sigma'`, `pw`, and `sigma'-pw` fields themselves are smooth. The next suspect should be the common CPU/GPU formulation path that creates the small residual in the bottom-row momentum balance, such as predictor/corrector timing of stress and pore feedback, the density/volume used in boundary-neighbor momentum pairs, or whether the separate effective-stress and pore-feedback discretizations remain exactly hydrostatic/self-weight balanced at the discrete bottom support.

## Split stress versus single total-stress balance

The offline momentum script was extended with additional diagnostic columns:

- `ace_single_totalstress_z_m_s2`: direct pairwise acceleration using `sigma_total = sigma' - pw I`.
- `ace_exact_totalstress_z_m_s2`: pairwise acceleration using an exact theoretical self-weight total stress line, `sigma_total_zz = -rho*g*(top-z)`.
- `ace_exact_balance_z_m_s2`: `exact_totalstress + gravity`.
- `ace_actual_totalstress_minus_exact_z_m_s2`: actual saved total stress minus the exact self-weight total-stress contribution.
- `ace_actual_balance_no_visc_damping_z_m_s2`: actual total-stress contribution plus gravity, excluding artificial viscosity and soil damping.

Comparison outputs:

- `tests/figures/self_weight_scenario2_totalstress_balance_Tv050_054_compare/totalstress_balance_compare.png`
- `tests/figures/self_weight_scenario2_totalstress_balance_Tv050_054_compare/totalstress_balance_summary.csv`

Main findings:

| Platform | split-single range m/s2 | exact total+gravity range m/s2 | actual-exact total range m/s2 | actual total+gravity range m/s2 |
| --- | ---: | ---: | ---: | ---: |
| GPU | 2.17e-13 | 1.94e-2 | 2.32e-2 | 8.98e-3 |
| CPU | 2.07e-13 | 1.95e-2 | 2.30e-2 | 9.18e-3 |

Selected GPU values:

| Tv | split stress+pore | single total-stress | split-single | exact total+gravity | actual-exact total | actual total+gravity | artificial viscosity | final total accel |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.500 | 9.80510 | 9.80510 | 4.97e-15 | -0.13475 | 0.12985 | -0.00490 | 0.00492 | 2.09e-5 |
| 0.520 | 9.81338 | 9.81338 | 1.18e-13 | -0.13718 | 0.14056 | 0.00338 | -0.00292 | 4.59e-4 |
| 0.523 | 9.81408 | 9.81408 | 7.11e-16 | -0.14310 | 0.14717 | 0.00408 | -0.00396 | 1.15e-4 |
| 0.540 | 9.80542 | 9.80542 | 4.17e-14 | -0.15110 | 0.14652 | -0.00458 | 0.00179 | -2.79e-3 |

Interpretation:

- The current separated effective-stress plus pore-pressure feedback form is numerically identical to the direct `sigma' - pw I` total-stress form in this test window, because bottom fluid and mDBC boundary `Rhop` are both exactly 2100 kg/m3.
- Therefore the mid-window rebound is not caused by an algebraic mismatch between the split u-pw terms and a direct total-stress term.
- However, an exact theoretical self-weight total-stress line does not discretely balance gravity at the bottom mDBC support: `exact_totalstress + gravity` is about `-0.135` to `-0.153 m/s2`.
- The saved actual total-stress field contains a compensating positive offset of about `0.130` to `0.153 m/s2`. The tiny observed acceleration is the remainder after this compensation, artificial viscosity, and gravity nearly cancel.
- The rebound around Tv 0.52 corresponds to a small sign/magnitude change of `actual total + gravity` and artificial viscosity, not to a jump in pore pressure, effective stress, or CPU/GPU precision.

Updated diagnosis: the issue is best described as a discrete bottom-support static-balance residual. The mDBC-supported self-weight state is held by a delicate compensation between the actual total-stress field and the SPH bottom-boundary force operator. The next useful test should isolate that support residual directly, for example by running a short window with mDBC corrector off/on from the same restart, or by testing a boundary-force variant where the exact self-weight total stress is assigned to boundary support particles for one diagnostic window. Any such solver-side diagnostic should be temporary and removed after the evidence is collected.

## mDBC corrector on/off short-window test

A short GPU window was run from the same Scenario2 `Part_0100` restart with only the mDBC corrector disabled:

- Config: `tests/configs/CaseSWSc2_Tv050_054_mdbcc0_Def.xml`
- Launcher: `tests/xCaseSWScenario2_restart_p0100_D_ratecomp_Tv050_054_mdbcc0_win64_GPU.bat`
- Output: `tests/outputs/CaseSWSc2_Tv050_054_mdbcc0_out`
- Offline momentum: `tests/figures/CaseSWSc2_Tv050_054_mdbcc0_momentum_offline`
- Offline mDBC split: `tests/figures/CaseSWSc2_Tv050_054_mdbcc0_mdbc_split`
- Comparison: `tests/figures/self_weight_scenario2_mdbccorrector_Tv050_054_compare`

The first attempt with the long case name failed in GenCase while saving VTK shape files because the path was too long. The failed output directory was removed and the internal case name was shortened to `CaseSWSc2_Tv050_054_mdbcc0`.

Run confirmation:

- `mDBC-Corrector=False`
- `PoreShepardRegularization="Disabled"`
- `SlipMode="DBC vel=0"`
- `CteB=384615.4`
- `Cs0=35.80574408560461`
- `DTs adjusted to DtMin=0`
- `Excluded particles=0`

Key comparison against the baseline `mDBC-Corrector=True` case:

| Case | bottom vz range m/s | fd dvz/dt range m/s2 | reconstructed accel range m/s2 | actual total+gravity range m/s2 | bottom pw range kPa |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline corrector on | 1.559e-5 | 1.047e-3 | 3.514e-3 | 8.983e-3 | 0.2485 |
| corrector off | 1.620e-5 | 1.762e-3 | 8.363e-3 | 1.141e-2 | 0.2729 |

Selected values:

| Tv | case | bottom vz m/s | reconstructed accel m/s2 | actual total+gravity m/s2 | artificial viscosity m/s2 | bottom pw kPa |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 0.501 | corrector on | -1.611e-5 | 2.11e-5 | -4.87e-3 | 4.89e-3 | 12.343 |
| 0.501 | corrector off | -1.170e-5 | -5.80e-3 | -6.19e-3 | 3.86e-4 | 12.371 |
| 0.520 | corrector on | -2.474e-6 | 4.59e-4 | 3.38e-3 | -2.92e-3 | 12.200 |
| 0.520 | corrector off | -2.473e-6 | 5.96e-4 | 3.53e-3 | -2.94e-3 | 12.199 |
| 0.523 | corrector on | -8.893e-7 | 1.15e-4 | 4.08e-3 | -3.96e-3 | 12.181 |
| 0.523 | corrector off | -1.122e-7 | -3.48e-6 | 4.81e-3 | -4.81e-3 | 12.180 |
| 0.540 | corrector on | -7.135e-6 | -2.79e-3 | -4.58e-3 | 1.79e-3 | 12.102 |
| 0.540 | corrector off | -8.073e-6 | 1.10e-3 | -1.57e-3 | 2.67e-3 | 12.098 |

Interpretation:

- Disabling the mDBC corrector does not remove the mid-window bottom-row rebound.
- It introduces a strong immediate difference at Tv about 0.501, where bottom pore pressure and vertical velocity deviate more than the baseline.
- The residual acceleration range is larger with corrector off, so the corrector is stabilizing this diagnostic window rather than causing the late-time deviation.
- The corrector affects the phase and magnitude of the small residual, but the underlying issue remains the same delicate discrete bottom-support static balance.

Updated conclusion: keep the mDBC corrector enabled for this case. The next diagnostic should not be "turn off corrector" as a fix. It should target the bottom boundary force operator itself: compare the contribution of boundary-neighbor volume/weighting against a manufactured exact self-weight balance, or test a temporary boundary-support force variant in which boundary-particle total stress is assigned from the exact self-weight line before the force loop to see whether the residual collapses.

## Boundary-position interpretation for manufactured self-weight balance

The offline momentum diagnostic was extended with two manufactured total-stress variants:

- `exact`: evaluate the theoretical self-weight total stress at the saved particle positions, including boundary particle positions below the soil.
- `interfacebound`: for bottom boundary neighbors with `z<0`, evaluate the theoretical boundary total stress at the bottom interface `z=0`.

The `interfacebound` interpretation is much worse:

| Tv | exact total+gravity m/s2 | interfacebound total+gravity m/s2 |
| ---: | ---: | ---: |
| 0.500 | -0.1348 | -3.2224 |
| 0.520 | -0.1372 | -3.2252 |
| 0.523 | -0.1431 | -3.2311 |
| 0.540 | -0.1511 | -3.2392 |

Therefore, for this current mDBC output and force reconstruction, treating boundary support stress as living at the boundary particle location is much closer to the actual discrete force balance than treating it as an interface value.

The exact self-weight residual is still dominated by a very large fluid/boundary cancellation. At Tv=0.520:

- exact total-stress acceleration from fluid neighbors: `-719.690 m/s2`
- exact total-stress acceleration from boundary neighbors: `+729.363 m/s2`
- exact total-stress total: `+9.673 m/s2`
- gravity: `-9.810 m/s2`
- exact balance residual: `-0.137 m/s2`

The actual saved total-stress field at the same Tv gives:

- actual total-stress acceleration from fluid neighbors: `-718.342 m/s2`
- actual total-stress acceleration from boundary neighbors: `+728.156 m/s2`
- actual total-stress total: `+9.813 m/s2`
- actual total+gravity residual: `+0.00338 m/s2`

Interpretation:

- The theoretical self-weight total-stress line does not exactly satisfy the current discrete bottom-support force operator.
- The evolved actual stress field carries a compensating offset relative to the exact line. This offset is not a small field error; it is the mechanism that nearly balances the discrete bottom support.
- The mid-window rebound is the small remainder left when this compensating total-stress offset and artificial viscosity vary slightly in time.

Updated diagnosis: the strongest current evidence points to a discrete bottom-support equilibrium defect of the mDBC force operator for the 1D self-weight problem. The next code-side diagnostic, if needed, should be a temporary manufactured-equilibrium test in the force loop: replace or override only the bottom-boundary support stress/pore contribution with a manufactured value that makes `actual total+gravity` exactly zero, then verify whether bottom `vz` and late EPWP residual collapse in the Tv 0.50-0.54 window. This should be kept as a diagnostic patch only and removed after evaluation.

## Temporary bottom-force balance test

A temporary GPU-only diagnostic patch was applied in `JSphGpu_ker.cu` for the
Tv=0.50-0.54 restart window. It forced the bottom 10 soil rows of this 1D
self-weight case to have zero z acceleration after gravity is applied. The
patch was only used to test whether the late pore-pressure deviation is caused
directly by the small bottom-row force residual.

Run confirmation for `CaseSWSc2_Tv050_054_tmpbal`:

- `mDBC-Corrector=True`
- `PoreShepardRegularization="Disabled"`
- `SlipMode="DBC vel=0"`
- `CteB=384615.4`
- `Cs0=35.80574408560461`
- `DTs adjusted to DtMin=0`
- `Excluded particles=0`

Key result:

| Case | bottom vz range m/s | max abs fd dvz/dt m/s2 | bottom error at Tv=0.52 kPa | bottom error at Tv=0.54 kPa |
| --- | ---: | ---: | ---: | ---: |
| baseline | 1.559e-5 | 6.824e-4 | 0.0730 | 0.0915 |
| forced bottom balance | 1.819e-12 | 4.992e-10 | 0.1356 | 0.1744 |

Interpretation:

- The temporary patch successfully suppressed the bottom-row velocity rebound:
  bottom `vz` stayed essentially constant and `dvz/dt` collapsed to numerical
  noise.
- However, the pore-pressure result became worse. The bottom EPWP stayed higher
  than theory and the error grew from about `0.1016 kPa` at Tv=0.50 to
  `0.1744 kPa` at Tv=0.54, while the baseline error was only `0.0915 kPa` at
  Tv=0.54.
- Therefore, the bottom force residual is not a standalone fix target. The
  velocity/compression response driven by that small residual is part of the
  coupled pore-pressure evolution, and artificially removing it slows local
  dissipation in this window.

Diagnostic outputs:

- `tests/figures/self_weight_scenario2_tmp_bottom_balance_Tv050_054_compare/tmp_bottom_balance_Tv050_054_compare.png`
- `tests/figures/self_weight_scenario2_tmp_bottom_balance_Tv050_054_compare/tmp_bottom_balance_Tv050_054_key_points.csv`
- `tests/figures/self_weight_scenario2_tmp_bottom_balance_Tv050_054_compare/tmp_bottom_balance_Tv050_054_window_summary.csv`
- `tests/figures/self_weight_scenario2_tmp_bottom_balance_Tv050_054_compare/tmp_bottom_balance_Tv050_054_timeseries_wide.csv`

Cleanup:

- The temporary source patch was removed from `JSphGpu_ker.cu`.
- `rg` confirms no remaining `MYF_TMP_SW_BOTTOM_BALANCE` or related temporary
  diagnostic markers.
- GPU Release was rebuilt successfully after cleanup, restoring
  `bin/windows/DualSPHysics5.2_GEO_win64.exe` to the normal source path.

Updated next step:

Do not pursue "zero bottom acceleration" as a correction. The next useful
diagnostic should separate the pore-pressure rate terms in the same window:
compare the compression/divergence contribution and Darcy/laplacian contribution
near the bottom against the local velocity/stress changes. The current result
suggests the late deviation is more likely in the coupled pore-rate response
near the mDBC support than in a simple residual force imbalance alone.

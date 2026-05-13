# T5 DP Feedback-Off Triaxial Baseline Report

## Purpose

T5 creates a reduced Drucker-Prager feedback-off platen triaxial baseline. It
uses the explicit T4s platen workflow, keeps lateral selected
`FlexibleConfiningStress`, and replaces the linear-elastic skeleton with
`SoilConstitutiveModel=1`.

This is not a full paper reproduction, not an MCC validation, and not a
full-feedback u-pw validation. It is a CPU-only reduced DP smoke/baseline with
specimen-only stress and reaction proxies.

## Experiment Directory

`examples/u-pw/04_Undrained_Triaxial/experiments/T5_DPFeedbackOffBaseline/`

Main files:

- `CaseT5_DPHighStrength_PlatenLateralConfinement_Def.xml`
- `CaseT5_DPMildYield_PlatenLateralConfinement_Def.xml`
- `make_t5_cases.py`
- `analyze_t5_dp_feedback_off_triaxial.py`
- `t5_case_summary.csv`
- `t5_dp_plasticity_metrics.csv`
- `t5_specimen_stress_path_proxy.csv`
- `t5_pore_pressure_strain_metrics.csv`
- `t5_measurement_region_metrics.csv`
- `t5_confinement_diagnostics.csv`
- `t5_reaction_proxy_metrics.csv`
- `figures/`

## Setup

Both cases use:

- `SoilConstitutiveModel=1`;
- `PorePressureFeedback=0`;
- `HydraulicElevationSource=0`;
- `PorePressureBoundaryOperator=0`;
- `FlexibleConfiningStress=1`;
- `ConfiningStressUseFiSelector=1`;
- `ConfiningStressUseLateralSelector=1`;
- `ConfiningStressP0=50 Pa`;
- top moving platen `mkbound=1`, prescribed `v_z=-0.005 m/s`;
- bottom fixed platen `mkbound=2`;
- specimen `mkfluid=0`;
- `CapConfiningStress=0`;
- CPU Release only.

The DP cases are:

| Case | `phi` | `coh` | `dlt` | Purpose |
| --- | ---: | ---: | ---: | --- |
| DP high strength | `33 deg` | `10000 Pa` | `0 deg` | stable DP plumbing check |
| DP mild yield | `30 deg` | `50 Pa` | `0 deg` | short yield-intended diagnostic |

## CPU Run Results

Both CPU Release cases completed:

| Case | Code | Excluded | DtMin adjustments | NaN/Inf scan |
| --- | ---: | ---: | ---: | --- |
| DP high strength | `0` | `0` | `0` | clear |
| DP mild yield | `0` | `0` | `0` | clear |

No GPU run was attempted.

## Platen And Confinement Checks

The explicit platen route remains correct:

| Case | Final top displacement | Final top `v_z` mean | Bottom displacement |
| --- | ---: | ---: | ---: |
| DP high strength | `-3.00e-5 m` | `-3.39e-3 m/s` | `0` |
| DP mild yield | `-3.00e-5 m` | `-3.40e-3 m/s` | `0` |

The final displacement matches the prescribed `-0.005 m/s` motion over the
`0.006 s` window. The bottom platen remains fixed.

Lateral confinement remains stable:

- active lateral targets: `112`;
- legacy material candidates: `407`;
- total absolute confinement force: about `0.4426 N`;
- max confinement acceleration: about `1.93 m/s2`;
- lateral inward radial acceleration mean: about `1.87 m/s2`;
- cap axial leakage diagnostic: `0`.

## Plasticity

The high-strength DP case does not yield:

- final `Kplastic` max: `0`;
- final `Kplastic` mean: `0`;
- final nonzero `Kplastic` count: `0`.

The mild-yield case activates the DP path without destabilizing the run:

- final `Kplastic` max: `4.38e-4`;
- final `Kplastic` mean: `9.05e-5`;
- final nonzero `Kplastic` count: `341 / 407`.

Center-region plasticity is smaller but nonzero:

- core-small final `Kplastic` max: `5.63e-5`;
- core-medium final `Kplastic` max: `1.20e-4`;
- specimen-minus-edge final `Kplastic` max: `2.65e-4`.

This is enough to confirm that the DP skeleton and `Kplastic` output are
active in the explicit-platen workflow.

## Stress And Reaction Proxies

T5 continues to use the T4s specimen-stress proxy:

```text
sigma_a_proxy = -mean(Sigma_zz) over specimen particles
Fz_proxy = sigma_a_proxy * pi * R^2
```

Final specimen-wide values:

| Case | `p'` proxy | `q` proxy | `sigma_a_proxy` | `Fz_proxy` |
| --- | ---: | ---: | ---: | ---: |
| DP high strength | `145.66 Pa` | `332.47 Pa` | `367.31 Pa` | `1.0385 N` |
| DP mild yield | `86.58 Pa` | `126.76 Pa` | `171.09 Pa` | `0.4837 N` |

The high-strength case is effectively identical to the T4s elastic lateral
baseline because no plastic correction occurs. The mild-yield case reduces
`q`, axial stress proxy, and mean pore-pressure response, consistent with a
lower-strength elastoplastic skeleton limiting the stress state.

## Pore Pressure

With feedback disabled, the PR pressure response remains bounded:

| Case | Final specimen mean `PorePress` | Final `PorePressRate` maxAbs | Final `DivVel` maxAbs |
| --- | ---: | ---: | ---: |
| DP high strength | `4.54e4 Pa` | `2.04e7 Pa/s` | `3.07e-2 1/s` |
| DP mild yield | `1.49e4 Pa` | `1.03e7 Pa/s` | `1.55e-2 1/s` |

The mild-yield case has lower final pressure-rate and divergence magnitudes
than the high-strength/elastic path over this short window.

## Comparison With T4s Elastic Baseline

The T5 high-strength DP case reproduces the T4s lateral elastic metrics because
the yield surface is not reached. This is useful as a regression check: simply
turning on `SoilConstitutiveModel=1` does not disturb the platen workflow when
the strength is high.

The mild-yield case differs materially:

- `Kplastic` becomes nonzero in most specimen particles;
- final `q` proxy drops from about `332 Pa` to `127 Pa`;
- final `Fz_proxy` drops from about `1.04 N` to `0.48 N`;
- final specimen mean `PorePress` drops from about `4.54e4 Pa` to `1.49e4 Pa`;
- velocity and pressure-rate diagnostics remain bounded.

## Limitations

- `PorePressureFeedback=0`; this is not a full coupled feedback validation.
- `Fz_proxy` is not true platen reaction.
- The run is short and reduced resolution.
- No MCC model is implemented or tested.
- No GPU simulation was run.

## Required Answers

1. T5 CPU cases: both `code=0`, `excluded=0`.
2. DP settings: `SoilConstitutiveModel=1`; high-strength `phi=33 deg`,
   `coh=10000 Pa`, `dlt=0`; mild-yield `phi=30 deg`, `coh=50 Pa`, `dlt=0`.
3. Top/bottom platens: top prescribed displacement correct, bottom fixed.
4. Lateral confinement: stable with `112` active targets and cap leakage `0`.
5. Pore pressure: bounded with feedback off.
6. `Kplastic`: high-strength no yield; mild-yield final max `4.38e-4`,
   nonzero count `341/407`.
7. `p'-q` proxy: available and specimen-only.
8. Difference from T4s: high-strength matches elastic; mild-yield activates
   plasticity and lowers `q`, `Fz_proxy`, and pore-pressure response.
9. True reaction patch: still not immediately required for this reduced DP
   smoke, but required before strict validation.
10. Next step: T5b DP refinement or T4t true reaction diagnostics can proceed
    depending on whether the next priority is constitutive behavior or
    measurement fidelity.
11. MCC, full feedback, and GPU remain deferred.

# 04 Undrained Triaxial

This directory tracks the u-pw PR reproduction path for the paper's undrained
triaxial tests.

The current runnable case is a reduced CPU smoke test, not a strict triaxial
reproduction. It uses the current Drucker-Prager soil path, a small 2D column,
and native DualSPHysics `accinput` on the top `mkfluid=1` material layer to
apply a tiny axial loading increment.

## Files

- `CaseUndrainedTriaxial_PR_Smoke_Def.xml`  
  Reduced CPU smoke case with u-pw PR enabled, undrained top drainage delayed,
  pressure feedback set to excess/difference-gradient mode, Shepard smoothing,
  and Supporting Information style damping.
- `xCaseUndrainedTriaxial_PR_Smoke_win64_CPU_debug.bat`  
  Debug CPU launcher for the smoke case.
- `TriaxialAxialAcc_m1.csv`  
  Native AccInput history for the top material layer. The final axial
  acceleration is only `-0.047619 m/s2`.
- `analyze_triaxial_smoke.py`  
  Lightweight postprocessing scaffold for framewise approximate `p'`, `q`,
  axial-strain proxy, velocity, and pore-pressure summaries from `PartCsv`
  outputs.
- `CaseUndrainedTriaxial_PR_TODO_Def.xml`  
  Historical TODO scaffold retained as a reminder that strict reproduction is
  not complete.

## Smoke Status

Latest short smoke:

| Item | Result |
| --- | --- |
| GenCase | code=0 |
| DualSPHysics CPU Release | code=0 |
| TimeMax | 0.001 s |
| Excluded particles | 0 |
| Particle rows in CSV | 1040 |
| AccInput target layer | `mkfluid=1`, 10 particles |
| Max velocity | `1.86e-5 m/s` |
| Mean pore pressure | `4719.96 Pa` |
| Mean excess pore pressure | `3.61 Pa` |
| Mean `p'` / `q` proxies | `9.05e-3 Pa` / `8.36e-3 Pa` |
| NaN/Inf scan | not detected |

The smoke test confirms code execution, pore-pressure fields, feedback
diagnostics, damping, and native AccInput loading are wired correctly. The pore
pressure response is small and positive under the tiny compressive increment.

## Strict Reproduction Reclassification

This reduced DP/u-pw AccInput smoke must not be counted as strict triaxial
reproduction complete. It lacks controlled axial strain or stress loading,
proper confinement / lateral stress boundary conditions, validated `p'`-`q`
stress-path output, and the paper's exact constitutive model choice. If the
paper triaxial test requires Modified Cam Clay, the current Drucker-Prager
smoke is only a qualitative plumbing check.

## Strict Reproduction Gaps

- No calibrated Modified Cam Clay model is used. The current DP model can only
  support qualitative smoke tests unless calibrated against the paper setup.
- The case does not yet implement true triaxial stress control.
- Lateral confinement is represented only by fixed side boundaries, not by a
  prescribed confining stress boundary.
- Stress-path output is postprocessed approximately from existing stress
  components; a strict `p'`-`q` workflow still needs validation.
- This case is not a long CPU parameter-tuning target. Longer and higher
  resolution reproduction should wait until the GPU path is available.

## T1 Undrained Triaxial Baseline

T1 is retained under:

`experiments/T1_UndrainedTriaxialBaseline/`

It is a reduced CPU Release baseline, not a full paper reproduction. T1 uses
`SoilConstitutiveModel=0`, `PorePressureBoundaryOperator=0`, and
`HydraulicElevationSource=0`. Native DualSPHysics `accinput` applies a small
downward acceleration to the top `mkfluid=1` material layer. No Cryer
deprecated boundary modes are used.

CPU Release smoke result:

| Item | Result |
| --- | --- |
| GenCase | code=0 |
| DualSPHysics CPU Release | code=0 |
| PartVTK | code=0 |
| Excluded particles | 0 |
| Steps | 6 |
| Final upper-middle mean excess pore pressure | `42.12 Pa` |
| Final max velocity | `4.42e-04 m/s` |
| Final `Kplastic` max | `0` |
| NaN/Inf scan | not detected |

GPU was not run because `HydraulicElevationSource=0` is CPU-only in this
branch. T1 is sufficient to move to T2 stress-path/loading refinement, but not
to paper-level triaxial comparison.

## T2 Zhao Flexible Confinement Audit

T2 completes the literature/source audit needed before replacing the reduced
fixed-side confinement smoke with a Zhao-style flexible lateral confinement
route.

New notes are in:

- `src/papers/u-p/zhao_flexible_confined_boundary_conditions_sph.md`
- `src/papers/u-p/zhao_flexible_confined_boundary_conditions_review.md`
- `src/papers/u-p/t2_zhao_confinement_source_audit.md`
- `src/papers/u-p/t2_zhao_confinement_requirements.md`
- `src/papers/u-p/t2_kernel_completeness_fi_diagnostic_design.md`
- `src/papers/u-p/t2_triaxial_lateral_selection_design.md`
- `src/papers/u-p/t2_initial_confinement_strategy.md`
- `src/papers/u-p/t3_flexible_confinement_implementation_plan.md`

Key decision:

- current CPU `FlexibleConfiningStress` is conceptually close to Zhao's
  isotropic confining-pressure pair term;
- it is not yet strict triaxial lateral confinement;
- it lacks the Zhao kernel-completeness index `f_i`, near-boundary selection,
  lateral-cylinder selection, cap exclusion, and initial hydrostatic stress
  strategy;
- MCC remains deferred until confinement and stress-path measurement are
  stable.

## T3 Flexible Confinement Diagnostics

T3 is implemented under:

`experiments/T3_FlexibleConfinementDiagnostics/`

It adds CPU-only Zhao-style diagnostics and opt-in selectors for
`FlexibleConfiningStress`:

- kernel-completeness diagnostic `f_i = sum_j (m_j/rho_j) W_ij`;
- cylinder lateral/top/bottom/edge/interior classification;
- optional `f_i <= 0.70` selector;
- optional lateral-only selector;
- confinement force diagnostics for net force, COM acceleration, radial
  tendency, cap leakage, and symmetry residual.

The default behavior is unchanged when the selectors are off. GPU remains
deferred because `FlexibleConfiningStress=1` is still CPU-only.

CPU Release T3 smokes:

| Case | Result |
| --- | --- |
| confinement-only legacy | `code=0`, `excluded=0`, `Kplastic=0` |
| confinement-only selected | `code=0`, `excluded=0`, `Kplastic=0` |
| axial + selected confinement | `code=0`, `excluded=0`, `Kplastic=0` |

The reduced cylinder has `407` material particles. The first diagnostic frame
reports `f_i` min/mean/max of `0.407175 / 0.745128 / 1.00132`, with
`208` particles below the `0.70` threshold. Cylinder classification reports
`196` lateral particles, `112` edge-ring particles, `18` top-cap particles,
`18` bottom-cap particles, and `63` interior particles.

The combined `f_i` + lateral selector reduces the active confinement targets
from `407` to `112` and reduces measured active cap axial leakage from about
`0.93 m/s2` to `0`. Lateral inward radial acceleration remains coherent
(`~1.87 m/s2`) and net-force symmetry residual remains order `1e-8`.

This is still a smoke/diagnostic stage, not strict triaxial validation. The
large short-time pore-pressure response indicates that T4 should refine
measurement, loading duration, stress-path postprocessing, and possibly
Zhao-style renormalized gradients before MCC or full paper comparison.

## T4 Stress-Path Postprocessing

T4 is retained under:

`experiments/T4_StressPathPostprocessing/`

It is a slightly longer CPU selected-confinement smoke derived from the T3
axial + selected confinement case. It keeps the same reduced linear-elastic
setup:

- `SoilConstitutiveModel=0`;
- `PorePressureBoundaryOperator=0`;
- `HydraulicElevationSource=0`;
- `FlexibleConfiningStress=1`;
- `ConfiningStressUseFiSelector=1`;
- `ConfiningStressUseLateralSelector=1`;
- no Cryer curved drained boundary modes;
- CPU Release only.

The retained stable window is intentionally short (`TimeMax=0.0015 s`). An
exploratory `0.004 s` window produced exclusions and is not treated as the T4
baseline.

CPU Release T4 result:

| Item | Result |
| --- | --- |
| GenCase | `code=0` |
| DualSPHysics CPU Release | `code=0` |
| PartVTK | `code=0` |
| Excluded particles | `0` |
| Steps | `14` |
| Final `Kplastic` max | `0` |
| Final top-strain proxy | `0.03326` |
| Final full-specimen mean pore pressure | `-3.82e6 Pa` |

The postprocessor now writes measurement-region sensitivity and `p'-q` proxy
curves for center-core and Zhao-style measurement regions. The stress path is
not strict yet: `Sigma` is treated as a skeleton/effective stress proxy, and
the output does not yet explicitly write total/effective stress conventions,
original positions, material `mk`, or per-particle confinement class.

The confinement selector remains healthy: selected targets stay at `112`,
active cap leakage is `0`, lateral inward acceleration is about `1.87 m/s2`,
and net-force symmetry residual remains small. The pore-pressure response is
still too oscillatory for validation, so the recommended next step is T4b:
Zhao-style renormalized-gradient confinement and loading/stability refinement
before a T5 DP baseline or any T6 MCC work.

## T4b Renormalized Confinement

T4b is retained under:

`experiments/T4b_RenormalizedConfinement/`

It adds the opt-in parameter:

`ConfiningStressGradientMode=1`

which applies a local first-order renormalized/corrected kernel gradient only
to the CPU `FlexibleConfiningStress` pair term. The default remains
`ConfiningStressGradientMode=0`, so old raw-gradient behavior is unchanged.

CPU Release T4b smokes:

| Case | Result | Key observation |
| --- | --- | --- |
| renormalized, T4 loading | `code=0`, `excluded=0`, `Kplastic=0` | gradient correction succeeded with `112/0` corrected/fallback targets, but pressure-rate artifacts worsened. |
| renormalized, gentle loading | `code=0`, `excluded=0`, `Kplastic=0` | gentler loading gave only a small improvement over the renormalized T4-loading case. |

The selector remains correct: cap leakage is still `0` and active targets stay
at `112`. However, the renormalized gradient roughly doubles the lateral
inward acceleration (`~1.87 -> ~3.76 m/s2`) on this reduced coarse cylinder and
does not remove pressure reversal. T4b therefore does not justify moving to T5
DP or T6 MCC yet. The next step should stabilize confinement/loading and then
add minimal output fields for strict stress-path validation.

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

## T4c Loading Stabilization

T4c is retained under:

`experiments/T4c_LoadingStabilization/`

It tests XML-level staging before any new source patch:

- `ConfiningStressRampEnd=0.001`;
- axial AccInput delayed to `0.0015 s`;
- retained short gate `TimeMax=0.0018 s`;
- selected `f_i` + lateral confinement remains active;
- CPU Release only.

Retained CPU Release T4c smokes:

| Case | Result | Key observation |
| --- | --- | --- |
| raw staged | `code=0`, `excluded=0`, `Kplastic=0` | cap leakage remains `0`, but pressure reversal still appears. |
| renormalized staged | `code=0`, `excluded=0`, `Kplastic=0` | still more violent than raw because confinement acceleration is amplified. |
| raw staged gentle | `code=0`, `excluded=0`, `Kplastic=0` | nearly identical to raw staged because reversal begins before axial loading matters. |

The important T4c result is that pressure reversal appears around `0.0014 s`,
before the delayed axial loading starts at `0.0015 s`. The blocker is therefore
not primarily AccInput onset. It is the selected-confinement equilibration and
u-pw feedback stage. T4c does not justify moving to T5 DP or T6 MCC. The next
physics task should stabilize confinement-stage dynamics before strict output
enhancement or stress-path validation.

## T4d Confinement Equilibration

T4d is retained under:

`experiments/T4d_ConfinementEquilibration/`

It removes axial AccInput entirely and isolates selected flexible confinement:

- raw-gradient selected confinement, feedback on;
- raw-gradient selected confinement, feedback off;
- raw-gradient selected confinement with `p0=12.5 Pa`;
- raw-gradient selected confinement with longer ramp and stronger damping.

All CPU Release confinement-only cases complete with `code=0`, `excluded=0`,
and `Kplastic=0`.

The key result is that pressure reversal still occurs in the target-p0
confinement-only feedback-on case at about `0.001404 s`. The same selected
confinement with `PorePressureFeedback=0` removes reversal over the retained
window, removes DtMin adjustments, and reduces max `PorePressRate` from
`3.12e12 Pa/s` to `2.11e7 Pa/s`. Lower p0 and longer ramp/damping only delay or
reduce the failure; they do not stabilize the coupled feedback-on route.

Cap leakage remains `0`, and lateral confinement remains geometrically
coherent. The current blocker is the confinement-stage u-pw feedback loop, not
axial loading or lateral/cap selection. T5 DP and T6 MCC remain deferred. The
next recommended step is T4e staged confinement equilibration with feedback
gating/delay before any source-level magnitude normalization or axial loading
reintroduction.

## T4e Feedback-Gated Confinement

T4e is retained under:

`experiments/T4e_FeedbackGatedConfinement/`

It adds a minimal CPU-only pore-pressure feedback gate:

- `PorePressureFeedbackStartTime`;
- `PorePressureFeedbackRampEndTime`;
- `PorePressureFeedbackScale`.

The defaults preserve the previous feedback behavior. Non-default feedback
gating is a CPU diagnostic path; GPU hard-errors instead of silently ignoring
the timing controls.

T4e confirms that selected confinement can equilibrate when feedback is kept
off over a longer confinement-only window:

| Case | Result | Key observation |
| --- | --- | --- |
| feedback off extended | `code=0`, `excluded=0`, `Kplastic=0` | no reversal, no DtMin adjustment, max `PorePressRate=2.11e7 Pa/s` |
| delayed abrupt full feedback | `code=0`, `excluded=391` | reversal after feedback activation, max `PorePressRate=1.55e13 Pa/s` |
| delayed short-ramp full feedback | `code=0`, `excluded=365` | ramp delays but does not remove instability |
| delayed long-ramp full feedback | `code=0`, `excluded=164` | still reverses after feedback restoration |
| delayed long-ramp feedback scale `0.25` | `code=0`, `excluded=0` | no DtMin burst, but still reverses at final frame |

No axial-loading variant was run because no full-feedback confinement-only case
passed the stability gate. The current blocker is the pore-pressure feedback
acceleration/operator coupling during selected-confinement equilibration, not
the lateral selector geometry. T5 DP and T6 MCC remain deferred.

## T4f Feedback Stabilization

T4f is retained under:

`experiments/T4f_FeedbackStabilization/`

It adds CPU-only opt-in diagnostics and stabilization for the
`PorePressureFeedback` acceleration:

- `SavePorePressureFeedbackDiagnostics`;
- `PorePressureFeedbackRelaxation`;
- `PorePressureFeedbackLimiterMode`;
- `PorePressureFeedbackMaxAccel`;
- `PorePressureFeedbackMaxAccelRatio`.

Defaults preserve the previous behavior. GPU builds pass, but non-default
feedback timing/stabilization remains GPU-unsupported and hard-errors.

The T4f confinement-only gate confirms the operator-level blocker. Full
feedback without stabilization reproduces the T4e failure
(`excluded=164`, `256` DtMin adjustments, max `PorePressRate=1.30e13 Pa/s`).
Relaxation alone is insufficient. Acceleration caps remove exclusions and
DtMin bursts. The best confinement-only diagnostic case, relaxation `0.2` plus
cap `50 m/s2` / ratio `25`, runs with `code=0`, `excluded=0`, `Kplastic=0`,
no DtMin adjustments, and no center-core pressure reversal, reducing max
`PorePressRate` to about `1.03e9 Pa/s`.

This is still not validation-ready. Local negative pressures remain, the
pressure-rate level is far above the feedback-off reference, and a gentle axial
loading smoke after the stabilized confinement stage reintroduces center-core
reversal. T5 DP and T6 MCC remain deferred. The next step should audit the
feedback formulation itself before further triaxial validation.

## T4g Feedback Formulation Audit

T4g is retained under:

`experiments/T4g_FeedbackFormulationAudit/`

It adds CPU-only opt-in class filtering for the pore-pressure feedback
acceleration:

- `PorePressureFeedbackUseClassFilter`;
- `PorePressureFeedbackExcludeCaps`;
- `PorePressureFeedbackExcludeEdges`;
- `PorePressureFeedbackExcludeConfinementTargets`;
- `PorePressureFeedbackInteriorOnly`.

The defaults preserve the previous feedback behavior. Non-default class
filtering is treated as a CPU diagnostic path; GPU hard-errors rather than
silently ignoring the filter.

The formulation audit finds no obvious direct double counting: the material
stress tensor is treated as a skeleton/effective-stress quantity, and feedback
operator `1` supplies the intended `-grad(p_w)/rho` coupling. Static
manufactured tests show that operator `1` is the better physical candidate:
uniform pressure gives near-zero acceleration, and a linear pressure field
produces the expected down-gradient direction. Operator `0` creates a nonzero
free-surface response even under uniform pressure, so it is not the preferred
internal pore-pressure feedback operator.

CPU Release confinement-only cases remain diagnostic, not validation-ready:

| Case | Result | Key observation |
| --- | --- | --- |
| feedback off | `code=0`, `excluded=0`, `DtMin=0` | stable reference, max `PorePressRate=2.11e7 Pa/s` |
| operator 1 unfiltered | `code=0`, `excluded=164`, `DtMin=256` | reproduces T4e/T4f full-feedback instability |
| operator 0 unfiltered | `code=0`, `excluded=0`, `DtMin=43` | avoids exclusion but still reverses |
| operator 1 interior-only | `code=0`, `excluded=0`, `DtMin=0` | removes the burst but still reverses and reaches `4.79e10 Pa/s` |
| operator 0 interior-only | `code=0`, `excluded=0`, `DtMin=0` | also reverses, with poorer physical consistency |
| operator 1 total-pressure interior-only | `code=0`, `excluded=0`, `DtMin=0` | identical to excess mode for `HydraulicElevationSource=0` |

Class filtering proves that cap/edge/lateral confinement feedback is a major
amplifier: it removes exclusions and DtMin bursts for operator `1`. It does not
pass the confinement-only gate because pressure reversal and large
`PorePressRate` excursions remain. Axial loading is therefore still not
restored, and T5 DP / T6 MCC remain deferred. The next step should be a narrow
T4h feedback formulation patch, not another loading schedule sweep.

## T4h Corrected Feedback Gradient

T4h is retained under:

`experiments/T4h_CorrectedFeedback/`

It adds a CPU-only experimental feedback operator:

```xml
<parameter key="PorePressureFeedbackOperator" value="2" />
```

Operator `2` reconstructs a local LSQ pressure gradient and applies
`a_fb=-grad(p_w)/rho` to the mechanical acceleration. The PR pore-pressure
update is unchanged. Defaults remain unchanged; operator `2` is opt-in and GPU
hard-errors.

The manufactured feedback gate improved exactly where intended: uniform
pressure gives zero acceleration, and a linear `p=1000 x` field gives machine
precision gradient error for operator `2` versus finite boundary-cloud error
for operator `1`.

The dynamic selected-confinement gate did not pass:

| Case | Result |
| --- | --- |
| operator `1` interior baseline | `code=0`, `excluded=0`, `DtMin=0`, max `PorePressRate=4.79e10 Pa/s`, reversal at `0.003821 s` |
| operator `2` LSQ interior | `code=0`, `excluded=0`, `DtMin=0`, max `PorePressRate=5.04e10 Pa/s`, reversal at `0.003821 s` |
| operator `2` LSQ with relax+cap | `code=0`, `excluded=0`, `DtMin=0`, max `PorePressRate=4.65e8 Pa/s`, reversal at `0.004022 s` |

LSQ conditioning is healthy (`407` solves, `0` fallbacks, condition proxy about
`3-4`), so the failure is not an LSQ matrix problem. The explicit feedback loop
itself remains the blocker. Axial loading was not restored, and DP/MCC remain
deferred.

## T4i-B Feedback Fidelity Audit

T4i-B is a documentation/source-audit stage, not a simulation stage. It is
retained in:

- `src/papers/u-p/t4i_original_upw_feedback_operator_audit.md`;
- `src/papers/u-p/t4i_current_feedback_source_mapping.md`;
- `src/papers/u-p/t4i_zhao_confinement_coupling_audit.md`;
- `src/papers/u-p/t4i_paper_faithful_feedback_route.md`;
- `src/papers/u-p/t4i_initial_confinement_before_feedback_plan.md`;
- `src/papers/u-p/t4j_feedback_fidelity_implementation_plan.md`.

The audit changes the direction of the triaxial feedback work. The original
u-pw implementation notes write the pore-pressure momentum contribution as a
symmetric stress-like pair term, adjacent to effective-stress divergence:

```text
sum_j m_j ((p_i+p_j)/(rho_i rho_j)) I . grad W_ij
```

Current operator `0` is algebraically closest to this paper form, but it is a
raw-gradient separate feedback pass with no boundary pressure completion.
Operators `1` and `2` are cleaner pressure-gradient estimators, yet they are
less faithful to the paper's pairwise stress-like discretization and did not
stabilize selected confinement.

T4i-B therefore recommends T4j as a CPU-only paper-style pore-pressure momentum
coupling prototype, with controlled manufactured/closed-support gates before
returning to selected-confinement axial loading. DP, MCC, GPU parity, and
full-paper triaxial reproduction remain deferred.

## T4j Paper-Style Feedback Prototype

T4j is retained under:

`experiments/T4j_PaperStyleFeedback/`

It adds a CPU-only experimental feedback operator:

```xml
<parameter key="PorePressureFeedbackOperator" value="3" />
```

Operator `3` computes the paper-style symmetric pressure stress-pair term

```text
a_i^pw = sum_j m_j (p_i+p_j)/(rho_i rho_j) grad W_ij
```

through the existing feedback acceleration path. Defaults remain unchanged and
GPU hard-errors when operator `3` is requested.

The manufactured checks behave as expected for a stress-pair term: operators
`1/2` give zero acceleration for uniform pressure, while operators `0/3`
produce a free-surface response under uniform pressure because the material
support is truncated and no dummy/boundary pressure completion exists. This is
not a sign/unit failure; it is the central limitation of the raw paper-style
prototype.

The selected-confinement gate did not pass:

| Case | Result | Max `PorePressRate` |
| --- | --- | ---: |
| operator `1`, interior-only | `code=0`, `excluded=0`, `DtMin=0` | `4.79e10 Pa/s` |
| operator `3`, unfiltered | `code=0`, `excluded=407`, `DtMin=82` | `1.86e12 Pa/s` |
| operator `3`, interior-only | `code=0`, `excluded=55`, `DtMin=243` | `2.27e12 Pa/s` |

Because confinement-only failed, no axial-loading smoke was run. Operator `3`
is closer to the u-pw notes in algebraic form, but it is not a validated
triaxial setting. The next step should be T4k initial hydrostatic confinement
stress/equilibration, not DP/MCC.

## T4k Initial Hydrostatic Confinement

T4k is retained under:

`experiments/T4k_InitialConfinementEquilibrium/`

It adds a CPU-only initial skeleton/effective stress initialization:

```xml
<parameter key="InitialStressMode" value="1" />
<parameter key="InitialEffectiveStressIso" value="50" />
<parameter key="InitialEffectiveStressTargetMk" value="-1" />
```

The XML value is a positive compression magnitude. The CPU implementation
writes it as negative diagonal `Sigmac` because the current skeleton/effective
stress convention stores compression as negative stress. The option does not
initialize pore pressure, does not alter PR pressure update, and defaults to
off.

T4k CPU Release cases:

| Case | Result | Max `PorePressRate` | Interpretation |
| --- | --- | ---: | --- |
| initial stress only, feedback off | `code=0`, `excluded=0`, `DtMin=0`, `Kplastic=0` | `4.63e7 Pa/s` | Numerically stable, but unbalanced free-surface initial stress drives negative pore pressure. |
| initial stress + selected confinement, feedback off | `code=0`, `excluded=0`, `DtMin=0`, `Kplastic=0` | `4.48e7 Pa/s` | Selected lateral confinement stays clean, but the state is not fully hydrostatic because cap/axial support is missing. |
| initial stress + selected confinement, delayed feedback | `code=0`, `excluded=0`, `DtMin=0`, `Kplastic=0` | `1.59e12 Pa/s` | Full feedback still destabilizes the confinement-only state. |

No axial smoke was run because the full-feedback confinement-only gate did not
pass. T4k shows that initial effective stress is wired correctly, but the
reduced cylinder needs a true staged hydrostatic equilibrium route, likely
including cap/axial confinement or restart-based equilibration, before axial
loading, DP, or MCC work resumes.

## T4l Full Hydrostatic Confinement Staging

T4l is retained under:

`experiments/T4l_FullHydrostaticConfinement/`

It adds a CPU-only cap-normal hydrostatic support route:

```xml
<parameter key="CapConfiningStress" value="1" />
<parameter key="CapConfiningStressP0" value="50" />
<parameter key="CapConfiningStressTopMk" value="1" />
<parameter key="CapConfiningStressBottomMk" value="0" />
```

The cap support balances the axial component of the initial hydrostatic
effective stress. Positive `CapConfiningStressP0` is external compression; the
top cap receives acceleration along `-axis`, the bottom cap along `+axis`, and
edge-ring particles are skipped so lateral flexible confinement is not counted
twice.

T4l CPU Release results:

| Case | Result | Max `PorePressRate` | Interpretation |
| --- | --- | ---: | --- |
| lateral-only initial stress, feedback off | `code=0`, `excluded=0`, `DtMin=0`, `Kplastic=0` | `4.48e7 Pa/s` | Reproduces the T4k axial-support mismatch. |
| full cap+lateral support, feedback off | `code=0`, `excluded=0`, `DtMin=0`, `Kplastic=0` | `4.42e7 Pa/s` | Center-core pressure improves strongly, but the specimen is still not fully hydrostatic. |
| full cap+lateral support, delayed feedback | `code=0`, `excluded=0`, `DtMin=0`, `Kplastic=0` | `1.16e12 Pa/s` | Full feedback still destabilizes the confinement-only state. |

No axial smoke was run. T4l confirms that cap/axial support was a real missing
piece, but it does not yet produce a validation-ready hydrostatic equilibrium.
DP, MCC, GPU parity, and full paper reproduction remain deferred.

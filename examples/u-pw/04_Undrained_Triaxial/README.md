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

## M3d MCC Feedback-Off Refinement

`experiments/M3d_MCCFeedbackOffRefinement/` extends the M3c MCC CPU branch to
the T5c platen time window (`TimeMax=0.018 s`) with `PorePressureFeedback=0`.

Status:

- high-pc MCC (`pc0=100000 Pa`) remains elastic-like:
  `code=0`, `excluded=0`, `DtMin=0`, `YieldFlag=0/407`, `Kplastic=0`;
- mild-yield MCC (`pc0=120 Pa`) remains solver-stable:
  `code=0`, `excluded=0`, `DtMin=0`, but the final frame reports
  `MccReturnStatus=-3` for `8/407` particles;
- pairwise platen reaction remains bounded, but it is still a pairwise
  interaction diagnostic, not a full actuator reaction;
- full pore-pressure feedback and GPU remain deferred.

Because the mild extended case exposes local MCC return failures, M3d is a
useful refinement diagnostic but not yet a clean MCC validation package.

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

## T4m Zhao All-Surface Isotropic Confinement

T4m is retained under:

`experiments/T4m_AllSurfaceIsotropicConfinement/`

It tests Zhao-style all-surface isotropic confinement:

```xml
<parameter key="InitialStressMode" value="1" />
<parameter key="InitialEffectiveStressIso" value="50" />
<parameter key="FlexibleConfiningStress" value="1" />
<parameter key="ConfiningStressUseFiSelector" value="1" />
<parameter key="ConfiningStressUseLateralSelector" value="0" />
<parameter key="CapConfiningStress" value="0" />
```

This route uses one pairwise kernel-truncation confinement mechanism across
lateral, cap, and edge free surfaces instead of mixing lateral confinement with
explicit cap support.

T4m CPU Release results:

| Case | Result | Final `p'` | Final `q` | Max `PorePressRate` |
| --- | --- | ---: | ---: | ---: |
| T4l lateral+cap reference, feedback off | `code=0`, `excluded=0`, `DtMin=0` | `38.9 Pa` | `53.5 Pa` | `4.42e7 Pa/s` |
| all-surface `f_i`, feedback off | `code=0`, `excluded=0`, `DtMin=0` | `46.4 Pa` | `15.6 Pa` | `3.98e7 Pa/s` |
| all-surface `f_i`, delayed feedback | `code=0`, `excluded=0`, `DtMin=0` | failed | failed | `1.63e12 Pa/s` |

The all-surface feedback-off stage is much closer to hydrostatic equilibrium,
especially at the cap and edge regions. It does not solve the full-feedback
instability, so axial loading, DP, MCC, and GPU validation remain deferred.

## T4n Staged All-Surface To Lateral Switch

T4n is retained under:

`experiments/T4n_StagedConfinementSwitch/`

It adds the CPU-only opt-in selector scheduling parameter:

```xml
<parameter key="ConfiningStressUseLateralSelector" value="1" />
<parameter key="ConfiningStressLateralSelectorStartTime" value="0.003" />
```

The default remains unchanged. With the start time set, the run begins with
Zhao all-surface `f_i` confinement and switches to lateral-only selected
confinement at `0.003 s`.

T4n CPU Release results:

| Case | Result | Active targets | Final `p'` | Final `q` | Max `PorePressRate` |
| --- | --- | ---: | ---: | ---: | ---: |
| all-surface reference, feedback off | `code=0`, `excluded=0`, `DtMin=0` | `208` | `46.4 Pa` | `15.6 Pa` | `3.98e7 Pa/s` |
| staged switch, feedback off | `code=0`, `excluded=0`, `DtMin=0` | `208 -> 112` | `19.1 Pa` | `46.3 Pa` | `5.46e7 Pa/s` |
| staged switch, delayed feedback | `code=0`, `excluded=0`, `DtMin=0` | `208 -> 112` | failed | failed | `9.15e9 Pa/s` |

The selector switch itself is numerically runnable and the active target count
changes as expected. It is not hydrostatically neutral: after switching to
lateral-only confinement, `q` grows and `p'` drifts away from the target. The
delayed-feedback case is much less violent than T4m delayed feedback but still
fails the stability gate. Axial loading was not restored. DP, MCC, and GPU
remain deferred.

## T4n1 Literature Audit For Staging Treatments

T4n1 is documentation-only. It is retained in:

- `src/papers/u-p/t4n1_zhao_confinement_staging_audit.md`
- `src/papers/u-p/t4n1_upw_stabilization_audit.md`
- `src/papers/u-p/t4n1_staging_treatment_classification.md`
- `src/papers/u-p/t4n1_ramped_selector_transition_decision.md`
- `src/papers/u-p/t4n1_next_step_recommendation.md`

Main conclusion:

- Zhao supports initial hydrostatic stress, damping during confinement
  equilibration, `f_i` free-boundary selection, smooth/fan-shaped specimen
  layouts, and large-deformation confinement rescaling.
- The u-pw notes support corrected gradients, artificial viscosity/kinematic
  damping, stress initialization, and careful pressure/time-step stability.
- Zhao does not directly support a time-ramped all-surface-to-lateral selector
  transition.
- A ramped selector may be useful as an engineering staging protocol, but it
  should not be presented as a paper-faithful boundary law.

Recommended next step: prioritize a restart-based all-surface confinement
equilibrium audit before implementing a ramped selector transition. DP, MCC,
axial loading, and GPU validation remain deferred.

## T4n2 Restart Equilibrium Audit

T4n2 is retained under:

`experiments/T4n2_RestartEquilibriumAudit/`

It tests the recommended restart route instead of adding selector smoothing:

1. Stage A: all-surface `f_i` confinement, initial hydrostatic effective
   stress, feedback off;
2. Stage B: true restart from Stage A `Part_0023`, switched to lateral-only
   confinement, feedback off;
3. Stage C: diagnostic delayed interior feedback after restart.

The existing restart path preserves the current elastic u-pw state. Stage B
restored `Sigma_kk`, `Sigma_ij`, `Kplastic`, and `PorePress` for `407/407`
particles, and the CSV continuity comparison is exact in saved precision for
stress, pore pressure, velocity, density, and position.

The restart workflow itself is therefore feasible, but it does not solve the
mechanical transition:

| Case | Result | Final `p'` | Final `q` | Max `PorePressRate` |
| --- | --- | ---: | ---: | ---: |
| Stage A all-surface, feedback off | `code=0`, `excluded=0`, `DtMin=0` | `46.38 Pa` | `15.65 Pa` | `3.98e7 Pa/s` |
| Stage B restart lateral, feedback off | `code=0`, `excluded=0`, `DtMin=0` | `13.50 Pa` | `37.89 Pa` | `4.02e7 Pa/s` |
| Fresh lateral-only, feedback off | `code=0`, `excluded=0`, `DtMin=0` | `17.11 Pa` | `51.47 Pa` | `4.48e7 Pa/s` |
| Stage C restart lateral, delayed feedback | `code=0`, `excluded=0`, `DtMin=0` | failed | failed | `1.84e12 Pa/s` |

Stage B improves `q` relative to a fresh lateral-only run and is slightly
better than the T4n instant switch, but it still loses hydrostatic balance and
drives all particles into negative pore pressure. Stage C confirms that
feedback after restart is still unstable. Axial loading remains disabled. DP,
MCC, and GPU validation remain deferred.

## T4o Cap-Support-Preserving Restart

T4o is retained under:

`experiments/T4o_CapSupportStagedLoading/`

It tests whether the T4n2 Stage B failure was caused by removing the cap/axial
hydrostatic support after all-surface confinement:

1. Stage A: all-surface `f_i` confinement, feedback off;
2. Stage B: restart with lateral selected confinement plus
   `CapConfiningStress=1`, feedback off;
3. Stage C: same lateral+cap support with delayed feedback.

The restart remains exact, and all runs completed with `code=0`, `excluded=0`,
`DtMin=0`, and `Kplastic=0`. The mechanical gate did not pass:

| Case | Final `p'` | Final `q` | Max `PorePressRate` |
| --- | ---: | ---: | ---: |
| Stage A all-surface, feedback off | `46.38 Pa` | `15.65 Pa` | `3.98e7 Pa/s` |
| Stage B restart lateral+cap, feedback off | `23.87 Pa` | `61.92 Pa` | `5.06e7 Pa/s` |
| Stage C restart lateral+cap, delayed feedback | failed | failed | `9.32e11 Pa/s` |

The current explicit cap support does not preserve the all-surface hydrostatic
state; it increases the `q` imbalance beyond the T4n2 lateral-only restart.
Delayed feedback remains unstable, so axial loading was not restored. DP, MCC,
and GPU validation remain deferred.

## T4p Cap / Platen Boundary Audit

T4p is documentation-only and is retained in:

- `src/papers/u-p/t4p_zhao_cap_platen_boundary_audit.md`
- `src/papers/u-p/t4p_current_triaxial_cap_group_audit.md`
- `src/papers/u-p/t4p_cap_boundary_source_audit.md`
- `src/papers/u-p/t4p_triaxial_platen_workflow_design.md`
- `src/papers/u-p/t4q_platen_boundary_implementation_plan.md`

The audit reinterprets the T4o failure as a cap/platen boundary formulation
problem, not a cap-force tuning problem. Zhao's triaxial examples use explicit
top/bottom loading platens: the bottom platen is fixed and the top platen has
prescribed downward motion. This differs from the current reduced triaxial
smokes, where `mkfluid=1` is a material top loading layer driven by
`AccInput`.

`AccInput` remains useful for smoke tests, but it is not a strict platen
boundary condition and it does not provide platen reaction output. The
`CapConfiningStress` feature is now classified as diagnostic-only; it should
not be tuned into a production triaxial cap route.

Recommended next step: T4q should prototype an explicit platen workflow with a
fixed bottom platen, prescribed top platen velocity or displacement, lateral
`FlexibleConfiningStress`, specimen-only measurements, and reaction-force
diagnostics. Axial loading validation, DP, MCC, and GPU remain deferred until
that cap/platen route is stable.

## T4q Explicit Platen Boundary Workflow

T4q is retained under:

`experiments/T4q_PlatenBoundaryWorkflow/`

It confirms that a reduced explicit platen workflow can be built with existing
XML features:

- specimen soil: `mkfluid=0`, `407` particles;
- top platen: moving `mkbound=1`, `74` particles;
- bottom platen: fixed `mkbound=2`, `74` particles;
- measurement core: `15` specimen particles, with `0` platen contamination;
- `CapConfiningStress=0`.

All three CPU Release smokes completed with `code=0`, `excluded=0`,
`DtMin=0`, and `Kplastic=0`. The top platen follows its prescribed
`v_z=-0.005 m/s` motion and reaches about `-7.5e-6 m` displacement; the bottom
platen remains fixed. The platen route also coexists with lateral
`FlexibleConfiningStress` (`112` active lateral targets, cap leakage
diagnostic `0`).

T4q does not yet validate axial stress because no robust top/bottom reaction
output is available. `AccInput` remains a smoke-only route. The recommended
next step is T4r: a platen-based selected-confinement baseline with reaction
diagnostics planned before DP, MCC, or GPU work.

## T4r Platen Reaction Diagnostics

T4r is retained under:

`experiments/T4r_PlatenReactionDiagnostics/`

It keeps the explicit T4q platen geometry and adds specimen-only
postprocessing:

- top platen: moving `mkbound=1`;
- bottom platen: fixed `mkbound=2`;
- specimen: `mkfluid=0`;
- center measurement core: `15` specimen particles with `0` platen
  contamination;
- `PorePressureFeedback=0`;
- `CapConfiningStress=0`.

Both CPU Release smokes completed with `code=0`, `excluded=0`, `DtMin=0`, and
`Kplastic=0`. The top platen displacement reaches about `-7.50e-6 m`; the
bottom platen remains fixed.

The current XML-only workflow still cannot output a true top/bottom platen
reaction. T4r therefore reports a specimen-stress proxy:

`Fz_proxy = -mean(Sigma_zz) * pi * R^2`

Final proxy values:

| Case | Final `p'` proxy | Final `q` proxy | Final `Fz_proxy` |
| --- | ---: | ---: | ---: |
| Platen axial, no confinement | `27.94 Pa` | `43.47 Pa` | `0.1609 N` |
| Platen axial, lateral confinement | `49.10 Pa` | `33.28 Pa` | `0.2015 N` |

The lateral confinement case remains stable and keeps the known selector
diagnostics (`112` active lateral targets, cap leakage `0`). T4s may proceed as
a feedback-off platen-based axial baseline using these specimen-only proxies,
but strict validation still needs a source-level true reaction diagnostic.
Full feedback, DP, MCC, and GPU remain deferred.

## T4s Feedback-Off Platen Axial Baseline

T4s is retained under:

`experiments/T4s_PlatenAxialBaseline/`

It extends the explicit platen workflow to a longer feedback-off elastic axial
baseline:

- top moving platen: `mkbound=1`, prescribed `v_z=-0.005 m/s`;
- bottom fixed platen: `mkbound=2`;
- specimen: `mkfluid=0`, `407` particles;
- `PorePressureFeedback=0`;
- `SoilConstitutiveModel=0`;
- CPU Release only.

Two cases are retained:

| Case | Result | Final `p'` proxy | Final `q` proxy | Final `Fz_proxy` |
| --- | --- | ---: | ---: | ---: |
| no lateral confinement | `code=0`, `excluded=0`, `DtMin=0`, `Kplastic=0` | `117.91 Pa` | `346.17 Pa` | `0.9859 N` |
| lateral flexible confinement | `code=0`, `excluded=0`, `DtMin=0`, `Kplastic=0` | `145.66 Pa` | `332.47 Pa` | `1.0385 N` |

The top platen reaches the expected `-3.00e-5 m` displacement over the
`0.006 s` window, while the bottom platen remains fixed. Measurement regions
remain specimen-only with zero platen contamination. The lateral-confinement
case keeps `112` active lateral targets and cap leakage diagnostic `0`.

T4s is a reduced feedback-off platen baseline. It still uses
`Fz_proxy=-mean(Sigma_zz)*pi*R^2`; no true platen reaction is available yet.
Full feedback, strict axial-reaction validation, MCC, and GPU remain deferred.

## T5 DP Feedback-Off Platen Baseline

T5 is retained under:

`experiments/T5_DPFeedbackOffBaseline/`

It keeps the T4s explicit-platen/lateral-confinement workflow and switches the
skeleton to `SoilConstitutiveModel=1` Drucker-Prager:

- top moving platen: `mkbound=1`, prescribed `v_z=-0.005 m/s`;
- bottom fixed platen: `mkbound=2`;
- lateral selected `FlexibleConfiningStress`;
- `PorePressureFeedback=0`;
- CPU Release only.

Two short DP cases are retained:

| Case | DP parameters | Result | Final `Kplastic` max | Final `p'` / `q` proxy |
| --- | --- | --- | ---: | ---: |
| high strength | `phi=33 deg`, `coh=10000 Pa`, `dlt=0` | `code=0`, `excluded=0`, `DtMin=0` | `0` | `145.66 / 332.47 Pa` |
| mild yield | `phi=30 deg`, `coh=50 Pa`, `dlt=0` | `code=0`, `excluded=0`, `DtMin=0` | `4.38e-4` | `86.58 / 126.76 Pa` |

The high-strength case reproduces the T4s elastic lateral baseline because the
yield surface is not reached. The mild-yield diagnostic activates plasticity
in `341/407` specimen particles while keeping pore pressure, velocity, and
confinement diagnostics bounded. This is a reduced DP feedback-off baseline,
not strict triaxial validation. True reaction output, full feedback, MCC, and
GPU remain deferred.

## T4t Platen Reaction Diagnostics

T4t is retained under:

`experiments/T4t_TruePlatenReaction/`

It adds an opt-in CPU diagnostic for top/bottom explicit platen reactions:

- `SavePlatenReactionDiagnostics=1`;
- top platen `mkbound=1`;
- bottom platen `mkbound=2`;
- `PlatenReactionMode=0`;
- `PlatenReactionArea=pi*R^2`.

Mode `0` is a CPU pairwise fluid-bound interaction accumulator. It sums the
opposite of the specimen-side SPH pair force contribution for pairs involving
the selected top or bottom platen. This is a specimen-platen contact reaction
diagnostic, not the previous specimen-stress proxy and not a full prescribed
motion actuator reaction.

Three CPU Release feedback-off cases completed with `code=0`, `excluded=0`,
and `DtMin=0`:

| Case | Final `Kplastic` max | Top/bottom `Fz` reaction | Pairwise reaction vs `Fz_proxy` |
| --- | ---: | ---: | ---: |
| elastic | `0` | `1.04649 / -0.867504 N` | `0.956997 N` vs `1.03854 N` |
| DP high strength | `0` | `1.04649 / -0.867504 N` | `0.956997 N` vs `1.03854 N` |
| DP mild yield | `4.38e-4` | `0.55936 / -0.426189 N` | `0.492775 N` vs `0.48374 N` |

The reaction diagnostic is usable for T5b reduced DP refinement. Full
pore-pressure feedback, MCC, and GPU triaxial validation remain deferred.

## T5b DP Feedback-Off Refinement

T5b is retained under:

`experiments/T5b_DPFeedbackOffRefinement/`

It keeps the explicit platen workflow, selected lateral
`FlexibleConfiningStress`, and T4t pairwise reaction diagnostic. Full
`PorePressureFeedback` remains off.

Three CPU Release cases completed with `code=0`, `excluded=0`, and `DtMin=0`:

| Case | Setup | Final `Kplastic` max | Final `p'` / `q` proxy | Pairwise reaction avg |
| --- | --- | ---: | ---: | ---: |
| elastic | `SoilConstitutiveModel=0` | `0` | `145.66 / 332.47 Pa` | `0.956997 N` |
| DP high strength | `phi=33 deg`, `coh=10000 Pa`, `dlt=0` | `0` | `145.66 / 332.47 Pa` | `0.956997 N` |
| DP mild yield | `phi=30 deg`, `coh=50 Pa`, `dlt=0` | `4.38e-4` | `86.58 / 126.76 Pa` | `0.492775 N` |

The high-strength DP line matches the elastic reference, while the mild-yield
line activates plasticity in `341/407` specimen particles and reduces `q`,
reaction force, and pore pressure without destabilizing the run. T5c may extend
this reduced feedback-off DP trend. MCC, full feedback, and GPU remain
deferred.

## T5c DP Feedback-Off Extended Response

T5c is retained under:

`experiments/T5c_DPExtendedFeedbackOff/`

It extends the T5b DP feedback-off platen workflow to `TimeMax=0.018 s` while
keeping the same explicit platens, selected lateral `FlexibleConfiningStress`,
and pairwise platen reaction diagnostic. `PorePressureFeedback` remains off.

Two CPU Release cases completed with `code=0`, `excluded=0`, and `DtMin=0`:

| Case | Setup | Final `Kplastic` max | Plastic count | Final `p'` / `q` proxy | Pairwise reaction avg |
| --- | --- | ---: | ---: | ---: | ---: |
| DP high strength | `phi=33 deg`, `coh=10000 Pa`, `dlt=0` | `0` | `0/407` | `385.80 / 1073.74 Pa` | `3.2740 N` |
| DP mild yield | `phi=30 deg`, `coh=50 Pa`, `dlt=0` | `1.462e-3` | `407/407` | `62.23 / 120.51 Pa` | `0.4335 N` |

The mild-yield case shows smooth saved-frame growth of `Kplastic` and remains
bounded without excluded particles, DtMin bursts, or velocity blow-up. The
reaction-based axial stress-strain and p'-q curves are more complete than T5b,
but this remains a reduced feedback-off diagnostic, not strict paper
validation. T5d may consolidate DP measurement/reporting; MCC planning can
begin as a design-only activity. Full feedback and GPU remain deferred.

## T5d DP Feedback-Off Package

T5d is retained under:

`experiments/T5d_DPFeedbackOffPackage/`

It adds no new simulation. It consolidates retained outputs from T4s, T4t, T5,
T5b, and T5c into one reduced validation package:

- `t5d_case_inventory.csv`;
- `t5d_summary_metrics.csv`;
- `t5d_reaction_comparison.csv`;
- `t5d_stress_path_comparison.csv`;
- `t5d_plasticity_summary.csv`;
- `t5d_pore_pressure_summary.csv`;
- main and supplementary figure candidates.

The package covers the feedback-off explicit-platen DP route only. It validates
the platen grouping, selected lateral confinement coexistence, pairwise
reaction diagnostic, high-strength DP elastic-like response, mild DP plastic
activation, and bounded PR pressure update with feedback off.

It does not validate full pore-pressure feedback, MCC, true actuator reaction,
strict paper triaxial reproduction, or GPU. MCC may now move into
planning-only work; implementation remains deferred.

## M1 Modified Cam Clay Design Audit

M1 is retained as documentation under:

`src/papers/u-p/m1_*.md`

It adds no source code and runs no new cases. The audit maps the current
effective-stress update path and defines the next MCC implementation route:

- current `Sigmac` stores skeleton/effective stress with compression negative;
- MCC formulas should use compression-positive `p' = -trace(Sigmac)/3`;
- `SoilConstitutiveModel=3` is reserved as the proposed MCC selector;
- MCC needs new restart-safe state, including `p_c`, void ratio/specific
  volume, plastic volumetric strain, and MCC diagnostics;
- the recommended next step is an M2 CPU single-point MCC return-mapping
  prototype before any SPH integration.

The first future SPH MCC smoke should reuse the feedback-off explicit-platen
T5 workflow. Full pore-pressure feedback, MCC implementation, and GPU remain
deferred until the single-point and state/restart gates are passed.

## M2 MCC Single-Point Prototype

M2 is retained under:

`src/papers/u-p/mcc_single_point/`

It is a standalone Python material-point prototype and does not modify the SPH
solver. The test runner generates CSV and SVG/PNG figures for:

- stress sign regression;
- isotropic compression/swelling;
- drained-like triaxial strain path;
- undrained-like zero-volumetric-strain path;
- yield consistency and return-iteration diagnostics.

The prototype uses compression-positive MCC variables internally and maps to
the current `Sigmac` convention with `p' = -trace(Sigmac)/3`. The retained
tests complete without failed steps; plastic-step normalized yield residuals
remain below about `3e-9`.

MCC is still not integrated into GeoDualSPHysics. M3 may now port the verified
single-point helper into a CPU-only `SoilConstitutiveModel=3` branch, with the
first SPH smoke still based on the feedback-off explicit-platen T5 workflow.
Full feedback and GPU remain deferred.

## M3j Boundary-Induced MCC Return Failure Audit

M3j is retained under:

`experiments/M3j_BoundaryFailureAudit/`

It is a postprocessing-only audit using retained M3d2/M3f/M3h failed-return
CSV outputs. No source was modified, no new solver case was run, no GPU
simulation was run, and full pore-pressure feedback remained off.

Main finding:

- failed MCC returns are strongly concentrated in cap/platen/edge regions;
- edge-corner records dominate the aggregate failed set;
- bottom fixed-platen-adjacent records recur in slower and cleaner final-frame
  routes;
- top cap and lateral surface records also appear, especially in ramp/adaptive
  variants;
- measurement-core failures are rare.

This supports a boundary-induced local strain/stress-path interpretation rather
than a global MCC return-mapping collapse or sign-convention error.

M3j recommends a boundary-first next step: a very-short dense-output
platen/edge diagnostic to capture neighbor count, support/completeness, local
velocity-gradient, and failed-vs-nearby-nonfailed metrics. More return-mapping
patches should be secondary until that boundary diagnostic is complete.

The MCC route remains reduced and caveated. Clean MCC validation, full
pore-pressure feedback, and GPU MCC remain deferred.

## M3a C++ MCC Helper Parity

M3a is retained under:

`src/papers/u-p/mcc_single_point/cpp/`

It ports the standalone Python MCC single-point prototype to a C++ helper
without connecting it to the SPH solver. Python-vs-C++ parity is exact in the
retained CSV outputs for isotropic, drained-like, and undrained-like paths:

- max `p'` diff: `0`;
- max `q` diff: `0`;
- max `p_c` diff: `0`.

The helper uses the same sign convention as M2: MCC internals are
compression-positive and future SPH mapping uses `p'=-trace(Sigmac)/3`.

## M3b MCC Parser / State Init Skeleton

M3b is retained under:

`experiments/M3b_MCCParserStateInit/`

It adds CPU parser/state/output infrastructure for
`SoilConstitutiveModel=3`, but still does not connect MCC return mapping to the
SPH stress update.

Two CPU Release smoke cases were run:

| Case | Key init route | Result |
| --- | --- | --- |
| `CaseM3b_MccPc0_Init` | direct `pc0=200 Pa`, no initial stress | `code=0`, `excluded=0`, `DtMin=0` |
| `CaseM3b_MccOCR_InitialStress` | `OCR=4`, `InitialEffectiveStressIso=50 Pa` | `code=0`, `excluded=0`, `DtMin=0` |

`SaveMccState=1` outputs `MccPc`, `MccVoidRatio`,
`MccPlasticVolStrain`, `MccEqPlasticStrain`, `MccYieldFlag`,
`MccPlasticMultiplier`, `MccReturnStatus`, `MccReturnIterations`, and
`MccYieldResidual`.

The OCR smoke confirms:

```text
InitialEffectiveStressIso=50 Pa -> Sigmac diagonal=-50 Pa -> p'=+50 Pa
OCR=4 -> pc=200 Pa
```

MCC stress update remains deliberately disconnected in M3b. M3c may now add
the CPU stress-update branch. Full pore-pressure feedback and GPU remain
deferred.

## M3c CPU MCC Stress Update

M3c is retained under:

`experiments/M3c_MCCStressUpdateCpu/`

It connects `SoilConstitutiveModel=3` to a CPU-only Modified Cam Clay stress
update branch. MCC internals use compression-positive stress and map to the
current `Sigmac` convention with:

```text
p' = -trace(Sigmac)/3
Sigmac_new = -stress_cp_new
```

Two feedback-off explicit-platen smokes were run with selected lateral
FlexibleConfiningStress and `InitialEffectiveStressIso=50 Pa`:

| Case | pc0 | Result |
| --- | ---: | --- |
| `CaseM3c_MCCHighPc_ElasticLike` | `100000 Pa` | `code=0`, `excluded=0`, `DtMin=0`, no MCC yield |
| `CaseM3c_MCCMildYield` | `120 Pa` | `code=0`, `excluded=0`, `DtMin=0`, MCC yield active |

The mild case updates `pc`, void ratio, plastic volumetric strain, equivalent
plastic strain, plastic multiplier, return iterations, and yield residual
outputs. Full feedback, strict MCC validation, and GPU remain deferred.

## M3d2 MCC Return Robustness Audit

M3d2 is retained under:

`experiments/M3d2_MCCReturnRobustness/`

It reruns the mild-yield MCC feedback-off platen case and adds three diagnostic
variants: half top-platen velocity, early stop, and tighter return tolerance
with higher max iterations. No solver source was changed.

All four CPU Release cases finish `code=0`, `excluded=0`, and `DtMin=0`. The
baseline and tight-return cases retain the same final local return issue:

```text
MccReturnStatus=-3: 8/407 particles
```

The final failed particles are localized near the bottom interior/cap
transition at `z≈0.01-0.02 m`. Half velocity removes final `-3` failures but
does not remove all intermediate local failures. Higher max iterations and
tighter tolerance do not change the final failed set. The recommended next
step is opt-in MCC constitutive substepping/admissibility guards before clean
M3e consolidation. Full feedback and GPU remain deferred.

## M3d3 MCC Substepping Robustness

M3d3 is retained under:

`experiments/M3d3_MCCSubstepping/`

It adds CPU-only, opt-in MCC local-return robustness controls:

- `MccSubstepping`
- `MccMaxSubsteps`
- `MccSubstepMode`
- `MccSubstepStrainThreshold`
- `MccAdmissibilityGuard`
- `MccFailureFallback`

Default behavior remains unchanged (`MccSubstepping=0`, guard off, fallback
off). GPU still hard-errors for `SoilConstitutiveModel=3`.

All M3d3 CPU Release cases finish `code=0`, `excluded=0`, and `DtMin=0`.
However, original-rate fixed/adaptive substepping does not fully clean the mild
MCC return issue. The main final statuses are:

```text
baseline:             -3:8|0:2|1:397
fixed_substeps4:      -3:18|-1:8|0:2|2:379
adaptive_substeps16:  -3:10|-1:8|0:2|1:387
adaptive_fallback16:  -5:17|0:2|1:387|2:1
half_speed_adaptive:  0:12|1:395
```

`adaptive_fallback16` removes final `-3` but leaves explicit `-5` partial
fallback, so it is a safety diagnostic rather than clean validation. The
cleanest reduced route is half-speed adaptive, which clears final negative
return statuses while keeping reaction, p'-q, and pore pressure bounded. M3e
may proceed only as a reduced feedback-off reporting package with this caveat.
Full pore-pressure feedback and GPU remain deferred.

## M3l Platen/Specimen Smoothing Diagnostic

M3l is retained under:

`experiments/M3l_PlatenSpecimenSmoothing/`

It tests four CPU-only, feedback-off, very-short dense-output variants:

- `baseline`: M3k-equivalent reference;
- `gap_2dp`: generated platen/specimen center gap increased to 2dp;
- `platen_overhang`: platen radius increased from 0.03 m to 0.04 m;
- `edge_selector_buffer`: cap/edge lateral confinement exclusion increased to
  0.025 m.

All cases finish `code=0`, `excluded=0`, and `DtMin=0`.

Main result:

```text
baseline:          max -3=16, max -1=157, final negative=40
gap_2dp:           max -3=0,  max -1=258, final negative=89
platen_overhang:   max -3=8,  max -1=20,  final negative=8
edge_selector:     max -3=13, max -1=174, final negative=69
```

`platen_overhang` is the best diagnostic direction. It greatly reduces failed
records and improves aggregate failed-particle support, while keeping pairwise
reaction, p'-q, and pore pressure bounded. It is not clean because saved-frame
`ReturnStatus=-3` remains.

The next step should be M3m refined boundary geometry: keep the overhang insight
and test a better platen/specimen interface plus real edge/corner smoothing.
The route still cannot be called clean MCC validation. Full feedback and GPU
remain deferred.

## M3k Platen/Edge Dense Diagnostic

M3k is retained under:

`experiments/M3k_PlatenEdgeDenseDiagnostic/`

It runs a very-short dense-output mild MCC feedback-off platen case to capture
the first local return-failure onset. The case finishes `code=0`,
`excluded=0`, and `DtMin=0`, with the first saved-frame failure at
`t=0.001005 s`:

```text
ReturnStatus=-1: 92
ReturnStatus=-3: 4
```

The hardest `-3` failures are localized at the top edge/corner in the first
onset frame, with reduced support and elevated local velocity-gradient proxies.
The broader `-1` failures are near-tension/admissibility states and include
edge, lateral, bottom-cap, and adjacent interior particles. Pairwise reaction,
p'-q, pore pressure, `pc`, void ratio, and plastic strains remain bounded.

M3k strengthens the boundary-induced failure interpretation. The next technical
step should test platen/specimen interface smoothing or edge/corner smoothing,
not another MCC return-mapping patch. The route still cannot be called clean
MCC validation. Full pore-pressure feedback and GPU remain deferred.

## M3h MCC Admissible Return

M3h is retained under:

`experiments/M3h_MCCAdmissibleReturn/`

It adds an opt-in MCC admissible line-search diagnostic for CPU
`SoilConstitutiveModel=3`:

- `MccAdmissibleLineSearch`;
- `MccLineSearchMaxBacktrack`;
- `MccLineSearchMinStep`;
- `MccLineSearchResidualReduction`;
- `MccEnforcePositivePlasticMultiplier`;
- `MccAdmissibleProjection`;
- `MccLineSearchBacktrackCount`;
- `MccLineSearchRejectReason`;
- `MccLineSearchMinAlpha`.

Defaults preserve the previous MCC return behavior.  Full pore-pressure
feedback remains off in all M3h cases, and GPU MCC remains unsupported.

Five CPU Release cases were run.  All finish `code=0`, `excluded=0`, and
`DtMin=0`.  However, no clean reduced MCC validation candidate was obtained:

```text
baseline final:                 -3:8
admissible-line final:          -3:8
adaptive+line final:            -3:10|-1:8
half-speed adaptive+line final: 0:407 split over elastic/plastic statuses
quarter-speed line final:       0:407 split over elastic/plastic statuses
```

Half-speed and quarter-speed clear the final frame, but both still contain
transient saved-frame negative MCC return statuses.  Original-rate admissible
line search does not improve the baseline, and adaptive substepping plus line
search worsens the original-rate result.

M3h therefore does not justify a clean M3g validation package.  The MCC route
remains a CPU-only, feedback-off reduced diagnostic.  Full feedback and GPU
remain deferred.

## M3e MCC Feedback-Off Reporting Package

M3e is retained under:

`experiments/M3e_MCCFeedbackOffPackage/`

It does not add new simulations. It consolidates M3c, M3d, M3d2, and M3d3
MCC feedback-off explicit-platen results into a reduced reporting package.

The package includes high-pc MCC smokes, mild-yield MCC smokes, the extended
M3d cases, M3d2 loading/tolerance diagnostics, and M3d3 substepping/fallback
diagnostics. The main conclusion is:

- high-pc MCC remains elastic-like;
- mild MCC yields and evolves `pc`, void ratio, and plastic strains;
- MCC state output and pairwise reaction diagnostics are usable;
- original-rate mild MCC is not clean because local return failures remain;
- adaptive fallback is a safety diagnostic, not a validation setting;
- half-speed adaptive is the cleanest final-frame reduced route;
- strong negative mild-MCC pore pressure keeps this as feedback-off diagnostic
  evidence, not strict undrained validation.

M3f is recommended before clean MCC validation. M4 can proceed only as planning
unless the reduced-route limitations are explicitly accepted. Full feedback and
GPU remain deferred.

## M3f MCC Return/Staging Refinement

M3f is retained under:

`experiments/M3f_MCCReturnStagingRefinement/`

It adds an opt-in improved MCC adaptive substepping diagnostic:

- `MccMinSubsteps`;
- `MccSubstepYieldDistanceThreshold`;
- `MccSubstepTriggerReason` output;
- `MccSubstepMode=2` can now trigger from minimum substeps, strain-increment
  threshold, and normalized trial yield-distance threshold.

Defaults remain unchanged. Full pore-pressure feedback stays off in all M3f
cases, and GPU MCC remains unsupported.

Seven CPU Release diagnostic cases were run. All finish `code=0`,
`excluded=0`, and `DtMin=0`, but none satisfies the strict clean gate because
every candidate still has at least one saved frame with negative MCC return
status.

Main M3f outcomes:

- transient failures remain local to edge/platen-adjacent regions;
- smoother platen ramping does not clean the route;
- improved adaptive substepping is implemented but does not improve the tested
  thresholds;
- quarter-speed adaptive has the fewest transient failures, but still has
  saved-frame `ReturnStatus=-3` episodes;
- reaction, p'-q, MCC state histories, and pore pressure remain bounded;
- M3g should not be claimed as clean validation unless a later return/staging
  refinement removes all transient negative statuses.

Full pore-pressure feedback and GPU remain deferred.

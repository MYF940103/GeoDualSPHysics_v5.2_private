# Notes: Undrained Triaxial

## Current Purpose

`CaseUndrainedTriaxial_PR_Smoke_Def.xml` is a reduced smoke case for the CPU
u-pw PR implementation. It is intended to verify that a tiny native AccInput
axial load can be applied to a top material layer while pore-pressure fields and
stress outputs are written.

It is not a validated reproduction of the paper's triaxial results.

Under the full CPU pre-GPU gate, this case remains incomplete for strict
reproduction. The existing smoke proves that native AccInput, pore-pressure
fields, and stress outputs can run briefly; it does not prove that the paper's
triaxial loading path, confinement, material response, or stress-path outputs
are reproduced.

## Current Numerical Setup

- Mechanical body gravity is disabled.
- Hydraulic gravity is `(0,0,-9.81)` to keep the hydraulic head definition
  available.
- `PorePressureInit=1` initializes a hydrostatic baseline.
- Top drainage is delayed with `PorePressureTopDrainedStartTime=999`, so the
  short smoke remains undrained.
- Feedback uses:
  - `PorePressureFeedbackMode=1` (excess pressure)
  - `PorePressureFeedbackOperator=1` (difference-gradient)
- Stabilization uses:
  - `HydromechDampingXi=0.05`
  - `PorePressureShepard=1`
  - `PorePressureShepardMode=1`

## Loading

The top material layer uses `mkfluid=1` and is driven by DualSPHysics native
`accinput`. The current CSV is intentionally tiny:

```text
0.001 s -> LinearAccZ = -0.047619 m/s2
```

This corresponds to an extremely small compressive load-equivalent acceleration
and is only meant to exercise the coupled field plumbing.

## Missing for Strict Triaxial Reproduction

- Paper geometry and loading:
  - cylinder height `0.15 m`;
  - diameter `0.05 m`;
  - particle spacing `0.002 m`;
  - top vertical velocity `0.01 m/s`;
  - bottom fixed;
  - top/bottom free-slip;
  - lateral flexible confined boundary.
- Prescribed confining pressure / lateral stress boundary.
- Calibrated constitutive law. The paper uses MCC for the triaxial tests; the
  current Drucker-Prager path is an approximation.
- Validated stress-path postprocessing for `p'`, `q`, axial strain, and
  volumetric strain.
- Higher resolution and longer runtime, preferably after GPU porting.

Known paper triaxial cases:

- TU-L: `(pc)_0 = 200 kPa`, confining pressure / initial mean effective stress
  `150 kPa`.
- TU-M: `(pc)_0 = 200 kPa`, confining pressure `30 kPa`.
- TU-N: `(pc)_0 = 200 kPa`, confining pressure `200 kPa`.
- permeability `k=1e-8 m/s` for undrained behavior.

## Smoke Interpretation

The current smoke passes the strict/minimal CPU execution health check:

- GenCase code=0.
- DualSPHysics code=0.
- Excluded particles=0.
- Pore-pressure and stress fields are written.
- The tiny compressive load gives small positive excess pore pressure.
- `analyze_triaxial_smoke.py` produces `triaxial_smoke_summary.csv` with
  framewise `p'`, `q`, pore-pressure, velocity, and axial-strain proxy metrics.

Strict triaxial validation remains feature-blocked by loading/confinement,
stress-path postprocessing, and material-model choices. It is no longer a pure
TODO scaffold, but it still blocks strict paper-case completion unless those
items are implemented or explicitly deferred.

## T1 Baseline Notes

T1 starts the post-Cryer benchmark route:

`experiments/T1_UndrainedTriaxialBaseline/`

Design choices:

- `SoilConstitutiveModel=0` for a linear elastic u-pw smoke;
- `PorePressureBoundaryOperator=0`;
- `HydraulicElevationSource=0` with `HydraulicGravity=(0,0,-9.81)` for
  scaling only;
- `PorePressureInit=0`;
- top-layer native `accinput`, final `LinearAccZ=-0.5 m/s2`;
- no true confining pressure;
- no GPU run.

T1 CPU Release completed with `code=0`, `excluded=0`, four PART frames, no
NaN/Inf in the postprocessed fields, and `Kplastic=0`. The upper-middle
measurement region below the loading layer developed positive excess pore
pressure (`42.12 Pa` at the final frame). The geometric center remains almost
unloaded over this very short window, so T2 should improve loading duration,
measurement definitions, and stress-path extraction before any paper-level
comparison.

## T2 Zhao Flexible Confinement Audit Notes

The Zhao flexible confined boundary paper has been converted and reviewed under
`src/papers/u-p/`. The method applies an isotropic confining-pressure pair term
to the SPH momentum equation. The term cancels in the interior when kernel
support is complete and becomes an inward traction near a truncated free
surface.

Current branch status:

- CPU `FlexibleConfiningStress` already adds a stress-like pair contribution,
  so it is the right starting point for triaxial lateral confinement.
- The current term uses the existing kernel gradient in the CPU force loop; it
  does not yet use Zhao's renormalized gradient form.
- It targets all selected material particles by mk and does not yet compute
  the kernel-completeness index `f_i = sum_j (m_j/rho_j) W_ij`.
- It cannot yet distinguish the cylindrical lateral membrane from top/bottom
  caps except by manual mk design.

T3 should therefore be diagnostic-first:

1. add `f_i` summary/histogram output;
2. classify lateral/cap/edge/interior particles in a cylinder;
3. report radial confining acceleration and axial leakage;
4. only then enable optional near-boundary and lateral-only selectors;
5. keep GPU and MCC deferred.

## T3 Flexible Confinement Diagnostic Notes

T3 completed the CPU diagnostic-first step. The source now provides optional
diagnostics and selectors for `FlexibleConfiningStress`, with all new selectors
off by default:

- `FlexibleConfiningStressFiDiagnostic`;
- `SaveConfiningStressDiagnostics`;
- `ConfiningStressFiThreshold`;
- `ConfiningStressGeometry=1` for cylinder classification;
- `ConfiningStressUseFiSelector`;
- `ConfiningStressUseLateralSelector`.

The reduced cylinder smoke has a coherent `f_i` and class split:

- `f_i` min/mean/max: `0.407175 / 0.745128 / 1.00132`;
- threshold selected count: `208 / 407`;
- lateral class count: `196`;
- top/bottom cap count: `18 + 18`;
- edge-ring count: `112`;
- selected active lateral targets: `112`.

Three CPU Release smokes ran successfully:

- confinement-only legacy selector off: `code=0`, `excluded=0`;
- confinement-only `f_i` + lateral selector on: `code=0`, `excluded=0`;
- axial AccInput plus selected flexible confinement: `code=0`, `excluded=0`.

The selector removes active cap axial leakage in the diagnostic force term:
legacy cap leakage is about `0.93 m/s2`, while selected cases report `0`.
The selected lateral acceleration is inward and balanced, with a net-force
symmetry residual of order `1e-8`.

Interpretation remains cautious. The pore-pressure response in the selected
cases is large over the very short reduced smoke, so T3 should be treated as
successful infrastructure/diagnostics, not paper-level triaxial validation.
T4 should refine measurement regions, axial/staged loading, and stress-path
postprocessing before MCC. A Zhao renormalized-gradient implementation is a
candidate T4b item if the selected raw-gradient confinement remains too noisy.

## T4 Stress-Path Postprocessing Notes

T4 adds a retained selected-confinement CPU short run under:

`experiments/T4_StressPathPostprocessing/`

The case keeps the T3 selected flexible confinement route and extends the
analysis side:

- five measurement regions;
- framewise pore-pressure and strain proxies;
- `p'` and `q` proxy extraction from the written `Sigma` tensor;
- confinement diagnostics copied from the T3 force log;
- SVG/PNG figures for pore pressure, strain, proxy stress path, `Kplastic`,
  and selector behavior.

The retained run completes with `code=0`, `excluded=0`, and `Kplastic=0`, but
it is not a strict stress-path validation. The current `p'-q` path is a proxy
because the output does not explicitly distinguish total from effective stress
and does not write original positions, material `mk`, or confinement class.

The selected confinement diagnostics remain good: active targets are `112`,
active cap leakage is zero, lateral inward acceleration stays around
`1.87 m/s2`, and force symmetry residual is small. The pore-pressure response
is not yet stable enough for validation. Late-frame pressure reversal and a
large pressure-rate excursion remain in the short dynamic window. T4 therefore
points to T4b Zhao renormalized-gradient confinement and loading/stability
refinement before DP or MCC reproduction work.

## T4b Renormalized Confinement Notes

T4b implemented `ConfiningStressGradientMode`:

- `0`: raw kernel gradient, legacy/default behavior;
- `1`: CPU renormalized/corrected gradient for the flexible confinement pair
  term only.

The implementation is opt-in and leaves the default confinement path unchanged.
Both T4b CPU Release smokes completed with `code=0`, `excluded=0`, and
`Kplastic=0`. The gradient matrix diagnostic reports all `112` active lateral
targets corrected with zero fallbacks.

The numerical result is not validation-ready. In this reduced cylinder the
renormalized gradient increases lateral inward acceleration from about
`1.87 m/s2` to about `3.76 m/s2`, keeps cap leakage at `0`, but worsens
velocity, pressure reversal, and `PorePressRate` excursions. Gentler axial
loading helps only marginally.

T4b therefore redirects the next step away from DP/MCC: first stabilize the
linear-elastic selected-confinement response, likely with a confinement
magnitude limiter, staged equilibration, or smoother loading strategy. Minimal
output enhancement for strict `p'-q` should follow once the reduced response is
smooth enough to measure.

## T4c Loading Stabilization Notes

T4c added three staged-loading CPU Release cases under:

`experiments/T4c_LoadingStabilization/`

The retained gate delays axial loading to `0.0015 s` and lengthens the
confinement ramp to `0.0010 s`. All retained cases complete with `code=0`,
`excluded=0`, and `Kplastic=0`.

The result is diagnostic rather than validating. Cap leakage remains `0`, and
selected lateral confinement remains symmetric, but the pressure reversal still
appears near `0.0014 s`, before axial AccInput starts. Raw staged and raw
staged gentle are nearly identical over the retained window, confirming that
gentler axial loading is not acting on the first instability trigger.

Renormalized staged confinement remains less stable than raw because it
amplifies lateral acceleration. The next step should not be T5 DP or T6 MCC.
First stabilize the confinement-only equilibration stage, possibly through
source-level confinement magnitude normalization, a confinement-stage damping
protocol, or a diagnostic delay/adjustment of pore-pressure Shepard during
confinement equilibration.

## T4d Confinement Equilibration Notes

T4d runs four confinement-only CPU Release variants under:

`experiments/T4d_ConfinementEquilibration/`

There is no axial AccInput in these XML files. The target-p0 feedback-on case
still reverses at about `0.001404 s`, proving that the first instability is
already present during selected-confinement equilibration.

The feedback-on/off comparison is the decisive diagnostic:

- feedback on: max `PorePressRate=3.12e12 Pa/s`, max velocity `215 m/s`,
  `85` DtMin adjustments, reversal present;
- feedback off: max `PorePressRate=2.11e7 Pa/s`, max velocity
  `7.57e-4 m/s`, zero DtMin adjustments, no reversal.

Lowering p0 to `12.5 Pa` reduces lateral acceleration nearly linearly but still
produces reversal and order `1e12 Pa/s` pressure-rate artifacts. A longer ramp
plus `HydromechDampingXi=0.20` delays the all-particle reversal but does not
stabilize the center core.

Source-level confinement magnitude normalization was designed but not
implemented in T4d. The immediate blocker is the active u-pw feedback loop
during confinement equilibration, so T4e should first test staged feedback
gating/delay: ramp confinement with feedback off or delayed, damp to low
velocity/DivVel, then re-enable feedback before adding axial loading. DP and
MCC remain deferred.

## T4e Feedback-Gated Confinement Notes

T4e adds CPU-only feedback timing controls for staged confinement diagnostics:

```xml
<parameter key="PorePressureFeedbackStartTime" value="0.003" />
<parameter key="PorePressureFeedbackRampEndTime" value="0.0045" />
<parameter key="PorePressureFeedbackScale" value="1" />
```

The default start/ramp/scale reproduces the old behavior, so existing cases are
unchanged.

The extended feedback-off confinement-only case remains stable to `0.005 s`
with zero exclusions, zero DtMin adjustments, and no pressure reversal. This is
the useful positive result: selected confinement itself can be equilibrated when
the feedback acceleration is disabled.

Re-enabling feedback remains the failure point:

- abrupt full feedback after `0.003 s`: reversal at `0.004001 s`, `391`
  excluded particles, `469` DtMin adjustments;
- short feedback ramp to `0.0035 s`: reversal at `0.004253 s`, `365`
  excluded particles;
- long feedback ramp to `0.0045 s`: reversal at `0.004503 s`, `164`
  excluded particles;
- long ramp with feedback scale `0.25`: no exclusions or DtMin adjustments,
  but pressure still reverses at `0.005015 s`.

Therefore T4e does not permit axial loading to be restored. The next blocker is
not the axial schedule and not the lateral/cap selector. It is the feedback
acceleration/operator coupling during selected-confinement equilibration.
Potential follow-up should be a narrow feedback relaxation/limiter/operator
audit before DP, MCC, or strict stress-path validation.

## T4f Feedback Stabilization Notes

T4f adds a narrow CPU-only stabilization layer to the feedback acceleration,
not to the PR pressure-rate equation:

```xml
<parameter key="SavePorePressureFeedbackDiagnostics" value="1" />
<parameter key="PorePressureFeedbackRelaxation" value="0.2" />
<parameter key="PorePressureFeedbackLimiterMode" value="3" />
<parameter key="PorePressureFeedbackMaxAccel" value="50" />
<parameter key="PorePressureFeedbackMaxAccelRatio" value="25" />
```

The default values keep legacy behavior. Non-default controls are CPU-only.

The result is useful but not sufficient for validation:

- full feedback without stabilization reproduces T4e instability
  (`excluded=164`, `256` DtMin adjustments, max
  `PorePressRate=1.30e13 Pa/s`);
- relaxation alone still reverses and reaches `3.17e12 Pa/s`;
- cap-only removes DtMin/exclusion but still reverses the center core;
- relaxation plus cap `50 m/s2` / ratio `25` removes DtMin/exclusion and center
  reversal in confinement-only full-feedback scale `1`, reducing max
  `PorePressRate` to about `1.03e9 Pa/s`;
- a stricter cap `10 m/s2` reduces rate and velocity further but reintroduces a
  weak final center reversal;
- gentle axial loading after the best confinement gate still reverses after
  axial onset.

This means the limiter is a diagnostic safety guard, not a physical closure.
Do not enter T5 DP or T6 MCC from this state. The next work should audit the
feedback formulation itself: pressure variable choice, gradient choice,
filtering, and effective-stress coupling consistency.

## T4g Feedback Formulation Audit Notes

T4g audits the feedback operator rather than adding another loading schedule or
cap-only variant. It introduces optional class-aware filtering for feedback
acceleration, with all controls off by default:

- `PorePressureFeedbackUseClassFilter`;
- `PorePressureFeedbackExcludeCaps`;
- `PorePressureFeedbackExcludeEdges`;
- `PorePressureFeedbackExcludeConfinementTargets`;
- `PorePressureFeedbackInteriorOnly`.

The new controls only affect feedback acceleration. They do not change the PR
pressure update, the stress update, flexible confinement, or any Cryer boundary
path. Non-default class filtering is CPU-only; GPU remains deferred and
hard-errors for this diagnostic path.

Manufactured feedback checks show:

- operator `1` is constant-pressure consistent: a uniform pressure field gives
  zero feedback acceleration;
- operator `1` gives the expected down-gradient sign and reasonable magnitude
  for a linear pressure field;
- operator `0` produces a nonzero free-surface response under uniform pressure,
  so it is not the preferred internal pore-pressure feedback operator.

Under `HydraulicElevationSource=0`, total-pressure and excess-pressure mode are
identical in the T4g reduced cases, as expected.

The CPU Release confinement-only matrix confirms that class filtering is useful
but insufficient:

- feedback off remains stable, with max `PorePressRate=2.11e7 Pa/s`;
- operator `1` unfiltered repeats the full-feedback failure
  (`excluded=164`, `256` DtMin adjustments, max `PorePressRate=1.30e13 Pa/s`);
- operator `1` interior-only eliminates exclusions and DtMin adjustments and
  reduces max `PorePressRate` to about `4.79e10 Pa/s`, but pressure reversal
  and negative pressure remain;
- operator `0` variants are not preferred because they fail the uniform-field
  physical consistency check.

The audit finds no clear direct total/effective stress double counting:
`Sigmac` is still treated as a skeleton/effective stress state, and feedback
operator `1` provides the expected `-grad(p_w)/rho` coupling. The remaining
failure is the explicit dynamic feedback formulation near selected confinement,
especially when class filtering is not applied. Do not restore axial loading or
enter DP/MCC yet. T4h should focus on a physically consistent feedback
formulation patch, likely starting from class-filtered operator `1`.

## T4h Corrected Feedback Gradient Notes

T4h implements `PorePressureFeedbackOperator=2`, a CPU-only experimental LSQ
pressure-gradient feedback operator. The local reconstruction solves

```text
p_j - p_i ~= grad(p)_i dot (x_j - x_i)
```

and applies `a_fb=-grad(p)_i/rho_i`. The operator respects
`PorePressureFeedbackMode`, reuses the T4g class filter, and leaves the PR
pressure update untouched. The new LSQ controls are:

- `PorePressureFeedbackLSQRadiusFactor`;
- `PorePressureFeedbackLSQConditionLimit`;
- `PorePressureFeedbackLSQFallback`.

The manufactured tests pass the intended consistency check. Uniform pressure
still gives zero acceleration. For the linear `p=1000 x` field, operator `2`
has machine-precision error while operator `1` has a finite boundary-cloud
gradient error.

The dynamic selected-confinement gate still fails:

- operator `1` interior-only reaches max `PorePressRate=4.79e10 Pa/s` and
  reverses at `0.003821 s`;
- unstabilized operator `2` reaches `5.04e10 Pa/s` and reverses at the same
  time;
- operator `2` plus relax+cap lowers max `PorePressRate` to `4.65e8 Pa/s`, but
  pressure still reverses and local negative pressure remains.

The LSQ systems are well-conditioned in this small test (`407` solved, `0`
fallbacks, condition proxy about `3-4`). That means LSQ consistency alone does
not solve the explicit u-pw feedback instability. Axial loading, DP, and MCC
remain deferred.

## T4i-B Feedback Fidelity Notes

T4i-B pauses limiter/operator tuning and compares the current feedback routes
against the original u-pw implementation notes and Zhao confinement paper.

Key conclusion:

- the u-pw notes place pore pressure in the momentum equation as an isotropic,
  symmetric, stress-like pair term;
- current operator `0` is the closest existing algebraic form;
- operator `0` is still incomplete because it uses a raw separate feedback
  pass and lacks boundary/MLS pore-pressure state completion;
- operators `1` and `2` are gradient estimators, not the paper-style
  stress-pair form;
- Zhao compatibility argues for consistent pair-loop and gradient handling
  across skeleton stress, pore pressure, and confinement.

The selected-confinement failure may also be entangled with missing initial
hydrostatic confinement. Zhao's paper warns that ramping confinement from an
unloaded state can launch stress waves; our T4d/T4e failures occur before axial
loading and are therefore consistent with an unresolved confinement-equilibrium
problem.

Recommended T4j:

1. add an opt-in CPU-only paper-style pore-pressure momentum coupling prototype
   rather than another limiter;
2. gate it with manufactured and closed-support tests;
3. only then retry selected-confinement full feedback;
4. keep DP/MCC and GPU deferred.

## T4j Paper-Style Feedback Notes

T4j implements `PorePressureFeedbackOperator=3`, a CPU-only experimental
paper-style pressure stress-pair route:

```text
a_i^pw = sum_j m_j (p_i+p_j)/(rho_i rho_j) grad W_ij
```

The operator follows the stress-divergence sign convention used by the
paper-style u-pw notes and by the flexible confinement pair term. It still runs
as a separate feedback pass rather than being merged into the skeleton stress
loop, so it is a prototype, not the final total-stress implementation.

Manufactured behavior:

- operators `1/2` remain the clean internal gradient routes for uniform and
  linear pressure fields;
- operator `3` behaves like a stress-pair term and therefore produces a
  free-surface response for uniform pressure on the truncated cylinder cloud;
- this response is expected without boundary pressure completion.

Dynamic selected-confinement results:

- operator `1` interior-only baseline: `code=0`, `excluded=0`, no DtMin burst,
  but reversal remains and max `PorePressRate=4.79e10 Pa/s`;
- operator `3` unfiltered: all particles were excluded and max
  `PorePressRate=1.86e12 Pa/s`;
- operator `3` interior-only: `excluded=55`, `243` DtMin adjustments, max
  `PorePressRate=2.27e12 Pa/s`.

T4j therefore does not unlock axial loading, DP, or MCC. It does strengthen the
diagnosis: a raw paper-style pressure pair needs boundary completion and/or an
initial hydrostatic confinement state. The recommended next stage is T4k
initial hydrostatic confinement, with total-stress coupling left as a later
candidate.

## T4k Initial Hydrostatic Confinement Notes

T4k implements a CPU-only opt-in initial skeleton/effective stress field:

- `InitialStressMode=1`;
- `InitialEffectiveStressIso=50`;
- `InitialEffectiveStressTargetMk=-1`.

`InitialEffectiveStressIso` is a positive compression magnitude in the XML, but
the CPU writes `Sigmac.xx=Sigmac.yy=Sigmac.zz=-InitialEffectiveStressIso`.
This matches the active skeleton/effective stress convention: compressive
elastic strain generates negative `Sigmac`. Pore pressure is not initialized or
modified by this option.

The initialization itself is correct: frame 0 has the requested isotropic
stress and `q=0`. The dynamic result is more instructive:

- initial stress only with feedback off is numerically stable, but all
  particles develop negative pore pressure because the free-surface stress
  state is not externally balanced;
- initial stress plus selected lateral confinement with feedback off remains
  numerically stable and keeps cap leakage at zero, but it is still not a full
  hydrostatic equilibrium because there is no cap/axial confinement;
- delayed full feedback again drives a large `PorePressRate` excursion
  (`~1.59e12 Pa/s`) and high velocities.

Therefore T4k does not unlock axial loading. The next stable-baseline task
should be a staged hydrostatic equilibrium route with cap/axial support or a
restart-based equilibrium stage. DP, MCC, and GPU validation remain deferred.

## T4l Full Hydrostatic Confinement Notes

T4l adds `CapConfiningStress`, a CPU-only opt-in cap-normal support for the
reduced triaxial cylinder. It is meant to complement selected lateral
`FlexibleConfiningStress` during pre-axial hydrostatic staging, not to replace
axial loading.

The source route is deliberately narrow:

- `CapConfiningStressP0` is a positive compression magnitude;
- `CapConfiningStressMode=0` distributes `p0*pi*R^2` over the selected top and
  bottom cap masses;
- top receives `-axis`, bottom receives `+axis`;
- edge-ring particles are skipped to avoid overlap with lateral confinement;
- GPU hard-errors if cap support is enabled.

The feedback-off T4l case shows the feature is doing useful work: final
center-core pore pressure improves from about `-1.10e4 Pa` in the lateral-only
mismatch case to about `-63 Pa` with full cap+lateral support. Cap diagnostics
are symmetric (`18` top and `18` bottom targets, zero symmetry residual).

The gate still fails once delayed full feedback is enabled. The delayed-feedback
case remains `code=0`, `excluded=0`, and has no DtMin burst, but it reaches
`~1.16e12 Pa/s` `PorePressRate`, high velocity, and strong negative pressure.
Therefore axial loading was skipped again. The next triaxial task should refine
hydrostatic equilibrium itself, likely through cap/support distribution,
pressure-boundary completion, or restart-based equilibration. DP and MCC remain
too early.

## T4m All-Surface Confinement Notes

T4m tests the hypothesis that isotropic confinement should first use Zhao's
original all-surface kernel-truncation idea:

- `ConfiningStressUseFiSelector=1`;
- `ConfiningStressUseLateralSelector=0`;
- `CapConfiningStress=0`.

This selects `208` low-`f_i` particles instead of the `112` lateral-only
targets. The active set includes lateral, cap, and edge free-surface regions
through the same pairwise `FlexibleConfiningStress` route.

The result is better than T4l for feedback-off hydrostatic equilibrium:

- final `p'` proxy improves from `38.9 Pa` to `46.4 Pa`;
- final `q` proxy drops from `53.5 Pa` to `15.6 Pa`;
- cap and edge `q` drop sharply;
- max velocity and max `PorePressRate` are slightly lower.

This is strong evidence that the explicit T4l cap force created a cap/edge
transition mismatch. `CapConfiningStress` remains useful as a diagnostic tool,
but all-surface `f_i` confinement is the better isotropic pre-equilibrium route.

Delayed full feedback still fails: max `PorePressRate` reaches `~1.63e12 Pa/s`
with large negative pressure. No axial smoke was run. The next step should be a
staged all-surface-to-lateral selector switch or restart equilibrium design,
but only after treating the full-feedback instability. DP, MCC, and GPU remain
deferred.

## T4n Staged Selector Switch Notes

T4n adds `ConfiningStressLateralSelectorStartTime`, a CPU-only opt-in schedule
for the `FlexibleConfiningStress` target selector. When
`ConfiningStressUseLateralSelector=1` and the start time is positive, the force
uses all low-`f_i` free-surface particles before the start time and lateral-only
particles after it. Defaults preserve the old static selector behavior.

The T4n feedback-off switch case runs with `code=0`, `excluded=0`,
`DtMin=0`, and `Kplastic=0`; active targets switch from `208` to `112`.
However, the switch is not mechanically neutral. Final `q` rises to about
`46 Pa`, final `p'` drops to about `19 Pa`, and center pore pressure becomes
strongly negative again. This means a direct all-surface-to-lateral switch
reintroduces deviatoric imbalance even before feedback is restored.

Delayed feedback after the switch is improved relative to T4m delayed feedback
(`~9.15e9 Pa/s` max `PorePressRate` instead of `~1.63e12 Pa/s`, with no
exclusions or DtMin burst), but it still fails the full-feedback stability
gate with high velocity, negative pressure, and large `q`. Axial loading should
remain disabled. The next step should refine the switch/stress transition or
use a restart/relaxation strategy before considering DP or MCC.

## T4n1 Literature Audit Notes

T4n1 does not run simulations or change source. It audits Zhao, the u-pw
implementation notes, the drained/undrained SPH framework, and the T4k-T4n
results before deciding whether to implement a ramped selector transition.

Classification:

- Reference-supported: initial hydrostatic effective stress, damping during
  confinement equilibration, `f_i` boundary selection, all-surface Zhao
  confinement for isotropic staging, smooth/fan-shaped particle layouts,
  corrected gradients, and Zhao `l0/ln` confinement rescaling.
- Engineering workflow: restart-based equilibrium, delayed feedback activation,
  and staged all-surface-to-lateral confinement. These can organize a stable
  simulation but must be documented as workflow choices.
- Diagnostic only: arbitrary feedback caps, reduced feedback scale without
  physical basis, and selector smoothing used as a final validation device.

Decision: do not make ramped selector transition the next primary source task.
It has no direct Zhao/u-pw basis and mainly smooths a target-set discontinuity.
Prefer a restart-based equilibrium audit: Stage A all-surface `f_i`
confinement with initial stress and damping, then restart into Stage B
lateral-only confinement without axial loading. If restart fidelity is blocked,
a ramped selector can be revisited as a clearly labeled diagnostic protocol.

## T4n2 Restart Equilibrium Audit Notes

T4n2 verifies that restart is not the missing link. The current Part restart
route restores the essential u-pw elastic fields:

- position, velocity, and density through standard Part data;
- `Sigma_kk`, `Sigma_ij`, and `Kplastic`;
- `PorePress`, provided `SavePorePressure=1`.

`ExcessPorePress` is not separately restored, but this is acceptable for the
current `HydraulicElevationSource=0` tests because it equals `PorePress`.
Diagnostic/rate fields such as `PorePressRate`, `DivVel`, and feedback
acceleration are reset and recomputed.

The Stage A all-surface state restarts exactly into Stage B in saved precision.
However, switching the restarted state to lateral-only confinement still drops
the final `p'` proxy to about `13.5 Pa`, increases `q` to about `37.9 Pa`, and
makes all particles negative in pore pressure. Delayed interior feedback after
restart remains unstable (`~1.84e12 Pa/s` max `PorePressRate`).

Conclusion: restart fidelity is adequate, but the all-surface-to-lateral
mechanical transition remains unresolved. Do not reintroduce axial loading,
DP, or MCC yet.

## T4o Cap-Support-Preserving Staging Notes

T4o tests a more mechanically plausible Stage B than the T4n2 lateral-only
restart: after all-surface isotropic confinement, the restart keeps lateral
selected confinement and adds `CapConfiningStress=1` so the top/bottom caps are
not left unsupported.

The hypothesis did not pass. Stage B is numerically clean (`code=0`,
`excluded=0`, `DtMin=0`, `Kplastic=0`) and cap support is symmetric, but the
hydrostatic state is not preserved:

- Stage A final `p' approx 46.38 Pa`, `q approx 15.65 Pa`;
- Stage B final `p' approx 23.87 Pa`, `q approx 61.92 Pa`;
- the Stage B `q` is worse than the T4n2 lateral-only restart (`q approx
  37.89 Pa`);
- all particles are negative in pore pressure by the final Stage B frame.

Delayed feedback after this lateral+cap restart reduces the peak
`PorePressRate` relative to T4n2 Stage C (`9.32e11 Pa/s` vs `1.84e12 Pa/s`),
but it still fails with high velocity, large negative pressure, and very large
`q`. Axial smoke remains disabled.

Conclusion: the all-surface Zhao confinement stage remains the best
feedback-off hydrostatic route, but the current explicit cap-support patch is
not compatible enough with that state to launch axial loading. The next step
should revisit the cap/loading transition formulation rather than enter DP or
MCC.

## T4p Cap / Platen Boundary Notes

T4p does not change source or run new simulations. It audits Zhao's triaxial
cap/platen boundary treatment, the current reduced triaxial XML groups, and
the source mechanisms available for cap/loading support.

Main findings:

- Zhao uses explicit loading platens, not a separate cap-normal acceleration
  patch. The bottom platen is fixed and the top platen is prescribed in
  downward motion.
- The current reduced cases do not yet have clean platen groups. The specimen
  is `mkfluid=0`, the top loading layer is `mkfluid=1`, and there is no
  separate bottom platen mk.
- `AccInput` is a body acceleration applied to the top material layer. It is
  acceptable for early smoke tests but is not a strict prescribed-displacement
  or prescribed-velocity platen.
- `CapConfiningStress` should remain diagnostic-only. T4o showed that it does
  not preserve the all-surface hydrostatic state and can increase the `q`
  imbalance.

Recommended T4q route: build an explicit platen-boundary workflow. The bottom
platen should be fixed, the top platen should use prescribed velocity or
displacement, lateral confinement should remain `FlexibleConfiningStress`, and
platen particles should be excluded from specimen measurements and p-q proxy
statistics. Axial loading, DP, MCC, and GPU validation remain deferred.

## T4q Platen Workflow Notes

T4q uses existing DualSPHysics XML mechanisms instead of adding source:

- fixed `mkbound=2` bottom platen;
- moving `mkbound=1` top platen using `<motion><objreal ref="1">`;
- `mkfluid=0` specimen;
- optional lateral `FlexibleConfiningStress`;
- no `CapConfiningStress`.

The XML-only route is feasible for reduced smokes. Geometry/no-load,
top-velocity/no-confinement, and top-velocity/lateral-confinement cases all
completed with `code=0`, `excluded=0`, `DtMin=0`, and `Kplastic=0`.

Important observations:

- the top platen prescribed velocity is respected;
- the bottom platen remains fixed;
- specimen/platen/measurement separation is clean;
- lateral confinement and moving platen motion can coexist;
- no validated reaction or axial stress output exists yet.

T4q therefore upgrades the triaxial loading route from `AccInput` smoke toward
explicit platens, but it does not yet unlock strict triaxial validation. T4r
should keep the elastic CPU-only route and add/verify reaction diagnostics
before restoring feedback, DP, MCC, or GPU validation.

## T4r Platen Diagnostics Notes

T4r keeps the T4q explicit-platen route and confirms that specimen-only
stress-path postprocessing can be produced without source changes.

Runs:

- `CaseT4r_PlatenAxial_NoConfinement`;
- `CaseT4r_PlatenAxial_LateralConfinement`.

Both runs complete with `code=0`, `excluded=0`, `DtMin=0`, and `Kplastic=0`.
The top moving platen reaches the expected `-7.5e-6 m` displacement over the
short run, while the bottom fixed platen remains at zero displacement.

The current source/output path does not provide true reaction for ordinary
fixed/moving `mkbound` platens. Existing `SaveFtAce` force output is tied to
floating bodies, not this platen route. T4r therefore records a
specimen-stress reaction proxy:

`Fz_proxy = -mean(Sigma_zz) * pi R^2`

Final specimen-wide proxies:

- no lateral confinement: `p' approx 27.94 Pa`, `q approx 43.47 Pa`,
  `Fz_proxy approx 0.1609 N`;
- lateral confinement: `p' approx 49.10 Pa`, `q approx 33.28 Pa`,
  `Fz_proxy approx 0.2015 N`.

The lateral confinement case remains compatible with the moving top platen:
`112` active lateral targets, coherent inward lateral acceleration, and cap
leakage diagnostic `0`.

Interpretation: T4r is good enough to enter a feedback-off platen-based axial
baseline, but not a strict axial-reaction validation. A future opt-in CPU
diagnostic should accumulate true specimen-platen reaction by `mkbound` before
full feedback, DP, MCC, or GPU validation.

## T4s Feedback-Off Platen Axial Baseline Notes

T4s runs the first reduced feedback-off axial baseline using the explicit
platen route:

- `CaseT4s_PlatenAxial_NoConfinement`;
- `CaseT4s_PlatenAxial_LateralConfinement`.

Both CPU Release cases complete with `code=0`, `excluded=0`, `DtMin=0`, and
`Kplastic=0`. The top moving platen reaches `-3.00e-5 m` displacement over the
`0.006 s` window, matching the prescribed `v_z=-0.005 m/s`; the bottom platen
stays fixed.

The specimen/platen/measurement split remains clean:

- specimen particles: `407`;
- top/bottom platen particles: `74 + 74`;
- center measurement core: `15` specimen particles;
- platen contamination: `0`.

The lateral-confinement case remains compatible with the platen route:
`112` active lateral targets, coherent inward lateral acceleration, and cap
leakage diagnostic `0`.

T4s still uses the specimen-stress reaction proxy
`Fz_proxy=-mean(Sigma_zz)*pi*R^2`. Final specimen-wide proxies are:

- no confinement: `p' approx 117.91 Pa`, `q approx 346.17 Pa`,
  `Fz_proxy approx 0.9859 N`;
- lateral confinement: `p' approx 145.66 Pa`, `q approx 332.47 Pa`,
  `Fz_proxy approx 1.0385 N`.

This is clean enough to serve as a reduced feedback-off platen baseline, but
not as strict reaction validation. A true per-`mkbound` reaction diagnostic is
still needed before paper-level axial stress comparison. Full feedback, MCC,
and GPU remain deferred. A reduced T5 DP feedback-off smoke can be considered
only with the reaction-proxy caveat kept explicit.

## T5 DP Feedback-Off Platen Baseline Notes

T5 runs the first DP skeleton baseline on the explicit-platen workflow:

- `CaseT5_DPHighStrength_PlatenLateralConfinement`;
- `CaseT5_DPMildYield_PlatenLateralConfinement`.

Both cases keep `PorePressureFeedback=0`, selected lateral
`FlexibleConfiningStress`, top prescribed platen velocity, and bottom fixed
platen. Both complete with `code=0`, `excluded=0`, `DtMin=0`, and no NaN/Inf
in the retained CSV metrics.

The high-strength case uses `SoilConstitutiveModel=1`, `phi=33 deg`,
`coh=10000 Pa`, `dlt=0`. It remains elastic in practice:

- final `Kplastic` max `0`;
- final specimen-wide `p' approx 145.66 Pa`, `q approx 332.47 Pa`;
- final `Fz_proxy approx 1.0385 N`.

The mild-yield diagnostic uses `phi=30 deg`, `coh=50 Pa`, `dlt=0`. It activates
the DP return mapping without destabilizing the reduced run:

- final `Kplastic` max `4.38e-4`;
- nonzero `Kplastic` count `341/407`;
- final specimen-wide `p' approx 86.58 Pa`, `q approx 126.76 Pa`;
- final `Fz_proxy approx 0.4837 N`.

This confirms that the DP skeleton and `Kplastic` output are usable in the
feedback-off platen workflow. It does not validate full coupling or reaction
forces. The true reaction patch remains a T4t/T5b measurement-fidelity item;
full feedback, MCC, and GPU remain deferred.

## T4t Platen Reaction Diagnostic Notes

T4t implements the first source-level axial reaction diagnostic for the
explicit platen workflow. It is off by default and CPU-only.

New controls:

- `SavePlatenReactionDiagnostics`;
- `PlatenTopMkBound`;
- `PlatenBottomMkBound`;
- `PlatenReactionMode`;
- `PlatenReactionArea`;
- `PlatenReactionInterval`.

`PlatenReactionMode=0` accumulates the opposite of the specimen-side
fluid-bound SPH pair contribution for interactions with the selected top and
bottom `mkbound` platens. This is closer to a true platen reaction than the
old specimen-stress proxy, but it still excludes the prescribed-motion
constraint force. It should be described as a pairwise interaction reaction.

T4t cases:

- `CaseT4t_Elastic_PlatenReaction`;
- `CaseT4t_DPHighStrength_PlatenReaction`;
- `CaseT4t_DPMildYield_PlatenReaction`.

All three CPU Release runs complete with `code=0`, `excluded=0`, and
`DtMin=0`. The elastic and high-strength DP cases remain identical, with
`Kplastic=0`. The mild-yield DP case retains the expected plastic response
(`Kplastic_max approx 4.38e-4`) while staying stable.

Final pairwise reaction averages:

- elastic/high-strength DP: `0.956997 N`, about `92.1%` of the old
  `Fz_proxy`;
- mild-yield DP: `0.492775 N`, about `101.9%` of the old `Fz_proxy`.

T5b may now use reaction-based axial stress as the reduced validation metric.
Full feedback, MCC, and GPU remain deferred.

## T5b DP Feedback-Off Refinement Notes

T5b reruns the explicit-platen DP baseline with T4t pairwise reaction
diagnostics enabled:

- `CaseT5b_Elastic_ReactionRefinement`;
- `CaseT5b_DPHighStrength_ReactionRefinement`;
- `CaseT5b_DPMildYield_ReactionRefinement`.

All three cases are CPU Release, feedback-off, and use selected lateral
`FlexibleConfiningStress`. All complete with `code=0`, `excluded=0`, and
`DtMin=0`.

The elastic and high-strength DP cases are identical over this short window:

- final `Kplastic=0`;
- final specimen-wide `p' approx 145.66 Pa`;
- final `q approx 332.47 Pa`;
- pairwise reaction average `0.956997 N`.

The mild-yield DP case remains stable while activating plasticity:

- final `Kplastic_max approx 4.38e-4`;
- nonzero `Kplastic` count `341/407`;
- final specimen-wide `p' approx 86.58 Pa`;
- final `q approx 126.76 Pa`;
- pairwise reaction average `0.492775 N`;
- mean pore pressure remains bounded at about `1.49e4 Pa`.

T5b makes the reduced DP feedback-off line easier to read because reaction,
axial-stress, `p'-q`, pore-pressure, and plasticity curves are all generated
from the same explicit-platen workflow. It is still not strict paper
validation: full feedback, MCC, true actuator reaction, and GPU remain
deferred.

## T5c DP Extended Feedback-Off Notes

T5c extends the feedback-off DP platen run to `0.018 s`:

- `CaseT5c_DPHighStrength_ExtendedFeedbackOff`;
- `CaseT5c_DPMildYield_ExtendedFeedbackOff`.

Both cases keep explicit platens, selected lateral `FlexibleConfiningStress`,
`SavePlatenReactionDiagnostics=1`, and `PorePressureFeedback=0`. Both complete
with `code=0`, `excluded=0`, and `DtMin=0`.

The high-strength DP case remains elastic-like:

- final `Kplastic=0`;
- final pairwise reaction average `3.2740 N`;
- final `Fz_proxy approx 3.1148 N`;
- final specimen-wide `p' approx 385.80 Pa`, `q approx 1073.74 Pa`.

The mild-yield DP case gives the main extended response:

- final `Kplastic_max approx 1.462e-3`;
- final `Kplastic_mean approx 4.529e-4`;
- plastic count `407/407`;
- final pairwise reaction average `0.4335 N`;
- final `Fz_proxy approx 0.4031 N`;
- final specimen-wide `p' approx 62.23 Pa`, `q approx 120.51 Pa`.

The mild-yield plasticity evolves smoothly at the saved frames and the reaction
remains bounded. The final pore-pressure mean is negative, so T5c should still
be presented as a reduced feedback-off diagnostic rather than strict undrained
validation. T5d can consolidate DP measurement/reporting; MCC should remain
planning-only until the DP reduced route is documented and full feedback is
revisited.

## T5d Reduced Validation Package Notes

T5d packages the existing feedback-off DP platen route. It does not run new
cases. It aggregates:

- T4s elastic platen lateral baseline;
- T4t elastic pairwise reaction diagnostic;
- T5 high-strength and mild-yield DP baselines;
- T5b high-strength and mild-yield reaction refinements;
- T5c high-strength and mild-yield extended responses.

The package makes five main figure candidates:

- reaction-based axial stress vs axial strain;
- p'-q path;
- Kplastic evolution;
- pore pressure vs axial strain;
- pairwise reaction vs `Fz_proxy`.

Supplementary figures cover top platen displacement, lateral active targets,
cap leakage, force-balance error, PorePressRate, DivVel, velocity, and plastic
fraction.

Interpretation boundaries:

- high-strength DP remains an elastic-like reference;
- mild DP activates plasticity and reduces reaction, q, and pore-pressure
  response;
- pairwise reaction and `Fz_proxy` remain close enough for reduced diagnostics;
- mild DP final mean pore pressure can become negative, so this is not strict
  undrained validation;
- full feedback, MCC implementation, true actuator reaction, and GPU remain
  deferred.

MCC planning can begin through an M1 design/audit track, but implementation
should wait for a return-mapping design and single-point tests.

## M1 MCC Design Audit Notes

M1 does not modify source and does not run simulations. It documents the MCC
implementation plan after the T5d reduced DP package.

Main decisions:

- current `Sigmac` is effective/skeleton stress and uses negative compression;
- MCC should use compression-positive internal invariants with
  `p' = -trace(Sigmac)/3`;
- MCC should become `SoilConstitutiveModel=3` only after parser/state/output
  support is added;
- `Kplastic` should remain a compatibility diagnostic, while MCC gets
  explicit state arrays for `p_c`, void ratio or specific volume, plastic
  volumetric strain, and return/yield diagnostics;
- the first implementation task should be M2 single-point return mapping, not
  SPH triaxial.

The first future SPH MCC smoke should be CPU-only, feedback-off, and based on
the explicit-platen T5 route. Full feedback and GPU remain deferred.

## M2 MCC Single-Point Prototype Notes

M2 adds a standalone Python MCC material-point prototype in
`src/papers/u-p/mcc_single_point/`. It is not connected to the solver and does
not add `SoilConstitutiveModel=3`.

Results:

- stress sign regression passes for `Sigmac=(-50,-50,-50) Pa`, mapping to
  internal `p'=+50 Pa`;
- isotropic compression/swelling reaches final `p' approx 194.48 Pa`,
  `q approx 0`, and `p_c approx 194.48 Pa`;
- drained-like path reaches final `p' approx 180.26 Pa`, `q approx 80.55 Pa`,
  and `p_c approx 205.26 Pa`;
- undrained-like zero-volume path reaches final `p' approx 86.22 Pa`,
  `q approx 99.57 Pa`, and `p_c approx 166.07 Pa`;
- plastic-step normalized yield residuals are below about `3e-9`;
- Newton return mapping converges in at most 5 iterations in the retained
  paths.

The elastic predictor is still linear `E,nu`; a `kappa`-based nonlinear elastic
law can be evaluated later. M3 can start CPU integration planning/implementation
from this prototype, but full feedback and GPU remain deferred.

## M3a MCC C++ Helper Notes

M3a ports the M2 material-point MCC model to standalone C++ under
`src/papers/u-p/mcc_single_point/cpp/`.

Important parity checks:

- C++ and Python use the same compression-positive MCC internal convention;
- future SPH mapping remains `p'=-trace(Sigmac)/3` because current `Sigmac`
  uses negative compression;
- isotropic, drained-like, and undrained-like paths have zero retained CSV
  difference in `p'`, `q`, and `p_c`;
- normalized yield residuals and `p_c` hardening match the Python prototype.

M3a still does not touch the SPH solver.

## M3b MCC Parser / State Init Notes

M3b adds only the first production-code infrastructure for MCC:

- `SoilConstitutiveModel=3` parser recognition;
- MCC XML parameter validation;
- CPU MCC state arrays;
- MCC initialization from direct `pc0` or `OCR`;
- `SaveMccState` output fields;
- GPU hard error for model `3`.

It does not connect the MCC return mapping to the stress update. The CPU model
`3` branch logs this explicitly and uses elastic-trial pass-through only for
short parse/init/output smoke tests.

Smoke status:

- direct `pc0=200 Pa`: `code=0`, `excluded=0`, `DtMin=0`;
- `OCR=4` with `InitialEffectiveStressIso=50 Pa`: `code=0`, `excluded=0`,
  `DtMin=0`;
- missing required `MccM` gives a clear parser error.

The initial-stress smoke confirms the sign convention:

```text
Sigmac=(-50,-50,-50) Pa -> p'=+50 Pa -> pc=OCR*p'=200 Pa
```

M3c can now implement the CPU MCC stress-update branch from the verified C++
helper. Full feedback and GPU remain deferred.

## M3c MCC CPU Stress Update Notes

M3c connects `SoilConstitutiveModel=3` to a CPU MCC return-mapping branch while
leaving the existing elastic/DP/DP-softening branches unchanged.

Implementation notes:

- MCC internals remain compression-positive;
- current `Sigmac` remains negative-compression, using
  `p'=-trace(Sigmac)/3`;
- the return mapping follows M3a: local Newton in `p, q, pc, Delta_gamma`;
- `Kplastic` is mapped to `MccEqPlasticStrain` only as a compatibility
  diagnostic;
- GPU still hard-errors for model `3`.

Smoke status:

- high-pc MCC (`pc0=100000 Pa`) is elastic-like: yield fraction `0`, plastic
  strain `0`;
- mild MCC (`pc0=120 Pa`) yields in the short feedback-off platen case:
  final yield fraction `1.0`, `Kplastic_max=7.07e-4`, max return iterations
  `24`, max raw plastic yield residual about `1.13e-4`;
- both cases finish `code=0`, `excluded=0`, `DtMin=0`;
- pore pressure remains bounded, but the mild case has negative mean pore
  pressure, so this is still a reduced feedback-off diagnostic route.

M3d may refine the MCC feedback-off platen smoke. Full feedback and GPU remain
deferred.

## M3d MCC Feedback-Off Refinement Notes

M3d extends the MCC CPU branch to the T5c platen time window without changing
source code.

Results:

- high-pc MCC is stable and elastic-like over `0.018 s`;
- mild-yield MCC activates plasticity in most particles and evolves `pc`, void
  ratio, plastic volumetric strain, and equivalent plastic strain;
- the mild case finishes `code=0`, `excluded=0`, and `DtMin=0`, but the final
  frame includes `MccReturnStatus=-3` for `8/407` particles;
- converged plastic residuals remain small (`~6.4e-5` max at the final frame),
  while failed returns carry large raw residuals and must not be hidden;
- mild MCC produces stronger negative mean pore pressure than the T5c mild DP
  feedback-off case.

This means M3d found the next MCC blocker: local return robustness in the
extended mild-yield path. M3e reporting consolidation should wait for either a
return-robustness fix or an explicit diagnostic-only limitation statement.
Full feedback and GPU remain deferred.

## M3d2 MCC Return Robustness Notes

M3d2 audits the `MccReturnStatus=-3` subset from the M3d mild-yield extended
case without changing source code.

CPU Release diagnostic cases:

- baseline M3d mild-yield rerun;
- half top-platen velocity;
- early stop at `0.006 s`;
- tighter return tolerance (`1e-10`) and higher max iterations (`80`).

All cases finish `code=0`, `excluded=0`, and `DtMin=0`. The persistent final
line-search failure is local, not global: in the baseline final frame the 8
failed particles are split between bottom cap-zone particles at `z≈0.00998 m`
and nearby interior particles at `z≈0.01998 m`. Their final `p'` remains
positive, so the final issue is not direct tension cutoff.

Half velocity clears final `-3` failures, but some intermediate local failures
remain. Higher max iterations/tighter tolerance reproduces the baseline. M3d2
therefore recommends M3d3 opt-in MCC substepping with admissibility guards
before M3e reporting consolidation. Full feedback and GPU remain deferred.

## M3d3 MCC Substepping Notes

M3d3 implements opt-in MCC local constitutive substepping and admissibility
guards for `SoilConstitutiveModel=3` only. Defaults preserve the old M3c/M3d
single-step return behavior.

New controls:

- `MccSubstepping`
- `MccMaxSubsteps`
- `MccSubstepMode`
- `MccSubstepStrainThreshold`
- `MccAdmissibilityGuard`
- `MccFailureFallback`

New `SaveMccState` diagnostics:

- `MccSubstepCount`
- `MccSubstepFailureCount`
- `MccAdmissibilityFailureCount`
- `MccFallbackUsed`

CPU Release diagnostic cases all finish `code=0`, `excluded=0`, `DtMin=0`.
The original-rate fixed/adaptive substepping cases are not clean: they retain
or move local failures into `-3` / `-1` statuses. Adaptive fallback removes
final `-3` but emits explicit `-5` partial-fallback statuses. The half-speed
adaptive case is the cleanest final-frame reduced route:

```text
final ReturnStatus = 0:12 | 1:395
```

M3e can consolidate a reduced feedback-off MCC reporting package only if it
keeps this distinction clear. Full feedback and GPU remain deferred.

## M3e MCC Feedback-Off Package Notes

M3e is a consolidation stage only. It collects:

- M3c high-pc and mild MCC smokes;
- M3d high-pc and mild extended responses;
- M3d2 half-speed, early-stop, and tight-return diagnostics;
- M3d3 baseline, fixed substepping, adaptive substepping, adaptive fallback,
  and half-speed adaptive diagnostics.

All included cases are CPU-only and feedback-off. The consolidated package
keeps the explicit platen workflow, selected lateral confinement, pairwise
reaction diagnostic, and `SaveMccState` outputs.

Main interpretation:

- high-pc MCC is an elastic-like reference;
- mild MCC is a useful yield/state-evolution diagnostic;
- original-rate mild MCC is not clean due to local `ReturnStatus=-3`;
- fallback replaces `-3` with explicit `-5` partial-fallback status, so it is
  not validation;
- half-speed adaptive is the cleanest final-frame reduced route but still does
  not prove original-rate robustness;
- strong negative pore pressure remains a feedback-off limitation.

The recommended technical path is M3f return/staging refinement if clean MCC
validation is the goal. M4 drained/undrained comparison can be planned, but not
claimed as strict validation yet. Full feedback and GPU remain deferred.

## M3f MCC Return/Staging Refinement Notes

M3f adds a targeted MCC-only return/staging diagnostic on top of M3d3. New
opt-in controls and outputs are:

- `MccMinSubsteps`;
- `MccSubstepYieldDistanceThreshold`;
- `MccSubstepTriggerReason`.

`MccSubstepMode=2` now supports proactive local substep counts from a minimum
substep count, approximate strain increment, and normalized trial yield
distance. The new trigger reason is only diagnostic; default behavior remains
unchanged.

M3f cases:

- original-rate mild baseline;
- smoother ramp plus current adaptive retry;
- original-rate improved adaptive mode 2;
- smoother ramp plus improved mode 2;
- half-speed adaptive reference;
- half-speed ramp adaptive reference;
- quarter-speed adaptive diagnostic.

All CPU Release cases finish `code=0`, `excluded=0`, and `DtMin=0`. However,
no clean validation candidate was obtained:

```text
baseline final:                  -3:8
ramp current adaptive final:      -3:5|-1:4
improved adaptive final:          -3:28|-1:19
ramp improved adaptive final:     -3:21|-1:20
half-speed adaptive final:        0:12|1:395
half-speed ramp adaptive final:   0:12|1:395
quarter-speed adaptive final:     0:23|1:384
```

The final frame can be clean at slower rates, but all cases have transient
negative-status episodes in saved frames. Quarter-speed adaptive has the fewest
bad frames, but still does not pass the clean gate.

Failure interpretation:

- failures are local, strongest near edge and bottom/platen-adjacent regions;
- many early failures are admissibility/tension-style `-1`;
- persistent original-rate failures include line-search `-3`;
- smoother ramping does not solve the issue;
- improved adaptive substepping did not clean the tested case.

The next clean-validation step should improve the local admissible Newton path
or platen-region staging. M3g can only be a caveated reporting package unless a
new refinement removes all transient `-3`/`-5` episodes. Full feedback and GPU
remain deferred.

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

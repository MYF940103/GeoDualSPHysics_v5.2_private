# Softening Model Gap Decision

Date: 2026-05-11

## Decision Summary

The current CPU `Softening=1` implementation should be kept as a reduced
Drucker-Prager approximation for qualitative smoke tests. It is useful and now
validated for short CPU checks, but it should not be treated as the complete
sensitive-clay / remolding / retrogressive landslide formulation from the u-pw
paper.

Recommended route:

1. Keep current `Softening=1` as the reduced approximation for 05/06 scaffolds.
2. Defer a fuller sensitive-clay/remolding/destructuration material model.
3. Do not include softening in GPU G1.
4. Plan GPU material softening later as a separate phase after passive PR core
   GPU plumbing is stable.

## 1. What The Current DP-Based Kplastic Softening Covers

The implemented CPU model covers reduced qualitative tests where the goal is to
verify execution plumbing rather than reproduce field-scale landslide behavior:

- short reduced slope smoke tests with PR pore-pressure fields enabled;
- material-path activation checks through nonzero `Kplastic`;
- peak-to-residual strength degradation in a Drucker-Prager return-mapping path;
- postprocessing of approximate local cohesion and friction angle from
  `Kplastic`;
- comparison of `Softening=0` and `Softening=1` cases in the same reduced
  geometry;
- guard checks that residual strength remains bounded and no NaN/Inf or
  excluded particles appear in short smokes.

The implemented law is:

```text
c(kappa)   = c_r   + (c_p   - c_r)   * exp(-n_coh * kappa)
phi(kappa) = phi_r + (phi_p - phi_r) * exp(-n_phi * kappa)
kappa      = Kplastic
```

This is enough for reduced smoke tests such as:

- `examples/u-pw/05_Retrogressive_Slope/experiments/SofteningMicro/`;
- `CaseRetrogressiveSlope_PR_SofteningSmoke_Def.xml`;
- future tiny qualitative slope or field-like checks that need the material
  branch to activate.

Observed CPU smoke evidence:

- softening micro trigger: `Kplastic_max = 8.5393706e-4`, estimated cohesion
  decreased from `1 Pa` to `0.8587 Pa`;
- reduced slope softening smoke: `Kplastic_max = 6.5801572e-4`, estimated
  cohesion decreased from `151 Pa` to `150.553 Pa`;
- GenCase and DualSPHysics both returned `code=0`, `excluded=0`, with no
  NaN/Inf in the tested smokes.

## 2. Differences From The Paper Sensitive-Clay / Retrogressive Formulation

The current implementation follows the paper-style exponential peak-to-residual
strength law, but the full retrogressive landslide formulation likely involves
more than this reduced DP material switch.

Known or likely differences:

- The current model uses only the existing `Kplastic` scalar as the softening
  driver. The paper's field-scale behavior may require accumulated plastic
  shear strain, remolding degree, destructuration, or another history variable
  tied more directly to sensitive-clay degradation.
- The current model has no explicit sensitivity variable `St = peak/remolded`
  beyond the implicit peak/residual strength ratio.
- There is no separate remolded-strength state, rate of remolding, or recovery
  variable.
- There is no bonding/destructuration variable controlling stiffness or yield
  surface shape.
- There is no strain-rate dependence.
- There is no localization regularization beyond the existing SPH smoothing and
  numerical stabilization choices.
- The current reduced slope smoke deliberately scales cohesion down to trigger
  plasticity in a short run; it is not calibrated to the paper slope or
  Sainte-Monique field values.
- The current model does not construct the paper's initial effective stress,
  pore pressure, `K0=0.5` state, or strength-reduction workflow.
- The current model is CPU-only and not available in GPU stress-update kernels.

Therefore, `Softening=1` is best described as a DP-based reduced approximation,
not a complete sensitive-clay remolding model.

## 3. Extra State Variables Needed For Strict Retrogressive Reproduction

A stricter reproduction may need additional particle state beyond `Kplastic`.
Candidate variables include:

| Variable | Purpose | Why `Kplastic` alone may be insufficient |
|---|---|---|
| Accumulated plastic shear strain | Direct softening driver for sensitive clay shear degradation. | `Kplastic` is equivalent deviatoric plastic strain, but paper calibration may use a different measure. |
| Remolding index / destructuration variable | Tracks transition from intact to remolded material. | Allows strength and possibly stiffness to depend on clay structure, not only instantaneous plastic strain. |
| Sensitivity or remolded strength ratio | Stores or computes `s_u,peak / s_u,remolded`. | Needed for material zoning or spatially varying sensitivity. |
| Local remolded cohesion / friction | Stores final degraded strength target if it varies by zone. | Current implementation assumes global soil constants. |
| Softening factor / strength ratio | Diagnostic or state for output and restart. | Helpful for slope failure visualization and debugging. |
| Accumulated volumetric plastic strain | If the final material model couples volumetric plasticity to strength or pore response. | Current reduced path only uses deviatoric-equivalent `Kplastic`. |
| Strain-rate measure | Needed only if the final paper/field calibration includes rate effects. | Current implementation is rate independent. |
| Bonding/destructuration state | Needed if stiffness/yield surface evolves with clay structure. | Current implementation only changes `c` and `phi`. |

Not all variables should be added immediately. A strict model design should first
confirm the exact paper/field constitutive law and calibration needs.

## 4. Impact On CPU Arrays, Restart, Output, And GPU Arrays

If fuller sensitive-clay state variables are introduced, each one becomes a
particle history variable and affects several subsystems.

CPU arrays:

- add persistent per-particle arrays for any new history variable;
- initialize them from soil material constants or initial-state preprocessing;
- copy them during sorting and periodic duplicate handling;
- update them inside the CPU stress integration path;
- keep default behavior unchanged when the fuller model is disabled.

Restart:

- write new state variables to `Part_XXXX.bi4`;
- read them in `JPartsLoad4`;
- restore by `Idp` mapping in CPU restart;
- define fallback behavior for old restart files without the new fields.

Output:

- expose at least one diagnostic field such as `SofteningFactor`,
  `RemoldingIndex`, or reconstructed local strength;
- retain `Kplastic` as a common diagnostic;
- update postprocessors for slope and Sainte-Monique failure metrics.

GPU arrays:

- allocate/free/resize/sort/duplicate each new state variable;
- add restart/output parity if GPU restart is later supported;
- update GPU stress kernels to use the same material law;
- add CPU/GPU one-step parity tests before production runs.

These are material-state changes, not passive pore-pressure storage changes.
They should not be folded into GPU G1.

## 5. Should A Fuller Model Be Implemented Before GPU G1?

Recommendation: no.

Reasons:

- GPU G1 is intended to be passive `PorePressg` plumbing only, not a full GPU PR
  or material-model port.
- The current CPU reduced softening path is sufficient for reduced qualitative
  case 05 smoke tests.
- A fuller sensitive-clay model would require new state variables, restart,
  output, CPU validation, and later GPU material kernels. That is a separate
  material-model phase.
- Implementing a fuller model before passive GPU storage would expand the scope
  and delay PR core GPU parity without improving the passive G1 objective.

Thus, fuller softening should not block GPU G1 if G1 remains narrowly scoped to
passive pore-pressure storage and output parity.

## 6. Can Fuller Softening Be Deferred Until After GPU PR Core?

Yes, with one caveat.

It is reasonable to defer the fuller sensitive-clay/remolding model until after
GPU PR core plumbing, provided that the project does not claim strict 05/06
paper reproduction before that material branch exists.

Suggested staging:

1. Finish CPU reduced softening documentation and keep `Softening=1` available.
2. If authorized, implement GPU G1 passive `PorePressg` only.
3. Continue GPU PR core phases separately: pressure rate, update, output parity,
   then feedback/stabilization as planned.
4. Design GPU/CPU material softening as its own phase once PR core arrays and
   stress-update GPU scope are clear.
5. Only then attempt production retrogressive slope or Sainte-Monique runs.

## 7. Recommended Route

### Current `Softening=1`

Keep it.

Use it as:

- a reduced DP-based sensitive-clay approximation;
- a CPU smoke-test tool for 05 reduced slope and future 06 placeholder checks;
- a way to verify `Kplastic`-driven strength degradation and postprocessing.

Do not use it as proof of strict retrogressive reproduction.

### Strict Sensitive-Clay Model

Defer it.

Before implementing, write a dedicated design document that answers:

- exact softening/remolding state variables;
- calibration from paper or field tables;
- relationship between accumulated shear strain, `Kplastic`, remolding, and
  residual strength;
- output and restart field requirements;
- CPU/GPU parity tests.

### GPU G1

Do not include softening.

Allowed G1 scope remains:

- passive `PorePressg` allocation/free/resize;
- sorting and periodic duplicate support for pore pressure;
- output of `PorePress` and `ExcessPorePress`;
- one-frame parity checks.

Forbidden in G1:

- GPU softening;
- GPU stress update changes;
- GPU PR rate;
- GPU feedback;
- GPU Shepard/damping;
- GPU boundary ghost.

### Later GPU Material Softening Phase

Plan as a separate phase after PR core GPU plumbing. That phase should include:

- GPU material constants for peak/residual strength and softening coefficients;
- GPU access to `Kplastic` or any new remolding variables;
- stress-update kernel changes;
- output/restart support for new state variables;
- CPU/GPU parity tests for micro material paths;
- reduced 05 slope softening parity before field-scale runs.

## Final Decision

The CPU reduced DP-based `Softening=1` path is accepted as the current reduced
approximation. It covers qualitative smoke and execution-path validation for
retrogressive-slope scaffolds.

Strict sensitive-clay/remolding/destructuration remains deferred. It is not a
GPU G1 requirement and should be handled later as a dedicated CPU/GPU material
model phase.

# T4o Cap-Support-Preserving Staged Design

## Stage A: All-Surface Isotropic Equilibrium

Stage A uses the T4m/T4n2 all-surface equilibrium route:

- `InitialStressMode=1`;
- `InitialEffectiveStressIso=50`;
- `FlexibleConfiningStress=1`;
- `ConfiningStressUseFiSelector=1`;
- `ConfiningStressUseLateralSelector=0`;
- `CapConfiningStress=0`;
- `PorePressureFeedback=0`;
- no axial loading.

This stage keeps the original Zhao-style idea: low-`f_i` free-surface particles
on the lateral surface, caps, and edge ring all receive the same confinement
mechanism. The Stage A target is a low-velocity, low-`q`, feedback-off
hydrostatic state.

## Stage B: Restart With Lateral Confinement And Cap Support

Stage B restarts from Stage A `Part_0023` and changes only the support model:

- `ConfiningStressUseFiSelector=1`;
- `ConfiningStressUseLateralSelector=1`;
- `CapConfiningStress=1`;
- `CapConfiningStressP0=50`;
- `PorePressureFeedback=0`;
- no axial loading.

The intended interpretation is that the specimen leaves isotropic
pre-equilibrium and enters a triaxial-style support state:

- lateral confinement is retained on the cylindrical side wall;
- cap normal support balances the axial hydrostatic component;
- no deviatoric axial loading is added yet.

The Stage B gate checks whether this support change keeps `p'` near the target
and keeps `q` close to the Stage A level.

## Stage C: Delayed Feedback

Stage C is only a feedback gate:

- restart from the same Stage A state;
- use the Stage B lateral+cap support model;
- enable delayed/ramped `PorePressureFeedback`;
- no axial loading.

This tests whether cap-support-preserving confinement improves the
full-feedback instability seen in T4n2.

## Stage D: Axial Smoke

Stage D is allowed only if Stage C is stable:

- lateral confinement and cap support remain active;
- axial `AccInput` starts after the confined feedback-on state is stable;
- the run remains very short.

If Stage C fails, Stage D is skipped.

## Metrics

The T4o workflow records:

- restart continuity;
- active lateral target count;
- cap target count and cap acceleration;
- lateral flexible confinement acceleration;
- `p'` and `q` proxies;
- region-wise `q` for interior, lateral, top cap, bottom cap, and edge;
- `PorePress`, negative pressure count, and reversal indicator;
- `PorePressRate`, `DivVel`, velocity, and DtMin adjustments;
- feedback acceleration if enabled.

## Gate Criteria

T4o passes only if:

- `code=0`, `excluded=0`, `Kplastic=0`;
- Stage B final `q` is close to Stage A or clearly below the T4n2
  lateral-only restart;
- Stage B keeps `p'` close to the target confinement;
- velocity, `DivVel`, and `PorePressRate` remain controlled;
- no strong negative pressure or pressure reversal develops;
- Stage C delayed feedback is improved enough to avoid the feedback runaway;
- only then is axial loading restored.

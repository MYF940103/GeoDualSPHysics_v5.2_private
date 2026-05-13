# M1 MCC SPH Integration Plan

## Integration Point

The future MCC branch should be inserted into `ApplySoilConstitutiveModelCpu` as:

```text
SoilConstitutiveModel=3
```

It should consume the current elastic trial stress `sigma_e`, convert to compression-positive MCC invariants, apply the local MCC return mapping, and return an updated stored-sign `Sigmac`.

## Implementation Phases

### Phase 1: Shared MCC Helper

Create a CPU helper that can be called by both:

- standalone single-point tests;
- the SPH constitutive dispatch.

The helper should take stress, MCC state, elastic constants/MCC parameters, and return updated stress and state.

### Phase 2: Parser and State Allocation

Extend:

- `StSoilCte` for MCC material constants;
- parser validation for `SoilConstitutiveModel=3`;
- CPU arrays for MCC state;
- output and restart arrays.

GPU should hard-error for model `3`.

### Phase 3: CPU Single-Point Parity

Before SPH, run the C++ helper through single-point tests and compare to the Python reference.

### Phase 4: First SPH Smoke

The first SPH MCC test should reuse the stable reduced T5 workflow:

- explicit top/bottom platens;
- selected lateral `FlexibleConfiningStress`;
- `PorePressureFeedback=0`;
- CPU Release only;
- no GPU;
- no full feedback;
- short run.

Start with an overconsolidated/high `p_c` elastic-like MCC case, then a mild-yield MCC case.

### Phase 5: SPH Output and Restart Gate

Verify:

- `MccPc` restart continuity;
- void ratio/specific volume restart continuity;
- plastic volumetric strain continuity;
- `Sigmac` continuity;
- `PorePress` continuity if hydromechanics is active.

Do not start longer SPH MCC runs until staged restart works.

## Drained and Undrained Development

After reduced feedback-off smokes:

1. design drained boundary conditions and pressure state;
2. design undrained tests with a clearly scoped pore-pressure interpretation;
3. revisit full feedback only after MCC local behavior and platen workflow are stable.

## GPU Plan

GPU implementation is deferred until:

- CPU single-point tests pass;
- CPU SPH smoke passes;
- MCC state output/restart is stable;
- full feedback status is decided.

GPU will require device arrays, sorting, restart/output integration, and a device return mapping mirroring CPU behavior.

## First SPH MCC Test Recommendation

Use:

```text
examples/u-pw/04_Undrained_Triaxial/experiments/T5b_DPFeedbackOffRefinement/
```

as the structural template, replacing DP with MCC only after the single-point helper is verified. Keep the reaction diagnostic and feedback-off caveat from T4t/T5.

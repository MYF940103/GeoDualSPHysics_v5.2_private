# TINT1 Pore-Pressure Time-Integration Audit Report

Date: 2026-05-14

## Objective

TINT1 audits where the PR pore-pressure scalar update sits inside the
DualSPHysics Verlet/Symplectic stepping schemes. It is motivated by the BND1
result: generalized boundary operator `2` is physically broader, but its
feedback-on case is unstable. Before tuning the boundary operator further, the
pressure time stage needs to be understood.

No source changes and no simulations were performed in TINT1.

## Current Update Stage

The current CPU pressure update is:

```cpp
porepress[p1] += double(porepressrate[p1]) * dt;
```

defined in `source/JSphCpu.cpp:2228`.

In CPU Verlet:

```text
Interaction_Forces -> DtVariable -> UpdatePorePressure -> ComputeVerlet
```

The call is at `source/JSphCpuSingle.cpp:1157`.

In CPU Symplectic:

```text
predictor Interaction_Forces -> ComputeSymplecticPre
corrector Interaction_Forces -> UpdatePorePressure -> ComputeSymplecticCorr
```

The call is at `source/JSphCpuSingle.cpp:1214`.

GPU follows the same broad placement:

- Verlet update at `source/JSphGpuSingle.cpp:638`;
- Symplectic update at `source/JSphGpuSingle.cpp:694`.

## Time Layer of `PorePressRate`

`PorePressRate` is computed inside `Interaction_Forces()`.

CPU call sequence:

- `ComputeHydroDivVel()`;
- `ComputeHydroLapPorePress()`;
- `ComputeHydroLapZ()`;
- optional `ApplyPorePressureBoundaryOperator()`;
- feedback acceleration computation and application;
- `ComputeHydroPorePressRatePR()`.

The rate depends on:

- current stage `Posc`;
- current stage `Velrhopc`;
- current `Codec`;
- current `PorePressc`;
- current boundary contributions to `LapPorePress` and `LapZ`;
- `DivVelc`.

In Verlet these are pre-Verlet variables. In Symplectic corrector they are
predicted mechanical variables, but the pressure is still old because there is
no pressure predictor.

## Time Layer of Feedback Acceleration

Feedback acceleration is computed from `PorePressc` during the same interaction
stage and applied to `Acec` before the mechanical step/corrector. The pressure
just produced by `UpdatePorePressure()` is not used by the same mechanical
update. It affects feedback at the next interaction.

This means the feedback route is lagged:

```text
Ace_feedback^stage = A(p_old, x_stage, rho_stage)
p_new = p_old + dt * R(p_old, v_stage, x_stage)
mechanical update uses Ace_feedback^stage
```

## Consistency With Verlet/Symplectic

The current route is consistent as a first-order explicit operator split. It
is not a time-centered Verlet or Symplectic pressure integration.

Pore pressure is currently:

- not density-like, because it does not use the same predictor/corrector
  update as `Rhop`;
- not stress-like, because it is not updated inside the mechanical stepper with
  stress rates;
- acceleration-coupled, because old pressure contributes to momentum feedback
  before the scalar pressure update.

The largest staging mismatch is in Symplectic:

- corrector `DivVel` comes from predicted mechanical state;
- `LapPorePress` comes from old pressure;
- feedback acceleration comes from old pressure;
- updated pressure is written before `ComputeSymplecticCorr()` but not used by
  its acceleration.

## Relation to BND1 Mode 2 Instability

The audit cannot prove that time staging caused the BND1 mode `2` feedback-on
failure. It does show a plausible amplification path:

1. generalized mode `2` adds ordinary solid-wall boundary contributions to
   `LapPorePress` and `LapZ`;
2. these contributions enter an explicit pressure update;
3. feedback acceleration is based on old pressure and current predicted
   mechanics;
4. the updated pressure is not synchronized with the same mechanical corrector;
5. boundary-induced pressure-rate spikes can therefore interact with feedback
   one step later.

This makes it premature to tune mode `2` further before a pressure time-stage
experiment is available.

## Experimental Mode Decision

No `PorePressureTimeIntegrationMode` was implemented in TINT1.

Reason:

- moving the update safely touches both `ComputeStep_Ver()` and
  `ComputeStep_Sym()`;
- the post-update ordering of Shepard, top drained, bottom no-flux, and curved
  clamps differs between CPU and GPU;
- an end-of-step or split-lagged mode needs a clearly scoped TINT2 patch and
  verification matrix.

Default behavior is unchanged.

## Recommended Next Step

Before continuing BND2 or a landslide baseline, implement a CPU-only TINT2
experimental mode:

```text
PorePressureTimeIntegrationMode=1
```

Recommended semantics:

- mode `0`: current behavior;
- mode `1`: end-of-step split update using the existing rate;
- mode `2`: reserved for recomputed end-of-step hydraulic operators;
- GPU hard error for nonzero modes until a CPU route passes.

Verification order:

1. L3c feedback-off, operator `1`;
2. L5 feedback-on, operator `1`;
3. BND1 generalized mode `2` feedback-off;
4. BND1 generalized mode `2` feedback-on only if earlier checks pass.

## Answers to TINT1 Questions

1. Current `UpdatePorePressure` stage: after interaction and before the
   mechanical update in Verlet; after corrector interaction and before the
   corrector update in Symplectic.
2. Current time-layer consistency: it is not synchronized with
   velocity/density/stress predictor-corrector staging; it is an explicit split
   scalar update.
3. Stage mismatch risk: yes, especially for feedback-on and generalized
   boundary operator cases.
4. Experimental mode implemented: no.
5. L3c/L5/BND1 improvement: not tested in TINT1 because no source experiment
   was implemented.
6. Explanation of mode `2` instability: time-stage mismatch is a plausible
   contributor, not the sole proven cause.
7. Next priority: fix/test pore-pressure time integration before continuing
   boundary mode `2`.
8. Landslide baseline: keep deferred until a CPU time-stage decision is made,
   or proceed only with operator `1` and strong caveats if project priority
   demands it.
9. GPU: any new time-integration mode must be CPU-first and later synchronized
   to GPU only after CPU validation.


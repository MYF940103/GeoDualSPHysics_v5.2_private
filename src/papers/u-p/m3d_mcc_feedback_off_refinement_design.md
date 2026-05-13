# M3d MCC Feedback-Off Refinement Design

## Objective

M3d extends the M3c MCC CPU stress-update smoke cases from `0.006 s` to
`0.018 s`, matching the T5c DP extended window. The goal is to check whether
the CPU MCC branch remains stable in a reduced explicit-platen triaxial
workflow with `PorePressureFeedback=0`.

This stage is still a reduced diagnostic benchmark. It is not a strict MCC
paper reproduction and does not validate full u-pw feedback.

## Why Feedback Remains Off

The full pore-pressure feedback loop remains unresolved in the selected
confinement route. Keeping `PorePressureFeedback=0` isolates the MCC skeleton
stress update and the PR pressure update from the unstable feedback
acceleration path. This lets M3d test whether the MCC state variables and local
return mapping are stable before reintroducing stronger hydromechanical
coupling.

## Cases

### Case 1: MCC High-pc Extended

- `SoilConstitutiveModel=3`
- `MccInitialPreconsolidationPressure=100000 Pa`
- `PorePressureFeedback=0`
- explicit top platen prescribed velocity
- bottom platen fixed
- lateral `FlexibleConfiningStress` selected confinement
- `SaveMccState=1`
- `SavePlatenReactionDiagnostics=1`
- `TimeMax=0.018 s`

This case is an elastic-like MCC reference. With a very large initial
preconsolidation pressure, the yield surface should remain far from the stress
path and MCC plastic variables should remain inactive.

### Case 2: MCC Mild-yield Extended

- `SoilConstitutiveModel=3`
- `MccInitialPreconsolidationPressure=120 Pa`
- same platen and confinement setup
- `PorePressureFeedback=0`
- `TimeMax=0.018 s`

This case checks plastic activation, `pc` evolution, void-ratio evolution,
plastic volumetric strain, equivalent plastic strain, return status, iteration
count, and yield residual over the longer T5c time window.

## T5c DP Comparison

M3d compares the MCC high-pc and mild-yield cases against the T5c DP
feedback-off extended cases:

- reaction-based axial stress vs axial strain;
- `p'-q` path;
- pore pressure vs axial strain;
- plasticity indicators;
- pairwise reaction vs `Fz_proxy`.

The comparison is qualitative because MCC and DP use different yield surfaces
and hardening laws.

## MCC Metrics

The required MCC checks are:

- `MccPc` min/mean/max;
- `MccVoidRatio` min/mean/max;
- `MccPlasticVolStrain` min/mean/max;
- `MccEqPlasticStrain` max/mean;
- `MccYieldFlag` count/fraction;
- `MccPlasticMultiplier` max/mean;
- `MccReturnStatus` counts;
- `MccReturnIterations` max/mean;
- `MccYieldResidual` max/mean/maxAbs;
- converged-plastic residual excluding elastic yield margin and failed returns.

## No-go Criteria

M3d should not be treated as a pass if any of the following occur:

- `excluded > 0`;
- `DtMin` burst;
- local MCC return non-convergence;
- negative or nonphysical `pc`;
- nonphysical void ratio;
- runaway `p' <= tension cutoff`;
- pore-pressure runaway;
- strong reaction-force oscillation.

If local return failures are present, M3d can still be useful as a diagnostic
stage, but M3e validation-package consolidation should wait for a return
robustness follow-up.

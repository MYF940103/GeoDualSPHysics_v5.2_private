# T4l Full Hydrostatic Confinement Design

## Design Objective

T4l tests whether the reduced triaxial specimen can hold an initially
hydrostatic effective stress state before any axial loading. The target state is
not a DP/MCC validation; it is a linear-elastic u-pw equilibrium gate.

The required balance is:

```text
sigma'_xx = sigma'_yy = sigma'_zz = -sigma_c
```

using the current code convention where compressive skeleton/effective stress
is negative. The XML still gives `InitialEffectiveStressIso` as a positive
compression magnitude.

## Candidate Routes

### Route 1: Lateral Confinement + Fixed Caps

This is close to T4k. Lateral `FlexibleConfiningStress` is selected cleanly, but
top and bottom caps do not receive an equal hydrostatic normal support.

Result from T4k: numerically stable with feedback off, but the free-surface
release generates negative pore pressure and delayed full feedback remains
unstable. This route is insufficient.

### Route 2: Lateral Confinement + Cap Normal Support

This is the T4l route. Lateral support remains with Zhao-style selected
`FlexibleConfiningStress`, while top/bottom support is added as a separate
cap-normal pressure-force route.

Expected advantages:

- matches all three hydrostatic stress directions at the external boundary;
- keeps cap support separate from axial deviatoric loading;
- keeps the T3 lateral selector and cap leakage diagnostics intact;
- avoids using edge-ring particles twice.

Limitations:

- it is a reduced cap acceleration support, not a rigid platen or full pressure
  boundary formulation;
- cap support is not written into stress;
- feedback and PR pressure dynamics still need their own equilibrium gate.

### Route 3: Initial Stress Only + Damping Relaxation

This can diagnose stress-release behavior, but it is not a strict triaxial
confinement state because no external traction balances the initialized stress.
It should not be the validation route.

### Route 4: Restart-Based Hydrostatic Equilibrium

Stage A would equilibrate confinement, save a restart, and Stage B would begin
axial loading from the equilibrated state. This is closer to a laboratory
workflow, but it should come after the single-run cap-support gate is understood.

## Implemented T4l Route

T4l implements Route 2 with `CapConfiningStressMode=0`:

```text
F_cap = p0_eff * pi * R^2
a_top    = -axis * F_cap / M_top
a_bottom = +axis * F_cap / M_bottom
```

where `M_top` and `M_bottom` are the selected cap particle masses. The pressure
ramp uses the same positive-compression convention as lateral confinement.

## Gate Logic

The gate is deliberately staged:

1. reproduce the T4k mismatch with lateral-only support and feedback off;
2. enable full cap+lateral hydrostatic support with feedback off;
3. re-enable delayed feedback only if the feedback-off state is improved;
4. restore axial loading only if full-feedback confinement remains stable.

Axial loading is not allowed to start from a failed feedback-on confinement-only
state.

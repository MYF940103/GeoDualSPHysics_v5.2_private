# M4 MCC Drained and Undrained Comparison Planning Stub

## Purpose

M4 is a planning stage for future MCC drained/undrained comparisons. It should
not begin strict comparison runs until the M3f return/staging issue is either
fixed or explicitly scoped as a reduced diagnostic limitation.

## Drained MCC Needs

A drained MCC triaxial comparison needs:

- clean MCC return behavior under platen loading;
- reliable axial reaction or a clearly documented reaction proxy;
- lateral confinement control;
- pore-pressure boundary/drainage assumptions documented;
- specimen-only stress and strain measures;
- output of `pc`, void ratio, plastic volumetric strain, and plastic shear
  measure;
- comparison against expected drained p'-q and volume-change behavior.

## Undrained MCC Needs

A strict undrained MCC comparison needs more than the current feedback-off
route:

- full or physically justified u-pw coupling;
- controlled pore-pressure feedback or a validated equivalent;
- bounded pore pressure without reduced-route caveats;
- clear total/effective stress accounting;
- specimen-only p'-q and pore-pressure response;
- verification against expected undrained stress path and pore-pressure
  generation.

The current feedback-off route is not a full undrained MCC validation because
the pore-pressure feedback path is disabled and mild MCC can produce strong
negative mean pore pressure.

## Role of Full Feedback

Full feedback remains a separate blocker. It should not be enabled in M4 until
the feedback coupling and staging route is revisited. For planning, M4 can
define expected drained/undrained outputs and acceptance criteria, but should
not claim strict undrained reproduction.

## Output and Reaction Requirements

Minimum output requirements:

- pairwise platen reaction and/or true actuator reaction if later available;
- axial stress-strain curve;
- p'-q path;
- `pc` evolution;
- void ratio evolution;
- plastic volumetric strain;
- equivalent plastic strain;
- pore pressure and `PorePressRate`;
- return status and residual diagnostics.

## Expected Stress Paths

Planning expectations:

- high-pc MCC should remain elastic-like over small strains;
- mild-yield MCC should reach the MCC yield surface and harden smoothly;
- drained paths should show volume-change response through void ratio;
- undrained paths should require physically consistent pore-pressure coupling.

## GPU Status

GPU remains deferred. `SoilConstitutiveModel=3` intentionally hard-errors on
GPU because there is no GPU MCC return mapping, state update, restart support,
or validation route.

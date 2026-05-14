# L4-L5 Strict 1D Consolidation Reproduction Definition

Date: 2026-05-14

## Objective

This note defines what "strict 1D consolidation reproduction" means for the
u-pw Terzaghi consolidation chain. It separates the validation target into
three levels so that L4 and L5 do not blur a clean diffusion gate with the
harder mechanical load-generation problem.

## Level 1: PR Diffusion And Boundary Gate

Level 1 validates the pressure initial-value problem:

- initialize excess pore pressure as `p_w0=|q0|`;
- apply top drained pressure boundary;
- apply bottom and lateral no-flux behavior;
- compare pore-pressure decay and profiles against the Terzaghi analytical
  solution;
- check CPU/GPU parity for the PR pressure update and hydraulic boundaries.

This is the layer covered by L3a/L3c and proposed L4.

L3c is currently the cleanest Level-1 route:

```text
PorePressureInit=3
PorePressureExcessAmp=10000 Pa
InitialStressMode=0
PorePressureFeedback=0
AccInput disabled
MechanicalTopLoad disabled
```

Level 1 is paper-compatible for the Terzaghi initial-state diffusion problem,
but it is not the full mechanical loading reproduction. It deliberately
represents the instantaneous undrained loading state directly rather than
generating it through a top surcharge.

## Level 2: Mechanical Loading Generation

Level 2 validates the process by which the top surcharge `q0=-10 kPa` creates
the initial undrained excess pore pressure. This requires one of the following
paper-faithful routes:

- force-controlled loading plate;
- true surface traction boundary;
- consistent total/effective stress plus pore-pressure initialization;
- quasi-static equilibration before drainage.

The main requirement is that the route generates the intended `10 kPa`
pressure scale without dynamic waves dominating the pressure response.

L2 and L3b have not passed Level 2:

- L2 maps `q0` to `AccInput` on a top material layer, which is a body
  acceleration rather than a surface traction;
- L3b distributes `q0*A` directly to top material particles, but it still
  behaves like an impulsive material-surface force;
- both routes generate excess-pressure peaks near `6e5 Pa`, far above the
  analytical `10 kPa` scale.

## Level 3: Fully Coupled Hydromechanical Validation

Level 3 validates the full coupled consolidation process:

- effective stress and pore pressure evolve together;
- pore-pressure feedback or an equivalent stress-coupling route is active;
- the skeleton response remains quasi-static;
- the same setup recovers Terzaghi pressure decay without artificial dynamic
  peaks;
- CPU/GPU parity is eventually established for the coupled path.

This layer is not validated yet. `PorePressureFeedback=0` in L3c is intentional
for the diffusion gate, but it means the full coupled storage and stress path
are not part of the current validation figure.

## Current Classification

| route | level | status |
| --- | --- | --- |
| L3a initial-pressure gate | Level 1 | passed CPU/GPU short-to-medium gate |
| L3c consistent initial-state gate | Level 1 | current best validation figure |
| L4 GPU long-run | Level 1 | recommended next step |
| L2 AccInput | Level 2 attempt | stable but not strict |
| L3b MechanicalTopLoad | Level 2 attempt | stable but not strict |
| L5 mechanical loading route | Level 2 | required for full strict reproduction |
| full feedback route | Level 3 | deferred |

## Definition Of Strict Reproduction

A strict complete 1D consolidation reproduction must eventually pass all three
levels:

1. Level 1 pressure diffusion and hydraulic boundaries match Terzaghi.
2. Level 2 top surcharge generation produces the correct undrained pressure
   scale without dynamic over-amplification.
3. Level 3 coupled effective-stress/pore-pressure response remains stable and
   physically interpretable.

L4 can strengthen Level 1. It cannot be described as strict full mechanical
reproduction. L5 is eventually required for the full claim.

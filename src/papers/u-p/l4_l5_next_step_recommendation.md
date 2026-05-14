# L4-L5 Next Step Recommendation

Date: 2026-05-14

## Decision Summary

Use a layered route:

1. Do L4 GPU long-run first.
2. Then design/prototype L5 CPU mechanical loading.
3. Keep full feedback and damping/viscosity sweeps deferred.

This separates the clean PR diffusion/boundary validation from the unresolved
mechanical load-generation problem.

## Step 1: Do L4 GPU Long-Run First

Recommended next action:

- reuse the L3c consistent initial-state route;
- run a longer GPU validation with CPU parity if runtime allows;
- compare against Terzaghi analytical pressure profiles and bottom pressure;
- keep `PorePressureFeedback=0`;
- keep `AccInput=0` and `MechanicalTopLoad=0`.

Reasons:

- low risk;
- no source changes required;
- builds on a case already passing CPU and GPU;
- directly strengthens the PR diffusion and hydraulic-boundary evidence;
- can produce a paper-compatible Level-1 validation figure.

Important caveat:

L4 must be described as a Level-1 diffusion/boundary validation. It is not full
mechanical reproduction.

## Step 2: Do L5 CPU Mechanical Loading Route After L4

L5 remains necessary if the final goal is strict complete 1D reproduction.

Recommended L5 focus:

- CPU-first source audit;
- force-controlled loading plate or true surface traction;
- consistent total/effective stress initializer;
- diagnostics for generated initial excess pressure and mechanical balance;
- no broad damping/viscosity sweep.

Reasons:

- Level-2 strict reproduction needs actual top surcharge generation;
- L2/L3b already showed that body acceleration and direct force-on-material
  routes are not enough;
- this route likely needs source/design work and should not be mixed with L4.

## Step 3: Defer Full Feedback And Stress Coupling

Full feedback should remain deferred until the load-generation route is fixed.

Reasons:

- full feedback has separate stability history in the triaxial route;
- enabling it now would obscure whether errors come from loading, pressure
  diffusion, or coupling;
- L3c/L4 already isolate the pressure update and boundary behavior.

## If The Goal Is Most Strict Complete Reproduction

Eventually do L5. Full strict reproduction cannot stop at L4 because L4 does
not generate the top surcharge mechanically.

## If The Goal Is The Next Most Stable And Valuable Step

Do L4 first. It strengthens the validated part of the implementation and does
not depend on unresolved mechanical loading features.

## Damping And Viscosity Sweeps

Do not start a damping/viscosity sweep now. L2 and L3b show that the dominant
problem is loading-route fidelity, not simply damping strength. A sweep before
the load route is fixed risks tuning away symptoms while keeping a non-paper
boundary condition.

## Recommendation

Proceed to L4 GPU long-run as the next task. Treat L5 as a follow-on CPU-first
mechanical loading design/prototype task. Do not let L5 block L4.

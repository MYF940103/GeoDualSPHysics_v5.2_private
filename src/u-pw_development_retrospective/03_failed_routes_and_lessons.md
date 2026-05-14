# Failed Routes And Lessons

## Cryer Curved Boundary Mode Proliferation

What failed:

- many `CurvedDrainedBoundaryMode` variants were added;
- geometry and diffusion errors remained difficult to isolate;
- the interface expanded faster than validation.

Lesson:

Do not add a new mode to explain every failed run. Freeze, compare, then delete
or archive failed subroutes.

## Mechanical Top Load For 1D Consolidation

What failed:

- L2 `AccInput` top-layer acceleration is a body-force route, not a true top
  surcharge;
- L3b force-on-material `MechanicalTopLoad` applied the correct total force
  scale but generated dynamic excess-pressure peaks near `6e5 Pa`, far above
  the analytical `1e4 Pa` scale.

Lesson:

Strict mechanical loading needs a quasi-static loading plate, true surface
traction, or consistent total/effective stress initializer. Do not try to fix
this with damping/viscosity sweeps first.

## BND1 Generalized Boundary Operator 2

What failed:

- operator `2` correctly included ordinary solid-wall no-flux samples;
- feedback-off was stable but analytically worse than operator `1`;
- feedback-on produced `excluded=973` and `DtMin=10252`.

Lesson:

Wider boundary coverage is not automatically a better numerical operator.
Boundary reconstruction and feedback response must be validated together.

## TINT2 End-Step Pressure Commit

What failed:

- end-step pressure commit was implemented cleanly;
- it did not improve L3c/L5/BND1 metrics;
- BND1 operator `2` feedback-on failure was unchanged.

Lesson:

The BND1 mode `2` instability is probably not primarily a pressure-commit
placement problem. Do not add more time-integration modes before cleanup.

## MCC Strict Triaxial Validation

What failed:

- original-rate mild MCC had local return failures;
- substepping, ramps, and line-search variants did not produce a clean route;
- failures localized to platen/edge/cap support issues;
- smooth Cartesian refinement did not fix the failure population;
- fan-like layout remained a geometry/support diagnostic and was not integrated
  into the solver workflow.

Lesson:

MCC solver integration works as a prototype, but clean validation needs a
better specimen/boundary layout or a different benchmark. Do not present the
current route as strict MCC validation.

## Full Feedback In Complex Benchmarks

What failed or remains risky:

- triaxial full feedback remained unstable/caveated;
- generalized boundary mode `2` plus feedback was unstable;
- feedback should be reintroduced through small gates, not large benchmarks.

Lesson:

Use 1D L5 feedback-on operator `1` as the current minimum coupling gate.
Advance to landslide only with reduced claims and strong diagnostics.

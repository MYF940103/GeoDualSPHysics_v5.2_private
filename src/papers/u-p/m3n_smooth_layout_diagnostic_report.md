# M3n Smooth Layout Diagnostic Report

## Objective

M3n tests whether a minimal smoother-layout route can improve the boundary
induced MCC return failures found in M3k-M3m.  No solver source is changed.
The MCC return mapping, PR pressure update, and FlexibleConfiningStress physics
are unchanged.

## Cases

Experiment directory:

`examples/u-pw/04_Undrained_Triaxial/experiments/M3n_SmoothLayoutDiagnostic/`

Cases:

- `CaseM3n_Overhang045Reference`: self-contained `Dp=0.01 m` M3m
  overhang045 reference.
- `CaseM3n_Dp0075Overhang045`: higher-resolution `Dp=0.0075 m` overhang045
  diagnostic.

Both cases are CPU-only, feedback-off, mild-MCC, very-short dense-output runs
with explicit top/bottom platens, selected lateral confinement,
`SaveMccState=1`, and pairwise platen reaction diagnostics.

## Run Status

Both cases ran cleanly at the solver level:

| variant | code | excluded | DtMin | steps | specimen particles |
|---|---:|---:|---:|---:|---:|
| overhang045_ref | 0 | 0 | 0 | 21 | 407 |
| dp0075_overhang045 | 0 | 0 | 0 | 30 | 1035 |

No GPU simulation was run.

## Geometry and Support Metrics

The higher-resolution candidate changed the realized particle set and improved
edge/cap support metrics:

| metric | Dp=0.01 ref | Dp=0.0075 |
|---|---:|---:|
| specimen particles | 407 | 1035 |
| edge/corner particles | 112 | 294 |
| cap/edge particles | 148 | 414 |
| edge support/core ratio | 0.8078 | 0.8507 |
| edge specimen-neighbor proxy | 68.1 | 87.5 |
| cap support/core ratio | 0.8529 | 0.8935 |
| cap specimen-neighbor proxy | 77.2 | 100.5 |

Thus the candidate did what it was supposed to do geometrically: it changed
the particle set and improved support completeness at the edge/cap regions.

## Return Status

The return-status result is negative:

| variant | first failure time (s) | max -3 | max -1 | bad frames | final negative |
|---|---:|---:|---:|---:|---:|
| overhang045_ref | 0.001106 | 8 | 8 | 12 | 0 |
| dp0075_overhang045 | 0.000829 | 16 | 52 | 17 | 0 |

The higher-resolution candidate has a clean final frame, but it is not clean
over saved frames.  It triggers near-tension `-1` earlier and more strongly,
and it doubles the maximum `ReturnStatus=-3` count.

## Local Diagnostics

For `ReturnStatus=-3` particles:

| metric | Dp=0.01 ref | Dp=0.0075 |
|---|---:|---:|
| failed support/core mean | 0.912 | 0.870 |
| failed specimen-neighbor mean | 128.3 | 134.1 |
| failed velocity-gradient mean | 0.0537 | 0.0422 |
| failed q mean (Pa) | 57.3 | 51.8 |
| failed residual max | 6994 | 6919 |

The high-resolution case improves some local support and velocity-gradient
averages, but that improvement does not translate into fewer return failures.
The failure population also spreads more broadly, including more near-tension
states and some measurement-core failures.  This suggests that plain
Cartesian refinement changes the local stress/pressure path rather than simply
removing the edge-support problem.

## Global Response

Final global metrics remain bounded:

| variant | p' (Pa) | q (Pa) | pairwise reaction (N) | mean PorePress (Pa) | velocity max (m/s) |
|---|---:|---:|---:|---:|---:|
| overhang045_ref | 57.77 | 52.55 | 0.293 | -2.15e3 | 0.00578 |
| dp0075_overhang045 | 57.33 | 55.92 | 0.357 | +2.00e3 | 0.00613 |

The candidate does not create a solver-level instability.  Reaction, p'-q,
pore pressure, velocity, lateral target count, and cap leakage remain
bounded.  However, bounded global response is not enough for clean MCC return
validation.

## Interpretation

M3n confirms two things at once:

1. Current `Dp=0.01` Cartesian geometry is too coarse for small XML
   trim/step edits to reliably change the realized boundary support.
2. Simply reducing `Dp` within the same Cartesian/cut-cell cylinder does not
   clean the MCC return route.  It improves support metrics, but it worsens
   saved-frame `-1` and `-3` return statuses in this diagnostic.

Therefore the evidence still supports a boundary-induced local path problem,
but the minimal higher-resolution Cartesian route is not the clean fix.

## Fan-Like / Smooth Layout Feasibility

No native XML-only fan/radial specimen layout route was identified in the
current triaxial workflow.  A true fan-like or radial boundary-shell layout is
feasible as an isolated external generator, but it requires a confirmed
custom-particle input path before it can be treated as a solver workflow.

## Clean Candidate Assessment

M3n did not obtain a clean MCC validation candidate:

- `ReturnStatus=-3` is not eliminated across saved frames;
- `ReturnStatus=-1` worsens in the high-resolution candidate;
- the final frame is clean, but transient failures remain;
- the route remains feedback-off and reduced.

## Recommendation

Do not proceed to clean MCC validation from M3n.

Recommended next step depends on priority:

- If clean MCC validation remains the goal, implement a true smooth/fan-like
  specimen generator or a hybrid radial boundary-shell prototype, then first
  run a geometry-only support diagnostic before SPH.
- If documentation is the near-term goal, proceed with a caveated MCC reduced
  reporting package that explicitly states the remaining boundary-induced
  return caveat.
- Do not spend more effort on small Cartesian edge edits or plain
  higher-resolution cut-cell variants without a true smoother boundary layout.

Full pore-pressure feedback and GPU MCC remain deferred.

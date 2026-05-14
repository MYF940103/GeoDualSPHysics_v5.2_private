# M3m Refined Platen / Edge Geometry Report

## Objective

M3m tests a small set of platen/specimen interface and edge-corner geometry
refinements after M3l showed that platen overhang improves MCC return
robustness.  No MCC return mapping, PR pressure update, or
FlexibleConfiningStress source code was changed.

All cases are CPU-only, feedback-off, mild-MCC, dense-output diagnostics with
explicit top/bottom platens, selected lateral confinement, `SaveMccState=1`,
and pairwise platen reaction diagnostics.

## Variants Tested

The M3m experiment directory is:

`examples/u-pw/04_Undrained_Triaxial/experiments/M3m_RefinedPlatenEdgeGeometry/`

Cases:

- `CaseM3m_OverhangReference`: M3l best reference, platen radius `0.04 m`.
- `CaseM3m_Overhang045`: larger platen overhang, platen radius `0.045 m`.
- `CaseM3m_TrimmedEdge`: intended cap-edge trimming with platen radius
  `0.04 m`.
- `CaseM3m_SteppedCap`: intended stepped cap transition with platen radius
  `0.04 m`.
- `CaseM3m_Overhang045Extended`: short extended check of `Overhang045`,
  `TimeMax=0.004 s`.

Important geometry realization note: on the current `Dp=0.01 m` Cartesian
particle lattice, the trimmed-edge and stepped-cap XML variants generated the
same specimen particle set as the overhang reference:

```text
specimen particles: 407
cap-zone particles: 148
particle-set added/removed vs reference: 0 / 0
max cap radius: 0.03162 m
```

Thus these two variants are XML geometry attempts, but not realized particle
geometry changes at this resolution.  Their results are therefore expected to
match the overhang reference.

## Run Status

All M3m CPU Release cases finished cleanly at the solver level:

```text
code=0
excluded=0
DtMin adjustments=0
```

No GPU simulation was run.

## Return-Status Comparison

Primary dense cases:

| variant | first failure time (s) | max -3 | max -1 | bad frames | final negative |
|---|---:|---:|---:|---:|---:|
| overhang_ref | 0.001005 | 8 | 20 | 16 | 8 |
| overhang045 | 0.001106 | 8 | 8 | 12 | 0 |
| trimmed_edge | 0.001005 | 8 | 20 | 16 | 8 |
| stepped_cap | 0.001005 | 8 | 20 | 16 | 8 |

The larger overhang is the only effective primary variant.  It does not reduce
the maximum saved-frame `ReturnStatus=-3` below the M3l overhang reference, but
it delays the first `-3` episode, reduces the near-tension `-1` population, and
cleans the final frame for the very-short diagnostic.

The short extended check shows the improvement is not yet sustained:

```text
Overhang045Extended: max -3=12, max -1=8, final -3=5, final -1=0
```

Therefore M3m did not obtain a clean MCC validation candidate.

## Local Diagnostics

The M3l overhang reference first `-3` episode appears at `t=0.001005 s` with
eight edge-ring particles:

```text
support/core mean      = 0.560
specimen-neighbor mean = 64
velocity-gradient norm = 0.093
q mean                 = 79.81 Pa
q/p' mean              = 1.274
max residual           = 1195.7
```

For `Overhang045`, the first negative frame at `t=0.001106 s` contains only
`-1` statuses.  The first `-3` episode is delayed to `t=0.001609 s`:

```text
support/core mean      = 0.870
specimen-neighbor mean = 97
velocity-gradient norm = 0.110
q mean                 = 84.73 Pa
q/p' mean              = 1.212
max residual           = 3411.5
regions                = edge_ring and adjacent interior
```

Interpretation:

- larger overhang improves neighbor/support completeness and suppresses the
  earliest top edge/corner `-3`;
- it does not remove the later edge/interior high-return-burden path;
- support improves, but the later `-3` still coincides with high local
  velocity-gradient and high yield residual.

## Global Response

At `t=0.002513 s`, the main short-window comparison is:

| variant | p' (Pa) | q (Pa) | pairwise reaction (N) | mean PorePress (Pa) | max velocity (m/s) |
|---|---:|---:|---:|---:|---:|
| overhang_ref | 55.88 | 52.42 | 0.283 | -4.61e3 | 0.00570 |
| overhang045 | 57.77 | 52.55 | 0.293 | -2.15e3 | 0.00578 |
| trimmed_edge | 55.88 | 52.42 | 0.283 | -4.61e3 | 0.00570 |
| stepped_cap | 55.88 | 52.42 | 0.283 | -4.61e3 | 0.00570 |

The larger overhang preserves the global response and does not distort the
reaction or p'-q path in the short dense window.  Pore pressure remains bounded
and less negative than the overhang reference.  Lateral target count remains
`112`, and the cap leakage proxy remains `0`.

The extended overhang check remains bounded but reintroduces local `-3`:

```text
final t=0.004021 s
p'≈58.44 Pa
q≈66.60 Pa
pairwise reaction≈0.360 N
mean PorePress≈-7.35e3 Pa
velocity max≈0.00605 m/s
```

## Clean Candidate Assessment

M3m did not produce a clean reduced MCC validation candidate:

- no case has all saved frames free of negative MCC return statuses;
- `Overhang045` is improved but still has transient `-3`;
- `Overhang045Extended` shows that the transient `-3` can reappear later;
- trimmed/stepped cap variants are not realized particle-geometry changes at
  current resolution.

## Boundary-Induced Failure Interpretation

M3m strengthens the boundary-induced failure interpretation:

- changing only platen boundary support changes the failure population;
- no MCC return mapping changes were made;
- solver stability, pairwise reaction, p'-q, pore pressure, and MCC state
  evolution remain bounded;
- the unresolved failures remain edge/corner and platen-adjacent local paths,
  not a global MCC constitutive collapse or sign-convention bug.

## Recommended Next Step

Recommended next step: do not proceed to clean M3g validation yet.

The most useful next route is one of:

1. a more explicit smooth/fan-like specimen layout or finer particle geometry
   that can actually realize rounded cap/edge particles; or
2. one more M3n clean-geometry extended check only after a geometry variant
   demonstrably removes transient `-3` in the dense window.

With the current Cartesian `Dp=0.01 m` reduced cylinder, the practical
recommendation is to move toward a smooth/fan-like or higher-resolution
geometry design rather than continuing small XML edge edits that do not change
the generated particle set.

Full pore-pressure feedback and GPU MCC remain deferred.

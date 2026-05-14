# M3j Local Strain and Stress-Path Failure Audit

## Objective

This audit compares failed MCC return records by local state variables and
available kinematic proxies.  The target is to determine whether failed
particles experience abnormal local stress/strain paths relative to the
specimen-scale response.

Generated output:

- `m3j_local_strain_path_comparison.csv`

## Data Availability

The retained M3d2/M3f/M3h files contain failed-particle records but not full
PartCsv frames.  Therefore:

- direct neighbor counts are unavailable;
- nearby non-failed particle comparisons are unavailable;
- local velocity-gradient tensors are unavailable;
- trial `p'`, trial `q`, and trial yield function are unavailable except as
  explicitly unavailable columns in M3h.

Available fields include:

- saved `p'` and `q` proxies;
- `pc`;
- void ratio;
- plastic volumetric and equivalent plastic strain;
- plastic multiplier;
- return iterations;
- yield residual;
- `Kplastic`;
- `PorePress`, `PorePressRate`;
- `DivVel`;
- local velocity magnitude;
- pairwise reaction proxy where available.

## Status-Family Behavior

The failed records split into two families.

### Tension / Admissibility Family (`-1`)

Baseline/admissible-line `-1` records have negative saved mean effective
stress:

```text
M3h baseline -1:
mean p' = -15.16 Pa
mean q  = 47.79 Pa
max |DivVel| = 0.1006
max velocity = 5.92e-3 m/s
max |PorePressRate| = 6.69e7 Pa/s
```

This is consistent with local inadmissible/tension-side states, not a global
MCC sign error.

### Line-Search Failure Family (`-3`)

Line-search failure records generally have positive `p'`, higher `q/p'`, and
bounded `pc`:

```text
M3h baseline -3:
mean p' = 43.23 Pa
mean q  = 83.94 Pa
mean q/p' = 2.07
mean pc = 119.81 Pa
max |DivVel| = 0.0724
max velocity = 3.88e-3 m/s
max |PorePressRate| = 4.81e7 Pa/s
```

This is a local return-path difficulty with valid state variables rather than
negative `pc` or unbounded state evolution.

## Effect of Loading Rate

The quarter-speed routes reduce local kinematic severity:

```text
M3h quarter-speed -3:
mean p' = 30.76 Pa
mean q = 62.56 Pa
mean q/p' = 2.05
max |DivVel| = 0.0202
max velocity = 1.26e-3 m/s
max |PorePressRate| = 1.34e7 Pa/s
```

Compared with the baseline, both `DivVel` and `PorePressRate` are lower, and
the final frame is clean.  However, transient failures remain.  This supports
the view that local strain increment/velocity path matters, but simply slowing
the loading is not enough for a clean validation gate.

## Adaptive / Ramp Cases

M3f improved-adaptive and ramp-improved-adaptive cases create more failed
records:

```text
M3f improved adaptive -3:
count = 997
mean p' = 46.29 Pa
mean q = 68.69 Pa
max return iterations = 274
max |DivVel| = 0.0924
max velocity = 5.10e-3 m/s

M3f ramp improved adaptive -3:
count = 1232
mean p' = 44.27 Pa
mean q = 68.45 Pa
max return iterations = 318
max |DivVel| = 0.0813
max velocity = 5.21e-3 m/s
```

The added substepping/ramping did not remove the local strain-path difficulty.

## Plastic State Behavior

Across failed records:

- `pc` remains positive and bounded around the mild-MCC hardening range;
- void ratio remains bounded;
- plastic strains remain finite;
- plastic multiplier is either zero for old failure paths or small and
  positive in substepped/admissible paths.

This again points away from global state corruption.

## Interpretation

The failed particles do experience locally more difficult stress paths:

- `-1` failures reach inadmissible/tension-side saved `p'`;
- `-3` failures have positive `p'` but relatively high `q/p'` and local
  return iteration burden;
- failures coincide with higher local `DivVel`, velocity, or pore-pressure-rate
  spikes than the slower routes.

The evidence supports a boundary-induced local strain/stress-path trigger, not
a global MCC return collapse.

## Limitation

Because full particle frames were cleaned, M3j cannot compute true local strain
gradients, neighbor counts, or direct failed-vs-nearby-nonfailed comparisons.
A later very-short dense-output diagnostic would be required for that level of
evidence.

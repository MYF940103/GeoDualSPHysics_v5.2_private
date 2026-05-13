# M3d2 MCC Return Failure Audit

## Scope

M3d2 audits the local return robustness issue found in the M3d mild-yield MCC
feedback-off platen case. No solver source was changed for this stage. The
diagnostics use the same explicit-platen, selected lateral confinement,
`PorePressureFeedback=0`, CPU Release workflow as M3d.

The experiment directory is:

`examples/u-pw/04_Undrained_Triaxial/experiments/M3d2_MCCReturnRobustness/`

## Cases

| Case | Purpose | Key change |
| --- | --- | --- |
| `baseline` | rerun M3d mild-yield reference | `v_z=-0.005 m/s`, `TimeMax=0.018 s` |
| `slower_half_velocity` | test increment/loading-rate sensitivity | `v_z=-0.0025 m/s`, `TimeMax=0.036 s` for similar final displacement |
| `early_stop` | locate failure timing threshold | `v_z=-0.005 m/s`, `TimeMax=0.006 s` |
| `tight_return` | test iteration/tolerance sensitivity | `MccReturnTolerance=1e-10`, `MccReturnMaxIter=80` |

All four cases finished `code=0`, `excluded=0`, and `DtMin=0`.

## Return Status Summary

| Case | Final status counts | Final failed count | Final line-search failures | Max failed count during run | Max line-search failures |
| --- | --- | ---: | ---: | ---: | ---: |
| baseline | `-3:8|0:2|1:397` | 8 | 8 | 157 | 9 |
| slower_half_velocity | `0:8|1:399` | 0 | 0 | 100 | 16 |
| early_stop | `1:407` | 0 | 0 | 157 | 4 |
| tight_return | `-3:8|0:2|1:397` | 8 | 8 | 157 | 9 |

The high early failed counts are mostly `ReturnStatus=-1` tension-cutoff
markers during the first transient. They recover later. The final persistent
failure of interest is `ReturnStatus=-3`, the line-search failure marker.

## Final Failed Particles

The baseline final `-3` particles are eight symmetric particles near the
bottom interior/cap transition:

| Idp | region | x | y | z | p' | q | pc | residual |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 260 | interior | -0.010000 | -0.010000 | 0.019978 | 40.30 | 76.94 | 119.80 | 1305.64 |
| 414 | interior | 0.010000 | -0.010000 | 0.019978 | 40.30 | 76.94 | 119.80 | 1305.64 |
| 282 | interior | -0.010000 | 0.010000 | 0.019978 | 40.30 | 76.94 | 119.80 | 1305.63 |
| 436 | interior | 0.010000 | 0.010000 | 0.019978 | 40.30 | 76.94 | 119.80 | 1305.63 |
| 336 | bottom_cap_zone | 0.000000 | -0.010003 | 0.009984 | 38.14 | 82.99 | 119.64 | 2411.01 |
| 270 | bottom_cap_zone | -0.010003 | 0.000000 | 0.009984 | 38.14 | 82.99 | 119.64 | 2411.01 |
| 358 | bottom_cap_zone | 0.000000 | 0.010003 | 0.009984 | 38.14 | 82.99 | 119.64 | 2411.00 |
| 424 | bottom_cap_zone | 0.010003 | 0.000000 | 0.009984 | 38.14 | 82.99 | 119.64 | 2411.01 |

They are not tensile at the final frame: `p'` is positive and far above the
`1e-5 Pa` tension cutoff. This makes a pure sign-convention or tension-cutoff
failure unlikely for the persistent final `-3` set.

## Region Pattern

Final baseline failures:

- `bottom_cap_zone`: 4 of 18 particles;
- `interior`: 4 of 67 particles;
- no final lateral-boundary or edge `-3` particles.

Early transient `-1` markers are broader and include edge, lateral boundary,
bottom cap, and interior particles. Late `-3` markers are small, symmetric
clusters around discrete rings near `z≈0.01-0.02 m`.

The slower-half-velocity case has no final failures, but it still records
intermediate `-3` episodes. These are mostly edge/top-zone events and recover
before the final frame.

## Failure Type Assessment

1. **Tension / p' cutoff:** important early, not the final blocker. Early
   `-1` markers show some particles temporarily enter non-admissible
   low/negative `p'` states, but the final persistent `-3` particles have
   positive `p'`.
2. **Trial stress too far / local increment robustness:** likely. Slower
   platen motion eliminates final `-3` while preserving the same reduced
   benchmark physics and keeping all other diagnostics bounded.
3. **Iteration limit only:** unlikely. Raising max iterations to 80 and
   tightening tolerance to `1e-10` reproduces the baseline final `-3:8`.
4. **Boundary/platen localization:** likely. Final failures sit in symmetric
   bottom-adjacent rings, not randomly throughout the material.
5. **Global return mapping bug:** not supported by the evidence. Most particles
   converge, residuals of converged plastic returns remain small, and the
   failed set is spatially structured.

## Output Files

Key retained diagnostics:

- `m3d2_failed_return_particles.csv`
- `m3d2_return_status_by_region.csv`
- `m3d2_return_status_comparison.csv`
- `m3d2_failed_particle_locations.csv`
- `m3d2_yield_residual_comparison.csv`
- `m3d2_pc_ev_plastic_strain_comparison.csv`


# T4n2 Restart State Audit

## Scope

T4n2 audits the existing DualSPHysics/GeoDualSPHysics restart route for the
u-pw triaxial staging problem. No source was changed in this task.

## Restart Entry Point

The command-line restart route is:

```text
-partbegin:begin[:first] dir
```

`JSphCfgRun` parses `begin` as the PART number to load and `first` as the
first PART number written by the continued run. Existing restart examples use
this route by regenerating the case files with GenCase and then passing the
previous `data` directory to DualSPHysics.

## u-pw Fields

Current restart support is adequate for the fields needed by this audit:

| Field | Restart status | Notes |
| --- | --- | --- |
| Position | supported | Core Part data. |
| Velocity | supported | Core `VelRhop` data. |
| Density | supported | Core `VelRhop.w`; CPU restart preserves it instead of resetting to `RhopZero`. |
| `Sigma_kk` / `Sigma_ij` | supported | `JPartsLoad4` loads them when the arrays exist in the PART file. |
| `Kplastic` | supported | Loaded together with the stress arrays. |
| `PorePress` | supported | Loaded when `SavePorePressure=1` and `PorePress` exists in the PART file. |
| `ExcessPorePress` | not separately restored | For the T4n2 cases `HydraulicElevationSource=0`, so excess pressure equals `PorePress` and can be recomputed. |
| `PorePressRate` | not restored | Rate/diagnostic field; reset to zero and recomputed. |
| `DivVel` / `LapPorePress` | not restored | Diagnostic/update fields; reset to zero and recomputed. |
| `PorePressureAccel*` | not restored | Diagnostics; reset to zero. |
| `InitialStressMode` state | embodied in `Sigmac` | On restart, restored stress fields take priority and XML initial stress is ignored. |
| `f_i` / cylinder classes | recomputed | Geometry diagnostics need not be stored. |
| Feedback gating state | time/XML based | Not stored; restart uses the PART time and the Stage B/C XML schedule. |

## Changeable XML Parameters After Restart

The restart run regenerates the same particle layout and then maps saved state
by `Idp`. The following staging changes are acceptable as long as the particle
configuration remains compatible:

- `ConfiningStressUseLateralSelector`;
- `FlexibleConfiningStress` settings;
- `PorePressureFeedback` and feedback timing;
- axial `AccInput` in a later task.

The audit did not use axial loading. `InitialStressMode=1` was left in the
Stage B/C XML only for transparency; the CPU log confirms it is ignored on
restart because `Sigmac` is restored from the PART file.

## Run Evidence

Stage B and Stage C both logged:

```text
Restart soil state restored from PART_0023: Sigma_kk, Sigma_ij and Kplastic restored for 407/407 particles using Idp mapping.
Restart pore-pressure state restored from PART_0023: PorePress restored for 407/407 particles using Idp mapping.
```

The continuity CSV compares Stage A `PartCsv_0023` against the restart
run's initial `PartCsv_0023`. The max absolute difference is exactly zero in
the saved CSV precision for position, velocity, density, stress, `Kplastic`,
and `PorePress`.

## Source Enhancement Need

No source enhancement is needed to restart the current elastic u-pw fields for
T4n2. A future stricter workflow may want explicit restart support for
diagnostic fields (`PorePressRate`, `DivVel`, feedback acceleration), but those
are recomputed fields and are not blockers for staged confinement.

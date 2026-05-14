# TINT1b Pore-Pressure Variable Dependency Audit

Date: 2026-05-14

## Objective

TINT1 showed that `PorePress` is currently advanced by an explicit
operator-split update. TINT1b expands that audit to every variable that feeds
or is fed by `PorePressRate`, so TINT2 does not merely move
`UpdatePorePressure()` and accidentally create a new inconsistency.

No source changes and no simulations are made in TINT1b.

## Summary Table

| Variable | Source and function | Storage | Current stage | CPU/GPU consistency | Correction/output notes |
|---|---|---|---|---|---|
| `PorePress` | CPU init/update in `JSphCpuSingle.cpp` and `JSphCpu.cpp:2228`; GPU update in `JSphGpu.cpp:1046` | persistent `double` array | initialized before run; read during `Interaction_Forces`; updated before mechanical update/corrector | broad placement is consistent; post-update clamp placement differs | overwritten by top drained/bottom no-flux clamps and Shepard; output as `PorePress` |
| `ExcessPorePress` | computed at save from `PorePress - hydrostatic` in `JSphCpuSingle.cpp:1792`; GPU in `JSphGpuSingle.cpp:1072-1084` | output-only derived field | save stage | consistent conceptually | not persistent; not used by rate except through mode-specific excess calculations |
| `PorePressRate` | CPU `ComputeHydroPorePressRatePR()` at `JSphCpu.cpp:2195`; GPU `ComputeHydroPrDiagnosticsGpu()` at `JSphGpu.cpp:880` | persistent `float` diagnostic array | interaction stage after `DivVel`, `LapPorePress`, `LapZ`, boundary contributions | yes for operator `0/1`; GPU lacks CPU modes `2/3` | output as `PorePressRate`; not corrected after Shepard/clamp |
| `DivVel` | CPU `ComputeHydroDivVel()` at `JSphCpu.cpp:2185`; GPU diagnostic kernel | persistent `float` diagnostic array | interaction stage | yes | uses current/predicted `Velrhop`; output as `DivVel` |
| `LapPorePress` | CPU `ComputeHydroLapPorePress()` at `JSphCpu.cpp:2617`; GPU diagnostic kernel | persistent `float` diagnostic array | interaction stage, before boundary additions | yes for material-material part | uses pre-update pressure; boundary operator may add to it before rate |
| `LapZ` | CPU `ComputeHydroLapZ()` at `JSphCpu.cpp:2682`; GPU diagnostic kernel | persistent `float` diagnostic array | interaction stage, before boundary additions | yes for material-material part | active when hydraulic elevation source is used; boundary operator may add to it |
| `PorePressureAccel` | CPU `ComputePorePressureAccel()` at `JSphCpu.cpp:4231` or paper operator at `JSphCpu.cpp:4299` | persistent `tfloat3` diagnostic array | interaction stage before `UpdatePorePressure` | GPU does not expose all CPU operators | feedback candidate using old/stage pressure |
| `PorePressureAccelDiff` | CPU `ComputePorePressureAccelDiff()` at `JSphCpu.cpp:4367`; LSQ at `JSphCpu.cpp:4550`; GPU diff at `JSphGpu.cpp:985` | persistent `tfloat3` diagnostic array | interaction stage before `UpdatePorePressure` | GPU supports operator `1` | output as `PorePressureAccelDiff` |
| feedback diagnostics | `ApplyPorePressureFeedback()` at `JSphCpu.cpp:4561`; reset/print in `JSph.cpp:3912` | persistent scalar diagnostics plus `PorePressureFeedbackUsedAce` | interaction stage | CPU richer than GPU | records raw/used acceleration from old/stage pressure |
| Shepard pressure | `ApplyPorePressureShepard()` at `JSphCpu.cpp:2412`; GPU at `JSphGpu.cpp:1070` | temporary local array, then writes `PorePress` | after `UpdatePorePressure` | yes, but CPU/GPU placement differs relative to mechanics | changes actual pressure after rate integration; no `DeltaP` bookkeeping |
| top drained clamp | CPU `ApplyPorePressureTopDrained()` at `JSphCpu.cpp:2424`; GPU at `JSphGpu.cpp:1115` | writes `PorePress` | initialization and post-update | yes in intent; stage differs | clamps top material layer to hydrostatic, i.e. excess `0` |
| bottom no-flux clamp | CPU `ApplyPorePressureBottomNoFlux()` at `JSphCpu.cpp:2480`; GPU at `JSphGpu.cpp:1186` | writes `PorePress` | initialization and post-update | yes in intent; stage differs | projects bottom material layer to reference excess mean |
| lateral/ordinary no-flux contribution | CPU operator `2` in `ApplyPorePressureBoundaryOperatorT()` around `JSphCpu.cpp:2849` | not persistent; adds to `LapPorePress`/`LapZ` | interaction stage before rate | CPU only | BND1 generalized route reconstructs boundary excess from old/stage pressure |
| boundary hydraulic state mode `1/2` | mode `1` virtual ghosts around `JSphCpu.cpp:2733`; mode `2` boundary particles around `JSphCpu.cpp:2849` | temporary per interaction; optional ghost output arrays | interaction stage before rate; ghost output recomputed at save | mode `1` CPU/GPU; mode `2` CPU only | uses pre-update pressure |
| pore-pressure dt restriction | CPU `DtVariable()` at `JSphCpu.cpp:6929`; GPU at `JSphGpu.cpp:1694` | scalar `PorePressureDt`, `PorePressureDtActive` | before update when dt is selected | yes | independent of instantaneous `PorePressRate` |
| output fields | CPU `SaveData()` around `JSphCpuSingle.cpp:1710-1806`; GPU around `JSphGpuSingle.cpp:1068-1099` | save arrays | save stage after previous completed step | mostly consistent | output pressure is corrected/clamped pressure, rate is last interaction-stage rate |

## Persistent Arrays Versus Temporary Values

Persistent arrays:

- `PorePress`;
- `PorePressRate`;
- `DivVel`;
- `LapPorePress`;
- `LapZ`;
- `PorePressureAce`;
- `PorePressureAceDiff`;
- `PorePressureFeedbackUsedAce`;
- optional ghost/corrected diagnostic arrays.

Temporary or derived values:

- `ExcessPorePress`, computed at save;
- mode `1` ghost point state;
- mode `2` reconstructed boundary excess;
- Shepard regularization buffer;
- top/bottom clamp before/after statistics;
- `PorePressureDt`, computed each `DtVariable()` call and stored as scalar
  state.

## Stage Classification

### Old/Stage Pressure Readers

The following read pressure before `UpdatePorePressure()` in the current step:

- `ComputeHydroLapPorePress`;
- `ApplyPorePressureBoundaryOperator`;
- `ComputeHydroCorrectedOperators`;
- `ComputePorePressureAccel*`;
- `ComputeHydroPorePressRatePR`.

### Pressure Writers

The following write pressure:

- `UpdatePorePressure`;
- `ApplyPorePressureShepard`;
- `ApplyPorePressureTopDrained`;
- `ApplyPorePressureBottomNoFlux`;
- `ApplyPorePressureCurvedDrainedClamp` for curved mode `2`;
- initialization and restart restore.

### Output

`PorePress` output is the current persistent pressure after the previous step's
corrections. `PorePressRate`, `DivVel`, `LapPorePress`, and `LapZ` are the last
interaction-stage diagnostics and may not correspond exactly to the final
corrected `PorePress` if Shepard or clamps changed it after the rate was
computed.

## Key TINT2 Implication

Moving `UpdatePorePressure()` alone is not enough. TINT2 must move or account
for:

- Shepard timing;
- top drained and bottom no-flux clamp timing;
- whether boundary operator contributions are computed from old or corrected
  pressure;
- whether feedback intentionally uses previous-step pressure;
- output of raw `DeltaP_rate` versus actual corrected `DeltaP`.


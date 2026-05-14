# TINT2 Implementation Checklist

Date: 2026-05-14

## Source Changes

### Parser and Configuration

- Add `PorePressureTimeIntegrationMode`.
  - `0`: current behavior, default.
  - `1`: CPU end-step pressure update.
  - `2`: reserved for recomputed end-step hydraulic operators.
- Add `SavePorePressureTimeStageDiagnostics`.
- Add GPU hard error for nonzero `PorePressureTimeIntegrationMode`.
- Log the selected mode and stage policy.

Likely files:

- `source/JSph.h`;
- `source/JSph.cpp`;
- `source/JSphCpuSingle.cpp`;
- `source/JSphCpu.cpp`;
- `source/JSphGpu.cpp` or parser-side GPU guard if shared.

### CPU Step Functions

Modify only when mode `1` is active:

- `JSphCpuSingle::ComputeStep_Ver()`;
- `JSphCpuSingle::ComputeStep_Sym()`.

Mode `0` must retain the current call order.

Mode `1` should:

- run mechanics first with previous-step pressure feedback;
- call `UpdatePorePressure()` after `ComputeVerlet()` or
  `ComputeSymplecticCorr()`;
- apply Shepard immediately after update;
- apply top drained/bottom no-flux/curved clamps immediately after Shepard.

### Diagnostics

Add CPU-only optional summaries:

- `PorePress` old/new min/max/mean;
- `DeltaP_rate` min/max/mean;
- `DeltaP_actual` min/max/mean;
- `DeltaP_correction` maxAbs;
- correction affected counts;
- `dt`, `dt_pore`, `PorePressureDtActive`;
- stage label: current, end_step, predictor/corrector if later used.

Output target can be log summaries first. Per-particle output should be added
only if needed.

## Tests

Create:

`examples/u-pw/01_1D_Consolidation/experiments/TINT2_PorePressureTimeIntegration/`

Minimum cases:

1. L3c feedback-off, operator `1`, mode `0` reference.
2. L3c feedback-off, operator `1`, mode `1`.
3. L5 feedback-on, operator `1`, mode `0` reference.
4. L5 feedback-on, operator `1`, mode `1`.
5. BND1 generalized mode `2` feedback-off, mode `0` reference.
6. BND1 generalized mode `2` feedback-off, mode `1`.
7. BND1 generalized mode `2` feedback-on short, mode `0` reference.
8. BND1 generalized mode `2` feedback-on short, mode `1`.
9. Optional hydrostatic closed-wall diagnostic.

All are CPU Release first. Do not run GPU for nonzero mode.

## Success Criteria

Default mode `0`:

- no behavior change;
- build passes;
- existing cases remain valid.

Mode `1`:

- L3c feedback-off analytical metrics are not worse;
- top drained residual remains small;
- bottom no-flux proxy remains small;
- L5 feedback-on remains stable;
- BND1 mode `2` feedback-off remains stable;
- BND1 mode `2` feedback-on has fewer exclusions, fewer `DtMin` adjustments,
  lower pressure peaks, or at least clearer diagnostics;
- no new pressure overshoot introduced;
- diagnostics explain `DeltaP_rate` versus `DeltaP_actual`.

## No-Go Criteria

- mode `1` worsens L3c feedback-off analytical comparison;
- top drained or bottom no-flux residuals become worse;
- L5 feedback-on develops exclusions or `DtMin` bursts;
- diagnostics show large correction not attributable to known boundary clamps;
- GPU path accidentally accepts nonzero mode without implementation.

## Documentation

Update:

- `u_pw_parameters.md`;
- `examples/u-pw/01_1D_Consolidation/README.md`;
- `examples/u-pw/01_1D_Consolidation/notes.md`;
- `src/papers/u-p/gpu_port_plan.md`;
- a TINT2 report describing mode `0` versus mode `1`.


# M1 MCC Risk and No-Go Analysis

## Sign Convention Risk

The largest immediate risk is mixing MCC compression-positive formulas with the code's negative-compression `Sigmac` storage. Any MCC implementation must centralize sign conversion and add tests for hydrostatic compression, shear, and unloading.

No-go:

- MCC return mapping implemented without an explicit `p' = -trace(Sigmac)/3` convention;
- output reports mix stored-sign mean stress and compression-positive `p'`.

## p' <= 0 Risk

MCC is not robust in tensile or near-zero effective mean stress. The feedback-off DP route has produced negative pore-pressure diagnostics in some mild-yield cases, so future MCC interpretation must be careful.

No-go:

- production SPH MCC run depends on hidden `p'` clamps;
- `p_c` becomes less than or equal to zero;
- large parts of the specimen enter `p' <= 0` without an explicit failure report.

## Full Feedback Risk

Full `PorePressureFeedback` remains deferred because selected-confinement feedback previously produced pressure-rate spikes and reversal. MCC should not be used to mask that unresolved coupling issue.

No-go:

- enabling full feedback in first MCC SPH smokes;
- treating feedback-off results as strict undrained validation.

## Reaction Caveat

The T4t reaction diagnostic is a pairwise specimen-platen interaction accumulator. It is not a full prescribed-motion actuator reaction.

No-go:

- using the diagnostic as a true actuator force without caveat;
- calibrating MCC parameters against it as if it were a laboratory load cell.

## Restart State Complexity

MCC requires more state than DP. Restart must include the MCC state arrays.

No-go:

- restart silently reinitializes `p_c` or void ratio;
- staged MCC cases proceed without state continuity checks.

## GPU Deferred Risk

The GPU path mirrors current elastic/DP logic but has no MCC state arrays or device return mapping.

No-go:

- accepting `SoilConstitutiveModel=3` on GPU before parity is implemented;
- committing GPU changes before CPU single-point and CPU SPH gates pass.

## Output Sufficiency Risk

Strict MCC interpretation needs clear stress, strain, pore pressure, plastic state, and reaction diagnostics. Current DP package is reduced but not strict.

No-go:

- MCC validation without `p'`, `q`, `p_c`, void ratio/specific volume, plastic volumetric strain, and yield residual output;
- MCC paper comparison without measurement-region clarity.

## DP Baseline Scope Risk

The DP route validates a reduced feedback-off platen workflow, not full u-pw triaxial reproduction.

No-go:

- using DP reduced benchmarks as proof that MCC full-feedback behavior will be stable;
- skipping MCC single-point tests because DP SPH cases ran.

## Recommended Gate Before M2/M3

M2 can proceed as a single-point MCC prototype. SPH implementation should wait until:

- return mapping passes material-point tests;
- XML/state design is implemented;
- output/restart fields are in place;
- first SPH smoke is explicitly feedback-off and CPU-only.

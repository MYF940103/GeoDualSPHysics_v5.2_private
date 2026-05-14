# TINT2 Pore-Pressure End-Step Update Report

Date: 2026-05-14

## Objective

TINT2 implemented one constrained, CPU-only pore-pressure staging experiment:
`PorePressureTimeIntegrationMode=1`. The experiment tests whether committing the
pressure state after the mechanical Verlet/Symplectic update changes the L3c,
L5, and BND1 behavior compared with the existing pre-corrector explicit commit.

This does not change the PR governing equation, feedback operator, or hydraulic
boundary operator physics. Mode `0` remains the default.

## Implemented Interface

`PorePressureTimeIntegrationMode` was added with the INTF1-constrained values:

- `0`: current default behavior.
- `1`: CPU end-step pressure commit.
- `2`: reserved and unsupported in TINT2.

GPU execution hard-errors for mode `1`; mode `2` hard-errors on all paths. The
log prints the selected mode and the operator-split convention.

No `SavePorePressureTimeStageDiagnostics` parameter was added. DeltaP
bookkeeping in this package is therefore an output-frame proxy computed in
postprocessing, not a per-step solver diagnostic.

## Calling Order

Mode `0` keeps the old order:

```text
Verlet:
Interaction_Forces -> UpdatePorePressure -> Shepard -> ComputeVerlet
         -> top drained / bottom no-flux / curved clamp

Symplectic corrector:
Interaction_Forces -> UpdatePorePressure -> Shepard -> ComputeSymplecticCorr
         -> top drained / bottom no-flux / curved clamp
```

Mode `1` uses the end-step commit:

```text
Verlet:
Interaction_Forces -> ComputeVerlet -> CommitPorePressureStep

Symplectic corrector:
Interaction_Forces -> ComputeSymplecticCorr -> CommitPorePressureStep
```

`CommitPorePressureStep` performs the full CPU pressure commit block:

1. raw `UpdatePorePressure`;
2. optional Shepard correction;
3. top drained clamp;
4. bottom no-flux projection;
5. existing curved-drained clamp when selected.

`PorePressureBoundaryOperator=2` has no separate post-update material
projection; its ordinary-wall no-flux contribution remains an interaction-stage
operator contribution. That physics was intentionally left unchanged.

## Path Coverage

Both CPU single-fluid Verlet and Symplectic paths were updated. No silent
fallback to mode `0` is present for mode `1` on CPU. GPU nonzero modes are
deferred and hard-error during XML loading.

The numerical matrix used Symplectic for the main L3c/L5/BND1 cases and added a
Verlet L3c operator-1 smoke. No GPU simulation was run.

## CPU Results

All 10 TINT2 CPU cases finished with solver `code=0`.

| case | mode | operator | feedback | integrator | excluded | DtMin | peak excess | bottom RMSE | final profile RMSE |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| L3c op1 | 0 | 1 | 0 | Symplectic | 0 | 0 | 1.000e4 Pa | 2.766e3 Pa | 6.427e3 Pa |
| L3c op1 | 1 | 1 | 0 | Symplectic | 0 | 0 | 1.000e4 Pa | 2.766e3 Pa | 6.427e3 Pa |
| BND1 op2 off | 0 | 2 | 0 | Symplectic | 0 | 0 | 1.000e4 Pa | 9.129e3 Pa | 9.675e3 Pa |
| BND1 op2 off | 1 | 2 | 0 | Symplectic | 0 | 0 | 1.000e4 Pa | 9.129e3 Pa | 9.675e3 Pa |
| L5 op1 | 0 | 1 | 1 | Symplectic | 0 | 0 | 1.000e4 Pa | 1.266e4 Pa | 1.083e4 Pa |
| L5 op1 | 1 | 1 | 1 | Symplectic | 0 | 0 | 1.000e4 Pa | 1.266e4 Pa | 1.083e4 Pa |
| BND1 op2 on | 0 | 2 | 1 | Symplectic | 973 | 10252 | 1.177e9 Pa | 4.603e8 Pa | 1.958e8 Pa |
| BND1 op2 on | 1 | 2 | 1 | Symplectic | 973 | 10252 | 1.177e9 Pa | 4.603e8 Pa | 1.958e8 Pa |
| Verlet L3c op1 | 0 | 1 | 0 | Verlet | 0 | 0 | 1.000e4 Pa | 2.766e3 Pa | 6.427e3 Pa |
| Verlet L3c op1 | 1 | 1 | 0 | Verlet | 0 | 0 | 1.000e4 Pa | 2.766e3 Pa | 6.427e3 Pa |

Boundary checks are unchanged by mode `1` in these cases. The top drained
residual is zero in the top material row, and the bottom no-flux proxy remains
small for operator `1`. Operator `2` still logs ordinary solid no-flux
participation (`ordinary_solid_noflux_pairs=690`), but this does not stabilize
the feedback-on case.

## DeltaP Bookkeeping

Because no solver-side diagnostic parameter was added, TINT2 reports an
output-frame proxy:

```text
DeltaP_rate_proxy = mean(PorePressRate at previous saved frame) * output_dt
DeltaP_actual = mean(ExcessPorePress at frame n) - mean(ExcessPorePress at frame n-1)
DeltaP_correction_proxy = DeltaP_actual - DeltaP_rate_proxy
```

This is useful only as a coarse consistency indicator; it is not a per-step
commit/correction balance. It shows that saved-frame `PorePressRate` is not a
reliable reconstruction of the actual pressure change between sparse outputs,
especially when boundary clamps and operator corrections are active. The proxy
is identical for mode `0` and mode `1` in all paired cases.

## Interpretation

Mode `1` successfully implements the unified end-step pressure commit, but the
short 1D tests are effectively neutral:

- L3c feedback-off operator `1`: no analytical or boundary improvement, no
  regression.
- L5 feedback-on operator `1`: no stability improvement, no regression.
- BND1 generalized operator `2` feedback-off: no analytical improvement.
- BND1 generalized operator `2` feedback-on: no improvement; the same
  `excluded=973` and `DtMin=10252` failure remains.

Therefore, the BND1 mode `2` feedback-on instability is unlikely to be caused
primarily by the placement of the raw pressure commit relative to the mechanical
corrector. The problem is more likely in the generalized boundary operator /
feedback coupling itself, the boundary-state reconstruction, or the feedback
response to the mode `2` pressure field.

## Answers To TINT2 Questions

1. `PorePressureTimeIntegrationMode=1` was implemented.
2. Mode `1` calls `CommitPorePressureStep` after `ComputeVerlet` or
   `ComputeSymplecticCorr`.
3. The pressure commit block includes raw update, Shepard, top drained clamp,
   bottom no-flux, and existing curved clamp when active.
4. Default mode `0` is preserved.
5. CPU Verlet and CPU Symplectic were both implemented.
6. No CPU integration path silently falls back for mode `1`; GPU nonzero modes
   hard-error.
7. L3c feedback-off is not worse, but not improved.
8. L5 feedback-on is not worse, but not improved.
9. BND1 mode `2` feedback-off is not improved.
10. BND1 mode `2` feedback-on is not improved.
11. DeltaP proxy confirms output `PorePressRate` and output pressure change
    cannot be interpreted as the same corrected state without per-step
    diagnostics.
12. TINT2-clean should not promote mode `1` yet.
13. Do not return to BND2 as if time-staging fixed the issue; BND2 should focus
    on operator `2` boundary/feedback physics.
14. Landslide baseline remains deferred unless it uses the already stable
    operator `1` route with caveats.
15. GPU support for nonzero time-integration mode remains deferred.

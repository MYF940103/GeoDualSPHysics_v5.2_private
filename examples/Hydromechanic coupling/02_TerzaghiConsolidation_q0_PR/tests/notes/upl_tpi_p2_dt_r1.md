# P2 four-phase necessary timestep audit — private author draft

2026-11-17. Author-only preparation. No prepare, compiler, program, solver, device
fixture, native reader, analysis or Git command was executed for this header.
Nothing in this note admits a physical run or claims improved accuracy/stability.

## Scope and base

Only these two files are added:

- `support/upl_tpi_p2_dt_r1.h`
- `notes/upl_tpi_p2_dt_r1.md`

The header is a complete local clone of `support/upl_tpi_m0_dt_r2.h`, with the
minimum P2 admission, four-phase accounting and separately named outputs. The
original header and all frozen M0 sources/receipts remain unchanged. Its namespace
is intentionally still `upl_tpi_m0_dt_r2` so a separately reviewed private source
prepare can substitute its include without changing all original host hooks.
Never include the original M0 and P2 headers in the same translation unit. It is
host-only and rejects `__CUDACC__`; no CUDA-visible structure/API is changed.

The base is original M0/P1, not the unsuccessful staged-load experiment. All four
forces use the original scalar `TimeStep=t_n`, `Nstep=n` and original external
load/drain policy. Neither this writer nor `EndpointPhase()` advances those fields.
This is not H3, a half-pressure reflection, a changed alpha, or a new spatial row.

## Private enable contract

`Enabled(false)` returns immediately, before any `getenv`, static policy
initialization, state allocation or file creation. Default A must use this original
pressure-helper OFF short circuit; malformed private environment cannot affect A.

For active B, the caller and `Init` require both:

```text
UPL_TPI_P2_ROWS_R1=2
UPL_TPI_M0_DT_R1=EQ40_RH1
```

Missing/empty P2 rows makes `Enabled(true)` false; any present value other than
exact `2` throws. With rows=2, missing/wrong old Eq40 policy throws. The resulting
policy is cached exactly once as in the original M0 header; changing environment
mid-process is unsupported. `Init` first rejects any scheme other than literal
`B`, before asking the private enable policy, and then independently requires it
enabled. This writer does not implement C or silently turn C into P2.

`AllowedDt(dt,event)` retains finite-positive and exact-bit comparison. This narrow
candidate allows only the original event `0.0100002288818359375 s` and
`dt=event/1000` (about 10.00022888183594 microseconds). The old optional event/500
candidate is deliberately not admitted here. No physical parameter or event is
adjusted to make this identity hold.

## API and actual call sequence

Original signatures remain: `Enabled`, `AllowedDt`, `Init`, `Record`, `Saved`,
`Finish`, `Need`, `Bits`, `Get`; `State` remains host-local. New `EndpointPhase()`
is only a checked query of this writer's expected phase, valid when it is 2 or 3.
It is not a phase setter and cannot certify which backend pressure round ran.
Root's integration should pass the independent actual CPU/GPU pressure helper's
`EndpointPhase()` into `Record`; the writer independently rejects a mismatch.
Do not introduce an unqualified namespace import that could shadow either query.

| Passed phase | Actual force | Counter | Expected next phase |
|---|---|---|---|
| 0 | Original predictor | `pre` | 1 |
| 1 | Original half corrector | `cor` | 2 |
| 2 | First full endpoint defect | `endpoint1` | 3 |
| 3 | Second full endpoint defect | `endpoint2` | 0 |

Each actual `FixedDt::GetDt`/`DtVariable` pass calls `Record` once. Phase2 does
not increment `completed` or advance `lastEnd`; phase3 alone increments it and
sets `lastEnd=time+dt`. Both endpoint passes still receive the unchanged source
step/time. This is scalar `+=dt` chronology, not a substitute `n*dt` clock.
An independent second force is mandatory: never manufacture phase3 by re-recording
phase2's bounds without its real force/rate computation.

For N successful updates, the writer therefore requires:

```text
pre = cor = endpoint1 = endpoint2 = completed = N
actual full force evaluations = 4N
```

This writer does not count or perform pressure-history/J/material/HG commits. The
separate P2 pressure helper must validate both rounds and commit pressure history
once; mechanics/J/material/HG remain their original single-update paths. In
particular, phase3 completion here occurs during its actual timestep check, before
the later final pressure write/BC/commit. It is an audit count, not a declaration
that the pressure transaction or physical timestep has already succeeded.

## Necessary bounds and signed intervals

Every record retains the original real positive finite values:

```text
bound = min(force_CFL, current-J skeleton-wave/AV_CFL, R_h hydro)
R_h = 1
error = dt - bound
```

The original `DtVariable` still rejects a locked step exceeding this necessary
bound. The old true-Kw wave remains diagnostic-only; it is not reintroduced into
the selected minimum. The passed HG limit reference retains the old unavailable
positive finite sentinel (`DBL_MAX`), and metadata still says unavailable. The
independent original HG safety guard is untouched; no false finite HG limit is
invented. No bound formula, coefficient, force/AV or hydro selection is changed.

Interval min/max reductions are identical to M0, now over all four actual phases.
`max_dt_minus_bound_s` keeps the signed maximum; negative values are not clipped or
replaced by absolute values. Initial `Extrema` remains all minima `DBL_MAX` and
error `-DBL_MAX`, with zero phase counts. A genuine initial save writes those empty
interval values with `interval_empty=1`; neither native dterror nor its sign is
rewritten by this helper.

## New evidence schema and failure behavior

All new outputs use `UplTpiP2DtR1`:

- `.policy.json`: stage `upl_tpi_p2_dt_r1`, B, rows2/four forces, original source
  clock and necessary-only Eq40 policy, no physical/stability claim.
- `.csv`: 21 columns, original actual save/step/clock/bound fields plus separate
  interval and total `endpoint1`/`endpoint2` counts; no old P1 CSV is overwritten.
- `.summary.json`: same new stage, updates and all four total counts, original
  extrema/end/save fields. It is written only by a separately called `Finish`.

`Saved` requires phase0, exact actual `lastEnd` and original saved-step convention
(initial0 or completed-1); all four interval counts must agree. It flushes the CSV,
then resets only interval extrema/counters. `Finish` requires exact supplied
completed count/end/last-save, phase0 and N in all four totals. Existing new sidecar
paths, duplicate owners/init, wrong phase/step/dt/source time, nonfinite/nonpositive
scales and I/O failure throw. Missing endpoint2 cannot be hidden by a later save or
successful endpoint1. A failure preserves partial new evidence; no retry, rollback,
summary fabrication or unsaved native state is promised. Normal summary completion
still does not establish row correctness, memory safety, convergence or physics.

Independent four-phase signed/native and first/second pressure-row review remain
necessary before any physical acceptance. Old three-phase reviewers may not
silently certify these products. Root must completely review and separately admit
any later prepare/build/program actions.

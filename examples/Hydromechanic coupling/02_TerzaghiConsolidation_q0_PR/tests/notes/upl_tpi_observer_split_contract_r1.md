# First observer split: saved text output only, not guard removal

2026-11-17. Design only. The actual source reference is
`outputs/upl_tpi_p1_loadclock_GPU_r1_source`, bound by its passed prepare receipt.
No source/runner/dependency is changed; no prepare/build/solver/reader/GPU command,
cleanup, Git or performance measurement is performed. The current B10us2s run remains
untouched. Accuracy review decides whether any production work is appropriate first.

## 1. Select exactly one small future patch

Select only **replace the successful save-time full pressure-observation export
with an explicitly different compact saved-guard summary**. Do not simultaneously
fuse kernels, cache maps, alter errors, remove snapshots, change cadence or modify
any numerical/state-update call. Keep the three P1 forces and staged-load clock,
original pressure/J/material/HG logic and all native22/signed/ledger/BC safety.

Narrow future host-only patch locations in `upl_tpi_gpu_r1.h` are:

- Init162-168: declare the new output schema/file identity, instead of advertising a
  complete28-column per-ID history file that will no longer be written;
- Saved213-218: retain every lifecycle guard and `MapCheck -> CollectDevice -> Check`
  in its original position, then omit only the successful bulk Observation D2H copy,
  host vector/1000-row formatting and full-history CSV flush;
- Finish224-228: mark full_history_csv_written=false and compact schema explicitly,
  retaining all existing numerical/lifecycle totals and original finish guards.

A compact CSV can contain part, actual time/saved-step, commits, endpoint calls,
core/HG check counters and successful saved-guard completion. It must have a new name,
for example `UplTpiGpuR1.compact.csv`, and an independent schema identifier; it is
not a sparse file masquerading as the old full history. No new public XML/ENV option
is proposed. Any later private author patch is a separately reviewed implementation.

Keep the existing device `collected` buffer allocation and complete CollectKernel
body for this first patch, although its observation copy becomes unused by the host.
That avoids a CUDA/header-prefix/kernel change. Keep the same APIs and all host/device
numerical fields. Only the host implementation section/CSV path should differ; the
old device-visible helper prefix, cuh/CUDA objects and HG class tokens must be identical.

Removing an optional text file changes its disk-capacity/I/O-failure surface. This
is an intentional output behavior difference, not permission to suppress a physics
error or native-write failure. Compact/native output failures must still be reported.
No speedup is assumed: per-step guard synchronization remains unchanged in this patch.

## 2. What remains, even if called diagnostic

| Must remain in the first patch | Reason |
|---|---|
| Original two mechanical forces plus genuine full endpoint force/rate | Third force supplies the selected pressure residual and acceleration feedback. |
| Every error Reset/Check/MapCheck and device row validity check | Removing/resetting them can change rejection and commit behavior. |
| Every native ID/role/map/periodic check | History is ID-owned while slots change during sorting/duplication. |
| Endpoint soil core snapshot and all bit comparisons | Still proves the extra force does not advance x/v/rho/sigma/kappa/P0/J. |
| HG history/rate D2D snapshot plus Stats24/RateInfo15 comparisons | Still proves the endpoint force reads committed HG memory without updating it. |
| Original HG physical force/history/rate/tau/spin/work/elastic gates | These are actual method/scope constraints, not optional plotting telemetry. |
| Method-specific three-phase signed-dterror check and original necessary limits | A smaller text output does not relax the timestep. |
| Native22, true scalar clocks/Step/dt, IDs, P0, J/n/V/rho/k ledger and real drain checks | These are the numerical result and required acceptance evidence. |
| Saved MapCheck/CollectDevice/Check | CollectKernel also validates final pressure and J; its purpose is not only CSV extraction. |

The new light loadclock and M0 interval sidecars already emit one row per native save;
keep them unchanged. Never claim that dropping CSV also removes the14 per-step TPI
error D2H calls or repeated full force: this selected patch removes neither.

## 3. Error reset ordering must not be weakened

`cuh:41` explicitly overwrites device error bits with0 and firstId withUINT_MAX.
A reset can erase an earlier unobserved error; it is not harmless initialization
once work has begun. Current `MapCheck` is `ResetError -> Map -> Check`, and each
pressure stage checks its own work before later stages can reset that shared packet.
On the ordinary path Begin/Corr/CaptureJ/Guess/StartEndpoint/Prepare/Write/Commit have
14 actual GetError observations. A saved reset follows successful prior step checks;
CollectDevice then gets its own immediate Check. Keep every one of those operations.

Do not delete one Check while leaving the next Reset in place: an invalid source,
missing ID, nonfinite row or illegal final BC could then disappear before rejection.
Do not simply delay a check until a native save: pressure/history may already have
committed on invalid data. Any proposal to latch errors across stages, guard later
kernels on those bits, merge reductions or move rejection is a **different safety
implementation**, not output-only, and is excluded from this first patch.
The existing failure/partial-output contract remains unchanged; no retry or recovery
from an unsaved in-memory state is added.

## 4. ID-map checks are not an output counter

The actual half cell division at `JSphGpuSingle.cpp:904` follows the predictor; the
full cell division at1218 precedes StartEndpoint. Sort/periodic operations can change
particle slots and counts. Begin/Corr/CaptureJ/StartEndpoint/Commit currently rebuild
and validate their owner map independently; saved MapCheck repeats that validation.
Some mappings might later be reused within proven no-sort intervals, but that would
need a separately specified map-version/role/periodic contract. A stale map can write
another particle's pressure/history while still producing finite numbers.

This patch keeps all five ordinary-step MapChecks and the saved MapCheck. It does not
assert that only the two visible cell divisions are the only possible reordering sites,
and does not infer map validity merely from unchanged total native counts.

## 5. Why not put readonly checks behind Debug now

Endpoint core/HG comparisons are observers in the numerical formula, but they reject
an unintended state advance or memory mutation in the present implementation. Removing
them in Release changes the set and timing of accepted/rejected executions. Retaining
only Debug checks could be considered after an explicit independent safety decision,
actual no-feedback regressions and a new evidence policy; it is not this output-only
patch. In particular, original HG tau/spin/work/finite/ID constraints never become
Debug-only as a side effect of such a choice.

## 6. Required regression evidence before using the compact writer

Root would independently admit any implementation/build and smallest relevant tests.
Reuse existing completed checked results as references when actual clocks/inputs match;
never rerun them merely for a new label and do not add automatic half/full chains.
Required evidence includes:

1. Same source/input/physical ENV, compile/arithmetic flags, CUDA objects and genuine
   owned run identity. Only the declared host output implementation may differ.
2. Actual common saved states compared through all22 typed native arrays, native IDs,
   exact scalar/Step/dt and signed dterror records, with both original headers retained.
   Five exports or rounded histories are insufficient for an all22-bit claim.
3. Unchanged original HG/J/pressure/BC/signed guards and actual counters. No observer
   deletion may hide a failure; initial signed sentinels remain unmodified.
4. Pressure-history pn/previous/final and actual HG History/HistoryRate at matching
   native IDs and specified phase/time. The checked program's existing detailed CSV
   supplies some pressure-history evidence, but native22 does not expose all HG memory.
   Where genuine old hidden snapshots are absent, do not reconstruct or claim them:
   root must separately admit a small instrumented qualification/fixture comparison
   or explicitly limit the claim. Same actual hidden arrays must be compared, not
   their norms or a guessed history inferred from later native fields. A qualification
   observer must itself be readonly and leave the numerical call/update order unchanged.
5. Default-A/OFF regression with actual matching native states as before. The compact
   writer must not create a new A-side output/context path.

Read-only/source evidence plus unchanged step-by-step readonly guards supports this
narrow split, but does not by itself fabricate all hidden-memory byte equality.
New compact output cannot be fed into the old per-ID pressure-formula reviewer and
reported as if that reviewer had all its old observations. Keep a separate compact
review that consumes unchanged native/signed guards and the explicit output limits.

Only after accuracy and this numerical/no-feedback review could controlled timing
assess the benefit. This note admits no code edit, build, program, cleanup or production
merge, and claims no faster runtime or exact-HG restart support.

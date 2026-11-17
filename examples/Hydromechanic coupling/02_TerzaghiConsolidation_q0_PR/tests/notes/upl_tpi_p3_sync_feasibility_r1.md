# P3 synchronization feasibility: narrow design reserve

2026-11-18. Read-only audit; only this new note is written. The active full2Tv
owner51340/solver35020, its source/program/scripts and all dependencies remain
untouched. No build, solver, reader, profiler, analysis rerun, hash or optimization
is performed. Anchors below use frozen outputs/upl_tpi_p3_GPU_r1_source; the full
candidate copied its helpers/CUDA unchanged and extended only a Single qualifier.

**Existing evidence, not a new measurement.** The passed cost_root_r1.review.json
separately preserves the failed original probe postcheck. Its 2000-update trace
has 22.48455 s summed kernels and 33.77919 s cudaMemcpy API durations. They overlap
and must not be added. The 210-save probe has about16.6x the full2s save density;
neither total nor API time predicts full2Tv cost or a speedup. Source attribution
already closes24B/10000 as physical top-band totals;8B/100637 as GetError70632,
skeleton wave10000, domain limits16004 and CellSize4001. Of152638 four-byte copies,
142635 are source-identified;10003 remain unattributed. Do not repeat that audit
or assign the gap by guess. The prior observer_split_contract and CPU skip audit
remain reserves, not implemented performance improvements.

| Candidate class | What is actually possible / what must remain |
|---|---|
| Exact duplicate host observation | A narrowly checked NextEndpoint -> StartEndpoint duplicate GetError can be considered first; details below. No device error producer or numerical call is removed. |
| Saved observation batching | h265-280 emits three bulk Observation copies and three CSV streams. Bounded host formatting/write batching can retain the same record bytes and save boundary. Async D2H needs pinned-buffer lifetime/completion/error semantics; it is a separate candidate, not a free replacement. Saved Map/Collect/Check and native/signed output remain. |
| Snapshot grouping | h206-208 takes core and HG-history/rate snapshots before each endpoint; h225-228 compares host Stats24/RateInfo15 and device core/H/rate. Keep every field and every round. These are not disposable counters; moving checks or fusing device work is a separate safety/kernel change. |
| Same-generation geometry cache | Prior source audit identifies fixed geometry/FS/C/LS geometry within the three full endpoints. A cache requires explicit generation/role validity and exact retained-result evidence. It is not an output-only synchronization patch and is not selected here. |
| Pressure-dependent physics | Wall pressure, current Ace and wall Ace, full LP/gp/Da/closed-FS residual, actual q2/q3 and AceMax must be fresh each round. No cached previous residual/force or half theta is acceptable. |

**First small candidate: two redundant packet observations, not35 checks removed.**
In h245-251, NextEndpoint validates the completed provisional transaction, then
line250 calls Check(), changes host-only flags, and immediately calls StartEndpoint.
StartEndpoint's host Need checks/GetFirstId/GetCount lead to another Check at206
before MapCheck. There is no intervening CUDA API, device producer, reset, map,
sort, force or data update on that exact path. The first blocking GetError has
already observed the packet and completed preceding default-stream work. A future
host-only explicit successful-check ticket could suppress only the second Check
for these two proven Next -> Start transitions; first-round entry keeps its Check.
The ticket must be consumed once, tied to the current owner/round/error generation,
and invalidated by any intervening CUDA API/reset/producer. Do not infer a ticket
merely from unchanged numeric error bits or add a general skip-check selector.
The original first rejection stays before host transition flags and Map reset.
At most2N duplicate8B calls are removed; their cost is not known and may be small
because they follow an already completed read. This is no throughput promise.

**Why broader GetError grouping is not presently equivalent.** cuh41 overwrites
the packet; h150 MapCheck resets it before rebuilding slots. Omitting an earlier
observation can erase a source/row/commit error. Map's completed check must precede
SnapshotKernel(cuh136-138), whose slot dereferences do not protect against a failed
map. Likewise Prepare(cuh144-151) must succeed before WriteRaw152-154; ValidateCommit
155-159 must succeed before Commit160-162 rotates pressure history. Those are
transaction boundaries, not save-time telemetry. Sticky errors and device-guarded
successor kernels could support later grouping, but would change device code and
failure execution/timing; they are not this host-only candidate. ExtraForce must
never proceed from an invalid map, snapshot or provisional BC for convenience.

Grouping core/HG snapshots across all three rounds is also unsafe without a new
contract: Snapshot resets seen and captures the round's real q, while q changes
q1->p1->p2 (q1 is the actual predicted float). H/rate are fixed committed readonly arrays, but the current code checks
them at every actual force; a shared baseline with delayed checking changes
rejection timing. Stats/RateInfo are host getters, not per-ID D2H. The HG AddReadonly
reduction at h213-220 validates actual finite force and cannot simply disappear.
Mapping cannot be cached across predictor/full RunCellDivide or periodic renewal
(Single901,1208); unchanged1040 native IDs do not imply unchanged slots.

**Independent qualification before any future use.** Review one exact host diff
and retained CUDA/device-prefix proof; test success and injected failure paths for
stale ticket, unseen error, owner/round mismatch, reset, missing/duplicate/changed
role IDs and failed provisional BC. Verify the same first error and zero illegal
pressure/history commits; a source proof alone is insufficient. On matching actual
saved clocks compare all22 typed raw arrays, IDs, Step/dt and signed records with
headers intact, plus actual pn/previous and hidden HG History/HistoryRate at defined
phases. Existing five exports and HG norms/counters cannot prove all hidden bytes;
where old snapshots are absent, report that limit rather than reconstruct them.
Keep default A untaken, five numerical force/rate calls, single material/J/HG-history
commit, all three endpoint rows and all original bounds/BC/ledger/safety. Any new
compressed observation schema must be honest and independently reviewed. Only then
could separate comparable timing assess benefit; current full computation is not
an optimization experiment and supplies no permission to alter its dependencies.

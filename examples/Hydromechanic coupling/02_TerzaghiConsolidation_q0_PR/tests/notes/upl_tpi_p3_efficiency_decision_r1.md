# P3 efficiency decision reserve — no action admitted

2026-11-17. Only existing small run/build receipts and their one-row Run.csv files
were read. No large table, process, active dependency, hash, profiler, script main,
reader, build or physical program was operated on. Only this new note is written.
P3 native/method/scientific acceptance is the root's independent task and remains
a prerequisite to any full2Tv decision. Performance cannot waive a failed physics
budget or turn solver completion into acceptance.

## Observed records, not controlled performance results

All times below are the actual Run.csv TSimul loop fields, excluding independent
native analysis. They include each run's actual instrumented solver output. These
are single runs with different dates, conditions and sometimes methods/configs;
they are not isolated repeats or controlled speedup measurements.

| Existing tag (under tests/outputs) | Backend / updates / frames | TSimul seconds |
|---|---|---:|
| `upl_tpi_m0_dt_B10us_window2s_GPU_r1` | RTX3050 Release / 199996 / 1263 | 2408.810059 |
| `upl_tpi_p2_B10us_window2s_GPU_r1` | RTX3050 Release / 199996 / 1263 | 3236.284912 |
| `upl_tpi_p3_B10us_window2s_GPU_r1` | RTX3050 Release / 199996 / 1263 | 3810.424561 |
| `upl_tpi_cpu_ReleaseCPU_A_startup015_r1` | CPU1 Release / 24000 / 344 | 249.370483 |
| `upl_tpi_cpu_ReleaseCPU_B_startup015_r1` | CPU1 Release / 24000 / 344 | 365.584503 |
| `upl_tpi_cpu_ReleaseCPU_C_startup015_r1` | CPU1 Release / 24000 / 344 | 356.340912 |
| `upl_tpi_gpu_Release_A_startup015_r1` | RTX3050 Release / 24000 / 344 | 199.877518 |
| `upl_tpi_gpu_Release_B_startup015_r1` | RTX3050 Release / 24000 / 344 | 318.201996 |
| `upl_tpi_p3_cpu_debug2ms_r1` | CPU1 Debug / 200 / 18 | 36.163887 |

The small problem has1040 total /1000 soil particles, so launch/synchronization and
logging overhead may matter, but their share has not been measured. The recorded
old CPU Release loops do not demonstrate that CPU already beats GPU. The Debug
record cannot be used as a Release performance prediction. The old CPU1 full A
run `upl_bigstep_2tv_CPU1_r1` took148603.906250s for11661219 updates /1682 frames;
it is a different finite-Kw method/build/window and does not control P3 efficiency.
Do not extrapolate any of these to a new full run as if costs were constant.

Both `logs/upl_tpi_p2_ReleaseCPU_r1.build.json` and
`logs/upl_tpi_p3_ReleaseCPU_r1.build.json` are actually passed,86-object ReleaseCPU
builds. Thus a real P3 ReleaseCPU program exists, but no P3 ReleaseCPU physical loop
or performance result was found among the current P3 run receipts. A build is not
the missing backend/native qualification. No canonical executable is substituted.

## Three different options

1. **Reduced observation first, conditional on accepted P3 physics.** The current
   private path has dense round CSVs, full first/second snapshots, host formatting
   and frequent small error reads. `upl_tpi_p2_static_cost_r1.md` documents P2's
   source counts; they are not automatically P3 counts. Selective CSV formatting
   or saved observation frequency can be reduced without changing pressure/J
   arithmetic. That does not authorize deleting required finite/owner/map/BC/HG
   checks, or losing errors before another ResetError. New metadata/review must
   state the real observation count; an old full-row reviewer cannot certify
   missing rows. Raw native outputs, clocks and original safety remain protected.

2. **CPU Release is a bounded backend question, not a presumed solution.** It avoids
   GPU launch/transfer overhead, but performs all five P3 force evaluations and
   CPU diagnostics; single-core wall reconstruction/neighbor work may dominate.
   Existing shorter ReleaseCPU data above are useful context only. Consider one
   already-defined bounded ReleaseCPU qualification/timing job only if its real
   program/actual environment and same-method native gates can be bound. Do not
   migrate the long calculation merely on small-grid intuition, compare Debug
   against Release, or use different dt/output/method as a backend speedup claim.

3. **Pressure-only endpoint work is the larger design opportunity.** See
   `upl_tpi_pressure_only_feasibility_r1.md`. Fixed full-endpoint geometry/J/C/FS,
   theta and pressure-independent work can sometimes be cached; current pressure,
   a(p), pressure/acceleration ghosts, LP/gp/Da/Neumann must be fresh. Preserve the
   original total-stress/pressure/AV accumulation order before attempting an
   aggregate cached-force split. This requires real numerical/lifecycle proof;
   it is not a logging switch and cannot replace full R_gamma now. It may cost
   more development than simply finishing a scientifically accepted diagnostic.

## Evidence required for one later root-admitted action

These are alternatives and decision conditions, not an automatic three-action
sequence, a new half/reference chain, or permission to execute anything now.

| Possible single action | Necessary evidence before admission | Honest outcome |
|---|---|---|
| One privately tagged reduced-observation candidate on an existing bounded plan | Root-accepted P3 science, exact scope showing which observation is removed, complete safety/error-latch retention, frozen new source/program and explicit new sparse-output review schema; retained P3 provides actual common-clock comparison without rerunning it | Report real exits, all original native/signed/ledger/drain/HG gates, actual observed records and physics-field comparison. Its one timing is still an observation, not a controlled speedup. |
| One existing bounded P3 ReleaseCPU qualification/timing job | Actual passed86-object program/build/runtime, explicit CPU1 or admitted thread environment, unchanged physical plan/material/operator, independent CPU/GPU match only at genuine common times/steps | Report actual loop/total time and backend/native errors. No interpolation or new half-step equivalence; a CPU result does not admit a full run automatically. |
| Author a pressure-only numerical component, no solver | Root full-read operator split and cache lifetime/owner rules; explicit retained full-R qualification truth, preserved float/BC and force-source timing, clear failure semantics | Only an arithmetic/implementation candidate. A component pass is not SPH stability, speed, paper accuracy or physical acceptance. Any later physical action is separately admitted. |

For a meaningful later runtime comparison, record physical endpoint and actual
steps, backend/configuration/hardware, thread settings, diagnostic/CSV settings,
native-save count, loop TSimul and total wall scope. A different observation mode
can expose overhead but is not the same fully instrumented benchmark. Reusing
the accepted prior run avoids a duplicate reference solve, while also requiring
that differences in ambient load and instrumentation be disclosed. No new exact
prefix/half chain is justified merely to improve a timing table.

## Decision order

Finish P3's original physical review first. If it fails, preserve the failure and
diagnose the relevant numerical error; faster output cannot repair that failure.
If it passes, keep that accepted result/program as truth, then choose at most one
of the narrowly justified actions above. Pure observation reduction has the lowest
numerical risk; CPU Release remains an evidence question; pressure-only work is
the likely larger structural saving but also requires the most numerical proof.

Current instrumented P3 has not demonstrated the intended total-cost advantage
over the baseline. Neither its added timestep nor a prospective optimization is
a speed guarantee. Full2Tv, server delivery and public-source acceptance need
both the original accuracy/safety gates and a defensible end-to-end cost decision.
No action, retry, watcher, build or new physical run follows from this note.

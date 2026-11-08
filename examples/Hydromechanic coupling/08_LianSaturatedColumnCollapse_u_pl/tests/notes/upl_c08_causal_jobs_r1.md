# C08 causal observer jobs ? author only

`support/upl_c08_causal_jobs_r1.py` was only authored and AST checked. It was not imported or executed. No XML/plan/BAT/seed, GenCase, solver, decode, VTK or queue attempt was created. No old source/helper/input/runtime/PRE was changed. Root must freeze/review the four-file observer and close all three causal builds before invoking any action.

Independent commands (no automatic sequence):

```text
python upl_c08_causal_jobs_r1.py prepare smoke --execution-authorized
python upl_c08_causal_jobs_r1.py smoke --execution-authorized
python upl_c08_causal_jobs_r1.py prepare window --execution-authorized
python upl_c08_causal_jobs_r1.py window --execution-authorized --notify
```

| Profile | Tag/output | Configuration | New updates / global end | TimeMax / TimeOut | PARTs |
|---|---|---|---|---|---|
| smoke | upl_c08_causal_smoke_GPU_r1 | Debug + memcheck | 10 / 4000010 | 10.000025 / .000025 s | one forced final |
| window | upl_c08_causal_window_GPU_r1 | Release | 360000 / 4360000 | 10.90 / .01 s | 90 |

Prepare writes only fresh tests/configs XML/test BAT, output/planned_steps.csv and logs/<tag>.prepare.json; no executable runs. Each later physical action calls official runtime_r6 GenCase once, then one solver. Whole-tree checks retain root r6 numerics: original r2 GPU ten-second PRE, dt2.5us, AS .2/n3, CompletedOnly, fixed-plane NoPen, keep5/retire255. Only TimeMax/TimeOut and truthful comments, absolute original PRE binding, exact two generated VTK labels and generated date differ. Plan is part,completed_step: smoke [4000010], window 4004000..4360000/4000. Native time/header is never replaced by n*dt.

Each job requires logs/<tag>.admission.json: passed=true, allowed_job=<tag>, ArtificialStressCoef=.2, ArtificialStressExp=3, FreeSeepagePondingPolicy=CompletedOnly. Window adds smoke_trace (stat Entry) to the real new-schema passed smoke checker with trace/totals Entries. Window also requires sealed smoke run + memcheck0 + logs/upl_c08_causal_smoke_GPU_r1.native_r1.json with original native guards, one final frame/global4000010 and actual ten-update cumulative counters. No future checker filename or passed admission is invented by this author.

Known prerequisites are logs/upl_c08_causal_{DebugCPU,Debug,Release}_r1.build.json, source_capture outputs/upl_c08_causal_source_r1/source.json and archive, true exit0, source/protection flags and 87/113/113 objects. CPU macros are off; GPU CL/NVCC has both C08_STAGE_TRACE and C08_CAUSAL_TRACE. The built causal native utility is bound, never launched. Seven known DLL/config files are copied only if missing beside the isolated program, from runtime_r6, with actual bytes plus size/mtime comparison; existing files are never overwritten.

Unchanged base.owned acquires real sanitizer/tool and solver handles, records creation/exe/exact argv/parent, and waits/captures true Popen and native Win32 exits before postchecks. Every30s status reports only the last complete original PART console line. Original Run.csv registry is7060/2060/2060; contiguous PARTs and no exclusions are checked. Separate native review retains6805/1805/5000, all22/P0/J/ledger/rho/cache/kappa/FS/AS/keep/plane/actual scalar/signed guards. Exit0 is not physical acceptance.

Run success preserves program/source_build/source_capture/source_archive/source_pre_file/input_xml, seed[3], planned_steps, actual GenCase_call, preparation, actual_call, runtime, consumed, actual_exit/actual_Win32_exit, actual_steps/saved_frames and consumed_stats_unchanged. Start/call/owner_admission use the existing base schema. New stat keys: trace_file=C08CausalTrace.csv, totals_file=C08CausalTotals.csv. The owner does not scan the large RHS CSV or replay numerical terms; the small totals table checks IDs7017/5944/6814, four counts equal to actual completed_step minus4000000, errors0 and final10/360000. Scientific/algebra review remains separate, not the incompatible old57-column checker.

Source sampling is every40 steps in [4000000,4360000), dense only [4316000,4324000) and [4332000,4340000):24600 sampled starts/window, with actual extra events retained rather than fabricated row counts. Smoke samples step4000000; final PART and cumulative counters cover all ten updates. The full90 no-feedback prefix comparison with actual r6 follows unique native decoding; no new reference solve is required here.

Only root-started window --notify can make one same-thread terminal queue attempt, recorded first with45s timeout. Timeout delivery is uncertain; no resend/rearm/watcher. No automatic next solver/native/VTK/PRE/other psi/half chain, no SHA/source-hash or old-object walk. Root independently decides later work under existing authorization. Unresolved physics is not accepted by this observer.

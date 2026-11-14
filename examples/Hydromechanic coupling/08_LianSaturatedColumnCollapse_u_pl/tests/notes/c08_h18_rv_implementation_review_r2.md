# Transparent Debug2 runtime recovery: implementation review r2

AUTHOR ONLY. New files are `support/c08_h18_rv_implementation_review_r2.py` and this note. No original runner, run/start/call/status, old review, source, program, native output or sidecar is edited. The earlier OFF1 implementation review stands and is not rerun. Root fully reads these new files and independently admits any future execution. No build, help/program call, solver, native reader, VTK, Git, SHA, watcher or queue is executed while authoring.

## Preserved failure and the separate runtime record

The original `c08_h18_rv_debug2_GPU_r1.run.json` must remain `passed=false`, `solver_completed=true`, with the exact first failure `Actual schema2 RV policy differs`. Its real solver, tool and Win32 exits must all be0, ownership must be intact, and it must contain no engine exception. The original wrapper used `m.f32(.072)`, which returns packed float bytes, when comparing the numeric policy H. This is a post-solver type-check rejection, not a numerical or physical failure and not permission to rerun the completed solver. A different or additional original failure cannot enter this path.

A new independent runtime-recovery receipt must be passed and stat-bound to this unchanged original run. Its canonical `rv_policy`, `rv_sidecar`, `rv_manufactured`, `memcheck_actual_call` and `memcheck_zero_errors_and_leaks` observations are consumed. The actual call remains the original sanitizer/solver call; no replacement execution is manufactured. The separate native receipt's `source_run` must **still bind the failed original run**, never the recovery JSON or a synthetic passed run.

The new inspection view is a shallow copy preserving every original field, including `passed=false`. It adds **only** the three missing output-stat aliases `rv_policy`, `rv_sidecar`, `rv_manufactured` from the independent recovery. Memcheck facts are checked directly from the recovery alongside the original actual call/log, not overlaid as an invented original field. No new original run is written and the old result is never promoted to passed.

## Unchanged native and numerical gates

The original `check_native` code is retained with only the declared source-text changes: add the recovery argument; read/require the recovery and exact known failed-wrapper condition; narrow the file pair to this single named old run and recovery; replace the original passed-run eligibility with that explicit condition; obtain the missing memcheck aliases from the recovery; bind the recovery receipt among consumed files; return it separately. All original owner/start/argv/environment/program/PRE/source/build/native/clock/ledger/safety checks and numerical limits remain. Author-only static inverse transformations recover the original function text.

The new tool reuses the frozen r1 `on_debug`/certificate/table functions directly. It checks both native states at completed2000001/2000002, all6805 IDs and22 arrays, original scalar clocks/signed diagnostics/P0/J/ledger/active FS/contact guards, actual sanitizer command and zero errors/leaks, exact schema2 Policy, all four66-column Pre/Cor saved stage records and three40-column first-force manufactured modes. The original stage work/net-force/torque/normal/float-commit/lambda gates and all <=1 ratios are unchanged. Running counters/maxima are independently checked over the four fully observed actual stages.

Derived work/torque residual export arithmetic keeps the r1 large-operand cancellation scales, not the small final residual scale; this does not widen any original physical/certificate budget. Manufacturing is same-body GPU scratch-only evidence, not Debug/Release bit equality. Offline checks do not reconstruct unexported neighbor primitives or turn the manufactured null budget into a substitute for nonaffine-stage mechanical certificates. There is no OFF1 rerun, .90s analysis, new time integration, half chain or physical/paper/clumping acceptance.

Only the `debug2` CLI profile exists:

```text
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_rv_implementation_review_r2.py --profile debug2 --run-receipt ORIGINAL_FAILED_RUN_JSON --runtime-recovery INDEPENDENT_RUNTIME_RECOVERY_JSON --native-receipt UNIQUE_NATIVE_RECEIPT_JSON --execution-authorized
```

The only future output is a fresh `logs/c08_h18_rv_debug2_implementation_review_r2.check.json`. It records the original run stat/failed status/first reason, the separate recovery stat, the actual native receipt, the three explicitly added inspection aliases, unchanged original thresholds and all scientific scope limitations. A failed offline review preserves original evidence and writes its first actual reason; existing complete/failed analysis rejects. It never repeats a solver or decoder, changes an original header, infers an unsaved state or launches the next job.

# Debug2 RV known-type runtime recovery r1

## Purpose and immutable original

Author-only offline script: support/c08_h18_rv_debug2_runtime_recovery_r1.py. Root must read it before a single authorized execution. It never calls prepare/run/invoke/notify, any program, reader, VTK, build, Git or SHA. Importing the future runner only defines/reuses its corrected telemetry and unchanged Run.csv parser; no main executes.

The sole accepted original is logs/c08_h18_rv_debug2_GPU_r1.run.json with passed=false, solver_completed=true, first_failure exactly "Actual schema2 RV policy differs", one captured solver launch, genuine solver/tool Win32 and Popen exits0, owner identity valid, two actual saved PARTs and global completed step2000002. Original files and flags are never edited. The actual raw log contains zero memcheck errors/leaks. No lost LASTEXITCODE, new exit or unsaved state is invented.

The postcheck bug is specific: m.f32(.072) returns four packed bytes; actual policy kernel_h_sph_float is the corresponding numeric float32 value converted to JSON double. Prepare's comparisons of packed bytes on both sides are valid and stay unchanged. The new runner differs from the old by exactly the five documented type/note/window-CLI replacements. Recovery verifies that transformation from the original bound script before using the corrected runtime helper.

## Narrow input and checks

The script binds the actual old run/start/call/preparation/admission, original consumed stat list, relevant program/private source/PRE/input/plan/runtime/seed stats, Run.out/Run.csv/PART stats, and the three newly consumed sidecar stats. Existing historical size/mtime bindings are verified; this does not create a retrospective sidecar seal. The sidecars and raw log are sealed at this recovery's first consumption. No object inventory or raw BI4 hashing is added.

It checks captured owner PID/creation, parent chain, actual target exe/argv and all three zero exits, normal schema2 completion, original two-part Run.csv coverage, exact original scalar source+dt clocks and two-step plan. Corrected telemetry then repeats the previously unreachable original runtime subset: schema2 policy, exact 66-column main header, four saved Pre/Cor rows with genuine source-n clocks and phase counters2, validated5000/committed/status safety, and three manufactured rows. Original numerical work/torque/manufactured certificates remain the separate implementation review's responsibility; this script does not replace that review or native22 validation. The memcheck assertions independently reread the actual captured call's raw log for zero errors and zero leaked bytes/allocations.

No new physical tolerance is added; the only expected-value correction changes Python type, not float32 H. No solver, decoder or telemetry output is rewritten.

## New exclusive output and consumer contract

One new exclusive output:

logs/c08_h18_rv_debug2_GPU_r1.runtime_review_r1.check.json

Canonical fields expected by the independent native/implementation review are:

- original_run: the original failed run stat; passed and consumed_stats_unchanged on this new review.
- rv_policy, rv_sidecar, rv_manufactured: actual consumed canonical file stats.
- memcheck_actual_call: the original actual call stat; memcheck_zero_errors_and_leaks=true only after raw-log verification.
- known_original_failure, original_passed_false_preserved, policy_type_bug: explicit recovery provenance.
- actual_steps=2000002, saved_frames=2, actual_end_s and original planned_steps.
- solver_invocations/reader_invocations/VTK_invocations/GenCase_invocations=0 for this offline action, SHA_scans=0.
- native_review_pending=true, physical_acceptance=false, automatic_next_job=false.

The native receipt's source_run must continue to point at the original run, not this recovery. A later implementation review records original_run and runtime_recovery independently; it may consume this passed runtime recovery plus genuine native result, but must never falsify the original passed=false. If recovery fails, preserve its new failed check and diagnose derived analysis only. There is no permission to rerun the completed Debug solver or overwrite this output.

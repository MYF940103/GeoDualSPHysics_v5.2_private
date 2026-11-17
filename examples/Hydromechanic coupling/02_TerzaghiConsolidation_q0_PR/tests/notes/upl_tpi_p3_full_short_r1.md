# P3 full-scope minimal short implementation regressions (author only)

New support/upl_tpi_p3_full_short_r1.py and this note are author-only assets.
No context, planner, admission, program, reader, solver, build or summary has been
executed while authoring. Each --phase run invocation selects exactly one job;
summary is another independently admitted action. No queue, automatic native
read, following job, half chain, new reference or physical parameter test exists.

The source candidate changes only the Single.cpp M0 allowed-TimeMax expression.
The minimum agreed runtime coverage reuses three genuine original P3 controls:

| Mode | Configuration/scheme | Updates / native frames | Actual old tag |
|---|---|---|---|
| cpu_debug2ms | DebugCPU / B | 200 / 18 | upl_tpi_p3_cpu_debug2ms_r1 |
| debug2 | GPU Debug / B, memcheck | 2 / 2 | upl_tpi_p3_gpu_debug2_r1 |
| Acontrol | GPU Release / default A | 320 / 18 | upl_tpi_p3_Acontrol_gpu_r1 |

Each exact old logs/<tag>.run.json and <tag>.native_review_p3_r1.json is actually
passed with the original P3 run/native stages. Input seed, plan, dt, scalar end,
argv, output cadence, ramp/drain and original physical model are reused. Only
the output argv is redirected; executable/runtime come from the new full-scope
build. CPU B actual end is .002000045776367196 s, GPU B2 is
.000020000457763671876 s and A320 is .002000045776367195 s. These are independent
actual scalar clocks, not n*dt substitutions. No post-drain state is covered.

New fixed tags are upl_tpi_p3_full_cpu_debug2ms_r1,
upl_tpi_p3_full_gpu_debug2_r1 and upl_tpi_p3_full_Acontrol_gpu_r1. Their run stage
is upl_tpi_p3_full_short_r1.run, never the old P3 run stage. Source binding is
logs/upl_tpi_p3_full_{CPU,GPU}_r1.prepare.json with stage
upl_tpi_p3_full_source_r1.prepare; build binding is
logs/upl_tpi_p3_full_<cfg>_r1.build.json with stage upl_tpi_p3_full_build_r1.
It requires actual new one-Single replacement, retained 85/110 objects, original
267/270 source inventory, unchanged helpers/CUDA/ABI, exact full expression, and
the genuinely built new program/runtime. An old P3 build cannot be substituted.

Existing original.own_solver / original.run_owned functions are reused directly
for their actual context-tagged ownership and Win32/Popen capture. They contain
no hardcoded source/build stage. The old context, source_build, notification,
get_job and main functions are never called. Original check_output is reused
only for unchanged runtime numerical/sidecar schemas. There is no monkeypatch,
global mutation or fabricated old receipt. CPU duplicates the genuine child
handle; GPU captures tool and target separately, verifies exe/argv/creation and
waits only its owned processes. The original exact allowed-paused GPU identities
must be supplied by root; active or unrecognized solvers are rejected and are
not stopped/resumed/restarted. Failed exits, first error and raw last PART stay
preserved; no failed/completed output is overwritten or retried.

All six pressure/M0/P1/P2/P3 selectors are explicitly cleared by the unchanged
tracked_environment function. B selects its actual backend=B, M0=EQ40_RH1,
P3_ROWS=3; P1 load clock and P2 are absent. A selects only GPU=A, with all other
prototype selectors absent. Actual selector values are in start/call/run; CPU
uses one OpenMP thread. GPU Debug requires genuine compute-sanitizer memcheck,
actual once-only 16-case fixture in console and zero errors. A must create no
prototype sidecars. B retains all three pressure rounds, five-phase dt, actual
HG2N/N/N lifecycle/cache and original finite/tau/spin gates. Run success is only
pending independent native and implementation comparison.

The original compiled four-profile M0 reader already supports these exact three
profiles; no new C++ reader/profile is necessary. A separately authored/admitted
thin native adapter must bind the new run/source/build honestly, then call the
existing reader at most once and independently review all22 arrays/IDs, actual
clocks, signed intervals, ledger/BC/HG and unchanged P3 pressure formulas. It
must compare only true old/new same-clock saved records and preserve headers.
Five exported binary series alone are not proof of all22 raw-array bit equality.
No old hardcoded run identity checker may be invoked under a renamed stage.

Expected new independent review receipt is
logs/<newtag>.native_review_full_short_r1.json, stage
upl_tpi_p3_full_short_native_r1.review, passed=true, job.mode and exact
job.run_receipt stat binding, with its actual comparison result. The later new
GPU Debug run requires the new CPU review; A requires both new B reviews. The
first CPU run has no new runtime prerequisite beyond its actual build and old
control. No next job is launched by passing any gate.

Each action admission has stage upl_tpi_p3_full_short_r1.<run|summary>_admission,
passed=true, action_only=true and a unique inputs stat list. Run admissions carry
job {mode,tag,configuration,scheme,build}; Debug also supplies memcheck_program.
required_passed_checks pins the preceding independent new native review(s).
Inputs include this script/note, original P3 runner/note and its imported M0/
CPU/GPU owner modules, actual build/source/program/runtime and critical executed
source/helper files, base/source-diff receipts, old passed run/native, original
three seed files/plan, new prerequisite reviews, psutil and genuine memcheck tool.
The script performs no SHA scans. Existing output or any start/call/run/status/
console/memcheck/notification path causes refusal, without process replacement.

```text
D:/anaconda3/python.exe -B tests/support/upl_tpi_p3_full_short_r1.py --phase run --admission ROOT_JOB_JSON --execution-authorized
```

After all three independent reviews have genuinely passed, root may separately
invoke --phase summary. It consumes those exact new run/review stats, program,
source/build and old controls and exclusively writes
logs/upl_tpi_p3_full_short_r1.check.json. Its stage is
upl_tpi_p3_full_short_r1.summary and its scope is implementation regression only.
It does not infer all22 raw equality from five exports, full physical accuracy,
runtime testing of ReleaseCPU or short B bit-equivalence for GPU Release. New
ReleaseCPU has build qualification only; GPU Release A plus Debug B provides
the stated limited coverage. New GPU Release B still needs separate root full
admission; no repeat 2 s, 2000-step probe or extra reference is scheduled here.

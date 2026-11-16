# P1 CPU single-job physical runner author draft

2026-11-17, Asia/Tokyo. Authoring only. This script has not launched help, a
solver, a decoder, VTK, GenCase, a build, SHA or Git. Each actual invocation
needs its own root-reviewed admission. No action chains another job, half,
reference, full2Tv, GPU, C08 PRE or native read. No old process is stopped,
resumed, replaced or restarted.

`tests/support/upl_tpi_cpu_run_r1.py` permits exactly one of:

| Configuration | Scheme | Window | Updates | Planned native frames | Actual scalar end (s) |
|---|---|---|---:|---:|---:|
| DebugCPU | B | debug2ms | 320 | 18 | .002000045776367195 |
| ReleaseCPU | A, B or C independently | startup015 | 24000 | 344 | .1500034332275618 |

All use original actual dt `6.250143051147461e-6`, CPU1, and the original
final-A input prefix
`tests/outputs/upl_bigstep_full_r1_seed/upl_bigstep_2tv_CPU1_r1`.
The existing initial BI4, normals NBI4 and runtime XML are read directly; no
GenCase, copy/relabel of old outputs, PART restart, new preload or formal XML
edit occurs. This is a fresh source-zero/cold-history run. The two real new
programs are the passed full DebugCPU r2 and passed link-only Release r3:

- `logs/upl_tpi_cpu_DebugCPU_r2.build.json` and its recorded program/runtime.
- `logs/upl_tpi_cpu_release_link_r3.build.json` and its recorded program/runtime.

The failed Release r2 stays failed. Release r3 retained both genuinely successful
r2 TU objects plus 84 original A objects and performed a new link; the runner
pins those two original compile calls and checks their actual exits. It does
not retry or rebuild either configuration. No canonical executable is installed.

## CLI endpoint override and exact clock plan

The original seed XML retains TimeMax72.88428690075874 and its complete special
output cadence. Frozen `JSphCfgRun.cpp` parses `-tmax` through float, then
`JSph.cpp` applies it to double TimeMax. A literal `.15` would become
0.15000000596046448, exceeding the already-reviewed private `TimeMax<=.15`
qualification. The root explicitly selected the following legal CLI caps;
these are declared stop overrides, not a physical dt modification:

- Debug: `-tmax:.002 -nsteps:320`; actual cap .0020000000949949026.
- Release: `-tmax:0.14999999 -nsteps:24000`; actual cap
  .14999999105930328. Completed23999 remains below that cap and completed24000
  crosses it, preserving the requested bounded update count and final save.

The remaining CLI is unchanged CPU1/stable/mDBC-FreeSlip syntax, `-dirdataout
data -svres`. Run.out's actual printed TimeMax and Run.csv's original step/frame
counts are checked after genuine completion. The frozen double log formatter
uses 16 significant digits; printed TimeMax is compared with
`float(format(actual_binary32_promoted_cap, '.16g'))`, not required to retain
all double bits. This is a text-format check. Owner CLI/cap remain fixed and
actual native clocks still require exact independent review. Run.csv PhysicalTime
is also rounded and is never treated as actual native time.

The new `logs/<tag>.clock.csv` is created once before Popen. Its eight columns
are the original part/completed_steps/saved_step/time_s/dt_s/
post_open_by_completed_step/target_time_s/forced_final schema. Clocks are
independent binary64 scalar `+=dt`; no n*dt is substituted. Only output targets
use the unchanged JDsOutputTime anchor/interval/integer-index arithmetic.
All five original segments remain, including later segments unused by these
short jobs. No fixed-grid clock snapping or saved metadata rewrite occurs.

Original event completed1600/part117 is pre-open, completed1601/part118 is the
first post-open state. Startup has226 post-open frames and2260 true receiver
checks pending native review. Debug ends before opening and expects zero.
The genuine terminal state is before the next ordinary output target and is
marked forced_final=1: it is saved because TimeMax/nsteps ends this run, not
because an ordinary output target was reached. Retained full A genuinely shares
only the first17 Debug states (through313) or first343 startup states
(through23691); their forced final320/24000 saves are not present in old A.
The runner checks that these planned shared rows exactly match the retained
original clock declaration, but does not claim a physical/native bit comparison.

## Admission and ownership

Run syntax for an independently authorized root invocation is:

`python -B tests/support/upl_tpi_cpu_run_r1.py --execution-authorized --admission ROOT.json`

The admission must have
`stage="upl_tpi_cpu_run_r1.run_admission"`, `passed=true`, `one_job_only=true`,
`inputs=[{path,bytes,mtime_ns}, ...]`, and a single job:

```text
job = {
  tag: upl_tpi_cpu_<Configuration>_<A|B|C>_<window>_rN,
  configuration: DebugCPU | ReleaseCPU,
  scheme: A | B | C,
  window: debug2ms | startup015,
  source_build: {path, bytes, mtime_ns}
}
required_passed_checks = [{path, bytes, mtime_ns}, ...]
```

Only the table's exact configuration/scheme/window combinations are accepted.
Each prerequisite review must actually say passed=true. Root reviews the
component/build/native prerequisites appropriate to that one job before
listing them; a previous job's normal exit alone is not that admission.
The consumed input set includes this script/note/Python, original full-A
run/seed3, the actual build/preparation/program/runtime, prepared two TUs/private
header/source_diff, and prerequisite reviews; Release additionally pins the
two adopted successful TU calls. psutil's module path is pinned at invocation.
The root admission must list all of these, with stable stat identities.
There is no old object/source/BI4 SHA sweep.

The runner refuses existing output, plan or start/call/run/status/log files and
any other present CPU solver. Existing GPU processes, including the suspended
C08 owner/context, are recorded and left untouched. Child environment is
explicit `UPL_TPI_CPU_R1=A|B|C`, `OMP_NUM_THREADS=1`, `OMP_DYNAMIC=FALSE`;
only these non-secret values are retained, not a dump of the user's environment.

The real child is started with Popen, shell=false and no visible helper window.
Its genuine CreateProcess handle is duplicated before waiting; actual Win32
creation FILETIME, PID and final native exit are observed from that handle.
Observed psutil creation/exe/argv/parent must match. The original Popen wait
exit and actual Win32 exit are recorded separately, without normalization or
invented LASTEXITCODE. A bookkeeping exception never terminates/restarts the
child; this direct owner awaits its already-created child and retains the first
exception plus real exits. No watcher, queue, resend or completion self-test is
installed by this runner.

Start seals actual owner/child/environment/input/clock bindings. Call seals the
genuine exits before output review. Run/status then preserve normal summary or
failure, original last raw console PART line and first actual error line.
Unreported native stop time is never inferred. A preflight rejection before
Popen writes a unique rejection receipt when its safe admitted tag is available;
it never overwrites an old result or silently retries.

## Terminal boundary and native adapter schema

Exit0/normal summary only means pending native/physical review. The runner
checks original no-exclusion/update/frame-presence and two-real-force/two-update
HG/cache counters, finite HG diagnostics, dt/tau<=.2 and spin<.01. A must have
no TPI sidecars. B/C must have the real completed policy/CSV/summary and their
expected lifecycle totals. It does not read the big CSV or any particle arrays.
Every original22-array/1040-ID/clock/signed-ledger/drainage/native/HG safety
guard remains in the independently admitted reader. No numerical gate is
relaxed by solver completion. Native PorePressRate is still the old scaled
endpoint residual in B/C, not their actual dp/dt.

The run receipt provides matching scheme/window/configuration/program,
output_directory/data, actual_environment, call and plan stats for
`upl_tpi_cpu_native_r1.py`. The native root admission's job also binds run_out
and the sealed run receipt. The original call provides child.exe plus
actual_Popen_wait_exit and actual_Win32_exit. A successful physical solve with
a failed terminal audit is retained for offline audit repair, not rerun.

No native reader, VTK, plot or subsequent solver is invoked here. Root separately
admits exactly one native read after inspecting the actual immutable run. The
native decoder checks original typed arrays, scalar clocks, signed intervals,
ledger, real drained receiver count and pressure sidecars. Default Release A
prefix controls are byte comparisons only for the genuinely shared saved
records; Debug is not Release0-ULP truth, and A/B/C are different pressure
models/predictions rather than 5-Pa half/backend equivalence tests.

# P1 short CPU native adapter: author preparation

This new reader is a narrow copy of `support/upl_bigstep_native_r1.cpp` and
includes the retained, unchanged `support/upl_cpu_public_native_r1.cpp`.
No old reader, loader, source result or binary declaration is rewritten.
It admits only the two independently planned original-A output schedules:

| Window | Updates | Actual scalar end (s) | Native frames | Post-open frames / true receiver checks |
|---|---:|---:|---:|---:|
| `debug2ms` | 320 | 0.002000045776367195 | 18 | 0 / 0 |
| `startup015` | 24000 | 0.1500034332275618 | 344 | 226 / 2260 |

Both use original `dt=6.250143051147461e-6`, the original special-output
segments and scalar `time += dt`. There is no `n*dt` clock substitution.
Debug's eighteenth state is a genuine forced-final save at step 320; the
retained A shares only its first 17 states through completed step 313.
Startup's final state is forced at step 24000; retained A shares 343 actual
states through completed step 23691. Original event completed step 1600,
part 117, is pre-open; part 118 / completed 1601 is first post-open. Debug
ends before the event, so its explicit profile expects no event-part entry
and zero drain receivers. That bounded exception does not weaken the
startup profile's nonempty drainage requirement.

The native reader preserves all original 1040 IDs (40 fixed, 1000 soil),
22 exact typed arrays, original15/common26 definitions, initial rest/lattice,
full finite/elastic/P0/float-display checks, scalar saved clocks/zero-based
Step, signed noninitial nonempty `dterror <= 1e-14`, single-J n/V/rho/k
ledger, fixed zero markers, top/bottom material sets, no-bottom-crossing,
and true FSType2/3 drainage tests. It does not promote normal completion to
physical acceptance. Run.out's original HG force/rate/update/cache counts,
`dt/tau <= .2`, `spinbound < .01` are separately checked without adding
an HG phase for the extra pressure endpoint.

The helper's public BI4 schema and input Kw remain legacy values for A/B/C;
they cannot prove which pressure integrator actually ran. The root must
bind actual owned environment `UPL_TPI_CPU_R1` and the real program. A
requires the default/explicit A branch and no TPI policy/CSV/summary.
B/C additionally require original `UplTpiCpuR1.policy.json`, `.csv`, and
`.summary.json`. The adapter checks all 28 columns for every native soil ID
in every saved block, actual scalar source and save times, exact lifecycle
counts, alpha=.5/0 and beta=0 history prediction, actual float writeback,
Dirichlet priorities, native pressure/J, and original J corrector. Initial
zero-diagonal rows are genuine cold-state initialization, not removed
elliptic rows. Each later unconstrained diagonal must be positive. Saved
history samples are not a claim of independent observation of unsaved
states. `PorePressRate` remains an old-scaled endpoint residual diagnostic
in B/C, not an actual `dp/dt`; do not use it to certify temporal accuracy.

Default Release A may be checked against the already decoded complete A
at `outputs/upl_bigstep_2tv_CPU1_r1_native_r1`: compare the genuinely shared
17 or 343 records in all five original binary exports, including actual
clock and signed diagnostic bytes. Preserve the distinct 18/344 and 1682
headers. The forced final state has no retained counterpart. Debug is not
Release 0-ULP truth. These five exports retain their existing layouts;
their comparison is not a newly invented all-22-raw-array byte export.
All 22 native arrays are independently loaded/typed/validated, including
the V/rho/k/PosDiv values recorded in ledger and marker CSVs. B/C versus A
is a cross-model accuracy comparison, not a 5-Pa/.005-mm half-step gate.
The old A 100-Pa stress-accuracy limitation remains recorded. Neither a
short pass nor an exact default-A prefix establishes final theory accuracy.

`support/upl_tpi_cpu_native_r1.py` provides three separate actions:

```text
python -B tests/support/upl_tpi_cpu_native_r1.py build|read|review
  --execution-authorized --admission ROOT_ADMISSION.json
```

Each admission is independently reviewed and has
`stage="upl_tpi_cpu_native_r1.<action>_admission"`, `passed=true`,
`action_only=true`, and `inputs=[{path,bytes,mtime_ns}, ...]`. It pins this
script, note, new C++ reader and `support/upl_tpi_cpu_build_r2.py` as the
actual common CPU build helper; each result records that helper's stat. No action
automatically invokes another. Existing receipts or partial outputs are
protected. No solver, VTK, half/reference chain, PRE, formal job, watcher,
Git action or process replacement is in this adapter.

Build additionally pins the retained reader build/compile/link receipts,
neutral loader, eight actually used frozen headers, retained objects/libs,
runtime and tool inputs. It replays that real reader recipe into
`outputs/upl_tpi_cpu_native_r1_build`, replacing only reader.obj; no old
objects are recompiled. Environment setup uses a literal CRLF batch file
and invokes its no-space relative filename with `cwd` set to its new
build root, not nested `call` quotes or a spaced absolute batch path in
the Popen argument list. Calls retain original
Popen/Win32 exits and logs. No old object/BI4 hash sweep is performed.

Read/review admissions carry a `job` with exact `tag`, `window`, `scheme`,
`configuration`, stat records `run_receipt`, `call`, `program`, `plan`,
`run_out`, and literal `output_directory`/`data`. The sealed run has
`passed=true` and matching scheme/window/configuration/program/output plus
`actual_environment.UPL_TPI_CPU_R1`; the original owned call has actual
child identity and Popen/Win32 exits. The root admission pins all PARTs,
and must have independently reviewed original input/clock/program/owner
bindings before read authorization. Read checks existing/active readers and
decodes at most once into `outputs/<tag>_native_r1`.

Offline review separately pins the successful native receipt and all its
files, the pressure sidecars for B/C, and retained-A completion plus five
exports when comparing default Release A. It creates only a new review
receipt; it never reruns the native reader. Pressure/material settlement,
stress and qualified-reference figures remain a subsequent offline review,
not an automatic physical acceptance or another solver admission.

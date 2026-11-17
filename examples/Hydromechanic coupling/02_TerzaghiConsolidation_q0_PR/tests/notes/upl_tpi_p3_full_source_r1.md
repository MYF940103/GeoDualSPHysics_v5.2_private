# Private P3 full-scope source preparation (author only)

This asset permits one separately admitted CPU or GPU source freeze. It does not
prepare a seed, build, call help, run a solver, read native data, notify another
thread, or start any later action. Authoring and a source-only receipt are not
short regression or full-cycle physical acceptance.

New assets are support/upl_tpi_p3_full_source_r1.py and this note. A separately
reviewed builder is support/upl_tpi_p3_full_build_r1.py with its own note. No
existing author, frozen source, public/canonical source, program, or receipt is
edited. Inputs and outputs are checked by path/size/mtime_ns; SHA scans are zero.

The CPU parent is outputs/upl_tpi_p3_CPU_r1_source, with 267 complete flat files;
the GPU parent is outputs/upl_tpi_p3_GPU_r1_source, with 270. The corresponding
passed logs/upl_tpi_p3_{CPU,GPU}_r1.prepare.json and both actual configuration
builds for that backend must be root-admitted and bind the same prepared source.
Every parent file and both build receipts are consumed; original bytes are copied
to a fresh output tree. There is no legacy C02/C04/C08 relabelling or source merge.

The sole patch is the one M0 true arm in JSphCpuSingle.cpp (parent line 1349) or
JSphGpuSingle.cpp (parent line 1157):

```cpp
?TimeMax<=2.:
```

becomes:

```cpp
?(TimeMax<=2. || (TimeMax==72.88428690075874 && NstepsBreak==7288262)):
```

The original short `TimeMax<=2.` expression remains the first short-circuit arm.
GPU's non-M0 full arm with NstepsBreak==11661219 remains byte-for-byte unchanged
and is not used as the new M0/P3 contract. Existing unchanged P3 helper Init and
selector checks still require B, M0 Eq40 Rh1, three endpoint defects, and fixed
dt=tD/1000; the change adds no alternate pressure method or timestep policy.

Numerical consequence: only the allowed execution time domain is expanded by
one exact TimeMax/cap pair. No pressure, force, material/J/HG/history update,
clock, boundary, kernel, normalization, observer, signed diagnostic, schema,
parameter, or tolerance changes. CPU/GPU class headers, all private helpers,
CUDA/cuH sources and shared device-visible tokens are copied unchanged. An
unchanged <=2 s input follows the same expression and numerical code; actual
short equivalence is still a later independently admitted test, not claimed by
source comparison. Long completion and physical accuracy remain pending.

Invocation, only after root review and one explicit backend admission:

```text
D:/anaconda3/python.exe -B tests/support/upl_tpi_p3_full_source_r1.py --backend CPU --admission ROOT_JSON --execution-authorized
```

GPU uses --backend GPU in a separate action. Admission stage is
upl_tpi_p3_full_source_r1.prepare_admission, passed=true, prepare_only=true,
backend exact, and inputs is a duplicate-free list of admitted stat dictionaries.
Inputs include this script/note, its imported P3 source module and defining
stat/read/write helper modules, the parent prepare/build receipts, and every
parent source file. No collector or main function has been executed in authoring.

Fresh outputs are outputs/upl_tpi_p3_full_{CPU,GPU}_r1_source,
logs/upl_tpi_p3_full_{CPU,GPU}_r1.source.diff, and
logs/upl_tpi_p3_full_{CPU,GPU}_r1.prepare.json. Receipt stage is
upl_tpi_p3_full_source_r1.prepare; it records base_prepare, base_builds,
base_source_entries[{original,pinned_snapshot}], files, source_diff,
changed_sources/recompile_sources=[Single.cpp], changed_headers=[], full_scope,
and actual consumed stat checks. Existing outputs/failures/partials are rejected
and retained. A failure after creation preserves partials under this unique tag;
it never triggers a retry or build.

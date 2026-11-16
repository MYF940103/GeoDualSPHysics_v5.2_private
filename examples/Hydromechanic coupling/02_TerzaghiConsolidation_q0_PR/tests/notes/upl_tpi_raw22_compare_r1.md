# P1 default-A actual native22 prefix comparison: author-only

2026-11-17. New assets are `support/upl_tpi_raw22_compare_r1.cpp`, its Python
build/compare wrapper and this note. They have not been compiled or executed
by the author. Old loaders/readers, source, programs, BI4, full native exports,
receipts and plots/CSVs are unchanged. Root must full-read these three assets
and separately admit each action. There is no physical solve, GenCase, hash,
new full22 export chain, automatic retry or automatic next action.

The current evidence gap is precise: default-A's five exported payloads have
343 shared records bit-identical, and each native read validated22 typed
arrays, but that does not itself prove every actual22-array value bit-identical.
In particular PosDiv and current V/rho/k must be compared directly, not inferred
from a compact export, ledger formula or a successful native reader.

## Small comparison executable

The new main includes the unchanged neutral `upl_cpu_public_native_r1.cpp`
under a renamed old main. It calls the existing `Load`/`NativeArray` functions;
the all-array byte loop follows the already reviewed
`upl_hg_raw_compare_r1.cpp` `Array/Arrays` method. No old comparator or reader
main is invoked. The actual22 arrays are:

Idp, Posd, Vel, Rhop, Sigma_kk, Sigma_ij, SigmaState_kk, SigmaState_ij,
Kplastic, FSType, FSNormal, HydroMechLoadAce, PorePress, PorePress0,
ExcessPorePress, PoroVolumeRatio, PoroPorosity, PoroThetaLastStage,
PoroCurrentVolume, PoroMixtureDensity, PoroHydraulicConductivity and PosDiv.

All1040 native IDs (including40 fixed) must exist once with exact array
types/counts and finite native values. The decoded typed bytes are compared
by original native ID, allowing ordinary storage-slot sorting. This is not
an equality claim for compressed BI4 container bytes or storage-slot order.
No fixed values, initial records, signed diagnostics or arrays are masked.
Per frame the arrays contain220480 bytes. The exact separate28-byte clock is
TimeStep double, zero-based Step uint, locked dt double, signed dterror double.
Its original initial value/sentinel is retained; noninitial signed intervals
must remain nonempty and <=1e-14. There is no absolute-value substitution.

Both original sequence counts and untouched eight-column actual clock plans
are checked. The executable reads only the explicitly declared common prefix,
requires every actual shared Step/time/dt to agree with its own plan and
requires the next planned record to differ if both inputs continue. It rejects
a shorter declared prefix that would conceal another real shared record.

For this first CPU comparison the old full output has1682 native frames, the
new startup output344, and exactly343 actual records are shared. The new forced
last record remains unshared; it is not relabelled as an ordinary old save.
Sequence headers, counts, plans, actual times, original PARTs and existing
export files are never rewritten. Later GPU default-A comparisons can supply
different independently verified original/shared counts and plans; no GPU
count or profile is guessed by this author.

Only a fresh comparison output directory is created, outside both raw input
directories. It contains `arrays.csv` (22 array rows plus one clock28 row per
shared frame) and `completion.json`. The CSV records per-array byte/element
differences and first differing native ID/element byte. It does not dump node
fields or duplicate native payloads. Array mismatches do not stop comparison
of the remaining valid frames. Invalid types/identities/clocks preserve the
first actual error and partial CSV; no rerun or inferred missing state follows.
The summary does not claim all unrelated BI4 scalar metadata were compared.

## Independent build and compare actions

The wrapper imports only definitions from the already reviewed CPU build/native
helpers. It never calls their build/read/review/main functions. Its build action
reuses the genuinely successful `upl_tpi_cpu_native_r1` compile/link arguments,
retained ReleaseCPU objects/libraries and frozen header closure, replacing only
the reader main object. The original MSVC14.36 environment helper and actual
Popen/Win32 exit capture are reused. All new object/program/PDB/ILK/runtime
copies stay under `outputs/upl_tpi_raw22_compare_r1_build`. The old native reader
program and native exports are not rebuilt or invoked. Build success writes
`logs/upl_tpi_raw22_compare_r1.build.json` and admits no compare automatically.

The separate compare action requires a passed comparator build, a passed old
native receipt and the passed new default-A native review with scheme A/data
directory association. It refuses existing comparator outputs/receipts and
checks active same-program readers before starting its one comparison process.
Only the actually read shared PART files and any existing native head are
content inputs; counting the complete1682-file old sequence is not a scan or
decode of its unshared payloads. Path/size/mtime pins are used, never SHA.

Each root admission contains `stage="upl_tpi_raw22_compare_r1.ACTION_admission"`,
`passed=true`, `action_only=true`, and `inputs=[{path,bytes,mtime_ns}, ...]`.
All three author assets, old raw comparator/neutral source and the imported
helper files are pinned in both actions. Build additionally pins the actual
successful native build/call/recipe dependencies, frozen included headers,
toolchain tools and copied runtime sources. Compare pins its new build/program/
runtime, original qualification receipts/plans, each opened shared PART and
any native head.

The compare admission also contains `comparison` with `label`, `old_data`,
`new_data`, entries `old_native_receipt/new_native_review/old_plan/new_plan`
(each including path/bytes/mtime_ns), and integer `old_frames/new_frames/
shared_frames`. Current label `CPU_A_startup015_r1` must be1682/344/343.
Its output is `outputs/upl_tpi_raw22_compare_r1_CPU_A_startup015_r1`, receipt
`logs/upl_tpi_raw22_compare_r1_CPU_A_startup015_r1.compare.json`.

After complete root review only:

`python -B tests/support/upl_tpi_raw22_compare_r1.py build --execution-authorized --admission BUILD_JSON`

`python -B tests/support/upl_tpi_raw22_compare_r1.py compare --execution-authorized --admission COMPARE_JSON`

Build and comparison are independently admitted; no chained execution is
included. A negative comparison preserves genuine process exits and, if
present, the comparator's actual failed summary. The original A105.390Pa
scientific safety failure is unrelated to this default-OFF bit proof and is
not changed or converted into acceptance. Raw22 equality would establish only
the declared implementation prefix; it would not establish physical accuracy,
full-cycle convergence, restart interoperability or new GPU acceptance.

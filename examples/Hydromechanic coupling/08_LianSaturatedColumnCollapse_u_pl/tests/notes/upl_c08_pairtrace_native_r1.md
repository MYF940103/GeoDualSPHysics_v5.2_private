# Pairtrace normal30 native adapter (author only)

The four new files are `tests/support/upl_c08_pairtrace_native_r1.cpp`, `_build.py`, `_run.py` and this note. Their names were absent on disk and absent from exact `git ls-files` before authoring. No existing helper, frozen core, program, archive, physical input or result is changed. This authoring task does not build, decode, run a solver, generate VTK, queue work or scan hashes.

Only one profile is accepted: psi0/GPU, source step4000000, 120000 new updates, global end4120000, 30 real post-event saves at completed steps4004000..4120000, cadence4000 (.01s), fixed dt2.5us. There is no smoke, half-step run, other material group or automatic next action. The actual clock starts at the certified PRE scalar time and advances by repeated addition in the unchanged core; neither integer10 nor Nstep*dt replaces it.

## Mechanical derivation and preserved scope

The builder calls the sealed `upl_c08_causal_native_r1_build.derive_core` chain. Relative to its generated causal core, exactly one string occurrence changes: `upl_c08_causal_native_r1` to `upl_c08_pairtrace_native_r1`. Reverse normalization must recover the complete prior generated text exactly. The inherited AS CSV anchors stay `rightpart="3)"`, `marker="AS_Bui2008(0.2;3)"`; left split remains `AS_Bui2008(0.2`. No CSV bytes or physical arrays are rewritten. The existing generic planned-CSV 11-argument main, conductivity exp law, all arithmetic budgets and field checks are unchanged.

The new adapter restricts the profile and lazily checks the same keep5/actual-retire255 policy, total-AS ReleaseOnly Active epsilon.2f/exponent3.f and CompletedOnly (both experimental ponding keys absent). All three private AV override keys must be absent: `DynamicArtificialViscosityPolicy`, `DynamicArtificialViscosityOverrideActive`, `DynamicArtificialViscosityCoef`. Original AV.1 is also checked by the frozen owner's exact input comparison; absence alone is not proof of its coefficient. Header scans do not decode field arrays or reload PRE. Actual observer IDs7011/7012/6230 are proved by the separate program/CSV evidence, never by adding a23rd BI4 array.

The core retains all22 fields/6805 IDs =1805fixed+5000soil, source7060 IDs/2060fixed, original release target260 and explicit kept IDs1800/1852/1904/1956/2008, actual255 retirement, fixed material P0, J/n/V/rho/k ledger, rho-cache bits, nondecreasing kappa from PRE, FS2/3 completed p<=0, fixed-plane gaps and signed intervals. Counts are150000 ledger/rho/kappa,204150 P0,54150 fixed markers,300000 plane gaps and30 signed intervals. The original clock/signed1e-14, ledger5e-13 and geometry1e-6*dp budgets remain. Reaction/J/Darcy closure, general restart and physical acceptance remain false.

## Build and one-reader interfaces

After independent root review only:

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_pairtrace_native_r1_build.py --execution-authorized
```

This compiles one new reader object with MSVC14.36, C++17, /O2 /MT /fp:precise /GL- and wmainCRTStartup. It links only six sealed ReleaseCPU BI4 utilities (JPartDataBi4, JPartDataHead, JBinaryData, JObject, JException, Functions) from `mdbc_partition_ReleaseCPU_r1.build.json`; seven total link objects, no JSph/main/Debug ABI or solver build. Headers come from that same retained utility capture. Fresh output: `tests/outputs/upl_c08_pairtrace_native_r1_build/C08PairTraceNative_win64.exe`; receipt: `tests/logs/upl_c08_pairtrace_native_r1.build.json`. Generated core, complete diff, one-label causal diff and reverse-proof receipt are retained there.

CLI: `--read psi0 GPU DATA PRE 4120000 30 1 PLAN FRESHOUT`. The independent runner is selected separately:

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_pairtrace_native_r1_run.py --execution-authorized
```

It consumes only the completed `upl_c08_pairtrace_window_GPU_r1` run/start/call/owner/root admissions and their stat-bound program/source/PRE/XML/seed/plan/PARTs. It uses the new owner's pure `summary(path)` and `check_input(path,generated=True)` functions, not old smoke or preparation schema. Actual direct Popen/Win32/tool/solver exits, argv, creation and parent identity are required. The matched Release build is `upl_c08_pairtrace_Release_r1.build.json`, program `outputs/upl_c08_pairtrace_Release_r1/DualSPHysics5.2_GEO_win64.exe`, capture `outputs/upl_c08_pairtrace_r1_source/source.json`: only four observer-ID mapping sites across three GPU TUs changed, 3 rebuilt+110 retained=113 objects, both macros on, no layout/sampler/physical equation change. Separate cumulative totals must contain the actual new three IDs at all30 saves with four counts ending120000 and errors0; the large trace is stat-bound, not rescanned here. No assumption of `run.preparation` or prior smoke is made.

The unique fresh decoder output is `outputs/upl_c08_pairtrace_window_GPU_r1/native_r1`; native receipt is `logs/upl_c08_pairtrace_window_GPU_r1.native_r1.json` with `source_run`, `actual_call`, `completion`, `metadata`, `original_native_guards_passed`, `consumed_stats_unchanged`, outputs/consumed. Completion stage is `upl_c08_pairtrace_native_r1`; metadata stage is that name plus `.metadata`, profile window, cadence4000 and30 per-header counts. The runner invokes only this reader once. Any existing/partial output/call is protected; errors retain evidence without retry.

After successful decode, the same invocation compares all30 original22-array records plus binary actual time against the first30 of the passed true causal90 native export. The original headers remain `(6805,22,30)` and `(6805,22,90)`; no header normalization is written. Layout must be byte-identical, and original clocks header/first30 rows (including signed dterror, saved Step and actual scalar time) must match byte-for-byte. Different actual programs are individually bound, not forced equal. This is observer-only implementation regression, not cross-model tolerance or physical accuracy acceptance. All old30/90/raw outputs remain untouched. No second PRE or BI4 decoding is performed for the comparison.

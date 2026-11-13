# Real old-path compatibility regression (author only)

The single runner supports one explicit action at a time. It changes no source,
root XML, retained PRE, old result or program. It does not launch a plastic
source, ten-second preload, half-step chain, other material group, VTK, build,
queue or automatic next job. A normal `run` invokes only its selected solver
once, then its existing native utility once after the real solver succeeds.
Failure preserves original owner/call/output/first error and prohibits retry.

`prepare --execution-authorized` runs GenCase once on the unchanged root
`CaseLianSaturatedColumnCollapse_shared_preload_r3_Def.xml`, generating one
fresh common source seed under `tests/outputs/c08_preload_schema2_regression_r1_seed`.
It extracts the actual generated material values into an11-key CSV for the
source inspector and writes the one-row global4000010 handoff plan. The old
and new source jobs both consume this exact seed. TimeMax remains13 (required
to exceed event10); `-nsteps:8000` is the actual20ms stopping rule. Damping,
Shepard, Cubic H=.048, dt2.5us, AS0/NoPen0 and strict Elastic source remain as
the original root input. GenCase is not repeated for each program.

The handoff jobs use the already generated root r6 seed directly, including
its absolute genuine schema1 law1 r2GPU Part1000, keep5/retire255,
AS.2-n3/FixedPlaneStageProjectionReleaseOnly and CompletedOnly. Their cap is
global4000010: ten real updates and one forced final post-PRE frame. The old
schema1 PRE is neither edited nor recomputed. This test is independent of the
new bedroles registry and schema2 plastic transfer.

Explicit Release actions (no automatic sequence):

```
python -X utf8 -B c08_preload_schema2_regression_r1.py run --kind source --program old --execution-authorized
python -X utf8 -B c08_preload_schema2_regression_r1.py run --kind source --program new --execution-authorized
python -X utf8 -B c08_preload_schema2_regression_r1.py compare --kind source --execution-authorized
python -X utf8 -B c08_preload_schema2_regression_r1.py run --kind handoff --program old --execution-authorized
python -X utf8 -B c08_preload_schema2_regression_r1.py run --kind handoff --program new --execution-authorized
python -X utf8 -B c08_preload_schema2_regression_r1.py compare --kind handoff --execution-authorized
```

Each job has a distinct `..._<kind>_<old|new>.run.json`, owner admission,
actual start/call, output and `native` directory. Old means the unchanged
runtime_r6 GPU Release executable bound to its actual bedkeep Release build.
New means `outputs/c08_preload_schema2_Release_r1/DualSPHysics5.2_GEO_win64.exe`
bound to its actual new build receipt and MSBuild Popen/Win32 closure. Both
programs' source capture/archive and runtime dependencies are stat-bound.
Existing base.owned holds real handles through exit, including error paths.
The run summary checks global steps, actual save count,7060 registry,2060
fixed, no exclusions and normal GPU completion. Original engine cell/finite/
material/necessary-step guards remain in force; none are replaced by this script.

No new native reader is needed:

- Source: `outputs/upl_c08_hdp15_preload_partial_r3_build/C08PreloadPartial_win64.exe`
  with `--read h12_control DATA MATERIAL_CSV FRESHOUT`. The actual frozen main
  accepts1..53 continuous source frames and completed<=208000, so the3-frame
  0/.01/.02 source is in scope. It checks exact22/7060/2060/5000, kappa0,
  P0/stress display/fixed markers/J-ledger/rho cache/scalar clock and signed
  intervals. Its `partial/uncertified/runtime_success_claimed=false` annotation
  is deliberately preserved: it is a diagnostic utility, not the run owner.
  Saved FS signs after Shepard/save classification are observational in this
  existing source utility; no new FS clipping or weakened solver guard is added.
- Receiver: `outputs/upl_c08_causal_native_r1_build/C08CausalNative_win64.exe`
  with `--read psi0 GPU DATA PRE 4000010 1 1 PLAN FRESHOUT`. The unchanged
  final-only ten-update profile checks all22/6805/keep5/P0/J/ledger/FS/kappa/
  planes/scalar clock/signed safety and reads the genuine law1 PRE once.

Each `compare` requires both jobs/native to pass, then compares the complete
`typed22.bin`, `typed22_layout.csv` and `clocks.csv` bytes. These contain all22
fields, actual double timestamps and signed diagnostic values. Original binary
headers and CSV rows remain intact. There is no model-change tolerance or5Pa
budget. A mismatch remains a regression result for investigation, not a reason
to rewrite data or relax numeric checks. Different program/build metadata and
wall times are not compared as physical payload.

Optional independent action:
`debug_handoff --memcheck --execution-authorized` selects the actual new
`c08_preload_schema2_Debug_r1.build.json` and its Debug GPU program. It uses the
same ten-update genuine schema1 handoff and qualified reader, with actual
compute-sanitizer child identity and zero error/leak summaries. Omitting
`--memcheck` runs that Debug job directly. It has its own `_handoff_debug` tag;
it is not part of either Release byte comparison and cannot silently select
an old object/program. No Debug job is started by prepare or any Release action.

Only author/static AST and input inspection were performed here. Root decides
each later action after actual builds pass. Passing establishes old-path
implementation compatibility, not source equilibrium, plastic transfer,
collapse accuracy, stability of a long run or acceptance of other psi groups.

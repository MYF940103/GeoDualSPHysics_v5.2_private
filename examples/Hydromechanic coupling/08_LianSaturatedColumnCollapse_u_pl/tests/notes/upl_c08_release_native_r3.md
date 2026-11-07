# C08 Release native reader r3: backend and certified-PRE compatibility

Author-only new files: `support/upl_c08_release_native_r3.cpp`, `_build.py`, and this note. No r2 source/build/note/program/receipt is changed. No build, decoder, solver, runtime copy or Git operation was performed by this author stage.

## Exactly three semantic changes from frozen r2

1. Same CLI layout, now `C08Native_win64.exe --read GROUP BACKEND DATA PRE EXPECTED_GLOBAL_END FRESHOUT`, where BACKEND is CPU or GPU. Completion writes that validated argument and retains `backend_proven_by_reader=false`. Native arrays do not prove hardware/backend; the formal postprocessor must bind the actual executed program, Run.csv, actual solver exit and XML.
2. The existing certified loader may return source MaterialLawVersion1 (legacy typedMR1) or2 (unifiedv2), and completion reports **certified.MaterialLawVersion**, not an assumed value. All complete elastic PRE/schema1/4M-step/time10/κ0/contract/geometry/state conditions stay mandatory. Unknown/untyped/new-version metadata does not fall back to a legacy format. Source target-cohesion qualification remains5000/5000/7500 by group.
3. Completion stage is `upl_c08_release_native_r3`.

These changes are exactly7 reversible text substitutions (comment, CLI/validated backend, PRE allowed-version condition/error wording, stage and two JSON values). Reversing them reproduces the frozen r2 CPP text exactly. No τ, density, signed time-step, IDs,22 arrays, ledger/cache/P0, retirement, κ/FS, actual frame enumeration, export order or arithmetic text changes. The r3 builder is a tag-only derivative of the r2 Release builder.

## Unchanged schema and scope

- GROUP remains only psi0/psi2p5/psim5, sf float0/.2/.2 and target peak cohesion5000/5000/7500. Target native metadata still requires MaterialLawVersion2, no MaterialReturn key and the correct group sf. The postprocessor separately validates the full material recipe from the actual executed XML.
- Only expected global end4040000 (existing0.1s output may validate this new implementation) or5200000 (full3s after certified10s) is admitted. Actual PartFiles/native sequence determines frame count; actual post-event Step/time and scalar+=dt are never rewritten. One supplied PRE is read once; no old1001-frame decode or general/post-plastic PART restart.
- `typed22.bin`: little-endian header three uint32 `(6800,22,actualframes)`; each record is actualtime float64 followed by22 whole ID-sorted arrays,212 bytes per particle. Record length1441608 bytes. Layout/order/clock/history/completion fields are exactly r2 except the three declarations above. Original ID domain7060, retained IDs0..1799 and2060..7059, all5000 soil and1800 retained fixed samples; no synthetic PRE/t0.
- History displacement remains genuinely relative to certified PRE positions and total stress uses sigma_eff-pI. No separate PRE material CSV is added to any frozen version. The formal plotter may use the history's PRE displacement metrics; absent per-ID PRE reference must not be replaced by the first post-frame or called true original-layer displacement.

All native safety/finite/ledger/fixed/P0/κ/free-seepage/clock gates and no-physical-acceptance qualification remain those documented in `upl_c08_release_native_r2.md`. This compatibility does not certify a source merely because κ was saved as zero: the dedicated elastic-source program enforces every Pre/Cor trial and the trusted loader checks its complete schema/contract/state.

## Same Release utility closure

After root full-read only: `D:/anaconda3/python.exe -X utf8 -B support/upl_c08_release_native_r3_build.py --execution-authorized` from tests. Fresh output `tests/outputs/upl_c08_release_native_r3_build/C08Native_win64.exe` and new r3 compile/link/build receipts.

Build uses the same frozen mdbc_partition_ReleaseCPU_r1 six utility objects (JPartDataBi4, JPartDataHead, JBinaryData, JObject, JException, Functions), source capture/archive headers, MSVC14.36 `/O2 /MT /fp:precise /GL-` and standard wmain CRT startup as r2. Seven total link objects; no Debug/JSph/CUDA object, solver rebuild or runtime replacement. Python syntax was checked by AST only; the builder was not imported/executed. Root may later validate this new generic implementation once on existing short data in a fresh native directory, comparing unchanged raw22/clock/history/layout with closed r2 output; that is new-reader validation, not a repeated solver or relabelled r2 result.

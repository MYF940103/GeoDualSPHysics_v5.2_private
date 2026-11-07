# Three-group Release C08 native reader, author-only

New files only: `support/upl_c08_release_native_r2.cpp`, `_build.py`, and this note. No compilation, native reader, solver, source/runtime replacement, Git or packaging was performed by authoring. Existing passed/frozen `upl_c08_resume_native_r1.cpp`, its program/data/receipts, and r2/r3 production programs are untouched.

## Mechanical delta from frozen r1

The CPP is derived by exactly7 reversible text substitutions. Reversing those substitutions reproduces the frozen r1 CPP text exactly; all helpers, array loops, arithmetic, source schema/clock, actual-frame enumeration, ledger, original density/pore/natural guards, P0/FS/kappa/fixed/retirement checks and binary export ordering are otherwise unchanged.

1. First comment identifies three C08 groups.
2. CLI adds GROUP: `C08Native_win64.exe --read GROUP GPU DATA PRE EXPECTED_GLOBAL_END FRESHOUT`; validate `psi0`, `psi2p5` or `psim5`, and map target cohesion5000/5000/7500 and sf float0/.2/.2.
3. Shift remaining argv indices by one; retain only global end4040000 (existing0.1s data can validate the generic implementation) or5200000 (full3s after the10s PRE).
4. Pass the declared target cohesion to the existing certified-PRE loader, preserving sourcecoh<=target validation. The same legacyMR1/schema1/κ0/actual4M-clock source remains required and is read once, never all1001 old frames.
5. Require the selected exact float sf in target Version2 metadata. All22 arrays and old-selector metadata absence stay mandatory.
6. Change completion stage to `upl_c08_release_native_r2`.
7. Write the actual validated GROUP into completion JSON.

The new group/cohesion mapping does not infer the full constitutive parameters from BI4: native metadata has MaterialLawVersion and sf, not the full psi/cohesion recipe. The formal postprocess owner must bind the actual executed XML and verify the requested group parameters, actual program/source/runtime identity and completed solver exits before invoking this reader exactly once. The reader independently validates the native model/state invariants and actual counts.

## Data and implementation scope retained

All frames are genuine post-event6800-ID states; original registry remains7060/2060/5000, only1800..2059 retire. No synthetic t0/PRE is written. Native PartFiles and actual directory sequence determine frames (not a hardcoded300). Every saved zero-based Step and scalar +=2.5us clock is retained from the actual certified source time. The honest typed22 header records6800/22/actualframes. TrueFS pressure<=0, nonempty FS, signed nonempty dterror<=1e-14, original700..3000 rho bounds, finite/nondecreasing κ, single-J n/V/rho/k, native cache bits, P0 bits and retained fixed markers remain unchanged. Finalκ need not be nonzero; report it. History displacement is relative to PRE, not a fictitious zero-stress initial state.

No5Pa A/B/half, uniform-stress, equilibrium or full-collapse physical acceptance gate is added. `PRE_contract_reader_check_is_against_saved_contract` remains explicit; the solver enforces the actual target contract. The loader does not permit a post-plastic/failed-stage checkpoint. A successful generic-reader check on already closed short data is new implementation validation, not a rerun or relabel of the old reader's result; it uses a fresh destination and leaves old data/receipts unchanged.

## Release-only build and later delivery

After root full-read, the one explicit build command from `tests` is `D:/anaconda3/python.exe -X utf8 -B support/upl_c08_release_native_r2_build.py --execution-authorized`.

The builder consumes passed `logs/mdbc_partition_ReleaseCPU_r1.build.json` and its `mdbc_partition_source_r1` capture/archive. It links only the six matching Release utility objects JPartDataBi4, JPartDataHead, JBinaryData, JObject, JException, Functions plus the new reader object; no main/JSph/CUDA/Debug object and no solver build. The actual existing ReleaseCPU CL tlog uses `/O2 /MT /fp:precise` without `/GL`; the new TU explicitly uses `/O2 /MT /fp:precise /GL-`, MSVC14.36/C++17, and the same archived headers as r1. Standard `/ENTRY:wmainCRTStartup` preserves Unicode arguments and CRT initialization. Link is x64, nonincremental, REF/NOICF; no debug CRT or Debug runtime is introduced.

Fresh program path is `tests/outputs/upl_c08_release_native_r2_build/C08Native_win64.exe`; build/call/failure records remain under tests. It reuses the already consumed minimal owned Popen/Win32 invocation utility; no new run framework or implicit decoder launch is created. Root can later copy the passed Release reader into `support/runtime_r3` for formal postprocessing, under a separate reviewed action. No such copy or formal BAT/postprocessor execution occurs in this author stage.

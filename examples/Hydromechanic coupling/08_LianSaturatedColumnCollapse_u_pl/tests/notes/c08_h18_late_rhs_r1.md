# C08 late three-state RHS diagnostic: author-only

New files are `tests/support/c08_h18_late_rhs_r1.cpp`, `tests/support/c08_h18_late_rhs_r1_build.py` and this note. They prepare a zero-advance CPU diagnostic, not another physical trajectory. No production C++/CUDA, XML, PRE, source material, damping, artificial stress, boundary, pressure projection or operator is changed. Authoring admits no import, build, native decode, component invocation, GPU/VTK, solver, or hash scan. Root must fully read these files and separately admit the build and then the one component call. All output paths are fresh and retained partials are protected.

The question is why the completed original AS.5/n2.55 full3 trajectory continues to develop a negative mean pressure after most motion has arrested. This is not an assumption that a global offset is unphysical or that zero mean pressure should be enforced. The same original CPU force is evaluated once on each already saved state, with no pressure/time/material update, to separate compression, Darcy pressure, acceleration and variable-conductivity contributions. It does not reconstruct unsaved GPU substeps, integrate their errors, demonstrate exact fluid-mass conservation, or prescribe a repair.

## Narrow derivation and inputs

The entry is an exact byte transformation of the already built and executed `c08_h18_storage_rhs_r2.cpp`. The builder checks every declared token count and the complete derived entry bytes before building. Changes are restricted to:

- diagnostic application/stage/output labels;
- native full count 91 -> 301 and corresponding extent/error labels;
- selected Parts 30/60/90 -> 200/250/300;
- completed steps 2060001/2120001/2180000 -> 2400001/2500001/2600000;
- the source folder/seed `c08_h18_as05_n255_r1` -> `c08_h18_n255_full3_r1`;
- the protected native check/offline-review/build paths and matching completion metadata.

The numerical force, original neighbor search, source-ordered rate, seven-term decomposition, donor partitions, arithmetic budgets, restoration, state-bit/ledger checks, cleanup and expected row counts are unchanged. No source equation or tolerance is edited. The original detailed numerical specification remains `tests/notes/c08_h18_storage_rhs_r1.md`; `c08_h18_storage_rhs_r2.md` explains its already resolved C++ helper-name collision.

Only the completed `c08_h18_n255_full3_r1` run is admitted. It must have all original runtime guards, exit0 for actual Popen/Win32/tool, 301 saves and completed2600000, original raw-FS AS=.5/2.55, Wendland hdp1.8/H=.072f/dp=.04, dt5us, unchanged original schema2 source archive and PRE. The already performed unique native read is `logs/c08_h18_n255_full3_native_r1.check.json`; no repeat decode is included. Its actual call and native completion/metadata are bound. The full22 typed binary/layout/clock inputs must match the exact consumed Entries in the completed offline `logs/c08_h18_n255_full3_review_r1.check.json`, rather than merely accepting fresh file stats. They remain bound before and after build. This requires completed offline analysis with unchanged inputs, not a physical pass; passing these receipts is not physical acceptance. The original built r2 entry and r1 recipe must also still match their retained successful r2 build bindings before deriving this new entry.

The native collection is full301 with6805 IDs, fixed0..1804, retired1805..2059 and soil2060..7059. The saved Part200/250 states include the genuine +1 scheduling step; the final Part300 is completed2600000. Actual native binary/CSV clocks must match bitwise. No interpolation, `n*dt` replacement, invented receiver t=0 save or rewritten header is used. The full3 end is12.999999999592434s; the certified PRE actual time is9.999999999706008s. Labels such as “2/2.5/3s” are approximate release-relative descriptions, not substitutes for these saved clocks.

The completed full3 run uses the same certified same-material Wendland PRE and original receiver. The entry initializes its genuine loader/release once, then restores all selected states independently by native ID, rebuilding cells under the retained restoration lifecycle. Original wall codes, normals and slip are preserved. Actual fresh CPU derivatives/wall/FS state are observed; they are not claimed bit-identical to an unsaved GPU force stage. Original full3 BI4 and native files, original program/source capture/archive, PRE, seeds, runtime and old results remain untouched.

## Build and independent call

After root review, build-only command:

`D:/anaconda3/python.exe -B tests/support/c08_h18_late_rhs_r1_build.py --execution-authorized`

The recipe retains exactly86 sealed original physical DebugCPU objects and compiles/links only this one new entry with MSVC14.36 and the original DebugCPU flags. It extracts only the original160 archived headers and checks compiler dependencies. Authoritative VS tlogs and resolved libraries remain the inputs; no project/solution/canonical executable or physical TU is rebuilt. The successful receipt is `tests/logs/c08_h18_late_rhs_r1.build.json`, executable `tests/outputs/c08_h18_late_rhs_r1_build/C08H18LateRhsR1.exe`. Build code does not execute that program.

Only after the successful build and a separate root admission may this exact zero-advance component be invoked once (absolute paths recommended):

`C08H18LateRhsR1.exe --check --native tests/outputs/c08_h18_n255_full3_r1/native_r1 -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 tests/outputs/c08_h18_n255_full3_r1/c08_h18_n255_full3_r1 tests/outputs/c08_h18_late_rhs_r1`

The component's new folder must not exist. It writes only its `Run.out`, `soil_rhs.csv`, `terms.csv`, `walls.csv`, `summary.csv` and `completion.json` plus ordinary diagnostic runtime files. Expected coverage is3 original force/Darcy calls,15000 soil rows,45000 term rows,5415 wall rows and27 summaries, with15000 exact final-float literal checks. Physical advances, material returns, filters and extra Darcy calls remain zero. Original numerical and arithmetic failure gates are unchanged; a real CPU wall/force failure stays failed, with partial output preserved.

For each soil ID the entry preserves primary position/velocity/rho/effective stress/kappa/p/P0/J bits and completed clock. It verifies J/n/V/rho/k cache, roles, literal actual float-rate equality, expanded-term arithmetic and fluid/fixed donor reconciliation under the original operation-count roundoff envelope. It observes actual CPU theta, FS, acceleration and stress rate. Active wall scratch is reported separately from inactive slots; stale scratch is not interpreted as a physical donor.

Storage `S=sum(n*V/Kw*p)` and its separate changing-coefficient term are conditional linear-storage proxies, not conserved water mass or total energy. All/interior/FS receivers and all/fluid/fixed donor partitions are additive bookkeeping on one assembled stencil, not counterfactual wall removal. The three late samples may identify instantaneous drivers and cancellation; they cannot establish the integrated source of the full3 drift by themselves. No pressure mean subtraction, negative clipping, new free-surface policy, parameter sweep, half chain, PRE rerun, other-psi source/receiver, long solve or physical acceptance follows automatically.

The root must retain real process exits, first errors and unchanged consumed Entries. Inner completion alone is insufficient. A failed/partial build or call is not overwritten or retried by this script. No SHA scanning is introduced.

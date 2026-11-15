# Independent GPU HG first-n force reference

AUTHOR ONLY: new c08_h18_hg_gpu_forcecheck_r1.cpp/_build.py and this note. The builder may later generate one private test-only core header under its fresh build directory. It never runs the component. No GPU/CPU program, build, solver, material return, decoder, Git or SHA was executed by these authors. All numeric/GPU source and successful output assets remain unchanged.

The sole eventual input is the actual Debug C08PlasticHGDebugFirstN.csv from outputs/c08_h18_hg_gpu_debug2_r1: exactly5000 original IDs2060..7059, with x/z/vx/vz/current V/current inertia/gamma and the final double HG force before its float acceleration cast. That first n snapshot is taken before the later h graph can overwrite it. It does not contain guessed PRE/half history. Source time is exactly9.9999999997060076, global2000000, full dt5us and trial width2.5us, cold e0. Root must bind the genuine passed Debug run/config/snapshot stats and check Config JSON before constructing the invocation. CPP stat-protects both CSV and JSON throughout its call; Config scalar arguments are supplied by that independent root wrapper, not parsed from arbitrary XML or inferred by n*dt.

## Independent reference and deliberately narrow order adaptation

The reference uses the already executed c08_h18_hg_numeric_r1 Audit core: its input validation, outward scalar-error arithmetic, positive actual-volume/inertia, support/rank/condition<1e8/necessary5us, complete LS and full adjoint, exact fixed-input local history integral, small-angle polynomial and ledger checks are retained. It calls a fresh State once with predictor width and never commits. This is not another physical step, material evaluation, matrix suite or27/65-fixture rerun.

The original CPU cell/pair traversal and scatter association differ from the GPU receiver-native-ID/reverse gather. Therefore no old CPU20k bit proof is silently claimed across backends. The builder makes three explicit test-only order adaptations, in addition to the private namespace rename: sort directed rows by receiver/donor before M/L accumulation; form the reverse displacement by xj−xi rather than unary-minus so the scalar signed-zero path matches; and replace only ApplyPT scatter by receiver gather of independently computed qij and its true reverse. The gather still forms Zi/Ti and back-propagates the complete LS fit. It does not use GPU row data or explicit basis-P as the implementation. Every source edit has unique-count and full byte-reverse proof, and the original header is never edited.

CPU support discovery is independently rebuilt from the exported coordinates through the already bounded linked-cell algorithm, not copied from the GPU graph. That can expose a GPU neighbor omission. Existing positive/rank/ambiguous-support/Audit-domain failures are retained as real reference failures; no diagonal regularization, epsilon-zero or output-fitting tolerance is added. Gamma and current V/m are the actual GPU inputs, so this reference does not separately requalify their material/source producers.

## Predetermined comparison model

For each of the10000 Fx/Fz scalars the predeclared absolute budget is the outward sum of two identical reference Audit enclosures plus the RN subtraction's own error:

    difference = GPU − CPU_reference
    budget = EA(EA(reference_error, reference_error), Round(difference))

EA/Round are the existing checked outward routines. The two evaluation terms express the same binary64 RN ordered-scalar error model, with explicit RN GPU add/multiply/divide/sqrt and the shared polynomial; the comparison does not fit a force scale, Pa threshold, relative physical tolerance or observed disagreement. The GPU is not being instrumented with per-op interval bounds here, so the same-RN-operation-model assumption is explicit. Unexpected implementation/graph/branch differences are exactly what the independent comparison is intended to falsify. CPU Audit gates and budget finiteness remain necessary.

Actual bit equality is counted and reported; it is not the admission criterion. Different CPU/GPU evaluation contexts may produce nonidentical values within the predetermined arithmetic envelope. This result cannot establish GPU material bit equality (the real Pre/Corr checks do that), float acceleration commit correctness, later nonzero-history/lifecycle correctness, coupled passivity or physical repair. No comparison is made to an invented native stage force.

The component writes one5000-row force_comparison.csv, a small completion.json, and failure.txt only inside a newly created fixed output. Every force scalar is compared; first failure records real ID/component/GPU/reference/difference/budget/ratio, and all comparison rows are retained. Existing complete/partial outputs are rejected without appending to them. All raw source files are left untouched. The CPU FP mode must be RN with FTZ/DAZ off; it is checked, never changed.

## Build/invocation boundary

The builder requires the actual passed numeric check/build/compiler/linker calls and source core stat. It compiles one DebugCPU/CRT entry with the original MSVC14.36 /Od /MTd /RTC1 /fp:precise /std:c++17 recipe; the only private include is the generated core. No physical objects, public headers, project libraries or runtime copies are used. Preparation/build uses no future snapshot or fake successful GPU receipt.

Future root-owned call, not executed here:

    C08H18HgGpuForcecheckR1.exe --check SNAPSHOT_CSV CONFIG_JSON FRESH_FIXED_OUT h bwen G xi dt width source_time source_step

The closed paths and ten-column schema must match the real Debug first-n files. Root must supply all argv entries as strings, bind the actual JSON values/stat to the call, then independently review every result. A passed check is one CPU/GPU frozen-input implementation comparison only: no physical updates, solver/native, new trajectory, restart, full energy stability or C08 scientific acceptance follows.

# Failure-only Pre material raw capture

AUTHOR ONLY: only `support/c08_h18_hg_matprobe_r1_build.py` and this note are new. This script has independent `prepare` and `build` operations; it never runs a GPU program, solver, help command, reader/native adapter, VTK, queue, Git or follow-on job. The author does not execute/import either operation. Root must read both frozen assets before separately preparing and building. A later narrowly bounded diagnostic replay, if justified, needs a separate owner/admission; no runner is included here.

## Why this specific observation is needed

The retained `c08_h18_hg_window_GPU_r1` failed genuinely with native/Popen exits1 and no ownership error. The original first error is step2000731/PreMaterial, nativeID7011, sorted slot2103, sigma_xx actual−5599.0531266314883 versus shadow−5599.0531266314892Pa:1ULP, absolute9.094947017729282e−13Pa. This is not evidence of physical divergence. Its reported source clock10.003654999705869 is not a saved failure state; only the first PART was saved. The old process is gone, so missing raw inputs cannot be reconstructed after the fact. All old results, failure/owner/queue receipts, inputs and programs stay unchanged.

The original predictor leaves the n stress alive in `SigmaPreg`: `JSphGpu.cpp:1763` swaps the old stress buffer there, and `ComputeSymplecticPre` reads it. The private check hook runs immediately after that method returns, before scratch cleanup and cell division. `Rsigmag` and the ID ordering are also still live. Corrector returns after freeing `SigmaPreg`, so this probe explicitly does **not** dereference a post-Corr base pointer or claim a Corr raw-capture facility.

## Exact new boundary

Preparation derives three files from the **already captured/passed private HG Release** source, retaining their basenames in a new `c08_h18_hg_matprobe_r1_source` directory. Original source/author files are never patched in place.

- The private `CheckMaterial` API receives three additional host-context arguments: base SigmaPreg, Rsigmag and DirOut.
- The Pre call supplies those genuine live pointers. Corr supplies null base/rate and cannot capture.
- The original `CheckMaterialKernel` call and every device definition remain unchanged. Its original `ErrorNow` rejection is wrapped by a host-only catch: only a genuine isolated MaterialMismatch in Pre may write raw evidence, then the original exception is rethrown unchanged.

Before any additional CUDA read, the failure branch writes `C08HGMatProbeFirstError.json` containing the actual original first error/source step/source clock and strict-rejection declaration. It then verifies the genuinely claimed error ID/slot against the current ID/map and reads just that particle. A capture error is reported separately to stderr; it never replaces or suppresses the original exception. There is no extra normal-path D2H read, per-stage full-state copy, new kernel, threshold change, regularization, time-step change or physical update.

`C08HGMatProbePreRaw.json` contains all six n-base stress doubles, all six actual float stress-rate values, all six actual returned half-stress doubles, current Pre kappa array value, shadow expected stress/old kappa/new kappa/qtrial/qreturn/status/gamma/root ratio, source clock/operator width and original reported error values. Every floating field has a17-digit decimal string and its native binary32/binary64 IEEE hex bits. The packed tensor order remains `(xx,xy)/(xz,yy)/(yz,zz)`.

The labels are deliberately asymmetric: the actual predictor kappa array still contains **old kappa**. The real material kernel's candidate returned kappa and internal Status are **not observed** by this adapter. `shadow_returned_kappa` and `shadow_status` are only the private shadow's outputs; neither is labeled as the production material result. The capture is not a native BI4 failure state, full particle export, restart state or physics acceptance.

## Mechanical proof and build closure

Each header/host/CUDA textual replacement has an exact unique old anchor and a reversible byte proof. The complete original CU prefix before host `Need`—including every original device definition and NodeKernel numeric body—must remain byte-identical. Device/kernel counts cannot increase. All changes are in the private API declaration, two private host calls and host-only failure handling/output definitions. The first error is preserved before dump reads. No GPU arithmetic compiler flag changes are admitted.

The builder reuses the already successful private HG Release's three **actual structured** CL/NVCC/link invocations. It rehomes the frozen include/source paths, IntDir and every private/link output, compiles the new host and CU, and links the same112 original physical objects plus two new private objects=114. Original force, Simpleker material, Darcy, legacy HG and all other original objects remain. This is a new derivative build, not an invented earlier object seal. No old object tree enumeration, full solution build or SHA scan is added.

New source preparation and new build directories/receipts are exclusive. Original source captures/archive, parent program/objects/runtime, failing call/log/PRE and passed implementation gates are stat-bound and checked again after the bounded operation. The original nine runtime files are copied to the private output and checked for byte identity. Any failure preserves its actual tool call, first error and partial artifacts, without overwriting old or new results. This script does not automatically retry a build or prepare/run a solver.

Future root-only operations after full review:

    python support/c08_h18_hg_matprobe_r1_build.py prepare --execution-authorized
    python support/c08_h18_hg_matprobe_r1_build.py build --execution-authorized

Successful build means only that the output-only diagnostic is available. A separately authorized fresh-tag replay would be capped near the first mismatch (about800 updates), not the entire0.9-second attempt, and reuse the original certified PRE without recalculating it. The strict material bit comparison stays unchanged. Interpretation of captured raw data, a possible single-particle arithmetic/FMA diagnosis, any numerical producer change and continuation of the collapse remain later root decisions.

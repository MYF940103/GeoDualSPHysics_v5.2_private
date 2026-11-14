# Private RV build environment repair r2

The actual r1 Debug and Release host CL tools exited0. Both NVCC tools exited1 before CUDA compilation/linking, with the reported compiler-in-PATH versus original `-ccbin` mismatch. These original failed receipts, outputs and frozen sources remain protected. This is an author-only build-environment repair, not a solver or numerical change.

`support/c08_h18_rv_gpu_build_r2.py --configuration Debug|Release --execution-authorized` transparently derives from the frozen r1 builder. The complete difference is `notes/c08_h18_rv_gpu_build_r2.diff`: fresh r2 output/receipt labels, fresh no-space r2 IntDir, and a separate NVCC environment whose PATH begins with the unchanged original `-ccbin` directory. Only that environment normalizes the case-insensitive PATH key; explicit host CL and link retain their original environment. The original `-ccbin`, `--use-local-env`, all compiler/link flags and all physical sources are unchanged. No host-adoption or retry framework is introduced.

The source capture, preparation receipt, author note and private host/CUDA/header remain frozen r1. Link membership remains112 original objects plus2 new private objects =114. New receipts are `logs/c08_h18_rv_gpu_Debug_r2.build.json` and `logs/c08_h18_rv_gpu_Release_r2.build.json`; outputs use the same stems. The runner must explicitly consume these r2 build receipts/programs after actual success; the new builder does not edit or execute that runner.

Only authoring and Python AST parsing were performed for this r2 file. Preparation, compilation, help, solver, native/VTK and Git calls were not executed by its author. Root independently reviews and admits any actual build. Build success would still not admit physical calculation.

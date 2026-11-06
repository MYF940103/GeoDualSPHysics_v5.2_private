# Shared material return: bounded CPU/GPU review

2026-11-06. This is a test-only constitutive core; no production material selector, spatial plastic admission or collapse run is implied.

The same shared host/device function consumed 66 retained deviatoric-history material cases and five explicit invalid cases. Separate MSVC CPU and CUDA Debug programs each returned 18 elastic, 36 radial, 12 unsupported apex and five invalid results. Six constant-strength cases also match their closed-form return. All 17 unsupported/invalid input states remain unchanged, member by member; structure padding is not compared. NonConverged has no natural witness in this set and remains untested.

For the 36 radial cases, the maximum independently recomputed yield residual is 4.547473508864641e-12 Pa using continuous endpoint kappa, and 3.7070172766107135e-5 Pa after the intentional float kappa write. These are different diagnostics. The existing float material parameters and persistent kappa are retained; only the coefficient, root and tensor arithmetic is double. This is an algorithm/history comparison, not an isolated precision experiment or a spatial accuracy result.

GPU results match the actual separately executed MSVC CPU results in all 71 defined state fields; stress, continuous kappa, lambda and saved kappa differences are zero in this set. One kernel also preserves all 73 input records and both output-tail canaries. The original independent residual, compliance, invariant and reference budgets were retained.

Actual CPU compile, link and target exits were zero. GPU NVCC compile/link, compute-sanitizer and retained target exits were zero; memcheck reports zero errors and zero leaked bytes. GPU standalone linking reported existing-style LNK4098 (LIBCMT/default CRT conflict with the Debug static CUDA runtime); this warning was retained, without changing flags to obtain agreement. No engine object, solver, BI4 decoder, repeated half-step chain or SHA scan was used.

Evidence: `../logs/upl_material_shared_CPU_r1.check.json`, `../logs/upl_material_shared_GPU_r1.check.json`, their actual call/build records, and both `../outputs/upl_material_shared_{CPU,GPU}_r1/result/points.csv`; GPU `CPU_GPU.csv` contains the joined results and original budgets.

The next implementation is an independent opt-in material-return choice, defaulting to the existing fast path. Preserve predictor kappa restoration and corrector commitment, and use explicit tensor member mapping on both backends. Unsupported apex returns must stop the candidate stage rather than silently use an elastic state or invent a tensile cap/history law. Initial equilibrium, wall release, variable permeability and spatial plastic validation remain separate work.

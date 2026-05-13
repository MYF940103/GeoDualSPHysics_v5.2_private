# M3a C++ MCC Helper Design

## Objective

M3a ports the M2 Python material-point model into an isolated C++ helper and driver. It is a parity step, not SPH integration.

## Location

Implemented under:

```text
src/papers/u-p/mcc_single_point/cpp/
```

Files:

- `mcc_model.h`;
- `mcc_model.cpp`;
- `mcc_single_point_driver.cpp`;
- `build_mcc_cpp.bat`;
- `README.md`.

The helper does not participate in the GeoDualSPHysics Visual Studio projects.

## C++ Parameter Interface

`mcc::Params` contains:

- `lambda`;
- `kappa`;
- `m`;
- `e0`;
- `pc0`;
- `young`;
- `poisson`;
- `tension_cutoff`;
- `return_tolerance`;
- `return_max_iter`;
- `max_line_search`.

`bulk()` and `shear()` are computed from `young` and `poisson`, matching M2.

## C++ State Interface

`mcc::State` contains:

- compression-positive stress tensor;
- `pc`;
- void ratio `e`;
- plastic volumetric strain;
- equivalent plastic strain diagnostic;
- plastic multiplier;
- yield flag;
- return status string;
- iteration count;
- residual.

This mirrors M2 and is intentionally independent from SPH arrays.

## Functions

The helper provides:

- `invariants()`;
- `yield_function()`;
- `elastic_predictor()`;
- `return_mapping()`;
- `update_state()`;
- `to_sigmac_negative_compression()`;
- `from_sigmac_negative_compression()`;
- path generators for isotropic, drained-like, and undrained-like tests.

## Stress Convention

C++ uses the same internal convention as Python:

```text
compression-positive internal stress
```

Mapping to future SPH `Sigmac` remains:

```text
Sigmac = -sigma_internal
p' = -trace(Sigmac) / 3
```

This conversion should remain localized in future M3b/M3c integration.

## Return Mapping

The C++ implementation reproduces the M2 local Newton return mapping with unknowns:

```text
p, q, p_c, Delta gamma
```

It uses finite-difference Jacobians and line search for parity with Python. A future solver-side implementation can keep the same math and later optimize the Jacobian.

## Driver Output

The standalone driver writes:

- `m3a_cpp_sign_regression.csv`;
- `m3a_cpp_isotropic_path.csv`;
- `m3a_cpp_drained_triaxial_path.csv`;
- `m3a_cpp_undrained_path.csv`;
- `m3a_cpp_yield_consistency.csv`;
- `m3a_cpp_return_iterations.csv`;
- `m3a_cpp_test_summary.csv`.

These are compared against M2 Python outputs by `compare_mcc_python_cpp.py`.

## Build

Build command:

```text
cmd /c papers\u-p\mcc_single_point\cpp\build_mcc_cpp.bat
```

The script uses VS2022 `cl.exe` and creates a local executable under `cpp/build/`. Build artifacts are not retained in git.

## Future Solver Use

The helper is suitable as a reference for a future solver-side MCC helper. M3b still needs parser integration, state arrays, output, restart, and careful CPU stress-update hook design before any SPH run.

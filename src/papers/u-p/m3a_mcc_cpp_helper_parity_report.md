# M3a MCC C++ Helper Parity Report

## Objective

M3a implements an isolated C++ Modified Cam Clay material-point helper and checks parity against the M2 Python prototype. It does not connect MCC to the SPH solver.

## Implementation Status

Implemented:

- C++ helper: `src/papers/u-p/mcc_single_point/cpp/mcc_model.h`;
- C++ helper implementation: `src/papers/u-p/mcc_single_point/cpp/mcc_model.cpp`;
- standalone driver: `src/papers/u-p/mcc_single_point/cpp/mcc_single_point_driver.cpp`;
- build script: `src/papers/u-p/mcc_single_point/cpp/build_mcc_cpp.bat`;
- Python-C++ parity script: `src/papers/u-p/mcc_single_point/compare_mcc_python_cpp.py`.

No production solver files were changed.

## Commands Run

```text
py -m py_compile papers\u-p\mcc_single_point\compare_mcc_python_cpp.py papers\u-p\mcc_single_point\run_mcc_single_point_tests.py papers\u-p\mcc_single_point\mcc_single_point.py
cmd /c papers\u-p\mcc_single_point\cpp\build_mcc_cpp.bat
py papers\u-p\mcc_single_point\run_mcc_single_point_tests.py
papers\u-p\mcc_single_point\cpp\build\mcc_single_point_driver.exe papers\u-p\mcc_single_point\output
py papers\u-p\mcc_single_point\compare_mcc_python_cpp.py
```

No GenCase, DualSPHysics, PartVTK, SPH CPU simulation, or GPU simulation was run.

## Symbol Convention

C++ matches Python M2:

- internal MCC stress is compression-positive;
- current GeoDualSPHysics `Sigmac` maps as `sigma_internal = -Sigmac`;
- `p' = -trace(Sigmac)/3`.

The C++ sign regression matches Python exactly for the retained CSV output:

```text
Sigmac=(-50,-50,-50) Pa -> p'=+50 Pa -> Sigmac=(-50,-50,-50) Pa
```

## Return Mapping

C++ reproduces the Python semi-implicit local Newton return mapping with unknowns:

```text
p, q, p_c, Delta gamma
```

The C++ implementation uses the same finite-difference Jacobian and line-search style as M2 for parity.

## Parity Results

Parity summary from `m3a_python_cpp_parity_summary.json`:

| Path | Rows | Max `p'` diff | Max `q` diff | Max `p_c` diff | Max iteration diff |
| --- | ---: | ---: | ---: | ---: | ---: |
| isotropic | `181` | `0` | `0` | `0` | `0` |
| drained-like | `141` | `0` | `0` | `0` | `0` |
| undrained-like | `141` | `0` | `0` | `0` | `0` |

Additional checked fields also have zero maximum CSV-level difference:

- void ratio `e`;
- plastic volumetric strain;
- equivalent plastic strain;
- plastic multiplier;
- stress components;
- mapped `Sigmac` components;
- normalized yield residual;
- yield flag.

## Yield Residual

The C++ output preserves the M2 yield consistency behavior. Maximum normalized plastic-step yield residual remains:

- isotropic: about `8.42e-11`;
- drained-like: about `2.69e-9`;
- undrained-like: about `2.68e-9`.

## p_c Hardening

C++ and Python hardening are identical in retained outputs:

- isotropic: `p_c` final `194.483439914 Pa`;
- drained-like: `p_c` final `205.259045757 Pa`;
- undrained-like: `p_c` final `166.067025917 Pa`.

## Figures

Generated parity figures include:

- Python vs C++ isotropic `p'-q`, `p_c`, residual, iterations;
- Python vs C++ drained-like `p'-q`, `p_c`, residual, iterations;
- Python vs C++ undrained-like `p'-q`, `p_c`, residual, iterations.

## Assessment

The C++ standalone helper passes M3a parity and is suitable as the numerical reference for M3b parser/state integration planning.

It is still not connected to SPH because the production solver needs:

- `SoilConstitutiveModel=3` parser support;
- MCC state arrays;
- output fields;
- restart fields;
- CPU stress update hook;
- GPU hard error for model `3`;
- feedback-off SPH smoke gates.

Full pore-pressure feedback and GPU remain deferred.

# M2 MCC Single-Point Prototype Report

## Objective

M2 implements a standalone Modified Cam Clay material-point prototype. It is not connected to the GeoDualSPHysics solver, does not add `SoilConstitutiveModel=3`, and does not run any SPH case.

The retained implementation and outputs are under:

```text
src/papers/u-p/mcc_single_point/
```

## Prototype Status

Implemented:

- `mcc_single_point.py`: standalone MCC material model and helpers;
- `run_mcc_single_point_tests.py`: test runner, CSV writer, and figure generator;
- `mcc_return_mapping_notes.md`: prototype equations and limitations;
- retained CSV output under `output/`;
- retained SVG/PNG figures under `figures/`.

Validation commands run:

```text
py -m py_compile papers\u-p\mcc_single_point\mcc_single_point.py papers\u-p\mcc_single_point\run_mcc_single_point_tests.py
py papers\u-p\mcc_single_point\run_mcc_single_point_tests.py
```

No GenCase, DualSPHysics, PartVTK, CPU SPH, or GPU simulation was run.

## Sign Convention

The prototype uses compression-positive MCC variables internally:

```text
p' = trace(sigma_internal) / 3
```

Mapping to the current GeoDualSPHysics convention is:

```text
sigma_internal = -Sigmac
p' = -trace(Sigmac) / 3
```

The stress sign regression test uses `Sigmac=(-50,-50,-50) Pa`, maps it to internal `p'=+50 Pa`, and maps it back to negative-compression `Sigmac`.

Result: passed.

## Elastic Predictor

M2 uses a linear isotropic `E, nu` elastic predictor:

```text
Delta sigma = K Delta epsilon_v I + 2G dev(Delta epsilon)
```

Default diagnostic parameters:

| Parameter | Value |
| --- | ---: |
| `M` | `1.20` |
| `lambda` | `0.20` |
| `kappa` | `0.04` |
| `e0` | `0.80` |
| `p_c0` | `160 Pa` |
| `E` | `5000 Pa` |
| `nu` | `0.30` |
| return tolerance | `1e-8` |
| max iterations | `45` |

The `E, nu` predictor is a diagnostic first step. A `kappa`-based nonlinear MCC elastic law should be evaluated before production SPH integration.

## Return Mapping

The yield surface is:

```text
f = q^2 + M^2 p' (p' - p_c)
```

The plastic corrector solves a four-variable local Newton system for:

```text
p, q, p_c, Delta gamma
```

with associated invariant directions:

```text
df/dp = M^2 (2p - p_c)
df/dq = 2q
```

Hardening uses:

```text
p_c,new = p_c,old * exp((1 + e_old) Delta epsilon_p_v / (lambda - kappa))
```

The implementation uses finite-difference Jacobians and line search. It is intentionally standalone and readable; M3 should port the verified logic into a C++ helper rather than calling this Python code.

## Test Results

Summary from `m2_mcc_test_summary.csv`:

| Test | Failed steps | Plastic steps | Final `p'` | Final `q` | Final `p_c` |
| --- | ---: | ---: | ---: | ---: | ---: |
| stress sign regression | `0` | `0` | `50.0 Pa` | `0` | `160 Pa` |
| isotropic compression/swelling | `0` | `58` | `194.48 Pa` | `~0` | `194.48 Pa` |
| drained-like triaxial | `0` | `100` | `180.26 Pa` | `80.55 Pa` | `205.26 Pa` |
| undrained-like zero-volume path | `0` | `87` | `86.22 Pa` | `99.57 Pa` | `166.07 Pa` |

No path hit the tension cutoff.

## Isotropic Compression / Swelling

The isotropic path gives `q ~ 0`, hardens from `p_c0=160 Pa` to `p_c=194.48 Pa`, and reduces void ratio from `e0=0.80` to `e=0.7285` under net compression.

Interpretation: reasonable for a first diagnostic material-point path.

## Drained-Like Path

The drained-like path is strain-controlled axial compression with zero lateral strain. It is not a strict constant-confining-stress triaxial driver.

It produces a readable `p'-q` path, plastic activation, and monotonic hardening to `p_c=205.26 Pa`.

Interpretation: useful for return-mapping diagnostics, but not a strict drained triaxial validation path.

## Undrained-Like Path

The undrained-like path imposes zero volumetric strain through deviatoric increments. It is not full u-pw coupling.

It produces a distinct effective stress path with `p'` decreasing to `86.22 Pa` while `q` increases to `99.57 Pa`. The pore-pressure proxy is diagnostic only.

Interpretation: reasonable material-point check, but not strict undrained SPH validation.

## Yield Consistency

From `m2_mcc_yield_consistency.csv`, maximum normalized yield residual on plastic steps:

| Path | Max normalized `|f|` on plastic steps | Max iterations |
| --- | ---: | ---: |
| isotropic | `8.42e-11` | `3` |
| drained-like | `2.69e-9` | `5` |
| undrained-like | `2.68e-9` | `5` |

This satisfies the M2 diagnostic gate for a standalone prototype.

## p_c Hardening

`p_c` increases during plastic compression:

- isotropic: `160 -> 194.48 Pa`;
- drained-like: `160 -> 205.26 Pa`;
- undrained-like: `160 -> 166.07 Pa`.

The trend is monotonic in the retained tests where plastic compression occurs.

## Figures

Generated SVG and PNG figures:

- `m2_isotropic_e_logp`;
- `m2_pq_paths`;
- `m2_pc_evolution`;
- `m2_yield_residual`;
- `m2_plastic_multiplier`;
- `m2_iteration_count`;
- `m2_stress_sign_regression`;
- `m2_yield_consistency_summary`.

## Limitations

M2 is not SPH integration:

- no `SoilConstitutiveModel=3`;
- no solver source changes;
- no restart/output MCC arrays in the production code;
- no full u-pw feedback;
- no GPU;
- drained-like path is not strict constant-confining-stress triaxial;
- undrained-like path is zero-volume material-point loading, not full pore-pressure coupling.

## M3 Readiness

M2 is sufficient to enter M3 planning/implementation for a CPU-only MCC helper and `SoilConstitutiveModel=3` integration, provided M3 keeps the first SPH smoke feedback-off and reduced.

Before M3 is merged into solver behavior, it still needs:

- C++ helper parity with this Python prototype;
- parser/state/output/restart design implemented;
- CPU-only hard errors for unsupported GPU path;
- SPH smoke cases based on the T5 explicit-platen workflow.

Full feedback and GPU remain deferred.

# M3a Python MCC Mapping Audit

## Scope

This audit maps the M2 Python standalone Modified Cam Clay prototype before porting it to a C++ helper. M3a remains outside the SPH solver.

## Python Files

The M2 prototype lives under:

```text
src/papers/u-p/mcc_single_point/
```

Core files:

- `mcc_single_point.py`: material model, tensor helpers, return mapping;
- `run_mcc_single_point_tests.py`: loading paths, CSV output, figures;
- `mcc_return_mapping_notes.md`: prototype equation notes.

## State Variables

Python `MCCState` contains:

- stress tensor in internal compression-positive convention;
- `pc`: preconsolidation pressure;
- `e`: void ratio;
- `eps_p_v`: plastic volumetric strain diagnostic;
- `eps_p_eq`: equivalent plastic strain diagnostic;
- `plastic_multiplier`;
- `yield_flag`;
- `return_status`;
- `iterations`;
- `residual`.

The C++ helper should reproduce these fields before any SPH integration.

## Stress Convention

Python M2 uses compression-positive stress internally. It maps current GeoDualSPHysics `Sigmac` through:

```text
sigma_internal = -Sigmac
p' = -trace(Sigmac) / 3
```

The sign regression test starts from `Sigmac=(-50,-50,-50) Pa`, maps to `p'=+50 Pa`, then maps back to negative-compression `Sigmac`.

## Invariants

Python definitions:

```text
p = trace(sigma) / 3
s = sigma - p I
J2 = 0.5 s:s
q = sqrt(3 J2)
```

The C++ helper must keep the same tensor dot-product convention and the same compression-positive `p`.

## Yield Function

Python M2 uses:

```text
f = q^2 + M^2 p (p - p_c)
```

Elastic acceptance checks the trial value against a normalized tolerance. Plastic consistency is reported with both raw and normalized residuals.

## Elastic Predictor

M2 uses linear isotropic elasticity:

```text
Delta sigma = K Delta eps_v I + 2G dev(Delta eps)
```

with `K` and `G` computed from diagnostic `E, nu`.

This is intentionally not yet the full `kappa`-based nonlinear MCC elasticity.

## Hardening Law

The Python prototype updates:

```text
p_c,new = p_c,old * exp((1 + e_old) Delta eps_p_v / (lambda - kappa))
```

where `Delta eps_p_v = Delta gamma * M^2 (2p - p_c)`.

## Newton Unknowns

The local return mapping solves for:

```text
p, q, p_c, Delta gamma
```

Residual equations:

```text
r_p  = p - p_tr + K Delta gamma M^2(2p - p_c)
r_q  = q - q_tr + 3G Delta gamma 2q
r_pc = p_c - p_c,old exp((1+e_old) Delta eps_p_v/(lambda-kappa))
r_f  = q^2 + M^2 p(p-p_c)
```

The Python implementation uses finite-difference Jacobians and line search.

## Convergence Criteria

The Python path reports:

- `plastic_converged`;
- `elastic`;
- `line_search_failure`;
- `jacobian_failure`;
- `tension_cutoff`.

M2 retained paths converged with maximum Newton iterations of `5`. Maximum normalized plastic-step yield residual was about `2.7e-9`.

## Tension Handling

If `p_tr <= tension_cutoff`, Python returns a `tension_cutoff` status. M2 retained tests did not hit this path.

M3b SPH integration should initially hard-stop or counted-error on this status rather than silently clamping.

## Test Paths

Python M2 paths:

1. stress sign regression;
2. isotropic compression/swelling;
3. drained-like strain-controlled triaxial path;
4. undrained-like zero-volumetric-strain path;
5. yield consistency summary;
6. return iteration diagnostics.

## CSV Format

Path CSVs include:

- step;
- strain increment components;
- stress components;
- mapped `Sigmac` components;
- `p`, `q`, `p_c`, `e`;
- plastic multiplier;
- plastic volumetric/equivalent strain;
- yield residual;
- normalized yield residual;
- status and iteration count.

The C++ driver should write compatible `m3a_cpp_*.csv` files for parity comparison.

## Core Functions to Replicate

The C++ helper should reproduce:

- tensor helpers: `trace`, `deviator`, `invariants`;
- sign mapping helpers;
- `yield_function`;
- `elastic_predictor`;
- `return_mapping`;
- `update_state`;
- loading path generators.

Only after this parity is verified should the implementation be ported into a solver-side C++ helper.

# M2 MCC Return Mapping Notes

This directory contains a standalone Python material-point prototype for Modified Cam Clay. It is not connected to the GeoDualSPHysics solver.

## Convention

The prototype uses compression-positive stresses and strains internally. The helper functions map to the current GeoDualSPHysics `Sigmac` convention by multiplying the stress tensor by `-1`, because current `Sigmac` stores compression as negative.

```text
p' = -trace(Sigmac) / 3
```

## Yield Function

The prototype uses:

```text
f = q^2 + M^2 p' (p' - p_c)
```

with `p' > 0` and `p_c > 0`.

## Elastic Predictor

M2 uses a linear isotropic `E, nu` elastic predictor:

```text
Delta sigma = K Delta eps_v I + 2G dev(Delta eps)
```

This is a diagnostic choice. A later MCC implementation may replace it with a `kappa`-based nonlinear elastic law after the return mapping is verified.

## Plastic Corrector

The corrector solves a four-unknown local Newton system for:

```text
p, q, p_c, Delta gamma
```

using an associated MCC flow direction in invariant form:

```text
df/dp = M^2 (2p - p_c)
df/dq = 2q
```

The hardening update is:

```text
p_c,new = p_c,old * exp((1 + e_old) Delta eps_p_v / (lambda - kappa))
```

The local Newton solve uses finite-difference Jacobians and a small line search. This is intentionally clear rather than optimized; M3 should port the verified logic to a C++ helper.

## Limitations

- This is a material-point prototype, not SPH integration.
- Drained triaxial is represented as a simplified strain-controlled drained-like path, not a strict constant-confining-stress driver.
- Undrained triaxial is represented as a zero-volumetric-strain material-point path, not full u-pw coupling.
- Full pore-pressure feedback and GPU are not involved.

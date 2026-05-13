# M1 MCC Theory and Sign Convention

## Objective

This note defines the Modified Cam Clay formulation to be used in future implementation planning and maps it to the current `Sigmac` storage convention.

## Compression Sign Mapping

Most MCC derivations use compression-positive mean effective stress. The current code stores compressive skeleton/effective stress as negative in `Sigmac`.

Use this mapping at the constitutive interface:

```text
m_stored = (sigma_xx + sigma_yy + sigma_zz) / 3
p'       = -m_stored
s_ij     = sigma_ij - m_stored * delta_ij
q        = sqrt(3 * J2)
J2       = 0.5 * s_ij * s_ij
```

Here `sigma_ij` are stored `Sigmac` components. `p'` is compression-positive. The deviatoric tensor is independent of the hydrostatic sign once `m_stored` is removed.

When returning stress to the code, the MCC-updated compression-positive state must be converted back to the stored negative-compression `Sigmac` convention.

## Yield Function

Use the standard compression-positive MCC yield surface:

```text
f = q^2 + M^2 * p' * (p' - p_c) = 0
```

Equivalently:

```text
f = q^2 - M^2 * p' * (p_c - p') = 0
```

where:

- `M` is the critical-state slope in `q-p'` space;
- `p_c` is the preconsolidation pressure;
- valid normally consolidated/compressed states require `p' > 0` and `p_c >= p'`.

The elastic domain is `f <= tolerance`.

## Stress Invariants

Mean effective stress:

```text
p' = -(sigma_xx + sigma_yy + sigma_zz) / 3
```

Deviatoric stress:

```text
s_xx = sigma_xx + p'
s_yy = sigma_yy + p'
s_zz = sigma_zz + p'
s_xy = sigma_xy
s_yz = sigma_yz
s_xz = sigma_xz

q = sqrt(1.5 * (s_xx^2 + s_yy^2 + s_zz^2
                + 2*s_xy^2 + 2*s_yz^2 + 2*s_xz^2))
```

This should be wrapped in a small helper in the implementation stage to avoid duplicated sign conversions.

## Hardening Law

For specific volume `v = 1 + e`, the standard isotropic hardening relation can be written as:

```text
d p_c / p_c = v / (lambda - kappa) * d epsilon_p_v
```

where:

- `lambda` is the virgin compression slope;
- `kappa` is the swelling/recompression slope;
- `epsilon_p_v` is compression-positive plastic volumetric strain.

If void ratio `e` is stored instead of `v`, use `v = 1 + e` at the update point.

The implementation must define a single compression-positive strain convention for MCC internal variables and document the conversion from the current SPH strain-rate sign.

## Elastic Law

MCC commonly uses pressure-dependent elastic bulk modulus:

```text
K = v * p' / kappa
```

The current code uses XML `ModulusK` and `ModulusG` for elastic and DP updates. The first MCC prototype should decide explicitly whether to:

1. keep the current constant elastic moduli for a minimal integration path; or
2. use pressure-dependent `K` for paper-faithful MCC behavior.

The recommended design path is to test pressure-dependent `K` in the standalone single-point driver first, before connecting it to SPH.

## Flow Rule

Classical MCC is associated:

```text
d epsilon_p = d gamma * d f / d sigma
```

This gives coupled plastic volumetric and deviatoric increments. The sign of `d epsilon_p_v` must be compression-positive in the hardening update.

## Tension and Low-Pressure Handling

MCC is not well-defined for tensile or near-zero effective mean stress. The implementation should enforce:

```text
p' >= MccTensionCutoff
p_c >= p' + small_margin
```

Recommended behavior for `p' <= cutoff`:

- single-point prototype: fail the step and report no-go;
- first SPH prototype: clamp only if explicitly requested by XML and count the event;
- production validation: avoid states that need clamping.

Silent clamping would hide formulation errors.

## Drained and Undrained Expectations

Drained triaxial compression should show volume change and a `q-p'` path governed by drainage and imposed confinement.

Undrained triaxial compression should develop pore pressure and an effective stress path controlled by the u-pw coupling. Because full feedback is currently deferred, the first MCC SPH case should be a feedback-off reduced baseline and not strict undrained validation.

## Implication for Current Code

MCC can be implemented as an effective-stress skeleton update. Pore pressure should remain outside the local MCC stress tensor. The key implementation risk is the sign conversion between negative-compression `Sigmac` and compression-positive MCC invariants.

# T4 Triaxial Output Field Audit

## Scope

T4 audits the fields available from the T1/T3 triaxial outputs before using
them for measurement-region and stress-path postprocessing. No source changes,
GPU runs, Cryer boundary work, MCC work, or long triaxial reproduction runs are
included in this audit.

The audited T4 output header is:

`Pos.x`, `Pos.y`, `Pos.z`, `Idp`, `Vel.x`, `Vel.y`, `Vel.z`, `Rhop`, `Type`,
`Sigma_kk.x`, `Sigma_kk.y`, `Sigma_kk.z`, `Sigma_ij.x`, `Sigma_ij.y`,
`Sigma_ij.z`, `Kplastic`, `PorePress`, `ExcessPorePress`, `PorePressRate`,
`DivVel`, `LapPorePress`, `LapZ`, `DivVelCorr`, `LapPorePressCorr`, `LapZCorr`,
`PorePressureAccel.x`, `PorePressureAccel.y`, `PorePressureAccel.z`,
`PorePressureAccelDiff.x`, `PorePressureAccelDiff.y`,
`PorePressureAccelDiff.z`.

## Directly Available Fields

| Field group | Status | Notes |
| --- | --- | --- |
| Position | available | Current particle positions are present. |
| Velocity | available | Current particle velocities are present. |
| Density | available | `Rhop` is available. Per-particle mass is not written, but the T4 XML uses the known material mass from the generated case. |
| Particle id | available | `Idp` is available and can be used to match the initial `Part_0000` frame. |
| Particle mk | not directly available | The CSV has `Type` but not explicit `mkfluid` or class labels. T4 reconstructs cylinder classes geometrically. |
| Pore pressure | available | `PorePress`, `ExcessPorePress`, and `PorePressRate` are written. |
| PR operators | available | `DivVel`, `LapPorePress`, `LapZ`, and corrected diagnostic variants are written. |
| Stress tensor | available | Six stress components are written as `Sigma_kk.*` and `Sigma_ij.*`. |
| Plasticity | available | `Kplastic` is written. T4 remains linear elastic, so the expected value is zero. |
| Displacement/original position | not directly available | Displacement must be reconstructed from `Idp` and `Part_0000` or approximated from specimen geometry. |
| Confinement class / f_i | not written per particle by source | T4 postprocessing recomputes the Zhao-style `f_i` and cylinder class from the current CSV frames. |

## Stress-Path Interpretation

The current CSV fields are enough to compute a useful stress-path proxy, but
not enough for a strict paper-level `p'-q` validation.

1. `p'` can be computed only as a skeleton/effective-stress proxy from the
   written `Sigma` tensor. The postprocessor uses compression-positive
   convention
   `p_eff_proxy = -(sigma_xx + sigma_yy + sigma_zz)/3`.
2. `q` can be computed from the deviatoric part of the written `Sigma` tensor.
   T4 uses
   `q_proxy = sqrt(1.5 * s_ij s_ij)`, with off-diagonal shear terms counted
   twice in the tensor contraction.
3. The output does not explicitly label `Sigma` as total stress or effective
   stress. In the current u-pw branch the pore pressure is written separately
   and is fed back through the coupling acceleration, so T4 treats `Sigma` as
   the material skeleton stress state for postprocessing. It does not subtract
   pore pressure again from `Sigma`.
4. A strict total/effective-stress reconstruction would need source-side
   documentation or explicit output of both stress conventions.

## Strain and Volume Measures

Axial strain is also a proxy at this stage.

- The primary T4 axial-strain proxy uses the mean current `z` of the top
  particle layer relative to the initial specimen height.
- A secondary height-based proxy uses the current `zmax-zmin` change.
- The two proxies can diverge in short dynamic runs because the top layer is
  driven by AccInput and the full height can respond nonuniformly.
- Volumetric strain is estimated as `-integral DivVel dt` within each
  measurement region. This is useful diagnostically but not yet a strict
  specimen volumetric strain.

## Measurement Regions

The T4 postprocessor defines five regions:

| Region | Definition | Purpose |
| --- | --- | --- |
| `center_core_small` | `r <= 0.25R`, middle 40-60 percent height | Small center response, most isolated from boundaries. |
| `center_core_medium` | `r <= 0.40R`, middle 30-70 percent height | Default center-core diagnostic. |
| `center_core_large` | `r <= 0.60R`, middle 20-80 percent height | More particles while still avoiding most caps. |
| `full_excluding_caps_edges` | interior plus lateral classes, excluding caps and edge rings | Bulk specimen proxy without cap/edge particles. |
| `zhao_measurement_cylinder` | `r <= 0.50R`, middle 25-75 percent height | Zhao-style central cylinder/cube analogue. |

Final-frame particle counts were:

| Region | Particles |
| --- | ---: |
| `center_core_small` | 3 |
| `center_core_medium` | 25 |
| `center_core_large` | 63 |
| `full_excluding_caps_edges` | 259 |
| `zhao_measurement_cylinder` | 45 |

## Audit Answers

1. Direct strict `p'` is not available; T4 computes a skeleton/effective-stress
   proxy from `Sigma`.
2. Direct strict `q` is not available; T4 computes a tensor-deviator proxy from
   `Sigma`.
3. `Sigma` is treated as the material skeleton/effective stress state, but the
   output does not explicitly label it. This needs source/output clarification
   before paper-level validation.
4. Pore pressure should not be subtracted from `Sigma` again under the current
   T4 interpretation. Total-stress reconstruction is deferred.
5. Axial strain can be estimated from top-layer displacement or total height,
   but neither is a strict controlled-strain measurement yet.
6. Volumetric strain can be approximated by integrating `DivVel`; this remains
   a proxy.
7. The current `p'-q` path is a proxy.
8. Future source output enhancement should add explicit `mk`, original
   position/displacement, per-particle volume or mass, stress-state convention,
   optional total stress, and optional per-particle confinement class and
   `f_i` fields.


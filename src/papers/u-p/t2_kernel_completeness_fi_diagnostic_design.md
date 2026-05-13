# T2 Kernel Completeness `f_i` Diagnostic Design

## Purpose

The next implementation should first observe Zhao's boundary-layer indicator without changing any force calculation:

```text
f_i = sum_j (m_j / rho_j) W_ij
```

The diagnostic answers whether the actual triaxial particle cloud has a clean separation between interior, lateral membrane, caps, and edge rings.

## Non-Behavioral First Step

T3 should add a diagnostic switch, off by default, that computes `f_i` for normal material particles during the CPU neighbor loop or a separate CPU diagnostic pass. It should not alter `FlexibleConfiningStress` application in the first smoke.

Proposed XML controls:

```xml
<parameter key="ConfiningStressFiDiagnostics" value="0" />
<parameter key="ConfiningStressFiThreshold" value="0.70" />
<parameter key="ConfiningStressFiCsv" value="1" />
```

Names are provisional. Defaults must preserve old behavior.

## Per-Particle Quantities

For each target candidate:

- particle id;
- `mkfluid`;
- position;
- radius from cylinder axis;
- axial coordinate;
- `f_i`;
- `f_i <= threshold`;
- geometric class: interior, lateral, top cap, bottom cap, edge ring;
- current confining acceleration magnitude;
- radial acceleration projection;
- axial acceleration projection.

The per-particle CSV can be limited to selected frames or small diagnostic cases to avoid large output.

## Summary Metrics

Per diagnostic print/frame:

| Metric | Meaning |
| --- | --- |
| `fi_min/max/mean/median` | Overall completeness distribution. |
| `fi_p05/p50/p95` | Robust threshold behavior. |
| `count_fi_le_070` | Zhao 3D boundary-layer count. |
| `count_lateral_fi_le_070` | Desired membrane candidates. |
| `count_topcap_fi_le_070` | False positives for lateral confinement. |
| `count_bottomcap_fi_le_070` | False positives for lateral confinement. |
| `count_edge_fi_le_070` | Cap/lateral mixed truncation. |
| `mean_radial_accel_projection` | Inward/outward traction check. |
| `mean_abs_axial_accel_projection` | Axial leakage check. |
| `net_force` and `COM_accel` | Symmetry and balance check. |

## Histogram

Recommended bins:

```text
0.00-0.40
0.40-0.50
0.50-0.60
0.60-0.70
0.70-0.80
0.80-0.90
0.90-1.00
1.00+
```

The key diagnostic is not just how many particles satisfy `f_i <= 0.70`, but whether those particles are spatially located on the lateral membrane rather than on caps or rough interior defects.

## Relationship To Confining Acceleration

For a correct Zhao-style term:

- low `f_i` lateral particles should have strong inward radial acceleration;
- interior high-`f_i` particles should have near-zero confining acceleration;
- cap particles may show axial acceleration from truncation and must be excluded for triaxial lateral confinement;
- edge-ring particles need either exclusion or a separate treatment because their normal is mixed.

T3 should report scatter summaries:

```text
f_i vs |a_conf|
f_i vs radial(a_conf)
f_i vs axial(a_conf)
```

## Output Files

Suggested outputs for a confinement-only smoke:

- `t3_fi_particle_diagnostics.csv`
- `t3_fi_summary.csv`
- `t3_fi_histogram.csv`
- `t3_fi_geometric_classification.csv`

Suggested figures:

- `f_i` histogram;
- `f_i` vs radius;
- radial acceleration projection vs radius;
- axial leakage by cap/lateral class;
- selected lateral candidates in an `x-z` or `r-z` view.

## Acceptance Criteria For Using `f_i` As Selector

Do not use `f_i` to alter confinement until:

1. lateral membrane particles form a coherent low-`f_i` band;
2. top/bottom cap false positives can be excluded geometrically;
3. interior low-`f_i` defects are rare;
4. radial projection is inward for lateral candidates;
5. net force and COM acceleration are small in a symmetric confinement-only smoke.

If these are not satisfied, the problem is likely particle-cloud quality or geometric classification rather than the pressure magnitude.

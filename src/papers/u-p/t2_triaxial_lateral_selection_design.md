# T2 Triaxial Lateral-Only Selection Design

## Goal

Strict triaxial compression requires flexible confinement on the cylindrical lateral membrane only. The top and bottom caps are mechanical loading/support surfaces and must not receive lateral confining traction from the Zhao boundary term.

## Geometry Definition

A cylinder selector should define:

- axis unit vector `a`, initially expected to be the global `z` axis;
- center point `c0` on the bottom or mid-height plane;
- radius `R`;
- height `H`;
- axial coordinate:

```text
s_i = dot(x_i - c0, a)
```

- radial vector:

```text
rvec_i = (x_i - c0) - s_i * a
r_i = |rvec_i|
```

## Geometric Classes

Recommended classes:

| Class | Criterion |
| --- | --- |
| Interior | `r_i < R - tol_r` and cap criteria false. |
| Lateral band | `abs(r_i - R) <= tol_r` and `cap_margin < s_i < H - cap_margin`. |
| Top cap | `s_i >= H - cap_margin`. |
| Bottom cap | `s_i <= cap_margin`. |
| Edge ring | lateral band and cap band overlap. |
| Outside/invalid | outside expected cylinder envelope. |

Initial tolerances should be expressed in terms of `dp` or smoothing length:

```text
tol_r = 1.5 dp to 2.0 dp
cap_margin = 1.5 dp to 2.0 dp
```

These values are diagnostic starting points, not calibration targets.

## Interaction With `mkfluid`

The selector should be applied after the existing target mk rule:

```text
candidate = IsFlexibleConfiningStressTarget(code[i])
```

Then:

```text
candidate = candidate && lateral_selector(i)
```

This preserves the current `ConfiningStressTargetMk` behavior and allows existing case geometry to tag soil/cap/platen material separately.

## Interaction With `f_i`

Two staged options:

1. Diagnostic-only:
   - compute lateral class and `f_i`;
   - report overlaps;
   - do not change forces.

2. Selector-enabled:
   - require lateral class;
   - optionally require `f_i <= threshold`;
   - exclude caps and edge rings unless explicitly enabled.

For first T3 implementation, the safest route is diagnostic-only, followed by an explicit XML switch for selection once the classification is verified.

## Cap Exclusion

Cap exclusion is mandatory. Without it, the Zhao term will produce axial traction on free cap surfaces because cap kernels are also truncated. That would contaminate the axial stress path and make the test no longer a clean triaxial compression.

Edge rings should be treated conservatively:

- exclude from lateral confinement for the first smoke; or
- include only if radial projection dominates axial projection by a documented ratio.

## Measurement Region

The stress-path measurement region should remain separate from the boundary selector:

- central radial core, e.g. `r_i <= 0.35 R`;
- away from caps, e.g. `0.35 H <= s_i <= 0.65 H`;
- excludes cap-platen particles and lateral membrane particles.

This prevents boundary artifacts from dominating `p'`, `q`, and pore-pressure summaries.

## Diagnostics

Required T3 diagnostics:

- lateral-selected count;
- top-cap false-positive count;
- bottom-cap false-positive count;
- edge-ring count;
- low-`f_i` interior defect count;
- mean and max inward radial acceleration;
- mean and max axial acceleration leakage;
- net force and COM acceleration;
- symmetry residual;
- selected radial roughness statistics.

## XML Design Sketch

Provisional controls:

```xml
<parameter key="ConfiningStressSelector" value="0" />
<parameter key="ConfiningStressCylinderAxis" value="0 0 1" />
<parameter key="ConfiningStressCylinderCenter" value="0 0 0" />
<parameter key="ConfiningStressCylinderRadius" value="0.025" />
<parameter key="ConfiningStressCylinderHeight" value="0.100" />
<parameter key="ConfiningStressCylinderRadialTolerance" value="auto" />
<parameter key="ConfiningStressCylinderCapMargin" value="auto" />
<parameter key="ConfiningStressUseFiSelector" value="0" />
<parameter key="ConfiningStressFiThreshold" value="0.70" />
```

`ConfiningStressSelector=0` should mean legacy behavior. A later mode can enable lateral-only cylinder selection.

## T2 Recommendation

Do not use geometry-only lateral selection as the final strict method. Use it first as a diagnostic and guardrail around Zhao's kernel-truncation mechanism. The strict route should require both geometric lateral classification and acceptable `f_i`/acceleration diagnostics.

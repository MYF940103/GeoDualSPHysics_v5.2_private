# T4n1 Staging Treatment Classification

This classification separates treatments that are supported by the references
from treatments that are useful diagnostics but should not be presented as
validated physics.

## Category A - Reference-Supported Workflow Elements

These can be part of the formal triaxial workflow if implemented and reported
carefully.

| Treatment | Status | Reason |
| --- | --- | --- |
| Initial hydrostatic effective stress | Supported | Zhao demonstrates immediate equilibrium when initial stress matches confinement; the drained/undrained SPH framework also relies on initialized stress states. |
| Damping during confinement equilibration | Supported | Zhao uses viscous damping when confinement is applied without matching initial stress; u-pw notes also report kinematic damping as a useful stabilizer. |
| Artificial viscosity with caution | Supported but risky | u-pw uses artificial viscosity in benchmarks, but warns about dissipation/error. |
| `f_i` near-boundary selector | Supported | Zhao gives kernel completeness index and empirical 3D threshold near `0.70`. |
| All-surface Zhao confinement for isotropic stage | Supported | Zhao's mechanism is all free-surface kernel truncation, not hand-separated lateral/cap force routes. |
| Smooth/fan-shaped cylinder layout | Supported | Zhao uses fan-shaped layouts to reduce boundary roughness/noise. |
| Staged confinement before axial loading | Supported as principle | Zhao and the drained/undrained SPH framework start from confined or initialized states before loading. |
| Large-deformation `l0/ln` rescaling | Supported as future work | Zhao proposes this to preserve confinement magnitude during deformation. |
| Corrected kernel gradients | Supported | u-pw notes use corrected gradients for key SPH operators. |

## Category B - Engineering Workflow

These can be used to build a stable workflow, but must be described as
implementation/staging choices rather than direct reference equations.

| Treatment | Status | Use |
| --- | --- | --- |
| Restart-based equilibrium | Engineering workflow | Consistent with starting from an equilibrated state, but GeoDualSPHysics restart fidelity must be validated. |
| Delayed feedback activation | Engineering workflow | Useful to isolate stages; not a literature boundary condition. |
| Staged all-surface -> lateral-only confinement | Engineering workflow | Matches the physical idea of isotropic pre-confinement followed by triaxial loading, but the selector switch itself is our implementation device. |
| Time-ramped selector transition | Engineering workflow | Can reduce target-set discontinuity, but has no direct Zhao/u-pw formula behind it. |
| Stronger damping only during Stage A | Engineering workflow | Literature supports damping for equilibration, but the exact timing/magnitude is code-specific. |
| CapConfiningStress diagnostic route | Engineering workflow/diagnostic | It helped identify missing axial support, but mixed discretizations were less hydrostatic than all-surface `f_i` confinement. |

## Category C - Diagnostic Only

These should not be used in final validation unless a physical derivation or
separate calibration study is completed.

| Treatment | Status | Reason |
| --- | --- | --- |
| Arbitrary feedback acceleration cap | Diagnostic only | It prevents blow-up but does not fix the continuum coupling. |
| Feedback scale below one without physical basis | Diagnostic only | T4e/T4f showed scale reduction helps numerically but changes coupling strength. |
| Pure limiter-based success criteria | Diagnostic only | A stable capped case is not a paper-faithful u-pw result. |
| Arbitrary selector smoothing used as final boundary condition | Diagnostic only | It solves a discontinuity we introduced; it is not a reference boundary law. |
| Broad parameter tuning of p0/ramp/feedback cap | Diagnostic only | Risks fitting the reduced cylinder rather than validating the formulation. |

## Classification Conclusion

The formal route should use Category A first: initial stress, damping,
all-surface `f_i` confinement, smooth layout, and corrected operators where
needed. Category B can be used to organize simulations and diagnose transitions,
but must be labeled as workflow engineering. Category C is useful only to
understand instability mechanisms and should not be used for validation claims.

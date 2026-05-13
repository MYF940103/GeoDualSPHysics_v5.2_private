# T2 Zhao Flexible Confinement Source Audit

## Scope

This audit compares the current branch's CPU `FlexibleConfiningStress` path with Zhao et al.'s flexible confined boundary condition. It is read-only: no source, XML, or simulation behavior is changed in T2.

## Current Interface

| Item | Location | Current behavior |
| --- | --- | --- |
| Storage | `source/JSph.h:268-281` | Stores `FlexibleConfiningStress`, `ConfiningStressP0`, ramp timing, target marker, mode, and diagnostics. |
| Function prototypes | `source/JSph.h:594-597` | Ramp helper, target helper, and diagnostic helpers. |
| Defaults | `source/JSph.cpp:257-262` | Disabled by default; `ConfiningStressP0=0`; target mk `-1`; mode `0`. |
| XML parsing | `source/JSph.cpp:979-990` | `FlexibleConfiningStress=0/1`; reads `ConfiningStressP0`, `ConfiningStressRampStart`, `ConfiningStressRampEnd`, `ConfiningStressTargetMk`, and `ConfiningStressMode`. |
| Validation | `source/JSph.cpp:1052-1058` | Rejects negative pressure/ramp values, invalid target mk, and GPU use. Warns if enabled with `p0=0`. |
| Logging | `source/JSph.cpp:2104-2111` | Prints mode and sign convention. Positive `ConfiningStressP0` is external compression. |
| Ramp helper | `source/JSph.cpp:3219-3229` | Linear ramp from `ConfiningStressRampStart` to `ConfiningStressRampEnd`; otherwise step load after start. |
| Target helper | `source/JSph.cpp:3235-3238` | Targets normal non-floating fluid/material particles; `-1` means all mkfluid values. |
| Diagnostics | `source/JSph.cpp:3243-3265` and `source/JSphCpu.cpp:1415-1443` | Tracks effective p0, target count, net force, total force magnitude, max acceleration, COM acceleration, and symmetry residual. |
| GPU path | `source/JSphGpu.cpp:1433` | Hard error if `FlexibleConfiningStress=1`. |

## CPU Momentum Coupling

The active CPU coupling is in `source/JSphCpu.cpp:1110-1225`.

The effective pressure is obtained once per interaction call:

```text
confp0d = GetFlexibleConfiningStressP0(TimeStep)
```

Then, for a target material particle `p1` interacting with target material neighbor `p2`, the acceleration receives:

```text
prsconf = massp2 * (confp0 + confp0) / (rho1 * rho2)
aceconf = prsconf * grad W_ij
acep1 += aceconf
```

This is directionally close to Zhao Eq. 51:

```text
a_i^conf = sum_j m_j * (sigma_c_i + sigma_c_j) / (rho_i rho_j) * grad_i W^R_ij
```

The current implementation does not write `ConfiningStressP0` into the material stress tensor. It is a mechanical pair contribution only.

## Kernel Gradient

Zhao Eq. 51 is written with the renormalized gradient `grad W^R_ij`. The current CPU implementation uses the same `frx/fry/frz` computed by the existing interaction loop:

```text
fac = fsph::GetKernel_Fac<tker>(CSP, rr2)
fr = fac * dr
```

Although `dengradcorr` is passed into `InteractionForcesFluid`, the confining-stress term does not use a renormalized or corrected gradient in the audited code path. This is a known gap relative to Zhao's formulation.

## Boundary Selection

Current behavior:

- `ConfiningStressTargetMk=-1` applies to all normal material particles.
- A nonnegative target mk can restrict by `mkfluid`.
- There is no kernel-completeness index.
- There is no near-boundary-only selector.
- There is no lateral-cylinder selector.
- There is no top-cap or bottom-cap exclusion except what can be approximated through `mkfluid` tagging.

Zhao's large-deformation treatment recommends identifying near-boundary particles by:

```text
f_i = sum_j (m_j / rho_j) W_ij
```

with an empirical 3D boundary-layer threshold of approximately `f_i <= 0.70`. That index is not currently computed for confinement.

## Lateral Triaxial Gap

Strict triaxial confinement needs the flexible pressure only on the cylindrical lateral membrane, while top and bottom platens/caps are controlled by axial loading and cap boundary conditions. The current `FlexibleConfiningStress` target logic can distinguish mk values but cannot geometrically separate:

- lateral free surface;
- top cap;
- bottom cap;
- edge/ring regions near cap-lateral intersections.

This is the biggest practical gap for moving from T1 fixed-side smoke to strict triaxial confinement.

## GPU Status

GPU behavior is currently correct for this branch: enabling `FlexibleConfiningStress=1` on GPU hard-errors instead of silently omitting the mechanical boundary. T2 does not change this. GPU should remain deferred until CPU confinement diagnostics pass.

## Gap Summary Against Zhao Eq. 51

| Requirement | Current status |
| --- | --- |
| Isotropic confining pair term | Present on CPU. |
| Positive compression sign convention | Present and documented. |
| Renormalized kernel gradient `grad W^R` | Not used in current confining term. |
| Kernel-completeness boundary index `f_i` | Missing. |
| Near-boundary-only application | Missing. |
| Lateral-only cylindrical selection | Missing. |
| Top/bottom cap exclusion | Missing except by manual mk design. |
| Large-deformation `l0/ln` rescaling | Missing. |
| Initial hydrostatic stress initialization | Missing for this interface. |
| GPU support | Intentionally unsupported / hard error. |

## T2 Conclusion

The current `FlexibleConfiningStress` path is a useful CPU starting point and is conceptually aligned with Zhao's confining pressure generator. It is not yet a strict triaxial flexible membrane implementation. The next source step should add diagnostics first: compute `f_i`, classify lateral/cap candidates, and compare confining acceleration projections before using those diagnostics to alter behavior.

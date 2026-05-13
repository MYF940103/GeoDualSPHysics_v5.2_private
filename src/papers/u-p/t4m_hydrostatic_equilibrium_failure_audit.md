# T4m Hydrostatic Equilibrium Failure Audit

## Purpose

T4l added explicit top/bottom cap support and improved the center-core pressure
response, but the state was still not hydrostatic and delayed full feedback
remained unstable. This audit explains why the lateral-plus-cap construction is
not yet equivalent to Zhao-style isotropic confinement.

## T4l Evidence

The T4l feedback-off comparison was:

| Case | final center pore pressure | final mean pore pressure | final `p'` proxy | final `q` proxy |
| --- | ---: | ---: | ---: | ---: |
| lateral only | `-10993 Pa` | `-14223 Pa` | `17.1 Pa` | `51.5 Pa` |
| lateral + cap support | `-62.9 Pa` | `-4494 Pa` | `38.9 Pa` | `53.5 Pa` |

Cap support solved a real missing support direction, but it did not reduce the
deviatoric stress. The residual `q` stayed near `50 Pa`, which is comparable to
the intended confinement magnitude.

## Region Source Of Residual q

The T4l lateral-plus-cap reference final frame in T4m gives:

| Region | `p'` proxy | `q` proxy | mean pore pressure |
| --- | ---: | ---: | ---: |
| interior | `51.9 Pa` | `77.9 Pa` | `-57 Pa` |
| lateral | `45.1 Pa` | `36.1 Pa` | `-3946 Pa` |
| top cap | `106.7 Pa` | `99.6 Pa` | `1355 Pa` |
| bottom cap | `106.7 Pa` | `99.6 Pa` | `1355 Pa` |
| edge | `-1.15 Pa` | `55.5 Pa` | `-9831 Pa` |

The largest mismatch is in the cap and edge regions. The explicit cap support
over-compresses the cap layers relative to the lateral and edge zones, while
the edge ring is skipped by cap support to avoid double-counting the lateral
force. This leaves a discontinuity between the lateral selected force and the
cap force.

## Cap/Lateral Discretization Mismatch

`FlexibleConfiningStress` is a pairwise isotropic stress-like term. It uses the
same kernel support truncation mechanism as the Zhao confinement idea. In
contrast, `CapConfiningStressMode=0` is an external integrated force
distributed over selected cap mass:

```text
F_cap = p0 * pi * R^2
```

Those two force routes do not have the same discrete support, smoothing, or
edge behavior. Even though both use the same target pressure magnitude, they
can generate a non-isotropic transition at the cap/lateral edge.

## Edge Ring Role

The T4l edge ring is intentionally skipped by cap support and is not selected by
lateral confinement when the lateral selector is active. The final edge region
has poor `p'` and high `q`, which is consistent with an unsupported transition
zone. This is not a code crash; it is a discrete traction compatibility problem.

## Feedback Failure Link

Delayed full feedback fails after this residual non-hydrostatic state has
formed. The feedback-on T4l case reaches order `1e12 Pa/s` `PorePressRate`.
That instability is likely amplified by residual `q`, remaining negative pore
pressure, and the uneven cap/edge/lateral support field.

## Working Hypothesis

T4l is better than T4k but still not the right isotropic confinement gate. A
more faithful Zhao first step is to let the flexible confinement term operate on
all low-`f_i` free surfaces, including lateral, cap, and edge regions, rather
than combining a lateral pair term with a separate cap force.

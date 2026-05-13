# T4c Selected-Confinement Stabilization Design

## Objective

The T4/T4b reduced triaxial smokes showed selected flexible confinement with
zero cap leakage, but the pore-pressure response developed large dynamic
excursions. T4c tests XML-level stabilization before any source-level magnitude
normalization.

## Route 1: Confinement Magnitude Normalization

This route would normalize the effective acceleration produced by
`ConfiningStressGradientMode=1`, so that the renormalized-gradient path has the
same mean lateral inward acceleration as the raw-gradient path for the same
`ConfiningStressP0`.

Pros:
- Directly addresses the T4b observation that renormalization roughly doubles
  lateral acceleration.
- Preserves direction and selector behavior.

Cons:
- Requires a source-level normalization rule.
- Could become a tuned correction unless tied to a clear Zhao-style
  completeness or surface measure.
- Does not address the T4c finding that raw-gradient confinement also reverses
  pressure before axial loading.

Decision: defer. T4c first tests schedule-level stabilization.

## Route 2: Staged Confinement Then Axial Loading

This route separates the loading path into:

1. Stage A: ramp selected lateral confinement to target pressure.
2. Stage B: hold confinement briefly.
3. Stage C: start axial AccInput compression.

The T4c variants use:

| Item | T4/T4b | T4c staged |
| --- | ---: | ---: |
| confinement ramp end | 0.0005 s | 0.0010 s |
| axial loading start | 0.0010 s | 0.0015 s |
| retained short window | 0.0015 s | 0.0018 s |

This avoids simultaneous ramp shocks and makes it possible to identify whether
pressure reversal begins before axial compression.

Decision: implemented in T4c.

## Route 3: Gentler Axial Loading Ramp

This route lowers the axial AccInput magnitude during the retained short window:

- staged raw: reaches `-0.10 m/s2` by `0.0018 s`;
- staged gentle: reaches `-0.04 m/s2` by `0.0018 s`.

Decision: implemented as a diagnostic comparison, not a parameter sweep.

## T4c Variants

| Variant | Gradient mode | Confinement ramp | Axial schedule |
| --- | ---: | ---: | --- |
| raw staged | 0 | 0 to 50 Pa by 0.0010 s | delayed to 0.0015 s, reaches -0.10 m/s2 |
| renormalized staged | 1 | same | same |
| raw staged gentle | 0 | same | delayed to 0.0015 s, reaches -0.04 m/s2 |

## Interpretation Rule

If reversal occurs before `0.0015 s`, axial AccInput is not the primary
trigger. If raw staged is much more stable than renormalized staged,
renormalized magnitude is an amplifier. If raw staged and raw staged gentle are
nearly identical, gentler axial loading is not yet acting on the main blocker.

## Recommended Next Design Step

T4c should not jump to DP or MCC unless the linear-elastic selected-confinement
response is smooth. If T4c fails, the next step should target confinement-stage
stability directly:

- either add a source-level confinement magnitude normalization/limiter;
- or implement an explicit staged confinement equilibration route with stronger
  damping control and delayed or disabled pore-pressure Shepard during the
  confinement-only stage.

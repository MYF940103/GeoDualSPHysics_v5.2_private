# T4d Confinement Equilibration Report

## Purpose

T4d tests whether the T4c pressure reversal is caused by axial AccInput or by
selected flexible-confinement equilibration itself. All T4d simulations are
CPU-only confinement-only cases. No source was modified.

## Cases

The retained cases are under:

`examples/u-pw/04_Undrained_Triaxial/experiments/T4d_ConfinementEquilibration/`

| Case | Feedback | p0 | Ramp | Damping | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| raw feedback on | 1 | 50 Pa | 0.001 s | 0.05 | `code=0`, `excluded=0` |
| raw feedback off | 0 | 50 Pa | 0.001 s | 0.05 | `code=0`, `excluded=0` |
| raw low p0 | 1 | 12.5 Pa | 0.001 s | 0.05 | `code=0`, `excluded=0` |
| raw long ramp + damping | 1 | 50 Pa | 0.0018 s | 0.20 | `code=0`, `excluded=0` |

All cases keep `SoilConstitutiveModel=0` and finish with `Kplastic=0`.

## Main Metrics

| Case | Reversal | Max PorePressRate | Max velocity | DtMin adjustments | Cap leakage |
| --- | ---: | ---: | ---: | ---: | ---: |
| feedback on | 0.001404 s | 3.12e12 Pa/s | 215 m/s | 85 | 0 |
| feedback off | none | 2.11e7 Pa/s | 7.57e-4 m/s | 0 | 0 |
| low p0 | 0.001504 s | 2.66e12 Pa/s | 131 m/s | 41 | 0 |
| long ramp + damping | 0.001588 s | 2.70e12 Pa/s | 196 m/s | 62 | 0 |

## Answers

1. **Does reversal appear in confinement-only?**  
   Yes. The target-p0 raw-gradient feedback-on confinement-only case reverses
   at `0.001404 s`, with no axial AccInput in the XML.

2. **Does feedback off improve the response?**  
   Yes, decisively. With the same confinement force and selector, feedback off
   removes reversal over the retained window, removes DtMin adjustments, and
   reduces max `PorePressRate` by roughly five orders of magnitude.

3. **Does lower p0 improve the response?**  
   Only partially. The lateral acceleration scales down as expected, and the
   all-particle reversal is delayed to `0.001504 s`, but the center-core
   reversal still appears near `0.001407 s` and the pressure-rate excursion
   remains `2.66e12 Pa/s`.

4. **Does longer ramp / stronger damping help?**  
   Only modestly. The all-particle reversal is delayed to `0.001588 s`, but the
   center core still reverses near `0.001405 s`. The maximum pressure-rate
   artifact remains order `1e12 Pa/s`.

5. **Is effective confinement magnitude too strong?**  
   The selected raw confinement is strong enough to trigger the unstable
   feedback loop, but the force magnitude alone does not explain the failure.
   A 75% p0 reduction still fails when feedback is active.

6. **Is source-level magnitude normalization needed?**  
   Not as the immediate next patch. T4d suggests a feedback/equilibration
   protocol is the primary blocker. Magnitude normalization should remain a
   designed, opt-in follow-up if staged feedback still fails.

7. **Was normalization implemented?**  
   No. This stage intentionally stayed source-free because the feedback-on/off
   decomposition gave a cleaner diagnosis than a force rescaling patch.

8. **Is there a stable confinement-only equilibration route?**  
   A mechanically stable confinement-only route exists with
   `PorePressureFeedback=0`, but the intended coupled feedback-on route is not
   stable yet.

9. **Can axial loading be reintroduced?**  
   Not yet for the intended coupled route. Axial loading should wait until a
   target-p0 confinement stage can equilibrate without reversal and DtMin
   collapse.

10. **Should T5 DP or T6 MCC start?**  
    No. The linear-elastic selected-confinement response is still unstable
    under active u-pw feedback, so DP/MCC would only add constitutive
    complexity on top of an unresolved loading/boundary problem.

## Recommendation

Proceed to T4e as a staged confinement-equilibration task:

1. ramp selected lateral confinement with pore-pressure feedback disabled or
   delayed;
2. damp until velocity, `DivVel`, and PorePressRate are small;
3. re-enable feedback and check for an immediate pressure-rate burst;
4. only then reintroduce axial loading.

If that still fails, implement the opt-in source-level confinement magnitude
normalization described in the T4d design note.

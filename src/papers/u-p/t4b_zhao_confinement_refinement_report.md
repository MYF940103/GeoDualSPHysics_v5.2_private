# T4b Zhao Confinement Refinement Report

## Objective

T4b tests whether a Zhao-style renormalized kernel gradient in the flexible
confinement pair term can reduce the T4 pressure-rate excursions and pressure
reversal while preserving the successful T3/T4 lateral selector behavior.

This is still a reduced CPU smoke stage. It is not DP validation, not MCC, not
full triaxial reproduction, and not GPU work.

## Source Change

T4b adds:

```text
ConfiningStressGradientMode
  0 = raw gradient, default legacy behavior
  1 = CPU renormalized/corrected gradient for FlexibleConfiningStress only
```

Mode `1` builds a local first-order correction matrix from target material
neighbours and applies `L_i^{-1} grad W_ij` only to the flexible confinement
pair term. It does not affect normal stress divergence, PR pore-pressure
operators, AccInput, or Cryer boundary code. If the local matrix is invalid,
the particle falls back to the raw gradient and reports the fallback count.

Default raw behavior is preserved.

## Build

| Build | Result |
| --- | --- |
| CPU Release | passed |
| GPU Release | passed compile-only |

No GPU simulation was run. `ConfiningStressGradientMode=1` and
`FlexibleConfiningStress=1` remain GPU-unsupported and hard-error on GPU.

## Cases

Retained package:

`examples/u-pw/04_Undrained_Triaxial/experiments/T4b_RenormalizedConfinement/`

| Case | Purpose |
| --- | --- |
| T4 raw reference | Existing T4 selected-confinement raw-gradient metrics reused as baseline. |
| `CaseT4b_RenormConfinement` | Same loading as T4, with `ConfiningStressGradientMode=1`. |
| `CaseT4b_RenormGentleLoading` | Renormalized gradient with smoother/lower axial AccInput. |

## Run Health

| Case | code | excluded | steps | DTmin adjusted | final `Kplastic` |
| --- | ---: | ---: | ---: | ---: | ---: |
| T4 raw reference | 0 | 0 | 14 | 0 | 0 |
| Renormalized, T4 loading | 0 | 0 | 22 | 9 | 0 |
| Renormalized, gentle loading | 0 | 0 | 21 | 7 | 0 |

Both T4b CPU Release smokes completed and PartVTK completed.

## Confinement Diagnostics

| Metric | T4 raw | Renormalized |
| --- | ---: | ---: |
| active targets | 112 | 112 |
| cap axial leakage | 0 | 0 |
| lateral inward acceleration mean | ~1.872 m/s2 | ~3.759 m/s2 |
| gradient corrected / fallback | n/a | 112 / 0 |
| correction determinant range | n/a | ~0.1169 to 0.1952 |

The selector still works: cap leakage remains zero and the active target count
is unchanged. The renormalized gradient is numerically available with no
fallbacks. However, on this reduced coarse cylinder it approximately doubles
the lateral inward acceleration.

## Stability Metrics

| Case | Final mean pore pressure | Final mean `PorePressRate` | MaxAbs `PorePressRate` | pressure reversal | final velocity max |
| --- | ---: | ---: | ---: | ---: | ---: |
| T4 raw reference | `-3.82e6 Pa` | `-8.89e10 Pa/s` | not retained from raw output | yes | `38.16 m/s` |
| Renormalized, T4 loading | `-1.46e7 Pa` | `-3.58e11 Pa/s` | `2.01e12 Pa/s` | yes | `87.68 m/s` |
| Renormalized, gentle loading | `-1.28e7 Pa` | `-3.38e11 Pa/s` | `1.99e12 Pa/s` | yes | `85.34 m/s` |

The renormalized-gradient confinement does not reduce the T4 pressure-rate
artifact. It makes the short-window instability worse in this reduced setup.
Gentler axial loading slightly improves the renormalized result, but not enough
to remove pressure reversal, DtMin adjustments, or large pressure-rate
excursions.

## Measurement-Region Outcome

Final center-core pore pressures remain strongly negative in both T4b variants.
The `full_excluding_caps_edges` region is even more negative than the center
regions, showing that measurement-region sensitivity remains significant.

The proxy `p'-q` curves are still only diagnostic. They should not be used as a
strict triaxial stress path until output conventions and loading stability are
fixed.

## Answers Required by T4b

1. `ConfiningStressGradientMode` is implemented.
2. The renormalized gradient is available on CPU and reported fallback-free in
   the T4b smokes.
3. Default raw behavior is preserved by `ConfiningStressGradientMode=0`.
4. Both CPU selected-confinement smokes completed with `code=0`, `excluded=0`.
5. Cap leakage remains zero.
6. Lateral confinement remains coherent but is too strong after the correction
   in this reduced cylinder.
7. `PorePressRate` excursions are not reduced; they are worse than T4.
8. Pore pressure versus axial strain is not smoother enough for validation.
9. Gentler loading helps only marginally and does not fix pressure reversal.
10. `p'-q` remains a proxy.
11. T4c output enhancement is still needed for strict stress-path validation,
    but the more urgent blocker is confinement/loading stability.
12. Recommended next step: do not proceed to T5 DP or T6 MCC yet. First do a
    smaller T4c/T4d stabilization task: cap/limit the renormalized confinement
    magnitude or introduce a staged confinement equilibration/loading ramp, then
    add minimal output enhancements once the reduced linear-elastic response is
    smooth.
13. GPU remains deferred.

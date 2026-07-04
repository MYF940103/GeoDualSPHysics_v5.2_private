# Self-weight Scenario2 CteB/Cs0 diagnostic conclusion

Date: 2026-06-29

## Purpose

This diagnostic checked whether the late-time slow dissipation in the restarted
SelfWeightConsolidation Scenario2 was mainly caused by the current soil
constant logic, where `ConfigConstantsSoil()` computes both:

- `Cs0 = sqrt((K + 4G/3) / rho0) ~= 35.806 m/s`
- `CteB = Cs0^2 * rho0 / gamma ~= 3.846e5 Pa`

The alternative tested value was the historical/XML equation-of-state value:

- `Cs0 = 62.33 m/s`
- `CteB ~= 1.165e6 Pa`

## Tests completed

1. Late-window restart diagnostic near `Tv=0.9`:
   - GPU release and CPU release were both run from Scenario2 `Part_0180`.
   - The temporary code preserved XML `Cs0/CteB`.
   - Result: GPU and CPU agreed almost exactly.
   - Result: larger `Cs0/CteB` did not restore the theoretical late-time
     dissipation rate.

2. Full-history diagnostic:
   - Stage1 was rerun with XML `speedsound=62.33 auto=false`.
   - Scenario2 inherited Stage1 `Part_0060` and was run to `Tv ~= 1`.
   - Solver `Run.out` confirmed `CteB=1165509`, `Cs0=62.3299988`.
   - No excluded particles and no `DtMin` adjustments occurred.
   - Result: full-history large `CteB` remained nearly identical to the current
     restarted small-`CteB` run.

## Key quantitative comparison

Bottom excess pore pressure in kPa:

| Tv | Theory | Old root analytical-init run | Current restart small CteB | Restart full-history large CteB |
|---:|---:|---:|---:|---:|
| 0.7 | 1.5488 | 1.6340 | 1.7398 | 1.7392 |
| 0.9 | 0.9455 | 0.9772 | 1.0913 | 1.0923 |
| 1.0 | 0.7388 | 0.7947 | 1.0818 | 1.0808 |

## Interpretation

The old root result was closer to theory mainly because it used the analytical
self-weight initial condition, not because the larger XML `CteB` by itself
improved the late-time dissipation.

Historical source inspection showed:

- In commit `a407fbd`, `ConfigConstantsSoil()` recomputed `Cs0` from the soil
  constrained modulus but did not recompute `CteB`; this left the XML/GenCase
  equation-of-state `B` value in place.
- In commit `2ba378f`, `CteB` was also recomputed from the soil-constrained
  `Cs0`, producing the current internally consistent soil-parameter logic.

The diagnostic runs support returning to the current internally consistent
soil-parameter logic and focusing next on the restart initial state, damping,
and mid-time oscillation source rather than forcing the historical XML `CteB`.

## Cleanup note

The heavy `xmlcs62`, `fullhist_xmlcs62`, and `cte_probe` run outputs, figures,
logs, and temporary XML/BAT launch files were removed after this note was saved.
The retained evidence is this conclusion note; baseline/freeslip/damping
diagnostic data are kept for the next damping sweep.

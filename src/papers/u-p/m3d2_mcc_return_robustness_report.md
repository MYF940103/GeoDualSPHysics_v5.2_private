# M3d2 MCC Return Robustness Report

## Executive Summary

M3d2 confirms that the M3d mild-yield MCC issue is a local return robustness
problem, not an SPH run failure. All CPU Release diagnostic cases completed
with `code=0`, `excluded=0`, and `DtMin=0`. The final baseline and tight-return
cases retain 8 `ReturnStatus=-3` particles. Slower loading removes final
failures, but not all intermediate return failures.

The clean next step is M3d3 constitutive substepping plus admissibility guards.
M3e package consolidation should wait unless it is explicitly labeled
diagnostic-only.

## Case Results

| Case | code | excluded | DtMin | Final status | Final failed | Final PorePress mean | Final reaction avg |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| baseline | 0 | 0 | 0 | `-3:8|0:2|1:397` | 8 | `-2.252e5 Pa` | `0.286 N` |
| slower half velocity | 0 | 0 | 0 | `0:8|1:399` | 0 | `-2.771e5 Pa` | `0.255 N` |
| early stop | 0 | 0 | 0 | `1:407` | 0 | `-5.512e4 Pa` | `0.277 N` |
| tight return | 0 | 0 | 0 | `-3:8|0:2|1:397` | 8 | `-2.252e5 Pa` | `0.286 N` |

## Failed Particle Locations

Final baseline `-3` particles are localized in two symmetric bottom-adjacent
rings:

- 4 particles in the interior at `z≈0.01998 m`, `r≈0.01414 m`;
- 4 particles in the bottom cap zone at `z≈0.00998 m`, `r≈0.01000 m`.

Their final `p'` values remain positive (`~38-40 Pa`), so the final persistent
`-3` failures are not caused by direct tension cutoff. Earlier transient
`ReturnStatus=-1` events are much broader and do involve low/negative `p'`
states during startup.

## Local Or Global?

The failure is local:

- only 8 of 407 particles fail at the baseline final frame;
- the failed particles are spatially symmetric and bottom-adjacent;
- most yielded particles converge with small residual;
- global run diagnostics remain stable (`excluded=0`, `DtMin=0`, bounded
  velocity and reaction).

It is not yet clean enough for MCC validation because the failed local returns
carry large raw yield residuals (`~4.49e3` max).

## Diagnostic Variant Interpretation

### Slower Loading

Half top-platen velocity eliminates final `-3` failures and lowers final
PorePressRate/DivVel/velocity:

- final status changes from `-3:8|0:2|1:397` to `0:8|1:399`;
- final PorePressRate maxAbs drops from `6.33e7` to `2.91e7 Pa/s`;
- final velocity max drops from `5.52e-3` to `2.79e-3 m/s`.

However, intermediate `-3` episodes still occur. Slower loading helps, but it
is not a full constitutive robustness solution.

### Shorter Time Window

The early-stop case ends cleanly at `0.006 s` with `1:407`. This shows the
final M3d failures emerge after additional accumulated plastic deformation,
not immediately from the parser/state initialization.

### Tighter Return Tolerance / Higher Max Iter

`MccReturnTolerance=1e-10` and `MccReturnMaxIter=80` reproduce the baseline
final status exactly: `-3:8|0:2|1:397`. The issue is not just an iteration-cap
or loose-tolerance problem.

## Curves And Diagnostics

The mild MCC reduced curves can still be used diagnostically if clearly marked:

- pairwise reaction is bounded;
- p'-q and axial stress-strain remain readable;
- `pc`, void ratio, and plastic strain evolve continuously for converged
  particles;
- pore pressure remains finite but strongly negative because this remains a
  feedback-off reduced route.

They should not be used as clean MCC validation curves until local return
failures are removed or explicitly recovered.

## Recommendation

Proceed to M3d3 before M3e:

1. Add opt-in local MCC substepping.
2. Add admissibility guards in Newton/line search.
3. Add explicit recovered-failure diagnostics if fallback is used.
4. Re-run the M3d2 baseline and half-velocity cases.

Full pore-pressure feedback and GPU remain deferred.


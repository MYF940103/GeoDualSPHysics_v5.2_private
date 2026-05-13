# T5b DP Feedback-Off Platen Refinement Design

## Objective

T5b refines the reduced platen-based triaxial workflow after T4t added a
CPU pairwise platen reaction diagnostic. The goal is to compare an elastic
reference, a high-strength Drucker-Prager skeleton, and a mild-yield
Drucker-Prager skeleton using the same explicit platen and lateral confinement
setup.

This is still a reduced benchmark. It is not a full paper reproduction.

## Why Feedback Remains Off

Full `PorePressureFeedback=1` remains deferred because T4e-T4h showed that
full feedback can destabilize confinement-only and platen cases before a
validated feedback formulation/staging route exists. T5b therefore keeps:

```xml
<parameter key="PorePressureFeedback" value="0" />
```

The PR pressure update and pore-pressure output remain active. This lets the
case track bounded pore-pressure response while isolating skeleton/platen
mechanics.

## Why DP Before MCC

The current code has an existing Drucker-Prager skeleton path and `Kplastic`
output. MCC remains a larger constitutive implementation and validation task.
T5b uses DP because it can verify plastic activation and stress-path plumbing
without introducing a new model.

## Why Pairwise Platen Reaction

T4t implemented `PlatenReactionMode=0`, a CPU pairwise fluid-bound interaction
accumulator for explicit top/bottom `mkbound` platens. It is closer to axial
reaction than the old specimen-stress proxy:

```text
Fz_proxy = -mean(Sigma_zz)_specimen * pi * R^2
```

The diagnostic still excludes prescribed-motion actuator/constraint force, so
T5b reports it as a pairwise interaction reaction rather than a complete
actuator reaction.

## Cases

| Case | Purpose |
| --- | --- |
| elastic reference | Linear-elastic baseline for the same platen/confinement route. |
| DP high strength | Elastic-like DP reference; should match the elastic response with `Kplastic=0`. |
| DP mild yield | Short plastic activation diagnostic; should show nonzero `Kplastic` without destabilizing. |

DP parameters:

- high strength: `phi=33 deg`, `coh=10000 Pa`, `dlt=0`;
- mild yield: `phi=30 deg`, `coh=50 Pa`, `dlt=0`.

## Common Setup

- explicit top moving platen, `mkbound=1`, `v_z=-0.005 m/s`;
- fixed bottom platen, `mkbound=2`;
- specimen `mkfluid=0`;
- selected lateral `FlexibleConfiningStress`;
- `ConfiningStressUseFiSelector=1`;
- `ConfiningStressUseLateralSelector=1`;
- `SavePlatenReactionDiagnostics=1`;
- CPU Release only.

## Stop Conditions

T5b should stop at short reduced runs. It should not continue if:

- `excluded > 0`;
- `DtMin` bursts appear;
- top prescribed motion or bottom fixed condition fails;
- mild-yield plasticity causes velocity blow-up;
- pairwise reaction diagnostics are missing.

## Known Limits

- no full pore-pressure feedback;
- no MCC;
- no strict paper reproduction;
- no true actuator reaction;
- no GPU simulation.


# T5c DP Feedback-Off Extended Response Report

## Setup

T5c extends the T5b explicit-platen DP workflow from `TimeMax=0.006 s` to `0.018 s`. Both runs are CPU Release, feedback-off, and use:

- top moving platen `mkbound=1`, prescribed `v_z=-0.005 m/s`;
- bottom fixed platen `mkbound=2`;
- selected lateral `FlexibleConfiningStress`;
- `PorePressureFeedback=0`;
- `HydraulicElevationSource=0`;
- pairwise platen reaction diagnostics enabled;
- no MCC, no GPU simulation, and no full-feedback coupling.

The retained cases are:

| Case | DP parameters | Role |
| --- | --- | --- |
| `CaseT5c_DPHighStrength_ExtendedFeedbackOff` | `phi=33 deg`, `coh=10000 Pa`, `dlt=0` | elastic-like DP reference |
| `CaseT5c_DPMildYield_ExtendedFeedbackOff` | `phi=30 deg`, `coh=50 Pa`, `dlt=0` | main mild-yield extended response |

## Run Status

| Case | code | excluded | DtMin adjustments | final top displacement | bottom displacement |
| --- | ---: | ---: | ---: | ---: | ---: |
| DP high strength | 0 | 0 | 0 | `-9.00e-5 m` | `0` |
| DP mild yield | 0 | 0 | 0 | `-9.00e-5 m` | `0` |

The prescribed top displacement matches `v_z=-0.005 m/s` over `0.018 s`. The bottom platen remains fixed.

## Plasticity

| Case | final `Kplastic_max` | final `Kplastic_mean` | plastic count | plastic fraction |
| --- | ---: | ---: | ---: | ---: |
| DP high strength | `0` | `0` | `0/407` | `0` |
| DP mild yield | `1.462e-3` | `4.529e-4` | `407/407` | `1.0` |

The mild-yield run activates plasticity after the early loading window and the retained output shows monotonic growth of `Kplastic_max` at the saved frames. The maximum observed saved-frame growth rate is about `0.127 s^-1`, with no negative saved-frame jumps.

## Reaction And Stress Proxies

The pairwise reaction diagnostic remains available. It is still a specimen-platen pairwise interaction reaction, not a prescribed-motion actuator reaction.

| Case | final pairwise reaction avg | final `Fz_proxy` | pairwise / proxy | final force-balance error |
| --- | ---: | ---: | ---: | ---: |
| DP high strength | `3.2740 N` | `3.1148 N` | `1.051` | `0.0507` |
| DP mild yield | `0.4335 N` | `0.4031 N` | `1.075` | `0.00533` |

The mild-yield reaction remains especially well balanced at the final frame. The high-strength reference is stable but stiffer and shows larger reaction oscillation than the mild-yield case.

## Stress Path And Pore Pressure

| Case | final `p'` proxy | final `q` proxy | final mean PorePress | final maxAbs PorePressRate |
| --- | ---: | ---: | ---: | ---: |
| DP high strength | `385.80 Pa` | `1073.74 Pa` | `1.115e5 Pa` | `1.52e7 Pa/s` |
| DP mild yield | `62.23 Pa` | `120.51 Pa` | `-3.525e4 Pa` | `1.44e7 Pa/s` |

The longer window makes the difference between elastic-like and mild-yield DP response clearer. The high-strength reference keeps accumulating high axial stress and pore pressure, while the mild-yield case sheds deviatoric stress through plastic response. Pore pressure remains bounded in both cases; the mild-yield final mean is negative, so this remains a reduced feedback-off diagnostic rather than a validated undrained triaxial prediction.

The p'-q and reaction-based axial stress-strain curves are more complete than T5b because the axial platen displacement is three times larger. They remain specimen/reaction proxies, not strict validation quantities.

## Stability

| Case | max velocity | max PorePressRate | max DivVel | cap leakage | lateral targets |
| --- | ---: | ---: | ---: | ---: | ---: |
| DP high strength | `5.87e-3 m/s` | `4.02e7 Pa/s` | `6.03e-2 1/s` | `0` | `112` |
| DP mild yield | `5.37e-3 m/s` | `5.14e7 Pa/s` | `7.73e-2 1/s` | `0` | `112` |

No excluded particles, no DtMin burst, no velocity blow-up, and no lateral confinement leakage were observed in the retained runs.

## Decision

T5c passes as a slightly longer DP feedback-off reduced platen response. It supports moving to T5d for DP measurement/reporting consolidation. MCC implementation planning can begin at the design level, but MCC implementation should still wait until the DP reporting decisions and full-feedback deferral are explicitly tracked.

Full PorePressureFeedback and GPU triaxial validation remain deferred.

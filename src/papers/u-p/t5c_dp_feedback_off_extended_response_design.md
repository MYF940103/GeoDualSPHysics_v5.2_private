# T5c DP Feedback-Off Extended Response Design

## Purpose

T5c extends the validated T5b mild-yield Drucker-Prager platen workflow to a slightly longer axial-compression window. The goal is not parameter sensitivity or paper reproduction. The goal is to check whether the reduced feedback-off DP triaxial route remains numerically stable as plastic strain, platen reaction, p'-q proxy, and pore-pressure response continue to evolve.

## Scope

T5c keeps the T5b mechanics:

- explicit top/bottom platens;
- top platen prescribed velocity;
- bottom platen fixed;
- lateral FlexibleConfiningStress with f_i and lateral selectors;
- CPU Release only;
- PorePressureFeedback=0;
- PR pore-pressure update still active;
- pairwise platen reaction diagnostic enabled;
- no MCC, no full feedback, no GPU simulation.

## Cases

Two CPU Release cases are used.

| Case | SoilConstitutiveModel | DP parameters | Role |
| --- | --- | --- | --- |
| `CaseT5c_DPHighStrength_ExtendedFeedbackOff` | 1 | phi=33 deg, coh=10000 Pa, dlt=0 | Optional elastic-like DP reference over the longer window |
| `CaseT5c_DPMildYield_ExtendedFeedbackOff` | 1 | phi=30 deg, coh=50 Pa, dlt=0 | Main extended mild-yield DP response |

`TimeMax` is increased from the T5b value of 0.006 s to 0.018 s, with `TimeOut=0.0005 s`.

## Why Only Extend Mild-Yield DP

T5b already showed that the elastic and high-strength DP cases are effectively identical over the short window, with Kplastic=0. T5c therefore focuses on the mild-yield case where plasticity actually activates. The high-strength DP case is kept as a low-cost reference to confirm the longer window does not introduce elastic-like numerical drift.

## Why No Parameter Sensitivity

The current objective is a stability and interpretability check for one already validated mild-yield DP setting. Broad friction/cohesion sweeps would mix constitutive calibration with workflow validation, so they are deferred until the reaction, measurement, and stress-path pipeline is stable.

## Why Feedback Remains Off

The T4e-T4j sequence showed that full PorePressureFeedback can destabilize selected-confinement triaxial cases even before axial loading. T5c therefore keeps `PorePressureFeedback=0` and treats the pore-pressure output as PR pressure response without momentum feedback. This preserves a stable reduced DP workflow while full-feedback coupling remains deferred.

## Why MCC Remains Deferred

The current route is still a reduced Drucker-Prager baseline with pairwise interaction reaction rather than full actuator reaction, and with feedback off. MCC should not be introduced until this DP baseline is stable over a longer window and the reporting pipeline is consolidated.

## Stability Metrics

The extended run is evaluated using:

- `code`, `excluded`, and `DtMin` adjustment count;
- top platen displacement and velocity;
- bottom platen displacement;
- lateral confinement active target count and cap leakage;
- pairwise top/bottom reaction and reaction/Fz_proxy ratio;
- specimen-only p' and q proxies;
- reaction-based axial stress vs axial strain;
- PorePress, ExcessPorePress, PorePressRate, and DivVel proxies;
- Kplastic max, mean, nonzero particle count, plastic fraction, and growth rate;
- velocity maximum.

## No-Go Criteria

T5c should stop the DP progression if any of the following appear:

- `excluded > 0`;
- a DtMin burst;
- velocity blow-up;
- pore-pressure runaway;
- nonphysical Kplastic jumps;
- reaction-force oscillation that dominates the stress-strain curve;
- loss of prescribed top-platen motion or bottom fixed support;
- lateral confinement cap leakage.

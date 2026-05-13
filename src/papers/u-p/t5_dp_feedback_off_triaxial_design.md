# T5 DP Feedback-Off Triaxial Design

## Objective

T5 moves the reduced explicit-platen triaxial workflow from a linear-elastic
skeleton to a Drucker-Prager skeleton while keeping the hydromechanical
feedback loop disabled. The target is a controlled CPU baseline that verifies
the existing DP return-mapping path, `Kplastic` output, specimen-only stress
proxies, and pore-pressure PR update under prescribed platen compression.

This is not a full paper reproduction, not a Modified Cam Clay validation, and
not a strict triaxial stress-path validation.

## Why DP Before MCC

DP is already implemented in the current source and is selected by
`SoilConstitutiveModel=1`. It can exercise the existing elastoplastic stress
update and `Kplastic` accumulation without introducing a new constitutive law.

MCC remains deferred because:

- the explicit platen route is still reduced;
- true platen reaction is not available yet;
- full pore-pressure feedback remains unstable in previous T4 gates;
- a strict paper-level triaxial comparison needs more complete stress/reaction
  diagnostics.

## Why Feedback Remains Off

T4e-T4j showed that full `PorePressureFeedback=1` destabilizes selected
confinement and platen-related reduced tests. T5 therefore keeps:

```xml
<parameter key="PorePressureFeedback" value="0" />
```

The PR pore-pressure update still runs and writes `PorePress`,
`PorePressRate`, `DivVel`, and stress fields. The only disabled piece is the
feedback acceleration from pore pressure into the mechanical momentum equation.

## Reduced Baseline Scope

T5 reuses the T4s explicit platen workflow:

- top platen: moving `mkbound=1`, prescribed `v_z=-0.005 m/s`;
- bottom platen: fixed `mkbound=2`;
- specimen: `mkfluid=0`;
- lateral selected `FlexibleConfiningStress`;
- `CapConfiningStress=0`;
- `HydraulicElevationSource=0`;
- `PorePressureBoundaryOperator=0`;
- CPU Release only.

The output remains proxy-based:

- `p'` and `q` come from specimen-only mean `Sigma`;
- `Fz_proxy = -mean(Sigma_zz) * pi * R^2`;
- no true top/bottom platen reaction is claimed.

## DP Parameters

Two small diagnostic cases are prepared, not a sensitivity sweep:

| Case | `SoilConstitutiveModel` | `phi` | `coh` | `dlt` | Purpose |
| --- | ---: | ---: | ---: | ---: | --- |
| DP high strength | `1` | `33 deg` | `10000 Pa` | `0 deg` | Stable DP path expected to remain mostly elastic |
| DP mild yield | `1` | `30 deg` | `50 Pa` | `0 deg` | Short yield-intended diagnostic |

The high-strength case guards the workflow against accidental DP plumbing
errors. The mild-yield case checks whether `Kplastic` can become meaningful in
the reduced platen baseline without driving immediate numerical failure.

## Plasticity Criteria

The postprocessor will report:

- `Kplastic` max;
- `Kplastic` mean;
- number of specimen particles with `Kplastic > 1e-12`;
- measurement-region `Kplastic` max/mean/count;
- `p'` and `q` proxy paths;
- `q` versus axial strain;
- pore pressure versus axial strain.

A T5 DP case is considered useful if it completes with `code=0`, no exclusions,
bounded velocities and pressure-rate fields, and a readable `Kplastic` history.
If the mild-yield case produces a sudden plastic burst, exclusions, or
unbounded pore-pressure diagnostics, it should be treated as a failed yield
diagnostic rather than tuned further in T5.

## Stop Conditions

T5 stops at a short-to-medium window (`TimeMax=0.006 s`) and does not chase
large deformation. Do not proceed to full feedback, MCC, GPU, or strict paper
comparison from T5 alone.

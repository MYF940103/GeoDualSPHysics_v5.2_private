# T4t Platen Reaction Diagnostic Design

## Interface

New optional parameters:

```xml
<parameter key="SavePlatenReactionDiagnostics" value="0" />
<parameter key="PlatenTopMkBound" value="1" />
<parameter key="PlatenBottomMkBound" value="2" />
<parameter key="PlatenReactionMode" value="0" />
<parameter key="PlatenReactionArea" value="0" />
<parameter key="PlatenReactionInterval" value="500" />
```

Defaults preserve previous behavior. The diagnostic is disabled unless
`SavePlatenReactionDiagnostics=1`.

## Modes

| Mode | Meaning | Status |
| --- | --- | --- |
| `0` | CPU pairwise fluid-bound interaction accumulator for selected top/bottom platens | implemented |
| `1` | acceleration-sum or constraint-reaction diagnostic | reserved |
| `2` | future native reaction output | reserved |

Mode `0` is preferred over the old specimen-stress proxy because it is
accumulated from the actual specimen-platen SPH pair interactions. It still
does not include the force needed to prescribe the platen motion, so it should
be called a pairwise interaction reaction rather than a full actuator reaction.

## Output Quantities

The solver prints a compact log record every `PlatenReactionInterval` steps:

- simulation step and time;
- top and bottom `mkbound` identifiers;
- top/bottom platen particle counts;
- top/bottom accumulated interaction-pair counts;
- top/bottom force vector in Newtons;
- compression-positive top/bottom axial stress from `PlatenReactionArea`;
- normalized force balance error.

The T4t postprocessor parses these log records and writes:

- `t4t_true_reaction_metrics.csv`;
- `t4t_reaction_vs_proxy_comparison.csv`;
- `t4t_axial_stress_metrics.csv`.

The postprocessor also keeps the previous proxy:

```text
Fz_proxy = -mean(Sigma_zz)_specimen * pi * R^2
```

so the pairwise reaction and specimen stress proxy can be compared directly.

## Safety Rules

- CPU-only.
- GPU hard error when enabled.
- No force, velocity, stress, pore-pressure, or constitutive update is changed.
- Top and bottom mkbound values must be non-negative and distinct.
- `PlatenReactionArea < 0` is rejected.
- `PlatenReactionInterval <= 0` is rejected.

## T4t Validation Cases

T4t uses three feedback-off CPU Release cases:

1. elastic explicit platen with lateral flexible confinement;
2. high-strength DP, expected to remain elastic;
3. mild-yield DP, expected to activate `Kplastic` without destabilizing.

The diagnostic gate is not a strict paper validation gate. It only checks that
the explicit platen workflow can produce a consistent axial force diagnostic
for later T5b/T4t refinement.


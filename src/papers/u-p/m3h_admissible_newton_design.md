# M3h Admissible Newton and Line-Search Design

## Objective

M3h adds an opt-in admissible line-search layer around the CPU MCC local return
mapping.  The change targets only `SoilConstitutiveModel=3` and is intended to
diagnose and reduce local MCC return failures without changing elastic, DP,
softening, PR pore-pressure update, or FlexibleConfiningStress behavior.

Default behavior is preserved.

## Motivation

M3f showed that substepping alone did not clean the mild MCC platen case.  The
remaining failures are local to edge and platen-adjacent particles, with two
main failure families:

- `ReturnStatus=-1`: tension / inadmissible `p'`;
- `ReturnStatus=-3`: line-search failure.

This suggests the local Newton path must reject inadmissible trial updates
before they corrupt the hardening path, and must record why line-search
candidates are rejected.

## New XML Controls

M3h adds:

```xml
<MccAdmissibleLineSearch value="0" />
<MccLineSearchMaxBacktrack value="12" />
<MccLineSearchMinStep value="0" />
<MccLineSearchResidualReduction value="1e-4" />
<MccEnforcePositivePlasticMultiplier value="1" />
<MccAdmissibleProjection value="0" />
```

Definitions:

- `MccAdmissibleLineSearch=0`: use the old M3c/M3d/M3f line-search behavior.
- `MccAdmissibleLineSearch=1`: enable configurable admissible line-search
  checks and output diagnostics.
- `MccLineSearchMaxBacktrack`: maximum local backtracking reductions.
- `MccLineSearchMinStep`: minimum accepted line-search alpha.
- `MccLineSearchResidualReduction`: required residual reduction coefficient.
  A value of `0` allows non-increasing residual acceptance.
- `MccEnforcePositivePlasticMultiplier=1`: reject negative plastic multiplier
  candidates.
- `MccAdmissibleProjection=0`: off.
- `MccAdmissibleProjection=1`: reject invalid candidates and backtrack.
- `MccAdmissibleProjection=2`: diagnostic projection/clamping mode.  This is
  not a clean validation route.

Validation rules:

- `MccLineSearchMaxBacktrack` must be in `[1,128]`.
- `MccLineSearchMinStep` must be in `[0,1]`.
- `MccLineSearchResidualReduction` must be in `[0,1)`.
- `MccAdmissibleProjection` must be `0`, `1`, or `2`.

## Admissibility Checks

For a Newton line-search candidate, the admissible path checks:

1. `p' > MccTensionCutoff`;
2. `q >= 0` and finite;
3. `pc > 0` and finite;
4. finite `void ratio` / hardening state;
5. finite stress state;
6. `plastic multiplier >= 0` when
   `MccEnforcePositivePlasticMultiplier=1`;
7. residual non-increase or required residual reduction, depending on
   `MccLineSearchResidualReduction`.

Invalid candidates are rejected and the line-search alpha is reduced.

## Reject Reason Codes

M3h stores one aggregate reject reason per particle:

| code | meaning |
| ---: | --- |
| 0 | no line-search rejection recorded |
| 1 | invalid `p'` / tension cutoff |
| 2 | invalid `q` |
| 3 | invalid `pc` |
| 4 | invalid plastic multiplier |
| 5 | non-finite residual/state |
| 6 | residual did not satisfy reduction rule |
| 7 | line-search alpha below minimum |
| 8 | no accepted candidate / maximum backtracking exhausted |

These diagnostics are output through `SaveMccState=1` as:

- `MccLineSearchBacktrackCount`
- `MccLineSearchRejectReason`
- `MccLineSearchMinAlpha`

## Return Status Policy

Existing return statuses remain:

- `0`: elastic;
- `1`: plastic converged;
- `2`: substepped plastic converged;
- `-1`: tension cutoff / inadmissible `p'`;
- `-2`: singular Newton Jacobian;
- `-3`: line-search failure;
- `-4`: maximum iteration failure;
- `-5`: explicit partial fallback;
- `-6`: admissibility guard failure.

M3h does not use fallback as a clean validation route.  Any `-3`, `-5`, or
transient negative saved status fails the clean candidate gate.

## Interaction With Substepping

The admissible line search can be combined with:

- `MccSubstepping`;
- `MccSubstepMode`;
- `MccMaxSubsteps`;
- `MccMinSubsteps`;
- `MccSubstepYieldDistanceThreshold`;
- `MccAdmissibilityGuard`;
- `MccFailureFallback`.

The recommended no-fallback clean-candidate configuration is:

```xml
<MccSubstepping value="1" />
<MccSubstepMode value="1" />
<MccMaxSubsteps value="16" />
<MccFailureFallback value="0" />
<MccAdmissibleLineSearch value="1" />
<MccAdmissibilityGuard value="1" />
<MccAdmissibleProjection value="1" />
```

M3h tests this combination at original, half, and quarter platen speeds.

## Design Limits

M3h does not alter the MCC yield function, hardening law, elastic predictor,
PR pore-pressure equation, or platen boundary formulation.  It also does not
implement GPU MCC.  The work is a local CPU robustness diagnostic/refinement.

If the original-rate route still has saved-frame negative return statuses,
M3h should not be treated as clean MCC validation.

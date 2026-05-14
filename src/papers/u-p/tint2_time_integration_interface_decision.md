# TINT2 Time-Integration Interface Decision

Date: 2026-05-14

## Decision Summary

`PorePressureTimeIntegrationMode=1` is implemented and runs on CPU, but the
TINT2 matrix shows a neutral result:

- no regression for stable L3c/L5 operator `1` cases;
- no improvement for BND1 operator `2` feedback-off;
- no improvement for BND1 operator `2` feedback-on instability.

Decision: keep mode `1` as `[ACTIVE_EXPERIMENTAL] [CPU_ONLY]
[GPU_HARD_ERROR]` only long enough for TINT2-clean review and possible replay.
Do not promote it, do not make it default, and do not port it to GPU.

## Interface Status

```text
PorePressureTimeIntegrationMode=0
```

Status: `[PRODUCTION]` current default.

```text
PorePressureTimeIntegrationMode=1
```

Status after TINT2: `[ACTIVE_EXPERIMENTAL] [CPU_ONLY] [GPU_HARD_ERROR]`.

Cleanup recommendation: deprecate unless a follow-up finds a semantics reason
to keep it. TINT2 did not provide a positive numerical reason for promotion.

```text
PorePressureTimeIntegrationMode=2
```

Status: reserved, unsupported. It must continue to hard-error.

## What Mode 1 Proved

Mode `1` proves that the CPU code can stage pressure as an end-step
operator-split scalar:

```text
Interaction_Forces -> mechanical update -> pressure commit
```

with the commit block containing raw update, Shepard, and existing hydraulic
boundary projections.

The result is numerically indistinguishable from mode `0` in the tested 1D
cases, including the unstable BND1 operator `2` feedback-on case.

## What Mode 1 Did Not Prove

Mode `1` did not explain the BND1 mode `2` feedback-on instability. The same
failure signature remains:

```text
excluded = 973
DtMin adjustments = 10252
peak excess ~= 1.177e9 Pa
```

That points away from pressure-commit placement as the primary cause and back
toward boundary-operator reconstruction, pressure-gradient feedback, or the
interaction between generalized solid-wall no-flux samples and feedback.

## Cleanup Rules

Following INTF1:

- do not add mode `3` or `4`;
- do not add a family of staging diagnostics by default;
- do not port mode `1` to GPU before a positive CPU decision;
- if mode `1` remains neutral after any replay need is gone, mark it
  `[DEPRECATED]` or remove it in a cleanup branch.

## Next Recommendation

Do not continue TINT variants. The next technical decision should be one of:

1. BND2 focused on CPU operator `2` boundary/feedback physics, not time staging;
2. a landslide reduced baseline using the already stable operator `1` route and
   explicit caveats;
3. cleanup branch to deprecate failed or neutral experimental interfaces.

GPU remains deferred for nonzero `PorePressureTimeIntegrationMode`.

# M3m Refined Platen / Edge Geometry Design

## Objective

M3m follows the M3l result that modest platen overhang strongly reduced MCC
return failures without changing the MCC return mapping.  M3m keeps the same
CPU-only, feedback-off, very-short dense-output workflow and tests a small set
of geometry refinements around the platen/specimen edge.

No source, PR pressure equation, MCC return mapping, or FlexibleConfiningStress
physics is changed.

## Common Setup

All variants use:

- `SoilConstitutiveModel=3`;
- mild MCC parameters from M3k/M3l;
- `PorePressureFeedback=0`;
- explicit top platen prescribed velocity;
- fixed bottom platen;
- selected lateral `FlexibleConfiningStress`;
- `SaveMccState=1`;
- `SavePlatenReactionDiagnostics=1`;
- dense `TimeOut=0.0001 s`;
- `TimeMax=0.0025 s` for primary diagnostics;
- CPU Release only.

## Variant 0: Overhang Reference

This is the M3l best diagnostic case repeated in the M3m directory:

```text
specimen radius = 0.03 m
platen radius   = 0.04 m
```

Purpose:

- provide a self-contained reference;
- compare all refined geometry variants against the best M3l result.

## Variant 1: Optimized / Larger Platen Overhang

This variant slightly increases the overhang:

```text
specimen radius = 0.03 m
platen radius   = 0.045 m
```

Purpose:

- test whether more edge support further reduces `ReturnStatus=-3`;
- avoid a broad parameter sweep by testing only one larger radius.

Risk:

- too much overhang may act like an artificial support blanket rather than a
  realistic platen geometry.

## Variant 2: Overhang + Trimmed Specimen Edge

This variant keeps the M3l overhanging platen and trims the specimen cap edge:

```text
platen radius = 0.04 m
cap radius    = 0.025 m, z in [0, 0.01] and [0.09, 0.10]
core radius   = 0.03 m,  z in [0.01, 0.09]
```

Purpose:

- remove the sharp full-radius material edge directly adjacent to platens;
- test whether the first-onset edge/corner `-3` disappears.

Risk:

- changes specimen cap geometry and effective platen contact area;
- not a final validation geometry by itself.

## Variant 3: Overhang + Stepped Cap Transition

This variant keeps the M3l overhanging platen and adds a small stepped cap
transition:

```text
cap radius        = 0.025 m, z in [0, 0.01] and [0.09, 0.10]
transition radius = 0.028 m, z in [0.01, 0.02] and [0.08, 0.09]
core radius       = 0.03 m,  z in [0.02, 0.08]
```

Purpose:

- reduce sharp support discontinuity at cap/lateral transitions;
- keep a full-radius core and measurement zone.

Risk:

- still a Cartesian/segmented approximation, not a true smooth/fan-like layout.

## Optional Variant 4: Best Candidate Short Extended

Only if one primary variant clearly improves both `-3` and `-1` without
distorting reaction, p'-q, or pore pressure:

- rerun the best geometry at a slightly longer `TimeMax`;
- keep dense output;
- do not run long or enable feedback.

## Success Criteria

A useful M3m candidate should:

1. finish `code=0`, `excluded=0`, `DtMin=0`;
2. reduce `ReturnStatus=-3` below the M3l overhang reference, ideally to zero;
3. avoid worsening `ReturnStatus=-1`;
4. improve failed-particle support and neighbor proxies;
5. lower local velocity-gradient/shear and `q/p'` spikes;
6. keep pairwise reaction, global p'-q, and pore pressure bounded;
7. avoid creating new failure regions;
8. have a clear boundary-physics explanation.

Clean MCC validation still requires no saved-frame negative return statuses and
no fallback.

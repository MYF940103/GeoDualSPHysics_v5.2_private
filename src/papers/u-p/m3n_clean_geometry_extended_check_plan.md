# M3n Clean Geometry Extended Check Plan

## M3m Outcome

M3m found one meaningful improvement: increasing platen overhang from
`0.04 m` to `0.045 m`.

Benefits:

- final frame of the very-short dense case has no negative MCC return status;
- `ReturnStatus=-1` max falls from `20` to `8`;
- first `-3` episode is delayed from `0.001005 s` to `0.001609 s`;
- global reaction, p'-q, pore pressure, velocity, cap leakage, and lateral
  confinement remain bounded.

Limitations:

- maximum saved-frame `ReturnStatus=-3` remains `8`;
- a short extended check reintroduces `ReturnStatus=-3` with final `-3:5`;
- trimmed/stepped cap XML variants did not change the realized specimen
  particle set at `Dp=0.01 m`.

## Decision

M3n should not be a clean validation package yet.

The next technical choice depends on the target:

## Option A: Smooth/Fan-Like Specimen Layout

Recommended if the goal is clean MCC validation.

Rationale:

- M3k/M3l/M3m point to edge/corner support truncation and platen-adjacent local
  strain paths;
- small XML cap trimming did not alter the particle set at the current grid;
- a smooth/fan-like layout is closer to Zhao-style boundary preparation and is
  more likely to remove the edge-corner failure source physically.

Minimum next work:

- design a generated smooth cylinder or ring/fan layout;
- keep explicit platens and lateral FlexibleConfiningStress;
- rerun the M3k dense-onset diagnostic first, not a long validation case.

## Option B: Higher-Resolution Geometry Check

Recommended only if a smooth/fan layout is too expensive.

Rationale:

- current `Dp=0.01 m` rasterization prevents the trimmed/stepped XML geometry
  from producing a different specimen particle set;
- a modestly finer geometry may allow edge/cap rounding to be realized.

Risks:

- more particles increase cost;
- this can become a resolution study, which is outside the narrow M3m scope.

## Option C: Caveated Reporting

Recommended if the immediate goal is documentation rather than clean
validation.

Rationale:

- high-pc MCC remains elastic-like;
- mild MCC yields and outputs bounded state histories;
- pairwise reaction and p'-q diagnostics are usable;
- remaining failures are localized and well characterized.

Limitation:

- this remains a reduced feedback-off diagnostic, not strict MCC validation.

## No-Go Criteria for M3n

Do not call a candidate clean unless:

1. `code=0`, `excluded=0`, and `DtMin=0`;
2. every saved frame has `ReturnStatus=-3 = 0`;
3. every saved frame has `ReturnStatus=-5 = 0`;
4. near-tension `ReturnStatus=-1` does not grow into a new failure mode;
5. pc, void ratio, plastic strains, reaction, p'-q, pore pressure, and velocity
   remain bounded;
6. the geometry change has a clear boundary-physics meaning.

Full feedback and GPU remain deferred until the CPU reduced geometry route is
clean.

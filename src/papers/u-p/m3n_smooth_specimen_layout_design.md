# M3n Smooth Specimen Layout Design

## Design Candidates

### Option 1: Higher-Resolution Smooth Cylinder

Reduce the GenCase spacing from `Dp=0.01 m` to `Dp=0.0075 m` while keeping the
same physical cylinder and `0.045 m` platen overhang.

Purpose:

- alter the realized boundary/cap particle set;
- improve edge support and neighbor completeness;
- test whether coarse Cartesian particleization is the controlling source of
  local MCC return failures.

Advantages:

- XML-only;
- no solver source changes;
- no custom particle import;
- cheap enough for very-short dense output.

Limitations:

- still Cartesian/cut-cell, not truly fan-like;
- may alter timestep/loading discretization;
- could introduce new local paths because it adds many boundary particles.

### Option 2: External Radial / Fan-Like Specimen Generator

Use an isolated Python generator to create ring-based specimen particles and
keep mkbound platens explicit.

Purpose:

- produce a smoother lateral/cap boundary;
- more closely match Zhao-style smooth/fan-like layouts;
- reduce edge/corner support truncation by construction.

Advantages:

- strongest route for strict clean MCC validation.

Limitations:

- requires a confirmed custom-particle input workflow;
- must preserve mk grouping, motion, MCC/u-pw output, and confinement
  selection;
- larger implementation and validation cost.

### Option 3: Hybrid Layout

Keep a Cartesian core but generate a radial/smoothed boundary shell.

Purpose:

- reduce boundary support truncation while limiting particle count.

Limitations:

- more complex spacing/neighbor transition;
- can introduce a core-shell artifact if not carefully designed.

### Option 4: Caveated Reporting Only

Accept that the current MCC route is a reduced feedback-off diagnostic and do
not pursue clean validation until a larger geometry workflow is justified.

## M3n Implemented Candidate

M3n selects Option 1 for this round:

```text
reference: Dp=0.0100 m, Rplate=0.045 m, specimen particles=407
candidate: Dp=0.0075 m, Rplate=0.045 m, specimen particles=1035
```

Both cases keep:

- `SoilConstitutiveModel=3`;
- mild MCC parameters;
- `PorePressureFeedback=0`;
- explicit prescribed top platen and fixed bottom platen;
- selected lateral FlexibleConfiningStress;
- `SaveMccState=1`;
- pairwise platen reaction diagnostics;
- dense output over the failure-onset window.

The candidate is a feasibility diagnostic, not a fan-like implementation and
not a clean validation claim.

## Gate

A useful candidate should:

1. run with `code=0`, `excluded=0`, `DtMin=0`;
2. improve edge/cap support and neighbor proxies;
3. reduce `ReturnStatus=-3`;
4. not worsen `ReturnStatus=-1`;
5. preserve bounded reaction, p'-q, pore pressure, velocity, and cap leakage;
6. avoid introducing a new failure region.

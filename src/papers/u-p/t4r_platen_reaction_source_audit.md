# T4r Platen Reaction Source Audit

## Scope

T4r audits whether the T4q explicit platen workflow can produce a reliable top
or bottom platen reaction force without changing the triaxial physics.

The workflow uses:

- `mkbound=1`: moving top platen driven by XML `<motion>`;
- `mkbound=2`: fixed bottom platen;
- `mkfluid=0`: soil specimen;
- optional lateral `FlexibleConfiningStress`;
- `PorePressureFeedback=0` for this elastic diagnostic stage.

## Existing CPU Force Paths

The CPU interaction path computes accelerations in `Acec` during
`JSphCpuSingle::Interaction_Forces`.

Relevant source locations:

- `source/JSphCpuSingle.cpp`: main CPU interaction sequence.
- `source/JSphCpu.cpp`: `InteractionForcesFluid` and `InteractionForcesBound`.
- `source/JSphCpuSingle.cpp`: `FtCalcForcesSum`, `FtCalcForces`,
  `SaveFtAceFun`.

The ordinary fixed/moving `mkbound` particles used in T4q are not floating
objects. They do not enter the floating-body reaction accumulator. The existing
floating-body route sums `Acec[p] * massp` over floating particles and can save
`SaveFtAce`, but that route is tied to `FtObjs`, not to generic prescribed
motion `mkbound` platens.

## Moving / Fixed Platen Mechanics

The T4q top platen uses standard moving-boundary XML motion:

```xml
<motion>
  <objreal ref="1">
    <begin mov="1" start="0" finish="0.0015" />
    <mvrect id="1" duration="0.0015">
      <vel x="0" y="0" z="-0.005" />
    </mvrect>
  </objreal>
</motion>
```

This prescribes the top platen kinematics. It does not expose a balanced
reaction force at the XML level. The bottom platen is a fixed boundary group.

The current output provides particle kinematics, density, stress tensors,
`Kplastic`, and pore-pressure diagnostics. It does not provide per-`mkbound`
contact force or reaction-force summaries for ordinary fixed/moving boundaries.

## Boundary Force Availability

Current available quantities:

- `Acec`: internal per-particle acceleration during the interaction step;
- saved particle arrays: `Pos`, `Vel`, `Rhop`, `Sigma_kk`, `Sigma_ij`,
  `Kplastic`, and pore-pressure fields when enabled;
- flexible confinement diagnostics in `Run.out`;
- floating-body force summaries only for floating objects.

Current missing quantities for strict platen reaction:

- per-pair specimen-platen force attribution;
- per-`mkbound` summed boundary reaction for ordinary fixed/moving platens;
- separation of contact force from prescribed-motion kinematic override;
- reliable top/bottom axial reaction CSV.

## Can T4r Compute True Reaction Without Source?

No. The XML-only T4q platens are not floating bodies, and no existing saved CSV
contains a true top or bottom reaction force for ordinary `mkbound` platens.

T4r can compute only a reaction proxy from specimen stress:

```text
Fz_proxy = sigma_a_proxy * A0
sigma_a_proxy = -mean(Sigma_zz) over a specimen-only region
A0 = pi R^2
```

This is useful for diagnosing whether the platen workflow produces a coherent
specimen-only axial stress signal. It is not a true platen reaction.

## Minimum Future Source Patch

A strict reaction diagnostic should be a CPU-only, opt-in patch that does not
alter physics:

- add `SavePlatenReactionDiagnostics=0/1`;
- identify `PlatenTopMkBound` and `PlatenBottomMkBound`;
- accumulate interaction-force contributions on ordinary moving/fixed boundary
  particles before motion constraints are applied;
- write top/bottom `Fz`, net force, and axial stress `Fz/A0` to CSV;
- keep default behavior unchanged;
- hard-error on GPU until the CPU route is validated.

This patch is not implemented in T4r because the available XML-only path is
sufficient for a specimen-stress proxy audit, and a true per-pair reaction
accumulator needs careful placement in the interaction loop.

## T4r Decision

T4r proceeds as a postprocessing-only diagnostic:

- true platen reaction: not available;
- reaction output type: specimen-stress proxy;
- source changes: none;
- validation status: not strict axial reaction validation.


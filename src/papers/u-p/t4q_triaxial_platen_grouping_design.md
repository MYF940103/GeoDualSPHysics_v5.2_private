# T4q Triaxial Platen Grouping Design

## Objective

Define a clean specimen/platen grouping for a reduced triaxial platen workflow.
The grouping must separate the deformable u-pw soil specimen from rigid support
or loading platens.

## Groups

| Role | Proposed group | Behavior |
| --- | --- | --- |
| Soil specimen | `mkfluid=0` | u-pw material, stress update, pore pressure, measurement candidate |
| Top platen | `mkbound=1` | prescribed axial velocity/displacement, excluded from soil measurement |
| Bottom platen | `mkbound=2` | fixed support, excluded from soil measurement |
| Lateral free surface | subset of `mkfluid=0` | optional `FlexibleConfiningStress` with `f_i` and lateral selector |
| Measurement core | subset of `mkfluid=0` | excludes platen, cap-adjacent layers, and edge rings |

## Specimen Soil

The specimen remains the only u-pw material. It participates in:

- PR pore-pressure update;
- skeleton/effective stress update;
- optional pore-pressure feedback;
- lateral `FlexibleConfiningStress`;
- p-q and pore-pressure measurement regions.

For T4q the specimen uses `SoilConstitutiveModel=0` and
`PorePressureFeedback=0` unless an optional very short feedback smoke is
explicitly run.

## Top Platen

The top platen is a separate `mkbound` group. It should:

- move by prescribed velocity or displacement;
- not be updated by the soil constitutive model;
- not carry pore-pressure state;
- be excluded from measurement;
- eventually provide axial reaction output.

In the XML-only prototype, prescribed velocity is implemented through a
standard `<motion><objreal ref="1">` block.

## Bottom Platen

The bottom platen is a separate fixed `mkbound` group. It should:

- remain stationary;
- support the specimen;
- be excluded from measurement;
- eventually provide bottom reaction output.

In T4q it is fixed by omitting motion for `mkbound=2`.

## Lateral Surface

The lateral surface remains part of the specimen. It can be selected by the
existing cylinder classification:

- `FlexibleConfiningStress=1`;
- `ConfiningStressUseFiSelector=1`;
- `ConfiningStressUseLateralSelector=1`;
- `CapConfiningStress=0`.

This preserves the T4p decision that `CapConfiningStress` is diagnostic only.

## Measurement Region

The measurement region must be specimen-only:

- include only `mkfluid=0`;
- use a center core or central cylinder;
- exclude the top/bottom platen blocks;
- exclude cap-adjacent specimen layers for stress-path metrics;
- exclude lateral edge rings when computing p-q proxies.

The T4q script reports possible platen contamination explicitly.

## Current Limitation

If the standard SPH boundary contact is not adequate to transmit platen motion
to the u-pw specimen, the T4q result should be reported as an XML-only
feasibility failure. The next step would then be a small source patch for a
dedicated platen boundary, not another `AccInput` or `CapConfiningStress`
tuning route.

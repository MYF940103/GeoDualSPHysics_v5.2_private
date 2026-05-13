# T4l Cap Hydrostatic Support Source Audit

## Purpose

T4k showed that `InitialStressMode=1` correctly initializes a uniform
hydrostatic skeleton/effective stress state, but the reduced triaxial cylinder
does not have matching external axial traction on the top and bottom caps.
This audit checks what the current code can support before adding the smallest
cap-normal confinement route.

## Existing Cap Representation

The reduced triaxial specimen is generated as material particles, not as a
separate rigid platen or stress boundary. The current T4/T4k scaffold uses:

- `mkfluid=0` for the main specimen body;
- `mkfluid=1` for the top axial loading layer;
- cylinder classification from the T3 flexible-confinement diagnostics:
  interior, lateral, top cap, bottom cap, edge ring, and outside.

There is no existing strict top/bottom cap stress boundary in the reduced
triaxial XMLs. The top layer can be driven by `AccInput`, but that is a loading
device, not a balanced hydrostatic cap support.

## Existing Loading Routes

### AccInput / Prescribed Acceleration

`AccInput` can apply a prescribed axial acceleration to a target `mkfluid`.
It is appropriate for the later deviatoric axial loading stage. It is not a
clean hydrostatic cap support because:

- it only acts on the chosen driven layer unless a mirrored bottom route is
  built;
- it represents an externally prescribed acceleration history rather than a
  pressure traction magnitude;
- using it for hydrostatic support would blur the distinction between
  pre-confinement and axial compression.

### FlexibleConfiningStress

`FlexibleConfiningStress` is a Zhao-style isotropic pair contribution. With the
T3 selectors enabled it can target only cylinder lateral free-surface particles.
This keeps cap leakage at zero, but it deliberately excludes top/bottom caps
and edge rings. Therefore it can balance lateral confinement but not the
`sigma_zz` part of a hydrostatic initial stress.

Extending the lateral selector to also hit caps would be ambiguous: cap
particles need axial normal support, while edge rings should avoid double
counting between lateral and cap support.

## Source Gaps Before T4l

The code had:

- cylinder top/bottom/edge classification via `GetConfiningStressCylinderClass`;
- selected lateral confinement diagnostics;
- `InitialStressMode=1` for uniform effective stress;
- no pressure-force equivalent cap support;
- no cap support diagnostics;
- no cap-specific GPU guard.

This explains the T4k mismatch: the initialized stress was three-dimensional
hydrostatic, but the external traction was lateral-only.

## T4l Source Feature

T4l adds an opt-in CPU-only cap-normal support route:

- `CapConfiningStress`
- `CapConfiningStressP0`
- `CapConfiningStressRampStart`
- `CapConfiningStressRampEnd`
- `CapConfiningStressTopMk`
- `CapConfiningStressBottomMk`
- `CapConfiningStressMode`
- `CapConfiningStressAxisX/Y/Z`
- `SaveCapConfiningStressDiagnostics`

Mode `0` computes the integrated cap pressure force

```text
F_cap = p0_eff * pi * R^2
```

and distributes it over the selected top or bottom cap material particles by
mass. The top cap receives acceleration along `-axis`; the bottom cap receives
acceleration along `+axis`. Edge-ring particles are skipped to avoid
double-counting lateral flexible confinement.

The feature is applied as an external acceleration, not written into the stress
tensor and not used as axial loading. Defaults remain off, so legacy cases are
unchanged.

## CPU/GPU Status

The implementation is CPU-only. GPU execution hard-errors when
`CapConfiningStress=1`, matching the current CPU-first status of the other
strict triaxial confinement diagnostics.

## Remaining Gap

The new cap support closes the obvious `sigma_zz` support gap, but it is still
a reduced diagnostic route. It does not add rigid platens, restart-based
equilibration, boundary pressure completion, or total-stress coupling.

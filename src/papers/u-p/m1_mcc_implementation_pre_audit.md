# M1 MCC Implementation Pre-Audit

## Why MCC Planning Can Start

The DP feedback-off platen workflow now has enough scaffolding for constitutive planning:

- explicit top/bottom platen geometry is available;
- selected lateral confinement is stable with feedback off;
- specimen-only stress and p'-q proxies are available;
- pairwise platen reaction diagnostics are available for CPU reduced runs;
- DP high-strength and mild-yield cases distinguish elastic-like and plastic response;
- Kplastic output and plastic particle counts are usable in postprocessing.

This is sufficient to plan MCC interfaces, state variables, and single-point tests. It is not sufficient to implement MCC directly into production triaxial validation.

## Why MCC Should Not Be Implemented Immediately

Several blockers remain:

- full `PorePressureFeedback` is deferred and previously destabilized selected-confinement cases;
- platen reaction is a pairwise interaction diagnostic, not a full actuator reaction;
- stress convention and effective-stress sign must be locked before MCC return mapping;
- no MCC single-point return mapping test exists yet;
- no strict drained/undrained MCC triaxial protocol has been selected;
- GPU support is deferred.

## Existing Preconditions From DP Route

The current reduced route provides:

- `SoilConstitutiveModel=0` elastic baseline;
- `SoilConstitutiveModel=1` Drucker-Prager baseline;
- `SoilConstitutiveModel=2` reserved/used for DP softening paths in existing documentation;
- explicit platen and lateral confinement workflow;
- feedback-off PR pore-pressure diagnostics;
- CPU postprocessing for p', q, pore pressure, reaction, and plasticity.

## MCC State Variables Needed

MCC will need at least:

- void ratio `e` or specific volume `v`;
- initial void ratio `e0` or initial specific volume `v0`;
- preconsolidation pressure `p_c`;
- compression index `lambda`;
- swelling/recompression index `kappa`;
- critical-state slope `M`;
- plastic volumetric strain;
- possibly accumulated plastic shear strain for diagnostics;
- OCR or equivalent initialization helper if cases are defined through OCR.

These variables must be restart-safe and output-safe before any long triaxial route is attempted.

## Stress Convention Requirements

The current skeleton/effective stress convention stores compression as negative in `Sigmac`. Earlier initial-stress work used `InitialEffectiveStressIso=50` to write `Sigmac.xx=Sigmac.yy=Sigmac.zz=-50 Pa`.

MCC planning must define:

- whether internal MCC formulas use compression-positive p';
- where sign conversion occurs;
- how `p' = -(sigma_xx + sigma_yy + sigma_zz) / 3` maps to stored `Sigmac`;
- how tensile or near-zero p' is guarded;
- how pore pressure is kept separate while full feedback remains deferred.

## SoilConstitutiveModel Mapping

Recommended mapping:

- `0`: linear elastic skeleton;
- `1`: Drucker-Prager;
- `2`: Drucker-Prager with softening or archived softening branch;
- `3`: proposed Modified Cam-Clay.

MCC should be introduced as an opt-in CPU path first. Existing cases must remain unchanged.

## Drained / Undrained Requirements

MCC triaxial work should eventually support:

- drained triaxial compression with pore-pressure drainage or prescribed pressure boundary;
- undrained triaxial compression with volume constraint/pore-pressure response;
- consolidation or initial equilibrium stage;
- p'-q and specific-volume paths.

The current reduced DP route is feedback-off and does not validate the full undrained coupling. MCC implementation should therefore begin with a single-point driver and only later return to SPH triaxial.

## Recommended M1 Follow-Up Tasks

1. Source audit of the current elastic and DP stress update path.
2. MCC state-variable storage and restart/output design.
3. MCC return mapping derivation with the current sign convention.
4. CPU-only single-point tests:
   - elastic unload/reload;
   - isotropic compression;
   - drained triaxial compression;
   - undrained triaxial stress path in a material-point setting.
5. Only after the single-point gates pass, add a reduced SPH platen triaxial MCC smoke with feedback still off.

## No-Go Criteria

Do not implement MCC into the SPH triaxial workflow until:

- the sign convention is documented in source comments and reports;
- state variables are restart-safe;
- single-point return mapping tests pass;
- p' stays positive under expected compression states;
- the reduced DP package remains the comparison baseline;
- full feedback remains either deferred or explicitly scoped out.

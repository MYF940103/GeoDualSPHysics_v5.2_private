# T4r Reaction And Stress Diagnostics Design

## Purpose

T4r adds a diagnostic layer to the XML-only T4q platen workflow. The goal is to
extract specimen-only stress-path proxies and a clearly labeled axial reaction
proxy before attempting a longer feedback-off platen baseline.

This is not a DP/MCC task and not a full paper reproduction.

## Platen Diagnostics

The postprocessor records:

- top platen particle count;
- top platen mean displacement and velocity;
- bottom platen particle count;
- bottom platen mean displacement and velocity;
- top prescribed velocity check;
- bottom fixed check.

The current XML-only route does not expose true reaction force. T4r therefore
records:

- `true_reaction_available = 0`;
- `reaction_type = specimen_stress_proxy`;
- `sigma_a_proxy = -mean(Sigma_zz)` over specimen-only regions;
- `Fz_proxy = sigma_a_proxy * A0`, with `A0 = pi R^2`.

The sign convention follows the current effective-stress output: compressive
skeleton stress is negative, so positive compression proxy is `-Sigma_zz`.

## Specimen Diagnostics

Only `mkfluid=0` particles are included in specimen stress calculations.
`mkbound` top and bottom platen particles are excluded.

For each region:

- particle count;
- mean `Sigma_kk` and `Sigma_ij`;
- `p' proxy = -(Sigma_xx + Sigma_yy + Sigma_zz)/3`;
- `q proxy` from the deviatoric stress tensor;
- axial stress proxy `-mean(Sigma_zz)`;
- axial strain proxy from the specimen height;
- radial strain proxy from the specimen radius;
- `PorePress`, `ExcessPorePress`, `PorePressRate`, `DivVel`;
- `Kplastic` max and mean.

## Measurement Regions

T4r uses three specimen-only regions:

- `core_small`: `r <= 0.012 m`, `0.035 <= z <= 0.065 m`;
- `core_medium`: `r <= 0.018 m`, `0.025 <= z <= 0.075 m`;
- `specimen_minus_edges`: all specimen particles excluding platen-adjacent caps
  and the outer edge band.

The measurement region never includes `mkbound` platen particles.

## Confinement Diagnostics

When lateral `FlexibleConfiningStress` is active, the analyzer parses the
existing `Run.out` diagnostics:

- active lateral target count;
- `f_i` selection count;
- lateral inward acceleration mean/max;
- cap axial leakage;
- net confinement force and symmetry residual.

## T4r Cases

Two CPU Release short cases are used:

1. `CaseT4r_PlatenAxial_NoConfinement`
   - moving top platen;
   - fixed bottom platen;
   - no lateral confinement;
   - `PorePressureFeedback=0`.

2. `CaseT4r_PlatenAxial_LateralConfinement`
   - moving top platen;
   - fixed bottom platen;
   - lateral selected `FlexibleConfiningStress`;
   - `PorePressureFeedback=0`.

## Success Criteria

T4r is considered successful if:

- both CPU cases finish with `code=0`;
- excluded particles remain zero;
- `Kplastic=0`;
- top platen prescribed displacement matches the XML motion;
- bottom platen remains fixed;
- measurement contamination is zero;
- specimen-only `p'-q` proxy and axial stress proxy are produced;
- lateral confinement diagnostics remain healthy in the confined case.

The stage does not require a true reaction force. Lack of true reaction remains
the next source-level diagnostics blocker.


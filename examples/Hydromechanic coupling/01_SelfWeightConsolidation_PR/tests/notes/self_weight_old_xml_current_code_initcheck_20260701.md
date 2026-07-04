# Self-weight old XML with current code init check

Date: 2026-07-01

## Purpose

Check whether the old `a407fbd` Scenario2 XML layout (`HydroMech*` options inside `<soils>`) is parsed differently from the current migrated `<special><hydromechanics>` layout.

## Result

The old XML layout is compatible with the current code. The runtime hydromechanics and mechanical parameters matched the current Mode3 test:

- `HydroMechInitMode=AnalyticalSelfWeight1D`
- `HydroMechDrainage=Enabled`
- `PoreWaterRho=1000`
- `PoreWaterBulkModulus=2e8`
- `Porosity=0.3`
- `HydraulicConductivity=0.001`
- `PoreShepardRegularization=Disabled`
- `SlipMode=DBC vel=0`
- `Visco=0.4`
- `SoilDampingCoef=4e-5`
- `PeriodicActive=Axis-X`
- `CteB=384615.4`
- `Cs0=35.80574408560461`
- `FixedDt=1e-6`
- `sigma_zz min=-43.1867, max=-0.217019`

The only expected differences were the command-line short-check `TimeMax/TimePart` and the warning that old hydromechanics options are still inside `<soils>`.

## Decision

Do not blame the XML migration/default compatibility for the current mismatch with the old CPU baseline. Continue checking source-side mechanical path changes.

The short-check output and temporary old XML config were deleted after recording this note.

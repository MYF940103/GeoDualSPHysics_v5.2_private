# Self-weight Scenario 1 restart setup, 2026-06-27

Scenario 1 is prepared as a restart calculation from the selected Stage 1 `0.30 s` handoff state.

## Reference interpretation

Supporting Information Section II describes Scenario (1) as follows:

- start from the initial self-weight undrained response,
- treat the top free surface as drained after that initial response,
- switch gravity off,
- let the pore-pressure field dissipate according to Terzaghi 1D consolidation.

Therefore this test inherits the Stage 1 state rather than using `HydroMechInitMode=3`.

## Restart source

- Restart part: `Part_0060`
- Restart time in Stage 1: `0.30 s`
- Restart directory: `tests/outputs/CaseSWStage1_d02_D_SH40_FS_out/data`
- Required files:
  - `Part_0060.bi4`
  - `PartExtra_0060.bi4`

## Prepared cases

Short test to `Tv=0.05`:

- XML: `tests/configs/CaseSWScenario1_restart_p0060_G0_D_DTv0005_short_Def.xml`
- Bat: `tests/xCaseSWScenario1_restart_p0060_G0_D_DTv0005_short_win64_GPU.bat`
- `TimeMax=0.1821857143 s`

Full test to `Tv~1`:

- XML: `tests/configs/CaseSWScenario1_restart_p0060_G0_D_DTv0005_full_Def.xml`
- Bat: `tests/xCaseSWScenario1_restart_p0060_G0_D_DTv0005_full_win64_GPU.bat`
- `TimeMax=3.85 s`

Shared settings:

- `gravity=(0,0,0)`
- `HydroMechInitMode=0`
- `HydroMechDrainage=1`
- `HydroMechDrainageStartTime=0`
- `HydraulicConductivity=1e-3 m/s`
- `PoreShepardRegularization=0`
- `DtFixed=1e-6 s`
- `TimeOut=0.0182185714 s`, equivalent to `Delta Tv=0.005`

## Post-processing

The post-processing script is:

- `tests/support/postprocess_scenario1_restart.py`

It uses the inherited `Part_0000` pore-pressure profile as the analytical initial condition and builds the Terzaghi cosine-series solution from that profile. This separates Stage 1 initial-profile error from the Scenario 1 gravity-off diffusion error.

Primary outputs:

- `scenario1_pore_pressure_and_degree.png`
- `scenario1_target_summary.csv`
- `scenario1_degree.csv`
- `scenario1_profiles_by_tv.csv`

Only `PorePress` is used for the primary theory comparison. `ExcessPorePress` is not the main Scenario 1 quantity after restart because `PorePress0` is inherited from the gravity-loaded Stage 1 state.

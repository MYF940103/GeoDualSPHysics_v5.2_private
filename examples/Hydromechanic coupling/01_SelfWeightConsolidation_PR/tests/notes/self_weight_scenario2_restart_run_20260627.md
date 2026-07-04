# Self-weight Scenario 2 restart run status, 2026-06-27

## Run

- Case: `CaseSWScenario2_restart_p0060_D_DTv0005`
- Config: `tests/configs/CaseSWScenario2_restart_p0060_D_DTv0005_Def.xml`
- Bat: `tests/xCaseSWScenario2_restart_p0060_D_DTv0005_win64_GPU.bat`
- Restart source: `tests/outputs/CaseSWStage1_d02_D_SH40_FS_out/data/Part_0060.bi4`
- mDBC restart source: `tests/outputs/CaseSWStage1_d02_D_SH40_FS_out/data/PartExtra_0060.bi4`
- Solver: `DualSPHysics5.2_GEO_win64.exe`
- Fixed time step: `DtFixed=1e-6 s`
- Output interval: `TimeOut=0.0182185714 s`, equivalent to `Delta Tv=0.005`
- Full target: `TimeMax=3.85 s`
- Background launcher log: `tests/run_scenario2_restart_p0060_gpu_full.log`
- Output folder: `tests/outputs/CaseSWScenario2_restart_p0060_D_DTv0005_out`
- Figure folder after completion: `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005`

## Current check

The first attempt produced the `Tv=0.005` output before it was stopped and restarted cleanly for the long run. The early trend was correct:

- `Tv=0`: bottom excess pore pressure `10.4016 kPa`, theory `10.6964 kPa`
- `Tv=0.005`: bottom excess pore pressure `9.9582 kPa`, theory `9.8890 kPa`
- Direction: dissipating downward, matching the analytical trend
- `Tv=0.005` bottom error: about `+0.069 kPa`
- `Tv=0.005` RMS excess-pore-pressure error: about `126 Pa`

The clean long run was restarted with the same `DtFixed=1e-6 s` setting. `Run.out` confirmed:

- `Restart soil data: Sigma inherited, Kplastic reset for restart stage.`
- `Restart hydromechanical data: PorePress and PorePress0 inherited.`
- `Part_0001` was written at `PartTime=0.018219 s`, corresponding to `Tv=0.005`.

The run is expected to take several hours because the full `3.85 s` run at `DtFixed=1e-6 s` requires roughly `3.85e6` time steps.

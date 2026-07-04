# Self-weight consolidation tests cleanup and Mode 3 GPU control

Date: 2026-06-29

## Cleanup policy

The `tests` folder had accumulated full runs, short-window diagnostics,
temporary source-patch diagnostics, parameter sweeps, and postprocessing figures.
To keep the folder usable, only complete reusable groups are retained:

- `CaseSWStage1_d02_D_SH40_FS`
- `CaseSWScenario2_restart_p0060_D_DTv0005`

The retained groups preserve the Stage 1 restart baseline and the completed
Scenario 2 restart/full-run baseline. Existing notes and support scripts are
kept because they contain the conclusions from removed diagnostics.

Removed categories:

- Tv=0.30-0.34 and Tv=0.50-0.54 short-window rate/momentum/support diagnostics.
- Temporary bottom-force balance diagnostic outputs and figures.
- mDBC-corrector, artificial-viscosity, and CPU/GPU short-window comparison
  outputs.
- Incomplete or diagnostic configs/BAT/logs without a retained full output.
- Earlier cs0/cteb theory-test outputs; the conclusion note is retained.

## Consolidated conclusions from removed diagnostics

- `speedsound value="62.33" auto="false"` and the larger resulting `CteB` did
  not restore the late-time Scenario 2 dissipation trend when the full Stage 1
  and Scenario 2 workflow was rerun. Therefore, the later return to the
  soil-parameter-derived `Cs0`/`CteB` logic is retained.
- Increasing `SoilDampingCoef` to `0.02` did not remove the late bottom-pressure
  plateau.
- Turning off mDBC corrector did not remove the bottom-row rebound and generally
  worsened the force residual. Keep the corrector enabled for this case.
- Changing artificial viscosity in the Tv=0.50-0.54 window did not isolate the
  late pressure deviation as a simple viscosity-triggered artifact.
- A temporary force-loop patch that forced bottom rows to zero z acceleration
  suppressed bottom `vz` rebound, but made the bottom EPWP error worse
  (`0.1744 kPa` at Tv=0.54 versus `0.0915 kPa` for baseline). Therefore, the
  bottom force residual is not a direct correction target.
- The remaining uncertainty is in the coupled pore-rate response near the mDBC
  support, but this branch is paused for now.

## Next control run

Prepare and run a GPU control group based on the original root Scenario 2 output
that used:

- `HydroMechInitMode="AnalyticalSelfWeight1D"` (`value="3"`)
- CPU root reference output:
  `CaseSelfWeightConsolidation_Scenario2_out`
- Root reference run evidence:
  `ProgramFile=".../bin/windows/DualSPHysics5.2CPU_win64.exe"`
  and `HydroMechInitMode="AnalyticalSelfWeight1D"` in `Run.out`

The purpose is to check whether a GPU run with the same analytical initial state
matches the earlier CPU reference result, before returning to restart-based
Stage 1 inheritance questions.

## Cleanup result

Cleanup was executed after saving a manifest:

- `tests/notes/self_weight_tests_removed_items_20260629.csv`

Retained test outputs:

- `tests/outputs/CaseSWStage1_d02_D_SH40_FS_out`
- `tests/outputs/CaseSWScenario2_restart_p0060_D_DTv0005_out`

Retained test configs:

- `tests/configs/CaseSWStage1_d02_D_SH40_FS_Def.xml`
- `tests/configs/CaseSWScenario2_restart_p0060_D_DTv0005_Def.xml`

Retained test figures:

- `tests/figures/CaseSWStage1_d02_D_SH40_FS`
- `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005`

## Mode 3 GPU control run status

Prepared files:

- `tests/configs/CaseSWScenario2_Mode3_GPU_Def.xml`
- `tests/xCaseSWScenario2_Mode3_GPU_win64_GPU.bat`

Run started:

- PID file: `tests/run_scenario2_mode3_gpu_full.pid`
- stdout log: `tests/run_scenario2_mode3_gpu_full.log`
- stderr log: `tests/run_scenario2_mode3_gpu_full.err.log`
- output folder: `tests/outputs/CaseSWScenario2_Mode3_GPU_out`

Runtime evidence from `Run.out` after initialization:

- `ProgramFile=".../bin/windows/DualSPHysics5.2_GEO_win64.exe"`
- `HydroMechInitMode="AnalyticalSelfWeight1D"`
- `HydroMechDrainage="Enabled"`
- `PoreShepardRegularization="Disabled"`
- `Boundary="mDBC"`
- `mDBC-Corrector=True`
- `mDBC-FastSingle=False`
- `PeriodicActive="Axis-X"`
- `CteB=384615.4`
- `Cs0=35.80574408560461`
- `TimeMax=3.849999904632568`
- `TimePart=0.01999999955296516`

Progress snapshot:

- `Part_0001` written at `t=0.02 s`
- `Part_0002` written at `t=0.04 s`
- Estimated completion from `Run.out`: around `2026-06-30 02:53`

After completion, compare against the old CPU reference folder:

- `CaseSelfWeightConsolidation_Scenario2_out`

## Decision logic after the Mode 3 GPU control

The root `figures/self_weight_consolidation_profiles.png` represents the earlier
Scenario 2 CPU result based on `HydroMechInitMode value="3"`. Its main error is
concentrated at the very beginning:

- the analytical `AnalyticalSelfWeight1D` initial pore pressure and effective
  stress are close to the theoretical profile,
- but they are not a fully relaxed discrete SPH/mDBC equilibrium state,
- therefore the first calculation steps show an overshoot, visible especially
  around `Tv=0` and `Tv=0.005`.

If the current GPU `CaseSWScenario2_Mode3_GPU` run matches the previous CPU
result closely, the next recommended workflow is:

1. Use `HydroMechInitMode value="3"` only as a preparation stage.
2. Run a Stage 1 undrained relaxation from the analytical self-weight state.
3. Stop when the profile is dynamically stable and close to the initial
   undrained theoretical state.
4. Start Stage 2 from that saved Stage 1 state, inheriting pore pressure,
   `PorePress0`, effective stress, velocity state, and mDBC extra parts.
5. Enable the intended drainage boundary in Stage 2 and use it as the formal
   consolidation run.

This is logically equivalent to the current self-weight-loading-and-restart
approach, but replaces the previous self-weight loading stage with a shorter
analytical-initialization relaxation stage.

If the current GPU run differs strongly from the previous CPU result, then the
priority changes:

- first determine whether CPU/GPU paths differ for `HydroMechInitMode=3`, or
- whether later code changes have altered the shared mechanical/pore-pressure
  path.

In that case, do not proceed to the two-stage Mode 3 workflow until a CPU/GPU
or code-path discrepancy check is completed.

## Automatic watcher

A watcher was started to avoid manual monitoring drift:

- watcher script: `tests/support/watch_mode3_gpu_then_compare.ps1`
- watcher PID file: `tests/run_scenario2_mode3_gpu_watcher.pid`
- watcher log: `tests/run_scenario2_mode3_gpu_watch.log`
- watcher stdout: `tests/run_scenario2_mode3_gpu_watcher_stdout.log`
- watcher stderr: `tests/run_scenario2_mode3_gpu_watcher_stderr.log`

The watcher polls every 600 seconds. After the GPU BAT process exits, it checks
that postprocessing produced:

- `tests/figures/CaseSWScenario2_Mode3_GPU/scenario2_bottom_dissipation.csv`
- `tests/figures/CaseSWScenario2_Mode3_GPU/scenario2_target_summary.csv`

Then it runs:

- `tests/support/compare_mode3_gpu_cpu.py`

and writes the CPU/GPU decision note:

- `tests/notes/self_weight_mode3_gpu_cpu_comparison_20260629.md`

The clean watcher was confirmed running at `2026-06-29 19:40:36`, attached to
GPU run PID `56224`, with `parts=14` and last part `Part_0013.bi4`.

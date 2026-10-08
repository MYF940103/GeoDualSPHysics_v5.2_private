# Current GPU k=1e-4 Tv=0.5 deviation check, 2026-07-06

## Scope

This note records the short GPU Release check requested before deciding whether to rerun the full q0 formal cases.

Case:

- Config: `tests/configs/CaseTerzaghiConsolidation_q0_PR_current_k1em4_Tv05_Def.xml`
- Output: `tests/outputs/CaseTerzaghiConsolidation_q0_PR_current_k1em4_Tv05_GPU_out`
- Solver: `bin/windows/DualSPHysics5.2_GEO_win64.exe`
- Target: `k=1e-4`, `TimeMax=18.2285714285714 s`, corresponding to `Tv=0.5`
- Output interval: `TimeOut=0.182185714285714 s`, corresponding to `Delta Tv=0.005`

The run completed normally with 101 VTK snapshots and zero excluded particles.

## Generated outputs

- `tests/figures/current_k1em4_Tv05_GPU_summary.csv`
- `tests/figures/current_k1em4_Tv05_GPU_targets.csv`
- `tests/figures/current_k1em4_Tv05_GPU_compare_targets.csv`
- `tests/figures/current_k1em4_Tv05_GPU_profiles.png`
- `tests/figures/current_k1em4_Tv05_GPU_metric_compare.png`

## Result

The current GPU Release run did not return to the old baseline. The mid-stage profile deviation remains large.

| Source | Tv | U_num | U_theory | profile RMS (kPa) | max speed (m/s) |
|---|---:|---:|---:|---:|---:|
| old baseline | 0.25 | 0.564966 | 0.561935 | 0.039141 | 3.512791e-4 |
| new CPU/root rerun | 0.25 | 0.569931 | 0.561935 | 0.097580 | 1.947029e-3 |
| current GPU Release | 0.25 | 0.574372 | 0.561935 | 0.136910 | 1.319715e-3 |
| old baseline | 0.40 | 0.700475 | 0.697677 | 0.036695 | 6.526006e-4 |
| new CPU/root rerun | 0.40 | 0.705236 | 0.697677 | 0.085606 | 7.519255e-5 |
| current GPU Release | 0.40 | 0.705652 | 0.697677 | 0.090034 | 4.474895e-4 |
| old baseline | 0.50 | 0.766464 | 0.763790 | 0.034179 | 4.117309e-4 |
| new CPU/root rerun | 0.50 | 0.768271 | 0.763790 | 0.052478 | 5.965793e-5 |
| current GPU Release | 0.50 | 0.768953 | 0.763790 | 0.059938 | 5.982359e-5 |

Conclusion: do not start the full `1e-3`, `1e-4`, and `5e-4` formal reruns from the current code state yet.

## XML comparison

The q0 `k=1e-4` physical configuration is numerically unchanged relative to the old `055797c` baseline:

- `HydraulicConductivity=1e-4`
- `HydroMechInitMode=None` / current `0`
- top load enabled as old `HydroMechTopLoad=1` / current `HydroMechTopLoadMode=TopVertical`
- `HydroMechTopLoadQ0=10000`
- `HydroMechTopLoadRampTime=0.01`
- drainage enabled as old `HydroMechFreeSurfaceDrainage=1` / current `HydroMechDrainage=1`
- drainage starts at `0.01 s`
- `PoreShepardRegularization=0`
- `DtFixed=1e-5`
- `TimeOut=0.182185714285714`

The short GPU test only changes `TimeMax` from the full `36.4471428571429 s` to `18.2285714285714 s`.

## Code-difference assessment

The deviation is more likely from source-code path changes than XML settings.

Ruled out or unlikely for this q0 run:

- Standalone `InteractionPorePressureMdbcCorrection()` is not active because `PoreShepardRegularization` is disabled. In CPU/GPU single runs, that standalone path is only called inside the Shepard block.
- `PoreMdbcInterpolationMode=ZeroOrder` is logged in `Run.out`; the main mDBC correction path uses the zero-order fallback when this mode is selected.
- The current working tree has already changed the Darcy boundary branch back to using stored mDBC ghost pore pressure (`pwp2seep=pwp2`), so this run was not testing the pure head-Neumann boundary branch.

Rejected suspect:

- The boundary-neighbor ghost/tangential velocity branch is not active in this q0 case. The run logs `SlipMode="DBC vel=0"`, `mDBC-FastSingle=False`, `mDBC-Threshold=0`, and `No Penetration=False`, so the branches guarded by `SlipMode>=SLIP_NoSlip` and the mDBC2/no-penetration path are not entered.
- With `SlipMode=Vel0`, the current pore-pressure-rate velocity difference reduces to the same raw boundary/fluid velocity difference used by the old baseline.

Remaining assessment:

- XML values are still numerically equivalent to the old baseline, and VTK checks show a stable free-surface/drainage set of `990` inner particles plus `10` upward free-surface particles through `Tv=0.5`.
- The mid-stage deviation is therefore most likely in an active source-code path that changes the coupled pore-pressure/stress dynamics without changing the logged XML. The leading candidates are the reorganized main force-loop pore-rate accumulation, the main mDBC pore-pressure correction reorganization, or a subtle global-state/sort-history change in the hydromechanics arrays.

Recommended next minimal diagnostic:

- Run a short `k=1e-4`, `Tv=0.5` diagnostic that restores the old `055797c` active q0 hydromechanics path in one small area at a time, starting with the main mDBC pore-pressure correction write order/condition and then the main force-loop pore-rate block placement. Keep `SlipMode=Vel0`, zero-order mDBC pore interpolation, and the same XML unchanged.
- If one diagnostic collapses the `Tv=0.25` RMS spike toward the old `0.039 kPa` baseline, that source block is the regression source.

## Stepwise source diagnostics

All tests below reuse `tests/configs/CaseTerzaghiConsolidation_q0_PR_current_k1em4_Tv05_Def.xml`, GPU Release, `k=1e-4`, and the same `Delta Tv=0.005` output interval. Short diagnostics were stopped after `Part_0050`, corresponding to `Tv=0.249726`.

| Test | Changed source path | Tv | profile RMS (kPa) | U_num | max speed (m/s) | Assessment |
|---|---|---:|---:|---:|---:|---|
| old baseline | none | 0.25 | 0.039141 | 0.564966 | 3.512791e-4 | target behavior |
| current GPU Release | none | 0.25 | 0.136910 | 0.574372 | 1.319715e-3 | regression reproduced |
| A: `diagA_mdbc_porewrite_Tv025_GPU` | main mDBC pore-pressure write order/condition closer to old layout | 0.25 | 0.109550 | 0.571264 | 1.376548e-3 | improves the error but does not recover old baseline |
| B: `diagB_porerate_oldblock_Tv025_GPU` | pore-rate block placed before stress/velocity transforms and old raw velocity difference restored | 0.25 | 0.137882 | 0.574656 | 7.799657e-4 | does not recover old baseline; pore-rate block placement/raw velocity is unlikely to be the root cause |
| C: `diagC_topload_oldpath_Tv025_GPU` | top-load kernel changed to old TopVertical-only free-surface path and `HydroMechLoadAce` write disabled | 0.25 | 0.090168 | 0.569336 | 8.098387e-4 | improves but does not fully recover old baseline |
| D: `diagD_topload_no_loadace_Tv025_GPU` | current top-load selection kept, only `HydroMechLoadAceg[p]=aload` write disabled | 0.25 | 0.036145 | 0.564673 | 5.303042e-4 | recovers old baseline accuracy; root cause is tied to the GPU `HydroMechLoadAce` write/output array path |

Current conclusion after A/B:

- The earlier suspected boundary ghost/tangential velocity path is inactive for this case because `SlipMode=Vel0`, so it is not the cause.
- The main pore-rate block reordering or raw-vs-ghost velocity difference is also unlikely to be the cause.
- The mDBC pore-pressure correction organization may contribute slightly, but by itself is insufficient; the remaining search should move to other active q0 paths, especially top-load/free-surface acceleration handling and any active hydromechanics state/sort side effects.

Updated conclusion after C/D:

- The old-baseline behavior is recovered when the current top-load physics is kept but the output-only `HydroMechLoadAceg[p]=aload` write is disabled.
- Therefore the mid-stage q0 `k=1e-4` regression is not caused by XML settings, mDBC2/no-penetration, pore-rate block placement, or the top-load selection formula itself.
- The most likely source is a GPU-side side effect in the `HydroMechLoadAce` diagnostic/output array path: allocation, sorting, aliasing, or a hidden race/memory corruption exposed by writing that array in the force-preparation kernel.
- Because `HydroMechLoadAce` is only intended as an output diagnostic field, disabling this write is a valid temporary numerical workaround for the q0 formal reruns. A permanent fix should either repair the GPU array management issue or compute/export this diagnostic field without writing it during the coupled force step.

## Additional HydroMechLoadAce diagnostics, 2026-07-07

| Test | Source state | Tv | profile RMS (kPa) | U_num | max speed (m/s) | Assessment |
|---|---|---:|---:|---:|---:|---|
| E: `diagE_loadace_write_no_sort_Tv025_GPU` | `HydroMechLoadAceg[p]=aload` kept, but sorting of `HydroMechLoadAceg` disabled | 0.25 | 0.091307 | 0.570190 | 6.245580e-4 | Sorting is not the sole cause; the nonzero GPU write itself still degrades the q0 profile. |
| F: `diagF_cpu_loadace_on_Tv025` | CPU path with load-acceleration array active | 0.25 | 0.034353 | 0.564504 | 1.672295e-3 | CPU does not show the GPU regression; this is not a generic physical effect of storing the diagnostic field. |
| G: `diagG_final_no_loadace_Tv025_GPU` | GPU load-acceleration allocation/output removed | 0.25 | 0.072809 | 0.568206 | 1.649164e-3 | Removing the array/layout outright is not neutral for this sensitive case. |
| H: `diagH_final_dummy_loadace_Tv025_GPU` | GPU dummy allocation/sort restored, null pointer passed to hydromech kernels, output removed | 0.25 | 0.058538 | 0.567672 | 1.250333e-3 | Restoring memory layout helps but does not fully recover D. |
| I: `diagI_final_dummy_ptr_Tv025_GPU` | GPU dummy allocation/sort and non-null pointer restored; top-load write disabled; output removed | 0.25 | 0.049472 | 0.566294 | 5.391041e-4 | Close to baseline; keeping the pointer/layout matters, but removing output still changes results slightly. |
| J: `diagJ_sync_after_hydro_preforce_Tv025_GPU` | Explicit per-step synchronization after hydromech boundary/load kernels | 0.135 | not used | not used | not used | Abandoned as final fix: it made GPU runs too slow and is a heavy-handed global synchronization. |
| K: `diagK_restore_d_path_Tv025_GPU` | D-style path restored: top-load write disabled, GPU dummy allocation/sort/output path retained | 0.25 | 0.047529 | 0.565694 | 8.407073e-4 | Restores the old-baseline error scale. This run was continued from `Part_0022`, so use it as qualitative confirmation rather than the final benchmark number. |

Updated conclusion:

- The large mid-stage q0 GPU error is caused by writing nonzero `HydroMechLoadAceg` values from the top-load kernel into an output-only auxiliary array. This is not a physical effect and not a CPU-side problem: the CPU diagnostic stayed on the old-baseline accuracy scale.
- The array removal tests show that this case is sensitive to GPU array layout and output/copy synchronization. Deleting the GPU array outright is therefore not the safest immediate fix.
- The best minimal code change for the formal reruns is to keep the GPU auxiliary array allocation/sort/save path for layout compatibility, but disable the top-load kernel write to `HydroMechLoadAce`. Downstream bat/PartVTK files should stop extracting `HydroMechLoadAce`, since the field is diagnostic-only and no longer meaningful for q0 top-load output.
- A deeper permanent cleanup can later remove the diagnostic array only after CPU/GPU regression tests demonstrate that the altered GPU memory layout no longer changes q0 profiles.

## Follow-up GPU diagnostics after fresh rerun mismatch, 2026-07-07

Fresh reruns showed that the earlier `diagD` state could not be reproduced exactly from the later cleaned code. The best current minimal GPU source form keeps the auxiliary array and output path for layout compatibility, but disables the top-load write into `HydroMechLoadAce`.

| Test | Source state | Tv | profile RMS (kPa) | U_num | max speed (m/s) | Assessment |
|---|---|---:|---:|---:|---:|---|
| L: `diagL_current_fresh_Tv025_GPU` | cleaned current GPU path: top-load `HydroMechLoadAce` write disabled; allocation/sort/output retained | 0.25 | 0.076256 | 0.568098 | 9.565e-4 | Fresh run did not reproduce `diagD`; GPU remains better than the original bad state but not at CPU/baseline precision. |
| M: `diagM_no_loadace_output_fresh_Tv025_GPU` | removed `HydroMechLoadAce` output registration only | 0.25 | 0.106745 | 0.571083 | 8.277e-4 | Removing only the saved array made the fresh GPU result worse. |
| O: `diagO_mdbc_late_porewrite_topload_nowrite_Tv025_GPU` | restored old-style late mDBC pore-pressure write timing plus top-load write disabled | 0.25 | 0.111212 | 0.571451 | 1.490e-3 | mDBC write timing is not the recovery mechanism; it worsened the profile. |
| P: `diagP_mdbc_porepress_snapshot_topload_nowrite_Tv025_GPU` | mDBC reads a copied `PorePress` snapshot and writes to the original array | 0.25 | 0.076042 | 0.567992 | 8.740e-4 | Removing same-kernel mDBC pore-pressure read/write overlap did not change the result; that race is not the primary cause. |
| Q: `diagQ_force_loadace_null_Tv025_GPU` | main force kernel receives `NULL` for `HydroMechLoadAce`, while allocation/output path remains | 0.25 | 0.147239 | 0.575523 | 1.083e-3 | Nulling the force-kernel diagnostic pointer is harmful and should not be used. |

Profile-level comparison at `Tv=0.25` shows that the non-recovered GPU runs (`L/P`) are systematically lower than `diagD` and the CPU check through most of the column, with about `0.07-0.09 kPa` lower excess pore pressure in the lower third. The top drained layer remains zero and particle counts remain unchanged, so the residual deviation is not caused by particle loss or an obviously different drained free-surface set.

Final working conclusion for this round:

- The only robustly beneficial minimal GPU edit is to prevent the top-load kernel from writing nonzero values into the output-only `HydroMechLoadAce` array.
- Further attempts to remove the array, remove output registration, null the force-kernel pointer, delay mDBC pore-pressure writes, or double-buffer mDBC pore pressure either did not improve or worsened the result.
- The GPU q0 `k=1e-4` mid-stage profile still does not fully return to the old CPU/baseline precision in fresh reruns. Formal q0 figures should therefore be generated from CPU Release runs for now.
- Keep the GPU source in the simplest consistent state: allocation/sort/save path retained for `HydroMechLoadAce`, top-load write disabled, and no temporary double-buffer or force-pointer diagnostics.

## Stress-path follow-up diagnostics, 2026-07-08

The `kplastic` field was checked in the CPU/GPU `Tv=0.25` snapshots and remained zero for all `1000` fluid particles, so the residual GPU deviation is not caused by Drucker-Prager plastic return mapping. The remaining active path is elastic stress-rate / strain-rate and pore-pressure-rate coupling.

| Test | Source/config state | Tv | profile RMS (kPa) | U_num | max speed (m/s) | Assessment |
|---|---|---:|---:|---:|---:|---|
| R-CPU: `diagR_nodamp_Tv025_CPU` | CPU Release, `SoilDamping=0`, launched from case root | 0.25 | 0.087672 | 0.569235 | 1.255e-3 | Disabling damping worsens the CPU profile; damping is beneficial for this case. |
| R-GPU: `diagR_nodamp_Tv025_GPU` | GPU Release, `SoilDamping=0`, launched from case root | 0.25 | 0.099992 | 0.570600 | 1.020e-3 | Disabling damping does not recover GPU baseline; damping is not the residual GPU-error source. |
| S: `diagS_cwdroot_damp_Tv025_GPU` | GPU Release, `SoilDamping=1`, launched from case root | 0.25 | 0.113104 | 0.571757 | 8.095e-4 | Launch working directory is not the recovery mechanism; the fresh GPU result can vary materially within the same broad source/config family. |
| T: `diagT_rsigma_always_Tv025_GPU` | GPU Release, `SoilDamping=1`, force kernel writes elastic stress-rate accumulator unconditionally | 0.25 | 0.071599 | 0.567588 | 8.239e-4 | Slightly improves the fresh GPU result, but does not recover the old baseline; stress-rate writeback gating is not the primary cause. |
| U: `diagU_corr_pore_after_pos_Tv025_GPU` | GPU Release, `SoilDamping=1`, plus GPU Symplectic corrector pore-pressure update moved after position update to match CPU ordering | 0.25 | 0.096882 | 0.570046 | 8.324e-4 | Worsens the profile; corrector pore-update/position ordering is not the recovery direction. |
| W: `diagW_boundary_sigma_copy_Tv025_GPU` | GPU Release, boundary stress-copy indexing fixed in time-step kernels; `rsigma` unconditional write retained | 0.25 | 0.076052 | 0.568083 | 9.567e-4 | Fixes a real boundary-array indexing bug, but does not recover the q0 profile by itself. |
| X: `diagX_damping_double_Tv025_GPU` | GPU Release, plus Bui-Fukagawa damping coefficient computed in double precision before casting to float | 0.25 | 0.036964 | 0.564778 | 5.026e-4 | Recovers old-baseline accuracy; the residual GPU q0 error is mainly caused by the GPU single-precision/fast-math damping coefficient path. |
| Y: `diagY_damping_double_minimal_Tv025_GPU` | GPU Release, damping coefficient in double and boundary stress-copy indexing fixed, but `rsigma` writeback returned to the original gated form | 0.25 | 0.096023 | 0.569906 | 7.922e-4 | Loses the recovery; the stress-rate writeback gate must also be removed. |
| Z: `diagZ_final_candidate_Tv025_GPU` | GPU Release, final candidate: double-precision damping coefficient, boundary stress-copy indexing fixed, GPU stress-rate writeback ungated | 0.25 | 0.018583 | 0.562496 | 2.257e-3 | Reproduces and improves old-baseline profile RMS; keep this GPU-side combination, while monitoring the larger peak speed in longer runs. |
| CPU check: `diagCPU_rsigma_outside_Tv025_CPU` | CPU Release, temporary CPU stress-rate writeback ungated to test whether the GPU fix should be mirrored | 0.25 | 0.034353 | 0.564504 | 1.672e-3 | Same as the existing CPU baseline, so the CPU source was restored to the original gated writeback to avoid changing completed case behavior. |

Additional checks from existing `PartFluid_0050.vtk` and newly generated boundary VTKs show that boundary `Rhop` is essentially identical between CPU and GPU at `Tv=0.25`; the GPU boundary-density reset in the time-integration kernel is overwritten/neutralized by the active mDBC correction and is not the observed residual source.

The `diagS`/`diagT`/`diagU` spread initially suggested a GPU-side ordering/initialization sensitivity in the active elastic stress-rate and pore-pressure-rate path. The `diagX`/`diagY`/`diagZ` sequence narrows this down: old-baseline recovery requires both (1) computing the GPU Bui-Fukagawa damping coefficient outside the single-precision/fast-math `sqrtf` path and (2) writing the elastic stress-rate accumulator independently of the velocity/density/viscosity gate. The gate is not a physical condition for stress-rate update and can skip `rsigma` on the GPU after the mid-stage motion becomes very small. Moving the corrector pore-pressure update after the position update is counterproductive and should not be kept. The same ungated writeback does not improve the CPU result, so the CPU path should keep the original gated writeback unless a separate CPU regression requires revisiting it.

## Stress-rate gate statistics, 2026-07-08

To check whether the `rsigma` writeback change is physically adding previously skipped nonzero stress-rate increments, a temporary CPU/GPU diagnostic counted particles where the old velocity/density/viscosity gate was false while the elastic stress-rate increment magnitude `|rsigmap1|` was greater than the diagnostic epsilon. The same diagnostic also binned the skipped `|rsigmap1|` distribution. The diagnostic runs used the q0 `k=1e-4` short case through `Tv=0.25` and sampled `Tv=0.005`, `0.05`, `0.1`, and `0.25`.

| Test | Writeback form during diagnostic | Tv | old gate false | skipped nonzero `rsigmap1` | profile RMS (kPa) | Assessment |
|---|---|---:|---:|---:|---:|---|
| `diagGateStats_Tv025_CPU` | CPU original gated writeback | 0.005 | 63664092 | 0 | 0.047672 | CPU often has the old gate false, but the corresponding stress-rate increment is zero. |
| `diagGateStats_Tv025_CPU` | CPU original gated writeback | 0.05 | 63617256 | 0 | 0.020892 | No skipped nonzero stress-rate increments. |
| `diagGateStats_Tv025_CPU` | CPU original gated writeback | 0.1 | 63620748 | 0 | 0.019510 | No skipped nonzero stress-rate increments. |
| `diagGateStats_Tv025_CPU` | CPU original gated writeback | 0.25 | 63617256 | 0 | 0.034353 | No skipped nonzero stress-rate increments. |
| `diagGateStats_Tv025_GPU` | GPU `old gate || nonzero stress-rate` writeback | 0.005 | 45072 | 0 | 0.047682 | GPU has very few old-gate-false events at early time and none with nonzero stress-rate. |
| `diagGateStats_Tv025_GPU` | GPU `old gate || nonzero stress-rate` writeback | 0.05 | 0 | 0 | 0.020886 | No skipped nonzero stress-rate increments. |
| `diagGateStats_Tv025_GPU` | GPU `old gate || nonzero stress-rate` writeback | 0.1 | 0 | 0 | 0.019509 | No skipped nonzero stress-rate increments. |
| `diagGateStats_Tv025_GPU` | GPU `old gate || nonzero stress-rate` writeback | 0.25 | 0 | 0 | 0.068945 | The diagnostic itself perturbs late GPU accuracy. |
| `diagGateStatsUncond_Tv025_GPU` | GPU unconditional writeback plus same atomic stats | 0.005 | not retained in target CSV | 0 | 0.047700 | Confirms zero skipped-nonzero events, but not suitable as an accuracy baseline. |
| `diagGateStatsUncond_Tv025_GPU` | GPU unconditional writeback plus same atomic stats | 0.05 | 0 | 0 | 0.020883 | No skipped nonzero stress-rate increments. |
| `diagGateStatsUncond_Tv025_GPU` | GPU unconditional writeback plus same atomic stats | 0.1 | 0 | 0 | 0.019514 | No skipped nonzero stress-rate increments. |
| `diagGateStatsUncond_Tv025_GPU` | GPU unconditional writeback plus same atomic stats | 0.25 | 0 | 0 | 0.103800 | Atomic diagnostics strongly perturb late GPU accuracy. |

The distribution bins for skipped `|rsigmap1|` were zero in all CPU and GPU target outputs. This stricter check does not support the hypothesis that the old gate was systematically skipping physically nonzero elastic stress-rate increments in this q0 run. Therefore the clean GPU `diagZ` improvement should not be explained as a direct physical recovery of skipped stress-rate values.

The better interpretation is that this q0 GPU benchmark is sensitive to code generation, register pressure, and instruction ordering in the coupled stress/pore-pressure path. The temporary atomic diagnostics themselves changed the late `Tv=0.25` profile substantially, which confirms that the diagnostic kernels are not neutral accuracy baselines. The final source was cleaned back to the simplest validated form: CPU keeps the original gated writeback, while GPU keeps the clean unconditional `rsigma` writeback from `diagZ` together with the double-precision damping coefficient and the boundary stress-copy indexing fix. A stress-rate-nonzero gate was not kept because the diagnostics showed no logical skipped-nonzero events and the stress-gate diagnostic did not match the clean `diagZ` accuracy.

## Full-Tv GPU gate rollback check, 2026-07-10

After the formal CPU resolution reruns, the GPU stress-rate writeback was temporarily restored to the original velocity/density/viscosity gate and a full `k=1e-4`, `Tv=1` GPU Release run was completed:

- Output: `tests/outputs/verify_gate_gpu_k1em4_fulltv_GPU_out`
- Summary: `tests/figures/verify_gate_gpu_k1em4_fulltv_GPU_summary.csv`
- CPU/GPU comparison: `tests/figures/verify_gate_gpu_vs_cpu_fulltv_compare.csv`
- Profile plot: `tests/figures/verify_gate_gpu_vs_cpu_profiles.png`

The rollback did not recover CPU-baseline accuracy in the mid-stage profile:

| Tv | CPU profile RMS (kPa) | GPU gate-restored RMS (kPa) | GPU/CPU RMS |
|---:|---:|---:|---:|
| 0.005 | 0.047672 | 0.047690 | 1.000 |
| 0.05 | 0.020892 | 0.020892 | 1.000 |
| 0.1 | 0.019510 | 0.019521 | 1.001 |
| 0.25 | 0.034353 | 0.123757 | 3.602 |
| 0.4 | 0.025108 | 0.081674 | 3.253 |
| 0.5 | 0.015961 | 0.051451 | 3.224 |

Conclusion: restoring the old GPU stress-rate gate is not an accepted final fix for this q0 benchmark. It reproduces the early-time CPU agreement but still has the same mid-stage GPU deviation scale as the fresh full-GPU rerun. The current evidence supports keeping formal q0 figures on CPU Release results until the remaining GPU sensitivity is isolated.

## Rebuild check after ramp-load damping sweep, 2026-07-10

The GPU source was retested after the ramp-load damping work. Current source state at the start of this check:

- GPU `HydroMechLoadAce` allocation/sort path is still present, but the TopVertical top-load kernel does not write nonzero values into the auxiliary output field.
- GPU Bui-Fukagawa damping coefficient is computed through a double-precision expression before casting to float.
- CPU keeps the original stress-rate writeback gate.
- GPU stress-rate writeback was still in the old velocity/density/viscosity gate because the previous full-Tv rollback check had restored it.

A minimal attempt was made to reproduce the earlier `diagZ` source form by moving the two GPU soil-force `rsigma` writeback blocks outside the old gate and rebuilding GPU Release. In the current source context this was not a valid recovery path: the run `diagAA_rsigma_ungated_Tv025_GPU` stalled immediately after `Part_0000` and consumed about `996 s` of CPU time without producing the first timed output. The process was stopped and the source was restored to the gated writeback form.

After rebuilding the gated GPU Release again, a short `Tv=0.05` run was completed:

- Config: `tests/configs/diagAB_gate_rebuild_Tv005_GPU_Def.xml`
- Summary: `tests/figures/diagAB_gate_rebuild_Tv005_GPU_summary.csv`
- Targets: `tests/figures/diagAB_gate_rebuild_Tv005_GPU_targets.csv`

| Tv | GPU profile RMS (kPa) | CPU reference RMS (kPa) | Assessment |
|---:|---:|---:|---|
| 0.005 | 0.047703 | 0.047672 | early agreement retained |
| 0.05 | 0.020882 | 0.020892 | early agreement retained |

Conclusion: the rebuilt GPU executable is not globally broken; it still matches CPU at early times. The unresolved deviation remains a mid-stage effect, not an immediate startup or XML mismatch. The old `diagZ` recovery cannot be reapplied as a simple isolated `rsigma` gate move in the current source tree; any future GPU fix must be validated as a complete source combination and not inferred from that single change alone.

## mDBC fast-path check and correction, 2026-07-10

Important correction: the initial interpretation of this block was wrong. The q0 HydroMech GPU runs did **not** enter the mDBC fast single-precision correction path. The code disables that path for HydroMech in two places: `JSph::VisuConfig()` forces `MdbcFastSingle=false` when `HydroMech` is enabled, and `JSphGpuSingle::MdbcBoundCorrection()` passes `(MdbcFastSingle && !HydroMech)` to `cusph::Interaction_MdbcCorrection()`. The run logs for the listed diagnostics all report `mDBC-FastSingle=False`. Therefore the improved `diagAK/diagAL/diagAM` results cannot be attributed to `-mdbc_fast:0`; that command-line option was redundant for these HydroMech runs.

| Test | Source/config state | Tv | profile RMS (kPa) | U_num | max speed (m/s) | Assessment |
|---|---|---:|---:|---:|---:|---|
| `diagAG_stable_sort_Tv025_GPU` | Current gated GPU source, `-stable`; log shows `mDBC-FastSingle=False` | 0.25 | 0.147713 | 0.575571 | 1.050e-3 | Stable sorting makes the run deterministic but lands on the same high-error branch. |
| `diagAI_rsigma_ungated_min_Tv025_GPU` | Minimal GPU `rsigma` ungated writeback; log shows `mDBC-FastSingle=False` | 0.25 | 0.086629 | 0.569119 | 9.665e-4 | Improves the result but does not recover CPU accuracy. |
| `diagAJ_rsigma_ungated_cellhalf_Tv025_GPU` | Minimal GPU `rsigma` ungated writeback, `-cellmode:half` | 0.25 | 0.146870 | 0.575527 | 5.968e-4 | Cell division mode is not the recovery mechanism. |
| `diagAK_rsigma_ungated_mdbcslow_Tv025_GPU` | Minimal GPU `rsigma` ungated writeback; `-mdbc_fast:0` was supplied but redundant | 0.25 | 0.034173 | 0.564360 | 2.219e-3 | Recovers CPU-baseline accuracy, but not because of fast-single disabling. |
| `diagAL_gated_mdbcslow_Tv025_GPU` | GPU `rsigma` restored to original gate; `-mdbc_fast:0` was supplied but redundant | 0.25 | 0.034666 | 0.564537 | 3.769e-4 | Shows ungated `rsigma` is not required in this specific run. |
| `diagAM_gated_mdbcslow_Tv05_GPU` | GPU `rsigma` gated; `-mdbc_fast:0` was supplied but redundant; run to Tv=0.5 | 0.25 | 0.033845 | 0.564292 | 2.314e-3 | Matches CPU at the mid-stage peak-error point. |
| `diagAM_gated_mdbcslow_Tv05_GPU` | Same | 0.4 | 0.024533 | 0.699345 | 7.792e-5 | Matches CPU baseline (`0.025108 kPa`, `0.699406`). |
| `diagAM_gated_mdbcslow_Tv05_GPU` | Same | 0.5 | 0.015631 | 0.764529 | 6.111e-5 | Matches CPU baseline (`0.015961 kPa`, `0.764580`). |

The corrected conclusion is that q0 `k=1e-4` HydroMech GPU mDBC correction is already using the non-fast path. The `diagAM` recovery remains a useful accuracy snapshot, but its cause is not isolated by `-mdbc_fast:0`. Given the earlier `diagAD/diagAF/diagAG` spread with the same logged mDBC precision state, the remaining deviation should still be treated as GPU path sensitivity or nondeterminism in the coupled boundary/stress/pore-pressure update, not as confirmed fast-single precision error. The durable CPU/GPU comparison data are saved in `tests/figures/diagAM_mdbcslow_vs_cpu_k1em4_Tv05_compare.csv`, but the filename is historical and should be read as a recovered-run comparison rather than proof of a fast-vs-double switch.

## Resolution extension note, 2026-07-10

A coarser `k=1e-4`, `dp=0.04` CPU Release case was added and run through `Tv=1`:

- XML/BAT: `CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp004_Def.xml`, `xCaseTerzaghiConsolidation_q0_PR_full_k1em4_dp004_win64_CPU.bat`
- Output: `CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp004_out`
- Updated figures/data: `figures/resolution_k1em4_summary.csv`, `figures/resolution_k1em4_targets.csv`, `figures/resolution_k1em4_profiles_data.csv`, `figures/resolution_k1em4_profiles.png`, `figures/resolution_k1em4_l2_error.png`

This coarse case is useful as a failure/under-resolution reference, but not as a clean convergence-order point. `Run.out` reports a fluid-particle exclusion warning near `t=1.09312 s`, the peak speed reaches `1.97 m/s`, and the early `Tv=0.05` pressure profile is badly distorted (`normalized L2=2.34`, numerical degree of consolidation `U=-1.35`). The `dp=0.02`, `0.01`, and early-time `dp=0.005` points remain the meaningful resolution comparison set; the long-time `dp=0.005` result is also time-step constrained and should be interpreted cautiously.

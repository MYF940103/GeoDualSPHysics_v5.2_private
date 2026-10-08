# q0 GPU no-flag precision conclusion

Date: 2026-07-11

Case family: `02_TerzaghiConsolidation_q0_PR`, `k=1e-4`, `dp=0.01`, `Tv=0.25` short validation.

## Finding

The poorer GPU results seen when the run did not explicitly pass `-mdbc_fast:0` were not caused by the mDBC fast-single correction branch itself.

Evidence:

- The solver logs for the old explicit good run, the old no-flag run, and the current no-flag runs all reported `mDBC-FastSingle=False`.
- The GPU mDBC correction call also passes `(MdbcFastSingle && !HydroMech)`, so an enabled hydromechanics case should not use the fast-single mDBC correction path.
- Adding an early `HydroMech` pre-read before boundary-command parsing made the no-flag state explicit, but did not recover the old baseline by itself.
- Removing the GPU `HydroMechLoadAceg` diagnostic array from allocation/sorting/kernel write/output restored the no-flag GPU result to the CPU baseline level.

## Tv ~= 0.25 profile metrics

| Case | Explicit `-mdbc_fast:0` | `HydroMechLoadAceg` active | RMS profile error (kPa) | Normalized L2 |
| --- | --- | --- | ---: | ---: |
| CPU baseline | n/a | CPU baseline | 0.034353 | 0.007026 |
| Old GPU good | yes | partially disabled | 0.034830 | 0.007123 |
| Old GPU no-flag | no | active | 0.088124 | 0.018052 |
| GPU no-flag + HydroMech preread only | no | active | 0.120189 | 0.024680 |
| GPU no-flag + no `HydroMechLoadAceg` | no | disabled | 0.020589 | 0.004215 |

## Code-side conclusion

`HydroMechLoadAceg` is diagnostic-only and should not participate in GPU production runs. Keeping it allocated and sorted changes the GPU array layout and leaves a conditional global write in the interaction kernel path, which is enough to perturb the sensitive q0 Terzaghi profile at later output times.

The current preferred fix is:

- keep hydromechanics forcing `MdbcFastSingle=false` during config parsing, so the printed/default state is unambiguous;
- remove GPU `HydroMechLoadAceg` allocation/sort/pass-through/output;
- keep the actual pore-pressure and stress-rate arrays unchanged.

The validation data are stored under:

- `tests/figures/gpu_validation/gpu_noloadace_noflag_Tv025_summary.csv`
- `tests/figures/gpu_validation/gpu_noloadace_noflag_Tv025_profiles.png`

## Follow-up correction: layout/write-path split

Later tests showed that the earlier "remove `HydroMechLoadAceg`" conclusion is not sufficiently precise and should not be used as the final fix without the full validation chain.

Additional short `Tv=0.25` tests with the same standard q0 setup found:

| Case | GPU array allocation/sort for `HydroMechLoadAceg` | force-kernel `HydroMechLoadAceg` argument | VTK output field | RMS profile error (kPa) | Note |
| --- | --- | --- | --- | ---: | --- |
| `gpu_layoutalloc_Tv025` | yes | `NULL` | no | 0.134197 | Allocation/layout alone did not recover the baseline. |
| `gpu_layoutforceace_Tv025` | yes | non-null | no | 0.034680 | Short run recovered the CPU/old-GPU baseline at `Tv=0.25`. |

The `gpu_layoutforceace_Tv025` run also reported:

- `mDBC-FastSingle=False`
- initial memory matching the old good layout: CPU `468866`, GPU `894496`
- final memory matching the old good layout: CPU `645414`, GPU `1265144`
- no `HydroMechLoadAce` field in the generated particle VTK.

Updated interpretation:

- the mDBC fast-single path is still not the active cause;
- array allocation by itself is not enough to explain the good result;
- the old good short-time behavior is reproduced only when the force-kernel side `HydroMechLoadAceg` write path is also preserved, while keeping the field out of saved VTK output.

This is only a short-run result. A full `Tv=1` GPU run with the same code/config is required before treating this as the final divergence point.

## Full `Tv=1` reproduction

The same `layoutforceace` code/config was then run to full `Tv=1`:

- config: `tests/configs/gpu_validation/CaseTCq0_gpu_layoutforceace_Tv1_Def.xml`
- output: `tests/outputs/gpu_validation/CaseTCq0_gpu_layoutforceace_Tv1_out`
- summary: `tests/figures/gpu_validation/gpu_layoutforceace_Tv1_vs_cpu_summary.csv`
- profiles plot: `tests/figures/gpu_validation/gpu_layoutforceace_Tv1_vs_cpu_profiles.png`
- metrics plot: `tests/figures/gpu_validation/gpu_layoutforceace_Tv1_vs_cpu_metrics.png`

Runtime checks:

- solver finished with `code=0`;
- `mDBC-FastSingle=False`;
- 201 `PartFluid_*.vtk` snapshots were generated;
- initial memory was CPU `468866`, GPU `894496`;
- final memory was CPU `645414`, GPU `1265144`;
- generated VTK files did not contain a `HydroMechLoadAce` output field.

CPU/GPU profile RMS comparison:

| Tv | CPU RMS (kPa) | GPU RMS (kPa) | GPU/CPU |
| ---: | ---: | ---: | ---: |
| 0.005 | 0.047672 | 0.047699 | 1.001 |
| 0.05 | 0.020892 | 0.020883 | 0.9995 |
| 0.1 | 0.019510 | 0.019506 | 0.9998 |
| 0.25 | 0.034353 | 0.033752 | 0.9825 |
| 0.4 | 0.025108 | 0.024554 | 0.9779 |
| 0.5 | 0.015961 | 0.015592 | 0.9768 |
| 0.7 | 0.010882 | 0.011075 | 1.018 |
| 1.0 | 0.013881 | 0.013948 | 1.005 |

Conclusion after full reproduction:

- the good short result is reproducible through a full `Tv=1` run;
- the divergence is tied to the GPU `HydroMechLoadAceg` force-kernel write path being removed or passed as `NULL`;
- the saved `HydroMechLoadAce` VTK field should remain disabled because the field is diagnostic-only and was associated with the earlier output clutter;
- the next production candidate is therefore to keep GPU allocation/sort/reset and pass `HydroMechLoadAceg` to the force kernel, but keep top-load writes and saved output disabled.

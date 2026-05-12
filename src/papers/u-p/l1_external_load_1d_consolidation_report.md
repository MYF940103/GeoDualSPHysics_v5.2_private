# L1 external-load 1D consolidation baseline

## Objective

L1 adds a first production-style external-load 1D consolidation baseline before moving to Cryer/triaxial/slope cases. The purpose is not to reproduce all artificial-viscosity or damping combinations from the paper, but to prove that the current u-pw PR path can accept an XML-native external load and remain stable.

## External-load route

The case uses native DualSPHysics `AccInput`, not source-side `TopLoad*`.

- Bulk soil: `mkfluid=0`
- External-load layer: `mkfluid=1`
- Acceleration history: `ExternalLoadAcc_L1.csv`
- AccInput scope: `<accinput mkfluid="1">`
- Top drainage is activated after the load ramp at `t=0.05 s`.

No `TopLoadEnabled`, `TopLoad`, `TopLoadThickness`, `TopLoadRampStart`, or `TopLoadRampEnd` parameters are present in the L1 XML.

## Workflow files

Directory:

`examples/u-pw/01_1D_Consolidation/experiments/ExternalLoad_L1_Baseline/`

Files:

- `Case1DConsolidation_PR_ExternalLoad_L1_Def.xml`
- `ExternalLoadAcc_L1.csv`
- `xCase1DConsolidation_PR_ExternalLoad_L1_win64_CPU_release.bat`
- `xCase1DConsolidation_PR_ExternalLoad_L1_win64_GPU_release.bat`
- `analyze_l1_external_load.py`
- `l1_external_load_setup_notes.md`

Both BAT files follow the example-style workflow:

`GenCase -> DualSPHysics Release -> PartVTK`

## Baseline setup

Key parameters:

- `HydromechCoupling=1`
- `PorePressureModel=1`
- `PorePressureBoundaryOperator=0`
- `PorePressureFeedback=1`
- `PorePressureFeedbackMode=1`
- `PorePressureFeedbackOperator=1`
- `PorePressureShepard=1`
- `PorePressureShepardInterval=10`
- `PorePressureShepardMode=1`
- `HydromechDamping=1`
- `HydromechDampingXi=0.05`
- `PorePressureDtSafety=0.20`
- `PorePressureTopDrained=1`
- `PorePressureTopDrainedStartTime=0.05`
- `PorePressureBottomNoFlux=1`
- `SavePorePressure=1`
- `TimeMax=0.2 s`
- `TimeOut=0.005 s`

## GPU baseline result

GPU Release was run as the primary baseline smoke. CPU Release BAT is provided for manual parity runs, but CPU was not executed in this step because the 0.2 s GPU run already required about 825 s and CPU cost is expected to be substantially higher.

| Metric | Value |
|---|---:|
| code | 0 |
| excluded | 0 |
| runtime | 824.707 s |
| steps | 209,747 |
| frames | 41 |
| physical time | 0.2 s |
| peak `ExcessPorePress` maxAbs | 219.358 Pa |
| final `ExcessPorePress` maxAbs | 0.0146 Pa |
| final bottom excess mean | 2.56e-4 Pa |
| final top-drained excess maxAbs | 4.79e-11 Pa |
| final bottom no-flux proxy | -2.54e-7 Pa |
| final max velocity | 1.66e-8 m/s |

The AccInput configuration was detected in the GPU log, and the top drained boundary activated at `t=0.0500004 s`. The bottom no-flux correction remained stable.

## Response

The native external load induced a measurable pore-pressure response, with the excess envelope peaking at about 219 Pa and then dissipating after the top-drained boundary became active. Velocity and settlement remained small and bounded, with no particle exclusion or pressure blow-up.

## Figures and metrics

Retained outputs:

- `l1_external_load_frame_metrics.csv`
- `l1_external_load_case_summary.csv`
- `figures/l1_bottom_excess_time.*`
- `figures/l1_excess_max_mean_time.*`
- `figures/l1_settlement_time.*`
- `figures/l1_velocity_max_time.*`
- `figures/l1_excess_profiles.*`
- `figures/l1_porepress_profiles.*`
- `figures/l1_boundary_checks.*`

## Limitations

- This is a baseline external-load smoke, not a strict full paper reproduction.
- The load is applied as acceleration to a material top layer, not through a physical loading plate.
- No artificial-viscosity or damping sensitivity was performed.
- No analytical comparison is claimed in L1.

## Recommendation

L1 confirms that the XML/native AccInput route can replace the removed source-side TopLoad path for a baseline external-load 1D consolidation case. Parameter sensitivity and stricter external-load reproduction can remain deferred; the workflow is sufficient to proceed to Cryer audit/development next.

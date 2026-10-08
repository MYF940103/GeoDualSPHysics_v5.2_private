# q0 k=1e-2 Stage2 dissipation from best Stage1 restart

Date: 2026-07-06

## Setup

Formal Stage2 dissipation was run from the best Stage1 restart candidate identified in `q0_stage1_stabilization_20260702.md`.

- Stage1 source: `CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t010`
- Restart snapshot: `Part_0138`
- Stage1 restart time: `0.069 s`
- Stage1 settings behind the restart: `DtFixed=1e-7 s`, `SoilDampingCoef=0.02`
- Stage2 case: `CaseTzq0_s2p0138_k1em2`
- Stage2 hydraulic conductivity: `HydraulicConductivity=1e-2 m/s`
- Stage2 drainage: enabled from `t=0`
- Stage2 top load: `TopVertical`, `q0=10000 Pa`, `RampTime=0`
- Stage2 pore Shepard regularization: disabled
- Stage2 duration: `0.364371428571429 s`, corresponding to `Tv=1`
- Stage2 output interval: `0.00182185714285714 s`, corresponding to `Delta Tv=0.005`

The run used `-partbegin:138:0` from `tests/outputs/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t010_out/data`.

## Run status

The CPU run completed successfully.

- Final output: `Part_0200`
- Initial particles: `1040`
- Fluid particles in VTK outputs: `1000`
- Excluded particles: `0`
- Solver runtime: `8557.5 s`
- Simulation steps: `3643715`

## Main results

Final `Tv=1` result:

- Numerical degree of consolidation: `U=0.920759`
- Theoretical degree of consolidation: `U=0.931260`
- Final mean excess pore pressure: `0.792408 kPa`
- Final pore-pressure profile RMS: `0.113547 kPa`
- Final max speed: `0.00231691 m/s`

Target snapshots:

| target Tv | snapshot | actual Tv | U num | U theory | profile RMS |
|---:|---|---:|---:|---:|---:|
| 0 | `PartFluid_0000.vtk` | 0 | 0.001911 | 0.000844 | 2.13198 kPa |
| 0.005 | `PartFluid_0001.vtk` | 0.005 | 0.660803 | 0.079788 | 6.03781 kPa |
| 0.05 | `PartFluid_0010.vtk` | 0.05 | 0.282527 | 0.252313 | 0.360361 kPa |
| 0.1 | `PartFluid_0020.vtk` | 0.1 | 0.381236 | 0.356823 | 0.268682 kPa |
| 0.25 | `PartFluid_0050.vtk` | 0.25 | 0.568331 | 0.562234 | 0.069397 kPa |
| 0.4 | `PartFluid_0080.vtk` | 0.4 | 0.693773 | 0.697882 | 0.048797 kPa |
| 0.5 | `PartFluid_0100.vtk` | 0.5 | 0.756475 | 0.763950 | 0.084326 kPa |
| 0.7 | `PartFluid_0140.vtk` | 0.7 | 0.845109 | 0.855893 | 0.120442 kPa |
| 1.0 | `PartFluid_0200.vtk` | 1.0 | 0.920759 | 0.931260 | 0.113547 kPa |

## Interpretation

The two-stage restart improves the mid-to-late dissipation profile substantially: after the initial transient, the numerical U-Tv curve and pore-pressure profiles track Terzaghi theory well from about `Tv=0.05` onward.

However, the first formal output at `Tv=0.005` still shows a strong dynamic drainage transient. The numerical mean excess pore pressure drops too far at `PartFluid_0001`, giving `U=0.660803` against the theoretical `0.079788`, before rebounding toward the theoretical consolidation curve by `Tv=0.05`. Therefore the two-stage workflow does not fully solve the very earliest `Tv=0.005` response, but it does produce a good complete dissipation calculation for `Tv>=0.05`.

## Files

- Stage2 XML: `tests/configs/CaseTzq0_s2p0138_k1em2_Def.xml`
- Stage2 output: `tests/outputs/CaseTzq0_s2p0138_k1em2_out`
- Stage2 history CSV: `tests/figures/CaseTzq0_s2p0138_k1em2/CaseTzq0_s2p0138_k1em2_stage2_history.csv`
- Stage2 target CSV: `tests/figures/CaseTzq0_s2p0138_k1em2/CaseTzq0_s2p0138_k1em2_stage2_targets.csv`
- Stage2 summary: `tests/figures/CaseTzq0_s2p0138_k1em2/CaseTzq0_s2p0138_k1em2_stage2_summary.txt`
- Stage2 U/RMS/speed plot: `tests/figures/CaseTzq0_s2p0138_k1em2/CaseTzq0_s2p0138_k1em2_stage2_history.png`
- Stage2 profile plot: `tests/figures/CaseTzq0_s2p0138_k1em2/CaseTzq0_s2p0138_k1em2_stage2_profiles.png`

## Next check

If the earliest `Tv=0.005` point is still required for publication-quality agreement, the next focused test should isolate the Stage2 activation transient. Candidate changes are a short Stage2 drainage ramp, a finer Stage2 `DtFixed` only for the first few outputs, or retaining pore-pressure Shepard regularization briefly at the beginning of Stage2. Keep the current `Part_0138` restart as the baseline because its mid-to-late dissipation behavior is already good.

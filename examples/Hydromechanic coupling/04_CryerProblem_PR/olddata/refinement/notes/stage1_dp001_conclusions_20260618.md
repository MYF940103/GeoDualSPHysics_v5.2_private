# Stage1 dp001 single-layer load test, 2026-06-18

Purpose: rerun Cryer Stage 1 with `Dp=0.001` after removing the temporary
three-layer loading implementation, using the restored single-layer
area-normalized `SphereNormal` load.

Configuration:
- Source XML template: `../../CaseCryerProblem_PR_Stage1_Def.xml`
- Generated XML: `CaseCryerStage1_dp001_l1_Def.xml`
- Output folder: `out/dp001_l1`
- Solver: `DualSPHysics5.2_GEO_win64.exe`
- `HydroMechDrainage=0`
- `HydraulicConductivity=0`
- `SoilDampingCoef=0.02`
- `HydroMechTopLoadMode=SphereNormal`
- `HydroMechTopLoadQ0=10000`
- `HydroMechTopLoadRampTime=0.005`
- `DtFixed=1e-6`
- `TimeMax=0.006`

Result:
- Initial particles: 545948 total, including 545940 fluid/free particles.
- SphereNormal load used 31685 surface particles.
- Area diagnostics were consistent:
  - `A_sum=0.0314159`
  - `4*pi*R_eff^2=0.0314159`
  - residual `|sum(A_i*n_i)|/sum(A_i)=2.91328e-15`
  - acceleration range `[4721.47, 4721.47]`
- Runtime: 7664.48 s on GPU.
- Final state is invalid:
  - excluded particles: 545849
  - excluded by density: 331526
  - excluded by velocity: 50948
  - current particles after final step: 99
  - exported final fluid VTK contains only 91 particles.

Conclusion:
This `Dp=0.001`, `DtFixed=1e-6`, `q0=10000`, `ramp=0.005` run cannot be used
to evaluate the center pore pressure because the center particle and nearly
all particles were excluded by the final output time. The single-layer load
diagnostics themselves are balanced, so this failure is a numerical stability
or particle-domain response problem under the refined resolution and current
loading/time-step settings, not a failed force-sum diagnostic.

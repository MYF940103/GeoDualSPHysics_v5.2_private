# Cryer Area-Load Smoke Test Notes

Date: 2026-06-18

## Directory layout

- Test XML and bat files: `area_load_test`
- Solver outputs: `area_load_test/out_smoke/stage1` and `area_load_test/out_smoke/stage2`
- VTK outputs: `out_smoke/stage1/particles` and `out_smoke/stage2/particles`
- Analysis files: `area_load_test/analysis_smoke`

## Run setup

- Particle generation: `setfrdrawmode auto="true"`
- Stage 1: undrained loading, `HydroMechDrainage=0`, `TimeMax=0.006`, `TimeOut=0.002`
- Stage 2: restart from Stage 1, `HydroMechDrainage=1`, `HydraulicConductivity=1e-4`, `TimeMax=0.012`, `TimeOut=0.001`
- Load mode: `HydroMechTopLoadMode=SphereNormal`
- Area-normalized load: `A_i = 4*pi*R_eff^2/N_surface`, `a_i = -q0*A_i*n_i/m_i`
- Soil damping: `SoilDampingCoef=0.02`

## SphereNormal load diagnostics

Stage 1:
- Surface particles: 3630
- `R_eff`: 0.05 m
- `A_sum`: 0.0314159 m2
- `4*pi*R_eff^2`: 0.0314159 m2
- `A_i`: 8.65453e-06 m2
- Scalar force at `q0=10000`: 314.159 N
- Residual `|sum(A_i*n_i)|/sum(A_i)`: 2.75482e-4
- Load acceleration range: [1526.37, 1526.37] m/s2

Stage 2:
- Surface particles: 3630
- `R_eff`: 0.0499997 m
- `A_sum`: 0.0314156 m2
- `4*pi*R_eff^2`: 0.0314156 m2
- `A_i`: 8.65443e-06 m2
- Scalar force at `q0=10000`: 314.156 N
- Residual `|sum(A_i*n_i)|/sum(A_i)`: 2.69989e-4
- Load acceleration range: [1526.36, 1526.36] m/s2

## Result summary

- Both solver stages finished with `code=0`.
- Stage 1 and Stage 2 VTK files were exported in the unified `out_smoke` folder.
- No solver access violation was observed in this Release GPU run.
- The only access warning came from deleting `analysis_smoke` while the parent PowerShell process was redirecting stdout/stderr into that same directory. The bat files were updated to keep the analysis directory and only remove this test's CSV/PNG/JSON outputs.

Postprocess summary:
- Snapshots: 13
- Free-surface count: 3630
- Center sample count: 84
- Final `p/q0`: 1.02526
- Final analytical `p/q0`: 1.03809
- Final absolute error: 0.01283
- Numerical peak `p/q0`: 1.03692 at `t=0.006 s`
- Analytical value at the numerical peak time: 1.03809

## Interpretation

The area-normalized spherical pressure discretization gives a balanced total surface force and a small residual resultant force. In this short smoke run, Stage 2 rapidly approaches the analytical center pressure level, but Stage 1 is still too short to be considered a fully equilibrated undrained loading stage. The next formal run should keep the same shallow directory structure and use the longer Stage 1 settings in `xCaseCryerProblem_AreaLoad_win64_GPU.bat`.

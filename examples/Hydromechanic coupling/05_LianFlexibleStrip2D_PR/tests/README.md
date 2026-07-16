# Lian 2023 Flexible Strip 2D Test Data

This directory keeps temporary validation assets separate from the release XML/BAT files in the case root.

- `outputs/`: GenCase, DualSPHysics, raw `data/`, and VTK `particles/` output.
- `logs/`: GenCase, solver, PartVTK, and postprocess logs.
- `configs/`: generated variant XML files, if parameter sweeps are needed.
- `figures/`: cross-run comparison figures.
- `scripts/`: helper run and postprocess scripts.
- `notes/`: preserved conclusions from previous attempts.

Current formal case root files:

- `../CaseLianFlexibleStrip2D_PR_Def.xml`
- `../xCaseLianFlexibleStrip2D_PR_win64_GPU.bat`

Current retained setup:

- Domain: `20 m x 10 m`, `dp=0.1 m`.
- Strip footing: hard-coded Lian mode `HydroMechTopLoadMode=4`, `x=[0,1.25] m`, top surface `z=10 m`.
- Drainage: open top surface outside the strip starts after the 1 s ramp; the strip contact remains impermeable.
- Boundary: mDBC free-slip command path, matching the side free-slip setting and the stable Yao 2-D setup.
- Pore-pressure regularization and density diffusion are disabled.

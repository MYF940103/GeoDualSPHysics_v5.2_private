# CryerProblem_PR

This case validates the u-pw pore-pressure-rate formulation on Cryer's problem: a saturated poroelastic sphere with a drained exterior surface and a uniform inward normal pressure.

The active verification path uses `HydroMechInitMode=0` (`None`), `HydroMechTopLoadMode=3` (`FlexibleConfinement`) for the sustained confining pressure, and `HydroMechDrainage=1` to drain tracked exterior free-surface particles. The direct uniform pore-pressure initialization path is not used because it was not paired with a consistent 3D effective-stress and displacement initialization.

The formal case is now a two-stage restart:

1. Stage 1 keeps the sphere undrained, applies the spherical normal pressure `p0`, and lets the pore pressure, effective stress, displacement, and velocity fields settle.
2. Stage 2 restarts from the Stage 1 state, opens the `FreeSurface` drained boundary, and treats the restart time as analytical `t=0`.

The retained validation record is the completed `dp=0.003`, `k=1e-4 m/s` full-cycle conclusion in `refinement/notes/cleanup_conclusions_20260617.md`. The formal XML files use `setfrdrawmode auto="true"` for the sphere generation as requested. The FrDraw surface is geometrically cleaner, but the retained refinement notes show that direct FrDraw generation can make the volumetric distribution less favorable than regular `drawsphere`; keep this in mind when interpreting the decay-stage error.

Run on Windows GPU release:

```bat
xCaseCryerProblem_PR_win64_GPU.bat
```

CPU note:

`FlexibleConfinement` is currently implemented in the GPU validation path; use the GPU batch file for this case.

Formal outputs are kept under one directory:

- `CaseCryerProblem_PR_out/stage1/data`
- `CaseCryerProblem_PR_out/stage1/particles`
- `CaseCryerProblem_PR_out/stage2/data`
- `CaseCryerProblem_PR_out/stage2/particles`
- `CaseCryerProblem_PR_out/figures`

The PartVTK command in both bat files requests:

```text
+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress
```

Open `CaseCryerProblem_PR_out/stage1/particles/PartFluid_*.vtk` or `CaseCryerProblem_PR_out/stage2/particles/PartFluid_*.vtk` in ParaView and inspect `FSNormal` together with `FSType` to check the tracked free-surface normals.

Expected postprocess outputs:

- `CaseCryerProblem_PR_out/figures/cryer_center_pressure.png`
- `CaseCryerProblem_PR_out/figures/cryer_center_pressure.csv`
- `CaseCryerProblem_PR_out/figures/cryer_center_pressure_summary.json`

The geometry includes a tiny fixed boundary block far outside the kernel support of the sphere. It is only a solver guard for code paths that expect at least one boundary particle and does not interact with the poroelastic sphere.

Exploratory tests are documented under `refinement/notes/`. Bulky temporary
outputs are intentionally not retained in the release case directory.

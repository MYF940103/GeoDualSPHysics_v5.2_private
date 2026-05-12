# C5d Curved Drained Boundary Quadrature

This directory contains targeted CPU-only tests for the C5d Cryer boundary
quadrature refinement. These cases are not final Cryer Figure 7B reproduction.

The tested `CurvedDrainedBoundaryMode` values are:

- `0`: old first-order spherical Dirichlet ghost;
- `1`: strengthened image Dirichlet ghost;
- `2`: diagnostic material surface drained clamp after pore-pressure update.
- `3`: multi-sample spherical Dirichlet boundary quadrature.

Compression cases use the same coarse sphere as C5/C5b with `p0=50 Pa`,
`SoilConstitutiveModel=0`, `FlexibleConfiningStress=1`,
`PorePressureBoundaryOperator=3`, and `HydraulicElevationSource=0`.

Pressure-only diffusion cases use uniform initial excess pressure and no
confining stress. They are included to isolate drained boundary behavior from
mechanical loading.

Run all tests manually with:

```bat
xCaseCryer_PR_StrictSphere_C5d_BoundaryQuadrature_win64_CPU_release.bat
```

The BAT runs GenCase, CPU Release, PartVTK, and the local Python analysis
script. It does not run GPU.

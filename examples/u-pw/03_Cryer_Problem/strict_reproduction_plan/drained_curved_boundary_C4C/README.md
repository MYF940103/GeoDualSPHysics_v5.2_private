# C4-C Drained Curved Pore-Pressure Boundary Smokes

This folder contains CPU-only short smokes for the experimental
`PorePressureBoundaryOperator=3` curved drained pore-pressure boundary. These
cases are not strict Cryer reproductions.

Cases:

- `CaseC4C_CurvedDrained_Zero_Def.xml`: zero-pressure/no-source consistency.
- `CaseC4C_CurvedDrained_Diffusion_Def.xml`: pressure-only uniform excess
  diffusion toward a drained spherical exterior.
- `CaseC4C_CurvedDrained_Compression_Def.xml`: small flexible confining stress
  compression plus drained spherical exterior.

Run:

```bat
xRun_C4C_DrainedCurved_CPU_release.bat
```

The BAT performs:

`GenCase -> DualSPHysics CPU Release -> PartVTK -> Python summary`

The retained outputs are XML/BAT, scripts, CSV summaries, and lightweight
figures. Heavy raw simulation output folders should be deleted before commit.

GPU is intentionally unsupported for this boundary prototype.

Latest CPU Release smoke status:

- zero/no-source: `code=0`, `excluded=0`;
- pressure-only diffusion: `code=0`, `excluded=0`;
- compression + drained boundary: `code=0`, `excluded=0`;
- compression smoke keeps `Kplastic=0`;
- the diffusion smoke shows surface excess pressure decreasing over the short
  run.

The current PR path still requires positive `HydraulicGravity` for hydraulic
scaling, so these smokes are boundary/operator checks rather than gravity-free
strict Cryer reproduction.

# C5f Boundary-Particle Weighting

CPU-only Cryer drained-boundary weighting refinement.

This package compares `CurvedDrainedBoundaryMode=4` with three weighting
choices:

- `CurvedDrainedBoundaryWeighting=0`: raw boundary-particle volume weighting
  from C5e;
- `CurvedDrainedBoundaryWeighting=1`: Adami-style local partition
  normalization using `S_m + S_b`;
- `CurvedDrainedBoundaryWeighting=3`: diagnostic missing-support capped
  weighting.

All cases are coarse short smokes. They are not strict Cryer Figure 7B
validation and they do not use GPU.

Run:

```bat
xCaseCryer_PR_StrictSphere_C5f_BoundaryParticleWeighting_win64_CPU_release.bat
```

The BAT runs:

- pressure-only diffusion, raw / normalized / capped;
- compression with `FlexibleConfiningStress`, raw / normalized / capped;
- Python postprocessing for metrics and figures.

Raw solver outputs are temporary and should be removed before committing.

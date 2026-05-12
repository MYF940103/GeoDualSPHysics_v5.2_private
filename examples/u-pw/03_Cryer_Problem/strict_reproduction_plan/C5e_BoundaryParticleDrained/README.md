# C5e Boundary-Particle Drained Boundary Prototype

This directory contains CPU-only Cryer boundary-coupling smokes for
`CurvedDrainedBoundaryMode=4`. These cases are not final Cryer Figure 7B
reproductions.

Mode 4 selects dummy `mkbound` particles on an exterior spherical shell, assigns
the prescribed drained hydraulic state `p_w=0`, projects their hydraulic
quadrature sites to the drained spherical surface, and lets those boundary
particles contribute to `LapPorePress` and `LapZ`. Material particles are not
clamped.

The test matrix is intentionally small:

- `Mode3Shell`: old material-side spherical quadrature with the same geometry.
- `Mode4BoundaryParticles`: boundary-particle prescribed Dirichlet state.
- `DiffusionMode3Shell`: pressure-only diffusion control.
- `DiffusionMode4BoundaryParticles`: pressure-only diffusion with mode 4.

Run all CPU Release tests manually with:

```bat
xCaseCryer_PR_StrictSphere_C5e_BoundaryParticleDrained_win64_CPU_release.bat
```

The BAT runs GenCase, CPU Release, PartVTK, and the local analysis script. It
does not run GPU.

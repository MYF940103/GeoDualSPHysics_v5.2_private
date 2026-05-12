# C4-D Hydraulic No-Elevation Smokes

These are short CPU-only checks for the `HydraulicElevationSource` switch.
They are not strict Cryer reproductions.

Cases:

- `CaseC4D_SourceOn_Regression_Def.xml`: legacy source-on regression with the
  curved drained operator active.
- `CaseC4D_NoElevation_Diffusion_Def.xml`: pressure-only diffusion with
  `HydraulicElevationSource=0`; `HydraulicGravity=(0,0,-9.81)` is kept only for
  `k/(rho_w g)` hydraulic scaling.
- `CaseC4D_NoElevation_Compression_Def.xml`: short flexible-confining-stress
  compression plus curved drained boundary with no elevation source.

Run:

```bat
xRun_C4D_HydraulicNoElevation_CPU_release.bat
```

The BAT runs `GenCase`, `DualSPHysics5.2CPU_win64.exe`, `PartVTK`, and the
lightweight analysis scripts. Generated raw solver outputs should be cleaned
before committing; the retained files are XML/BAT/scripts/CSV/figures.

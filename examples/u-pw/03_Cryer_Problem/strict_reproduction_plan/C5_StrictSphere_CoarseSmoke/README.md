# C5 Strict-Sphere Cryer Coarse Smoke

This directory contains a coarse CPU-only integration smoke for the strict Cryer route.
It is not a final Fig. 7B reproduction and should not be used as a quantitative benchmark.

The smoke combines:

- `SoilConstitutiveModel=0` linear elastic skeleton.
- `FlexibleConfiningStress=1` with a small positive compressive `ConfiningStressP0`.
- `PorePressureBoundaryOperator=3` plus `PorePressureCurvedDrained=1`.
- `HydraulicElevationSource=0`, with `HydraulicGravity` retained only for hydraulic scaling.

Run manually with:

```bat
xCaseCryer_PR_StrictSphere_C5_CoarseSmoke_win64_CPU_release.bat
```

The BAT runs the 0.006 s smoke, then generates lightweight CSV metrics and figures.
Exploratory extensions beyond this window showed coarse free-sphere oscillation and eventual particle exclusion, so they are not part of the passing smoke.
Generated heavy solver outputs are not intended to be committed.

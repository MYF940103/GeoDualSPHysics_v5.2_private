# C5b Strict-Sphere Refinement

This directory performs a small targeted refinement of the C5 coarse Cryer
smoke. It is not a Poisson-ratio sweep, not a resolution study, and not a
Figure 7B quantitative validation.

Variants:

- `Baseline`: C5 retained setup, `p0=50 Pa`, ramp end `0.0005 s`, `TimeMax=0.006 s`.
- `SlowRamp`: same `p0`, ramp end `0.005 s`, `TimeMax=0.012 s`.
- `LowerP0`: `p0=10 Pa`, ramp end `0.0005 s`, `TimeMax=0.006 s`.
- `LongSlowRamp`: `p0=50 Pa`, ramp end `0.005 s`, `TimeMax=0.05 s`.

Run manually with:

```bat
xCaseCryer_PR_StrictSphere_C5b_Refinement_win64_CPU_release.bat
```

The BAT runs CPU Release only and then generates CSV metrics plus lightweight
figures. Heavy solver outputs are not intended to be committed.

# C4-B4 Free-Sphere Flexible Confining Stress Smoke

This folder contains CPU-only traction-smoke cases for the experimental
`FlexibleConfiningStress` source. These are not strict Cryer reproductions.

Cases:

- `CaseFlexConf_C4B4_FreeSphere_NoLoad_Def.xml`: free-sphere no-load regression.
- `CaseFlexConf_C4B4_FreeSphere_Ramp_Def.xml`: free sphere with `p0=50 Pa`
  ramped over `0.0005 s`.
- `CaseFlexConf_C4B4_FreeSphere_StrongerOptional_Def.xml`: optional `p0=100 Pa`
  draft, not run by default.

Run:

```bat
xRun_C4B4_FreeSphere_CPU_release.bat
```

The BAT performs:

`GenCase -> DualSPHysics CPU Release -> PartVTK -> Python summary`

The retained outputs are CSV summaries and lightweight figures. Heavy raw
simulation output folders should be deleted before commit.

Run status:

- no-load CPU smoke: `code=0`, `excluded=0`;
- ramped `p0=50 Pa` CPU smoke: `code=0`, `excluded=0`;
- ramped smoke final surface radial velocity mean: `-6.28e-04 m/s`;
- ramped smoke final net/absolute force: `1.94e-08`;
- ramped smoke final `Kplastic`: `0`.

This folder is a traction-source smoke package only. It is not a strict Cryer
simulation and does not include the drained curved pore-pressure boundary.

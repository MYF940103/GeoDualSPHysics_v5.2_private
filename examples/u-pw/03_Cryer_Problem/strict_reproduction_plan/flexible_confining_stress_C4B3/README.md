# C4-B3 Flexible Confining Stress CPU Smoke

This directory contains minimal CPU-only smoke cases for the flexible confining
stress source. These are not strict Cryer simulations.

Cases:

- `CaseFlexConf_C4B3_NoLoad_Def.xml`: default-off no-load regression.
- `CaseFlexConf_C4B3_Sign_Def.xml`: immediate small compressive load.
- `CaseFlexConf_C4B3_Ramp_Def.xml`: same load with a short linear ramp.

Run:

```bat
xRun_C4B3_FlexibleConfiningStress_CPU_release.bat
```

The BAT performs:

`GenCase -> DualSPHysics CPU Release -> PartVTK -> Python summary`

Heavy output folders are not intended for commit. Keep the XML, BAT, scripts,
CSV summaries, and figures only.

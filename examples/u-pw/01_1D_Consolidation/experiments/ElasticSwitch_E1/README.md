# E1 Elastic Skeleton Switch Smoke

This directory contains short regression cases for the `SoilConstitutiveModel`
soil switch.

## Cases

| XML | Purpose |
| --- | --- |
| `CaseElasticSwitch_E1_Elastic_Def.xml` | `SoilConstitutiveModel=0`; linear elastic skeleton, DP return mapping and softening bypassed. |
| `CaseElasticSwitch_E1_DP_Def.xml` | `SoilConstitutiveModel=1`; explicit Drucker-Prager backward-compatibility smoke. |
| `CaseElasticSwitch_E1_SofteningLegacy_Def.xml` | Legacy `Softening=1` without explicit `SoilConstitutiveModel`; parser should map to model 2. |

The geometry and AccInput route are copied from the L1 external-load baseline,
but the time window is shortened to `TimeMax=0.005 s`. These are smoke tests,
not paper-scale Terzaghi or Cryer reproductions.

## Launchers

- `xCaseElasticSwitch_E1_Elastic_win64_CPU_release.bat`
- `xCaseElasticSwitch_E1_Elastic_win64_GPU_release.bat`
- `xCaseElasticSwitch_E1_DP_win64_CPU_release.bat`
- `xCaseElasticSwitch_E1_SofteningLegacy_win64_CPU_release.bat`

Each launcher follows the usual example workflow:

```text
GenCase -> DualSPHysics Release -> PartVTK
```

The helper `analyze_e1_elastic_switch.py` scans the CSV outputs and writes
`e1_elastic_switch_summary.csv`, including `Kplastic` checks for elastic runs.

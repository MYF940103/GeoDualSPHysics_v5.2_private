# M3d2 MCC Return Robustness

This directory contains the feedback-off CPU diagnostics used to audit
`MccReturnStatus=-3` in the M3d mild-yield MCC platen triaxial smoke.

No solver source is changed by these cases.

## Cases

- `CaseM3d2_MCCMildBaseline`: M3d mild-yield rerun.
- `CaseM3d2_MCCMildSlowerHalfVelocity`: half top-platen velocity with longer
  runtime for similar displacement.
- `CaseM3d2_MCCMildEarlyStop`: short time-window check.
- `CaseM3d2_MCCMildTightReturn`: tighter tolerance and higher max iterations.

All cases keep:

- `SoilConstitutiveModel=3`;
- `PorePressureFeedback=0`;
- explicit top/bottom platen workflow;
- selected lateral `FlexibleConfiningStress`;
- `SaveMccState=1`;
- `SavePlatenReactionDiagnostics=1`.

## Outputs

Run:

```powershell
py -3 make_m3d2_cases.py
cmd /c xRun_CaseM3d2_MCCMildBaseline_win64_CPU_release.bat
cmd /c xRun_CaseM3d2_MCCMildSlowerHalfVelocity_win64_CPU_release.bat
cmd /c xRun_CaseM3d2_MCCMildEarlyStop_win64_CPU_release.bat
cmd /c xRun_CaseM3d2_MCCMildTightReturn_win64_CPU_release.bat
py -3 analyze_m3d2_mcc_return_robustness.py
```

Retained CSVs and figures summarize return status, failed particle locations,
MCC state evolution, reaction, stress path, pore pressure, DivVel, and velocity.


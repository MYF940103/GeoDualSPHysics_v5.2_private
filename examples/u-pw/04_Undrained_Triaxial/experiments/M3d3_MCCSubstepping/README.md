# M3d3 MCC Substepping

CPU-only diagnostic cases for opt-in Modified Cam Clay constitutive substepping and admissibility guards. These cases keep `PorePressureFeedback=0` and reuse the explicit platen plus lateral confinement workflow from M3d/M3d2.

Cases:

- `CaseM3d3_MCCMildBaseline`: old single-step return behavior.
- `CaseM3d3_MCCMildFixedSubsteps4`: fixed four local constitutive substeps with admissibility guard.
- `CaseM3d3_MCCMildAdaptiveSubsteps16`: adaptive retry on failed return, up to 16 substeps, with admissibility guard.
- `CaseM3d3_MCCMildHalfSpeedAdaptive`: optional half-speed adaptive diagnostic.

Run `python make_m3d3_cases.py` to regenerate XML/BAT files, then run the CPU Release BAT files. Run `python analyze_m3d3_mcc_substepping.py` after the solver runs to regenerate CSV metrics and figures.

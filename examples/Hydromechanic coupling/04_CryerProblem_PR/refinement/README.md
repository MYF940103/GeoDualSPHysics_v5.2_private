# Cryer refinement notes

This folder keeps only compact conclusions from exploratory Cryer tests.
Large temporary outputs, generated particles, solver logs, and test-only XML/BAT
files are removed after their conclusions are recorded.

Retained notes are in `notes/`.

Current baseline for further Cryer debugging:

- Use `dp=0.003` as the practical test resolution.
- Use the formal two-stage path: undrained loading first, then drained restart.
- Use `HydroMechTopLoadMode=3` (`FlexibleConfinement`) as the current Cryer loading baseline.
- The main unresolved issue is the Stage1 undrained pore-pressure distribution:
  surface pressure remains too high and center pressure too low, even after
  increasing resolution to `dp=0.002`.

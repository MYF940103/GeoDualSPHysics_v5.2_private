# Cryer refinement notes

This folder contains historical exploratory Cryer tests, not just conclusion
notes. Retained subdirectories include damping, resolution, corrected-load,
and ramp/drainage comparisons, with inputs, logs, and native/derived results.
Do not infer that a dataset was deleted merely because its conclusion was
recorded.

Retained notes are in `notes/`.

## Current entry point versus historical tests

- The current default is the one-stage drained case described in
  [the case README](../README.md): `dp=0.0025`, `k=1e-5`, and
  `HydroMechTopLoadMode=2` (`FlexibleConfinement`).
- The root also retains separate `dp=0.002` closed-ramp Poisson-ratio variants.
- The earlier `dp=0.003` debugging setup and undrained-then-drained restart
  route are historical experiments. Their Stage1 pressure-distribution
  problems must not be read as instructions to replace the current entry point.
- Original dated notes remain unchanged in `notes/`; read them in their
  experiment context rather than as the latest configuration specification.

## Retention

Keep the native BI4 results, selected comparisons, inputs, logs, and notes
until a separate reviewed archive/cleanup decision identifies exact targets.
The scripts in `../support/` refer to these directory names; do not rename or
move a study without checking those dependencies. Some legacy scripts target
experiments whose data are no longer present and are not current launchers.

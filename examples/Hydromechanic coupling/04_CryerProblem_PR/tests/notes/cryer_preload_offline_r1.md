# Cryer preload probe: offline analysis repair

The GPU solver completed normally at 0.00830078125 s, 17408 steps and 69 native saves. The original worker then failed at Part0: all-zero stress columns were inferred as int64 by CSV parsing; adding floating q0 to the integer residual caused a NumPy casting error. No native frame had yet been checked. This is an analysis defect, not a solver failure or equilibrium rejection.

This new support script reads the retained, sealed trajectory only. It promotes pressure and six stress columns explicitly to float64 without changing values, then calls the original frozen inspector and its unchanged five criteria for Parts61-64. It verifies bound inputs, executable and completed outputs before and after analysis. The old script, check/run/status/completion and native files are not edited; no solver, worker or notifier is launched. Original failure evidence is retained.

Outputs use the new `cryer_preload_offline_r1` tag: a 69-row summary CSV and two PNGs under tests/figures, and a new offline check under tests/logs. The full saved history is shown without smoothing, invented intermediate samples or time shifts. Full-load reference lines apply only during holding before drainage; all-sample error histories are labelled full-load target errors, with equilibrium gates used only on the four declared closed states.

Passing original safety is not passing equilibrium, half-step, peak or full physical validation. A missed equilibrium criterion is reported as such, never repaired by relaxing limits or relabelling time. Conditional fluid-content observations are small-strain diagnostics, not exact water mass. The density reference is a diagnostic finite-storage uniform-strain estimate, not a field assignment or proof of a precision cause.

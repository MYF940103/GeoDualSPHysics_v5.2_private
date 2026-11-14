# Late one-step material/volume offline review

Only this note and `tests/support/c08_h18_late_step_review_r1.py` are added. Authoring runs no imports, analysis, builds, physical components, solvers, native readers, VTK, hashes or Git. The root must fully read the helper and separately admit its one offline execution after all three actual components have passed.

The inputs are exactly the existing `c08_h18_late_step_r1_p200/p250/p300` checks, their bound actual calls/build/completions and five CSVs per component. It verifies all105000 actual stage rows,30000 material-shadow rows,15000 trace/balance rows, original5000 IDs at each stage, real source clocks/steps, original per-row arithmetic budgets and reported six-component stress/history bit matches. Status/reason numbers are decoded from the archived `FunSoilMaterial.h` that the actual isolated build consumed, not guessed from enum values.

Each actual CPU call advanced only one original5 us step from an independently restored saved GPU state. The extra material evaluations were performed after all original calls and fed nothing back. Their status names describe **same-input, bit-matched pure-function shadows**, not a hook that recorded the original material-call status. Predictor saved kappa remains kappa_n; candidate shadow kappa must not be described as committed predictor growth. Corrector actual kappa is the returned saved history.

The helper reports Elastic/Smooth/Apex/TensionRepair counts for both stages, all-ID mean/sum/RMS/range of trace reduction and each multiplier, actual saved kappa growth, pressure/kappa/source-FS cohorts, and full-step trace decomposition. The measured identity is

`delta(logJ)-delta(I)/(3K) = log-quadrature - rate-trace-mismatch - trial-addition-roundoff + material-return-trace`.

The existing original arithmetic budgets are checked; no new physical acceptance threshold is introduced. Full-step pressure/J changes, actual pressure-cap counts and per-axis contact displacement/velocity maxima are preserved separately. Source current highest z is only a geometric quantity, never a substitute for the original fixed material top layer. The per-ID table retains all15000 source IDs/positions/pressures/FS/kappa and actual trace terms without clipping.

Fresh outputs are `tests/figures/c08_h18_late_step_review_r1_{summary,cohorts,per_ID}.csv`, `..._{summary,fields}.png` and a terminal `tests/logs/c08_h18_late_step_review_r1.check.json`. Figures use exact original source positions, shared signed ranges and a declared symmetric-log display for very small arithmetic terms. No smoothing, fit, mean-pressure subtraction, pressure cut-off, old result overwrite or native reread is involved.

After root full review, run once:

`D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_late_step_review_r1.py --execution-authorized`

Inspect both PNGs and matching CSVs before a physical decision. Three sampled CPU steps do not reconstruct the full GPU material history, identify the earliest cause of clumping, prove that a tension policy is wrong or justify extrapolating their increments over the entire trajectory. No cap disable, model replacement, PRE/other-psi/half/long run is admitted by this offline review. Existing results and all physical thresholds remain unchanged.

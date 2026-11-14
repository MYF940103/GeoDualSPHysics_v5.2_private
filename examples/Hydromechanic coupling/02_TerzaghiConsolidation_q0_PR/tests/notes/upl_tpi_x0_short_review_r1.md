# Closed CPU X0 short-window offline review

`support/upl_tpi_x0_short_review_r1.py` consumes only already completed unique reads from `upl_tpi_x0_short_r2_original`, `_off` and `_on`, each 151 native states/1040 IDs/22 typed arrays. It invokes no solver, reader, compiler, VTK or Git tool and performs no hash sweep. All pre-existing outputs and failed/partial new reviews are protected.

Root independently reviews and admits each command:

```
python -B tests/support/upl_tpi_x0_short_review_r1.py --phase single --which original --execution-authorized
python -B tests/support/upl_tpi_x0_short_review_r1.py --phase pair_off --execution-authorized
python -B tests/support/upl_tpi_x0_short_review_r1.py --phase single --which off --execution-authorized
python -B tests/support/upl_tpi_x0_short_review_r1.py --phase single --which on --execution-authorized
python -B tests/support/upl_tpi_x0_short_review_r1.py --phase compare --execution-authorized
```

No command authorizes the next command or a new physical run. In particular, the OFF pair is an implementation equivalence test, independent of the retained model's physical performance; its success does not itself admit ON.

## Single-run fields and unchanged gates

Every native state retains its actual saved clock/Step and all 100 initial material layers, ten original X columns per layer. The plot and CSV use total vertical compression `p - sigma_zz`, fixed-material top/bottom settlement `-(z-z0)` and periodic minimum-image X drift. The load number is `sum(native rho * native V * saved LoadAce)` only: it is a saved-state proxy and does not observe the actual force-stage normalization guard.

The original post-.1 s safety limits are evaluated without removing the first sample: the maximum of the 100 layer-mean absolute total-compression errors relative to 10000 Pa must be at most 100 Pa, and the absolute difference between the top two material-layer means must be at most 100 Pa. Additional retained geometry gates require positive soil z and no more than .5 mm of minimum-image lateral drift. No threshold is applied to option differences. Initial and startup states remain in every history, even though the 100-Pa stress gates apply only after .1 s. First failing part/time/layer, all failing layer-sample count and peak location/value are reported separately.

`Q` here is a fully specified descriptive measure: the RMS of the second differences of the 100 material-layer mean total compressions (98 valid interior differences). It has no new acceptance threshold. The per-layer alternating-X coefficient is `mean((-1)^initial_column * Uz)` over its ten original columns; the analogous total-compression coefficient is exported separately. These coefficients preserve amplitude/sign and are not inferred null modes or an eigenanalysis.

The outputs are `figures/upl_tpi_x0_short_r2_<which>_review/{history.csv,layers.csv,history.png,pressure_profiles.png}` and `logs/upl_tpi_x0_short_r2_<which>.review.check.json`. The 15100-row layer CSV contains pressure, total compression, Uz and alternating-X coefficients plus native J/n/rho/k summaries; every ledger row is checked against the corresponding native time/ID/J/n. Analysis completion is independent of physical gates: an ordinary scientific gate failure still writes `analysis_complete=true`, `physical_pass=false` and the complete artifacts. A malformed or failed analysis writes a preserved failure receipt and does not rerun or rewrite native data.

## OFF proof and ON comparison

The OFF pair compares complete `typed22.bin`, `clock.bin`, `physical.bin`, `original15.bin`, `common_j_theta.bin`, `soil_n.bin` and typed-layout bytes, including their original headers, all 151 records and all signed dterror values. No exclusions, interpolation, header normalization or source-clock substitution are permitted. It writes `logs/upl_tpi_x0_short_r2_off_pair.check.json`; only genuine equality yields `passed=true` and both requested equality flags true.

The separate ON comparison requires actual identical saved times and Steps. Its pressure RMS and material displacement differences are descriptive across finite-Kw and beta-zero incompressible-limit models; they are not a 5-Pa half-step, physical error or accuracy-improvement test. ON native `PoroThetaLastStage` and saved load telemetry are endpoint observations, whereas the original model's fields are half-force observations. The private sidecar must be reviewed separately for the exact pressure history, original source-n event clock, unchanged J integration and one commit per complete step.

No theory fit, full-consolidation/CPU-GPU/restart/C08-collapse/other-psi acceptance is implied by this short review. Figures require root visual inspection before conclusions.

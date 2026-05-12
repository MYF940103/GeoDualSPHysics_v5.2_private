# C5f Surface Residual Audit

The detailed particle-field audit compares raw, normalized, and capped boundary-particle weighting for mode 4.

For the raw mode-4 control at the final retained frame (`t=0.006032 s`), the `r>0.85R` surface layer has mean excess `-34.5562 Pa`, p95 absolute excess `195.085 Pa`, and max absolute excess `195.085 Pa`.

Classification: `systematic`. The residual is not explained by the ghost residual diagnostic, because that log diagnostic samples the prescribed ghost state rather than the full material surface layer through time.

The radial-bin CSV records whether the residual is concentrated near `0.95R-1.0R` or spread through the outer shell.

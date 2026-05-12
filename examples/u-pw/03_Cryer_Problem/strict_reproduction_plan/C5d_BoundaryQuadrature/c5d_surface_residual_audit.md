# C5d Surface Residual Audit

The detailed particle-field audit was rerun under the C5d old-ghost case because C5b retained only frame summaries after raw-output cleanup.

For the old mode-3 ghost at the final retained frame (`t=0.006032 s`), the `r>0.85R` surface layer has mean excess `179.374 Pa`, p95 absolute excess `218.473 Pa`, and max absolute excess `263.154 Pa`.

Classification: `systematic`. The residual is not explained by the ghost residual diagnostic, because that log diagnostic samples the prescribed ghost state rather than the full material surface layer through time.

The radial-bin CSV records whether the residual is concentrated near `0.95R-1.0R` or spread through the outer shell.

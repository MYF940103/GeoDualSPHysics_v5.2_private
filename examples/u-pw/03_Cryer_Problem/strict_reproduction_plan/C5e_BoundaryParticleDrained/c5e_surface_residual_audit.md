# C5e Surface Residual Audit

The detailed particle-field audit compares the material-side mode-3 shell control with mode-4 boundary-particle Dirichlet coupling.

For the mode-3 shell control at the final retained frame (`t=0.006032 s`), the `r>0.85R` surface layer has mean excess `170.961 Pa`, p95 absolute excess `208.9 Pa`, and max absolute excess `252.395 Pa`.

Classification: `systematic`. The residual is not explained by the ghost residual diagnostic, because that log diagnostic samples the prescribed ghost state rather than the full material surface layer through time.

The radial-bin CSV records whether the residual is concentrated near `0.95R-1.0R` or spread through the outer shell.

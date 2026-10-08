# Ghost-position candidate comparison, 2026-07-24

Candidate was enabled only by temporary environment variable `DSPH_PORE_DIAG_BOUND_GHOST_POS=1` in CPU diagnostics.

| case | nstep | interstep | n_p1 | mean p Pa | comp Pa/s | seep Pa/s | total Pa/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| q0_k1em4_base | 0 | 3 | 1800 | 546.260944 | -1072498.744039 | 3681.780475 | -1068816.963563 |
| q0_k1em4_ghostpos | 0 | 3 | 1800 | 546.26073 | -1072503.30105 | 3666.170175 | -1068837.130874 |
| SelfWeight_base | 9 | 3 | 1790 | 5215.504147 | 30159.045575 | -28343.689496 | 1815.356079 |
| SelfWeight_ghostpos | 9 | 3 | 1790 | 5237.647102 | 31601.362321 | 1190880.411742 | 1222481.774062 |
| Lian_bottomleft_base | 0 | 3 | 799 | 1950.315337 | 15452.078724 | -15463.142551 | -11.063827 |
| Lian_bottomleft_ghostpos | 0 | 3 | 799 | 1950.313094 | 16079.604337 | -16511.673093 | -432.068756 |

Conclusion: the candidate improves Lian bottom-left local decay direction but catastrophically over-amplifies SelfWeight bottom-boundary seepage. It is not safe as a formal patch.

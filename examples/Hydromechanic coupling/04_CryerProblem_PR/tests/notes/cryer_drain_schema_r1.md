# Cryer drainage XML regression

The private CPU Debug and GPU Release Cryer solvers accepted the sibling `special/drainage` node. Each comparison used its own backend's earlier strict executable or retained native outputs. The shipped server program uses its original XML.

| Check | CPU | GPU |
| --- | ---: | ---: |
| Default model, explicit models 0, 1 and 2, two updates each | 4/4 | 4/4 |
| Model 2 pressure rounds per update | 3 | 3 |
| Byte-identical model 2 pressure and time-step sidecars | 6/6 | 9/9 |
| Explicit u-pl maximum absolute tracked surface pressure at the opening time (Pa) | 297.0725403 | 297.0726013 |
| Zero-pressure receivers on each of the next two saves | 5153/5153 | 5153/5153 |
| Unsupported private `freeSeepage` rejection before initial particle output | exit 1 | exit 1 |

The four-update explicit u-pl fixture used `dt=2^-20 s`, ramp duration `dt`, and fixed-step drainage start `2*dt`. The five actual saves from 0 to `4*dt` matched byte for byte across old and new XML on each backend for all 22 native fields over 37,181 IDs, including eight fixed IDs. The signed time-step error also matched. The saved state at `2*dt` still contains the surface pressure from the preceding update. The update starting at that time enforces zero pressure, visible at `3*dt`. The three-round TPI fixture kept its original ramp, drainage start and step, and its two updates precede drainage. These checks address configuration and saved-state equivalence.

The preparation and test entry is `tests/support/cryer_drain_schema_r1.py`. Its actions are `prepare`, `build`, `suite`, `event-old`, `event-new`, `event-review` and `reject` with backend `cpu` or `gpu`. Dedicated folders preserve the existing results. Native checks are recorded in `tests/logs/cryer_drain_schema_{cpu,gpu}_r1_*.check.json`. The historical strict-source and GenCase fixtures use the repository inputs at `7965df7d7cabb1d1ba42f131c4873ea01a242f46`. Reconstructing the old CPU and GPU JSph.cpp from that revision reproduced both retained private sources exactly.

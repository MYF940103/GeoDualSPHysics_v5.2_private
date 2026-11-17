# P2 bounded2s error-source arithmetic r1

Existing small tables only; no solve, decode, pressure trial, interpolation or fitted reference.
All rows retain their own actual saved times. Units mm; positive top error means excess settlement.

| Series / selection | Actual time (s) | Top error | Bottom shift | Pressure bias | Total-stress bias | Native-J | J-stress/pressure | Reference quadrature |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A / preopen | 0.0100002288818 | -0.0006525680644 | +2.801976643e-06 | +0.1585173927 | -0.1591609183 | -1.17429998e-05 | -1.014488595e-07 | +5.724587471e-17 |
| A / nearest_0p15 | 0.1500284338 | +0.02034894667 | +9.468480468e-06 | +0.009137470973 | +0.009909699555 | +0.001298347109 | -0.0002867724728 | +0.0002807330294 |
| A / legacy_Tv_0.005 | 0.192998167276 | +0.01998023552 | +9.405373539e-06 | +0.007080488367 | +0.01184334255 | +0.001128588331 | -0.0003272423939 | +0.0002456532903 |
| A / legacy_Tv_0.05 | 1.83166692256 | +0.01701652101 | +1.549667093e-05 | +0.004245645818 | +0.01340305493 | +0.0003012757377 | -0.001026835815 | +7.788367078e-05 |
| B10 / preopen | 0.0100002288818 | +0.008996664926 | +5.133173584e-05 | -0.1468097867 | +0.1557692488 | -1.408806789e-05 | -4.075197158e-08 | -4.440892099e-16 |
| B10 / nearest_0p15 | 0.150033433914 | +0.02811342579 | +4.850620166e-05 | +0.01465713321 | +0.01211729531 | +0.001295461073 | -0.0002862659258 | +0.0002812959174 |
| B10 / legacy_Tv_0.005 | 0.192994417191 | +0.02760749317 | +4.852021814e-05 | +0.01405636915 | +0.01245780413 | +0.001125313382 | -0.0003266661207 | +0.0002461524106 |
| B10 / legacy_Tv_0.05 | 1.83167192269 | +0.02239905151 | +5.413266346e-05 | +0.009603638227 | +0.01339161931 | +0.0002968337042 | -0.001025212258 | +7.803986043e-05 |
| BP2 / preopen | 0.0100002288818 | +0.004424433443 | +2.475298857e-05 | -0.08366966835 | +0.08808055199 | -1.11932624e-05 | -9.931272249e-09 | -4.440892099e-16 |
| BP2 / nearest_0p15 | 0.150033433914 | +0.02425620302 | +2.424457043e-05 | +0.008915264516 | +0.01402252217 | +0.001298813943 | -0.0002859380912 | +0.0002812959174 |
| BP2 / legacy_Tv_0.005 | 0.192994417191 | +0.02381171387 | +2.421954924e-05 | +0.01017612011 | +0.01256322104 | +0.001128295296 | -0.0003262945418 | +0.0002461524106 |
| BP2 / legacy_Tv_0.05 | 1.83167192269 | +0.0197147343 | +3.036374963e-05 | +0.006950886364 | +0.01338038283 | +0.0002991728364 | -0.001024111338 | +7.803986043e-05 |

## Same-clock P2 correction and remaining own-clock extra error

| Selection | B10-A top | P2-A top | Removed B10-P2 | Removed pressure bias | Remaining P2-A pressure bias | Remaining P2-A total-stress bias | Remaining P2-A bottom shift |
|---|---:|---:|---:|---:|---:|---:|---:|
| preopen | +0.009649232991 | +0.005077001507 | +0.004572231484 | -0.0631401184 | -0.2421870611 | +0.2472414703 | +2.195101193e-05 |
| nearest_0p15 | +0.007764479117 | +0.003907256347 | +0.00385722277 | +0.005741868696 | -0.0002222064571 | +0.00411282261 | +1.477608996e-05 |
| legacy_Tv_0.005 | +0.007627257657 | +0.003831478351 | +0.003795779305 | +0.003880249041 | +0.003095631745 | +0.0007198784927 | +1.481417571e-05 |
| legacy_Tv_0.05 | +0.005382530501 | +0.002698213289 | +0.002684317211 | +0.002652751863 | +0.002705240545 | -2.267210011e-05 | +1.48670787e-05 |

The complete unrounded component vectors, original absolute-error budget records and exact actual clock gaps are in the matching check JSON.
The reference-only time-gap scale evaluates the same original analytic companion at both actual times. It never corrects measured error, aligns native states or changes a budget.

Preopen uses an ideal uniform undrained end-load companion, not finite-ramp/inertial dynamic truth. Other selections use the original unfitted512-mode drained companion at each own time. Material-centre trapezoids span0.99m; J-1/Mc decomposition is a small-strain diagnostic, not exact strain, mass, energy, force closure or a proof of causal mechanism.
Existing physical budget failures remain failures. This arithmetic passed flag only means the table association and identity completed.

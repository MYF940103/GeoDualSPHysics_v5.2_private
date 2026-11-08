# C08 Darcy bare-r2 diagnostic: reject for delivery

The owned single GPU run completed 360000 new updates/global4360000 in 2384.828 s, ending at actual10.90000000065993 s (tau0.9000000002856723). All90 saved frames were decoded once. Original6805 IDs/22 arrays/P0/J/cache/kappa/plane/FS/signed-clock checks passed:450000 ledger/cache/history checks,612450 P0,162450 fixed,900000 plane,13262 trueFS checks; clock and ledger maximum error0. This establishes implementation/safe-save review, not physical acceptance.

The only physical intervention was Darcy LP/Lx denominator rr2+Eta2 -> rr2 in a private CUDA TU. Force/AV Eta2, total-AS.2/n3, original certified law1 r2 PRE -> law2 receiver, keep5, fixed-plane unclosed reaction, releaseShepardOFF/dampingOFF and CompletedOnly were retained. Production source/formal inputs/PRE were not changed.

At the identical final actual time:

|Metric|Retained Eta2|Bare r2|
|---|---:|---:|
|Pressure RMS kPa|14.3236681|23.8717289|
|Minimum pressure kPa|-40.6846641|-165.745672|
|Maximum pressure kPa|16.6083066|776.442250|
|Total stress Frobenius RMS kPa|31.6369766|44.0902742|
|Mean material settlement from PRE mm|102.280592|103.815072|
|Front particle center x m|4.64902991|4.67633624|
|Unique soil pairs r<.7dp|36|43|
|Minimum nonself NN/dp|.424153456|.513816774|

Pressure RMS is66.6593% higher and total stress RMS39.3631% higher. Mean settlement differs1.534480mm; it is not an error relative to paper truth. At tau.72, minNN/dp changes.420334883 ->.398401595 and near pairs42 ->47. The apparently better final minimum does not mean general clustering improved.

Across the90 saved states, the candidate pressure minimum is-1.152328125MPa at part82/tau.8300000002634533, native ID5809 at(x3.234124501,z1.500777012),FS0,J.9940420717,kappa.3039773107. The same ID supplies final+776442.25Pa with kappa unchanged,FS0. Forty-three final soil IDs have abs(p)>100kPa, versus0 in the control. The control full-window minimum is-143572.109375Pa at ID7017/tau.8. These are10ms-sampled extrema, not unsaved or continuous peaks.

All five PNGs and matching six CSVs were inspected. Gross shape remains similar, while pressure oscillations and shear-region clumping are not repaired. Therefore retain the original regularized production operator; do not merge this candidate, alter thresholds, repeat a PRE, or admit other psi from solver exit0. Existing original raw data and failed earlier attempts remain protected.

Next diagnosis uses a minimal actual full one-step velocity-direction map from the retained total-AS/n3/ShepardOFF control state, not the rejected Shepard state. It changes no physical formula and introduces no new long window or half chain. A gain would be directional sensitivity, not a complete energy/spectral proof.

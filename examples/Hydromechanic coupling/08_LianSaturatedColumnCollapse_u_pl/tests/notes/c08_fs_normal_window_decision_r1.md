# C08 normal-Taylor free-surface trial: not selected

2026-11-14, private GPU closure only. Original AS05 is the same-material control: Wendland H/dp1.8, dp.04, fixed5us, AS.5/n3.825, original AV.1, same certified10s schema2 PRE, psi0. No public numerical source or root formal input was changed. Source history was imported, not recalculated. CompletedOnly, fixed-plane release NoPen and unclosed same-stage Darcy reaction remain.

The actual owned solver48396 (parent41688, creationFILETIME134390861318993215) and Popen/Win32 exits were0. New180000updates ended at2180000/time10.899999999671936,91actual frames. Independently invoked existing full Wendland native reader once: all6805IDs/22arrays,455000soil ledger checks,619255P0 bit checks,910000plane checks and13445FS pressure checks passed; max scalar clock error0, original signed diagnostic guard unchanged. First frame is PRE+1, not a pre-update imported state. Native/solver completion is not physical acceptance.

All91 exact saved times/steps compare without interpolation. Original -> normal-Taylor:

| Descriptive metric | Original | Candidate |
|---|---:|---:|
| Worst absolute pressure kPa | -85.4465 | -88.2433 |
| Maximum pressure RMS kPa | 36.7548 | 36.5501 |
| Peak / final pairs r<.7dp | 110 / 23 | 106 / 27 |
| Minimum pair spacing / dp | .363086 | .377001 |
| Maximum J | 1.040609 | 1.053473 |
| Final front advance from PRE m | .338313 | .337519 |
| Final top-material settlement mm | 109.0973 | 108.7562 |
| Final velocity RMS m/s | .026392 | .024893 |
| Final current mixture KE J/m | 5.77582 | 5.13797 |
| .6-.9s fixed-material motion RMS mm | 4.96054 | 5.03108 |

Pressure RMS improves only0.56%, worst suction and final pair count worsen, and early arrest persists. Saved-state principal/pair-axis audit of original AS05 separately shows most first-close pairs are compressive; do not label every close pair tensile instability. The local affine consistency improvement and passed CPU/GPU components did not establish C08 physical benefit. The frozen small-matrix candidate also had larger storage-weighted nonnormal amplification/left defect, not a conservation/energy proof.

Decision: retain the private trial/evidence but do not merge or select this closure for the next physics run. No other-psi,3s or half chain is admitted by this result. Next bounded comparison under the user's exponent authorization uses original raw closure and AS.5/n2.55, matching the dry cohesive example's Wendland hdp1.8 exponent, with all other physics unchanged; it is a diagnostic, not a presumed repair. No new PRE is needed.

Seven PNGs inspected; matching histories/extrema/layers/tracks/fields/first-update/selection/differences CSVs reside at `../figures/c08_fs_normal_window_review_r1_*`. Native p-fixedP0 is not established as the paper excess-pressure field. No full paper accuracy/general contact or full restart claim. No SHA scans, duplicate solver, native decode or VTK.

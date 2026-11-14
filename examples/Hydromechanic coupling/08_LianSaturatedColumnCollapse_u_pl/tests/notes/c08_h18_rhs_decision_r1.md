# C08 n2.55 coefficient rejection and instantaneous pressure-rate review

The completed original/raw-FS AS0.5/n2.55 window remains retained, not physically accepted. A new single-factor AS0.7/n2.55 window genuinely failed: owner48944, solver36236/creation FILETIME134390921759832815, actual Popen/Win32/solver exits1, ownership errors empty. The first engine rejection is dynamic pressure wall808, stage0, sorted443, reported step2065916/start10.32957999969353. Only33 states are saved, ending actual10.320004999693893/completed2064001. The displayed finish10:40:46 on the final console PART line is an estimated finish, not an exit time. No unsaved arrays or failure-state time were reconstructed.

One separately admitted partial33 utility read passed all original22-array/6805-ID checks:165000 soil ledgers/cache/kappa checks,224565 P0 bits,330000 plane checks and4891 FS checks, scalar clock error0. The original full91/2180000 launch plan and original failed flags were preserved. This does not certify the failed whole run. No solver, PRE or VTK was repeated.

At the exact same last saved time, comparing AS0.5 to AS0.7, both exponent2.55:

| Metric | AS0.5 | AS0.7 failed prefix |
|---|---:|---:|
| Absolute pressure RMS, kPa | 10.68131 | 31.08041 |
| Minimum absolute pressure at this save, kPa | -26.84882 | -81.21716 |
| Total stress Frobenius RMS, kPa | 33.73016 | 56.19652 |
| Top material settlement from PRE, mm | 51.96886 | 45.42137 |
| Front advance from PRE, m | .1716071 | .1651468 |
| Nearest distance/dp at this save | .3706345 | .4380776 |
| Close pairs below .7dp | 36 | 64 |
| Maximum kappa | 2.214757 | 2.019369 |

The slightly larger final minimum spacing does not offset worse pressure, more close pairs and genuine runtime failure. Reject AS0.7/n2.55; do not select another coefficient merely from one spacing statistic. Matched33 history/field PNGs and history/extrema/layers/tracks CSVs are `figures/c08_h18_a07_n255_partial_review_r1_*`.

## Fresh CPU rates on the retained AS0.5/n2.55 states

`c08_h18_storage_rhs_r2` evaluates the original CPU corrector-mode force/Darcy on existing GPU Part30/60/90, with no physical advance. Its15000 actual final float rates match the source-ordered recomputation bitwise. Seven decomposed terms and fluid/fixed additive partitions reconcile inside declared arithmetic budgets; max cast/budget ratios are .49634/.49356. All5000 soil primary states and actual clocks remain unchanged per call. No GPU force substage has been reconstructed.

Rates below are normalized by the total instantaneous storage weight sum(nV/Kw), in kPa/s:

| Actual tau, approximately s | Compression contribution | Hydraulic contribution | Actual weighted rate |
|---|---:|---:|---:|
| .300005 | +78.638 | -75.491 | +3.147 |
| .600005 | -136.467 | -25.471 | -161.938 |
| .900000 | -3.474 | -15.368 | -18.842 |

FS receivers contribute only2.20% and8.48% of the negative netQ at.6/.9. Interior receivers with zero direct fixed donors contribute91.02% and83.36% respectively. Large individual FS Ace.Lx, LP and Taylor terms strongly cancel. Fluid/fixed donor partitions hold the full reconstructed field fixed and are additive bookkeeping, not wall-removal causal experiments. These facts do not exclude earlier or nonlocal boundary effects, and an instantaneous pressure derivative is not itself an error.

The storage coefficient-change contribution is included separately and is small at these samples. Conditional S=sum(nV/Kw*p) is not water mass, boundary discharge or a conservation theorem. Fresh-vs-saved theta changes the aggregate compression contribution only slightly; that comparison also does not recover the omitted GPU stages.

Both new RHS plots were inspected. The raw wall CSV exports all1805 slots; far slots may have stale derivative scratch even when their saved mode is0 or1. At.3 every huge-velocity slot is at least.17161m from soil, outside support2h≈.144m. Only support-participating wall values are meaningful force/donor reconstructions. Do not report far scratch as physical velocity or a participating-donor defect. Original CSV remains untouched.

The first test-entry compile failed2 solely because inherited JSph::Gamma hid a roundoff helper. Original r1 evidence/source is preserved; r2 changes exactly that helper spelling and fresh output tags, without changing equations or tolerances. Its isolated DebugCPU build links one new entry with86 original physical objects and passed. No public source or canonical solver changes occurred.

Read-only source review found the correct pn-based midpoint pressure update, paired J midpoint, and sole completed-step positive-FS cap owner. No wrong-base, duplicate compression or release reset was found. Next justified diagnostic is one original CPU step from restored Part60 with an all-ID pressure/J/hydraulic/cap balance, before deciding any new operator or trajectory. The former half-stage cap policy, Eta0 and already-existing pair-C are not proposed again. Other psi groups remain held. Figures and matched CSVs are retained; SHA scans0.

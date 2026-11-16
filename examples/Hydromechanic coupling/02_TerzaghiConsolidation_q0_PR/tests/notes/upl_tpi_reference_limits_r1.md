# P0: finite-Kw and M0 reference limits for the retained loaded column

2026-11-17. This is an offline comparison of existing reference CSV values, not a solver, component rerun, native decode, build, hash scan, Git operation, new benchmark gate or physical acceptance. The new CSV is `figures/upl_tpi_reference_limits_r1.csv`. Both new files were absent and created exclusively. Existing source, native records and plots/CSVs are unchanged.

## Frozen physical values and reference definitions

The actual consumed XML is `configs/upl_bigstep_c625_r1.xml`, not the generic Fourier material used in the small time-layer component. It has E=2000000 Pa, nu=0.29999999999999999, k=0.0001 m/s, rho_w=1000 kg/m3, Kw=200000000 Pa, n0=0.29999999999999999, q0=10000 Pa, dp=.01 m and drainage/ramp end tD=0.010000228881835938 s. The XML selects dynamic seepage and constant conductivity. It also retains the finite Kw value; setting a future M0 projection scheme must explicitly make storage zero rather than claiming that a finite XML Kw was solved.

The original companion function is in `support/upl_bigstep_full_review_r1.py:300`. Its primary H=1 m remains fixed, g=9.81 m/s2 is the existing reference conversion, and its 512 modes are not refitted. The constrained modulus M=E(1-nu)/[(1+nu)(1-2nu)]=2692307.692307692 Pa. Cv_M0=k M/(rho_w g)=0.027444522857366895 m2/s. With B=1/[1+n0 M/Kw]=0.99597778203409315, Cv_finite=B Cv_M0=0.027334135004464254 m2/s, so finite compressibility changes both the initial undrained pressure scale and decay rate by 0.402221797 percent. The initial ideal companion pressure scales are q0 and B q0=9959.7778203409307 Pa: their difference is -40.2221796591 Pa before any discretization error.

With lambda_j=(j+.5)pi, c_j=2(-1)^j/lambda_j and tau=t-tD, the M0 quasi-static pressure is q0 sum_j[c_j cos(lambda_j z/H) exp(-Cv_M0 lambda_j^2 tau/H^2)]. The finite-Kw companion replaces the amplitude q0 by B q0 and Cv_M0 by B Cv_M0. Settlement is positive downwards, s_M0(z)=1000 q0/M [z-H sum_j(c_j/lambda_j) sin(lambda_j z/H) exp(-Cv_M0 lambda_j^2 tau/H^2)]; the finite companion multiplies that summed pressure contribution by B and uses B Cv_M0. These are the original formulas, not a new solution.

## Ten existing actual selected times

All ten rows join `profile_times.csv` to exactly equal saved `theory.csv` time values. No interpolation, time shift, new H, fitted loading or rewritten clock is used. Requested Tv is a label; the actual Tv column is retained separately. In particular, selected Tv=.1 through1.5 is about .014 s earlier than the nominal target, as already recorded in the original table.

The displayed mean is the same-node arithmetic mean of the reference evaluated at the 1000 fixed original soil IDs; it is not a continuum integral or a current-J-weighted mean. The new CSV additionally retains the separate continuum means. Current-J weighted means are deliberately not used to define the pure reference difference because their weights come from an already evolved trajectory. Top/bottom settlement refers to the original material layers z0=.995/.005 m, respectively, not boundary planes z=H/0. Thus bottom-material settlement can be nonzero even for a fixed continuum base.

| Requested Tv | Actual time s | Actual Tv | M0 mean P Pa | Finite-Kw mean P Pa | Finite-M0 P Pa | Finite-M0 top mm | Finite-M0 bottom mm |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.005 | 0.192998167276 | 0.00502229110312 | 9200.67065 | 9165.26757 | -35.4030847 | +0.013148725 | +7.46983337e-05 |
| 0.05 | 1.83166692256 | 0.0499947732132 | 7477.1045 | 7452.08888 | -25.0156205 | +0.00929120172 | +7.32087902e-05 |
| 0.1 | 3.63972080467 | 0.0996159493082 | 6438.69839 | 6419.94081 | -18.7575879 | +0.00696688172 | +6.01627466e-05 |
| 0.25 | 9.10528964888 | 0.249615878382 | 4381.88759 | 4375.15811 | -6.72947782 | +0.00249942549 | +2.03889697e-05 |
| 0.4 | 14.5708647438 | 0.399615979004 | 3024.07702 | 3023.88643 | -0.190589873 | +7.07881088e-05 | +6.03293435e-07 |
| 0.5 | 18.2145793904 | 0.499615988908 | 2362.75874 | 2364.95312 | +2.19438367 | -0.000815023206 | -6.39469536e-06 |
| 0.7 | 25.5020086836 | 0.699616008717 | 1442.45128 | 1446.65922 | +4.20793471 | -0.00156288291 | -1.22749928e-05 |
| 1 | 36.4331463733 | 0.999615866898 | 688.062126 | 692.126967 | +4.06484106 | -0.00150973602 | -1.18576826e-05 |
| 1.5 | 54.6517196063 | 1.49961591642 | 200.372565 | 202.55895 | +2.18638506 | -0.000812052482 | -6.37797642e-06 |
| 2 | 72.8842868995 | 2.00000002625 | 58.2958063 | 59.2252919 | +0.929485627 | -0.000345223321 | -2.71143338e-06 |

The maximum absolute same-node pressure-reference difference among these ten times is 35.4030847207 Pa at requested Tv=0.005; the corresponding continuum mean difference is -35.4024171317 Pa. The maximum top-material difference is 0.0131487249639 mm and bottom-material difference is 7.46983336526e-05 mm, both at requested Tv=0.005. These are physical-reference differences, not integration errors, independent-half errors or reasons to change the original 5 Pa/.005 mm numerical comparison limits. For example the early pressure and top-settlement model differences themselves exceed those two limits.

At requested Tv=2, the actual mean-pressure references are 58.2958062912 Pa for M0 and 59.2252919183 Pa for finite Kw; the corresponding top-material references are 3.67406244809 and 3.67371722476 mm. The common ultimate continuum top settlement is 1000 q0 H/M=3.71428571429 mm; its existence does not make the transient companions identical.

## Required A/B/C interpretation

- A, the retained explicit finite-Kw u-pl model, must be interpreted against the finite-Kw companion and an appropriate finite-storage coupled component reference. Comparing A solely to the incompressible curve folds the known storage-model difference into numerical error.
- B (TPI alpha=.5) and C (PPE-t alpha=0), as currently defined with beta=0, share the M0 physical pressure constraint and must use the M0 companion / independent coupled M0 component reference. Their time predictors differ, but their intended continuous physical limit does not. They should not use different B-versus-C theory curves.
- A-versus-B/C differences are cross-model and temporal-discretization effects together; no universal 5 Pa/.005 mm cross-model equality is implied. Benchmark accuracy should still be compared by each method's appropriate qualified reference and observables at the same actual times, rather than fitting one curve to another.

The original two quasi-static companions assume an ideal closed undrained loading state followed by single-top drainage, constant small-strain coefficients and no inertia. Neither is an exact solution for the actual finite ramp, normalized top-kernel-band traction, startup waves, dynamic fluid/solid inertia, changing J/n or mDBC/SPR/HG discretization. In particular the coupled beta0 Fourier M0 reference includes dynamic terms absent from this quasi-static curve. The existing unfitted H=.995 pressure-plane sensitivity remains separate and was not selected, recomputed or fitted here. This table establishes reference bookkeeping, not full transient theory or release acceptance.

## Consumed existing evidence (stat only)

- `configs/upl_bigstep_c625_r1.xml`: 14824 bytes, mtime_ns=1793721555265363000.
- `support/upl_bigstep_full_review_r1.py`: 38206 bytes, mtime_ns=1793729164192983900.
- `figures/upl_bigstep_full_r1.theory.csv`: 1292520 bytes, mtime_ns=1793876714915077500.
- `figures/upl_bigstep_full_r1.profile_times.csv`: 1620 bytes, mtime_ns=1793876714993155200.

Read 1564 existing post-open theory rows and the existing ten selection rows. No original file was written. No SHA256 or other content hash was calculated; same input size/mtime_ns was checked before the exclusive writes. Only the two new deliverables were created.

# Dynamic pair-C and Lian second derivative: existing implementation

Read-only mapping of the original schema2 `full_source.zip`; no new numerical candidate, run, parameter or source change.

Legacy `PoreDarcySymmetricCorr` affects only old u-pw soil-soil Darcy pressure/elevation terms: receiver `d dot Ci*g` becomes `d dot (Ci+Cj)*g/2`. Dynamic mode explicitly rejects that flag (`JSph.cpp:666-667`), rather than silently ignoring it. Old CPU references2393ff/2452-2462; GPU1978-1989.

Dynamic already has pair-C for the two-point terms:

`w_ij = Vj * d_ij dot (Ci+Cj)g_ij / (r^2+Eta^2)`

`LP = sum w_ij*(pi-pj); Lx = sum w_ij*d_ij`.

Its `gp = sum Vj*(pj-pi)*Ci*g_ij`, `Da = sum Vj*(Aj-Ai) dot Ci*g_ij` and gradJ retain receiver-Ci. See frozen `JSphCpu.cpp:3224-3234`, `JSphGpu_ker.cu:1555-1569`. Pair-C in LP/Lx is already the baseline and must not be proposed again as a new repair.

Local `papers/u-pw/Lian 2023 u-pl.md:309-319` Eq23 uses a receiver-C, bare-r2 full Hessian. Its2D trace is algebraically comparable to the corresponding LP-gp.Lx only with matching neighbors/volumes/gradients, both two-point ends using Ci and Eta0. The current pair-C/Eta operator is not a literal full Eq23 implementation.

Existing tests must be distinguished:

- `upl_lian_c08_snapshot81_review_r1.md:19-31`: weak-PRE interior x-squared trace RMS Ci/Cavg=.02041998/.02041999; smooth=.01382737/.01382739. Not a collapse-trajectory comparison.
- `upl_c08_darcy_eta0_decision_r1.md:5-24`: a physical window retained symC and removed only Eta; end pressure RMS14.324->23.872kPa. It rejected that intervention, not symC.
- `upl_c08_gradient_flux_decision_r1.md:30-38`: pair-k shadow with symC/Eta retained, not LP symmetrization.
- `upl_c08_four_direction_review_r1.md:27`: pressure-force G and fully paired D/G were different operators and were not admitted repairs.

The bounded record search found no new collapse A/B changing LP/Lx receiver-C to pair-C because pair-C was already present. This mapping prevents duplicate work; it neither attributes the pressure offset nor justifies changing gp/Da/gradJ, momentum force, Eta or time integration. No SHA scan, build, solver or reader was performed.

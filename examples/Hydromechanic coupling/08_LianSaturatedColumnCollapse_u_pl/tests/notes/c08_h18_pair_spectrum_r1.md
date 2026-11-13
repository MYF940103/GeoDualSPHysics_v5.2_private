# C08 saved close-pair tensile spectrum

New author-only adapter `support/c08_h18_pair_spectrum_r1.py`; no solver,
reader, build, native scan, VTK, analysis or Git has been invoked by its author.
Root must read it before one offline invocation:

```text
python -X utf8 -B tests/support/c08_h18_pair_spectrum_r1.py --review-check tests/logs/c08_h18_wend_a03_partial_review_r1.check.json --tag c08_h18_wend_a03_pair_spectrum_r1 --execution-authorized
```

Paths supplied on the command line are relative to the current working directory;
run from the C08 case root. Other relative paths retain the existing case resolver.
The existing successful partial-analysis check and its unchanged stat-bound
typed22/layout/clocks/completion exports are consumed. No original BI4 or source
archive is read. All90 original records and IDs are checked by the existing pure
typed-export reader; the failed solver and missing91st state remain failed/missing.

For all5000 original soil IDs and every saved time, construct the symmetric double
total tensor `Sigma_eff-p*I` using absolute native pore pressure and the six double
effective-stress values. Tensile stress is positive. Its three-dimensional positive
spectral part is `Q diag(max(lambda,0)) Q^T`. Saved close pairs are the distinct
unordered soil pairs whose true in-plane separation is strictly less than `.7dp`;
this spacing threshold is a descriptive diagnostic, not a new numerical gate.

For each endpoint report the maximum total principal stress, and crucially the
positive-part projection `n^T Sigma_total^+ n`, with `n=(dx,0,dz)/r`. A positive
out-of-plane principal value alone can give zero in-plane projection and therefore
does not directly indicate a repulsive force along this 2D pair. Signed normal
stress, pressure, kappa, J, FSType, positions and speed are also preserved. A
zero-distance pair has an undefined direction: retain it, report null directional
values, and count the omission explicitly; never invent a direction.

CSV outputs retain all90 histories, all observed close-pair states, and each pair's
first saved occurrence. History includes earliest IDs, full-body extrema with their
original IDs, nearest spacing and pressure. Fractions use pair-endpoint occurrences,
so an ID in two pairs counts twice; direction fractions exclude zero-distance
undefined directions. Both `>0` and `>100 Pa` are descriptive spectral categories,
not acceptance limits or parameter tuning. One readable four-panel PNG accompanies
the exact matching CSVs.

The actual GPU artificial-stress input is cast to float before its Jacobi spectrum;
this double spectral diagnostic is not a bitwise reproduction of that eigensolver,
cell traversal, predictor states, force amplitude, mass/J weighting, or kernel-ratio
factor. Positive directional content shows that the AS coefficient can act along
that saved pair under the spectral model. It does not establish that AS was the
cause of clustering, or that increasing its coefficient repairs the trajectory.
Keep all pressure spikes and compressive pairs. No physical acceptance, winner,
next epsilon, solver, half chain or PRE is admitted by this adapter.

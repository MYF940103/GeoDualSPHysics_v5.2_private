# C08 snapshot81: closed-output review

Reviewed the existing check,10368 field rows,162 receiver rows and PNG; did not
rerun the source script, solver, decoder, build or modify production/server data.
New aggregate: `tests/figures/upl_lian_c08_snapshot81_review_r1.csv` (640 rows).
Each row reports RMS/max tensor and trace errors for one oracle/region/variant/
storage/field. RMS relative error divides by the group's analytic RMS, not the
mean of pointwise relative errors. Zero analytic trace has no relative value.

The saved10s preload has J=[0.9992884029437142,0.9999845690293798]. Regions are
disjoint:9 interior (>2R from walls and savedFS),45 wall-only,9 top-only,18 wall+
top. Top bands use distance to savedFS, not a newly inferred physical top wall.
All23328 original arithmetic checks passed; constant fields were exactly null.
Maximum double-affine tensor residual was1.61e-14; max trace/budget ratio.00203.

Interior, double manufactured scalar: RMS errors (normalized scalar derivatives,
not actual pore-pressure error):

| variant | x² trace | xz tensor | x²-z² tensor | smooth trace |
|---|---:|---:|---:|---:|
| Ci_Eta0 | 2.207e-5 | .2784070 | .5568141 | .00352056 |
| Cavg_Eta0 | 2.209e-5 | .2784070 | .5568140 | .00352058 |
| Ci_Eta2 | .02041998 | .2862706 | .5148332 | .01382737 |
| Cavg_Eta2 | .02041999 | .2862707 | .5148331 | .01382739 |

On this weakly deformed interior, receiver/pair differences are tiny. Eta2 is
the larger difference: it reduces the x²-z² tensor error but increases xz tensor
and smooth errors. The current-pattern x² trace error is1.021% of analytic2;
bare receiver-C is.001103% here. Smooth relative trace errors are1.365% and
.348%, respectively. These observations do not prove a stable coupled gain
from removing Eta2, and tensor errors are not benchmark pressure errors.

Boundary support changes the comparison. For wall-only x², literal/current-
pattern trace RMS is1.1010/1.0964 with soil-only truncation, versus3.371e-5/
.0204307 with analytic images. For x²-z² tensor RMS the image values are.55659/
.51461, while xz tensor is.27830/.28616: again there is no uniform winner.
Top-only data do not change with side/bed images: current-pattern x² trace RMS
is.33116 and xz tensor RMS.52447. Wall+top completion removes lateral truncation
but leaves top truncation, as intended; no top wall was introduced.

Crucially, **soil-only excludes the actual native mDBC wall samples**, while
analytic images are a mathematical extension, not production wall closure.
Their difference demonstrates support sensitivity, not a diagnosed native-wall
defect or physical boundary acceptance. Neither oracle contains exported C.

Float storage is separately retained in every aggregate row. Paired float-
minus-double Hessian maxima are.0002412 for x,.0001144 for z,.0009876 for x²,
.0004931 for xz,.0009983 for x²-z² and1.583e-5 for the smooth field. These are
direct component differences, not differences between aggregate error norms.
They do not explain the much larger quadratic/tensor errors in this test.

Decision: retain the current production operator. Explicit Hessian storage alone
does not improve its constant-isotropic-k trace. If further work is justified,
the next small step is one separately reviewed real zero-step component on this
same snapshot: existing wallState/FS/C/wallC, genuine completed mechanical Ace,
wallAce and Darcy; compare at most81 receiver references, retaining original
hydrostatic cancellation/free-surface policies. Only then assess a private
denominator variant. No new public knob, half chain or physical long run follows
automatically. This is small preload deformation, not collapse disorder or an
original production-rate replay (native C/totalAce/BoundMode/rate are absent).

The check has no instrumented elapsed-time field. Root observed roughly a dozen
seconds for the offline run; this is not a solver/GPU throughput benchmark.
Reconstruction covered561/693 C sites and11384/15062 cached geometry edges,
including1050 analytic images;81x7060 is not claimed as the full work count.

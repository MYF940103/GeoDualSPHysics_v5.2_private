# C08 Darcy-only Eta zero-step result

The closed `upl_lian_c08_darcy_zero_cpu_r1.check.json` and component completion passed. One actual ct at the original Eta was followed by three Darcy calls (Eta2, zero, Eta2). All5000 soil rates remained finite; 410 walls were active, FS23 count100 and saved/recomputed FSType changes0. The upstream fields remained bit-exact between calls, and the restored baseline5000 rate floats were byte-exact. Rate/reference max original-budget ratio was0.000203167; Eq23trace/scalar-identity ratio0.467908. This closes execution and operator isolation, not physical accuracy.

The recomputed complete-state rate is **not the old10s native rate**: CorrMat/finished Ace/rate were not saved. It is one new next-predictor evaluation using current boundary/C/ct closure, with original AV.1/G1/damping.02 and unchanged upstream Eta. No time was integrated, and the source10s preload is a small-deformation state rather than collapse disorder. Large instantaneous rate is neither equilibrium evidence nor proof of an unstable physical trajectory.

All5000 rates: candidate-minus-baseline RMS859.039691Pa/s, max6118.4375Pa/s; baseline/candidate absmax546879.25/552997.5625Pa/s. These counts and extrema come from completion. The selected81 below are deliberately boundary-weighted and must not be treated as a uniform5000-particle sample.

| Selected band | N | Eta2 rate RMS [Pa/s] | Eta0 rate RMS [Pa/s] | Difference RMS [Pa/s] | Difference max [Pa/s] |
|---|---:|---:|---:|---:|---:|
| All selected |81|163310.8025|165161.6232|1854.8125|6118.3125|
| True FS2/3 |9|485457.2609|490948.3858|5494.2854|6118.3125|
| Non-FS |72|23358.6487|23650.9478|311.4067|986.6875|
| Strict interior |9|515.2682|430.5693|88.1000|116.4035|
| Wall-only |45|16102.5948|16301.1977|234.0746|511.3594|
| Top-only |9|314941.4005|318463.9446|3522.6281|6118.3125|
| Wall and top |18|264148.5802|267167.6829|3022.6097|5802.1563|

`figures/upl_lian_c08_darcy_zero_review_r1.csv` contains the matching7 rows, original-budget ratios and compression RMS. It joins the two actual variant records by native ID with the already closed snapshot81 receiver geometry. The last4 rows partition81; FS/non-FS is a separate overlay. Geometry regions retain the earlier diagnostic2R boundary: wall distance is min(left,right,bed), top distance is distance to savedFS, R=2h. No region is a new physical pass criterion.

Approximately97.5% of the **selected81** difference sum-of-squares lies in the9 actual FS receivers. Thus the largest present difference concerns the free-seepage raw hydraulic-head branch, not just the interior Taylor-defect/Hessian trace. The lower interior rate RMS at Eta0 cannot be called a lower error without a true rate reference. Likewise the larger FS rate cannot by itself be called worse. The all-real-source arithmetic reference uses actual completed C/Ace operands; it verifies implementation, not a second physical model. Its max absolute actual/reference difference is0.030577Pa/s (float output storage), well inside the original propagated budget.

Production Eta remains unchanged. The prior manufactured P2/smooth scalar evidence still makes Darcy-only Eta0 a low-cost candidate, but any later short physical comparison must retain the real free-surface policy, pair symC and upstream Eta. This review adds no solver, half-step, new theory gate or automatic follow-on.

## Selective backup suggestion

- New source/recipe: `support/upl_lian_c08_darcy_zero_cpu_r1.cpp` and `.py`.
- Notes: `notes/upl_lian_c08_darcy_zero_cpu_r1.md` and this review.
- Small derived table: `figures/upl_lian_c08_darcy_zero_review_r1.csv`.
- Actual build/compile/link/run/check JSON records under `logs/upl_lian_c08_darcy_zero_cpu_r1*` (and small text logs if root selects them).
- Preserve/select only `outputs/upl_lian_c08_darcy_zero_CPU_r1/completion.json` and `receivers.csv` as numerical component evidence, using explicit paths if ignored. Do not stage/move the helper executable, objects, runtime or original snapshot. No Git operation or repeated execution was performed by this review.

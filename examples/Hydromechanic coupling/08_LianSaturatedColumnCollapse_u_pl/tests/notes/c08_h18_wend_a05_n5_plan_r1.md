# Planned single Wendland epsilon .5 / exponent5 comparison

Planned only: one bounded .90s candidate, not admitted, prepared or launched.
Only this note is added. No code, XML, BAT, active input, output or receipt is
changed; no build, solver, reader, Git or hash operation is performed. Current
centroid-AS.7 run must first receive its independent native and wall-geometry
review. Normal exit alone does not satisfy that prerequisite or physical review.

## Hypothesis and fixed scope

Keep epsilon=.5 and change only the declared AS exponent3.825 to5, using the
accepted current Wendland-only centroid recovery after existing-nearest geometry
failure. Proposed fresh future label: `c08_h18_centroid_a05_n5_w09_r1`.
Retain Wendland h/dp1.8, dp=.04/H=.072f, fixed5us, psi0 material, original AV.1,
CompletedOnly pressure policy, NoPen/release/slip/retired IDs, and the same full
schema2 PRE Part1000 with native stress/kappa/J/p/fixed-P0 history. No PRE rerun,
history reset, half chain, contact gate or time schedule change is proposed.
The unchanged91-row scalar plan targets completed2180000; first actual save is
PRE+one update. Any earlier stop remains a failed partial, with its true endpoint.

Local Bui08 text, `src/papers/elastoplastic basic/Num Anal Meth Geomechanics -
2008 - Bui - Lagrangian meshfree particles method  SPH  for large deformation
and failure.md:1464–1472`, reports .3 reduction versus .5/.7 removal in that
test, fixed n2.55, and recommends epsilon.5/n2.55 for h1.2dp. It also warns that
n4 caused overly strong tensile-pair repulsion there. This is not calibration
of the present Wendland1.8 saturated u-pl discretization or justification for n5.

The narrower numerical hypothesis follows the implemented `[W(r)/W(dp)]^n`,
with W from `src/source/FunSphKernel.h:88–98,206–212`, and the actual GPU W(dp)
normalizer at `JSphGpu_ker.cu:2212–2213,1881–1890`. Matching its logarithmic
slope at r=dp to Cubic1.2/n2.55 gives n=5.0165044 for Wendland1.8: n5 is a nearby
locality probe. Versus n3.825, n5 strengthens the .7dp weight about36.5% and
reduces the1.5dp weight about51.8%; dp weight and3.6dp support remain unchanged.
Actual AS also depends on total positive-spectrum stress, gradients and J/rho.
This is neither full-distance operator equivalence nor a paper-calibrated fix.

## Comparison and decision evidence

Use retained `c08_h18_wend_psi0_a05_w09_r1` / n3.825 as the documented control.
Bind both actual programs/source versions. The retained control predates the
extra centroid fallback. Report retry counts only if actually observed; no
counts are invented from a saved trajectory. Without that observation, retain
the operator-version attribution limit: differences cannot be credited solely
to n. No replacement control run or new counter interface is automatic.
Compare only exact shared completed-step/actual-time saves and all5000 original
material IDs; show each own-window endpoint separately, without interpolation.

- Absolute p: mean/RMS/extrema, negative counts and original extreme IDs. Keep
  native p-minus-fixed-material-P0 separate from absolute p and from any change
  since release; none is silently equated to the paper's excess-pressure field.
- Nearest-spacing distributions and r<.7dp pairs, alongside total stress
  `Sigma_eff-pI`, positive principal values and pair-direction positive spectral
  projection. Close pairs/negative p alone do not prove tensile instability.
- J and kappa histories, extrema/IDs and spatial patterns. Derived n/V/rho are
  not independent volume evidence; unchanged kappa does not prove elastic-only.
- PRE-relative front/material displacement, layer settlement, velocity RMS/max,
  current mixture KE and stated pressure-storage quadratic. These are not a
  complete energy/conservation balance; early arrest or low KE is not a winner.
- Native IDs/P0/ledger/cache/FS/contact/signed clocks and actual wall det/domain,
  donors/retry scope. Preserve original numerical gates; no new arbitrary
  thresholds or5Pa/.005mm half-step-error claims apply to changed parameters.

The previous .3/.5/.7 results already show nonmonotonic pressure/motion, so this
single distance-locality hypothesis is not another endless epsilon sweep or
shape-fitting exercise. If it remains deficient, stop parameter selection and
review the validated causal evidence; no next epsilon/psi/formal3s is automatic.
Do not transplant beta/Eq47 from Lian3.5.3 into this integrator: that plastic
negative-pressure treatment is tied to its TPI discretization and calibration,
not AS n, pressure clipping or a free replacement coefficient. No new physical
acceptance, parameter winner or future solver is authorized by this plan.

# C08 snapshot81 — author-only geometric derivative diagnostic

No import, execution, solver, decoder, build, source/server change or SHA scan.
After full review, one proposed offline command from the case08 root:

`D:/anaconda3/python.exe -X utf8 -B tests/support/upl_lian_c08_snapshot81_r1.py --out-prefix tests/figures/upl_lian_c08_snapshot81_r1`

The only frame is Part1000 of the closed `upl_prestress10_CPU_r1_native_r1`:
7060 IDs,22 arrays,4M completed steps,actual time10.000000000374257s.
This is real small preload deformation, not post-collapse strong disorder.
Bind the actual source run, reader completion, exported layout/IDs/clock/data,
and source seed XML/BI4/Normals stat. Reuse typed22 schema and C02 Eq23 pure
functions; never call the old reference main, old matrices or source hashing.
The input NBI4 is bound, **not decoded**. Three physical planes come from this
actual run's explicit XML `boundnormal_plane clear=true` initialization. They
do not supply missing saved per-ID BoundMode or prove native wall-C values.

Map81 IDs from the real initial100x50 material grid; do not renumber IDs.
x indices0,1,2,25,50,75,97,98,99;z0,1,2,12,25,37,47,48,49.
Freeze saved FSType/FSNormal. Use actual current coordinates,J and native V0J.
Cubic h is source float(.048); constants use its promoted-double value;
Fac follows original float32 intermediate operations. This is a source-pattern
calculation, not a newly measured native bitwise kernel parity proof.

Two explicitly conditional quadratures: (1) real soil support, with an interior
subset more than2R from all three physical planes and saved free-surface nodes;
(2) analytic wall-image completion using only real-soil owners within2R of the
left/right/bed planes. Include side-bed corner images once. No repeated images,
top wall, inferred water table, native wall quadrature or wet/contact admission.
Analytic fields at image locations are mathematical extension values, not a
claim that every manufactured field satisfies the real mDBC/Neumann policy.
Wall/top-band errors remain separate from the qualified interior subset.

KDTree broad phase only avoids NxN storage. Final unchanged moment float(rr2)
and rate double(rr2) cutoffs are distinct; the candidate radius's one-ULP
envelope does not change either predicate. Rebuild neighbor Cj as needed and
report those sites/pairs;81x7060 is not presented as total reconstruction cost.
All Ci/Cj are independent reference inverses, not exported production matrices
or the native inverse/fallback implementation. Undefined inverses fail visibly.

Retain4 Ci/Cavg x r2/Eta2 variants and both double/float manufactured pressure.
Fields1,x,z,x²,z²,xz,x²-z²,sin(pi*x)sin(pi*z) produce10368 rows plus162 receiver
rows. Reuse original gamma(64N+256) trace/action budgets, exact constant null and
double-affine forward bounds using the actual first-moment residual. Float
affine and all P2/smooth errors are descriptive; no new accuracy threshold,
relative denominator for zero trace, smoothing, fit, scalar-rate/5Pa gate.
The small PNG shows selected geometry and trace-zero tensor errors; raw CSVs
retain every component/variant/precision. Missing C/totalAce/CODE/BoundMode/rate
precludes production-rate replay. No coupling, physical accuracy or release
acceptance follows. Real zero-step FS/C/wall/Ace/Darcy calls remain a later,
separately reviewed component, not an automatic follow-on from this script.

# Scalar-trace interpretation of the existing snapshot81 outputs

Only the existing10368-row CSV was reduced; no source-script rerun, new probe,
solver, decode, figure or production change. New table:
`tests/figures/upl_lian_c08_scalar_trace_review_r1.csv` (400 rows).
It separates2oracles,9interior/45wall-only/9top-only/18wall+top (plus all81),
4variants,2pressure storage modes and5fields. Only scalar trace errors enter.
Zero analytic traces retain absolute errors without an invented denominator.

The earlier whole-Hessian comparison does not settle the diffusion choice:
constant isotropic-k interior diffusion needs its trace, not each component.
For the9interior points, double-pressure trace RMS is:

| variant | x² | z² | x²-z² | xz | smooth |
|---|---:|---:|---:|---:|---:|
| Ci_Eta0 | 2.207e-5 | 2.207e-5 | 4.414e-5 | 5.720e-8 | .00352056 |
| Cavg_Eta0 | 2.209e-5 | 2.198e-5 | 4.407e-5 | 8.908e-8 | .00352058 |
| Ci_Eta2 | .02041998 | .02038580 | 3.685e-5 | 5.616e-8 | .01382737 |
| Cavg_Eta2 | .02041999 | .02038586 | 3.679e-5 | 8.790e-8 | .01382739 |

Holding Cavg fixed isolates the denominator. Eta0 materially improves both
nonzero-trace quadratics and the smooth field here, for **both double and float
pressure**. Float core RMS changes Eta2→Eta0: x² .0205962→.00033098;
z² .0203749→.00007439;smooth .0138280→.00352116.
The exact-zero-trace fields slightly favor Eta2, but their absolute residuals
are much smaller (float x²-z² .00011355 vs.00011820;xz .00012692 vs.00012844).
They remain reported; no tolerance is invented to call those outcomes equal.

The analytic-wall completion gives the same useful direction for45wall-only
points: Cavg x²/z² trace RMS falls from .0204307/.0203771 to3.372e-5/3.404e-5;
smooth falls .0305066→.00776470. This also persists with float pressure.
It is an analytic-extension oracle, not actual mDBC wall-C or flux evidence.

There is **not** global uniform dominance. Without wall completion, Cavg Eta2
has slightly smaller trace RMS for all five wall-only fields; that oracle omits
native wall quadrature. At top-only points, Cavg Eta0 improves x² (.331163→
.324808), but slightly worsens z² (1.209208→1.212678), zero-trace fields and
smooth (.0367476→.0375814). Wall+top with images shows the same tradeoff.
The table records savedFS counts: top-only contains3true FS points and wall+top
6. The actual free-seepage FS branch uses raw hydraulic head rather than this
interior Taylor-defect trace, so these geometric traces cannot replay that rate.

Conclusion: **keep production unchanged for now, but retain Cavg+Eta0 as an
explicit low-cost diffusion candidate worth the next bounded validation**.
Do not reject it because one Hessian component worsened, and do not remove
proven pair symC together with Eta2. No new arrays or neighbor pass is implied
by a denominator-only candidate; its actual cost/stability are not measured.
First compare genuine existing FS/C/wall/Ace/Darcy calls at the same frozen
snapshot, preserving hydrostatic cancellation and the real free-surface policy;
only a justified subsequent short physical check can support production choice.
No such component/physical run is launched by this review. Small-preload
deformation and reconstructed-C/oracle limitations remain in full effect.

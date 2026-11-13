# C08 affine free-seepage witness and bounded closure candidate r1

2026-11-14. Read-only mathematical review plus this new note only. No production edit, build, solver, native decode or GPU action. The completed zero-step result is not physical acceptance.

## Continuum and primary-reference scope

Let F=grad(p)+rho_w*Ace and q=n*w_ls=-(k/gamma_w)*F. Lian2023 `src/papers/u-pw/Lian 2023 u-pl.md:170–174` Eq5 gives this relative Darcy flux; lines204–218 Eq9/10 give pdot=Kw/n*(-theta+div(k*F)/gamma_w). Ace=a_s-g is explicit in `source/JSphCpu.cpp:3170–3187`.

For the fixture p=-16+b*x, b=0,+4,-4, Ace=0, constant J/k/n and v=theta=0, F=b*e_x, div(F)=0. The physical flat top has n=e_z and q.n=0. Every pressure is strictly negative. Thus the field is locally admissible for the negative-p, non-infiltrating soil seepage face: it satisfies p<=0 and the stronger usual complementary condition p<0 => q.n=0. Lian2023 lines881–883 explicitly adopts free-seepage with p<=0, so negative pressure alone does not disqualify this hydraulic witness.

Bui2017 `src/papers/elastoplastic basic/Bui 2017 A coupled fluid-solid SPH approach tomodelling flow through deformable porousmedia.md:699–716` separates solid fixity from hydraulic wall Neumann treatment; lines717–720 imposes p=0 at its **water-body** free surface. That different two-layer water boundary does not admit this negative-p fixture and must not be cited as its soil free-seepage condition.

Lian2023 lines309–319 Eq23 retains a Taylor term to remove distortion errors. However the older free-seepage-specific omission was deliberate: retained `tests/notes/lian_seepage_boundary_review_r1.json:5–10` records the direct visual check of Lian2021 local PDF printed pp20–22, Eq71 positive-head-only cap and Eq72 without Eq57 error removal. This audit read the local primary MD and that retained PDF audit; it did not freshly re-extract Eq72. Current pair-C/Eta2/dynamic-Ace split is not a literal full tensor reproduction of that paper. An affine defect therefore motivates reevaluation, not a claim that simply restoring a term is the paper's prescribed fix.

## Completed actual CPU evidence

`tests/logs/c08_fs_affine_cpu_r1.run.json` records one successful component execution, zero physical steps. `tests/outputs/c08_fs_affine_cpu_r1/completion.json` and `rates.csv` contain486 rows, production FS/C, two kernels and b=0,+4,-4. Boundary projection preserved all negative pressures; actual FS2 ID76=(1,2) was detected in both kernels. Its physical top is flat; no FS label or C was supplied by hand.

At ID76, b=+4 (Pa/m); the b=-4 values reverse sign and b=0 is exactly null:

| Quantity | Cubic h/dp1.2 | Wendland h/dp1.8 |
|---|---:|---:|
| Lx_x (1/m) | +0.0137423675342 | -0.00155848381932 |
| LP=Hraw=b*Lx_x (Pa/m2) | +0.0549694701369 | -0.00623393527727 |
| Actual pdot (Pa/s) | +0.0373688377440 | -0.00423789629713 |
| Declared raw arithmetic budget (Pa/s) | 8.16505353e-5 | 6.24902033e-5 |
| Actual/budget magnitude | 457.6680 | 67.8170 |
| Direct Hstar=LP-gp.Lx (Pa/m2) | +6.38378e-16 | -3.72966e-16 |

Both use actual generated C and reproduce gp=(4,0,0) to arithmetic precision, with da=0. Across all rows actual-production/reference error divided by its unchanged budget is at most .00769860/.01008103; corrected affine cancellation divided by its budget is at most2.16063e-11/5.06732e-11. The real production branch matches its intended raw formula but fails the local affine zero-divergence test. The sign depends on geometry/kernel, so this is not a universal negative-pressure source.

## Normal-projection candidate: algebra versus geometry

Define Hstar=LP-gp.Lx+rho_w*da. Current raw FS term is Hraw=Hstar+F.Lx. It omits the complete vector Taylor defect, leaving the nonzero tangential F_t.Lx on disordered truncated support.

The existing closedfs target in `source/JSphCpu.cpp:3239–3254` is gpcorr=gp-n*(n.F)/|n|2. Using its existing consistent expression gives HN=LP-gpcorr.Lx+rho_w*da=Hstar+(n.F)*(n.Lx)/|n|2=Hraw-F_t.Lx. This retains the normal natural-boundary response while correcting the tangential defect; with exact n=e_z the witness gives HN=Hstar, approximately zero. Because F includes **all** rho_w*Ace, the same algebra retains the old F=0 hydrostatic null. Removing only a pressure term would not provide that guarantee.

Using actual saved estimated normals instead of the known true flat normal gives a different, explicitly geometric prediction (b=+4; no candidate code was executed):

| Quantity | Cubic | Wendland |
|---|---:|---:|
| Actual FSNormal_x | -0.000600023020525 | -3.42180078405e-6 |
| Estimated n.F (Pa/m) | -0.00240009208210 | -1.36872031363e-5 |
| Predicted HN (Pa/m2) | +0.0129203026903 | +0.0000601929880743 |
| Predicted candidate pdot (Pa/s) | +0.00878336084900 | +0.0000409198412382 |
| Magnitude/original raw arithmetic budget | 107.5726 | .6548201 |

The remaining Cubic term is23.50% of raw; the Wendland prediction reverses the raw sign. Normal-angle error is amplified by n.Lx~1/h. It is geometry error, not sourcefloat roundoff, and must not be hidden by changing budgets or forcing an estimated normal vertical. Exact-normal and estimated-normal references must remain separate. Existing source already calls its closedfs Taylor target an approximation, not an exact zero-flux boundary (`JSphCpu.cpp:3189`); extending it does not by itself prove the full seepage complementarity at p=0.

## Limits and staged next decision

This is a local hydraulic operator counterexample, not a globally closed seepage problem: the finite patch's side faces need compatible prescribed hydraulic data for a global affine solution. The center's primary support does not intersect the sides; donor Cj can still reflect the finite patch through their own supports. Prescribed Ace=0 means instantaneous a_s=g, not a stationary solid. Sigmac=0 and affine p were not equilibrated by the mixture force equation, so this is not a full coupled mechanical solution of Lian Eq6 (MD175–180). Lstar is not a conservative pair flux (`JSphCpu.cpp:3172`); affine cancellation proves neither mass conservation, boundary work, energy balance nor diffusion stability. Neither AS parity, NoSlip acceleration parity, pressure clipping, constitutive dilation nor actual C08 suction causation follows.

1. Retain the completed fixture/receipts unchanged. First review a minimal private candidate that reuses the existing normal Taylor target and consistent lap for FreeSeepage FS, retains negative p and the current completed-step positive cap, and adds no public parameter. This note authorizes no code execution or public change.
2. Before any physical comparison, qualify the actual candidate against separate true-normal algebra and actual-estimated-normal references, the same b=0/+-4 fields, and retained constant/hydrostatic/nonconstant-Ace controls. Compare only to the declared arithmetic budgets for the matching numerical reference; report analytic-normal geometry error descriptively. The variable-k chain uses gpcorr+rho_w*Ace too (`JSphCpu.cpp:3255–3259`), so extending the target also requires its existing product-rule component check.
3. If CUDA is changed, obtain CPU/GPU zero-step parity and the required GPU memory check before release use. A candidate that merely applies the universal interior expression would remove the natural normal response and does not establish an impermeable/seepage boundary. A pressure or flux clip is not justified by this witness.
4. Only after component/native review decide whether one already planned, identical-parameter C08 comparison is justified. It must assess the actual common saved times, pressure and material state, not normal completion alone. No solver, half-step chain, 5Pa/.005mm bound, automatic physical acceptance or additional parameter sweep is launched here.

# C08 residual-viscosity GPU migration/cost audit r1

Read-only source/provenance audit; only this note was authored. No candidate source, build, component, solver, reader, VTK, Git or SHA action. GPU work remains held until the new H1.8 AS03 CPU force component passes and its scientific result justifies a candidate.

## Which existing GPU code can actually be reused

The standalone support/upl_c08_residual_visc_gpu_math_r1.cu is a small mathematical fixture: both Fit and Force explicitly loop j=0..n−1 for every receiver (lines54 and104). It is O(N²), has no solver cell list/wall/CTE, and is hard-Cubic. It must not be installed as a production-neighbor implementation. support/upl_c08_residual_visc_backend_r1.py only compares that math fixture with old CPU results at Parts13/14; its own receipt explicitly disclaims a full GPU-force/Darcy comparison. The old float-Ace maximum differences were2.13e−6/4.26e−6m/s², not a new H1.8 backend proof.

The actual private Release implementation is instead in outputs/upl_c08_residual_visc_gpu_r1_source/JSphGpu_ker.cu1476–1624, declared by its JSphGpu_ker.h319–330 and called by JSphGpuSingle.cpp750–793. Its actual source capture/source.json records the original private archive and three-file reversible patch; this is program-source proof, not an inference from the standalone math fixture.

Real Fit1516–1545 and Force1546–1572 each call cunsearch::InitCte and ParticleRange over dvd.beginendcell+dvd.cellfluid (1524–1529,1556–1561,1596–1600). They visit actual nearby soil cells, with no fixed-wall bonds and no neighbor count cap. Complexity is two O(N*n_nb) passes plus O(N) validation/commit, not an all-pairs N² scan. Fit uses the unregularized scaled2×2 affine fit with the original rank predicate; Force uses symmetric residuals at both endpoints and a single final float Ace commit per node. Same-ID self pairs are skipped, coincident nodes are rejected, and current V=V0J/rho mixture values are used.

## Current source must be the migration base

Current selected AS03 full3 run is bound to:

- program outputs/c08_preload_schema2_Release_r1/DualSPHysics5.2_GEO_win64.exe;
- logs/c08_preload_schema2_Release_r1.build.json;
- outputs/c08_preload_schema2_source_r1/full_source.json and full_source.zip;
- original certified PRE outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4.

This is unified MaterialLawVersion2, same-material plastic schema/contract2 (original archived JSph.cpp2980 and3797–3800), original kappa/stress/J/p retained, Wendland H=.072/dp=.04,5us, contiguous bed-last retire255/keepfalse,5000 soil IDs2060..7059 and1805 fixed IDs0..1804. The old private build is based on outputs/upl_c08_bedkeep_source_r1/source.zip, Cubic H1.2/2.5us, elastic schema1/keep5, AS.2/n3. That old archive, executable, PRE qualification and old111-object retained set cannot be relabelled as the new source. Equal6805/1805 counts do not establish equal boundary identity or material-history contracts.

## Minimal later transplant, if CPU evidence warrants it

Reuse the old two-pass/cell-search/rank/error/atomic-free gather architecture, not the old whole translation units. In a new private copy of the CURRENT schema2 archive:

1. Add a narrow helper declaration/result POD to JSphGpu_ker.h without class/CTE layout changes. Add the helper kernels/function beside dynamic pressure in JSphGpu_ker.cu. The old Pair line1505 hardcodes GetKernel_Fac<KERNEL_Cubic>; replace only with the current CPU component's exact Wendland distance/support/weight/order. Do not assume old all-pairs accumulation order is bit-equivalent to actual cell order. Alpha/rank/weight formulas must match the newly frozen CPU result, not silently inherit oldalpha.1.
2. Add one host hook to current JSphGpuSingle.cpp between Resety at archived line686 and ComputeDynamicPorePressureRateGpu at687. It must run at both actual released Pre/Cor stages, before original wall-Ace/Darcy reconstruction. Pressure/geometry/material primaries remain untouched. Keep the actual current NoPen policy and ReactionClosed=false disclosure.
3. Replace the old hook's guard752–760: require current contract2/law2, keepfalse/retire255, Wendland/H1.8/5us/AS.3n2.55 and original AV.1, while retaining original finite/ID/current-state/rank/necessary-step gates. Update sidecar policy strings/counter binding from Cubic/old source; do not mislabel its independent sidecar schema1 as PRE schema1. The old extra save hook corresponds to current JSph::SaveData at archived1359, after the real completed scalar clock, not a guessed normalized time.

The old helper validates all errors and dt*lambda_max/2<=1 before its only D2D Ace commit (1611–1620). Preserve that no-partial-commit rule. The original isolated lambda bound is not proof of coupled u-pl stability or a replacement for existing pore/natural-step limits. The alpha0 macro skips the entire helper/allocation/launch/commit; this remains a useful implementation control, with actual native equality required rather than assumed from macro-off source text.

The old builder support/upl_c08_residual_visc_gpu_r1_build.py22/44/69 demonstrates a feasible two-physical-object replacement: one JSphGpuSingle host TU plus one JSphGpu_ker CUDA TU, header included by both, all other current closed objects retained. Reuse the recipe pattern with the CURRENT build's authoritative CL/NVCC/link closure. It is not safe to take the old113-object list as current without its actual source/object proof. Original CUDA11.7/MSVC14.36/sm86/fast-math/CRT flags and private runtime copy must remain explicit; Debug memcheck/backend qualification is new evidence, not inherited from old Cubic math.

## Cost and the preserved counterexample

Old per-active-stage helper makes5 cudaMalloc/5 cudaFree calls, launches2 kernels, copies5000 unsigned errors plus5000 doubles to host (60000B), validates on host, and copies5000 float3 candidate Ace back device-to-device (60000B). Scratch is about300000B for5000 nodes. With two stages this is4 neighbor kernels and10 allocations/frees per physical step. The neighbor algorithm is sparse, but allocation and synchronization may dominate; particle count alone is not a whole-run speed estimate. A later reuse of existing array-pool scratch or device reduction would be a separately justified efficiency change, not part of this audit or automatic minimal transplant.

Old upl_c08_rvisc90_partial_review_r1.check.json preserves a genuine rejected trajectory: reported step4212949 necessary pore bound2.4992403879125872us was below fixed2.5us; last complete save was10.530000000542486s (tau .5300000001682292),53 frames. No unsaved failure time is reconstructed. Its later pressure/pair behavior was not accepted. That failure remains evidence against assuming a residual-viscosity benefit; neither sparse implementation nor a passed math comparison proves a repair in current H1.8 AS03.

No GPU candidate is prepared now. The next decision belongs to root after the new current CPU force/RHS scientific review; no new window, PRE or other psi run follows this note.

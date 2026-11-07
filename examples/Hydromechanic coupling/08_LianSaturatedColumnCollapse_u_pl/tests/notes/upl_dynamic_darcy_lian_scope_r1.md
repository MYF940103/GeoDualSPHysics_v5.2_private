# Current dynamic Darcy and Lian second-derivative scope

Read-only source review after material checkpoint `d3c743b`; no build, solver,
native decode, source change, or server case08 r2 dependency change.

- CPU: `src/source/JSphCpu.cpp:4239`, `ComputeDynamicPorePressureRateCpuT`;
  host kernel dispatch at 4348 supports Wendland and Cubic.
- GPU: `src/source/JSphGpu_ker.cu:1659`, `KerComputeDynamicPorePressureRate`;
  host wrapper at 1762 and `JSphGpu.cpp:1921` use the same formulation.
- CPU4290–4300 / GPU1696–1716 use the pressure weight
  `w=Vj*d·(Ci+Cj)*gradW/(r2+Eta2)`, with `d=xi-xj`, `Vj=V0*Jj`.
- The first pressure gradient and acceleration divergence use receiver `Ci`.
  The interior scalar term is `lp-gp·lx+rho_w*divAce`; `Ace` excludes gravity.
  Thus pair symC and the affine Taylor defect are already present dynamically.
- `PoreDarcySymmetricCorr` is a different, default-zero legacy u-pw soil-pair
  option (CPU2639, GPU2315). `JSph.cpp:658–659` rejects it and the old mDBC
  pore-interpolation option when the dynamic master switch is enabled.
- Dynamic k uses `k(J)=k0*exp((J-1)/((1-n0)*Ck))` (CPU4213), with the separate
  product-rule term `k'(J)*gradJ·(gp+rho_w*Ace)` (CPU4320 / GPU1730).
  This is a smooth scalar conductivity formulation, not a conservative
  material-interface flux. Standard `gamma_w=rho_w*9.80665` supplies units.

Lian2023 printed p6 Eq23 is the Hessian expression. With identical correction,
denominator, neighbor/volume and first-gradient operands, its trace is Lstar.
The literal receiver-C/r2 formula must remain distinct from current pair-C/Eta2.
Computing/storing the full tensor alone adds no constant-isotropic-k operator.
Neither this trace identity nor affine cancellation establishes P2 exactness,
pair conservation, boundary consistency, or coupled stability.

Retain, do not rerun, case02 `upl_lian_eq23_reference_review_r1.json` and
`upl_lian_eq23_review_r1.json`: they already distinguish these variants and
report tensor/trace, truncation, disorder and matrix behavior. The 1536-response
`upl_lian_variable_root_r1.json` found no uniform Eq25 pair-k improvement.
Those tests used Wendland h/dp1.8 and did not reproduce real C08 mixed walls.

Current walls reconstruct state/C/Ace (CPU4007/4096/4124; GPU1751), followed by
the complete Darcy rate. Free-seepage raw-head, closed-face Taylor correction
and active drainage remain different branches. Public scope is bounded by
`JSph.cpp:639–677,3761` and backend initialization; this note opens no scope.

Next useful information is actual C08 Cubic/deformed/disordered geometry,
separating interior, wall and free-surface polynomial/known-Ace responses.
Existing Cubic, free-seepage and Ck2 zero-step components can be reused.
Typed22 contains neither CorrMat nor total finished Ace: an offline rebuilt C
is not native saved C, and HydroMechLoadAce is not total Ace. Any actual
snapshot `FS/C -> wall state/C/Ace -> rate` call requires its own clear admission;
it is not authorized by this review and implies no new half or long run.

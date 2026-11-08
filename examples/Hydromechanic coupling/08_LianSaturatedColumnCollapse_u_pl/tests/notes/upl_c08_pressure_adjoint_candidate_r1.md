# Frozen pressure spatial pairing: offline candidates only

Read-only source/math audit; no source changes, new computation, solver, build or decoder. The new name was absent and exact git ls-files was empty before writing this note.
The existing actual-AS spectrum summary has 8 frozen blocks and all/FS0 views. The 4956/4959 FS0 principal views at tau .63/.64 retain max real eigenvalues +1665.73/+2223.86 s^-1; direct-only views are negative. These are conditional local pressure spectra, not a full coupled-domain cause proof.

## Actual operators and signs

For a complete bidirectional fluid stencil, freeze V_i=V0 J_i, rho_i, C_i and geometry; g_ij=grad_i W_ij=-g_ji. Define the receiver-C divergence

    (D v)_i = sum_j V_j (v_j-v_i) dot (C_i g_ij).

GPU Darcy uses this divergence on Ace at JSphGpu_ker.cu:1551-1565. Theta uses the same mathematical receiver-C form at 1942-1954, but its packed-float geometry/factor path is not bit-identical to Darcy's double-position path. An exact algebraic adjoint must use the same chosen D coefficients, full stencil and cutoffs on both sides; do not silently identify these floating-point implementations.
Let Vp=diag(V_i), Vv=diag(V_i I), R=diag(rho_i I), M=R Vv. The negative weighted adjoint gradient and pressure acceleration are

    Gadj = -Vv^-1 D^T Vp,
    Bad  = M^-1 D^T Vp = -R^-1 Gadj,
    (Bad p)_i = -1/rho_i sum_j V_j (p_i C_i+p_j C_j) g_ij.

Thus v^T M Bad p = p^T Vp Dv: pressure kinetic power cancels the compression storage power from pdot=-(Kw/n)Dv. For the full symmetric total stress T=sigma'-pI, the corresponding mechanical pair is (T_i C_i+T_j C_j)g_ij, not (T_i+T_j)(C_i+C_j)g_ij/2.
Current J momentum is raw (T_i+T_j)g_ij at JSphGpu_ker.cu:1833-1842. Current Darcy LP uses pair C_i+C_j, then subtracts the receiver gradient defect (1557-1559,1581-1583); variable-k adds the explicit gradJ chain (1589-1596). This non-nested Lstar is not algebraically D Gadj. Consequently Bad alone gives no negative-semidefinite guarantee for current Lstar + rho_w D Bad, including its FS/chain additions.

## Minimum next offline comparison

1. Reuse the already evaluated current matrix as A0. Build A1 with only the raw pressure-to-Ace map replaced by Bad; retain the current direct Lstar/raw-FS branch, variable-k chain, actual-AS pressure Jacobian, native coefficients, pressure unknowns and outside-held policy. This isolates the mechanical gradient mismatch without pretending it is a production pressure-only patch.
2. A separately labelled fully paired algebraic control uses B=diag(Kw/n_i), Ck=diag([k_i/gamma]*(1-rho_w/rho_i) I):

       A_pair = B D Ck Gadj.

   It comes from pdot=B D diag(k_i/gamma I)(Gadj p+rho_w Bad p), not from silently rewriting the existing product-split chain. With Wpressure=Vp B^-1=diag(n_i V_i/Kw) and z=D^T Vp p,

       p^T Wpressure A_pair p = -z^T Ck Vv^-1 z <= 0

   for k_i>=0 and rho_i>=rho_w. This proves only a frozen pressure-only dissipative quadratic form; AS, theta/velocity/stress dynamics and time discretization are outside this inequality. Add the same existing AS channel separately and report whether the sign survives.
3. Report the storage-weighted symmetric part and max-real eigenvalue together with constant/affine/hydrostatic responses on the same cloud. Construct full matched products before restricting to the same FS0 principal unknowns; outside perturbations remain zero. A principal view is not a whole-domain spectrum, and FS neighbours can still affect its frozen coefficients.

## Required limits before any production proposal

- Gadj 1 = sum_j V_j(C_i+C_j)g_ij is generally nonzero on a truncated/irregular cloud. Adjointness alone does not establish constant-pressure nullspace, second-order consistency or hydrostatic balance. The nested operator can also have extra null/checkerboard modes; inspect these rather than declaring a negative spectrum sufficient.
- The dissipative proof assumes complete matched fluid stencils and appropriate zero-work/zero-flux boundary terms. The actual free-seepage raw branch, full-only positive ponding, walls and external tractions are not supplied by that proof. Start with the same far-wall FS0 conditional view; do not overwrite the boundary policy to obtain a favourable sign.
- Bad needs C at every force neighbour. C reconstruction itself needs each neighbour's full moment stencil: pressure columns are two-hop, but qualifying the needed C can require a third geometry hop. Mark unsupported/fixed-contaminated stencils rather than truncate them.
- If subsequently changing production momentum, apply the pairing to all of sigma'-pI and consistent external loads. In particular uniform Cryer q must pair as +q(C_i+C_j)g_ij with the same V_j/rho_i to cancel T=-qI; the current raw +2q pair at 1853-1859 belongs to the current raw force. AS/AV and wall/contact work remain separate qualified terms.
- The existing native reconstruction is a frozen saved-state/packed proxy, not the unsaved stage replay. A1 improving its eigenvalues would support one mismatch hypothesis; neither A1 nor A_pair is an accepted replacement or an instruction to launch a solver.

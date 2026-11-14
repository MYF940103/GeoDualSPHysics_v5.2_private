# Finite-Kw compatibility with Lian TPI / beta: bounded audit r1

2026-11-15. Read-only audit; only this note is new. No code/build/component/solver/reader/native/input/PRE/Git/SHA action or physical admission. Earlier assets remain unchanged.

## Primary and bound-source evidence

Local paper: src/papers/u-pw/Lian 2023 u-pl.md395-404 explicitly removes n/Kw before deriving TPI;459-478 gives Eq38/39 pressure-history extrapolation;484-519 acknowledges remaining stability limits and the LF procedure;584-608 gives Eq47 only for plastic-deformation applications and warns against negative-pressure clipping. Original PDF printed7-11 was previously reviewed.

Physical reference: tests/outputs/c08_preload_schema2_source_r1/full_source.zip. CPU JSphCpu.cpp3174-3277 evaluates the current full dynamic rate, including raw-FS, acceleration and variable-k chain;3346-3377 advances p_n+.5hR_n and p_n+hR_h. GPU JSphGpu.cpp1756 allocates Preg,1764 swaps in this step's full p_n, and1908 frees it. Preg is **not** p_(n-1). P0 is a fixed reference, not either history value.

## Dimensions and original transient

The current equation, multiplied by gamma_ref, is

    M(J) p_dot = F(p,a,J,theta),    M = gamma_ref*n/Kw.

k is hydraulic conductivity[m/s]; gamma_ref=rho_w*9.80665[Pa/m], distinct from actual stored body gravity. M and beta have units1/m; pressure-row A/S have1/(m*s); F,B,E,N(p) havePa/(m*s). Dividing the row by gamma also divides M and beta. The paper's bare beta=.04 has no portable SI/row-normalization contract; it is not a dimensionless coefficient to insert anywhere.

A finite-M method must discretize **M_h*(pnew-pn)/h**, not (Mnew*pnew-Mn*pn)/h. The latter adds p*M_dot and changes this pressure equation. Likewise the conditional nV*p/Kw storage proxy is not exact fluid mass. Changing J/n cannot silently turn the method into a different conservative storage model.

A coherent finite-M extrapolated/IMEX extension exists mathematically, but is not the paper's incompressible TPI. For a declared half-state decomposition M_h R_h=B_h+N_h(ph)-S_h ph, a diagonal-CN form is

    (M_h/h+S_h/2)pnew=(M_h/h-S_h/2)pn+B_h+N_h(ph).

The increment includes hR_h+(hS_h/M_h)(ph-pn), divided by1+hS_h/(2M_h); merely damping hR_h loses the compensation. A true full-history ph=pn+.5*(pn-pPrevious) has a fixed-linear-row second-order expansion, not a proof for moving J/k, AS, walls, FS or coupled solids. This is an existence example, **not a selected new CN candidate**. Genuine global implicit finite-M pressure would require a converged pressure block, with a(p)/wall/AS either explicitly lagged or consistently linearized/iterated. Taylor/chain/ghost/AS do not guarantee SPD/CG applicability; matrix-free still costs iterations.

## Why direct Eq47 does not preserve finite-Kw physics

Adding the paper term to a finite-M row gives

    M(pnew-pn)/h + beta(pnew-pAlpha)/h = B+N(pAlpha)-S*pnew,
    pAlpha=pn+alpha*(pn-pPrevious).

For a smooth fixed negative branch, constant h and finite force/source coefficients, pnew-pAlpha=(1-alpha)h*p_dot+O(h^2). Leading capacity becomes **M+beta(1-alpha)**. This alteration survives h->0. With current n~.35,Kw1GPa, M~3.4323e-6/m. Under an explicitly assumed SI beta=.04/m,alpha=.5, added capacity=.02/m~5827M and effective Kw~.172MPa. Existing coupled elastic-negative-branch algebra already shows a growth counterexample; it does not disprove the paper's qualified plastic model.

An original-transient-preserving penalty would require a different, independently derived vanishing-step/increment-defect design or explicit physical storage recalibration. It would no longer be Eq47 as written. No model is selected; alpha1 extrapolation is not an implicit solve.

## Missing lifecycle / qualification and decision

History needs ID-owned p_(n-1), previous dt/clock/valid through sorting/periodic/compression, rotated once after successful full-step boundary commit. Old PRE lacks5us history; Part999 is not a prior step. Cold start differs from exact restart. Eq47 additionally needs defensible full-commit plastic-dilation eligibility; materialTypePlastic, accumulated kappa or p<0 alone is insufficient. Psi0 Smooth has no shear-plastic dilation; tension/apex volume return is not automatically that paper mechanism.

Existing evidence is retained: the late genuine finite-Kw CN step changed p only.001460279Pa RMS and.0078125Pa maximum; the CPU short X0 beta0 changes the model to M0, had mixed indicators and~45% extra observed loop time. Neither admits finite-M beta or C08 TPI. Implicit integration alone does not repair spatial nonadjointness, plastic regularization or unclosed contact/Darcy reaction.

**Root decision:** no beta/TPI/CN trajectory now. The new four-weight manufactured-field evidence instead proceeds to its separately reviewed private CPU implementation qualification. Default pressure behavior remains unchanged; no new pressure parameter, clipping, history or solver chain is introduced by this audit.

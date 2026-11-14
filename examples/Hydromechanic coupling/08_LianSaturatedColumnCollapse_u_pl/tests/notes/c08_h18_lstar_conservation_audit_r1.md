# C08 receiver-C/bare: conditional conservation and stability audit

Read-only mathematics for interpreting the one bounded Lstar window, not a new operator, test requirement or physical acceptance. No solver/reader/build was run for this note. Source is the current schema2/law2 full archive `outputs/c08_preload_schema2_source_r1/full_source.zip`: CPU `JSphCpu.cpp:3230`, GPU `JSphGpu_ker.cu:1561`, with the original adjoining LP/Lx/Gp/Da/product-rule/FS expressions. The private candidate changes only the shared LP/Lx pressure weight. The passed CPU manufactured comparison proves implementation and improved fixed-field consistency; it does not prove conservation or trajectory stability.

## The original LP-only identity has conditions

Let `d=x_i−x_j`, `g=Fac(r²)d`, `V_i=V0 J_i`, and freeze the geometry/J/C during this calculation. For a reciprocal fluid–fluid neighbor pair, original

`s_ij = d·(C_i+C_j)g / (r²+Eta²)`, `LP_i=Σ_j V_j s_ij(p_i−p_j)`.

Reversing the pair changes both d and g signs, so `s_ji=s_ij`. Consequently `Σ_i V_i LP_i=0` for a complete reciprocal fluid-only pair set. If every `s_ij<=0`, then

`Σ_i V_i p_i LP_i = Σ_(i<j) V_i V_j s_ij (p_i−p_j)² <=0`.

For constant positive k and fixed positive `W_i=n_i V_i/Kw`, this is the LP-only contribution to `d[½Σ W_i p_i²]/dt`, up to k/gamma. It is not a proof for the complete dynamic equation, changing weights, variable k, prescribed ghost fields or free-surface projection. Sign requires the relevant correction quadratic forms; finite/rank guards alone are not an independent all-neighbor spectral proof.

## Receiver-only correction loses that volume-weighted reciprocity

Write the new pair coefficients as `a_i=2 d·C_i g/r²`, `a_j=2 d·C_j g/r²`. Then

`Σ_i V_i LP_i = Σ_(i<j) V_i V_j (a_i−a_j)(p_i−p_j)`.

The quadratic expression becomes

`Σ_(i<j) V_i V_j [ (a_i+a_j)/2*(p_i−p_j)² + (a_i−a_j)/2*(p_i²−p_j²) ]`.

The second part is not sign-definite. The old bare pair identity is recovered when `dᵀ(C_i−C_j)d=0` on every participating edge, including uniform C, but not for a general varying anisotropic correction field. Thus the candidate must not be called more conservative merely because its manufactured residual is lower.

Nonreciprocity does not by itself imply unstable eigenvalues. If all new coefficients `a_i<=0`, V/n/k are positive and only the frozen LP term acts, its pressure matrix has nonnegative off-diagonal entries and zero fluid-only row sums. Gershgorin then gives `Re(lambda)<=0`; prescribed walls may give row-sum loss plus forcing rather than a closed fluid system. A sufficient forward-Euler monotonicity bound is `dt<=1/(-A_ii)` on the actual frozen pressure matrix. The present pore/natural necessary-step guards are not this complete rowwise/spectral certificate, nor is that LP-only statement a stability proof for the coupled predictor/corrector.

The full rate also has the Taylor correction `−Gp·Lx`, raw-FS `rho_w A_i·Lx`, acceleration divergence Da, compressional theta and variable-k chain. Those terms need not form an M-matrix or the preceding quadratic identity. With receiver-dependent k_i, even the original symmetric LP weight multiplied by k_i is not generally pairwise conservative; the existing product-rule chain is not a conservative pair flux. Fixed ghost nodes have no matching evolved pressure/storage row. Their hydraulic extension plus FS projection cannot be counted as a closed-system conservation proof. Contact/Darcy reaction also remains explicitly unclosed.

## What the existing91-frame native data can establish cheaply

Keep all5000 material IDs and every actual clock; compare original AS03 and Lstar at identical saved steps/times without interpolation. Existing22 fields support pressure and p−P0 signed means/RMS/extrema/quantiles, FS classifications/switches, J/n/rho/k and ledger, kappa-history distributions, velocity/motion and real3D nearest-neighbor/unique-close-pair counts. They do not contain C, pressure-rate or separated force/flux components, so they cannot directly certify a pressure-matrix spectrum, `Σ V LP`, exact Darcy mass transport or the causal force behind clumping.

`S=Σ(nV/Kw)p` is a signed storage proxy; `E_p=½Σ(nV/Kw)p²` is a conditional pressure-storage quadratic. Neither is fluid mass or total coupled energy. In this constant-Kw ledger `nV/Kw=V0[J−(1−n0)]/Kw`, so changes in weights matter. An exact saved-interval product decomposition is `ΔS=Σ[W_bar Δp+p_bar ΔW]`; it can separate observed pressure and volume contributions without pretending to integrate unsaved RHS/fluxes. The saved last-stage theta is not a full interval integral. FS constraints, external drainage/ghost extension, pressure quantization and changing J may alter S; its drift alone cannot assign a mechanism or prove a conservation failure.

For the bounded physical review, report whole-soil plus fixed material/top/bottom and descriptive near-bed/interior/FS cohorts. Check whether pressure improvement coexists with smaller nearest-neighbor gaps, larger close-pair populations, negative-pressure tails, J/k excursions, excessive plastic localization or arrested motion. Kappa>0 is accumulated history, not proof of currently active plastic flow. Keep negative pressure and signed observations; do not use smoothing, clipping, fitted loading/time/radius, another half chain or a changed threshold to hide an unfavorable tradeoff. Existing native safety passing remains separate from this scientific interpretation.

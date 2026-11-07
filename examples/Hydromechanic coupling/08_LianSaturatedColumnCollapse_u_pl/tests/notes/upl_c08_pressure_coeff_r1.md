# C08 saved-geometry pressure coefficient probe r1

Author-only; no execution during preparation. One later offline invocation:

`D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_pressure_coeff_r1.py --execution-authorized`

It consumes only the already passed `outputs/upl_c08_plane_partial_r1` native54 prefix and `logs/upl_c08_plane_partial_r1.check.json`, plus the existing typed-layout loader and audited float Cubic helper. The solver failed at unsaved step4218523; this analysis does not reconstruct that state or relabel54 as60. Parts0,47,48,49,53 are actual first post-save10.01,10.48,10.49,10.50,10.54s (actual binary64 clocks retained), not a synthetic PRE/t0. Only native IDs4808,4859,5809,5556 are selected.

## Exact algebra and reconstruction scope

Production references: `JSphGpu_ker.cu:742–762,778–870` constructs the fluid correction matrix; `1514–1520,1538–1549` constructs the pressure operator. `FunSphKernel.h:51–66,104–115` supplies float Cubic constants/Fac; `JSph.cpp:1712–1729` supplies float H/R2 and Eta2. No new numerical tolerance, determinant floor, clipping or regularization is introduced.

Let d=x_i−x_j, g=Fac(float(r2))*d, Vj=V0*Jj, V0=float(3.316)/2072.5. Fluid C is the inverse of M=−sum Vj*d tensor g, with the production exact-zero determinant identity fallback. Every neighbor j obtains its C from its complete own support, not the receiver's restricted cloud. The proxy uses native double coordinates and float(rr2) for this moment membership, the existing nonself ALMOSTZERO=1e−18f cutoff, and audited float Fac. Actual GPU FS reconstruction uses packed-float PosCell differences and GPU cell accumulation order; these are not exported. Thus the formula/float constants match the implementation, but reconstructed C is explicitly a CPU-style geometry proxy, never original native C or GPU bit identity. Condition number and minimum symmetric-moment eigenvalue are observations, not new admission limits.

Only receivers at least2R from every saved fixed B are considered. Both each receiver's Darcy/C stencil and every contributing neighbor's full C stencil are checked against all saved fixed particles. Any fixed support leads to a `not_evaluated_fixed_wall_scope` row; it is never silently dropped or replaced by an invented ghost. KDTree's next-float broad phase only covers rounding into the unchanged moment cutoff; exact stage predicates still decide memberships.

Define gi=Ci*g, gj=Cj*g, wj=Vj*d·(gi+gj)/(r2+Eta2), lx=sum d*wj, gJ=sum Vj*(Jj−Ji)*gi, ki=saved k_i, k'_i=ki/[(1−n0)Ck], A=Kw/(ni*gamma), gamma=1000*9.80665. For rate_i^p=sum aij*(p_j−p_i):

- raw LP: aij_raw=−A*ki*wj;
- Taylor increment: aij_T=−A*ki*Vj*(gi·lx);
- conductivity-chain increment: aij_k=A*k'_i*Vj*(gJ·gi).

The saved FS2/3 branch uses raw+chain; FSType0 uses raw+Taylor+chain. LP/Lstar without chain are reported as diagnostic decompositions, not different solver runs. In this rate convention aij<0 violates local minimum preservation; for −L in an M-matrix convention this is positive off-diagonal. A negative coefficient alone is not proof of a positive-real-part global eigenvalue or the observed pressure failure's cause.

`worst_unit_minimum_rate_Pa_s` sets receiver pressure0, negative-coefficient neighbor values1Pa and other neighbors0, keeping geometry/J/C/Ace frozen. It is the most negative row rate for these bounded local perturbations. Existing-pressure contributions include only the pressure-dependent part; compression theta and acceleration terms are not replayed. The pressure-vs-Ace coupling, missing reaction feedback, current stage FS changes and global spectrum are outside this probe. The coefficient/direct-expression roundoff difference is reported without a fitted acceptance threshold.

Fresh products are `figures/upl_c08_pressure_coeff_r1_rows.csv`, `_pairs.csv`, `_local_points.csv`, `_local4808.png`, `_local5809.png` and `.check.json`. The local native plots show parts47/48/49 around4808 and part53 around5809, FS0/other circles versus FS2/3 triangles, the reconstructed receiver C, and red edges for negative current off-diagonal coefficients. Each panel uses its own labelled full raw pressure range; values are not clipped, smoothed or interpolated. The CSV preserves every plotted point. Part0 is a first-post baseline only. Native fixed-particle derived volume fields are0 markers, so the ledger comparison is soil-only; no fixed source is silently given zero weight. No global5000 matrix, spectrum, time integration, decoding, source change, dt change or parameter adjustment is performed. `passed` means the sealed-data analysis completed, not that all coefficients have the desired sign or that the physical case passed.

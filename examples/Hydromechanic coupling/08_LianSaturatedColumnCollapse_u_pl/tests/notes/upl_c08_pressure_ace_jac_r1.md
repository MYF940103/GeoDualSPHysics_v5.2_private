# C08 pressure-dependent Ace/Darcy local Jacobian r1

Author-only. One later offline command from C08:

`D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_pressure_ace_jac_r1.py --execution-authorized`

This new probe leaves the validated `upl_c08_pressure_coeff_r1.py`, its outputs, native54 and production source unchanged. It consumes the same five actual saved post states/4 native IDs. The first post-save is not PRE. Only a far-wall fluid patch is admitted: every original Darcy/C stencil and every complete mechanical stencil required for the pressure-to-Ace two-hop composition is checked; any fixed particle causes an explicit not-evaluated row. There is no global5000 matrix, eigenvalue solve, time integration, solver, decoder, dt change or parameter tuning.

## Mechanical pressure derivative

GPU `JSphGpu_ker.cu:1712–1723,1754–1779` and CPU `JSphCpu.cpp:2303–2322` use J-derived volume/inertia with a raw momentum gradient, not Ci/Cavg:

`a_i^p = −sum_l [Vl/rho_i * (p_i+p_l) * h_il]`, where h_il is the raw mechanical gradient, Vl=V0*Jl and rho_i is double J-derived mixture density, not float native density cache.

Thus the vector derivative B_im=da_i/dp_m is `−sum_l Vl*h_il/rho_i` for m=i, `−Vm*h_im/rho_i` for a direct mechanical neighbor m, and0 otherwise. Both p_i and p_l terms are retained. Its row sum can be nonzero near truncated supports; it must not be silently replaced by a pressure-difference gradient or forced to annihilate a constant pressure. The mechanical proxy first casts native coordinate differences to float components, uses the float squared-distance cutoff, float Cubic Fac and float gradient products; J-volume/rho weights are double. Actual GPU packed PosCell differences, FMA and accumulation/float increment rounding are unavailable, so this is a real-algebra linearization of the audited expression, not a bit replay or AD of the quantized production function.

## Composition into the pressure equation

Use the frozen prior-probe direct pressure row H^p, gi=Ci*gradW, lx=sum d*wj, gJ=sum Vj*(Jj−Ji)*gi, k'_i=ki/[(1−n0)Ck], A=Kw/(ni*gamma), and f_i=1 only for saved FS2/3. Source: `JSphGpu_ker.cu:1522–1523,1538–1549`, CPU `3233–3260`.

`H^A_im = A*rho_w * [ki*sum_j Vj*gi·(B_jm−B_im) + f_i*ki*lx·B_im + k'_i*gJ·B_im]`.

The full conditional pressure row is H=H^p+H^A. For each receiver, all its direct Darcy neighbors j and each j's entire mechanical support are included, giving every two-hop pressure column. The FS ai·lx term and the conductivity-chain ai term are reported separately, not omitted. C_j is still reconstructed from its own full moment support through the unchanged prior Cloud. Body gravity, fixed effective stress, velocity/AV, material state, J, theta and FS are held fixed; their constant source terms and actual finished Ace are not claimed to have been reproduced. The completed-step finite-positive-p free-surface projection and the time integrator are not linearized here.

For ideal smooth constant-density continuum operators, a^p=−gradp/rho reduces pressure diffusion by1−rho_w/rho (roughly0.52 here). The reported local-continuum scaled row is only this limit, not an alternative run or an exact discrete identity. Varying rho introduces additional terms; two unequal discrete gradients need not achieve the ideal cancellation.

Each CSV preserves the self diagonal, all off-diagonal columns, row sum/constant1Pa response, negative off-diagonal weight, unit local-minimum/maximum perturbation counterexamples, and native-p pressure-channel contributions. Because momentum uses p_i+p_j, the composite row is not forced into sum aij*(p_j−p_i); a nonzero constant-pressure row sum is retained. Expansion roundoff is observed without fitting a new tolerance. Negative coefficients, positive diagonal or a negative response at the saved negative-pressure point alone do not prove a positive global eigenvalue, a complete coupled instability or the unsaved failure's cause.

Fresh products: `figures/upl_c08_pressure_ace_jac_r1_rows.csv`, `_coefficients.csv`, `_pressure_Ace.csv`, optional `_not_evaluated.csv`, and `.check.json`. `pressure_Ace` is the pressure-only partial acceleration on this frozen geometry, explicitly not native total acceleration. `passed` means the sealed-data observation completed, not physical acceptance or permission to weaken existing guards.

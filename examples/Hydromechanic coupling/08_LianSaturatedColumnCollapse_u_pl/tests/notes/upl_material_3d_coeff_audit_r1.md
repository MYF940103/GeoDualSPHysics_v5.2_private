# MR1: narrow 3-D DP coefficient audit (author/read-only)

No production edits, build, material execution, spatial solver or package change. The delivered r2 program/input remains frozen. This proposes a material component stage, not 3-D u-pl admission.

MR1 is an independent return algorithm rather than a patch only to dilation. It evaluates the yield surface at the new continuous history, uses deviatoric plastic history, includes the corresponding softening derivative in the scalar return, and evaluates decaying dilation inside that same return. The old `LegacyFast` implementation remains default. Adding only a new psi value to the old algorithm would retain its old/new-strength consistency and history-definition differences. Float material constants and float persistent kappa remain unchanged.

## Primary equations and actual source

Visually inspected original GeoDualSPHysics PDF pp.3-4, Eqs.11-12c, and Bui & Nguyen (2021) PDF p.16, Eqs.74-75. GeoDualSPHysics calls the plus branch “middle circumscribes”; retain this project's `DP_MC` name rather than silently relabeling the fit. Bui Eq.75 gives the minus branch. Lian (2023) PDF p.5 Eq.16 is the plane-strain fit; Eqs.17-19 give strength/dilation histories. The previously closed primary audit distinguishes Bui Eq.78 deviatoric history from the printed full-norm/sign inconsistencies.

- `source/DualSphDef.h:410-412`: existing selectors `DP_PS=3`, `DP_MC=2`, `DP_C=1`.
- `source/JSphCpu.cpp:3812/3832` and `source/JSphGpuSimple_ker.cu:135/155`: legacy `UpdateDPvars` / `Updatedfdk` already contain both 3-D coefficient branches and their full strength derivatives. They use float arithmetic and `1.732f`; do not modify them or use their output as double-accuracy truth.
- `source/FunSoilMaterial.h:43/51/58`: MR1 `At` / `Evaluate` / `Return` currently hardcode DP_PS. Its invariants and stress return already carry all six 3-D tensor components; “plane strain” here primarily identifies the admitted coefficient/kinematic scope, not omission of sigma_yy.
- CPU material calls at `JSphCpu.cpp:4867/5021`; GPU at `JSphGpuSimple_ker.cu:720/939`. CPU has `DPCtes`, and GPU already has compile-time `dpctes` for each Pre/Cor specialization.
- `JSph.cpp:4075-4085` currently rejects non-2-D/non-DP_PS MR1. That gate stays unchanged during the first coefficient/component stage.

## Exact fixed-friction extension

Use eta = -1 for DP_C, eta = +1 for DP_MC, with angles in radians:

\[
D_\theta=3+\eta\sin\theta,\quad
\alpha={2\sin\phi\over\sqrt3D_\phi},\quad
k_c={6c\cos\phi\over\sqrt3D_\phi},\quad
\beta={2\sin\psi\over\sqrt3D_\psi}.
\]

For fixed phi, `c=cr+(cp-cr)exp(-nc*kappa)` and `psi=psi0*exp(-sf*kappa)`, MR1 needs:

\[
f_\kappa=-k_c'={6\cos\phi\over\sqrt3D_\phi}\,n_c(c-c_r),\qquad
\beta_\kappa={6\cos\psi\over\sqrt3D_\psi^2}(-s_f\psi).
\]

This is the literal partial derivative of `f=alpha*I+q-kc` at fixed stress, not a signed hardening modulus. Psi does not appear directly in f. Its derivative enters through the flow direction and returned I. The legacy formulas also give `alpha_phi=6cos(phi)/(sqrt3*D_phi^2)` and `kc_phi=6c*(-3sin(phi)-eta)/(sqrt3*D_phi^2)`, confirming the existing plus/minus `Updatedfdk` branches. These identities are an audit, not authorization to enable phi softening.

With `q=sqrt(J2)`, `h_kappa=1/sqrt3` (not the smoothing length), and `k=k_old+h_kappa*lambda`, preserve the existing MR1 equations:

\[
I(\lambda)=I_{tr}-9K\beta(k)\lambda,\quad q(\lambda)=q_{tr}-G\lambda,
\]
\[
F=q_{tr}-G\lambda+\alpha I(\lambda)-k_c(k),\qquad
F'=-G-9K\alpha[\beta+\lambda\beta_\kappa h_\kappa]+f_\kappa h_\kappa.
\]

The deviatoric norm gives the same `h_kappa` in full 3-D: `s:s=2q^2`, hence `sqrt((2/3)*dep:dep)=lambda/sqrt3`. Stress recovery remains `s_new=(1-G*lambda/qtr)*s_trial` plus `I_new/3` on its three diagonal components. No extra plastic-volume term belongs in J; J still integrates total velocity divergence. No apex/cap or phi-softening extension is implied.

## Authorized next component milestone (author-only preparation first)

1. First change only shared material coefficient selection and the four material call sites: `FunSoilMaterial.h`, `JSphCpu.cpp`, `JSphGpuSimple_ker.cu`. Pass existing `TpDPCtes` through `At/Evaluate/Return`; preserve DP_PS literal arithmetic and default arguments used by existing material fixtures. Invalid fit values must be rejected. A neutral native adapter name such as `ReturnStress` can replace `ReturnPlaneStrain` at its four actual source callers; no retained test source calls that adapter. No new StSoilCte field, CUDA wrapper parameter, particle array or neighbor pass is needed. GPU specialization can fold the fit choice. Shared-header changes require the relevant new CUDA objects; never replace the delivered r2 executable.
2. Reuse the small material CPU/CUDA fixture pattern, with a new local case selector rather than changing frozen 71-case input. For DP_C and DP_MC: fixed phi25/40, psi0/+2.5/-5, constant-strength and c/psi-decay cases at kappa0/.5; elastic, ordinary radial, unloading, nonzero xy/yz/xz, and explicitly unsupported hydrostatic/apex/invalid cases. Keep ordinary radial stresses compressive enough to stay away from the apex. Carry the original return/root/compliance budgets; saved-float kappa residual remains distinct from the continuous root residual.
3. Independently finite-difference f(kappa) at fixed stress and beta(kappa), then F(lambda) strictly inside the root bracket. Use double kappa for these derivative checks, not repeated float storage. Declare truncation/roundoff budgets from the chosen finite-difference increment before executing; do not reuse a pressure/half-step threshold or tune a physics tolerance to the result. Include sf0/nc0 zero-derivative controls and negative psi signs.
4. For all six components, check `q/I`, full tensor elastic-compliance recovery, plastic trace `3*beta*lambda`, and deviatoric increment `lambda/sqrt3`. Add a proper non-axis 3-D rotation of one nonzero-six-component trial: returning then rotating must agree with rotating then returning within the original tensor arithmetic budget. GPU adapter ordering is `(xx,xy)/(xz,yy)/(yz,zz)`; compare named members, not struct padding.
5. Only after the material checks pass, exercise actual CPU/GPU Pre/Cor wrappers for both existing DP modes with those six-component trials, Pre-kappa restore, Cor commit and existing error-bit rejection. Retain DP_PS regressions. A later narrowly reviewed ordinary 3-D material admission would modify `JSph.cpp` and XML guidance; leave dynamic free-body/wall, 3-D plastic u-pl, mDBC, HG and restart gates closed. No new spatial/half chain is part of this proposal.

Primary files: [GeoDualSPHysics](<../../../../../src/papers/PDF/GeoDualSPHysics.pdf>), [Bui 2021](<../../../../../src/papers/PDF/Bui 2021-CG.pdf>), [Lian 2023](<../../../../../src/papers/PDF/Lian 2023 u-pl.pdf>). Existing detailed history/sign audit: [upl_material_primary_r1.md](upl_material_primary_r1.md).

# General DP return: candidate and migration audit

Authorized development preparation only. New candidate: `tests/support/upl_material_general_candidate_r1.h`; no production source, active solver, old failed r1 probe, or delivered r2 file is changed. This is not the final full-function replacement: non-radial/tension policy and general path continuation remain necessary work.

## Coefficients and derivative contract

All three choices retain `DP_phi`, `DP_kc`, `DP_psi`. The angle/strength histories use the same accumulated deviatoric kappa:

`phi=phi_r+(phi_p-phi_r)exp(-n_p*kappa)`, `coh=coh_r+(coh_p-coh_r)exp(-n_c*kappa)`, `psi=psi0 exp(-sf*kappa)`.

The parameters remain float; temporary coefficients, derivatives and stress/root arithmetic are double. `UpdateDPvars(material,kappa,DPCtes)` returns those three coefficients and `dDP_phi_dk`, `dDP_kc_dk`, `dDP_psi_dk`. It is independent of lambda, so the eventual apex branch can reuse it at its own correct history.

For DP_C/DP_MC let `s=-1/+1`, `D=3+s*sin(phi)`. Then

\[
\alpha_\phi={6\cos\phi\over\sqrt3D^2},\quad
(k_c)_\phi={6c(-3\sin\phi-s)\over\sqrt3D^2},\quad
(k_c)_c={6\cos\phi\over\sqrt3D}.
\]

DP_PS retains `alpha_phi=9sec²(phi)/(9+12tan²(phi))^(3/2)`, `kc_phi=-36c tan(phi)sec²(phi)/(9+12tan²(phi))^(3/2)`, and `kc_c=3/sqrt(9+12tan²(phi))`. Beta uses the same angle derivative evaluated at psi. Chain with `phi_k=-n_p(phi-phi_r)`, `coh_k=-n_c(coh-coh_r)`, `psi_k=-sf*psi`.

`Updatedfdk(DP,I)` must use the returned I, not the trial I:

\[
f_\kappa=I(\lambda)\,\alpha_\kappa-(k_c)_\kappa,
\quad k=\kappa_o+\lambda/\sqrt3,
\quad I=I_{tr}-9K\beta(k)\lambda,
\]
\[
F=q_{tr}-G\lambda+\alpha(k)I-(k_c)(k),
\quad F_\lambda=-G-9K\alpha[\beta+\lambda\beta_\kappa/\sqrt3]+f_\kappa/\sqrt3.
\]

No direct `f_psi` term exists. The psi derivative changes flow/returned I. The history relation `delta_kappa=lambda/sqrt3` applies to the smooth radial segment. At an actual tip the deviatoric increment saturates at `qtr/(sqrt3 G)`; a total apex multiplier must not continue accumulating radial kappa. See `upl_dp_apex_physical_review_r1.md` for the unresolved tension/cap choice.

## Two entries, one internal numerical implementation

The candidate exposes `ConsRelationEP(state,K,G,DP_phi,DP_kc,DP_psi)` for fixed coefficients, and `ConsRelationEPsft(state,material,DPCtes)` for same-kappa evolution. Two tiny coefficient evaluators feed the shared internal scalar/tensor return. There is no new XML algorithm selector. The coefficient names are retained instead of disguising constitutive meaning behind generic a/b/fk fields.

The candidate still does not implement an apex/cap. It adds a sufficient interval-wide upper bound on F' for an early, provably monotone radial subset. A failed certificate returns candidate-only `UnresolvedPath`, not a fabricated apex or an elastic fallback. This is deliberately conservative and may reject otherwise solvable parameters. It is useful for the first coefficient/path tests, not an acceptable final substitute for continuation/first-branch handling. Current soft-entry validation still requires positive friction endpoints; phi0 is an explicit remaining candidate gap, although the fixed-coefficient entry can express alpha0. No extra hard rejection layer should be added instead of completing the model.

## Minimum eventual CPU/GPU integration changes

1. `FunSoilMaterial.h`: one shared coefficient/general-return implementation and the two basic/softening entries; named native tensor adapters. Avoid keeping two algorithm copies after validation.
2. `JSphCpu.cpp` and `JSphGpuSimple_ker.cu`: replace the current old/MR1 fork with the two physical entries, preserving the existing Pre-kappa restore, Cor commit and six-component layouts. Existing DPCtes is passed; no additional particle array/wrapper switch is required. Retain `DP_phi/DP_kc/DP_psi` variable names. The old routines remain external test references only during migration.
3. `JSph.cpp`/`DualSphDef.h`: remove the long-term `MaterialReturn` algorithm selector and its tied validation only after equivalent ordinary/tip behavior is actually covered. Account for input migration deliberately, rather than silently routing old XML to a different algorithm. Preserve unrelated geometry/hydromechanical guards.
4. Important current dispatch gap: `JSph.cpp:3966-3968` defines `StrainSoftening` only from phi/cohesion; psiDecay is read later. Unified soft dispatch must also select evolution when sf>0 with constant strength. CPU and GPU `SOILSTRAINSOFTENING`/constant upload must have the same meaning; otherwise pure dilation decay is lost after removing MR1.
5. `JSphGpu.cpp`/`.h` and existing Pre/Cor wrapper error plumbing: `MaterialErrorg` is currently allocated only for MR1. Unified calls still need that one run-owned scalar/error channel; deleting the old condition without changing allocation would leave a NULL atomic destination. Keep the same fail-before-stage-accept behavior. Shared source elasticity certification must test actual unified return status, not the removed selector value. The preload state/contract/schema and docs also need a versioned migration; never relabel the shipped r2 bytes.

No new 3-D u-pl/mDBC/HG/restart scope follows from these material changes.

## Material-path reference comparison (no spatial half-step chain)

Use separately initialized `(model,method,N)` material paths, a proportional deviatoric strain increment `deps=diag(delta,-delta,0)`, and positive signed q throughout the planned smooth intervals. The initial stress is `diag(I/3+q,I/3-q,I/3)`, kappa0. For each step the elastic trial is `xx+=2G*delta; yy-=2G*delta`. Cover 3 fits, joint phi/c/psi decay, constant-strength controls, load/unload/reload, and phi0 as a pressure-insensitive limit. DP_C/DP_MC coincide at phi0; their kc is not the same as DP_PS for the same c, so do not silently rescale or claim all fits coincide.

- `candidate_general`: current general candidate endpoint solve, with laws at the new continuous kappa before float storage. Expose `UnresolvedPath` and known phi0 failure instead of concealing them.
- `linearized_dev`: independent one-step Taylor comparator, coefficients frozen at old kappa, lambda=`ftrial/(G+9K alpha beta-fk/sqrt3)`, and kappa increment=lambda/sqrt3. No hidden final projection to old or new strength. This isolates first-order integration; it is NOT the unmodified production legacy algorithm.
- `legacy_actual`: call the actual linked `ConsRelationEPsft_fast` from the frozen 85-object closure. It has its original full-history/sign/projection choices and no native continuous-kappa/status/lambda return. Record that distinction; do not manufacture those diagnostics from a post-projection strain norm.
- Optional `currentMR1`: actual current header return only for eligible fixed-friction DP_PS rows. Keep it as a reference, not another future production selector.

An independent fine reference can integrate `(I,q,kappa)` with tightly controlled SciPy DOP853 and analytic elastic/yield events. For this fixed direction and zero total volumetric strain, plastic loading obeys

\[
\dot\lambda={2G\dot\delta\over G+9K\alpha\beta-(I\alpha_\kappa-k_{c,\kappa})/\sqrt3},\quad
\dot I=-9K\beta\dot\lambda,\quad
\dot q=2G\dot\delta-G\dot\lambda,\quad
\dot\kappa=\dot\lambda/\sqrt3.
\]

Unloading/interior motion has lambda_dot0, I/kappa fixed and q_dot=2G delta_dot. Split exactly at yield; do not use a stress tolerance to turn unloading into plastic loading. Refine material ODE error tolerances and verify constant-coefficient/elastic closed controls. High-precision scalar endpoint checks may be added only if ordinary double reference precision is insufficient; no SPH solve is needed.

Track all six plastic-strain components from elastic compliance, the accumulated norm of EACH deviatoric increment, and signed plastic volume. Do not equate accumulated kappa with the norm of the final net plastic tensor after load reversal. Verify `total strain = elastic strain change from the initial prestress + accumulated plastic strain`. Compare continuous endpoint history, actual saved float history and that accumulated dev-norm diagnostic separately. A finer float-rounded microstep history is not a high-precision truth: round only at the declared constitutive output/storage boundaries when isolating storage error.

The driver accepts the 19-column CSV specified by root, emits one output per input row, and continues other methods if one candidate path fails. `N` is a resolution label; `step` runs 1..actual rows within a contiguous group across its segments. All planned rows are expected smooth Elastic/Radial. A failed/unresolved/nonfinite smooth path makes completion false and later rows in that group are marked skipped. Point count comes from input rows rather than an invented fixed matrix. Actual apex/tension paths wait for the physical policy; mean clipping is not silently substituted.

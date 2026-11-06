# Cohesion-softening periodic candidate: draft only

Status: source read only; no patch, engine edit, build or run. The completed constant-strength periodic CPU/GPU128 pair and its native/copy checks are the retained baseline, not a softening validation.

## Smallest proposed admission change

- `source/JSph.cpp:3643–3652`, `IsDynamicPorePlasticPeriodicConfig()`: remove only `coh==coh_r && n_coh==0`. Keep MaterialReturn=1 and every current periodic/no-wall/g0/constant-k/zero-dilation/disabled-option condition. Existing MaterialReturn validation already requires finite cp>=cr>=0, n_coh>=0 and fixed phi; do not duplicate it or admit friction softening.
- `source/JSphCpu.cpp:4464` and `source/JSphGpu.cpp:1774`: replace only the unconditional StrainSoftening rejection with `StrainSoftening && !IsDynamicPorePlasticPeriodicConfig()`. All other initializer clauses remain. These are the two present blockers once cohesion differs and n_coh>0. The gravity-container, independent SPR and HG softening restrictions stay unchanged.
- No constitutive or stage change: retain the actual shared endpoint return, float parameters/kappa, Pre old-kappa/Cor commit rules, periodic kappa/Dk copying and current CPU finite/nonnegative-kappa check. GPU NULL-kappa waiver remains corrector-only after checked real material success; every unmatched configuration keeps the old kappa0 gate. Preserve all J/n/rho/cache/range/finite, support/owner, strict decay-domain and current-step/DtMin guards. No new public input, array, kernel or interface is needed.

## One proposed short same-physics pair

Copy the verified periodic configuration/seed unchanged except **cp=5000 Pa, cr=1000 Pa, n_coh=5**. Keep phi=25 degrees with n_phi=0; dlt=psiDecay=0; constant k; the exact same initial float sine samples, lattice, Wendland operator, dt=2^-19, DtMin/CFL/PoreDtSafety, 128 updates and five saved times. Use fresh `upl_plastic_softening_CPU_r1` / `GPU_r1` results: one CPU1 run and one GPU run after separately reviewed source application/build/admission. No half, old-control rerun, dynamic-Ck, negative psi, wall/gravity/HG/SPR/damping or extended duration.

Require actual nonzero finite nonnegative/nondecreasing native kappa and inspect the resulting `c(kappa)=1000+4000*exp(-5*kappa)` decrease at each saved material ID. Report its actual magnitude; a short window can produce only a small strength loss and does not establish large-strain softening. Keep the existing native/material/domain/time checks. Compare p, displacement/velocity, effective/total stress, kappa, derived cohesion and J/n/rho/k across CPU/GPU and descriptively against the already closed constant-strength results at their actual matching times. Retain every point; introduce no 5 Pa equality, accuracy or energy-decay gate.

## Numerical and physical limits

The return must solve strength at the continuous endpoint `kappa_old+lambda/sqrt(3)`, not lag cohesion at old kappa. For psi=0, its derivative is `dF/dlambda=-G+f_kappa/sqrt(3)`; retain the existing negative-derivative, bracket, radial q>=0, convergence and ApexNeeded/Invalid/NonConverged failure handling. Saved float-kappa yield residual remains distinct from the continuous root residual; do not tighten or relax the tested budgets implicitly.

Zero dilation avoids inventing plastic volume/apex flow. A successful local return does not prove complete discrete coupled dissipation or global energy decay. Local cohesion softening has no length/fracture-energy regularization here: this single lattice/short pair cannot establish mesh-objective localization, band width, post-peak capacity or continuum convergence. Those limits remain explicit; no TPI or kappa-double change is proposed.

# Unified DP history and return: primary-source findings

2026-11-07. Research/design only: no production, input or server-r2 package changes, build, solver, decoder, Git or SHA. Relevant original PDF pages were visually inspected, not inferred solely from OCR. No proposed material test below has run.

## Decision and primary evidence

For reproducing **Lian/GeoDual shear-softening DP**, use one accumulated equivalent **deviatoric** history:
`dκ=sqrt((2/3) de_p:de_p)`, `de_p=dev(dε_p)`.
For regular radial flow with `q=sqrt(J2)>0`, this gives `Δκ=λ/sqrt(3)`. Plastic volume change remains `tr(Δε_p)=3 DP_psi λ`; excluding it from κ does not remove dilatancy.

- [Bui & Nguyen 2021](<D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b/src/papers/PDF/Bui 2021-CG.pdf>), printed p.17 Eq78 explicitly defines κ from deviatoric plastic strain. However, Eq81/87 and Algorithm2 print a full `∂g/∂σ` norm. Those differ for nonzero ψ. Eq86 prints `f_trial-f_σ:Δσ_p+f_κΔκ=0`, while Eq87 uses a plus denominator; interpreting f_κ as the actual partial derivative does not directly produce that sign. Record this inconsistency without silently declaring a typo. Eq80's plastic-strain magnitude versus the prose's accumulation also leaves notation ambiguity.
- [Lian et al. 2023](<D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b/src/papers/PDF/Lian 2023 u-pl.pdf>), printed p.4 Eq13 uses **`∂g0/∂s`**, the deviatoric derivative. Printed p.5 Eq17-19 applies equivalent plastic history to φ/c/ψ, with separate sf for dilation. Its printed plus denominator does not resolve the sign convention above.
- [GeoDualSPHysics](<D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b/src/papers/PDF/GeoDualSPHysics.pdf>), printed pp.3-4 §2.3/Table1 explicitly names equivalent deviatoric κ and adopts Bui's semi-implicit update. It supplies no independent complete softening/apex derivation. Its plane-strain and two 3D DP coefficient calibrations are distinct.
- Bui p.18 §3.2.2.2 deliberately freezes trial gradients to avoid iterations, justified by small SPH increments. That is a cost/accuracy rationale, not proof of optimal accuracy for arbitrary paths. The following localization discussion warns that local softening without a length scale does not guarantee mesh-convergent post-localization solutions.

Dev versus full norm is a **model/calibration choice**, not a floating-point accuracy choice. Full history has `h_full=sqrt(2 DP_psi²+1/3)`; its ratio to dev history is `sqrt(1+6 DP_psi²)`. That ratio varies when ψ evolves, so generally one constant rescaling of η/sf cannot preserve the full path. A calibrated full-norm damage model can be legitimate; it should not be presented as the same Lian shear-softening model with unchanged parameters.

## Numerical return: what is and is not established

Current `JSphCpu.cpp:3937-3948` uses devκ in basic fast return, while the soft fast return uses full h at4031/4058. `Updatedfdk:3859` computes the actual `f_κ=I1 DP_phi_κ-DP_kc_κ`; it is positive for fixed-φ cohesion softening. The soft fast denominator at4034 is `A+f_κh`, and its final scaling at4062-4079 retains old-κ coefficients.

Current `FunSoilMaterial.h:43-97` solves the declared endpoint equation:
`F=q_trial-Gλ+DP_phi(κ)[I_trial-9K DP_psi(κ)λ]-DP_kc(κ)=0`.
For `κ=κold+hλ`, general friction softening needs
`F_λ=-G-9K DP_phi(DP_psi+λ DP_psi_κ h)+(I_new DP_phi_κ-DP_kc_κ)h`.

A small endpoint residual proves consistency with that discrete equation, **not** accurate integration of the entire stress/history path or more physical soil behaviour. Backward Euler is first order. For constant-coefficient isotropic DP on the regular radial segment, trial and returned `s/q` directions agree; stress-direction freezing alone need not cause an error. Evolving coefficients, yield entry, nonproportional loading and increment size must be tested.

Recommended baseline: one DP_phi/DP_kc/DP_psi coefficient/derivative engine, devκ and consistent endpoint return; perfect plasticity follows by zero evolution derivatives. Assess bounded internal **material** substepping against a path reference, rather than adding multiple public algorithm selectors or claiming the endpoint method already optimal. Float material parameters and saved κ remain separate from local double arithmetic; saved-history rounding is not removed by better root convergence.

## Apex and the φ0 limit

For a one-step backward-Euler apex with `s_new=0`, elastic compliance gives
`Δε_p_dev=s_trial/(2G)`, hence `Δκ=q_trial/(sqrt(3)G)`.
Do not continue `λ_total/sqrt(3)` beyond the regular radial limit. Require `λ_total>=q_trial/G` for the apex subgradient and `I_new=I_trial-9K DP_psi(κnew)λ_total`. Pure hydrostatic trials have no dev-history advance under this closure.

For DP_phi>0, a tensile trial above `I_tip=DP_kc/DP_phi` needs I1 to decrease. ψ0 cannot change it; negative ψ with nonnegative λ changes it in the opposite direction. There may be **no admissible return under the stated flow law**. A tensile cutoff or altered apex flow is a new material choice, not harmless clipping. For φ0, the yield surface is the J2 cylinder `f=q-DP_kc`, without a finite DP tip; avoid division by DP_phi.

## Minimal executable material-only comparison

Use the same actual float E20MPa/ν.33 inputs, six tensor components, zero spin and effective stress (no pore-pressure state). No spatial/half/reference solver run is needed.

1. **Closed-form constant-strength path:** initial `σ=-100000 I Pa`, κ0; φ25, cp=cr5000, ψ+2.5, all decay factors0. On τ0..1 prescribe engineering `γ_xz=.02τ`, meaning `ε_xz=γ_xz/2`; other strains0. This is spin-free tensor shear, not a laboratory simple-shear rotation claim. Check exact radial stress/λ, devκ and volumetric plastic strain.
2. **One smooth coaxial softening path first:** for example `I0=-300000Pa,q0=1000Pa,κ0`, path duration1, engineering shear rate.02 and tensile-positive volumetric strain rate-.001. Thus `q_el_rate=G*.02`, `I_el_rate=3K*(-.001)`. Use cp7500/cr1000, φp25/φr20, n_phi=n_coh5 and sf.2; positive/zero/negative ψ and the three coefficient fits may reuse exactly this protocol. These are synthetic same-row algorithm checks, not all Lian Table1 groups or a plane-strain laboratory experiment. Initial yielding is located analytically on the elastic segment; verify q>0, compressive I, positive consistency denominator and a nonempty plastic interval. Nonproportional/unload/reload paths can follow if this minimal comparison leaves a real ambiguity; they need not delay this first result.
3. **Separate apex feasibility:** one hydrostatic-above-tip trial with positive/zero/negative ψ, plus the φ0 cylinder limit. Compare against the same declared apex/no-solution policy; do not force a smooth ODE reference through a nonsmooth tip.

Hold the **same devκ law** when comparing a trial-linearized companion, endpoint/backward Euler and material substepping at8/16/32/64 increments per segment. An unmodified legacy full-norm/plus-denominator output is a separately labelled historical control, not a fair same-model algorithm error.

For smooth plastic segments, independently integrate differential flow with elastic/plastic event location:
`λdot=(n_f:C:εdot)/(n_f:C:n_g-f_κ h)`,
`σdot=C:(εdot-λdot n_g)`, `κdot=h λdot`.
Tighten reference precision/tolerance until its own change is well below the candidate errors; halving the same implementation alone is only self-convergence. First isolate algorithm error with a test-only continuous-history reference, then quantify actual float-κ writeback separately.

For fixed deviatoric direction this reduces exactly to the proposed reference: `D=G+9K DP_phi DP_psi-(I DP_phi_κ-DP_kc_κ)/sqrt(3)`, `λdot=(q_el_rate+DP_phi I_el_rate)/D`, `qdot=q_el_rate-G λdot`, `Idot=I_el_rate-9K DP_psi λdot`. No separate `λ DP_psi_κ` term belongs in this *instantaneous rate* denominator; it belongs in the finite-increment BE Jacobian above. Use the elastic system while f<0 or unloading, not this plastic formula everywhere. Under tensile-positive strain, `ev=trace(εdot)`; if compression is instead defined positive, the sign of I_el_rate reverses.

A practical numerical-reference budget is DOP853 rtol1e-11, stress-component atol1e-9Pa and κ atol1e-13, followed by a tenfold tighter repeat. Report the actual reference difference as uncertainty; rank candidate error only when clearly above it, otherwise report resolution-limited. These are proposed reference controls, not material/physical acceptance thresholds. Monitor f drift without projecting it away. Legacy `1.732f` versus exact sqrt(3), float DP coefficients, history norm, denominator sign and stale-surface projection are separate differences; keep the real old method in its own column.

Compare full stress-path error, κ/c/φ/ψ, volumetric plastic strain, loading/unloading/complementarity, continuous versus saved-κ yield residual and work/elastic-energy balance. In the coaxial protocol `Wdot=q*gamma_dot+I*ev/3`, `We=q²/(2G)+I²/(18K)`, and `Wp_dot=λdot*(q+DP_psi*I)`; require the *observed numerical* closure `W-ΔWe-Wp` to converge with the reference. Positive work alone is not material calibration or a general thermodynamic proof. Time only material calls; infer no whole-case speed.

Existing36-point legacy and71-point shared-core audits establish their reported local behaviours, not an accuracy-improvement ratio between different point sets. The proposed comparison can rank numerical error/cost for a declared model; it cannot select a universal history law, prove physical calibration or cure localization/mesh dependence. No new tolerance, fit or implementation is approved here.

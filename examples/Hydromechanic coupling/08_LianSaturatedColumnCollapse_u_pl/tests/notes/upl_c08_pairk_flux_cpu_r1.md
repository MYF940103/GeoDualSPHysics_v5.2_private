# Frozen C08 hydraulic pair-k rate shadow (author only)

Only four new files: `tests/support/upl_c08_pairk_flux_cpu_r1.cpp`, `_build.py`, `_run.py` and this note. All four names were absent and untracked before writing. No production source, physical object, formal input, runtime, PRE, old component or active pair-gradient dependency is modified. This draft does not execute a build, force, solver, native decoder, VTK, parameter window or hash scan.

## Scope and one physical-stage evaluation per saved state

The input is the already passed true total-AS/n3 `upl_c08_causal_window_GPU_r1/native` export: original90 frames/6805 IDs/22 fields, with its actual run/native receipts and exact90-frame prefix proof against root-r6. Read only parts13/14/29 (tau .14/.15/.30). Keep the actual scalar clocks, all5000 soil fields,1805 fixed roles, original certified law1 PRE, target law2, kept IDs1800/1852/1904/1956/2008 and actual255 retirement. Native current fixed n/V/rho/k zero markers are never used as quadrature; all neighbor volumes are actual V0*J, including fixed samples.

Legal `LoadConfig -> InitRunCpu -> handoff -> one real release` and per-ID `CopySaved/Restore/LoadDcellParticles/RunCellDivide` are copied from the passed pair-force component, not synthesized. Each state gets exactly one `Interaction_Forces(INTERSTEP_SymCorrector)`, which recomputes actual wall state, FS/C, mechanics/total-AS/AV, wall Ace and current Darcy. Its actual `DtVariable(false)` guard remains. Dump all shadows before normal `PosInteraction_Forces` cleanup. There are3 force calls/3 actual Darcy calls/0 physical updates, no ReturnMaterial, filter, plane projection, extra Darcy call or time advance. Saved versus recomputed FS differences are reported, not suppressed or called GPU replay.

All original settings remain: Cubic h=.048f/dp=.04, SymC, positive original Eta2, AS total-stress .2/n3, AV.1, keep5, FixedPlaneStageProjectionReleaseOnly/ReactionClosed=false, CompletedOnly, release damping/ShepardOFF, Model1/Ck2. This component links the original frozen bedkeep force objects; no private physical source replacement or production hook is needed. Its new definition is only a test-side read-only rate shadow, never fed back to p, J, mechanics or actual rate arrays.

## Two rate expressions, common continuous target

Let d=xi-xj, gi=Ci*gradW, gj=Cj*gradW, w=Vj*d.dot(gi+gj)/(r2+Eta2), Lx=sum(w*d), Gp=-sum(Vj*(pi-pj)*gi), DA=sum(Vj*(Aj-Ai).dot(gi)), F=Gp+rho_w*Ai, chi=0 on the actual open FS2/3 and1 elsewhere. Ace excludes body gravity. The target is p_dot=Kw/n*(-theta+div[k*(gradp+rho_w*Ace)]/gamma), gamma=rho_w*9.80665.

- Current: ki*(LP +rho_w*Ai.dot(Lx)-chi*F.dot(Lx)+rho_w*DA) + k'_J*gradJ.dot(F). The actual dump retains the five original terms compression/LP/defect/divAce/chain and checks their sum against actual float PorePressRate with the unchanged propagated arithmetic budget.
- PairFlux shadow: sum(kbar*w*(pi-pj+rho_w*Ai.dot(d))) -chi*ki*F.dot(Lx)+rho_w*ki*DA, kbar=(ki+kj)/2. It has no additional old chain term. Pair-k pressure weighting already approximates part of grad-k coupling; retaining the old whole chain would double count its pressure part.

Constant k makes these expressions algebraically equal, not automatically bit-identical because accumulation/grouping differs. The shadow's variable-k difference replaces the receiver product rule by an edge-weighted hydraulic defect. At a consistent continuum limit its extra vector sum(kbar-ki)*w*d approximates gradk; the actual finite stencil need not reproduce it exactly. There is no claim of conservative pair flux, negative energy, full coupled stability or literal Lian Eq25. In particular, paper2023 printedp6 Eq25 uses pair-k also in the acceleration-difference sum and has an apparent dimensional ambiguity in the printed pressure-defect prefactor. Paper2021 printedp15 Eq57/p22 Eq72 supplies the scalar-head boundary pattern, not a proof for this dynamic Ace extension. Neither original momentum nor mechanical/AV Eta is changed.

## Small manufactured controls, frozen real geometry

Select exactly32 output soil receivers per state: explicit7011/7012/6230/6231, the nearest8 available points outside the actual fixed/FS2/3 2R halo, then nearest remaining points to the four focus positions. This is an output cohort only. Every rate always uses the complete original neighbor support, including walls; no stencil is limited to32. The halo label is based on current detected FS/fixed geometry, not proof of physical support completeness. Report actual FS, fixed-neighbor counts and halo membership. For actual FS with a nonzero actual FSNormal, export F projected on its unit normal; this is not a certified discrete normal water flux or contact reaction.

Use the real J/V/k and real C for every shadow. Manufactured p/A fields are created in temporary test vectors for all6805 coordinates; real arrays are untouched. They are an explicit analytic ghost oracle, not the actual reconstructed wall closure or a replay. Their theta is0. The six controls per receiver are:

1. Native p/A/theta with k fixed everywhere to k0: current versus pairFlux algebraic reduction.
2. Constant p=-1024Pa,A=0,theta=0 with actual variable k: exact constant null.
3. Uniform A=(1/32,0,1/16)m/s2, p=-1024-rho_w*(x/32+z/16): float64 and independently quantized float32 p/A.
4. Nonconstant curl-free A=gradPsi, p=-1024-rho_w*Psi, Psi=x/32+z/16+(x*x+z*z)/64+x*z/128: float64 and float32.

The last two have continuous F=0 for arbitrary k. Uniform-A FS chi0 has pairwise hydraulic cancellation apart from manufacture/storage arithmetic; its interior correction still depends on the actual corrected first-gradient closure. Report F and pair residual; do not impose an unconditional zero gate on interior points. The nonconstant potential case also tests the mismatch between second-pressure and first-Ace-divergence stencils: measure errors against continuous zero, with no new physical tolerance. Float p and A quantization maxima are separate columns. There is no manufactured wall-fit/AS/force evaluation, so these controls cannot establish the actual wall boundary's manufactured accuracy.

## Arithmetic and outputs

The actual current-rate budget is copied from the passed Darcy component: (32*FLT_EPSILON+gamma_m)*max(1,propagated_absolute_scale), m=64*neighbor_count+256, gamma_m=m*DBL_EPSILON/(1-m*DBL_EPSILON). Constant-k algebra uses the same gamma_m and the sum of both expressions' propagated absolute scales, with pressure subtraction and hydraulic terms retained in the absolute pair scale. This is arithmetic, not a5Pa, accuracy, energy or physical acceptance gate. Only exact constant null and this algebraic reduction are asserted. Potential/hydrostatic errors are reported without result-dependent relaxation or a new gate.

Fresh outputs: `tests/outputs/upl_c08_pairk_flux_cpu_r1/{receivers.csv,manufactured.csv,calls.csv,completion.json,Run.out}`. Exactly96 actual receiver rows,576 manufactured rows,3 call rows,96 null and96 constant-k checks. Before/after all shadows, all6805 actual C/Ace/FS/FSNormal/theta/rate bits must remain unchanged; original5000 primary bits/clock/ledger/wall roles are also checked before and after every force/cleanup. No field is integrated or zero-filled to make a result pass.

## Separate root-reviewed build and run

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_pairk_flux_cpu_r1_build.py --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_pairk_flux_cpu_r1_run.py --execution-authorized
```

These are two separate explicit actions, never an automatic chain. The builder is the passed pair-force builder with only its TAG changed (reverse text comparison required at author review): one helper CL/link, original86 non-main bedkeep DebugCPU objects plus helper=87; authoritative MSVC14.36 Debug /Od /MTd /fp:precise /openmp/C++17 recipe, headers from the same frozen archive as runtime_r6. Fresh helper `outputs/upl_c08_pairk_flux_cpu_r1_helper/component.exe`; build/check receipts `logs/upl_c08_pairk_flux_cpu_r1.{build,check}.json`. No solver rebuild, new native decode, GenCase or GPU object is involved.

The runner retains the already reviewed causal90 source/clock/schema/PRE/seed/exact-prefix/provenance admission block, then verifies only this new3-call CSV/completion profile. It preserves real Popen/Win32 exits, existing/partial results and consumed stats. Any failure is retained without retry, dropped receiver, numerical relaxation or automatic next job. An exit0 means this component and its arithmetic/identity checks completed; it does not certify the shadow, explain the instability, accept collapse physics or unlock other psi groups.

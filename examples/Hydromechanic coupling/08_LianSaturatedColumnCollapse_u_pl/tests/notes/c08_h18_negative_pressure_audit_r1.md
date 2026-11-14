# C08 negative pressure: literature and bound-source audit

Read-only mechanism audit, 2026-11-14. Only this UTF-8 note is newly authored. No solver, reader, analysis script, build, Git, SHA scan, native-payload scan or public-source/input change was performed. Existing conclusions below were read from sealed notes, not recomputed.

## Identities

The physical source reference is tests/outputs/c08_preload_schema2_source_r1/full_source.zip, entries src/source/JSphCpu.cpp, JSphGpu.cpp, JSphCpuSingle.cpp, JSphGpuSingle.cpp, JSphGpu_ker.cu and FunSoilMaterial.h. They were read in memory without extraction. The AV20 host intervention changes release AV and metadata; this audit does not substitute current editable source for the archived FS/Darcy implementation. PRE, programs and old failed candidates stay unchanged.

Primary text is src/papers/u-pw/Lian 2023 u-pl.md. Line numbers below refer to this auto-converted Markdown; printed PDF pages disambiguate OCR layout. The relevant passages were read fully.

## Eq19 versus Eq47

Eq19 (Markdown263, printed5) is psi=psi0*exp(-sf*kappa). Archived FunSoilMaterial.h:50-52 evaluates friction, cohesion and exactly that dilation decay in double from float material constants. Lines231-232 pass c.dlt/c.psiDecay and select the required return. Current psi0=0 makes this smooth-return dilation term identically zero. That does not force elastic/total theta or geometric J to zero, nor establish that every negative pressure is physical plastic dilation. Constitutive attribution remains separate.

Eq47 (Markdown584-608, printed11) modifies the paper's TPI pressure row. It is not Eq19 or a negative-pressure clipping rule. The paper explicitly says setting negative p to zero removes the intended dilative-soil physics. Its negative branch adds beta/h to the diagonal AND beta*p_tilde_i/h to the numerator. With S=sum Aij:

p_new-p_tilde_i = (B + sum Aij*p_tilde_j - S*p_tilde_i)/(S+beta/h).

The displayed branch condition uses old pressure p_l^t<0, while the text discusses negative excess pressure from plastic dilation. These must not silently become native p-fixedP0, current hydrostatic excess, or any negative diagnostic. A future implementation must define variable and eligibility.

The preceding derivation (Markdown395-474, printed7-8) first removes finite storage n/Kw (401-404), then uses p_tilde=p_n+alpha*(p_n-p_previous) (464). Current finite-Kw predictor/corrector is not this old-time TPI extrapolation. Eq47 is absent by algorithm choice, not a proven missed line in the present integrator. Adding beta=.04 to an explicit rate, clipping p, or simply dividing the entire RHS would not implement Eq47.

Units must follow the complete row: in the current gamma-normalized row M=gamma*n/Kw has units1/m; A and S have units1/(m*s), so beta/h needs beta with the same capacity units as M. The paper calls beta a calibrated coefficient, without a portable normalization contract. Current M is roughly3.43e-6/m; literal .04 in that normalization would dominate finite storage by about four orders. This is not a proposed beta value.

## Actual boundary and sign handling

Archived CPU JSphCpu.cpp:1231-1233 identifies FST_FreeSurface/FST_Isolated, native FS2/3. Distinct paths exist:

- Drained Dirichlet: CPU1443-1456; GPU host1360-1368 and kernel1104-1106 set both signs p=0 and dynamic rate=0 when HydroMechDrainage is active.
- C08 one-sided ponding: CPU1633-1641; GPU1424-1438 and kernel1108-1109 cap only finite positive p on normal native FS2/3. Negative p is retained. !PorePressPre/Preg restricts it to completed states. CPU1725-1729/GPU1453-1456 repeat the same policy after Shepard, without clearing rate or the old corrector base.

CPU Single903-920/GPU Single813-830 order force_n, predictor, half divide/FS, force_half, corrector. Half p can thus be positive under CompletedOnly even when saved FS p<=0. This is a documented timing policy already tested separately, not an unexplained indexing error. No negative-pressure clipping or Eq47 capacity appears in the audited pressure paths.

Dynamic hydraulic assembly is CPU3185-3189,3251-3260 and GPU kernel1533-1600. At free-seepage FS it uses LP+rho*(a_i dot Lx+Da), plus the variable-k chain; interior rows use LP-gradp dot Lx+rho*Da. The closed-pre-drain normal Taylor target has its separate closedfs=(HydroMechDrainage&&!drainfs) guard, not activated by free-seepage alone. Neither the cap nor raw FS formula is a measured conservative face flux. A negative FS value alone cannot certify the intended hydraulic flux/complementarity, saturation, cavitation or water-mass balance.

Paper Section4.4 (Markdown881-889, printed19) adopts free-seepage and ponding p_l<=0; retaining negative FS p is not by itself contrary to that text. This is not two-sided drained p=0. Fig14's zero plastic-dilation excess at psi0=0 (891-908) also does not require every deformed material point to preserve its fixed P0. Table1 alpha=.5 is TPI history, not AV.

## Existing interventions: scope and decisions

Historical H1.2/dt2.5us trials are not isolated controls for current H1.8/dt5us/source. These values belong to the cited trials:

- upl_c08_stage_ponding_review_r1.md: H1.2/AS.2n3, 66 matched saves. At tau.66 completed-only -> released-substage minimum p -44.16631 -> -65.69314kPa, RMS12.97630 ->13.89954kPa, close pairs45 ->58. Some extreme spacing tails improved, overall benefit was inconsistent. Policy withdrawn; negative p was never cleared.
- upl_c08_shepard_decision_r1.md: release Shepard40 failed original pore-step guard after72 saves, last tau.72, engine-reported step4289868. Saved pressure/NN worsened; no unsaved state was reconstructed.
- upl_c08_as_effective_fresh_decision_r1.md: fresh effective-only AS failed after51 saves, last tau.51. At that save total-AS -> effective-AS close pairs49 ->86 and positive maximum16.9348 ->120.3424kPa. Removing pressure-induced tension from AS was not a repair.
- c08_fs_normal_window_decision_r1.md: H1.8/AS.5n3.825 normal-Taylor completed91 saves, but worst suction -85.4465 -> -88.2433kPa, final close pairs23 ->27, and early arrest persisted. Local affine benefit did not establish physical benefit; candidate not selected.
- c08_h18_pressure_row_decision_r1.md: original AS.5/n2.55 full3 Part300 zero-advance rows had all5000 S>0, only2 negative-A rows, exact constant-pressure null and dt*S/M .223719/.310814/.389800 min/median/max. No widespread diagonal-sign failure was demonstrated; this is not coupled stability.
- c08_h18_cn_step_decision_r1.md: genuine finite-Kw midpoint diagonal-CN late single step changed p by only .001460279Pa RMS/.0078125Pa max. It is not TPI/beta and did not justify a new trajectory.

One genuine paper/code difference remains: Eq46 (Markdown570-576, printed10) averages total p and is used only for Section4.5 low-permeability large deformation. CPU1669-1700/GPU1450 instead smooth p-fixedP0 and add fixedP0. The failed release-Shepard trial therefore was not an exact Eq46 transplant. That difference does not itself justify a total-p filter in C08 Section4.4 or matching paper colours.

## Minimum remaining information gap

No missing negative-clamp line or direct Eq19 bug was identified. c08_as05_volume_pressure_audit_r1.md already documents broad negative drift with almost unchanged global J. S=sum(nV*p/Kw) is a conditional storage proxy, not water mass. Constant p is a null mode of frozen hydraulic differences; local diagonal signs do not bound a global offset or establish a conservative left nullspace.

First check existing bounded force/RHS CSVs for retained terms. If missing, the smallest additional observation would be one separately reviewed zero-advance original CPU evaluation at an already saved early tension state, e.g. Part38/76: separate theta compression, pressure LP, Taylor defect, acceleration Da/a dot Lx and variable-k chain, with signed sums split into interior/wall-adjacent/actual FS2/3. Preserve the actual force lifecycle and fields; do not fit acceleration or add gravity to Ace. A pressure-only counterfactual with frozen a is partial because p also changes total-stress momentum and hence a.

For FS, report the actual normal target (gradp+rho*a) dot n and defect terms using the source's normal orientation. Test the intended boundary relation rather than infer flux from p<=0. This does not reopen the rejected normal-Taylor trajectory absent a distinct falsifiable omission. A saved-state split does not recover substage flux or the history integral of storage/volume/boundary changes.

This remains distinct from the parallel raw-momentum versus G1-strain work audit. If consistent finite-Kw spatial/boundary terms still require the paper's TPI/negative-capacity model for stability, that is explicit model development needing history/manufactured/benchmark qualification, not a low-cost parameter patch. This note admits no beta, TPI, clip, filter, new half chain, other-psi run or solver; AS03/AV20 changes remain diagnostic differences rather than solved clumping or physical accuracy.

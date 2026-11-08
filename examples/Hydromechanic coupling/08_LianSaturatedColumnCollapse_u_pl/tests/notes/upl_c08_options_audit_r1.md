# C08 option/strength-trigger audit

Read-only audit of current source, actual r2 source XML, actual r5 receiver XML/Run.out and retained retrogressive inputs. src/AGENTS.md and Hydro AGENTS.md were read. This new name was absent and exact git ls-files was empty. Only this note is new; no source/input edit, build, solver, decode or hash scan.

## SoilTriggerFos is a legacy restart law change, not a collapse timer

- `JSph.cpp:4071-4073`: default `SoilTriggerFos=1.65f`, finite and >=1. `4074-4082`: strength softening is activated by positive n_phi/n_coh with supplied residuals, or DilationDecay>0. There is no separate trigger-time XML parameter for Fos.
- CPU Verlet/Pre/Cor pass `PartBegin && StrainSoftening` (`JSphCpu.cpp:3028-3029,3503-3504,3638-3639`). GPU uploads PartBegin as a bool at `JSphGpu.cpp:875`; all three kernels pass `SOILPARTBEGIN && usesoftening` (`JSphGpuSimple_ker.cu:214-215,429-430,622-623`). This condition persists throughout the PART-restarted run; it is not a new division of an already reduced cp on every step.
- `FunSoilMaterial.h:228-233` reduces **peak cohesion only**: cp_eff=cp/Fos when trigger && (n_phi>0 || n_coh>0). It does not divide phi, psi or residual cohesion. With n_coh>0, c(kappa)=cr+(cp_eff-cr)exp(-n_coh*kappa); otherwise cohesion stays cp_eff. A sf-only law is not strength-reduced. The ordinary softening law already evolves with kappa without this trigger (`49-53`).
- C08 r2 certified PRE and r5 statefile handoff use **PartBegin=0**, not `-partbegin`. `RestoreGravityPreloadClock` (`JSph.cpp:3781-3788`) restores actual Time/Nstep/Part but does not change PartBegin. The r5 log prints the default 1.65, but trigger=false: psi0 cp stays 5000 Pa, cr1000, eta5. At kappa=0 it is not silently 3030.303 Pa. The original PRE was certified Elastic, not a plastic restart.
- Fos is included in the PRE contract (`JSph.cpp:3739`). Changing the receiver from the source default1.65 to1 would reject that retained PRE even though the trigger is inactive. Do not set PartBegin to force a reduction: dynamic scope explicitly rejects it and the certified handoff is a different interface.

## What the retrogressive precedent actually did

`03_RetrogressiveSlopeFailure_u_pw/CaseRetroSlope_u_pw_failure_Def.xml:90-99` specifies phi=0, cp25kPa, cr1.5kPa, eta5, Fos1.65; its GPU BAT line62 supplies `-partbegin:50:0`. Thus its intended failure stage uses cp/Fos about15.15kPa after a separate peak-strength gravity stage. It also keeps Shepard40 and a small damping coefficient1e-5 during failure (XML88-89,118-119). Prestress uses5s, Shepard40 and damping.02 (prestress XML88-89,113-114,128).
This is a different u-pw sensitive-clay initiation mechanism, not evidence for reducing C08 strength. Its README also records different h/dp between its prestress/failure inputs; do not transfer its complete workflow as an already equivalent control.
Lian2023 local primary MD Table1 lines873-878 gives C08 phi25, cp5/5/7.5kPa, cr1kPa, eta5 and psi0/+2.5/-5; lines886-894 explicitly obtain gravity stress then suddenly remove the right wall to trigger collapse. No additional Fos reduction is specified there. Removing lateral confinement can produce an out-of-yield trial and subsequent kappa softening; no time trigger is required. Whether the present resulting trajectory matches the paper remains a separate numerical question.

## Actual r5 values and support boundaries

Actual inputs: root `CaseLianSaturatedColumnCollapse_psi0_shared_r5_Def.xml` and its generated output XML; actual phase confirmation in its `Run.out:86,109-117,157-167,255-269`. Source reference: `CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/CaseLianSaturatedColumnCollapse_shared_preload_r2.xml`.

| Option | C08 PRE / released r5 | Implemented/validated scope and conclusion |
|---|---|---|
| SoilStressRateGradCorr | 1 / 1 | Already on; container predicate requires it (`JSph.cpp:3818`). Not a missing stabilizer. |
| PoreCompressionGradCorr, SourceMode | 1,0 / 1,0 | Corrected receiver-C pair divergence already on; the same predicate requires these. |
| SoilBoundaryDerivativeSPR | 0 / 0 | Independent SPR is deliberately off. Dynamic wall already supplies derivative-image velocity (`JSphGpu.cpp:1501`, CPU1777). Public independent SPR requires Wendland, elastic fresh cases and no AS (`JSphGpuSingle.cpp:155-171`); C08 Cubic/softening/AS is excluded. |
| SoilHourglassXi | 0 / 0 | Deliberately off. Dynamic HG is admitted only in the constant-k X-periodic loaded elastic column (`JSph.cpp:668-671`); C08 Model1 gravity/softening/retirement is outside that scope. |
| Artificial viscosity | .1 / .1 | Already on, constant artificial form. Current-J inertia/volume adaptation exists; container requires this treatment (`JSph.cpp:3814`). Increasing it changes dissipation, not constitutive correctness. |
| SoilDamping, Coef | 1,.02 / **OFF** | PRE gravity relaxation already uses the existing intrinsic-density rate (`JSph.cpp:4020-4034`). Release explicitly turns it off (`JSphGpuSingle.cpp:1079`, CPU1274), not just a postprocessing label. |
| PoreShepardRegularization, Interval | 1,40 / **OFF** | PRE filters excess p-p0 using current-J volumes; event turns it off at the same release line. Full-step filter/wall refresh is `JSphGpuSingle.cpp:580-587`; dynamic kernel `JSphGpu_ker.cu:1654-1701` preserves p0 and uses V0J. |
| PoreDarcySymmetricCorr | 0 / 0 | Legacy option is rejected for dynamic seepage (`JSph.cpp:666-667`). Dynamic Darcy already uses pair Ci+Cj (`JSphGpu_ker.cu:1553-1559`); its log word `Receiver` does not mean that dynamic pair correction is absent. |
| PoreMdbcInterpolationMode | 0 / 0 | Same legacy rejection; dynamic wall uses its own same-stage MLS state/C/Ace producer. Enabling the legacy switch would not select a higher-order dynamic wall. |
| ArtificialStress | off / 1,.2,2.55 | r5 already enables the scoped total-stress release-only AS; PRE uses the original AS0 operator. Do not add retrogressive .3/exponent5 as a presumed missing paper parameter. |
| NoPen/bed overlap | off / fixed-plane stage projection, kept5 | Already enabled in the r5 receiver; reaction-to-Darcy is explicitly not closed. Current support is restricted certified gravity handoff, not a general contact claim. |
| k model / other transport | Model1,Ck2 / same | Already on. DDT/shifting0, legacy drain0, free seepage1. No missing legacy symmetry switch. |

Historical support is bounded: C02 `notes/upl_spr_av_root_r1.json` records CPU constant-k/g0/FreeSlip elastic column SPR+AV; `upl_gpu_stabilizers_r1.json` records Debug/Release GPU component and short-column compatibility, explicitly not plastic/variable-k HG/full acceptance. These do not qualify switching C08 SPR/HG on. C08's PRE and release evidence qualifies its present options as implementation paths, not the full collapse physics.

## Minimum candidate order, without starting a run

1. **No Fos/trigger correction is required.** Preserve paper cp and the existing statefile contract. First use the separately proposed frozen spatial pairing comparison; it directly addresses the demonstrated conditional pressure growth without changing material strength.
2. If a single existing-control dissipation diagnostic is later selected, **continue only Shepard40 after release** while retaining damping off and every other operator. This is the smallest plausible control from the retrogressive precedent, but current code hard-disables it at release: it requires a separately labelled phase-policy candidate at GPU1079/CPU1274 plus matching metadata/review, not merely an XML flip. Reuse the current full-step V0J/excess filter and existing finite-positive FS projection; retain negative p and p0. It is a smoothing experiment, not a conservation proof or accepted spatial fix.
3. A separate released-damping-on experiment would deliberately remove mechanical energy and could worsen the already short runout. It is lower priority than pressure-specific investigation and cannot be justified by the PRE damping value or by another case's1e-5. Do not combine it with Shepard/Fos/AS changes in one test.
4. Do not treat SPR/HG, disabling required gradient corrections, enabling legacy Darcy switches, increasing AS, or inventing a trigger time as available one-parameter fixes. Their current scope/formulation restrictions require distinct development evidence; this audit does not propose relaxing them.

No mandatory production/input patch follows from this audit. A later documentation-only clarification could say explicitly that Fos is inactive for certified statefile handoff and that the legacy `Receiver` log is not the dynamic Darcy operator description. Retained inputs and programs remain frozen.

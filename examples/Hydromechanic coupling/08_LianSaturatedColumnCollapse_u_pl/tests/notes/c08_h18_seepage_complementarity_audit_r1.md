# C08 free-seepage complementarity: bounded read-only audit

2026-11-14. Only this note is new. No code/probe, build, solver, reader, native-payload scan, analysis script, Git or external browser was run. Source is tests/outputs/c08_preload_schema2_source_r1/full_source.zip, original src/source/JSphGpu_ker.cu, JSphGpu.cpp/Single and matching CPU path. Current AS03/AV20 host instrumentation does not redefine this hydraulic operator.

## Direct answer and notation

The original negative-pressure FS2/3 branch is not an explicit enforcement of zero normal combined Darcy flux. It is a particular truncated-support Taylor-defect closure, followed separately by completed-step positive-pressure projection. Its hydraulic RHS branches on FSType, not on the pressure sign.

Use the actual code's g_p (corrected pressure gradient), Lp (pair-C pressure differences), Lx (pair first moment), Da=sum Vj*(a_j-a_i) dot corrected_gradient, and a_i=Ace_i. For scalar isotropic k define F=g_p+rho_w*a_i. Source GPU kernel1534-1569 assembles these at the same stage; fixed-wall donors use their current fitted state. The mechanical Ace excludes body gravity.

The interior expression is:

L_int = Lp - g_p dot Lx + rho_w*Da.

At actual free-seepage FS2/3 the original expression is:

L_FS = Lp + rho_w*(a_i dot Lx+Da)
     = L_int + F dot Lx.

These are GPU1584-1588; matching CPU3251-3254. There is no p<0 test and no surface normal in this branch. It applies to zero/negative saved FS pressure and also to any positive half-stage FS pressure permitted by CompletedOnly.

Algebraically this replaces the full g_p target inside the Taylor correction by -rho_w*a_i. The actual pressure values and computed g_p are not changed to satisfy that relation. In particular, n dot F=0 permits a nonzero tangential F, and does not imply F dot Lx=0. A full-vector defect omission is therefore different from imposing a normal condition. At variable k, GPU1593-1600 additionally retains grad(k) dot F from the actual g_p and a_i; the same full-vector assumption is not even imposed on this entire product-rule contribution.

## Pressure sign policy is separate

CPU JSphCpu.cpp1231-1233 and the GPU free-surface predicate select native FS2/3. GPU1424-1438/kernel1108-1109 cap only finite positive pressure on normal native fluid at completed geometry, retaining negative pressure and leaving its rate unchanged. Predictor PorePressPreg prevents this cap at the half state. The true Dirichlet path at kernel1104-1106 instead sets both signs p=0 and rate=0 when HydroMechDrainage is active; that is not current C08.

Consequently p<0 does not select a new no-flux stencil, disable the RHS, reset the rate or pin pressure to zero. It merely avoids the positive cap while the same raw-FS operator continues evolving. Negative FS pressure is neither proof of zero normal flux nor, on its own, a violation of the chosen p<=0 ponding inequality. Setting every such pressure to zero would introduce a different boundary/model.

The original pre-drain closedfs branch (GPU1575-1583) does use a normal-projected Taylor target. Host closedfs means HydroMechDrainage&&!drainfs (CPU3188-3189; GPU2087). C08's free-seepage-only configuration does not activate this closed-pre-drain branch.

## What Lian2023 actually establishes

Local src/papers/u-pw/Lian 2023 u-pl.md:

- Lines170-179, Eqs5-6, printed3: relative water/solid velocity is driven by -grad(p)+rho_w*b-rho_w*D(v_s)/Dt, while mixture acceleration is stress-divergence acceleration plus b. Therefore n*w_ls=-k/gamma*(grad(p)+rho_w*Ace) after cancelling body acceleration consistently. Do not add gravity to the code's Ace a second time. For positive scalar k, zero physical normal relative flux would require the corresponding n dot F=0, with a properly defined normal.
- Lines204-214, Eqs9-10, printed4: pressure evolution contains total velocity divergence plus divergence of that relative transport. A pressure inequality alone does not specify all discrete flux terms.
- Lines299-320, Eqs22-23, printed5-6: the first-moment Taylor correction removes particle-distortion error in the second derivative. These bulk formulas do not by themselves prove the validity of deleting the entire vector defect on every FS particle.
- Lines881-889, printed19, Section4.4: walls are impermeable, the surface uses the free-seepage treatment of reference36 plus p_l<=0 ponding. This local statement does not give the complete discrete active/inactive flux/complementarity equations. Reference36 is the earlier transient unsaturated-seepage framework (bibliography1289ff).

Thus the current inequality is compatible with the text, but that alone does not establish exact reproduction of its hydraulic boundary. The present model is saturated; retained negative gauge pressure is not a separately solved unsaturated/cavitation state. Eq47 is TPI negative-pressure stabilization, not a substitute for a boundary flux definition or permission for an explicit clip.

## What the rejected normal-Taylor candidate changed

The exact private intervention is documented in notes/c08_fs_normal_taylor_r1.md and its frozen CPU/GPU source. It retained original p, classification, normals, material, time integration and force. At FS it formed:

g_c = g_p - n*(n dot F)/(n dot n),
L_normal = L_int + (n dot F)*(n dot Lx)/(n dot n).

This retains the tangential Taylor correction instead of omitting the entire F dot Lx. It also changes the variable-k chain to grad(k) dot (g_c+rho_w*a_i). That is an explicit additional consequence even though the chain source line was not edited. It projects the target used inside this RHS; it does not solve p so that its actual reconstructed gradient obeys zero normal flux, construct conservative pair/face flow, or close the post-force NoPen reaction.

The flat-top affine component found an actual tangential-consistency counterexample for the raw branch. It proved an operator limitation under those manufactured states, not the cause of C08 suction. Production normals were slightly tilted, so even the projected target was not an exact geometric-flat continuum condition.

Physical decision is notes/c08_fs_normal_window_decision_r1.md: original AS.5/n3.825, Wendland H1.8/5us, same PRE and91 actual matched saves. Raw -> normal candidate worst suction -85.4465 -> -88.2433kPa, maximum p RMS36.7548 ->36.5501kPa, final close pairs23 ->27, front advance .338313 ->.337519m and early arrest persisted. The slight RMS/local-affine benefit did not justify selecting this closure. It remains rejected; it is not carried into AS03 or reopened here.

## What remains unknown

The actual C08 history has not measured a conservative boundary-relative flow or established active/inactive seepage-face complementarity at every force stage. Neither saved p<=0 nor the previous normal-projection implementation test supplies that evidence. Changing FS membership can change the chosen RHS without a corresponding recorded flux; saved10ms labels are not the full substage membership history.

The cumulative storage observer can distinguish pressure increment, capacity change and actual positive-cap removal under the original algorithm. Its S=sum(nV*p/Kw) is a conditional storage proxy, not water mass. Its sidecar does not record every force-stage normal F or FS membership; successful storage telescoping cannot prove the missing boundary-flux property.

The current same-stage Darcy acceleration also omits the later fixed-plane projection impulse (ReactionClosed=false). This is a declared contact coupling limitation, not evidence that a different FS correction is the root cause. These questions must stay distinct from the separate momentum/strain work audit.

No new cap/filter, blind parameter trial, normal-Taylor rerun or additional solver is proposed by this audit. First interpret the already prepared cumulative observer under its actual limitations; any later boundary change would need a separately defined flux condition and a falsifiable, bounded qualification rather than merely smaller negative pressures.

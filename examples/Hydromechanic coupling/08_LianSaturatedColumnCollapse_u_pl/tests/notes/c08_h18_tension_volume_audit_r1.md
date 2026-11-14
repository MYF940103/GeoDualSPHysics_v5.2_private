# C08 psi0 tension-face volume: bounded read-only audit

2026-11-14. Only this new note is written. The audit reads the original archived material header, the current same header, existing one-step completions/review summaries and three bounded material-shadow CSVs. No script, material component, solver, reader, build, Git, SHA or native-array scan is executed. The frozen negative-pressure note is unchanged.

## Bound source and the actual constitutive distinction

Reference: tests/outputs/c08_preload_schema2_source_r1/full_source.zip, src/source/FunSoilMaterial.h. This one current source header was also read and is byte-for-byte equal to the archived text; this is not a tree/hash scan. The private AV20 host override does not change this material law.

Let I=trace(sigma_effective), q=sqrt(J2), a=DP_phi, kc=DP_kc and b=DP_psi. The code's names remain DP_phi/DP_kc/DP_psi. Smooth flow (lines105-109,172-175,202-205) gives:

I_return = I_trial - 9 K b lambda_shear.

For psi0=0, UpdateDPvars (52-68) gives b=0, so this shear return preserves I even when cohesion softens. A SmoothEndpoint labelled Apex can also preserve I; the label alone does not prove plastic volume.

The distinct ReturnApex policy (127-150) first removes trial deviatoric stress with lambda0=q_trial/G, evaluates coefficients at kappa_tip=kappa_n+lambda0/sqrt(3), and defines I_tip=kc/a (a>0). Positive dilation can reach the tip through its original flow (138-143). At psi0 that positive-b branch is skipped. The additional existing tension face uses f_t=I-I_tip and g_t=I (145-149):

lambda_tension = (I_trial-I_tip)/(9K),
Dret = I_trial-I_return = 9K*lambda_tension,
delta(epsilon_p_vol)_return = Dret/(3K) = 3*lambda_tension.

The last expression is the small-strain isotropic elastic/plastic decomposition of the stress correction, not an extra native porosity variable. Thus psi0 does permit an additional positive plastic-volume return through this separately declared face. It is not the b=0 shear potential.

Kappa records the equivalent deviatoric plastic increment lambda0/sqrt(3); a purely isotropic tension multiplier does not add to it. In the exact q_trial=0 limit the code can reduce I with unchanged kappa. This is not automatically a history-update bug: kappa is not total plastic volume. For q_trial>0 a positive continuous kappa increment can also round away in the saved float history. Whether separate tensile-fracture softening should be modelled is a different constitutive choice.

This cap keeps an otherwise unreachable nonassociated psi0 cone-tip state admissible. Removing it does not supply another valid return: the zero-dilation shear potential cannot lower I to the tip. The explicit source comment does not claim that this added policy is the original single-potential apex solution or a general positive-work proof. Neither its necessity for this implementation nor its commit status establishes that its tensile law is a calibrated soil-fracture model. It must not be cancelled as a presumed bug.

## What the existing actual steps show

Read evidence: outputs/c08_h18_late_step_r1_p200, p250 and p300 completion.json/material_shadow.csv; logs/c08_h18_late_step_review_r1.check.json; figures/c08_h18_late_step_review_r1_cohorts.csv. All are from the old original AS0.5/n2.55 H1.8 trajectory, not current AS03/AV20 full histories.

Each original CPU component restored one saved GPU state and advanced one real5us step with two actual force/Darcy calls. The extra pure material shadows were evaluated afterwards without feedback. Their six stress components and history policy match the actual commits bitwise. Their status is therefore a bit-matched same-input reconstruction, not a hook recording the original call's status.

Important sign: raw material_shadow.csv return_deltaI_Pa is I_committed-I_trial. This note defines positive trace reduction Dret=I_trial-I_committed=-return_deltaI_Pa. K=19607844Pa, 3K=58823532Pa.

| Old source Part / tau | Full-stage tension IDs | mean Dret over5000 [Pa] | mean Dret/(3K) over5000 | max Dret [Pa] / ID | max Dret/(3K) |
|---|---:|---:|---:|---:|---:|
|200 /2.0000049999242844s|164|.0986696454|1.6773838972e-9|18.7603551 /5102|3.1892602269e-7|
|250 /2.5000049999053555s|174|.0977183481|1.6612118450e-9|13.3954009 /6377|2.2772180555e-7|
|300 /2.999999999886427s|162|.1045858778|1.7779598438e-9|30.4804803 /4899|5.1816814201e-7|

The full-stage mean Dret over the tension subset alone is3.008220895,2.807998509,3.227959190Pa. The same subset is entirely source-interior and p<0 in the published cohort table. Correlation does not establish pressure as the direct return input: ReturnMaterial consumes effective stress, not total sigma-pI.

Half-stage tension counts are also164/174/162. Mean Dret over5000 is .0493363919/.0488599512/.0522948785Pa; normalized mean is8.3871862530e-10/8.3061913377e-10/8.8901289470e-10. Half maximum Dret is9.38064595/6.69785667/15.24028152Pa at IDs5102/6377/4899. Predictor histories are intentionally kept at kappa_n; all164/174/162 unchanged actual predictor histories are not evidence of an omitted commit.

In every tension row of these six sampled stages, q_trial>0, kappa_n>0 and continuous kappa_increment>0. No q_trial=0 or kappa_n=0 tension event was observed here. The exact-zero possibility is established by the code, not by these samples.

Actual full-stage float-kappa unchanged counts are6/2/6, identical to the reconstructed saved-float shadows:

- Part200:5295,5586,5925,5927,5928,6075.
- Part250:5928,5975.
- Part300:5537,5634,5732,6422,6861,6872.

Their q_trial ranges are respectively .148910574-.528904872, .307697490-.423479522, .128659870-.513517960Pa. Their continuous increments remain positive, approximately9.88e-9 to4.06e-8 across all14 events, but are below the saved float change at their existing kappa. Example Part200 ID5295: kappa1.090965867 unchanged, continuous increment4.06133e-8, Dret6.69558750Pa and Dret/(3K)=1.1382498244e-7. Example Part300 ID5537: kappa1.341495991 unchanged, continuous increment1.20201e-8, Dret .633298905Pa. No native history was rewritten.

The existing trace-balance identity is:

delta(logJ)-delta(I)/(3K)
= log-quadrature - rate-trace-mismatch - trial-addition-roundoff + Dret/(3K).

For these full steps the measured mean left side is1.6773830660e-9/1.6612131708e-9/1.7779612518e-9, matching the return contribution above. Mean rate-trace differences are about1e-15 strain-equivalent; mean log-quadrature terms about1e-19. Thus the sampled trace/logJ defect is demonstrably dominated by the material return, not a large operator-roundoff discrepancy. This conclusion is limited to the three actual CPU steps.

The earlier step_balance_r1 Part60 component contains pressure/J balance but no material-shadow trace instrumentation, so it cannot independently attribute Dret. The CN Part300 material_shadow.csv reproduces the same original material inputs/returns while changing pressure afterwards; it is not an independent new cap history. Its presence does not turn these observations into a current AS03 trajectory claim.

## Consequences for volume, pressure and comparison with Lian

J integrates total kinematic volume, whereas stress decomposes total strain into elastic and plastic parts. A plastic-volume correction of stress at fixed total strain need not immediately change J. Adding Dret/(3K) to J or pore pressure as another source would generally double-count or change that decomposition. The existing pore equation responds to total theta and hydraulic transport; the material return can affect later momentum, deformation and pressure indirectly. This audit does not demonstrate a missing direct pressure increment.

The saved endpoint residual R=I-I_PRE-3K*log(J/J_PRE) can accumulate negatively under such trace-reducing returns. The published volume-stress audit is compatible with that mechanism, but these three steps do not reconstruct its full GPU time integral or prove the cause of broad suction/clumping. In that earlier audit the genuinely current-kappa-zero subsets had only about .000406/.000647Pa RMS R: do not conflate kappa unchanged with kappa exactly zero.

Local Lian2023 Markdown231-263 (printed4-5), Eqs12-15, defines the single potential g0=xi_psi I+q; zero psi gives no plastic volume from that smooth shear potential. Section4.4 lines891-908 calls Fig14's psi0 response zero plastic-dilation excess. The printed equations do not specify this code's extra g_t=I face. However, the paper refers detailed constitutive implementation to Bui: this bounded audit does not prove that its underlying implementation never employs a tensile/apex treatment. Consequently the paper's psi0 image is not an exact reference for every pressure or strain component in our cap-active trajectory, and native p-fixedP0 is not automatically that plotted plastic-dilation excess.

## Minimum next information and limits

The existing AS05 samples already establish active trace-reducing return; repeating another AS05 late step is unnecessary. If root needs causal attribution in the selected AS03/AV20 trajectory, the unresolved information is an actual original-step return trace at one already saved onset state, together with the existing pressure/J split, preserving the same material/force lifecycle. Recording actual status/multipliers or bit-matched shadows, Dret and continuous versus saved kappa would distinguish an active tension policy from operator/integration contributions. A single sampled step would still not identify the full-history integral or justify disabling a cap.

No broader DP rewrite, cap/apex removal, new material law, physical window, PRE, half chain, other-psi run or acceptance is admitted by this note.

# Primary material-equation audit (read-only)

2026-11-06. No constitutive source, program, tests, thresholds or legacy defaults changed. This resolves definitions/signs from the original PDFs, not from Markdown extraction alone. Rendered and visually inspected: Lian (2023), PDF pp.4-5, Eqs.11-19; Bui & Nguyen (2021), PDF pp.16-18, Eqs.68-87 and Algorithm 2. Source page images: `../figures/upl_material_primary_r1_lian_p4.png`, `_lian_p5.png`, `_bui_p17.png`, `_bui_p18.png`.

## 1. Which accumulated plastic measure?

Bui Eq.78 explicitly defines positive accumulation from the **deviatoric** plastic strain:

\[
 d\kappa=\sqrt{(2/3)\,d e^p:d e^p},\qquad e^p=\operatorname{dev}\epsilon^p.
\]

Lian Eq.13 visibly uses derivatives with respect to **s** inside its norm, rather than full stress. Eqs.17-19 use one accumulated equivalent plastic strain, \(\epsilon_p^{eq}\), for friction, cohesion and dilation decay. Identifying that measure with the deviatoric \(\kappa\) in Eq.13/Bui Eq.78 is the consistent intended reading; Lian does not separately write an explicit equality between its two symbols. Bui Eqs.81/87 instead print a full \(\partial g/\partial\sigma\) norm, inconsistent with their own Eq.78 for nonzero dilation; the current soft routine follows that printed full-norm expression, not Eq.78. Bui Eq.80 also writes \(|\epsilon^p|\) for dilation decay without a separate incremental norm definition; do not silently substitute that notation for Lian Eq.19.

For \(g=\beta I_1+\sqrt{J_2}\), \(J_2>0\),
\[
 m=\partial g/\partial\sigma=\beta I+s/(2\sqrt{J_2}),\quad
 m_{dev}:m_{dev}=1/2,\quad h_{dev}=d\kappa/d\lambda=1/\sqrt3.
\]

The current softening routine uses \(h_{full}=\sqrt{(2/3)(3\beta^2+1/2)}\), i.e. includes plastic volume. Its constant-strength routine removes plastic volume before accumulating \(\kappa\). These are different history definitions for nonzero dilation. For the retained plane-strain parameters, full/dev differences are about +0.06337% at +2.5 degrees and +0.25224% at -5 degrees. At zero dilation both definitions coincide apart from float arithmetic; zero-dilation evidence cannot distinguish them.

## 2. The printed denominator has a real sign inconsistency

Lian Eq.13 and Bui Eqs.81/87 **really print a plus**, including in the rendered PDFs. Bui Eq.86 on the same page, however, gives
\[
 f_{new}\simeq f_{trial}-f_\sigma:\Delta\sigma^p+f_\kappa\Delta\kappa,
\quad\Delta\sigma^p=D^e:m\,\Delta\lambda,\quad\Delta\kappa=h\Delta\lambda\ge0.
\]

Therefore, with the **literal partial derivative** \(f_\kappa\),
\[
 \Delta\lambda={f_{trial}\over A-f_\kappa h},\qquad
 A=f_\sigma:D^e:m=9K\alpha\beta+G.
\]

The same result follows directly from Bui Eqs.69/70/73/78; Algorithm 2 explicitly adds positive \(d\kappa\) to old \(\kappa\). A plus would be consistent only for an explicitly redefined modulus \(H=-f_\kappa\); neither source defines that replacement. Thus the plus cannot be justified by a hidden negative accumulation or a code convention. This is a primary-equation inconsistency, not OCR. No automatic global sign flip is authorized by this audit.

## 3. Current source and retained observations

`JSphCpu.cpp:3788-3835` computes exponentially decreasing strengths and the literal derivative
\(f_\kappa=I_1\alpha'(\kappa)-k_c'(\kappa)\). The prior independent finite difference confirmed its positive sign for cohesion softening. `:4007-4010` then uses **full** norm and \(A+f_\kappa h_{full}\); `:4033-4035` writes \(\kappa+\Delta\lambda h_{full}\) as float. `:4040-4058` projects using coefficients still frozen at **old** kappa; it does not solve the new-strength yield equation.

Consequently the observed new-kappa residuals (about 0.128-1.492 Pa) cannot be dismissed as the roughly 0.0008-Pa float coefficient noise. Sign/old-strength consistency is independent of the norm discrepancy: the positive residual already exists at zero dilation. The float-history synthetic ULP loss remains a separate observation and does not justify changing material constants or all state to double.

## 4. Minimal next material step, after the current GPU work

Reuse the existing tiny linked material-point probe, not another spatial/half chain. One reviewed candidate must expose first return and final projection separately; evaluate yield at **new saved kappa**, use one explicit deviatoric history definition, and preserve constant-strength/unloading controls. Include nonzero shear and the actual Lian -5-degree/cp=7500-Pa group. Evaluate \(\psi=\psi_0 e^{-s_f\kappa}\) inside the material routine at its declared trial/current state, not once outside the particle return. Yield is independent of psi, so no spurious direct \(\partial f/\partial\psi\) belongs in `Updatedfdk`; psi changes the flow direction and A. This is a low-cost candidate design, not an implemented correction or physical acceptance.

Primary files: [Lian PDF](<../../../../../src/papers/PDF/Lian 2023 u-pl.pdf>), [Bui PDF](<../../../../../src/papers/PDF/Bui 2021-CG.pdf>). Prior measured probe: `lian_material_baseline_review_r1.md` and retained `../outputs/lian_material_baseline_r1/points.csv`.

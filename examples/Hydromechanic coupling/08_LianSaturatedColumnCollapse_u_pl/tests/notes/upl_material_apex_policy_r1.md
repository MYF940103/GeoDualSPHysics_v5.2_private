# Apex / tensile-cap policy audit

2026-11-06. Read-only constitutive conclusion. No production change, new candidate, build, material/spatial run or Git operation. The completed radial material-point evidence is retained separately; apex policy is deferred and does not block elastic wall/cache compatibility.

## Original source and exact correction

Bui et al. (2008), original PDF **pp.8-10** (printed pp.1544-1546), Section 3.3, expressly uses an **elastic-perfectly plastic** model. PDF p.9, Section 3.3.1 / Figure 2 / Eqs.29-30, gives:

\[
I_1>k_c/\alpha_\phi:\quad
\bar\sigma_{aa}=\sigma_{aa}-\tfrac13(I_1-k_c/\alpha_\phi),
\]

with shear components unchanged. This corrects hydrostatic tension beyond the apex. PDF p.10, Section 3.3.2 / Eqs.31-33, then scales deviatoric stress when \(q=\sqrt{J_2}>k_c-\alpha_\phi I_1\):

\[
r=(k_c-\alpha_\phi I_1)/q,\qquad
\bar s=r s,\quad \bar I_1=I_1.
\]

Together, a hydrostatic cap followed by scaling maps a nonzero deviator to the full apex (the numerator becomes zero). An already hydrostatic state needs no division by zero. PDF p.20, Section 4.6, specifies checking the stresses after each integration step and applying these corrections, also at the leapfrog half step.

**The paper supplies no extra accumulated softening-history or plastic-volume update for these corrections.** It therefore supports the stress-admissibility projection policy, not a unique extension to Lian's evolving cohesion/dilation. The paper also states that hydrostatic tension correction alone is insufficient to suppress cohesive-soil SPH tensile instability; its artificial-stress treatment is a separate issue.

Source: [Bui 2008 original PDF](<../../../../../src/papers/PDF/Num Anal Meth Geomechanics - 2008 - Bui - Lagrangian meshfree particles method  SPH  for large deformation and failure.pdf>). Original PDF pp.9-10 were rendered in memory and visually inspected. Local transcription: `src/papers/elastoplastic basic/Num Anal Meth Geomechanics - 2008 - Bui - Lagrangian meshfree particles method  SPH  for large deformation and failure.md`, lines 466 onward and 522 onward; the original equations take precedence over damaged OCR.

## Current code and missing closure

In `ConsRelationEPsft_fast` (`JSphCpu.cpp`, current lines 3993-4062), strengths are evaluated at old float kappa; the multiplier is formed, then `G/sqrt(J2)` is evaluated (4019); kappa is written (4041-4042); only afterwards are the hydrostatic cap and radial scaling applied (4047-4062), still with old strength. No history correction follows the final projection. Thus the existing cap does not protect a plastic `q=0` trial from the earlier undefined flow direction.

The new material-point helper deliberately reports apex cases as unsupported. For the smooth potential \(g=\beta I_1+q\), a positive multiplier gives \(\Delta I_1=-9K\beta\Delta\lambda\). Pure hydrostatic tension cannot be reduced by that smooth flow when psi=0; negative psi increases I1 instead. Clipping the trial stress before the smooth return does not prove history/volume consistency, and unsupported is not elastic acceptance.

## Two meanings that require an explicit model decision

1. **Retain a stress-only numerical cap.** Do not add kappa for the final projection. This is closest to the existing post-step policy and Bui 2008's stated stress correction. With deviatoric scaling, however, saved kappa cannot simultaneously be claimed to measure the whole actual plastic-deviatoric stress correction.
2. **Treat the cap as an independent inelastic mechanism.** Infer its plastic correction from the elastic compliance of the complete trial-to-return stress change; use deviatoric equivalent strain for kappa, evaluate the strength at the declared updated history, and record its plastic trace separately. This is a model extension requiring validation, not an existing softening rule supplied by Bui 2008.

For a pure hydrostatic cap the compliance-derived deviatoric kappa increment is zero, while the implied plastic trace is \((I_{trial}-I_{cap})/(3K)\), generally nonzero. For a complete radial-deviator removal to the apex its total deviatoric equivalent increment is \(q_{trial}/(\sqrt3G)\). These are compliance identities, not proof that the correction follows the specified non-associated potential. Total J/porosity remains governed by total kinematics; stress clipping must not directly modify J or pore pressure.

A later narrow constitutive candidate can combine a consistent deviatoric radial return and an explicitly declared tensile-cap policy, choosing mutually exclusive paths before any `G/q`, preserving default legacy behavior. It must state the cap strength/history timing and avoid double-counting a successful radial return. The known phi=25-degree material avoids `kc/alpha` at phi=0; no general zero-friction/apex model is admitted. The constitutive choice must remain independent from the dynamic-seepage switch. No production apex choice is made by this note.

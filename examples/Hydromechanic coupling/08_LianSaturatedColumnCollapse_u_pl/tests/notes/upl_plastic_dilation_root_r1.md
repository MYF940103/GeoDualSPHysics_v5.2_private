# Periodic dilation and decay: bounded integration review

2026-11-06; base86bc238ac04f5d60079a486531f04c4ece58242b. The sole production
change removes dlt==0/psiDecay==0 from the existing narrow periodic material
predicate in JSph.cpp. The actual shared material core, stage order, J/pressure
sources, float material/history types and all original rejection budgets remain.
No plastic-volume source was added: J and pressure continue to use total theta.

POS uses psi0=+2.5deg/cp5000 Pa; NEG uses psi0=-5deg/cp7500 Pa. Both use cr1000 Pa,
n_coh5 and sf=float(.2), the same genuine1024-owner lattice and literal initial
velocity table, constant k,dt2^-19,128 updates and five exact actual saved times.
Companions are explicitly derived, and no GenCase or retained control was rerun.

Default CPU Debug and GPU HostDelta Debug builds passed; GPU reused14 unchanged
CUDA objects and compiled97 host objects with all111 actual link inputs verified.
One new115-line native profile was compiled once. Each of the four candidates
ran once and was decoded once; both GPU targets passed memcheck with zero errors
and leaks. Each native result passed22 arrays,1024 IDs,5120 ledger/cache checks,
1024 initial velocity checks,4096 nondecreasing-kappa checks and four original
signed interval guards. The CPU driver's initial parse error launched no program;
its setup record is preserved separately, not counted as a physical attempt.

At0.000244140625s, POS CPU/GPU max kappa is0.00033009116305/0.00033009119215
(640 positive IDs); NEG0.00019435035938/0.00019435040304 (512 IDs). Final pressure
RMS is34.84380559/34.84394567 Pa for POS and8.93606226/8.93657928 Pa for NEG.
Negative pressures were not clipped. Minimum saved-history cohesion is about
4993.40362 Pa /7493.68668 Pa; only small softening and dilation relaxation occurred.

Across all five times, maximum CPU/GPU pressure-difference RMS is0.00453120077 Pa
(POS),0.00228225483 Pa (NEG); total-stress Frobenius-difference RMS0.00792811806 /
0.00395201914 Pa. These compare matching material options and IDs, not POS-versus-NEG
accuracy: their peak cohesions differ. Initial FSNormal/PosDiv differences are
recorded, without an all22-field cross-backend bit-equality claim.

Root inspected `../figures/upl_plastic_dilation_pair_r1.png`: six panels, raw
times, units, small strength/angle changes and different material parameters are
clear. Matching `_history.csv`, `_differences.csv`, `_arrays.csv` and independent
visual QA retain all five states. No theory curve, fitting, smoothing or new
physical/half-step gate is inferred. These checks do not prove complete softening,
gravity-plasticity, prestress, wall removal, localization, restart or collapse.

Next: reuse the existing fixed-gravity/mixed-slip container scope for the material
selector, keeping its geometry and operator checks. Cold elastic startup is not
nonzero-plastic wall evidence or the paper's gravity equilibrium.

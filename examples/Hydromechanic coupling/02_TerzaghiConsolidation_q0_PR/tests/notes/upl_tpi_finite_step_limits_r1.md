# Finite-h rejection of reflected candidates; narrow P1 load-clock correction

2026-11-17. New author-only assets: this note and `support/upl_tpi_finite_step_limits_r1.py`.
No author execution, SPH, reader, build, old-script import/main, reference solve or SHA scan.
The earlier tiny-h32-map result was mathematical only; it did not admit10us.
H3 common/CPU/component drafts are retained **HOLD**, not prepared/built/run; the component CPP was not created.

## Finite-h reduction and its scope

Use the same original case02 XML example M=2692307.6923Pa,rho2100,rho_w1000,
k1e-4,gamma9806.65. Set r=rho_w/rho, t=1-mu, e=r*t, delta=(1-r)*t,
m=1-delta, tau=k*(rho-rho_w)/gamma, C=delta*h/tau, Omega^2=M*q^2*h^2/rho.
Mu is a prescribed common Fourier-row symbol, not a measured full SPH eigenvalue.
In the formal low-Omega limit, one neutral stress root factors out of the H3 four-state polynomial:

```
z^3+(2*C-3*m)*z^2+(4*m-1)*z-m=0.
```

For0<m<1 and C>0, real Schur reduction gives `C<4*m` and
`m*C<(1-m)^2`, i.e. the critical additional condition `h/tau<(1-m)/m`.
Tau≈11.2169us; mu=.2 gives h<≈8.09us, mu=.8 h<≈1.313us.
This explains why the autonomous tiny-h consistency result does not support a10us step.
It is not a new hard SPH gate: the actual traction/Neumann/FS/force operator need not possess the assumed symbol or null mode.
In particular, m→1 does not itself prove a real global pressure gauge or infinite-M0 instability.

With the explicitly requested known source `a_source=a_n` instead of `a_h(guess)`, the low-Omega cubic is

```
z^3+(2*C-2*e-3*mu)*z^2+(2*e+4*mu-1)*z-mu=0.
```

For0<mu<1, necessary Schur conditions are `C<2*e+4*mu` and
`mu*C<(1-mu)*delta`, equivalently `h/tau<(1-mu)/mu`.
Mu=.2 allows≈44.87us, but mu=.8 only≈2.804us. This is not a general10us remedy.
Writing the smooth constraint as p_star=P*y, its remaining first-order pressure term is
`h*r/[2*(1-r)]*(E_sigma-P)*L*y`, where E_sigma=[1,0].
The old-acceleration source restores a half-step source lag; it must not be renamed solved new acceleration.
Extrapolating `a_source=1.5*a_n-.5*a_previous_F0` restores the leading half-time source,
but needs a fifth genuine full-old-force history and recovers the unfavorable finite-h feedback.

## Independent finite-h checks already observed

Root directly inspected the new math definition at actualh; child independently formed the matrices in an inline
NumPy expression without importing any old/new author module. The small new script reproduces only these8 combinations.
At h10.00022888us:

| q | mu | H3 radius | old-a radius | extrap-a radius |
|---|---:|---:|---:|---:|
| pi/2 | .2 |1.038110349|.999999323|1.038110362|
| pi/2 | .8 |1.175407217|1.130156429|1.175407222|
| pi/.01 | .2 |1.043840238|.972422930|1.044363622|
| pi/.01 | .8 |1.180666156|1.135184611|1.180880943|

At20.00045776us the largest radii are respectively1.275656079,1.229746186,1.276403305.
All three reflected candidates have counterexamples; none is selected for a physical implementation.
These are robustness counterexamples for the proposed closure, not a claim that an actual SPH production eigenvalue equals one of them.
The optional author check reports arithmetic completion, not stability passage; it cannot launch later work.

## P1 ordering alternatives and the selected narrow change

The explored pressure-first closure `Euler predicted endpoint -> one Eq38 p1 -> mean(pn,p1) at mechanical half`
has exactly the same homogeneous4x4 characteristic polynomial as current P1, for all Omega^2,C,e,m
(independent symbolic determinant difference was exactly0). Its leading lag remains
`-h*m/[2*(1-m)]*P*L*y`; reordering by itself does not cancel the one-row lag.
The half/end separated stronger extrapolation and reflected candidates are not selected.

The next narrow author action therefore retains **all** current P1 history, pressure rows, mechanical/J/material/HG
updates and three forces, changing only external-load evaluation from allTn to F0Tn/F1Tn+h/2/F2Tn+h.
The actual scalar source/native clock and original Dirichlet/event policy remain unchanged.
The homogeneous map is identical because there is no external source in that map.

For local linear forcing f(t), let p_star=P*y+D*f(t), with
`D=rho_w*iq/[q^2*(1-r)]`, and let c=m/[2*(1-m)]. The established current P1 pressure lag is

```
all-old load clock:       p-p_star=-h*c*d(p_star)/dt-h*D*f_dot+O(h^2)
stage-aligned load clock: p-p_star=-h*c*d(p_star)/dt+O(h^2).
```

The half mechanical force also loses its avoidable old-time local forcing defect
`-h^2*e_v*f_dot/2` when its load is evaluated at Tn+h/2.
This is a deterministic time-order correction, not overall second order: intrinsic one-row lag remains.
Finite band geometry, wave startup, ramp corners and drainage discontinuities are not an exact linear-forcing reference.

For q0=10000Pa and ramp≈.01s, the10us old half/end load ages correspond to≈5/10Pa.
Using S_infinity=3.7142857mm only as a uniform quasi-static scale gives≈1.86/3.71micrometres.
The differential ages10us versus6.25us are≈1.875/3.75Pa, or≈.70/1.39micrometres on that scale.
The existing near-.15s top-error increase is2.8835micrometres, with distinct actual sample times;
these estimates identify a plausible relevant scale, **not** a decomposition proving that the clock fix explains it or will pass.
No radius, time, load or reference is fitted. No pressure/top/bottom/stress budget changes.

If stage timing alone is insufficient, two genuine complete endpoint defects would give m_effective=m^2
and reduce the simple-row lag coefficient by m/(1+m), still first order. Recomputing actual a(newguess)/Taylor
is mandatory; retaining old Da is not the same residual. A straightforward version costs a fourth force,
about one-third more interaction work rather than a proven wall-time ratio. It is not selected by this note.

## Root-only optional algebra execution

After complete review only: `python -B tests/support/upl_tpi_finite_step_limits_r1.py --execution-authorized`.
The only products are a new8-row CSV under `tests/outputs/upl_tpi_finite_step_limits_r1` and its log check.
The script independently constructs24 small matrices/104 roots, checks arithmetic and records counterexamples;
no original component or physical state is run. Exclusive output checks preserve existing/partial results.
P1 host-clock author/build/real regression decisions belong to root, not this mathematical check.

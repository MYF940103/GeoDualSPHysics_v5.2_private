# Conditional next P1 correction after the staged-load window

2026-11-17. Read-only reasoning/author preparation. The one running staged-load10us2s
job and every bound source/program/input remain untouched. No solver, reader, build,
old script or new mathematical main is executed. H3/reflection drafts remain HOLD.
The new small author `support/upl_tpi_next_time_layer_options_r1.py` is independent
fixed-mode arithmetic only; root must read it before any separate algebra execution.

## Paper statements versus current implementation

Lian2023 Sections3.3–3.4, Eq27 and Fig1 specify LF half-level p/sigma/v/n and
pressure before constitutive/acceleration updates. Eqs35–39 first define a local
pressure row and replace unknown neighbour pressure by a two-history extrapolation;
alpha=.5 is the paper's selected numerical value. Eq36 contains the acceleration
source, and the text treats its source as known, but does not fully specify that
source's time centring. Eq40 limits timestep by both mechanical and amplified
hydraulic scales. It neither proves an arbitrary large step stable nor prescribes
benchmark error budgets or a converged pressure solve.

Current P1 is the explicitly documented full-step Symplectic-compatible variant.
Its full R_gamma includes Taylor/Neumann and rho_w*div(k*a), evaluated at the current
endpoint pressure guess. S is only leading-LP, not the complete Jacobian.
Current acceleration feedback is therefore **retained**, not an accidentally omitted
old source that can simply be dropped. Stage-load clocks now under test remove an
avoidable forcing-time error while retaining all P1 pressure history/mechanics/HG.
They do not remove the intrinsic one-row lag.

## Lowest implementation-risk next candidate, only if needed

Retain original two physical mechanical forces and the committed endpoint geometry,
v/sigma/J/n/rho/material/HG history. At the already required endpoint do:

```
g = p_n + .5*(p_n-p_previous)
R0,S = full_original_row(endpoint,g,a(endpoint,g))
p1 = g + R0/S                       # first true complete defect
refresh actual pressure BC/ghost/periodic data
R1,S = full_original_row(endpoint,p1,a(endpoint,p1))
p2 = p1 + R1/S                      # one additional complete defect
apply genuine endpoint BC; commit history once using the accepted p2
```

Both endpoint forces use the same staged load time Tn+h and unchanged actual global
source/Dirichlet clock. They do not update material/J/position/HG history again.
Source acceleration and Taylor/Neumann terms must be recomputed from each actual
pressure guess. Updating only LP while retaining old Da is not a second iteration
of the same full equation. No alpha/beta, diffusion, damping, load or space tuning.

A straightforward implementation requires **four** complete force evaluations per
step: old / mechanical-half / endpoint-first / endpoint-second, instead of three.
This adds about one-third interaction work, not a controlled wall-time prediction.
An eventual pressure-only operator application could cost less but would require
its own exact force/BC/Jacobian decomposition; that optimization is not assumed.

## What one extra iteration can and cannot achieve

For a frozen linear pressure row T(g)=p_star+J*(g-p_star), repeated complete defects
give T^k(g)=p_star+J^k*(g-p_star). In the common Fourier model
m=rho_w/rho+(1-rho_w/rho)*mu, delta=1-m. With the original alpha=.5:

```
one row:  p_n-P*y_n = -h*m/[2*(1-m)]*P*L*y_n + O(h^2)
two rows: p_n-P*y_n = -h*m^2/[2*(1-m^2)]*P*L*y_n + O(h^2).
```

The coefficient is reduced by m/(1+m) for0<m<1. It is generically still O(h),
**not eliminated and not made second order**. Exact removal requires a converged
constraint (or a genuinely different justified time integrator), not renaming one
Jacobi correction an implicit solve. A complete *global* Jacobian/Newton solve is
different from a full local diagonal; the latter need not make J=0.
The converged model in the small author is only a mathematical fixed point at
nonzero q, not an implemented global solver or a statement about a real closed BC gauge.

Pressure lag relative to the instantaneous discrete constraint is not the same as
error relative to a quasistatic pressure/settlement companion. Changing that lag
also changes the coupled mechanical trajectory. Its sign does not predict that
the observed top over-settlement or total pressure error will decrease.

## Finite10us evidence required before a physical candidate

For k defects the ideal endpoint map uses m_k=m^k while the mechanical predictor
and half guess remain unchanged. The original source coefficient scales by
(1-m_k)/(1-m), with fixed continuous M0 constraint P. Merely substituting m^2
without also scaling the source is a different, inconsistent equation.
At low mechanical Omega, the current-P1 cubic is
`z^3-(1+1.5*m_k-1.5*C_k)*z^2+(2*m_k-.5*C_k)*z-.5*m_k`,
where C_k=(1-m_k)*h/tau and tau=k*(rho-rho_w)/gamma.
For0<m_k<1, h/tau<1 is sufficient in this *low-Omega model*.
Actual10us has h/tau≈.8915, but finite Omega, boundaries, nonnormal operators,
AV/HG and current geometry are not covered by that limit. It is not a hard SPH gate
or an admission. At20us the same sufficient scale is absent; no20us run is proposed.

The small unexecuted author reuses the existing120 nominal LP symbols and their
original loaded constants plus the four previously used illustrative(mu,q) fixtures.
It reports one/two/converged endpoint maps at the existing6.25/10/20us only.
It does not recompute a kernel, import an old component, evolve a reference or read
physical data. All eigenvalues and failures are retained; nominal radius is not
actual SPH stability. A newly unstable10us fixture blocks that proposed candidate's
mathematical rationale rather than being hidden by a smaller diagnostic step.

## Conservative implementation and physical decisions

First finish the active staged window and inspect its original unchanged budgets.
If it passes, there is no reason to add an endpoint iteration merely for elegance.
If it fails, local pressure-iteration diagnostics and the separate finite-h check
must justify any next private author. A real candidate must prove default-A
no-feedback, four actual force/necessary-bound phases, two read-only endpoint HG
additions, one material/J/position/history commit, updated legacy-rate semantics,
and all original IDs/22 arrays/ledger/FS/signed/geometry gates.
An old three-phase native checker must not certify a four-force run by relabelling.

No additional half/reference chain is prescribed. Any bounded physical comparison
retains original100Pa full-history stress/top-gap,10Pa pressure noninferiority,
.1pp normalized top-error increment and bottom.005mm plus A+.002mm budgets.
Both B results use their unchanged M0 reference; A retains its finite-Kw reference
at its own actual time. Normal exit or fewer row residuals is not physical acceptance.
No full2Tv/public-source/formal release follows automatically from this note.

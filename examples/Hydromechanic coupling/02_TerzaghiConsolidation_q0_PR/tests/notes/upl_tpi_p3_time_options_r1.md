# P3 third complete endpoint defect: review-only finite-h algebra

2026-11-17. Author preparation only. The new Python script has not been executed.
No physical source, build, solver, reader, reference trajectory, original result
or active dependency is changed. Root must fully read and separately authorize
one pure-algebra execution; nothing here admits a P3 implementation or physical run.

New files are `support/upl_tpi_p3_time_options_r1.py` and this note. The script
imports the frozen prior mathematical module for its functions, never its main
or `calculations`. It reads that passed receipt and its actual 1116 saved case rows
(P1, P2, assumed converged), preserving their original numerical results. Only
P3's 124 x 3 = 372 new matrices / 1488 roots are evaluated, using the identical
120 nominal positive-LP symbols, four illustrative symbols and original
6.25 / 10 / 20 microsecond steps. No new mode, fit, parameter scan or SPH kernel
symbol is introduced. Previous root counts/radii are not recomputed or replaced.

## Method and exact frozen-row formula

The possible P3 method retains original alpha=.5, beta0, original source/load clock
Tn, original mechanical predictor/corrector and the committed full geometry,
v/sigma/J/n/rho/material/HG history. Each endpoint round recomputes the complete
R_gamma, including pressure-dependent acceleration, Taylor/Neumann/ghost and the
original actual BC, from its actual float pressure. The next round reads the
BC-adjusted preceding result, without re-predicting or rotating pn/previous.
Only after the third actual round would pressure history rotate once.

This algebra uses the same homogeneous linear Fourier simplification as the prior
component; it does not model intermediate float/FTZ or nonlinear BC changes.
For one frozen endpoint, define

```text
r = rho_w/rho
delta = (1-r)(1-mu), m = 1-delta
g = 1.5*p_n - .5*p_previous
T(g) = p_star + m*(g-p_star), p_star = P*y_full
P = [ -r/(1-r), -gamma*i*q/(k*q^2*(1-r)) ]

p3 = (1-m^3)*P*y_full + m^3*g
1-m^3 = delta*(1+m+m^2).
```

The complete source factor is scaled by `1+m+m^2`; merely substituting m^3 while
leaving the original one-row source coefficient is a different equation. The
checker uses the stable delta expression rather than a cancellation-prone
subtraction near m=1. It also reuses the original sequential `step(...,3)` so every
round refreshes a_endpoint from its current pressure, at fixed solid endpoint.

For y=(sigma,v), Omega^2=M*q^2*h^2/rho, define the unchanged mechanical blocks

```text
H = [ 1-Omega^2/2, h*M*i*q       ]
    [ h*i*q/rho,  1-Omega^2/2   ]
K = [ Omega^2/2,       0         ]
    [ -1.5*h*i*q/rho, .5*h*i*q/rho ]
c = [1.5,-.5]

A3 = [ H                 K                         ]
     [ (1-m^3)*P*H       (1-m^3)*P*K + m^3*c       ]
     [ 0       0         1                 0       ].
```

The two top rows are H/K and the bottom row shifts accepted pn into previous.
The new checker compares this block formula with the existing sequential step,
checks linearity and eigensystem arithmetic, using the prior 4096-epsilon
roundoff budget with explicit uncancelled terms. This is numerical arithmetic
verification, not a pressure error tolerance or changed physical gate.

## Lag, finite step and what is not proved

For 0<m<1 the same smooth asymptotic analysis gives

```text
p_n - P*y_n = -h*c3*P*L*y_n + O(h^2)
c3 = m^3/[2*(1-m^3)]
c3/c2 = m*(1+m)/(1+m+m^2) < 2/3.
```

Thus three defects reduce this particular leading pressure-constraint lag
coefficient, but do not generally remove the O(h) error or make the integrator
second order. The sign/size of quasistatic-reference top settlement error is not
this coefficient and must not be extrapolated from it. The actual SPH operator
may be nonnormal and nonuniform; scalar m need not control its iteration norm.
More local iterations need not improve the coupled time scheme's stability.

The prior low-Omega cubic uses m_k=m^k and C_k=(1-m_k)*h/tau,
tau=k*(rho-rho_w)/gamma. Under 0<m_k<1, h/tau<1 is the same sufficient condition
for that limiting model; actual10us has h/tau about .8915. This is neither a hard
SPH stability gate nor a proof for finite Omega, physical boundaries or forcing.
The exact four-state finite-h P3 map is therefore separately reported. Even when
P2 and assumed-converged endpoints have radius <=1 at a step, intermediate P3
stability cannot be inferred from that fact alone.

All original20us failures are retained in the new comparison: nominal P2 has
48/120 radii >1 (maximum1.4071204396958437), assumed converged has120/120
(maximum2.1028455393404126); its illustrative failures also remain. No20us
physical candidate is proposed, and an unstable radius is reported rather than
converted into an overall algebra failure or hidden by a smaller step.

The linear model does not represent ramp/band forcing, inertial startup, drainage
switches, real Taylor/ghost boundaries, nonlinear materials or finite native
float arithmetic. It is not the literal paper LF algorithm or a global implicit
solve. All SPH, timestep, candidate-selection and physical-acceptance flags remain
false, regardless of the new radii.

## Cost and conditional decision

A straightforward P3 would need five complete forces per update versus P2's four:
about25% more interaction work, not a measured wall-time increase. It would need
three actual endpoint/necessary-bound/BC passes, three readonly HG additions and
one material/J/position/pressure-history commit. Full first/second observations
would add qualification costs; an optimized pressure-only operator is not assumed.
Saved native PorePressRate would then describe the third evaluation at actual p2,
not R(p3), a converged residual or dp/dt.

P2's near-miss early top budget motivates this low-cost algebraic screening, not
automatic acceptance. Only after root review of the new finite10us evidence could
a distinct bounded P3 source/implementation/physical trial be considered. It would
retain all original pressure, stress, top/bottom settlement, ID/22-array, ledger,
drainage, geometry, five-phase signed and HG gates. No new half/reference chain or
full2Tv calculation follows from the mathematical script.

## Unique algebra execution and products

The entry accepts only `--execution-authorized`; absent authorization, or an
existing output/check path, rejects. Inputs are stat-bound before work and checked
afterward, including the old passed receipt/cases/script/notes and original
mode/parameter evidence. No SHA scans are used. All writes are exclusive and a
failure preserves a new failed receipt/partial outputs, without rerunning old work.

New `outputs/upl_tpi_p3_time_options_r1` would contain:

- `cases.csv`: every old1116 row plus new372 P3 rows, evidence origin explicit;
- `comparison.csv`: 372 mode/step rows with P1/P2/P3/converged radii and lag factors;
- `new_P3_roots.csv`: only the1488 genuinely new P3 roots.

`logs/upl_tpi_p3_time_options_r1.check.json` would retain all step reports,
old20us failures, inputs and product stats. `passed` would mean only that the
arithmetic and retained-evidence checks completed, never physical acceptance.

# Paper time layers, current P1, and one three-force midpoint design

2026-11-17. Author preparation only. New files are this note and
`support/upl_tpi_paper_time_layers_r1.py`; neither is a physical implementation.
No original component, SPH solve, native reader, build, Git or hash is run by the author.
All old sources, solver results, failures, current pressure coefficients and budgets remain unchanged.
Root must read these assets and independently authorize any new algebra execution.

## 1. What the paper specifies, and what it does not

Source: `src/papers/u-pw/Lian 2023 u-pl.md`, Section3.3–3.4, Eqs27 and30–39;
original `src/papers/PDF/Lian 2023 u-pl.pdf`, Fig1 on printed page10, visually
checked using the existing root-derived `outputs/upl_tpi_paper_timing_r1/Lian2023_page10.png`.
Eq27 places pressure, effective stress, velocity and porosity at half levels,
with particle position at full levels. Fig1 orders neighbour search, porosity rate,
pressure, strain/material update, total stress/acceleration, then velocity/porosity/position.
This differs from the private current implementation's full mechanical corrector followed by endpoint pressure.

Using full position times `t_n=n*h`, Eq27's declared storage is:

| Quantity | Input of an LF step | Output |
|---|---|---|
| Position | `x^n` | `x^(n+1)` |
| Pressure | `p^(n-1/2)` and its previous half-level value | `p^(n+1/2)` |
| Effective stress, velocity, porosity | `sigma'^(n-1/2),v^(n-1/2),n^(n-1/2)` | corresponding `n+1/2` values |
| Rates in Eq27 | declared full-time rate at `t_n` | **not another committed state** |

To keep the TPI indexing separate from physical half levels, call a pressure-update index `k`.
Then `p^[k]=p^(n-1/2)`, `p^[k-1]=p^(n-3/2)`, and Eq39's alpha=.5 extrapolation
`p^[k]+.5*(p^[k]-p^[k-1])` approximates physical `p(t_n)`, not `p(t_(n+1/2))`.
Eq38 nevertheless labels its newly calculated pressure `p^[k+1]`.
Thus merely copying Eq39 into a full-step stored-pressure scheme does not reproduce the paper's LF storage.

Eq36's source contains velocity divergence, gravity/head, Taylor correction, and
`rho_w*div(k*a)`. The text following Eq37 treats the right-hand quantities as known.
Fig1 computes the new acceleration **after** the pressure calculation. Therefore its source cannot be
silently interpreted as the already solved new acceleration containing that same unknown pressure.
The paper does not give a component-level pseudocode declaring whether this source acceleration is
stored old acceleration, a full-time predictor, or a separately evaluated force; nor does it specify
how half-level velocities/stresses are centred to obtain every full-time rate in Eq27.
These are real closure choices, not permission to omit the acceleration term.

An LF implementation must explicitly state both `a_source` used in Eq36 and `a_kick` used to update velocity,
their physical times, how each pressure contribution is formed, and when their histories are committed.
Even the paper's alpha=1 statement must not be reinterpreted as proof that finite pressure extrapolation
is a converged global implicit solve. This design does **not** claim to reconstruct an exact literal LF algorithm.

## 2. The actual current private full-step schedule

Lineage: `support/upl_tpi_time_layers_r1.py::step` and its already reviewed note;
private GPU hooks in `upl_tpi_gpu_r1_prepare.py` and its descendants.
All stored `p_n,p_(n-1),sigma_n,v_n,J_n,n_n,x_n` are full-step quantities in the current scheme.
The current four-state P1 mode has `y=(sigma',v)` and `iq=i*q`:

```
a_n = iq*(sigma_n-p_n)/rho
v_h = v_n + h*a_n/2
sigma_h = sigma_n + h*M*iq*v_n/2
g_h = p_n + .5*(p_n-p_(n-1))
a_h = iq*(sigma_h-g_h)/rho
sigma_1 = sigma_n + h*M*iq*v_h
v_1 = v_n + h*a_h
p_1 = Jrow(y_1,g_h)                    # endpoint force/row, after mechanics
history <- p_n once after success
```

The actual displacement corrector is `x_1=x_n+h*(v_n+v_1)/2`, not `x_n+h*v_h`.
This is read directly from `JSphGpuSimple_ker.cu::KerComputeStepSymplecticCor`;
the same rule is present at line872 of the actual flat frozen
`outputs/upl_tpi_m0_dt_GPU_r2_source/JSphGpuSimple_ker.cu`.
the new algebra includes an independent passive fifth position state using that rule.
Its difference from stress-inferred displacement is exactly
`(sigma_1-sigma_n)/(M*iq)-(x_1-x_n)=h^2*(a_n-a_h)/2` in this homogeneous mode.
For smooth acceleration this is O(h^3) locally; at startup it is not a universal zero identity.

The current row is the **original full R** evaluated at one known pressure guess,
preconditioned by the leading-LP diagonal S. S is not the complete pressure Jacobian.
Taylor/Neumann terms and pressure-dependent acceleration remain inside R.
The third endpoint force is read-only for already committed solid/J/material/HG history;
it changes the pressure solution but does not retroactively feed the mechanical corrector.
This is a first-order Symplectic-compatible endpoint defect correction, not paper LF.

## 3. Independent homogeneous Fourier reduction

Keep the same constant k, original pressure/force operators, and beta=0. Define

```
r = rho_w/rho,  dr=rho-rho_w>0,  delta=(1-r)*(1-mu),  m=1-delta
P = [-r/(1-r), -gamma*iq/(k*q^2*(1-r))]
L = [[0, M*iq], [iq/dr, -gamma/(k*dr)]]
p_star = P*y,  y_dot=L*y
S = k*q^2/(1-mu)
Jrow(y,g) = delta*P*y + m*g
```

The density shift from mu to m retains the complete acceleration feedback in this fixed-mode model.
It must not be dropped or replaced by a fluid-capacity multiplier. Actual SPH has noncommuting pressure,
Taylor, divergence and force operators and boundary rows; one common Fourier symbol is a diagnostic idealization.

On a smooth stable slow manifold, the current method has

```
p_n = P*y_n + h*z1*y_n + O(h^2)
z1_current = -m*(1-alpha)/(1-m) * P*L
L1_current = [alpha-.5-m*(1-alpha)/(1-m)] * b*(P*L)
b = [0,-iq/rho]^T
```

With alpha=.5 this leaves a generic O(h) pressure lag and a generic O(h) modified-generator error.
The already observed startup top bias is therefore a reason to audit time coupling;
it is not by itself proof that this formula is the only source of the observed physical error.

## 4. H3: a clearly defined three-force midpoint/reflection candidate

This is a new mathematical design, **not** a claim that Eq38 is literally evaluated at its paper LF time levels.
Freeze alpha=.5; no alpha tuning, pressure clipping, relaxation beta, damping, HG or spatial modification.

1. Force0 at the old full state `(x_n,y_n,p_n)` forms the original predictor once.
2. At the actual predicted half state `(x_h,y_h,J_h,n_h)`, install `g_h=p_n+.5*(p_n-p_(n-1))`.
   Force1 computes the same full M0 residual `R_h(g_h)`, including **known** `a_h(g_h)` and the original S.
   Form scratch `p_h*=g_h+R_h/S`. This does not use an already solved `a_h(p_h*)` inside the first pressure row.
3. Force2 at the **same** half geometry/material/velocity/J and corrected `p_h*` computes the acceleration
   for the original mechanical corrector. This is a pressure/force feedback pass, not a second material/J update.
4. Commit the original full solid corrector once, using Force2 rates; define full pressure
   `p_1=2*p_h*-p_n`; apply the original genuine endpoint pressure boundary, then commit history once.

The reflected endpoint is an extrapolated endpoint pressure, **not** a pressure obtained from a full endpoint residual.
Without a new pressure-force decomposition/cached linear update, simultaneously demanding an independently
solved half pressure, a force using it, and an independent endpoint residual requires four distinct force states
`old / half-guess / half-corrected / endpoint`. A simple three-call reorder cannot preserve all those meanings.
Saving `p_h*` under the old `p_1` label would also mis-time the history and is rejected as a design.

For H3's four-state map:

```
p_h* = delta*P*y_h + m*((1+alpha)*p_n-alpha*p_(n-1))
p_1  = 2*p_h*-p_n
```

At h=0 the two history roots satisfy
`z^2-[2*m*(1+alpha)-1]*z+2*m*alpha=0`.
For alpha=.5 this is `z^2-(3*m-1)*z+m=0`; real strict Schur stability requires `0<m<1`.
This is stricter on negative m than the current alpha=.5 block's `-.5<m<1`.
At m=1 the double unit branch is not a convergence proof. Actual complex/nonnormal SPH rows and finite h
need separate evidence; this real scalar condition is not a new hard SPH timestep gate.
H3 also changes the damping and phase of the history roots: for a complex-conjugate pair their modulus is
`sqrt(m)`, whereas the current pair has modulus `sqrt(m/2)`. Thus reduced slow-manifold lag can coexist
with a more persistent oscillatory startup history. All roots must be retained; no startup improvement is presumed.

The smooth-manifold expansion now gives

```
z1_H3 = m*(alpha-.5)/(1-m) * P*L
L1_H3 = b*z1_H3
```

Thus alpha=.5 eliminates the **homogeneous autonomous** leading pressure lag, rather than merely halving it.
In general fixed spatial linear algebra, `Jrow(y,g)=C*y+J*g` and `C=(I-J)*P`; the same calculation yields
`z1_H3=(I-J)^(-1)*J*(alpha-.5)*P*L` when this inverse and a stable slow manifold exist.
This argument does not require S to be a full Jacobian, but requires a well-defined fixed point and stable history block.
It supports a possible second-order smooth autonomous limit, **not** an overall second-order SPH or startup claim.

## 5. The existing load clock prevents an automatic second-order forcing claim

The actual three current force evaluations retain the source clock `TimeStep=t_n`, including the endpoint pass.
Reusing this policy at H3's half geometry does not create midpoint forcing.
For a local linear source acceleration `f(t)`, write the fixed point and reduced dynamics as

```
p_star(y,t)=P*y+D*f(t)
D=rho_w*iq/[q^2*(1-r)]
y_dot=L*y+[b*D+e_v]*f(t),  e_v=[0,1]^T
```

This is a fixed-coefficient source-mode diagnostic, not an exact representation of the finite kernel-band load.
Suppose the two half-state forces evaluate `f(t_n+zeta*h)` while the predictor still uses `f(t_n)`.
For alpha=.5 the established pressure slow manifold has

```
p_n-p_star(y_n,t_n) = h*(zeta-.5)*D*f_dot + O(h^2)
```

For retained source time zeta=0, the leading forced pressure lag is therefore `-h*D*f_dot/2`.
The mechanical midpoint also misses `h^2*[b*D+e_v]*f_dot/2` locally, so its forced global limit is generally first order.
With exact input history, the **first** new H3 step instead has endpoint mismatch
`(1-m)*(2*zeta-1)*h*D*f_dot+O(h^2)`; this initial local coefficient is not the established-history lag.
Only a separately declared numerical source-time change to zeta=.5 cancels these first forcing defects in this model.
That would retain the same physical ramp duration and q(t), but evaluate it at the correct stage time;
it is not implemented or silently included here. At ramp corners, a drainage switch, wave startup or changing band support,
these smooth expansions do not establish accuracy. The pressure first computation in Fig1 does not remove this caveat.

## 6. Boundary and lifecycle conditions before any implementation

- At first opening, `p_n` can be nonzero while the true drained `p_h*=0`.
  Unrestricted reflection would make `p_1=-p_n`. Preserve the **actual** endpoint Dirichlet rule and write positive0;
  do not clip all negative pressures or alter the physical drain/ramp time to hide this transition.
- Preserve the fixed-grid completed-step policy: the event sample is pre-open; true drained receivers open only
  on the following admitted source-clock step. Stage metadata and every actual receiver check must state the layer used.
  A half-stage wall/pressure rule cannot simply be inferred from an endpoint mask after geometry changes.
- Ordinary nondrained negative pressure is not Dirichlet and must not be zeroed by the reflection adapter.
- Force1 is a pressure-source observation; Force2 is a force feedback at the same half state.
  They may add force/cache calls, but only one predictor and one corrector material/J/HG-history commit are permitted.
  A future implementation must define its new actual counters before running; old two-physical-force/HG identities
  cannot be copied or faked. HG force/read-only evaluation at the identical half history needs explicit lifecycle review.
- Store `p_n` and history until full success; do not overwrite either before reflection/BC checks.
  A failed stage must not advance the pressure history. Existing sort/owner/periodic role/positive-zero/FTZ contracts remain.
- The fifth position map retains the original trapezoidal full-velocity corrector; no alternate advection is implied.
  Porosity, density, stress and material history are not updated by a pressure residual or repeated force pass.

## 7. Why not immediately replace the entire integrator by an alleged literal LF

A new LF prototype would have to specify half-level sigma/v/n/p initialization, full-time rates, Eq36 acceleration,
boundary source times, one constitutive/J/porosity update, HG history time, output semantics and restart storage.
Predicting full-time values from old half values and a previous rate is one possible closure, but Fig1/Eq27 do not
prove it is the paper's closure. Computing a new pressure first and then treating its new acceleration as already known
in its own Eq36 is circular unless an actual coupled solve is declared. Choosing an old acceleration instead is explicit
and must be assessed for its own time lag. No such undisclosed full-LF prototype is selected by this note.

Recommended low-cost order: finish the retained small-dt B two-second control review; then have root independently
review the new autonomous and forced algebra. If evidence warrants H3, write its complete stage/BC/HG/source-clock
contract before a small private implementation. Do not start a new full run or retrofit the formal source merely
because an autonomous coefficient vanishes. The existing top noninferiority budgets remain unchanged.

## 8. The small author component and its limits

The component directly copies P1's generic current four-state formula, substitutes the original case02 XML constants,
and compares the new H3 formula. It does not import or run an old component, invoke force code, integrate an SPH state,
or solve a new spatial/reference problem. The nominal examples use q=pi/2 or pi/dp and mu=.2/.8; these are declared
algebraic fixtures, not measured SPH modes. Eight h0/fast-block identities,32 new4x4 maps/128 roots and the passive
5x5 position consistency are checked at h=1e-8..8e-8 solely to expose the asymptotic limit.
Generator errors/orders and nominal spectral radii are observations, not accuracy/stability admission criteria.
Eight affine-ramp first-jet identities distinguish exact-history local error from established slow-manifold lag.
No physical ramp amplitude is fitted and no reference trajectory is generated.

After root full read only:
`D:/anaconda3/python.exe -X utf8 -B tests/support/upl_tpi_paper_time_layers_r1.py --execution-authorized`.
Exclusive products would be four small CSVs in `tests/outputs/upl_tpi_paper_time_layers_r1` and one log check.
Existing/partial products refuse overwrite. Source/reference stat checks are local necessary bindings, not SHA scans.
`passed` means algebra/coverage/arithmetic completed only; the receipt always denies actual SPH spectrum,
timestep, paper-literal, boundary/HG, physical or public-source acceptance. No automatic next work is run.

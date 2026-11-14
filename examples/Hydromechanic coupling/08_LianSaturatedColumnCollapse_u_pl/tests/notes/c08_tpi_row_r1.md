# TPI pressure row: standalone algebra only

2026-11-14, author-only. New support/c08_tpi_row_r1.py and this note; no author import/execution, build, solver, force, native read, VTK, Git or SHA action. Root must fully read and separately admit one algebra-only execution. Outputs are exclusive outputs/c08_tpi_row_r1/{rows,invalid,scalar_modes,histories}.csv and logs/c08_tpi_row_r1.check.json. Failed/partial outputs are preserved and cannot be overwritten or retried automatically.

## Row and units

This small function implements only the scalar algebra of Lian2023 Eqs38/39/47, as visually reviewed by root in the original PDF printed pp7-11. No spatial Aij, Bi or Ei is assembled. It is not a production TPI implementation, a change to the finite-Kw integrator, or a server package.

Inputs are S=sum(Aij) in 1/(m s), neighbor_sum=sum(Aij*p_tilde_j) and B in Pa/(m s), p_n/p_nm1 in Pa, alpha in [0,1], beta_capacity_m_inv in 1/m, and dt in seconds. The self history is p_tilde_i=p_n+alpha*(p_n-p_nm1). The ordinary row is p_new=(B+neighbor_sum)/S. Only when plastic_eligible AND negative_branch_enabled AND old p_n<0 is the branch selected:

```
c = beta_capacity_m_inv / dt
p_new = (B + neighbor_sum + c*p_tilde_i) / (S+c)
p_new-p_tilde_i = (B+neighbor_sum-S*p_tilde_i)/(S+c)
```

Exactly zero old pressure uses the ordinary branch, an explicit deterministic choice where the displayed paper omits equality. The branch does not inspect p_new or p-fixedP0; no pressure is clipped. The residual is reduced relative to p_tilde_i, not necessarily relative to p_n: extrapolated negative history may retain a negative slope, so this row cannot guarantee that absolute suction decreases. Plastic eligibility is an explicit input to this algebra component, not an implemented material-policy decision. A positive beta with active branch that underflows to c=0 is explicitly rejected. Nonfinite inputs/intermediates/results, nonpositive S/dt, out-of-range alpha, negative beta and non-bool controls are rejected; no denominator repair or clamp is supplied.

The .04 m^-1 value appears only in a clearly unit-labelled paper-row example. It is not selected for actual C08 and is not a dimensionless multiplier on current R. Scaling the complete row by lambda requires scaling S, neighbor_sum, B AND beta by lambda; otherwise the negative row changes. Neither this row nor beta may be copied into the current finite-storage equation without a separate derivation. The current spatial correction, variable-k law, source acceleration and boundary treatment remain outside this function.

## Declared tests

Valid cases cover positive/negative/zero constant fixed points; alpha0/.5/1 with explicit external neighbor histories; the negative residual identity; old-negative/new-positive behavior; ordinary nonnegative and zero branches; disabled plastic/control and beta0 branches; complete-row scaling; and a counterexample that deliberately omits beta rescaling. Binary64 row outputs are independently checked using a 90-digit Decimal rational evaluation of exact binary64 inputs. Its reference expresses the history as (1+alpha)*pn-alpha*pm, rather than reusing the float function's intermediates. The fixed forward arithmetic allowance is gamma32 times a stated operand/diagonal condition scale, plus a subnormal allowance. It is an arithmetic test envelope, not a physical tolerance.

Invalid configurations must raise ValueError and are recorded separately. They include bad S/dt/alpha/beta, nonfinite states/sums, non-bool controls, numeric bools and explicit capacity overflow/underflow. No invalid configuration is silently converted to a valid one.

The frozen homogeneous neighbor-row illustration uses

```
u_next = mu*((1+alpha)*u_current-alpha*u_previous)
z^2-(1+alpha)*mu*z+alpha*mu = 0
```

For real mu and 0<=alpha<=1, strict Schur stability is -1/(1+2alpha)<mu<1. The component compares this domain with Jury inequalities and the actual two roots at predeclared values, retaining marginal and unstable cases. Two finite 25-update scalar histories illustrate alpha=.5/mu=-.75 growth and alpha=1/mu=1 exact linear drift. Decimal histories and propagated arithmetic bounds are independent of any solver clock. Their indices are dimensionless recurrence indices, not physical timesteps or a new particle calculation. Alpha1 is not an actual implicit solve; the scalar real-mu domain is not a complete coupled or nonnormal/complex-spectrum stability proof.

## Exclusions

No native IDs, PRE, pressure history buffers, predictor/corrector, sorting, material return, boundary, XML/BAT or existing numerical thresholds are modified. The two-time-level history and branch controls in the function do not implement those missing interfaces. Passing this algebra test cannot admit a physical window, formal case or other psi group. Root's separate spatial/time-layer design and implementation review remain required.

Root-only command after review: python -B tests/support/c08_tpi_row_r1.py --execution-authorized. The script contains no subprocess invocation or calls to other project tools.

# Strict Cryer Reference Notes

The paper reference is the center pressure in a drained poroelastic sphere under
all-around traction:

```text
p_w(0,t) / p0 =
  eta * sum_j [ (sin(xi_j)-xi_j)
  / (eta*xi_j*cos(xi_j)/2 + (eta-1)*sin(xi_j)) ]
  * exp(-xi_j^2*T_v)
```

with:

```text
(1 - eta*xi_j^2/2)*tan(xi_j) = xi_j
eta = (1 - nu)/(1 - 2*nu)
T_v = c_v*t/a^2
```

Before strict comparison:

- implement an independent reference script;
- check root convergence;
- digitize/check Figure 7B or another trusted reference;
- confirm the `c_v` mapping to the current material constants;
- generate curves for `nu=0.1`, `0.2`, `0.3`, `0.45`.

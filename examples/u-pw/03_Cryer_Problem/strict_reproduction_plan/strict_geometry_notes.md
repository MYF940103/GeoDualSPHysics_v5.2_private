# Strict Cryer Geometry Notes

Preferred first strict route: true 3D sphere.

Draft choices:

- center: `(0,0,0)`;
- tentative radius: `a=0.05 m` if no paper-specific value is found;
- tentative coarse spacing: `dp=a/10` to `a/12`;
- material marker: sphere interior;
- boundary marker: exterior spherical shell, not yet implemented;
- center extraction radius: start with `max(1.5 dp, 0.05 a)`.

Axisymmetric or 2D surrogate setups are allowed only as reduced diagnostics.
They should not be called strict Figure 7 reproduction unless a matching
reference solution is supplied.

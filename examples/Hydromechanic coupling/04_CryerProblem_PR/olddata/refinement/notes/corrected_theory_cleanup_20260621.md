# Cryer corrected-theory cleanup note (2026-06-21)

## Why the previous ramp sweep is superseded

The previous ramp-time sweep was postprocessed with an incorrect Cryer analytical
series. The theoretical solution has been corrected to match the u-pw reference
paper Equations (46)-(47):

- root equation: `(1 - eta*xi^2/2) tan(xi) = xi`;
- center pressure denominator:
  `eta*xi*cos(xi)/2 + (eta - 1)*sin(xi)`;
- Figure 7B-style axes: logarithmic `T_v` and normalized center pore pressure
  `p^w/p0`.

With the corrected theory and `nu=0.3`, the Mandel-Cryer peak is about
`1.24-1.25 p0`, not the lower value used in the previous sweep. Therefore, the
old conclusion that `RampTime=0.0115 s` closely matched the peak is invalid.

## Preserved conclusions

- `RampTime=0.0115 s` still reduces maximum particle velocity compared with
  `RampTime=0.010 s`.
- Neither `RampTime=0.010 s` nor `RampTime=0.0115 s` reaches the corrected
  theoretical peak.
- The next sweep should use the corrected theory and should focus only on the
  early window up to about `T_v=0.1` before investing in full-cycle runs.
- Both drainage-from-start and delayed-drainage strategies must be rechecked
  under the corrected theory.

## Cleanup scope

The old heavy `out` folders from the previous complete runs can be removed after
this note and the corrected summaries are preserved:

- `refinement/r010_drain0_full_20260620/out`
- `refinement/ramp_refine_20260620/r0115_drain0_full/out`

The old non-corrected theory figures should not be used for future decisions.

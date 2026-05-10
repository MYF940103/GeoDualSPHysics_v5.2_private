# Notes: Cryer Problem

Missing before strict reproduction:

- 3D spherical or axisymmetric geometry.
- Drained pore pressure boundary around the specimen.
- Pore-pressure ghost / MLS boundary treatment.
- Corrected-gradient PR operators for better boundary consistency.
- Analytical solution and center-pressure postprocessing.
- Likely GPU support for useful resolution.

Minimum first smoke test: coarse CPU Debug run with pressure output, symmetry check, no NaN, excluded=0.

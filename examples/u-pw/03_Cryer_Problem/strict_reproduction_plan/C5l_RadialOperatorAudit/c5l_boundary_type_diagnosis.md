# C5l Boundary Type Diagnosis

C5l separates boundary flux strength from radial operator consistency. The
static manufactured-field audit shows that the material-material
`LapPorePress` operator is consistent in the interior but has a large
near-boundary bias for curved radial fields. The pressure-only shell audit
then shows that matching a global or boundary flux ratio is not sufficient
when shell-to-shell redistribution is wrong.

## Classification

- Mode 4 normalized remains an over-strong, nonuniform Robin-like boundary.
- Mode 5 is an over-strong shell-flux boundary with poor radial profile consistency.
- Mode 6 is a radial FV boundary sink with inconsistent shell redistribution; it is not a validated true Dirichlet operator.

## Main Diagnosis

The current strict route is best described as an inconsistent near-boundary
radial Laplacian / shell-exchange problem. The boundary flux at `R` is only one
part of the failure. Surface-shell pressure remains high because the outer
shell, adjacent shell, and interior storage exchange do not reproduce the
finite-volume radial diffusion balance.

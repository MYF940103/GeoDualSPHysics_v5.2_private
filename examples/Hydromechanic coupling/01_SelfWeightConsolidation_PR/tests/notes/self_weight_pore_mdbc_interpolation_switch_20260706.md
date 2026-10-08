# Self-Weight Pore mDBC Interpolation Switch

Date: 2026-07-06

## Change

Added `PoreMdbcInterpolationMode` under `<special><hydromechanics>`:

- `0`: zero-order mDBC boundary pore-pressure interpolation. This is the default and preserves existing hydromechanics cases.
- `1`: MLS direct mDBC boundary pore-pressure interpolation. Boundary `PorePress` then participates directly in the Darcy term.

The mDBC moment matrix is reused for stress and pore-pressure extrapolation when MLS mode is enabled, avoiding a separate pore-pressure matrix build.

## Rationale

Self-weight consolidation tests showed that MLS recovers imposed linear boundary pore-pressure fields much better than zero-order interpolation, but did not improve the full consolidation accuracy and increased runtime. The explicit XML switch keeps the stable zero-order behavior as the default while preserving MLS direct interpolation as a controlled test option.

## Implementation Notes

- CPU and GPU implementations are synchronized.
- `PoreMdbcInterpolationMode=0` uses the previous zero-order fallback path.
- `PoreMdbcInterpolationMode=1` uses MLS direct reconstruction of excess pore pressure and falls back to zero-order interpolation when the matrix determinant is too small.
- Pairwise head-Neumann diagnostic code is not retained as the default production path.

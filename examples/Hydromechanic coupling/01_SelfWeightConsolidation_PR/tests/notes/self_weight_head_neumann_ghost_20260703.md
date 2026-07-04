# Self-weight Scenario 2 head-Neumann ghost test

Date: 2026-07-03

## Superseded source change

An intermediate source change tried to replace the boundary pore pressure in each seepage pair with:

`p_w,ghost = p_w,i + rho_w * g_h * (z_i - z_b)`

so that

`p_w,i - p_w,ghost + rho_w * g_h * (z_i - z_b) = 0`

for each fluid-boundary pair.

This was not kept. The existing mDBC pore-pressure correction already constructs boundary pore pressure as:

`PorePress_b = PorePress0_b + extrapolated(PorePress_f - PorePress0_f)`

When `PorePress0` is the hydrostatic reference, that boundary value is already the more consistent hydraulic-head ghost. Therefore the current source direction is:

- keep boundary neighbors in the `khyd > 0` seepage branch;
- use the already-corrected boundary `PorePress[p2]`;
- do not exclude boundary seepage pairs;
- do not replace the boundary value with the pair-local `p_w,i + rho_w*g_h*dz` formula.

Modified source files:

- `source/JSphCpu.cpp`
- `source/JSphGpu_ker.cu`

## Invalid short-window attempt removed

A first `Tv=1.20-1.23` head-Neumann short-window run was removed because it inherited from:

`support/diagnostics/legacy_stage2_out_before_scenario2_rename/data/Part_0240`

That legacy restart is not the retained current two-stage reference state. Its initial bottom excess pore pressure was already about `5.17 kPa`, so it could not be compared with the current baseline platform-window notes.

## Valid next test direction

The retained complete reference output currently contains restart data through `Part_0211`, so there is no retained valid `Tv=1.20` binary restart state for a late-platform short-window replay. A true platform comparison requires a continuous long run or a newly retained late restart state. Before running, the boundary-condition interpretation should be rechecked against the u-pw references and current code paths.

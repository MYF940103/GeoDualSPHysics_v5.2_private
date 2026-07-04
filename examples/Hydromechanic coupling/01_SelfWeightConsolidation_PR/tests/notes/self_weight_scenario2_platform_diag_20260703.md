# Self-weight Scenario 2 late-time platform diagnostic

Date: 2026-07-03

## Scope

Case:
`examples/Hydromechanic coupling/01_SelfWeightConsolidation_PR`

Issue:
In the formal two-stage Scenario 2 run, the bottom excess pore pressure follows Terzaghi theory well through the early and middle period, but after about `Tv > 1.1-1.2` it enters a clear late-time plateau. At `Tv=2`, the SPH bottom excess pore pressure remains about `0.55 kPa`, while the theoretical value is about `0.063 kPa`.

## Temporary diagnostic

A temporary CPU-only diagnostic was inserted into the merged pore-pressure-rate path in `source/JSphCpu.cpp`. It was enabled only through the environment variable `DSPH_PORE_DIAG_CSV` and was removed after the test.

The diagnostic split the bottom-zone pore-pressure-rate equation into:

- `rate_comp = Kw/n * (-divv)`
- `rate_seep = Kw/n * (2*k*lapw/(rho_w*g) + 2*k*lapz)`
- `rate_total = rate_comp + rate_seep`

It also separated `fluid`-neighbor and `bound`-neighbor contributions.

Outputs retained:

- `tests/outputs/CaseSWDiagPoreRate_Tv120_124_CPU_pore_rate_diag.csv`
- `tests/outputs/CaseSWDiagPoreRate_Tv120_124_CPU_pore_rate_diag_combined.csv`
- `tests/outputs/CaseSWDiagPoreRate_Tv120_bottom005_CPU_pore_rate_diag.csv`
- `tests/outputs/CaseSWDiagPoreRate_Tv120_bottom005_CPU_pore_rate_diag_combined.csv`

## Main finding

The late-time platform is caused by a near cancellation between the compression source term and seepage dissipation term in the lower column. The net pore-pressure rate becomes very small even though the individual terms are large.

For the bottom band `z <= 0.15 m`, restarted from `Part_0240` (`Tv ~= 1.20`), the typical averaged values were:

- total compression source: about `+6.5e4 Pa/s`
- total seepage term: about `-6.5e4 Pa/s`
- net pore-pressure rate: only about `-10` to `-70 Pa/s`

For the near-bottom band `z <= 0.05 m`, the same behavior is stronger:

- total compression source: about `+6.6e4 Pa/s`
- total seepage term: about `-6.6e4 Pa/s`
- net pore-pressure rate: only tens of `Pa/s`

This explains why the bottom excess pore pressure decreases extremely slowly after `Tv ~= 1.2`.

## Boundary-neighbor evidence

The `fluid` and `bound` neighbor contributions are nearly opposite in the near-bottom band:

For `z <= 0.05 m`, window-average:

- fluid contribution:
  - `rate_comp ~= +5.41e4 Pa/s`
  - `rate_seep ~= -9.80e4 Pa/s`
  - `rate_total ~= -4.39e4 Pa/s`
- bound contribution:
  - `rate_comp ~= +1.21e4 Pa/s`
  - `rate_seep ~= +3.17e4 Pa/s`
  - `rate_total ~= +4.39e4 Pa/s`

The bound-neighbor contribution almost cancels the fluid-neighbor drainage contribution. Therefore the late-time platform is not a global permeability/time-scale error. It is a bottom mDBC support/boundary-neighbor contribution problem that becomes dominant when the analytical excess pressure is small.

## Large cancellation inside seepage

The seepage term itself contains a large cancellation between the pressure-gradient part and the gravity-head part:

For `z <= 0.05 m`, window-average:

- fluid neighbors:
  - `lapw` contribution: about `-7.43e6 Pa/s`
  - `lapz` contribution: about `+7.34e6 Pa/s`
  - net seepage: about `-9.80e4 Pa/s`
- bound neighbors:
  - `lapw` contribution: about `+7.37e6 Pa/s`
  - `lapz` contribution: about `-7.34e6 Pa/s`
  - net seepage: about `+3.17e4 Pa/s`

This means the bottom boundary is enforcing an almost hydrostatic local balance, but its residual is large enough to cancel late-time drainage.

## Conclusion

The late-time plateau is best explained by bottom mDBC boundary-support behavior in the u-pw pore-pressure-rate loop:

1. The lower-column pressure-gradient and gravity-head terms are individually very large and nearly cancel.
2. Boundary-neighbor seepage and compression contributions then cancel the fluid-neighbor drainage contribution.
3. The remaining net pore-pressure rate becomes tiny, so bottom excess pore pressure appears to stop dissipating.

This is not primarily caused by:

- Shepard regularization, which was disabled in the formal run.
- `CteB/Cs0`, which does not control the u-pw pore-pressure-rate terms and was previously shown to have negligible effect.
- A wrong global hydraulic conductivity or time factor, because the early and mid-time curves agree well with theory.
- Top drainage failure, since the top residual stays near zero.

## Suggested next code direction

The most targeted fix is to revisit how boundary particles enter the u-pw seepage operator near an impermeable mDBC bottom:

- Check whether bound-neighbor `lapw` and `lapz` should be included symmetrically in the same way as fluid neighbors for the pore-pressure-rate diffusion term.
- Consider a boundary-consistent zero-normal-flow treatment for pore pressure at impermeable mDBC boundaries, instead of letting extrapolated boundary pore pressure contribute as ordinary neighbor pressure.
- Keep the current top free-surface drainage treatment unchanged; the diagnosed issue is bottom-side support behavior.

## Boundary-seepage isolation test

A targeted source test was then run with the following pore-pressure-rate rule:

- keep the compression/volumetric term from both fluid and boundary neighbors;
- keep the existing `khyd > 0` and gravity-head switch logic;
- exclude boundary neighbors only from the Darcy seepage operator (`lapw/lapz` terms).

This preserves the original no-gravity safeguard because the seepage branch still requires hydraulic conductivity and only uses the gravity-head correction when gravity is nonzero.

Short CPU diagnostic from `Part_0240`, near-bottom band `z <= 0.05 m`, showed:

- boundary-neighbor seepage became exactly zero;
- boundary-neighbor compression remained active;
- the net bottom pore-pressure rate increased from almost zero (`~-20 Pa/s`) to mostly `~-60` to `~-770 Pa/s` after the initial restart transient.

A GPU late-window restart test was then run:

- case: `tests/outputs/CaseSWScenario2_Tv120_130_Noflux_GPU_out`
- restart: formal Scenario 2 `Part_0240` (`Tv ~= 1.20`)
- duration: `0.10 s`
- figure/data:
  - `tests/figures/CaseSWScenario2_Tv120_130_Noflux_GPU/bottom_excess_compare.csv`
  - `tests/figures/CaseSWScenario2_Tv120_130_Noflux_GPU/bottom_excess_late_window_compare.png`

Result:

- old formal GPU output over the same window stayed on the platform: bottom excess pore pressure changed from `0.5743 kPa` to about `0.5723 kPa`;
- corrected GPU restart decreased from `0.5743 kPa` to `0.5422 kPa`;
- Terzaghi theory over the same `Tv` window decreased from `0.4510 kPa` to `0.4215 kPa`.

The corrected run therefore recovers the correct late-time dissipation slope, while retaining the existing `khyd` and no-gravity branch logic. The remaining offset from theory is inherited from the restart state; the local slope is the important diagnostic here.

Interim conclusion after the short window: the late-time platform is strongly linked to how impermeable mDBC boundary neighbors enter the u-pw pore-pressure-rate Darcy terms. Excluding boundary neighbors from `lapw/lapz` while retaining their contribution to the volumetric compression term was a useful isolation test, but it still required a full-history validation.

## Formal 2Tv validation of the boundary-seepage exclusion

The root release GPU two-stage Scenario 2 was rerun to `Tv = 2.0` using the boundary-seepage exclusion rule.

Run evidence:

- case root: `01_SelfWeightConsolidation_PR`
- executable: `DualSPHysics5.2_GEO_win64.exe`
- restart: `CaseSelfWeightConsolidation_Stage1_out\data`, `PartBegin=60`
- `TimeMax = 7.2874285714 s` (`Tv = 2.0`)
- `TimeOut = 0.0182185714 s` (`Delta Tv = 0.005`)
- `HydraulicConductivity = 1e-3`
- `PoreShepardRegularization = Disabled`
- `Excluded particles = 0`
- `Finished execution (code=0)`

Formal result from `figures/self_weight_consolidation_targets.csv`:

- `Tv = 1.0`: SPH bottom excess `0.8213 kPa`, theory `0.7388 kPa`
- `Tv = 1.5`: SPH bottom excess `0.5242 kPa`, theory `0.2151 kPa`
- `Tv = 2.0`: SPH bottom excess `0.5118 kPa`, theory `0.0627 kPa`

The full-history run therefore still develops a late residual platform. From `Tv = 1.5` to `Tv = 2.0`, the SPH bottom excess decreases by only about `0.0124 kPa`, while Terzaghi theory decreases by about `0.1525 kPa`.

Additional VTK inspection at `Part_0400` showed:

- bottom fluid excess pore pressure is about `511.8 Pa`
- bottom mDBC boundary excess pore pressure is about `511.9 Pa`
- the boundary total pore pressure differs mainly by the hydrostatic head, so the boundary extrapolation itself is not being reset to zero

Updated conclusion: simply deleting boundary neighbors from the Darcy seepage accumulation is not a sufficient formal fix. It removes the most obvious erroneous boundary seepage contribution, but it also leaves a truncated one-sided operator near the impermeable bottom. The next candidate should keep mDBC boundary particles as kernel-support/ghost neighbors while enforcing a zero-normal-hydraulic-head-gradient value in the seepage pair contribution, instead of either (a) treating the extrapolated boundary value as an ordinary neighbor or (b) removing the boundary seepage contribution entirely.

## Boundary compression isolation follow-up

A more aggressive temporary isolation test then excluded boundary neighbors from all pore-pressure-rate terms while leaving momentum and mDBC otherwise unchanged. This was only a diagnostic test and was reverted from the source after measurement.

Case/data:

- config: `tests/configs/CaseSWScenario2_Tv120_130_NoBoundPoreRate_GPU_Def.xml`
- output: `tests/outputs/CaseSWScenario2_Tv120_130_NoBoundPoreRate_GPU_out`
- figure/data: `tests/figures/CaseSWScenario2_Tv120_130_NoBoundPoreRate_GPU/bottom_excess_compare.csv`

Late-window result from `Tv ~= 1.20`:

- formal boundary-seepage-exclusion full run over the same window: `0.5345 kPa -> 0.5318 kPa`
- no-boundary-pore-rate diagnostic: `0.5355 kPa -> 0.5227 kPa`
- Terzaghi theory over the same window: `0.4455 kPa -> 0.4240 kPa`

This confirms that the boundary-neighbor compression/divergence contribution is also involved in the late platform, but removing boundary particles entirely from pore-pressure rate is still not a complete or physically clean fix. The more defensible next direction is a proper impermeable mDBC pore-pressure ghost treatment: keep boundary particles in support, but construct their hydraulic head and normal velocity contributions so that the wall imposes zero normal flux and zero normal skeleton velocity consistently.

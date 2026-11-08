# Frozen velocity block: no AV pumping evidence in this direction

The component completed its unique 10 CPU force evaluations and zero time updates. Actual Popen and Win32 exits were zero. This review consumed only the four sealed CSVs and component JSON/call. No additional force, solver, reader, build or parameter window was run. The Shepard trajectory remains a failed trajectory.

|Actual tau (s)|eta|All5000 pressure gain (1/s)|Noncompression/compression norm|Kinetic directional power (W)|Noncompression storage rate (W)|Maximum rate-response ID|
|---:|---:|---:|---:|---:|---:|---:|
|0.500000000159|.001|42.27294|3.5854%|-2503.654|-5.214383|6087|
|0.500000000159|.0005|42.27308|3.5857%|-2503.301|-5.203890|6087|
|0.720000000229|.001|754.5501|.66382%|-1642.318|-30.39630|5304|
|0.720000000229|.0005|754.5622|.66608%|-1643.636|-30.61112|5304|

Along the actual velocity-scaling direction, the rate gain rises from about 42 to 754 1/s and is dominated by -Kw/n times delta-theta. The noncompression norm is only about 3.6% and 0.66% of the compression norm. Its pressure-storage contribution and the kinetic directional power are negative at both eta values. This does not support AV pumping in this measured direction. It does not justify disabling AV or opening an AV parameter scan. Maximum-response IDs 6087 and 5304 lie outside the original eight focus IDs.

|Part / tau|Selected81 rate derivative: relative L2 difference between eta values|Compression derivative: relative L2 difference|Maximum two-eta rate difference / sum of original arithmetic budgets|
|---|---:|---:|---:|
|49 / .50|2.053512%|2.067015%|10.78966|
|71 / .72|.092984%|.090245%|1.71114|

The original per-call five-term Sum has maximum budget fraction 0.00989819902. At a fixed eta, the actual rate derivative versus the differenced five-term Sum has maximum propagated-budget fraction 0.00930868943. Both satisfy the original arithmetic checks. Selected-receiver LP, pressure-defect = defect - FS-Ace, and chain-Gp central derivatives are exactly zero at both snapshots and both eta values; no new tolerance was used to erase them.

The two eta values do not demonstrate pointwise exact convergence. In particular, the selected rate derivative at tau .50 differs by about 2.05%. The two-eta difference also exceeds the summed original arithmetic budgets. Those budgets constrain rate versus shadow for each actual input, not the physical responses of two different float perturbation directions. This is not a new failure gate, and the discrepancy is not uniquely attributed to rounding or AV switching. The JSON retains actual directions, one-sided asymmetry, channel L2 differences and budget ratios.

Baseline-relative soil FS/C/AS changes are zero, and selected81 AV dot<0 shadow switches are zero. This does not cover every pair among all5000 particles or other velocity modes. All wall p/stress/J/C values were not independently checked as held. The global residual therefore remains a noncompression velocity response or AV-mediated candidate, not a strict AV-only attribution. Zero non-Ace terms support the selected local interpretation without proving its global counterpart.

Actual inputs are float((1 +/- eta) * v_saved). Gains use the actual float direction norm; powers use its central direction u and saved absolute pressure. The analysis does not assume u equals v_saved exactly. All5000 norms and powers come from the original directions.csv; this offline review did not reconstruct all5000 primary states. These are conditional directional power/storage rates, not a complete solid-fluid dissipation theorem. Stress/plastic return, J/position evolution, boundary work and the actual two-stage full Jacobian remain outside this block. Other velocity modes are not excluded; negative directional powers do not prove whole-system stability or physical accuracy.

This closes the present AV-direction investigation. Further work should return to the known pressure G/D mismatch and full coupled block, rather than add an AV scan. Other psi groups remain unadmitted.

Evidence: outputs/upl_c08_av_velocity_r1/{calls,rates,response,directions}.csv, logs/upl_c08_av_velocity_r1.check.json, and the actual run.call. The sealed result is logs/upl_c08_av_velocity_result_r1.review.json. Source CSV/JSON/call stats were rechecked unchanged. Only this new untracked note was replaced to repair its encoding; sealed artifacts were not modified.

# P2 small-table error-source identity r1

Author-only draft, not executed. New files are `tests/support/upl_tpi_p2_error_sources_r1.py` and this note. No existing script, input, budget, result or source is modified. No solver, reader, pressure trial, build, VTK, plot, queue, Git or SHA action is performed.

## Scope and direct reuse

The script imports `upl_tpi_p1_error_sources_r1` without calling its main. Its exact `companion`, `decompose`, typed-table parser, stat/admission methods and output helper are reused. No new stress/pressure/J identity or companion formula is substituted.

It consumes the already completed P2 window science history/profiles/targets/metrics/check and the retained causal history/targets/metrics/check. These are nine existing small inputs, plus the two new author files and original error-source script/note: thirteen distinct stat-bound inputs. No layers CSV is needed because the original scientific history already stores the same total/pressure/J integrals and the target profiles independently associate their pressure integral. No BI4, new native read, physical binary, ledger or large table is consumed.

Main series are A finite-Kw, original B10 P1 M0, and BP2 M0. Each uses four genuine own saved states, producing twelve identity rows:

- True pre-open: completed1600 for A and1000 for B10/P2; not a shifted time origin.
- The own actual saved state nearest0.15s, explicitly descriptive nearest selection only.
- The two original nearest actual states corresponding to legacy Tv=.005/.05, bound to the completed target/profile records.

Selected original A/B10 settlement and integral fields must remain identical to the original causal table. B10/P2 selected clocks and completed steps must be exactly equal. A keeps its own sampling times. All three original material-centre z coordinates must match.

## Unchanged diagnostic identity

The reused identity is:

`top_error = bottom_translation + (native_span - J_integral) + (J_integral - stress_pressure_integral) + total_stress_integral_bias + pressure_integral_bias + reference_trapezoid_residual`.

Total, pressure and J contributions are the actual saved history fields, not reconstructed strains chosen to fit settlement. Original material-centre trapezoidal weights are0.005m at the two ends and0.01m internally, spanning0.99m. The original H=1m,512-mode, q0, Mc, Cv and capacity constants are unchanged and must match the completed P2 metrics.

Positive pressure-integral bias means the simulated pressure integral is below its own companion, which adds compression in this small-strain diagnostic. The decomposition separates measurable residuals; it does not prove that a particular numerical term is the unique cause.

True pre-open uses the original ideal uniform undrained end-load companion: finite-Kw capacity for A and M0 for B10/P2. It is not a finite-ramp/inertial/current-J dynamic truth, and it does not use a truncated drained series at tau=0 to invent a closed boundary solution. The other selections retain the original drained companion at each actual own time.

All original arithmetic scales are retained:5e-12mm identity/association closure,2e-8Pa and2e-10mm target companion reproduction. These are arithmetic checks, not a relaxed or new physical budget.

## Comparisons and residual error

For each of the four selections the JSON retains complete component vectors for:

- P2 minus B10, at exactly shared actual clocks and the same original material IDs.
- Original B10 minus A and P2 minus A, each with its own actual clock and corresponding reference.
- B10 minus P2: the signed extra error removed by the second full pressure defect, with every component shown separately.

The optional fraction of positive original extra signed top error removed is only defined when original extra error is positive and remaining error lies between zero and that original value. Otherwise it is null; signed component differences are still recorded without a manufactured improvement percentage. These are descriptive decompositions, not a causal certificate or cross-method half/5Pa equivalence test.

The two complete original P2 target records are copied intact. Their A reference part/time/errors and pressure/top/bottom limits must match the old B10 target table. The original top limit remains `.001*S_infinity_continuum_surface_mm`. The report exposes the actual P2-minus-A absolute-error increment, remaining top margin and positive excess, while retaining the original science pass/fail flags. It never uses a reconstructed approximate error to replace the original budget decision.

The actual A/P2 target time gaps are reported explicitly. For scale only, the same unchanged analytic M0 companion is evaluated at the two actual times, and likewise the unchanged finite-Kw companion. The resulting reference-only top changes are not native velocities, interpolation, shifted data, fitted target time, measured-error corrections or budget allowances. In particular, a few-microsecond gap is never subtracted from the observed top-budget excess.

## Products and execution contract

A separately admitted execution would produce only:

- `tests/notes/upl_tpi_p2_error_sources_r1_result.md`: twelve identity rows and four compact component-comparison rows.
- `tests/logs/upl_tpi_p2_error_sources_r1.check.json`: all unrounded values, actual selections/clocks, original budgets, component vectors, reference-only gap scales and consumed stats.

No CSV, layers table or plot is generated or rewritten. Existing/partial products refuse overwrite. Entry is `D:/anaconda3/python.exe -B tests/support/upl_tpi_p2_error_sources_r1.py --admission PATH --execution-authorized`.

Admission requires `stage=upl_tpi_p2_error_sources_r1.admission`, `passed=true`, `small_tables_only=true`, and deduplicated actual path/bytes/mtime_ns inputs. The completed P2 science must already be analysis-complete and physically unaccepted; its pressure/bottom/100Pa/top decisions are preserved even when top fails. No new solver or native action is admitted by this arithmetic script.

`passed/analysis_complete` only mean that associations and the original arithmetic identity completed. `physical_acceptance=false`, `causal_mechanism_proven=false`, exact mass/energy/force closure false, and all original budget results unchanged remain explicit. The root reviews the resulting split before choosing any further numerical experiment.

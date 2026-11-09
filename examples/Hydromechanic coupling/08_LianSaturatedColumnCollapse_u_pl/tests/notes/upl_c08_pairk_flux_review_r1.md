# Pair-k frozen-rate interpretation (author only)

Only new `tests/support/upl_c08_pairk_flux_review_r1.py` and this note; names checked absent/untracked. No script import/execution, plot, force, solver, reader, VTK, build, raw payload read, input change or SHA scan by the author. The existing helper files/results remain immutable.

After root full-read, one explicit derived-only action is available:

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_pairk_flux_review_r1.py --execution-authorized
```

Consume only the passed `logs/upl_c08_pairk_flux_cpu_r1.check.json`, its actual call/completion and stat-bound `receivers.csv`96 rows, `manufactured.csv`576 rows and `calls.csv`3 rows. No BI4, typed22, PRE, trace or physical object is read again. Reuse the component's original arithmetic and identity checks rather than inventing physical thresholds. Check actual terminal Popen/Win32 exits0; inputs must keep the same stats before/after analysis. Fresh outputs/check only; preserve a first failure and any derived partials without rerunning the helper.

Outputs under `tests/figures/upl_c08_pairk_flux_review_r1_*`:

- `actual.csv`: every96 original selected response rows plus cohort, retaining exact source clock/ID/FS/halo information and all original current/pair terms. `actual_plot.png` has each of the3 states: all32 current-versus-pair rate points, four fixed material focus IDs' two total rates, and their current compression/LP/defect/divAce/chain plus candidate-minus-current. Rates are shown in kPa/s with no clipping/fitting; a small total can result from cancellation of much larger channels.
- `manufactured.csv`: RMS/maxabs/mean for all states, fields, storage and observed cohorts. For constant-k native fields the reference is pair-minus-current algebra, not zero physical RHS. For constant-null, affine hydraulic and nonconstant-potential fields, the reference is continuous zero with conditional analytic ghosts. Keep `FS0_halo_free`, `FS0_halo_near`, `FS23`, and `FS1_other` separate; empty cohorts are absent, not zero-filled or silently combined.
- `quantization.csv`: match each manufactured float32 row to the same state/ID/field float64 row. Separately report RMS/max/mean rate32-minus-rate64 and the original p/A storage-quantization maxima. This avoids attributing float storage error to a spatial improvement.
- `manufactured_plot.png`: current and pair zero-reference RMS separately for constant(C0), affine(A64/A32) and nonconstant-potential(Q64/Q32) controls; a separate row shows storage effects. Each state/cohort remains explicit. Symlog1Pa/s is display only, not an acceptance threshold, and zeros remain visible. Constant-k algebra results are in the CSV, not misleadingly plotted as a zero-RHS error.

The fresh `logs/upl_c08_pairk_flux_review_r1.check.json` binds inputs/outputs, includes descriptive actual-rate differences/sign changes and all12 focus rows, and retains physical_acceptance=false. Passing means the sealed-data analysis completed; it does not mean lower manufactured error everywhere, better physical collapse, dissipation, conservation, a proved root cause or an accepted operator replacement. No candidate rate was ever applied to a state.

The controls retain actual C/J/V/k and FS classification. Analytic p/A on fixed samples is a declared ghost oracle, not actual mDBC reconstruction. Uniform-A FS raw-pair cancellation is distinct from interior first-gradient closure; the nonconstant-potential zero also probes pressure-Laplacian versus Ace-divergence mismatch. Thus FS and interior errors, storage effects and native-field rate changes must be read separately. Neither the original96 outputs nor this review supplies a global or fully coupled spectrum, evolving material/contact response or authority to unlock other psi groups.

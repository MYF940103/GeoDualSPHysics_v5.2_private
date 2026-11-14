# Pressure-feedback offline scientific review r1

Author-only. Root must read this script/note and separately admit one offline execution after the actual r3 component passes. It does not call a force, material function, reader, solver, build, VTK exporter, Git or SHA tool. Earlier r1/r2 failures remain failures and are not reused as completed data. No physical parameter or public source is changed.

## Actual admitted input and provenance

Only logs/c08_h18_pressure_feedback_r3.check.json is accepted, with passed/consumed_stats_unchanged, exactly one component invocation and zero physical/solver steps. The root receipt must stat-bind the actual r3 build, actual owned exit0 call, completion and four CSVs. The private DebugCPU87-object/86-retained-object build and no-hook/defined-scope metadata must pass. Actual component program and source stats are checked once. No source/object/native SHA sweep or repeated old native qualification is performed.

Completion must confirm34 original force/Darcy calls, two real5000-ID baseline bit matches=10000,34 trials,80000 responses,48 original summaries,64 focus records and the original numerical/wall/FS/primary-state guards. Original literal/final-float and expanded source arithmetic maximum ratios must remain in[0,1]. Wall scratch is only read by the passed component for the actual effective active prefix; ignored mode is not read, local sentinel255 is diagnostic only. Its per-ID checks are not falsely presented as independently repeated by this CSV review. The review independently checks per-state NpbOk/active/inactive/ignored counts in every trial, including their sum1805, the same actual clock/step and completed coverage. Actual counts are used; an older wall-mode histogram is not reused as a physical active count.

Source CSVs are read once each. responses.csv is streamed into sixteen small5000-ID numeric groups, with no full native scan. All16 groups must cover native2060..7059 exactly and preserve their common per-ID baseline pressure/fixed P0/capacity/FS/cohort/R0 at each state. Actual times/steps must match the trials, with expected completed steps2076001/2152001; tau is kept as actually reported, not refitted. The genuine initial alt-X phase is reused from the passed component, checked for consistency across amplitudes/states; current x is not used to invent a phase.

## Independent arithmetic and its limits

The script verifies actual float p_plus/p_minus as float32(baseline_p ± h*phi), their exact quantization error, and genuine central half-differences dp=(p_plus−p_minus)/2 and dR=(R_plus−R_minus)/2. It verifies the reported second difference R_plus+R_minus−2R0. Baseline p is distinct from the native fixed P0 reference; neither is silently labelled paper excess.

For all5000, no-fixed-neighbor receiver and freshFS2/3 receiver cohorts separately, it recomputes capacity-weighted Q=sum(w*dp*dR), N=sum(w*dp²), w=nV/Kw, and Q/N where N>0. Full donors are retained. Q and N have units Pa m²/s and Pa m² for the2D unit-thickness convention; the ratio is1/s. These are conditional pressure-subsystem quantities, not fluid mass, total energy, full coupled spectrum or stability acceptance. A constant pressure perturbation at fixed effective stress changes total stress/free traction and the FS closure, so there is no gauge-null or sign requirement. Empty/zero-norm cohorts remain explicitly undefined; no clamp is introduced.

Original summary sums are compared with compensated independent sums using only double-aggregation roundoff envelopes based on the actual exported summands: gamma(n+16)*sum(abs(summand))+8eps*abs(sum)+64double_denorm. Original Q/N algebra and descriptive RMS are checked using corresponding propagated double operation-count envelopes. These are output-aggregation arithmetic gates, not new physical tolerances. No5Pa physical/model-equivalence gate is introduced.

The eight central channels are seven original physical RHS terms plus a separately labelled signed float/source-order residual. Their exported per-row and global Q closure errors are explicitly measured. The absolute plus/minus seven-term magnitudes and original per-row expanded budgets are NOT exported, so this script does not pretend to reconstruct those original budgets from central differences. The actual passed component's original per-row assertions and its two maximum ratios remain authoritative for that arithmetic qualification. Central closure error is reported as scientific numerical evidence without inventing a looser row tolerance or hiding it in a physical channel. Signed channels/cohorts can cancel; no net-source fractions are inferred from a small net Q.

For1Pa versus10Pa, the script reports Q/N ratios, rate RMS per requested Pa, second-difference RMS and actual quantization maxima. The amplitudes are not assumed equivalent, especially near AS spectral switches and float limits. Zero ratios are not forced to be equal. Focus64 rows must match the response actual p/P0/R values and actual float AS tensors; tensor norm checks use an arithmetic-only double bound. No constitutive eigenvalue or additional AS force model is introduced.

## Exclusive outputs

New folder figures/c08_h18_pressure_feedback_review_r1 and logs/c08_h18_pressure_feedback_review_r1.check.json must not already exist. On failure, inputs and partial derived outputs are preserved; the script does not retry or overwrite.

- summary.csv:48 independently recomputed cohort entries, eight signed Q channels, observed central closure and original-summary double aggregation ratio.
- amplitude.csv:24 one-versus-ten amplitude comparisons, including undefined ratios without substitution.
- focus.csv:64 fixed material-ID entries retaining actual AS tensors, pressure/reference, central rate/Ace and eight channels.
- conditional_work.png:two source states, with the constant mode shown separately from high-frequency/fixed-pair modes and all/no-wall/FS receiver cohorts. Q sign is not an acceptance condition.
- channels_focus.png:eight channels remain separately visible (numeric residual last), and four original fixed IDs show the actual alt-X rate response at both amplitudes. Signed symlog color scaling is display-only and retains zero/negative values.

There are exactly two static scientific PNGs, with matching small CSV data. No new raw CSV/native history is duplicated. The derived check records actual wall counts, clocks, original arithmetic ratios and observed central closure, with visual_QA_pending until root examines the figures.

## Interpretation boundary

All sigma-effective/v/J/kappa/P0/rho/k/positions are frozen. Wall p and Ace are lawfully reconstructed by the original force and the AS spectrum changes with actual p, but geometry/material evolution and same-stage contact reaction are absent. Fixed FS classification is a conditional mathematical experiment, not a new admissible physical solution. Negative high-frequency/local Q/N means damping in those sampled conditional directions only; positive constant Q/N does not prove full-system instability. No pressure-cap/filter/AS/AV modification or new physical window follows automatically.

Root-only later command: python -B tests/support/c08_h18_pressure_feedback_review_r1.py --execution-authorized. This is offline analysis only.

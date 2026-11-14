# C08 six-state power review r1

Author-only offline script `support/c08_h18_bed_power_review_r1.py`. Root must read and separately admit its one execution. The component and all original source/CSV/native files remain unchanged. This script calls no component, physical solver, native reader, build, Git, SHA, filter or material return.

## Inputs and finite scope

Require genuine passed `logs/c08_h18_bed_power_probe_r1.check.json`, bound completion/actual call/build, true Popen/Win32 exits0 and unchanged consumed stats. The passed coverage is14 Restore/CellDivide,8 sorting-only states,6 force/Darcy,30000 material rows×58 external scalar bits (1740000),theta30000,Rσ180000,24 focus,2855 active walls and12 power rows. This existing implementation evidence is reused; no historical qualification chain or native field is re-read.

The component receipt had no exit-time CSV stat list. Therefore the script records **first post-pass author observation** of the seven current CSV size/mtime values at 2026-11-14T21:50:12.319Z; it does not relabel these as exit-time seals. Every observation must still match before reading and after analysis. The source check, completion, call and build retain their original bindings.

Read exactly the actual CSV widths/counts: power23×12, metrics18×6, soil89×30000, focus89×24, walls44×2855, route9×14 and full signed clock12×6. Match actual time/completed-step/IDs, the original signed dterror<=1e-14 guard, all5000 soil IDs per state, four fixed material focus IDs, active wall modes/counts, and the14-state order with six selected forces. No numerical values are smoothed, discarded or clipped.

## Independent arithmetic / scientific comparison

Stream the30000 soil rows once in **original file order**, separately accumulating the nine actual exported nodal power columns and their absolute values for fluid and wall passes. All216 resulting sums (12 groups×9×2) must reproduce the source power summary double bits. This is a saved-table arithmetic/association check, not a physical tolerance or a new stress-force truth. Focus rows must equal their source soil rows. The script does not re-evaluate neighbors, forces or gradients.

Derived comparison.csv has12 rows:

* P = combined pure source-literal momentum power;
* Wraw = effective_raw_virtual + pressure_raw_virtual;
* Wcorrected = effective_G1_virtual + pressure_theta_virtual;
* raw/corrected gap = P−W;
* descriptive scale = Σ|nodal effective force power|+Σ|nodal pressure force power|, with signed gap percentages; a zero denominator remains N/A;
* the source nine signed/absolute powers, original split-residual power and its small double-association difference from P−Peff−Pp remain explicit.

The scale is **not** the denominator used by the earlier bed-gradient conditional work percentage; the values (e.g. prior45.5% versus new~29.7% at originalP30 wall) must not be compared as though normalized identically. Wcorrected uses actual double theta for pressure, not a manufactured equality to G1 trace. Pressure p and P0 retain their original meanings; p−P0 is not relabelled paper plastic excess.

Pure combined/effective/pressure accumulators are independent float source-literal evaluations; they are not obtained by subtracting mixed total Ace. There is no preexisting pure-term bit truth. Wall ghost-force/mirror-strain accounting is conditional and is **not** a closed real-wall external-work balance. These are CPU saved-state recomputations, not true GPU substage force/energy. Signed gaps are not used as an acceptance threshold, proof of J error, proof of injected energy, or causal proof for clumping/early arrest.

## Outputs

Exclusive new paths only:

* `figures/c08_h18_bed_power_review_r1_comparison.csv`:12 pass/state comparisons;
* `figures/c08_h18_bed_power_review_r1_focus.csv`:24 same-material points with pressure/J/κ/FS/theta/rate and per-pass powers/gaps;
* `figures/c08_h18_bed_power_review_r1.png`:one2×2 scientific figure, top row P/Wraw/Wcorrected for fluid and wall, bottom row signed gaps. Bottom axes use symlog with0.01W/m linear threshold so small raw-rounding and larger corrected gaps remain visible without deleting sign or points. All lines join only the three actual sampled times; no fitted curve or interpolation is computed.
* `logs/c08_h18_bed_power_review_r1.check.json`:arithmetic coverage, explicit definitions/limits, first-observation stat scope and file stats. Physical acceptance stays false; visual QA is explicitly pending root inspection.

Root may invoke once after full review:

`D:/anaconda3/python.exe -B tests/support/c08_h18_bed_power_review_r1.py --execution-authorized`

Existing outputs or partials are protected with exclusive writes. Any failure preserves the new partial products and reports its actual first cause; the script never retries the component or physical calculation. Author only read receipt/schema/small headers and wrote these two new files; no analysis script was executed.

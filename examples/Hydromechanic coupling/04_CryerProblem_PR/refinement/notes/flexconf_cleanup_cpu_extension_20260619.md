# FlexibleConfinement cleanup and CPU extension note

Date: 2026-06-19

Scope:
- Previous `zhao_flexconf` and `zhao_flex_full003` test outputs were cleaned from `out/`, `analysis/`, run logs, and stale PID files.
- XML, BAT, and analysis script files were retained for reuse.
- The near-free-surface limiter branch was judged worse than the no-limiter flexible confinement baseline and was removed before this note.
- Current Cryer loading baseline remains `HydroMechTopLoadMode=3`, i.e. no-correction `FlexibleConfinement`.

Code conclusion:
- `FlexibleConfinement` is now extended to the CPU interaction path using the same pairwise pressure contribution as the GPU validation path.
- Stage restart inherits `Sigma`, `PorePress`, and `PorePress0` when `HydroMechInitMode=0`; `Kplastic` is reset for the restarted stage.

Next test:
- Use `dp=0.003` as the baseline resolution.
- First rerun Stage 1 long enough to identify a quasi-stable undrained state.
- Then restart Stage 2 from the selected Stage 1 PART and compare the center pore pressure against the analytical Cryer curve with drainage time reset at the restart time.

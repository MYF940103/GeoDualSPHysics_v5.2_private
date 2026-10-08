# q0 Terzaghi test artifact layout rule, 2026-07-14

All temporary or diagnostic q0 Terzaghi test artifacts should stay under
`tests/` instead of the case root.

Use this layout:

- XML test configs: `tests/configs/<test-family>/`
- Runnable top-level test BAT files: `tests/`
- Archived/generated BAT files that are not intended as the primary runner:
  `tests/configs/<test-family>/`
- Solver output directories: `tests/outputs/<test-family>/`
- Run logs and stale process markers: `tests/logs/<test-family>/`
- Figures and CSV summaries: `tests/figures/<test-family>/`
- Conclusions and diagnostics: `tests/notes/`

After moving existing resolution/formal/gpu validation artifacts, the path
fallbacks in the following helper scripts were updated:

- `tests/support/resolution_k1em4_convergence.py`
- `support/summarize_full_validation_q0.py`

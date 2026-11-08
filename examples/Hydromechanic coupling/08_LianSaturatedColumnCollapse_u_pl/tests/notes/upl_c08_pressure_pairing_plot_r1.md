# Frozen pressure-operator comparison figure

`support/upl_c08_pressure_pairing_plot_r1.py` reads the completed eight-block A/B CSV and its passed receipt. It creates one fresh PNG and a stat-bound check under `tests/figures`; no matrix, solver or native export is recomputed. The two panels retain all patch variables and the FS0 principal block separately. The paired D/G curves are mathematical controls, not implemented production operators or full-state stability results. Their constant/hydrostatic consistency and boundary limitations remain those in `upl_c08_pressure_pairing_ab_r1.md`.

# Display tick spacing only

Derived verbatim from c08_h18_field_display_r2.py except its new tag and one colorbar-tick expression. Root read the entire r2 source and this two-edit derivation. Prior r2 source, receipts and PNGs remain unchanged.

The zero-centered pressure scale has two slopes. Equally spaced physical ticks can put a small negative tick directly beside zero. Use two equally spaced ticks per half, retaining the same min/zero/max, normalization, color values, raw data and all old checks. No extra scientific gate, smoothing, clipping, decoder or solver.

Use the same explicit {tag,review_check,fields_csv,title} manifest under a fresh output tag. The r2 method note describes the unchanged behavior. New outputs remain in tests/figures and tests/logs, never overwrite r2 figures.

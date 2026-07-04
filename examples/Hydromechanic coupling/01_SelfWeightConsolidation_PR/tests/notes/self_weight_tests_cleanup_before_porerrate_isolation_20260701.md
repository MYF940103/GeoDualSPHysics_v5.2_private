# Self-weight tests cleanup before pore-rate isolation

Date: 2026-07-01

Cleaned the previous `MdbcPwLegacy` isolation outputs from `tests/outputs`, `tests/figures`, `tests/configs`, and root-level run logs/batch files.

Kept notes only. Previous conclusion: restoring the old mDBC pore-pressure scheduling alone did not reproduce the old CPU baseline, so the next isolation targets the pore-pressure-rate path.

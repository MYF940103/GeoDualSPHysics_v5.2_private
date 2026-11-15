The original offline review failed only because the complete first-n snapshot is a 907392-byte CSV, not a .bin. Preserve its original failed check and all completed solver/native outputs. This r2 changes only the snapshot leaf and writes a fresh .review_r2.check.json; all byte/ID/clock/signed/HG/safety requirements remain unchanged. No solver or reader is rerun.

# Host-only capture implementation controls

This offline tool starts no solver, native reader, VTK, build or next job. It consumes each already completed, uniquely decoded host-capture short once and preserves its first check result.

Debug2 and Release4 compare the complete same-count typed22 binary exports, including actual record times, plus the entire layout/clock/signed CSV rows. No field or signed diagnostic is excluded. HG60-column phase records and policy must match the retained optimized controls. Debug additionally compares the complete907392-byte first-n snapshot/configuration and checks the actual memcheck log; Release must contain a genuine plastic saved stage.

The native reader's original IDs/P0/J/ledger/FS/plane/time/signed guards remain independent prerequisites. These are implementation no-feedback checks, not new half-step runs or physical accuracy/energy certificates. Cache bit checks establish coherence, not an independent material solve. An unexpected fault directory or any byte difference rejects the candidate; existing data and checks are never overwritten.

Use only after root review: `python -X utf8 -B tests/support/c08_h18_hg_wall_host_short_review_r2.py --profile debug2|prefix4 --execution-authorized`.

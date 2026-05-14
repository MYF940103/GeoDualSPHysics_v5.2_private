# Interface Cleanup Lessons

This file distills INTF1 into rollback guidance.

## Categories

Use exactly four lifecycle categories:

- Production/stable: documented, validated, default-safe.
- Active experimental: default off, narrow owner/task, explicit exit criteria.
- Deprecated/archived: retained only to replay old reports.
- Delete candidate: failed or temporary interface to remove in cleanup.

## Rules For Rebuild

1. Every new XML parameter must default off or preserve prior behavior.
2. Every new parameter must document CPU/GPU status.
3. GPU unsupported experimental parameters must hard-error, not silently ignore.
4. No mode family should grow without a cleanup decision.
5. If a test fails, first decide deprecate/delete before adding another mode.
6. Diagnostics should prefer CSV/postprocessing/logs over permanent XML knobs.
7. A failed route should be archived as a report, not left as a recommended
   example.

## Specific Interface Decisions

Keep or consider cherry-pick:

- `PorePressureInit=3` for uniform initial excess pressure.
- `PorePressureFeedbackOperator=1` for current 1D feedback gate.
- analytical postprocessing scripts for 1D consolidation.
- pairwise platen diagnostics if triaxial work resumes.

Keep as active experimental only with caveats:

- `SoilConstitutiveModel=3` MCC CPU prototype.
- `PorePressureBoundaryOperator=1` until promoted by stronger validation.

Deprecate or delete candidate:

- most `CurvedDrainedBoundaryMode` variants;
- `PorePressureBoundaryOperator=2` as default candidate, after BND1 failure;
- `MechanicalTopLoad*` as strict validation route;
- `PorePressureTimeIntegrationMode=1` after TINT2 neutral result;
- MCC substepping/fallback/line-search knobs not needed for replay.

## Strong Warning

The next branch should not start by copying the whole current parameter surface.
It should cherry-pick only the minimum validated interfaces needed for the next
benchmark.

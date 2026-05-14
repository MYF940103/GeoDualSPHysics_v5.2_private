# Cherry-Pick After Rollback

This file lists likely candidates to recover after resetting the branch.

## High-Value Commits

Use `git show --stat <commit>` before cherry-picking. Prefer reimplementation if
the commit drags in too much experimental surface.

Likely high-value:

```text
d5367c0 Add consistent initial-state 1D consolidation validation
1521423 Add GPU long-run 1D consolidation validation
1fdf949 Add feedback-on 1D consolidation coupling gate
db3c5cf Register experimental u-pw interfaces
```

Consider only if needed:

```text
3801e69 Add mechanical top-load route for 1D consolidation
0a5050f Generalize pore-pressure boundary particle operator
1b1c1f8 Add end-step pore-pressure integration experiment
b8488ca Add CPU MCC stress update branch
40a373b Add C++ MCC single-point parity helper
```

Avoid cherry-picking wholesale:

```text
Cryer curved boundary mode sequence
MCC substepping/admissible line-search sequence
M3 geometry smoothing/fan-like diagnostic sequence
TINT2 mode 1, unless replaying the neutral result
BND1 mode 2 as recommended/default boundary operator
```

## Suggested Recovery Order

1. Restore interface governance docs.
2. Restore minimal `PorePressureInit=3`.
3. Restore L3c/L4 scripts and example package.
4. Restore L5 feedback-on gate with operator `1`.
5. Only then decide if landslide reduced baseline should begin.

## Cherry-Pick Safety Pattern

```powershell
git checkout <clean-base-branch>
git checkout -b u-pw-rebuild
git cherry-pick -n <candidate-commit>
git diff --stat
git diff
```

If the diff includes unrelated experimental parameters, abort and reimplement
the smaller feature:

```powershell
git cherry-pick --abort
```

## What To Reimplement Instead Of Cherry-Pick

Some features are better rewritten in smaller form:

- uniform initial excess pressure initializer;
- 1D analytical postprocessing;
- feedback-on diagnostics;
- interface registry table.

Reason: many commits mixed useful code with experimental XML/report churn.

## What Not To Claim After Rollback

Do not claim:

- strict mechanical Terzaghi loading reproduction;
- clean MCC validation;
- strict Cryer validation;
- GPU support for CPU-only experimental modes;
- production readiness of boundary operator mode `2`.

# Experimental Interface Cleanup Policy

Date: 2026-05-14

This policy governs u-pw XML/source interfaces added during prototype work.
The goal is to stop interface creep: failed modes should be archived or
deleted, not hidden under another mode number.

## Categories

### Category A: Production / Stable

Use `[PRODUCTION]`.

Criteria:

- validated in the relevant CPU path and, when claimed, GPU path;
- documented in `u_pw_parameters.md`;
- safe default or safe documented option;
- no unresolved hard-error surprise for expected workflows;
- can be used in new cases without referencing an old experiment caveat.

Action:

- keep source and docs;
- add regression tests when possible;
- if GPU is unsupported, the docs must say so explicitly.

### Category B: Active Experimental

Use `[ACTIVE_EXPERIMENTAL]`.

Criteria:

- currently being evaluated for a named task sequence;
- default is off;
- owner/task and exit criteria are documented;
- not recommended as a default;
- GPU support is either implemented, deferred, or hard-error documented.

Action:

- allow only in explicitly named experiments;
- record pass/fail after each task;
- decide `promote`, `deprecate`, or `delete` immediately after the experiment
  family finishes.

### Category C: Deprecated / Archived

Use `[DEPRECATED]`.

Criteria:

- retained for reproducibility of old cases or reports;
- not recommended for new cases;
- may be CPU-only or partially unsupported;
- source cleanup is possible but not immediate.

Action:

- mark in `u_pw_parameters.md`;
- keep old XML/reports reproducible until an archive branch is created;
- do not port to GPU;
- do not extend with new modes.

### Category D: Delete Candidate

Use `[DELETE_CANDIDATE]`.

Criteria:

- failed validation;
- no current planned follow-up;
- only used by obsolete exploratory XML;
- or was added as temporary diagnostics.

Action:

- do not use in new XML;
- do not port to GPU;
- collect affected old XML into an archive note;
- delete in the next cleanup branch unless explicitly preserved for replay.

## Mandatory Tags

Every new or existing non-production interface should carry applicable support
tags:

- `[CPU_ONLY]`
- `[GPU_DEFERRED]`
- `[GPU_HARD_ERROR]`

`[GPU_DEFERRED]` means a port may be designed later. `[GPU_HARD_ERROR]` means
the parser must fail early if the interface is requested on GPU.

## Rules For New Interfaces

1. New parameters must default off or preserve legacy behavior exactly.
2. New parameters must state CPU/GPU support at introduction.
3. New parameters must name an owning task, for example `TINT2`, `BND1`, or
   `M3h`.
4. New parameters must have a cleanup decision planned from the beginning:
   `keep`, `promote`, `deprecate`, or `delete`.
5. New parameters cannot stay permanently in `u_pw_parameters.md` without a
   status label.
6. The same function must not accumulate unlimited numbered modes.
7. If a mode fails, the next step should be diagnosis, deletion, or archive,
   not `mode+1` by default.
8. Temporary diagnostics should prefer logs, postprocessing scripts, and
   existing CSV fields over new XML switches.
9. A GPU port should not begin until CPU behavior is validated and the cleanup
   decision is not `delete`.
10. Default changes require a separate default-decision document and a rollback
   plan.

## Exit Criteria Template

Each active experimental interface should be able to answer:

- What task introduced it?
- Which cases must pass?
- Which cases failed?
- Is it allowed in new cases?
- Does GPU hard-error, defer, or pass?
- What is the next decision date/task?
- What is the cleanup action if it fails?

## TINT2-Specific Rules

TINT2 is allowed to add only a minimal pressure time-staging selector:

- `PorePressureTimeIntegrationMode=0`: current default.
- `PorePressureTimeIntegrationMode=1`: CPU end-step pressure commit.
- `PorePressureTimeIntegrationMode=2`: reserved only; do not implement extra
  behavior in TINT2.

Diagnostics should use existing output, scripts, or logs first. If
`SavePorePressureTimeStageDiagnostics` is unavoidable, it must be marked
`[ACTIVE_EXPERIMENTAL] [DELETE_CANDIDATE]` at introduction, with a TINT2-clean
decision immediately after the test matrix.

If mode `1` does not improve or clarify L3c/L5/BND1 behavior, it should be
deprecated or deleted after TINT2. Do not add mode `3/4` before removing or
archiving failed modes.

## Cleanup Branch Priorities

1. Archive/delete failed Cryer curved-drained modes `5-8` and their MLS/shell/
   limiter parameters.
2. Archive/delete triaxial feedback class filters and limiter routes that did
   not produce a clean validation path.
3. Archive/delete `CapConfiningStress*` unless a specific old report must be
   replayed.
4. Decide whether MCC robustness controls remain useful diagnostics or become
   deprecated after the caveated MCC package is frozen.
5. Decide the fate of `MechanicalTopLoad*` after any future L3d/L5b mechanical
   loading route is chosen.

# Autonomous Pre-GPU Completion Run Log

Date: 2026-05-11

## Current Commit

`139c359` - `Add final pre-GPU readiness report`

## Working Tree Summary

`git status --short` shows no tracked source modifications. The working tree
does contain long-standing untracked files outside the current automation scope,
including:

- legacy/example input CSV files under `examples/`;
- local experimental files such as `src/CPUF6a_SelfWeightS2_Def.xml` and
  `src/_codex_phase3g_verify/`;
- `src/docs/`;
- the main u-pw paper PDF in `src/papers/u-p/`;
- many untracked reference/source files under `src/source/` and
  `src/source_DualSPHysics+/`.

These are not touched or committed by this automation unless explicitly needed
for the u-pw reference ingestion step.

## This Run's Goal

Complete the remaining CPU pre-GPU bookkeeping and readiness checks without
entering GPU coding:

1. ingest available paper PDFs into text/markdown if tooling permits;
2. reconcile the case audit and implementation backlog from the extracted
   references;
3. refresh case smoke readiness documentation;
4. verify deprecated debug interfaces remain removed from active source;
5. record final readiness status and any blockers.

## Hard Exclusions

This run does not modify:

- `JSphGpu*`;
- `JCellDivGpu*`;
- `.cu` files;
- CUDA kernels;
- GPU memory, sorting, duplicate, or output code.

This run also does not start CPU long-time parameter studies.

## Planned Automatic Phases

1. Preflight and run-log commit.
2. PDF/reference ingestion.
3. Case audit reconciliation.
4. Case smoke readiness refresh.
5. CPU cleanup/freeze check.
6. Remaining blocker decision.
7. Optional short build/smoke sanity if source state is clean and runtime is
   expected to remain short.
8. Final pre-GPU readiness report.

## Phase 4 Cleanup / Freeze Check

Active source search:

- `TopLoadEnabled`, `TopLoad`, `TopLoadThickness`, `TopLoadRampStart`,
  `TopLoadRampEnd`, and `ApplyTopLoad`: no active `src/source` matches.
- `PorePressureAccelSymCorr` and `PorePressureAceSymCorrc`: no active
  `src/source` matches.

Formal XML search:

- No formal `examples/u-pw` XML outside archived `experiments/` and historical
  result folders depends on `TopLoad*`.
- Many archived experiment XML files still contain historical `TopLoad*` keys.
  These are retained as historical records and are not guaranteed to run after
  CPU-F6a.

Conclusion:

- The CPU production interface cleanup is complete.
- GPU planning must not include source-side `TopLoad*` or
  `PorePressureAccelSymCorr`.

## Phase 6 Build / Smoke Sanity

CPU Debug rebuild:

- Command: `msbuild .\src\VS\DualSPHysics5ReCpu_vs2022.sln /m /t:Build /p:Configuration=DebugCPU /p:Platform=x64 /v:minimal`
- Result: success.
- Executable refreshed: `bin/windows/DualSPHysics5.2CPU_win64_debug.exe`.

Extended-timeout short smoke sanity:

| Smoke | GenCase | DualSPHysics | Excluded | Runtime | Key fields | Notes |
|---|---:|---:|---:|---:|---|---|
| 01 pressure-only micro | 0 | 0 | 0 | 19.95 s | ok | Pore-pressure diagnostics written. |
| 02 Scenario 1 Stage A | 0 | 0 | 0 | 52.40 s | ok | Self-weight generation stage. |
| 02 Scenario 1 Stage B restart | 0 | 0 | 0 | 25.50 s | ok | `PorePress` restored from restart; XML init skipped. |
| 02 Scenario 2 micro | 0 | 0 | 0 | 80.69 s | ok | Gravity-on short dissipation smoke. |

CSV scan:

- No `NaN` / `Inf` tokens detected in `PartCsv_*.csv`.
- Required fields were present: `PorePress`, `ExcessPorePress`,
  `PorePressRate`, `DivVel`, `LapPorePress`, `LapZ`,
  `PorePressureAccelDiff`.

Conclusion:

- The build sanity is valid.
- The 01/02 CPU smoke sanity passed under the extended 120-minute allowance.
- This removes the previous automation timeout blocker, but it does not complete
  strict 03-06 paper-case readiness.
- Do not enter GPU coding from this automation run.

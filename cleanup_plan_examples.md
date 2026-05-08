# Cleanup Plan for examples generated during u-pw / 1D consolidation work

Scope: this is a planning document only. Do not delete, move, rename, or modify source files from this document without a separate explicit command.

Checked directories:

- `examples/myf`
- `examples/u-pw/01_1D_Consolidation`

Generated after read-only inventory.

---

## 1. Current Git Status Summary

Important tracked source/paper state seen during inventory:

- Modified source files currently present:
  - `src/source/JSph.cpp`
  - `src/source/JSph.h`
  - `src/source/JSphCpu.cpp`
  - `src/source/JSphCpu.h`
  - `src/source/JSphCpuSingle.cpp`
- Tracked deletion currently present:
  - `src/papers/u_pw_sph_implementation_notes.md`
- Large number of untracked example test files and output logs/directories exist under `examples/myf` and `examples/u-pw/01_1D_Consolidation`.

Do not clean these with a broad command until the source commit state and paper-note deletion are intentionally handled.

---

## 2. Output Footprint Summary

### `examples/myf`

Generated/output-like files and folders detected:

- `*_out/`: 84 directories
- nested `data/`: 81 directories
- `PartCsv_*.csv`: 402 files, about 6369 MB
- `Part_*.bi4`: 1881 files, about 71999 MB
- `PartExtra_*.bi4`: 5 files
- `PartInfo.ibi4`: 77 files
- `PartOut_*.obi4`: 77 files
- `*.nbi4`: 73 files, about 154 MB
- `*.vtk`: 3812 files, about 84119 MB
- `*.dual.log`: 21 files
- `*.gencase.log`: 21 files

This directory contains very large generated artifacts. Most reclaimable space is in `.vtk`, `.bi4`, and `PartCsv_*.csv` files inside output directories.

### `examples/u-pw/01_1D_Consolidation`

Generated/output-like files and folders detected:

- `*_out/`: 53 directories
- nested `data/`: 53 directories
- `PartCsv_*.csv`: 316 files, about 99 MB
- `Part_*.bi4`: 316 files, about 27 MB
- `PartInfo.ibi4`: 53 files
- `PartOut_*.obi4`: 53 files
- `*.nbi4`: 53 files
- `*.vtk`: 689 files
- `*.dual.log`: 33 files
- `*.gencase.log`: 33 files
- `*.status.txt`: 11 files

This directory is smaller but cluttered by many diagnostic phases.

---

## 3. Category A: Keep as Formal Case Templates

### `examples/myf`

Keep the original or long-term useful case folders and their source inputs/scripts:

- `examples/myf/00_StaticSoilColumn/`
  - dry/static soil column base case.
- `examples/myf/01_GranularFailuerOnBed/`
  - original granular failure case. Note spelling appears to be existing project spelling.
- `examples/myf/02_ImpactForces/`
  - current VS Code debug case uses slope45 ImpactForces. Keep XML, scripts, experimental/reference inputs, plotting scripts.
  - Do not delete experimental data such as any `Impact_force_exp.csv` if present.
- `examples/myf/03_CudeSlidingOnSlope/`
- `examples/myf/04_BallDropOnGranularBed/`
- `examples/myf/05_ImpactGranularOnBlocks/`
- `examples/myf/06_TestPerformance/`
- `examples/myf/07_TestPerformanceCoupling/`
- `examples/myf/08_CohesiveGranularCollapse/`
- `examples/myf/Case01_2DGranular Collapse/`

Keep these as case templates. Remove only their generated output directories/logs after confirmation.

Potentially keep as useful u-pw preparation templates:

- `examples/myf/01_SaturatedSoilColumn_PR/`
  - early saturated PR column template.
- `examples/myf/04_StaticSoilColumn_DryRelaxation_RestartReady/`
  - useful restart-ready dry relaxation template.
- `examples/myf/05_SaturatedSoilColumn_PR_RestartFromDry/`
  - useful restart-from-dry saturated PR template.

For those three, keep `.xml` and `.bat`; clean generated `_out/`, logs, backup XML copies only after preserving the final intended XML.

### `examples/u-pw/01_1D_Consolidation`

Keep formal pressure-only baseline:

- `Case1DConsolidation_PR_Def.xml`
- `xCase1DConsolidation_PR_win64_CPU_debug.bat`

This is the pressure-only / Terzaghi-like diffusion baseline and should remain directly in the case root.

Keep or promote after review:

- `Case1DConsolidation_PR_AccInputSmoke_Def.xml`
- `xCase1DConsolidation_PR_AccInputSmoke_win64_CPU_debug.bat`
- `TopLoadAcc_m1.csv`

These are not a final paper reproduction case, but they are useful for AccInput diagnostics. Better moved to `experiments/AccInputSmoke/` rather than deleted.

Input CSV files to avoid accidental deletion:

- `TopLoadAcc_m1.csv`
- `TopLoadAcc_Phase4o_m1.csv`
- `TopLoadAcc_Phase4o_m5.csv`
- `TopLoadAcc_Phase4o_m10.csv`
- `TopLoadAcc_Phase4o_m50.csv`
- `TopLoadAcc_SW1_zero.csv`

These are small input files; either move them to `input/` or to matching experiment folders.

---

## 4. Category B: Move to `experiments/` or `archive/`

These are useful diagnostics but should not remain mixed with formal case templates.

### Recommended archive groups under `examples/myf`

Move to something like `examples/myf/archive_u_pw_restart/` or keep as subfolders under an `experiments/` folder:

- `02_StaticSoilColumn_DryRelaxationCompare/`
- `06_RestartContinuityDiagnostics/`
- `06_RestartContinuityDiagnostics_A_ReleaseCheck/`
- `07_RestartContinuity_ContinuousExtension/`
- `07_RestartContinuity_ContinuousExtension_FinalOnly/`
- `07_RestartContinuity_ContinuousExtension_FinalOnly_Debug/`
- `07_RestartTimeContinuityDiagnostics/`
- `08_RestartPrecisionDiagnostics_SavePosDouble/`
- `08_StaticSoilColumn_DryRelaxation_RestartReady_SavePosDouble/`
- `09_RestartBoundaryModeDiagnostics/`

Rationale: these diagnose restart continuity, Rhop reset, stress restore, mDBC/cDBC behavior, and SavePosDouble. They are valuable history but not formal examples.

### Recommended `examples/u-pw/01_1D_Consolidation/experiments/` structure

Move exploratory XML/BAT/CSV inputs, not output folders, into:

```text
examples/u-pw/01_1D_Consolidation/
  experiments/
    AccInputSmoke/
    AccInputIsolation/
    FeedbackOperatorDiagnostics/
    TwoStageSmoke/
    RampSensitivity/
    DampingLadder/
    SmallLoadLadder/
    ShepardSmoke/
```

Suggested mapping:

- `AccInputSmoke/`
  - `Case1DConsolidation_PR_AccInputSmoke_Def.xml`
  - `xCase1DConsolidation_PR_AccInputSmoke_win64_CPU_debug.bat`
  - `TopLoadAcc_m1.csv`

- `AccInputIsolation/`
  - `Case1DConsolidation_PR_AccIso_T1_GG0_Def.xml`
  - `Case1DConsolidation_PR_AccIso_T1_GG1_Def.xml`
  - `Case1DConsolidation_PR_AccIso_T2_PR_NoFeedback_Def.xml`
  - `Case1DConsolidation_PR_AccIso_T3_Model0_Feedback_Def.xml`

- `FeedbackOperatorDiagnostics/`
  - `Case1DConsolidation_PR_Phase4h_*_Def.xml`
  - `Case1DConsolidation_PR_Phase4i_*_Def.xml`
  - `Case1DConsolidation_PR_Phase4k_A_SymUniform_Def.xml`
  - `Case1DConsolidation_PR_Phase4k_B_DiffUniform_Def.xml`

- `TwoStageSmoke/`
  - `Case1DConsolidation_PR_Coupled_Def.xml`
  - `Case1DConsolidation_PR_TwoStageSmoke_Def.xml`
  - `Case1DConsolidation_PR_TwoStageHydroInit_Def.xml`
  - `Case1DConsolidation_PR_TwoStageHydroInit_ExcessFb_Def.xml`
  - `Case1DConsolidation_PR_Phase4k_C_TwoStageDiff_Def.xml`
  - `Case1DConsolidation_PR_Phase4k_C2_TwoStageDiff001_Def.xml`

- `RampSensitivity/`
  - `Case1DConsolidation_PR_Phase4l_Ramp005_Def.xml`
  - `Case1DConsolidation_PR_Phase4l_Ramp010_Def.xml`
  - `Case1DConsolidation_PR_Phase4l_Ramp020_Def.xml`
  - `Case1DConsolidation_PR_Phase4l_Loadm*_Def.xml`

- `DampingLadder/`
  - `Case1DConsolidation_PR_Phase4m_*_Def.xml`
  - `Case1DConsolidation_PR_Phase4n_Damp*_Def.xml`

- `SmallLoadLadder/`
  - `Case1DConsolidation_PR_Phase4o_Loadm*_Def.xml`
  - `TopLoadAcc_Phase4o_*.csv`

- `ShepardSmoke/`
  - `Case1DConsolidation_PR_SW1_*_Def.xml`
  - `TopLoadAcc_SW1_zero.csv`

---

## 5. Category C: Safe Deletion Candidates After Confirmation

Delete only after the user explicitly confirms. Current step did not delete anything.

### Output directories

In both checked roots, the strongest deletion candidates are:

- any `*_out/` directory
- nested `data/` directories created by solver runs

Examples in `examples/u-pw/01_1D_Consolidation`:

- `Case1DConsolidation_PR_out/`
- `Case1DConsolidation_PR_AccInputSmoke_out/`
- `Case1DConsolidation_PR_AccIso_*_out/`
- `Case1DConsolidation_PR_Coupled_out/`
- `Case1DConsolidation_PR_Phase4h_*_out/`
- `Case1DConsolidation_PR_Phase4i_*_out/`
- `Case1DConsolidation_PR_Phase4k_*_out/`
- `Case1DConsolidation_PR_Phase4l_*_out/`
- `Case1DConsolidation_PR_Phase4m_*_out/`
- `Case1DConsolidation_PR_Phase4n_*_out/`
- `Case1DConsolidation_PR_Phase4o_*_out/`
- `Case1DConsolidation_PR_SW1_*_out/`
- `Case1DConsolidation_PR_TwoStage*_out/`

Examples in `examples/myf`:

- all `*_out/` directories under original cases if regenerated output is not needed.
- restart diagnostic outputs under `06_*`, `07_*`, `08_*`, `09_*` diagnostic folders.
- historical saturated/restart outputs under `01_SaturatedSoilColumn_PR`, `04_StaticSoilColumn_DryRelaxation_RestartReady`, `05_SaturatedSoilColumn_PR_RestartFromDry`, after preserving final XML/BAT templates.

### Generated files

Within examples, these are generally generated outputs:

- `PartCsv_*.csv`
- `Part_*.bi4`
- `PartExtra_*.bi4`
- `PartInfo.ibi4`
- `PartOut_*.obi4`
- `*.nbi4`
- `*.vtk`
- `Run.out`
- `Run.csv`
- `*.dual.log`
- `*.gencase.log`
- `*.status.txt`

Caution: `.csv` is ambiguous. Do not delete all CSV blindly because `TopLoadAcc_*.csv` and possible experimental datasets are inputs.

### Backup XML files

Likely deletion candidates after confirming final XML is preserved:

- `*.phase4*_backup*`
- other temporary `*.backup*` files

Examples seen under `examples/myf/05_SaturatedSoilColumn_PR_RestartFromDry/`:

- `CaseSaturatedSoilColumn_PR_RestartFromDry_Def.xml.phase4dB2_backup`
- `CaseSaturatedSoilColumn_PR_RestartFromDry_Def.xml.phase4dB_backup_20260507231411`
- `CaseSaturatedSoilColumn_PR_RestartFromDry_Def.xml.phase4d_backup_20260507231229`
- `CaseSaturatedSoilColumn_PR_RestartFromDry_Def.xml.phase4e*_backup*`
- `CaseSaturatedSoilColumn_PR_RestartFromDry_Def.xml.phase4f_backup*`

---

## 6. Category D: Uncertain / Needs Manual Confirmation

Do not delete these automatically:

- Any `TopLoadAcc_*.csv` file. These are AccInput input files, not output.
- Any experimental/reference data CSV, e.g. possible `Impact_force_exp.csv` or similar validation datasets.
- Any `.mp4` videos that are intentionally kept for documentation or presentations.
- Any plotting scripts: `.m`, `.py`, `.ps1`, `.sh`, `.bat` should be reviewed case by case.
- `examples/myf/08_CohesiveGranularCollapse/runlogs*/` contain diagnostic logs that may or may not be desired. They are not `_out/` directories, so confirm before deleting.
- `examples/myf/08_CohesiveGranularCollapse/videos/` and other `videos/` folders.
- `examples/myf/04_StaticSoilColumn_DryRelaxation_RestartReady/` final restart-ready templates.
- `examples/myf/05_SaturatedSoilColumn_PR_RestartFromDry/` final restart-from-dry templates.
- Any XML that may have become the latest manually tuned template.

---

## 7. Recommended Final Directory Structure

For the u-pw paper reproduction path:

```text
examples/u-pw/01_1D_Consolidation/
  README.md
  Case1DConsolidation_PR_Def.xml
  xCase1DConsolidation_PR_win64_CPU_debug.bat
  input/
    TopLoadAcc_m1.csv
    TopLoadAcc_Phase4o_m1.csv
    TopLoadAcc_Phase4o_m5.csv
    TopLoadAcc_Phase4o_m10.csv
    TopLoadAcc_Phase4o_m50.csv
    TopLoadAcc_SW1_zero.csv
  experiments/
    AccInputSmoke/
    AccInputIsolation/
    FeedbackOperatorDiagnostics/
    TwoStageSmoke/
    RampSensitivity/
    DampingLadder/
    SmallLoadLadder/
    ShepardSmoke/
```

Future formal self-weight case should be added later as a new formal template, not mixed with diagnostics:

```text
examples/u-pw/01_1D_Consolidation/
  Case1DConsolidation_PR_SelfWeight_Def.xml
  xCase1DConsolidation_PR_SelfWeight_win64_CPU_debug.bat
```

---

## 8. Current `.gitignore` Assessment

Current `.gitignore` already covers:

```gitignore
examples/**/*_out/
examples/**/particles/
examples/**/data/
examples/**/*.out
examples/**/Run.csv
examples/**/Run.out
examples/**/*.vtk
examples/**/*.bi4
examples/**/*.nbi4
examples/**/*.csv
```

Issues:

1. `examples/**/*.csv` is too broad. It ignores generated `PartCsv_*.csv`, but also ignores input CSV files such as `TopLoadAcc_*.csv` and possible experimental validation CSV files.
2. It does not explicitly cover:
   - `examples/**/*.ibi4`
   - `examples/**/*.obi4`
   - `examples/**/*.dual.log`
   - `examples/**/*.gencase.log`
   - `examples/**/*.status.txt`
   - `examples/**/*.log` if desired
3. It does not cover backup XML suffixes such as:
   - `*.phase4*_backup*`
   - `*.backup*`

Recommended `.gitignore` revision, do not apply automatically yet:

```gitignore
# DualSPHysics generated output directories
examples/**/*_out/
examples/**/particles/
examples/**/data/

# DualSPHysics generated binary/data outputs
examples/**/PartCsv_*.csv
examples/**/Part_*.bi4
examples/**/PartExtra_*.bi4
examples/**/PartInfo.ibi4
examples/**/PartOut_*.obi4
examples/**/*.bi4
examples/**/*.nbi4
examples/**/*.ibi4
examples/**/*.obi4
examples/**/*.vtk
examples/**/Run.out
examples/**/Run.csv

# Run logs/status generated by Codex diagnostics
examples/**/*.dual.log
examples/**/*.gencase.log
examples/**/*.status.txt

# Temporary XML backups
examples/**/*.phase*_backup*
examples/**/*.backup*
```

Recommended change: remove or narrow `examples/**/*.csv` so input CSV files can be tracked intentionally. Use `examples/**/PartCsv_*.csv` for generated particle CSV output instead.

---

## 9. Recommended Execution Order

No command below should be run until explicitly approved.

1. Commit or stash current source changes first.
   - Current source has uncommitted SW-1 changes.
   - Resolve the tracked deletion `src/papers/u_pw_sph_implementation_notes.md` intentionally before broad cleanup.

2. Update `.gitignore` intentionally.
   - Narrow CSV ignore rule.
   - Add log, ibi4, obi4, status, and backup patterns.

3. Create archive/experiment folders.
   - Move useful diagnostic XML/BAT/CSV inputs into `experiments/` or `archive/`.
   - Do not move generated output directories.

4. Delete generated output directories and files.
   - Start with `examples/u-pw/01_1D_Consolidation/*_out/` after preserving any needed CSV summaries.
   - Then clean `examples/myf` diagnostic output directories.
   - Finally clean original case output directories if they are known reproducible.

5. Re-run `git status --short`.
   - Verify only intended templates/input files remain untracked.

6. Commit formal templates and README updates only.
   - Do not commit output directories or generated binary files.

---

## 10. Suggested Manual Review Checklist Before Deletion

- Confirm whether to keep any `PartCsv_*.csv` summaries for figures/tables.
- Confirm whether `TopLoadAcc_*.csv` should be tracked as input files.
- Confirm whether videos under `examples/myf` are desired documentation assets.
- Confirm whether restart-ready final `Part_0040.bi4` / `PartExtra_0040.bi4` should be archived outside Git before deletion.
- Confirm whether diagnostic logs are useful enough to archive as compressed text outside Git.

# Cleanup plan for examples/u-pw/01_1D_Consolidation

Generated: 2026-05-10 16:37:25

This is a read-only cleanup plan. No files were deleted, moved, or renamed while generating it.

## Current Inventory

Top-level directories: 27
- _out run directories: 19
- SW diagnostic/result directories: 7
- experiments directory: present

Top-level files: 63
- XML files: 21
- BAT files: 3
- CSV files: 2
- log files: 36

Tracked files under this case directory: 69

## A. Formal Case Templates And Lightweight Results To Keep

  - Case1DConsolidation_PR_Def.xml
  - xCase1DConsolidation_PR_win64_CPU_debug.bat
  - Case1DConsolidation_PR_SelfWeight_Scenario2_T3p6_Xi010_Def.xml
  - xCase1DConsolidation_PR_SelfWeight_Scenario2_T3p6_Xi010_win64_CPU_release.bat
  - SW3h_scenario2_T3p6_xi010/analyze_sw3h.py
  - SW3h_scenario2_T3p6_xi010/plot_sw3h_si.py
  - SW3h_scenario2_T3p6_xi010/sw3h_case_summary.csv
  - SW3h_scenario2_T3p6_xi010/sw3h_frame_metrics.csv
  - SW3h_scenario2_T3p6_xi010/figures/*.svg

Curated tracked experiment template folders to keep unless manually retired:
  - experiments/AccInputSmoke/
  - experiments/AccInputIsolation/
  - experiments/DampingLadder/
  - experiments/FeedbackOperatorDiagnostics/
  - experiments/RampSensitivity/
  - experiments/ShepardSmoke/
  - experiments/SmallLoadLadder/
  - experiments/TwoStageSmoke/

Possible additional formal templates to keep if SW-2/SW-3 setup is still actively used:
  - Case1DConsolidation_PR_SelfWeight_Def.xml
  - xCase1DConsolidation_PR_SelfWeight_win64_CPU_debug.bat
  - Case1DConsolidation_PR_SelfWeight_Scenario2_Def.xml

## B. Exploratory Files Recommended For experiments/archive

Recommended target: experiments/SelfWeightDevelopment/ or subfolders below it.

Top-level SW-2/SW-2b XML and summary CSV files:
  - Case1DConsolidation_PR_SW2B_T0p001_D10_Def.xml
  - Case1DConsolidation_PR_SW2B_T0p001_D50_Def.xml
  - Case1DConsolidation_PR_SW2B_T0p001_D85_Def.xml
  - Case1DConsolidation_PR_SW2B_T0p002_D10_Def.xml
  - Case1DConsolidation_PR_SW2B_T0p002_D50_Def.xml
  - Case1DConsolidation_PR_SW2B_T0p002_D85_Def.xml
  - Case1DConsolidation_PR_SW2B_T0p005_D10_Def.xml
  - Case1DConsolidation_PR_SW2B_T0p005_D50_Def.xml
  - Case1DConsolidation_PR_SW2B_T0p005_D85_Def.xml
  - Case1DConsolidation_PR_SW2_T001_D0p07_Def.xml
  - Case1DConsolidation_PR_SW2_T001_D10_Def.xml
  - Case1DConsolidation_PR_SW2_T001_D1_Def.xml
  - Case1DConsolidation_PR_SW2_T001_D50_Def.xml
  - Case1DConsolidation_PR_SW2_T001_D85_Def.xml
  - Case1DConsolidation_PR_SW2_T005_D0p07_Def.xml
  - Case1DConsolidation_PR_SW2_T005_D85_Def.xml
  - Case1DConsolidation_PR_SW2_analysis_summary.csv
  - Case1DConsolidation_PR_SW2_T001_analysis.csv

Top-level short Scenario 2 XML files:
  - Case1DConsolidation_PR_SelfWeight_Scenario2_Def.xml
  - Case1DConsolidation_PR_SelfWeight_Scenario2_T0p02_Def.xml

SW diagnostic/result directories to archive after trimming heavy outputs:
  - SW2c_sweep_runs
  - SW3b_sensitivity_runs
  - SW3c_extended_runs
  - SW3d_extended_runs
  - SW3f_dt_safety_runs
  - SW3g_longrun_safety020
  - SW3h_scenario2_T3p6_xi010

Recommended treatment for these SW directories:
  - Keep summary CSVs, analysis scripts, and small figures.
  - Delete nested _out/, data/, vtk_particles/, PartCsv_*.csv, Part_*.bi4, and VTK outputs.
  - Optionally move each directory under experiments/SelfWeightDevelopment/ after trimming heavy outputs.

## C. Generated Outputs Safe To Delete After Summaries Are Preserved

Top-level generated output directories:
  - Case1DConsolidation_PR_out
  - Case1DConsolidation_PR_SelfWeight_Scenario2_out
  - Case1DConsolidation_PR_SelfWeight_Scenario2_T0p02_out
  - Case1DConsolidation_PR_SW2B_T0p001_D10_out
  - Case1DConsolidation_PR_SW2B_T0p001_D50_out
  - Case1DConsolidation_PR_SW2B_T0p001_D85_out
  - Case1DConsolidation_PR_SW2B_T0p002_D10_out
  - Case1DConsolidation_PR_SW2B_T0p002_D50_out
  - Case1DConsolidation_PR_SW2B_T0p002_D85_out
  - Case1DConsolidation_PR_SW2B_T0p005_D10_out
  - Case1DConsolidation_PR_SW2B_T0p005_D50_out
  - Case1DConsolidation_PR_SW2B_T0p005_D85_out
  - Case1DConsolidation_PR_SW2_T001_D0p07_out
  - Case1DConsolidation_PR_SW2_T001_D10_out
  - Case1DConsolidation_PR_SW2_T001_D1_out
  - Case1DConsolidation_PR_SW2_T001_D50_out
  - Case1DConsolidation_PR_SW2_T001_D85_out
  - Case1DConsolidation_PR_SW2_T005_D0p07_out
  - Case1DConsolidation_PR_SW2_T005_D85_out

Generated top-level logs from exploratory runs:
  - Case1DConsolidation_PR_SelfWeight_Scenario2_dual.console.log
  - Case1DConsolidation_PR_SelfWeight_Scenario2_gencase.console.log
  - Case1DConsolidation_PR_SelfWeight_Scenario2_T0p02_dual.console.log
  - Case1DConsolidation_PR_SelfWeight_Scenario2_T0p02_gencase.console.log
  - Case1DConsolidation_PR_SW2B_T0p001_D10_dual.console.log
  - Case1DConsolidation_PR_SW2B_T0p001_D10_gencase.console.log
  - Case1DConsolidation_PR_SW2B_T0p001_D50_dual.console.log
  - Case1DConsolidation_PR_SW2B_T0p001_D50_gencase.console.log
  - Case1DConsolidation_PR_SW2B_T0p001_D85_dual.console.log
  - Case1DConsolidation_PR_SW2B_T0p001_D85_gencase.console.log
  - Case1DConsolidation_PR_SW2B_T0p002_D10_dual.console.log
  - Case1DConsolidation_PR_SW2B_T0p002_D10_gencase.console.log
  - Case1DConsolidation_PR_SW2B_T0p002_D50_dual.console.log
  - Case1DConsolidation_PR_SW2B_T0p002_D50_gencase.console.log
  - Case1DConsolidation_PR_SW2B_T0p002_D85_dual.console.log
  - Case1DConsolidation_PR_SW2B_T0p002_D85_gencase.console.log
  - Case1DConsolidation_PR_SW2B_T0p005_D10_dual.console.log
  - Case1DConsolidation_PR_SW2B_T0p005_D10_gencase.console.log
  - Case1DConsolidation_PR_SW2B_T0p005_D50_dual.console.log
  - Case1DConsolidation_PR_SW2B_T0p005_D50_gencase.console.log
  - Case1DConsolidation_PR_SW2B_T0p005_D85_dual.console.log
  - Case1DConsolidation_PR_SW2B_T0p005_D85_gencase.console.log
  - Case1DConsolidation_PR_SW2_T001_D0p07_dual.console.log
  - Case1DConsolidation_PR_SW2_T001_D0p07_gencase.console.log
  - Case1DConsolidation_PR_SW2_T001_D10_dual.console.log
  - Case1DConsolidation_PR_SW2_T001_D10_gencase.console.log
  - Case1DConsolidation_PR_SW2_T001_D1_dual.console.log
  - Case1DConsolidation_PR_SW2_T001_D1_gencase.console.log
  - Case1DConsolidation_PR_SW2_T001_D50_dual.console.log
  - Case1DConsolidation_PR_SW2_T001_D50_gencase.console.log
  - Case1DConsolidation_PR_SW2_T001_D85_dual.console.log
  - Case1DConsolidation_PR_SW2_T001_D85_gencase.console.log
  - Case1DConsolidation_PR_SW2_T005_D0p07_dual.console.log
  - Case1DConsolidation_PR_SW2_T005_D0p07_gencase.console.log
  - Case1DConsolidation_PR_SW2_T005_D85_dual.console.log
  - Case1DConsolidation_PR_SW2_T005_D85_gencase.console.log

Generated output patterns to delete recursively wherever found in this case directory:
  - *_out/
  - data/
  - PartCsv_*.csv
  - Part_*.bi4
  - PartExtra_*.bi4
  - PartInfo.ibi4
  - PartOut_*.obi4
  - Part_Head.ibi4
  - *.vtk
  - *.nbi4
  - *.ibi4
  - *.obi4
  - *.dual.log
  - *.gencase.log
  - *.console.log
  - *.status.txt
  - Run.out
  - Run.csv
  - monitor_sw3h.log
  - monitor_sw3h.ps1

Important: do not delete summary CSVs such as sw3h_frame_metrics.csv, sw3h_case_summary.csv, sw3b_case_summary.csv, etc. before deciding whether they should be archived.

## D. Uncertain / Needs Human Confirmation

  - Any TopLoadAcc_*.csv or other AccInput history CSV.
  - Any manually curated *_summary.csv or *_analysis.csv.
  - analyze_*.py, plot_*.py, or other analysis scripts.
  - SVG figures under figures/.
  - Case1DConsolidation_PR_SelfWeight_Def.xml and Case1DConsolidation_PR_SelfWeight_Scenario2_Def.xml until the final formal self-weight workflow is decided.
  - Any XML/BAT under experiments/ that may still reproduce an important diagnostic.

Top-level CSV files requiring review:
  - Case1DConsolidation_PR_SW2_analysis_summary.csv
  - Case1DConsolidation_PR_SW2_T001_analysis.csv

## Recommended Final Structure

  - Case1DConsolidation_PR_Def.xml
  - xCase1DConsolidation_PR_win64_CPU_debug.bat
  - Case1DConsolidation_PR_SelfWeight_Scenario2_T3p6_Xi010_Def.xml
  - xCase1DConsolidation_PR_SelfWeight_Scenario2_T3p6_Xi010_win64_CPU_release.bat
  - SW3h_scenario2_T3p6_xi010/analyze_sw3h.py
  - SW3h_scenario2_T3p6_xi010/plot_sw3h_si.py
  - SW3h_scenario2_T3p6_xi010/sw3h_case_summary.csv
  - SW3h_scenario2_T3p6_xi010/sw3h_frame_metrics.csv
  - SW3h_scenario2_T3p6_xi010/figures/*.svg
  - experiments/SelfWeightDevelopment/SW2c_sweep_runs/
  - experiments/SelfWeightDevelopment/SW3b_sensitivity_runs/
  - experiments/SelfWeightDevelopment/SW3c_extended_runs/
  - experiments/SelfWeightDevelopment/SW3d_extended_runs/
  - experiments/SelfWeightDevelopment/SW3f_dt_safety_runs/
  - experiments/SelfWeightDevelopment/SW3g_longrun_safety020/

## Recommended Execution Order

  - Confirm this plan manually.
  - Preserve/copy summary CSVs and scripts from SW2c, SW3b, SW3c, SW3d, SW3f, and SW3g if they are still needed.
  - Move exploratory top-level XML/logical templates into experiments/SelfWeightDevelopment/.
  - Delete generated _out/ directories at the top level.
  - Delete nested generated output under SW*/ directories, keeping only summary CSV, scripts, and figures.
  - Run git status --short and verify that only intended XML/BAT/CSV/PY/SVG inputs remain.
  - Commit the cleaned example organization separately from source changes.

# M3d MCC Feedback-Off Refinement

CPU-only extended feedback-off cases for the first SPH Modified Cam Clay
stress-update branch. The workflow reuses the explicit platen and lateral
flexible confinement setup, keeps `PorePressureFeedback=0`, and enables MCC
state output plus pairwise platen reaction diagnostics.

Run `python make_m3d_cases.py` to regenerate XML/BAT files, then run the two
`xRun_*_win64_CPU_release.bat` launchers. Run
`python analyze_m3d_mcc_feedback_off_refinement.py` after the CPU runs.

# M3c MCC Stress Update CPU

CPU-only smoke cases for the first SPH Modified Cam Clay stress-update branch.
The workflow reuses the explicit platen and lateral flexible confinement setup
from T5b, keeps `PorePressureFeedback=0`, and enables MCC state output plus
pairwise platen reaction diagnostics.

Run `python make_m3c_cases.py` to regenerate XML/BAT files.

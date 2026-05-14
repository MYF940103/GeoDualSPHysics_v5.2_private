# M3m Refined Platen / Edge Geometry

CPU-only, feedback-off MCC dense diagnostics for refined platen/specimen
interface and edge-corner geometry.  These cases do not modify the MCC return
mapping, PR pressure update, or FlexibleConfiningStress physics.

Generate cases with:

```powershell
py .\make_m3m_cases.py
```

Run the generated `xRun_*_win64_CPU_release.bat` files from this directory,
then postprocess with:

```powershell
py .\analyze_m3m_refined_platen_edge_geometry.py
```

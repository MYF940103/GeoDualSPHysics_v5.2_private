# Shared basic material regression tools

Use the single helper implementation in `../../../10_StaticDrySoilColumn/tests/support/` from the repository root:

```powershell
D:/Anaconda3/python.exe -X utf8 -B examples/Elastoplastic_basic/10_StaticDrySoilColumn/tests/support/basic_material_r1.py run collapse short old
```

The same owner supports `short|full`, `old|new`, and refuses existing run output/evidence. `prepare collapse` was already executed once and must not be repeated. Native reading uses `basic_native_r2_run.py collapse WINDOW MODE`; offline comparison uses `basic_material_review_r1.py collapse WINDOW`. Each action requires the preceding actual closed receipt; the owner never decodes or launches a next solver automatically. Current execution remains controlled sequentially by the agent/root authorization, not by this README.

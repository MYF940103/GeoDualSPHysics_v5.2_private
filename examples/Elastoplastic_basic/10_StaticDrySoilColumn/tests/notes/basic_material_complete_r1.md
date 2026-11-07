# Completed real basic-case old/new comparison

Eight authorized CPU1/stable/mDBC NoSlip spatial runs completed once each: Case10 short0.5/full5s and Case12 a=1 short0.1/full1s, old frozen ReleaseCPU_r2 versus new frozen ReleaseCPU_r3. Every original Popen/Win32 exit was0, with complete native IDs, finite exported fields, positive density/nonnegative kappa, unchanged fixed geometry/velocity and no particle exclusion. Formal inputs/retained outputs, production source and H frozen dependencies were untouched. No GPU, SHA scan, physical retry or extra half/reference run was used. The setup-only missing-runtime failure and native-reader r1 compile failure remain preserved; their repairs did not repeat any physical target.

| actual case/window | old/new updates | old/new frames | final max kappa old/new | max nearest-time stress Frobenius RMS gap (Pa) | max nearest-time XYZ position RMS gap (m) |
|---|---:|---:|---:|---:|---:|
| column short | 6803/6803 | 6/6 | 0.0002555416722 / 0.000255541614 | 0.0041186923 | 6.9090494e-09 |
| column full | 68090/68090 | 51/51 | 0.0003991848498 / 0.0003356934176 | 0.010720947 | 2.1375155e-08 |
| collapse short | 8564/8564 | 11/11 | 3.023812532 / 2.955853939 | 0.0042290451 | 5.9164539e-09 |
| collapse full | 85608/85608 | 101/101 | 12.59802055 / 12.54063034 | 1.553785 | 4.3086862e-05 |

All initial14 exported physical scalars match bit patterns. Every frame uses native double SigmaState stress; positions were saved float32 and exactly expanded for arithmetic. Offdiagonal order is xy,yz,xz. Adaptive saved clocks differ, so noncoincident-time differences are explicitly descriptive, with both actual times/gaps in the CSV; no interpolation, borrowed5Pa/.005mm gate or all22-array equivalence claim is made. Actual elapsed times are shared-machine observations, not a benchmark.

Case10 full sigma_zz relative L2 against the retained H=1/current-z reference is0.0043277841(old)/0.0043279064(new). Final kappa maximum decreases15.905271%, despite close stress/motion. `basic_material_kappa_r1.md` and its separate figure/CSV localize the top-ID history offset to the first available noninitial save0.100071s. The old basic law already uses a deviatoric history norm. Its later cap/final stress scaling does not revise its earlier history; the new apex-tip/repair history differs, but the actual unrecorded startup branch cannot be proven from saved compressive states. A smaller residual alone does not prove a physically more accurate history. Constant material coefficients here do not depend on kappa; this does not establish equivalence under softening.

Case12 full native end times are1.0000017528966658(old) and1.0000018624807263(new); maximum nearest-state time gap is1.15863760364e-7s. Both retain all2500soil/2028fixed IDs and101frames. Final kappa maxima12.59802055/12.54063034 differ by-0.45555%. The all-particle contours, stress and velocity curves nearly overlay; the real history difference remains visible. Final same-original-material measurements (old/new):

- mean settlement: 25.8136231405 / 25.8137450246 mm.
- initial-top material settlement: 67.1355061792 / 67.1357090026 mm.
- initial-bottom material settlement: -0.0118521857075 / -0.0118549866602 mm.
- x maximum: 325.917512178 / 325.928032398 mm.
- stress Frobenius RMS: 795.826251745 / 795.820992552 Pa.
- velocity XYZ RMS: 0.00024607769804 / 0.000247742247436 m/s.

Case12 new particles were exported once by official PartVTK5.0.206 for short11frames and full101frames, all2500soil points each. Full series: `../../../12_GranularColumnCollapse/tests/outputs/basic_material_full_new_CPU_r1/particles/PartFluid_0000.vtk` through0100. Use the actual path in the JSON receipt when opening from outside this note. It includes native double SigmaState_kk/ij, float display stress, Kplastic, Vel, Rhop and Press plus IDs/MK and positions. `Press` is dry WCSPH EOS pressure, NOT pore-water pressure. The run-local particles README lists actual declarations; original BI4/native exports are unchanged.

Per-case PNGs have matching complete history/final-per-ID/difference CSVs. Each PNG was visually inspected, including the full Case12 figure. Original review `visual_QA_pending:true` remains immutable; separate `.visual_qa.json` records actual viewing. These observations support bounded default-basic compatibility with explicitly different history; they are not general spatial convergence, exact apex branch proof, softening equivalence,3D public admission or Verlet irreversibility acceptance. RawBI4/BIN/exe/VTK remain local; the selective Git manifest includes reproducible sources/configs, readable evidence and necessary PNG/CSV only.

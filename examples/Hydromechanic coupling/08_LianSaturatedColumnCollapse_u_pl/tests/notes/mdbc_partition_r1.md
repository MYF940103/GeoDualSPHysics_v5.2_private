# mDBC implementation partition and hydraulic-wall admission

This stage follows the unified material return at `d3c743b` and the u-pl operator-scope note at `6912e82`. It has two distinct purposes: move the existing boundary implementations into readable modules, and reject hydromechanical wall inputs that select cDBC. Build and runtime receipts determine validation status; this note is not a physical acceptance record.

## Source organization

- `src/source/JSphCpu_mdbc.cpp`: the original boundary MLS helper, pore-pressure extrapolation, SPR velocity reconstruction, traditional mDBC/cDBC, dynamic-wall state/matrix/acceleration and fixed-plane SPR initialization.
- `src/source/JSphGpu_mdbc.cpp`: the corresponding host dispatch and initialization.
- `src/source/JSphGpu_mdbc_ker.cuh`: the corresponding device code, included inside the original `cusph` namespace in `JSphGpu_ker.cu`. It uses the same CUDA translation unit and device constants; it is not separately compiled and introduces no RDC requirement.
- The two authoritative VS projects and their filters list the new modules. The extracted initialization functions are called at their original position. Free-surface tracking, Darcy rates, time integration, load application and Shepard regularization remain in their original modules.

The pure-move checks in `tests/outputs/mdbc_partition_cpu_base_r1/partition.check.json` and `tests/outputs/mdbc_partition_gpu_base_r1/review.json` compare the moved bodies with the captured originals. The CPU check covers 16 function bodies (57045 body bytes), three full comment/code blocks and the original 81-line SPR initialization. The GPU check covers six exact moved blocks. These checks precede the separate admission change below and do not by themselves establish compiled-program equivalence.

## Hydraulic walls and no-wall bodies

`JSph::LoadConfig` checks the final XML/command-line boundary selection. A hydromechanical case with physical walls must select mDBC. An actual call to either CPU or GPU `CdbcBoundCorrection` also rejects hydromechanics before any empty-boundary early return.

Cryer uses remote fixed markers rather than a physical mirror wall. Simply enabling mDBC would not supply valid wall normals. The internal `HydroMechNoWall` state therefore bypasses cDBC only for an empty wall registry or a narrowly admitted isolated body. It is not an XML switch and is not selected by the case name or a hardcoded marker count. The isolated-body admission retains the existing checks on fixed/fluid identity, initial rest state, geometry and strict marker-to-soil separation. Dynamic free bodies retain their existing per-update enclosure guard. Static no-wall bodies additionally query the current marker/fluid kernel support before forces and reject contact; the query writes no particle fields.

This changes rejection/dispatch behavior for unsupported hydraulic cDBC inputs. It does not add a hydraulic cDBC formulation or change the accepted mDBC equations, interpolation, slip conditions, gradients or integration order. Dry cDBC remains available.

## Verification scope

Use isolated `mdbc_partition_*_r1` programs, preserving canonical binaries and the frozen server-r2 package. Required checks are the authoritative CPU Debug build, other affected build configurations, representative old/new boundary component outputs, actual same-configuration mDBC native outputs, a real cDBC hydraulic-wall rejection, and the static/dynamic no-wall Cryer paths. A no-wall check is not evidence for hydraulic cDBC support.

The separate basic-elastoplastic comparisons live under each `examples/Elastoplastic_basic` case. They compare the earlier and unified material algorithms and may differ physically. They must not be confused with the strict same-algorithm checks used for this source partition.

No formal case inputs/results or server jobs are changed by this stage. Generic PART restart, inclined NoPen, moving/curved-wall and general large-rotation acceptance are outside this partition. Porous-pressure and external-load module reorganization remains deferred until after the u-pl development work.

## Completed implementation checks, 2026-11-07

All four isolated authoritative builds passed: DebugCPU/ReleaseCPU each produced 87 project objects; Debug/Release each produced 113. There were no compiler errors. Debug retained third-party missing-PDB linker warnings; Release retained one warning. Canonical programs and the server-r2 package remained unchanged during the builds.

`logs/mdbc_partition_components_review_r1.json` closes 15 actual component cases: eight CPU and seven GPU, covering 2D/3D, all three legacy slip modes, multiple planes, Wendland/Cubic, mixed slip and the dynamic-wall state/matrix/acceleration stages. All 41 same-backend Debug CSV files (129484 data rows) are byte-identical to their retained controls. The single GPU wall memcheck reports zero errors and leaks.

`logs/mdbc_admission_r2.check.json` closes the actual-program regressions. The real case02 hydraulic-wall input with `-dbc` exits with the new hydraulic-wall error before saving particles. Twelve positive jobs and their independent native reads passed. Eight same-configuration comparisons cover case08 mDBC (22 frames per backend), periodic plastic soil without walls (five), and static/dynamic Cryer (three each). All 1410 typed-array pairs and 66 actual clock/signed-dterror pairs are bit-identical; pressure RMS and material XYZ differences are zero. These are implementation-continuity checks, not new full-cycle physical acceptance or a performance benchmark.

Earlier tool failures are preserved: the first reader used a class name as a namespace; component preparation assumed a normals file that the original XML already generated; one historical GPU exit-field schema was misread; and the first process preflight tried to resolve an unrelated named pipe. Corrected tools use new tags, reuse completed helpers, and do not rerun a completed physical result or relax a numerical comparison.

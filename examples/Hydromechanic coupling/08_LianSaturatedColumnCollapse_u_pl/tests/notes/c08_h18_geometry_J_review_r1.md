# C08 material-grid geometry versus J: CSV-only diagnostic

Author-only new files are support/c08_h18_geometry_J_review_r1.py and this note. No script/import, native read, solver/probe, build, GPU, Git or SHA is executed during authoring. Root must read both before one offline invocation. No existing file or physical state is changed.

Inputs are only the passed global_modes_r1 component check, passed global_modes_review_r1 check and the component's stat-bound mode_fields.csv/soil.csv. The script streams each CSV once. It extracts the unique altX_Uz rows at Parts38/76/92/300 (4x5000); it uses their actual coordinates and initial material ix/iz, not the virtual velocity u. That phase was already reconstructed from true initial positions by the admitted component. It is not inferred from ID ordering. No full ABI/native/signed-clock qualification is repeated.

## Geometry definitions and limits

The initial phase is100x50 with nominal dX=dZ=.04m. This script does not reread or reconstruct exact initial Posd float bits. Ratios use the declared nominal cell area .0016m2; tiny initial-coordinate generation roundoff is not a geometric error gate. Native J is referenced to the original pre-gravity state, so it is compared directly, not reset to PRE or divided by J_PRE.

Every original four-particle logical cell is ordered A(i,j),B(i+1,j),C(i+1,j+1),D(i,j+1). Signed area is the sum of triangles ABC and ACD divided by dp2. Both diagonal decompositions are retained: ABC/ACD and ABD/BCD. Each signed triangle ratio uses .5dp2, giving the same ratio as a uniform affine cell. All negative/zero values and diagonal-sum roundoff remain. A concave or self-crossing quadrilateral can have cancellation; one diagonal's triangle sign does not independently prove a physical element inversion. These are material-neighbor descriptors in a meshless method, not an added finite-element mesh.

Each cell's area ratio is compared with arithmetic mean native J of its four corners. Full and all-four-corners-no-fixed-neighbor cohorts are distinct. The no_fixed flag is the original conservative current support classification; no wall/donor is removed by this diagnostic.

For logical interior nodes only, centered four-neighbor coordinate differences form F=[(x(i+1,j)-x(i-1,j))/(2dp), (x(i,j+1)-x(i,j-1))/(2dp)] in xz. detF is compared with that node's native J. There are4704 such nodes/state. No one-sided boundary fallback, regularizer or fitted radius is introduced. The node no-fixed cohort requires its receiver flag, whereas the cell cohort requires all four corner flags; neither claims a closed wall response.

Four fixed material IDs4953/4954/6767/6865 retain their3x3 logical neighborhoods and available centered F. For pairs4953/4954 and6767/6865, the nominal initial vector is dp times the actual phase-index difference. The affine shadow is .5*(F_A+F_B)*dX. The CSV records actual/predicted lengths, vector residual, signed length residual and both detF/J. This shadow may cross shear discontinuities, rotations or newly adjacent particles, so disagreement alone is not a J bug, zero-energy proof or physical tensile instability.

## Descriptive outputs

Only two scientific figures are prepared:

- _cells.png: all four actual saved geometries, signed area ratio and area-ratio minus mean-J maps. Row color scales are common over all states and preserve extrema; black x marks negative total signed area. No spatial smoothing/interpolation or clipping.
- _comparison.png: area/J and centered-detF/J scatters, four-state RMS differences with the stated cohorts, two pair measured/affine lengths and residuals, and the four fixed materials. Lines connect only four actual samples; no intervening onset or trajectory is inferred.

Small matching CSVs in tests/figures share prefix c08_h18_geometry_J_review_r1: summary (16 cohort/family rows), extremes (top8 by absolute area-minus-J plus minimum signed cell/triangle per state), focus_neighbors (up to144 rows) and pairs (8 rows). The extreme ranking is descriptive, not an acceptance threshold. Original corner IDs and logical indices are retained.

The full19404-cell table is local tests/outputs/c08_h18_geometry_J_review_r1_quads.csv. It is reproducible and need not be added to cloud Git. Input CSVs and scripts fully define the centered-coordinate scatter without another native extraction. The check JSON includes actual counts, summary/extreme/pair descriptors, stat bindings and visual_QA_pending=true. Native J/n/k/mass are never altered.

Run only after root full review/admission:
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_geometry_J_review_r1.py --execution-authorized

Current/partial outputs are protected. Failure preserves the first exception and fresh derived artifacts. No physical threshold, J reset, state remap, true-mass claim, cap change or subsequent solver/other-psi admission follows. Shape/area mismatch can result from finite-stencil smoothing, genuine localization, nonaffinity or contact staging; its cause must be interpreted with the existing force/material evidence.

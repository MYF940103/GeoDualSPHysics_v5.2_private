# Saved-wall constant and affine consistency probe

Only this note and `tests/support/c08_h18_wall_affine_probe_r1.py` are added.
The author does not execute the probe, solver, reader, build or Git. Root reads
the whole script before one offline invocation:

```text
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_wall_affine_probe_r1.py --execution-authorized
```

The source is the already validated AS.3 failed90 `native_partial_r1` typed22
export and bound `c08_h18_wend_a03_partial_review_r1_wall_support_replay.csv`.
The failed whole run remains failed. Only stat identities are checked; no SHA
scan or BI4 decoding is introduced. Six distinct actual saved stencils are
selected deterministically: first/middle/last eligible wall893 and front-wall
records. Each has physical-B double-support, failed primary mirror geometry,
and a successful existing nearest-source or offline centroid fit. The last
saved wall893 is mandatory. This does not reproduce its later unsaved rejection.

The original pure `fit` function is imported, not copied or edited. It retains
actual positive native J volume weights, float Wendland kernel evaluation,
double moments, original `.001` determinant limit, nearest-value anchoring and
centre-to-original-mirror translation. Existing primary, nearest and centroid
centres are read literally from the bound replay CSV. All replayed determinants
and geometry flags must equal that prior saved-state replay; this is an artifact
identity check, not a new physical acceptance threshold.

Eleven components are assigned distinct manufactured constants and affine
fields. These are dimensionless property tests, not replacements of the native
physical fields. With original target G and real source position xj, component c
uses `fc(xj)=cc + bxc*(xj-G)x + bzc*(xj-G)z`; exact target value is `cc`.
For a fit centre C, the existing signed-gradient convention returns
`fc(x_near) - qx*(C-x_near)x - qz*(C-x_near)z + qx*(C-G)x + qz*(C-G)z`.
Thus a consistent affine fit returns the original G value even when C changes.
The constant test uses zero slopes. Tests cover J, head-removed pressure, XYZ
velocity and all six stress component slots; actual native J remains the weight.

New shallow outputs are `tests/figures/c08_h18_wall_affine_probe_r1.csv` and
`tests/logs/c08_h18_wall_affine_probe_r1.check.json`. They preserve every field's
signed/absolute/relative target error and descriptive raw moment condition,
support size, determinant, actual clock and method. Geometrically failed primary
fits retain null target/error entries rather than invented values. No new error
or condition gate is added, and roundoff-sized errors must not be described as
proof of stable contact, conservation, full physical accuracy or an unsaved-stage
repair. CUDA cell traversal, packed PosCell and FMA order are not reproduced.
No active program, PRE, configuration, wall operator or existing output changes.

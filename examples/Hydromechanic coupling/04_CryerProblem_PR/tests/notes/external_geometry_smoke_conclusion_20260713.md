# Cryer external geometry smoke test conclusion, 2026-07-13

Purpose: check whether an externally generated smooth sphere could replace the
native Cryer particle construction before investing more time in this route.

## Temporary test scope

The temporary smoke-test files were created under `tests` only:

- `tests/support/generate_external_cryer_sphere.py`
- `tests/geometry/external/`
- `tests/configs/external_geometry_smoke/`
- `tests/logs/external_geometry_smoke/`
- `tests/outputs/external_geometry_smoke/`

They were removed after recording this conclusion, because this route is not
being pursued for now.

## Setup

- Working directory: `04_CryerProblem_PR/tests`.
- Sphere radius: `R = 0.05 m`.
- Particle spacing target: `dp = 0.0025 m`.
- Tested formats:
  - ASCII STL surface mesh with `drawfilestl`.
  - ASCII VTK point cloud with `drawfilevtk` and `polyselec=points`.

## Observations

The STL import ran successfully, but it did not produce a filled Cryer sphere.
The generated fluid set had `18916` particles with radius range approximately
`0.05` to `0.07237 m`, so it behaved like a surface or offset shell rather than
a volumetric particle model.

The VTK point-cloud import also ran successfully, but GenCase did not preserve
the external point cloud directly. The input point cloud had `33510` points,
whereas the generated fluid set had `25238` particles. The output nearest
neighbor distance was very regular and close to `dp`, indicating that GenCase
filtered or regularized the imported points.

The raw generated point cloud was volumetrically distributed, but not yet a
final SPH-quality glass or Poisson-disk cloud: the nearest-neighbor coefficient
of variation was about `0.24`, with a very small minimum spacing.

## Conclusion

The external-geometry route is not a good next step for the Cryer peak-accuracy
problem. The STL route is unsuitable for a filled volume in the tested form, and
the VTK point route would require extra work to control or bypass GenCase
resampling. For now, do not continue with external STL/point-cloud modeling.

The next Cryer work should stay with the existing native case setup and focus on
the pressure-loading, drainage timing, particle-quality diagnostics already
available from the current benchmark workflow.

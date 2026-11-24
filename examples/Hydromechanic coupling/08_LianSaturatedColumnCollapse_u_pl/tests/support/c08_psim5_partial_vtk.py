"""Export and verify the 68 saved frames of the failed formal C08 -5 degree release."""
from pathlib import Path
import json
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "support"))
import postprocess_lian_release as post

RUN = ROOT / "CaseLianCollapse_psim5_GPU_out"
PRE = ROOT / "CaseLianCollapse_psim5_pre_GPU_out"
DEST = RUN / "validation_partial" / "particles"
RECEIPT = ROOT / "tests/logs/c08_psim5_partial_vtk.json"
FLUID_FIELDS = ("Idp", "Vel", "PorePress", "PorePress0", "ExcessPorePress", "Kplastic",
                "SigmaState_kk", "SigmaState_ij", "PoroVolumeRatio", "PoroPorosity",
                "PoroHydraulicConductivity", "PoroMixtureDensity", "FSType")
VTK_TYPE = {"f8": "double", "f4": "float", "u4": "unsigned_int"}
NAMES = ("PartFluid", "PartBound")


def verify_vtk(path, pos, fields):
    """Compare VTK geometry, connectivity, field names, tuple types and bytes to native values."""
    with path.open("rb") as f:
        def line(expected):
            post.require(f.readline().rstrip(b"\r\n") == expected.encode("ascii"),
                         f"{path}: expected {expected}")

        def payload(a):
            expected = a.astype(a.dtype.newbyteorder(">"), copy=False).tobytes()
            post.require(f.read(len(expected)) == expected and f.read(1) == b"\n",
                         f"{path}: binary payload differs")

        line("# vtk DataFile Version 3.0")
        line("C08 saved material particles; SI units")
        line("BINARY")
        line("DATASET POLYDATA")
        n = len(pos)
        line(f"POINTS {n} double")
        payload(pos)
        line(f"VERTICES {n} {2*n}")
        payload(np.column_stack((np.ones(n, dtype="i4"), np.arange(n, dtype="i4"))))
        line(f"POINT_DATA {n}")
        line(f"FIELD FieldData {len(fields)}")
        for key, a in fields.items():
            count = 1 if a.ndim == 1 else a.shape[1]
            line(f"{key} {count} {n} {VTK_TYPE[a.dtype.str[1:]]}")
            payload(a)
        post.require(not f.read(1), f"{path}: unexpected trailing data")


def main():
    provenance = json.loads((RUN / "provenance.json").read_text(encoding="utf-8-sig"))
    log = (RUN / "Run.out").read_text(errors="replace")
    post.require((provenance["group"], provenance["stage"], provenance["state"]) ==
                 ("psim5", "collapse", "failed") and "Finished execution (code=1)." in log,
                 "This export is scoped to the failed formal -5 degree release")
    files = sorted((RUN / "data").glob("Part_*.bi4"))
    post.require([f.name for f in files] == [f"Part_{i:04d}.bi4" for i in range(68)],
                 "The retained 0000-0067 snapshot inventory has changed")
    reference = PRE / "data/Part_1000.bi4"
    meta0, initial = post.native(reference)
    post.verify_source_material(meta0, "psim5")
    post.require(np.array_equal(initial["Idp"], post.PRE_IDS), "PRE material registry differs")
    origin = float(meta0["TimeStep"])
    prev_kappa = initial["Kplastic"][post.SOIL_IDS]
    for name in NAMES:
        (DEST / name).mkdir(parents=True, exist_ok=True)
    clocks = []
    sizes = {name: 0 for name in NAMES}
    for i, path in enumerate(files):
        meta, a = post.native(path)
        prev_kappa = post.check_frame(meta, a, i, False, initial, prev_kappa, origin, "psim5")
        time = float(meta["TimeStep"])
        post.require(time > (clocks[-1] if clocks else origin), f"Clock order at {path}")
        clocks.append(time)
        soil = slice(-len(post.SOIL_IDS), None)
        fixed = slice(None, -len(post.SOIL_IDS))
        fluid_fields = {k: a[k][soil] for k in FLUID_FIELDS}
        fluid_fields["Displacement"] = a["Posd"][soil] - initial["Posd"][post.SOIL_IDS]
        ids = a["Idp"][fixed]
        bound_fields = {"Idp": ids, "MkBound": np.searchsorted([255, 1805], ids, side="right").astype("u4")}
        for name, subset, fields in (("PartFluid", soil, fluid_fields), ("PartBound", fixed, bound_fields)):
            vtk = DEST / name / f"{name}_{i:04d}.vtk"
            if not vtk.exists():
                post.vtk_particles(vtk, a["Posd"][subset], fields)
            verify_vtk(vtk, a["Posd"][subset], fields)
            sizes[name] += vtk.stat().st_size

    series_paths = {}
    for name in NAMES:
        directory = DEST / name
        expected = [{"name": f"{name}_{i:04d}.vtk", "time": t} for i, t in enumerate(clocks)]
        post.require(sorted(f.name for f in directory.glob("*.vtk")) == [item["name"] for item in expected],
                     f"{directory}: unexpected frame inventory")
        series = directory / f"{name}.vtk.series"
        if not series.exists():
            post.make_series(directory, name, clocks)
        post.require(json.loads(series.read_text()) == {"file-series-version": "1.0", "files": expected},
                     f"VTK collection differs: {series}")
        series_paths[name] = series.relative_to(ROOT).as_posix()
    receipt = {"solver_state": "failed", "solver_exit_code": 1, "group": "psim5",
               "stage": "partial collapse", "frames_per_series": len(files), "planned_frames": 301,
               "physical_acceptance": False, "first_part": 0, "last_part": len(files)-1,
               "preload_reference": reference.relative_to(ROOT).as_posix(), "time_origin_s": origin,
               "first_time_s": clocks[0], "last_time_s": clocks[-1], "last_tau_s": clocks[-1]-origin,
               "points_per_frame": {"PartFluid": len(post.SOIL_IDS), "PartBound": len(ids)},
               "vtk_bytes": sizes, "series": series_paths,
               "verification": "All saved VTK coordinates, vertex cells and point-field payloads "
                               "matched source values byte for byte. Both series use native absolute time."}
    if RECEIPT.exists():
        post.require(json.loads(RECEIPT.read_text()) == receipt, "Existing partial export receipt differs")
    else:
        post.write_json(RECEIPT, receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()

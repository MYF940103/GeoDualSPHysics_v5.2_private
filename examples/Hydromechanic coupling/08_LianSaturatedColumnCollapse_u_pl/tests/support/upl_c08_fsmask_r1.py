"""Initial-frame Eq68 mask audit only. Consumes a completed reader; never decodes BI4."""
import argparse
import csv
import json
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np
from scipy.spatial import cKDTree

SCHEMA = [
    ("Idp", "uint32", 1), ("Posd", "float64", 3), ("Vel", "float32", 3),
    ("Sigma_kk", "float32", 3), ("Sigma_ij", "float32", 3), ("FSNormal", "float32", 3),
    ("HydroMechLoadAce", "float32", 3), ("native_Rhop", "float32", 1),
    ("Kplastic", "float32", 1), ("PorePress", "float32", 1), ("PorePress0", "float32", 1),
    ("ExcessPorePress", "float32", 1), ("SigmaState_kk", "float64", 3),
    ("SigmaState_ij", "float64", 3), ("FSType", "uint32", 1),
    ("PoroVolumeRatio", "float64", 1), ("PoroPorosity", "float64", 1),
    ("PoroThetaLastStage", "float64", 1), ("PoroCurrentVolume", "float64", 1),
    ("PoroMixtureDensity", "float64", 1), ("PoroHydraulicConductivity", "float64", 1),
    ("PosDiv", "float32", 1),
]
TYPES = {"uint32": np.dtype("<u4"), "float32": np.dtype("<f4"), "float64": np.dtype("<f8")}
VARIANTS = ("soil_self", "soil_no_self", "soil_wall_self", "soil_wall_no_self")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def load_initial(native, companion):
    done = json.loads((native / "completion.json").read_text(encoding="utf-8"))
    need(done.get("stage") == "upl_c08_elastic_start_native_r1" and done.get("passed") is True
         and done.get("input_run_tag") == "upl_c08_elastic_start_CPU_r2"
         and done.get("samples") == 5 and done.get("total_native_IDs") == 7060
         and done.get("typed_arrays") == 22, "Completed CPU r2 reader required; never launch a decoder")
    with (native / "typed22_layout.csv").open(newline="", encoding="utf-8") as f:
        layout = list(csv.DictReader(f))
    need(len(layout) == 22, "Exactly22 original layout rows required")
    for row, (name, kind, nc) in zip(layout, SCHEMA):
        need((row["array"], row["type"], int(row["components"]), int(row["bytes_per_particle"]))
             == (name, kind, nc, TYPES[kind].itemsize * nc), "Typed layout changed")
    per_frame = 8 + 7060 * 212
    rawpath = native / "typed22.bin"
    need(rawpath.stat().st_size == 12 + 5 * per_frame, "Incomplete/extra typed22 export")
    arrays = {}
    with rawpath.open("rb") as f:
        need(struct.unpack("<III", f.read(12)) == (7060, 22, 5), "Typed header differs")
        need(struct.unpack("<d", f.read(8))[0] == 0, "Only initial t=0 is admitted")
        for name, kind, nc in SCHEMA:
            data = np.fromfile(f, dtype=TYPES[kind], count=7060 * nc)
            arrays[name] = data.reshape(7060, nc) if nc > 1 else data
    with (native / "native_ids.csv").open(newline="", encoding="utf-8") as f:
        ids = list(csv.DictReader(f))
    need(len(ids) == 7060 and np.array_equal(arrays["Idp"], np.arange(7060)), "Native ID ordering differs")
    x0 = np.array([[float(r[k]) for k in ("x0", "y0", "z0")] for r in ids])
    need(all(int(r["id"]) == n and int(r["is_fixed"]) == int(n < 2060) for n, r in enumerate(ids))
         and np.array_equal(x0, arrays["Posd"]), "Original per-ID coordinates/classification differ")
    constants = ET.parse(companion).getroot().find("execution/constants")
    need(constants is not None, "Actual execution companion constants missing")
    value = lambda key: float(constants.find(key).attrib["value"])
    rho0 = value("rhop0")
    mass = float(np.float32(value("massfluid")))
    wallmass = float(np.float32(value("massbound")))
    h = float(np.float32(value("h")))
    need(value("dp") == .04 and h == float(np.float32(.048)) and rho0 == 2072.5
         and mass == wallmass == float(np.float32(3.316)), "Original h/dp/material mass differs")
    v0 = mass / rho0
    j = arrays["PoroVolumeRatio"]
    need(np.all(np.isfinite(j)) and np.all(j > 0) and np.all(j[2060:] == 1)
         and np.all(arrays["native_Rhop"][2060:] == rho0), "Initial J1/reference-density control differs")
    need(np.array_equal(arrays["PoroCurrentVolume"][2060:], v0 * j[2060:]), "Actual native volume ledger differs")
    # Fixed public V=0 is a save marker, not the wall quadrature volume used by FS.
    volumes = v0 * j
    return arrays, volumes, h, {"massfluid_actual_float": mass, "massbound_actual_float": wallmass,
                              "rho0": rho0, "V0_actual_mass_over_rho": v0, "h_actual_float": h,
                              "initial_fixed_J_range": [float(j[:2060].min()), float(j[:2060].max())]}


def cubic_w(rr2, h):
    """Existing 2-D Cubic W expression with float constants/pointwise operations; double sums."""
    f = np.float32
    r = np.sqrt(np.asarray(rr2, dtype=np.float32))
    hf = f(h)
    q = r / hf
    a2 = f(10. / (7. * np.pi * h * h))
    a24 = f(.25 * (10. / (7. * np.pi * h * h)))
    low = a2 * (f(1) + (f(.75) * q - f(1.5)) * (q * q))
    t = f(2) - q
    high = a24 * ((t * t) * t)
    return np.where(r > hf, high, low).astype(np.float64)


def run(native, companion, prefix):
    targets = [prefix.with_suffix(s) for s in (".csv", ".png", ".check.json")]
    need(prefix.parent.is_dir() and not any(p.exists() for p in targets), "Fresh existing figures parent/prefix required")
    a, volumes, h, material = load_initial(native, companion)
    xy = a["Posd"][:, (0, 2)]
    tree = cKDTree(xy)
    ds = np.empty((5000, 4), dtype=np.float64)
    self_terms = np.empty(5000)
    # Radius enlarged only for candidate retrieval; actual float rr2 cutoff below is unchanged.
    r2f = np.float32(np.float32(2 * h) * np.float32(2 * h))
    # A double rr2 just above r2f can still round down to r2f; include its candidates.
    candidate_radius = float(np.sqrt(float(np.nextafter(r2f, np.float32(np.inf)))))
    for k, idx in enumerate(range(2060, 7060)):
        neighbors = np.asarray(tree.query_ball_point(xy[idx], candidate_radius), dtype=np.int64)
        neighbors.sort()  # Deterministic native-ID accumulation, not claimed production sum bits.
        d = xy[idx] - xy[neighbors]
        rr2 = np.sum(d * d, axis=1)
        use = rr2.astype(np.float32) <= r2f
        neighbors, rr2 = neighbors[use], rr2[use]
        contribution = volumes[neighbors] * cubic_w(rr2, h)
        soil = neighbors >= 2060
        own = float(contribution[neighbors == idx].sum())
        self_terms[k] = own
        soil_sum, whole_sum = float(contribution[soil].sum()), float(contribution.sum())
        ds[k] = soil_sum, soil_sum - own, whole_sum, whole_sum - own
    current = np.isin(a["FSType"][2060:], [2, 3])
    masks = ds < .95
    x, z = xy[2060:, 0], xy[2060:, 1]
    radius = 2 * h
    bands = {"all": np.ones(5000, bool), "left": x <= radius, "right": 4 - x <= radius,
             "bottom": z <= radius, "top": 2 - z <= radius}
    for v in ("left", "right"):
        for w in ("bottom", "top"):
            bands[v + "_" + w] = bands[v] & bands[w]
    bands["interior"] = ~(bands["left"] | bands["right"] | bands["bottom"] | bands["top"])
    summary = {}
    for name, select in bands.items():
        rows = {"soil_count": int(select.sum()), "current_FS2": int(((a["FSType"][2060:] == 2) & select).sum()),
                "current_FS3": int(((a["FSType"][2060:] == 3) & select).sum())}
        for col, variant in enumerate(VARIANTS):
            m = masks[:, col]
            rows[variant] = {"Eq68_count": int((m & select).sum()),
                             "both": int((m & current & select).sum()),
                             "Eq68_only": int((m & ~current & select).sum()),
                             "current_only": int((~m & current & select).sum()),
                             "both_interior": int((~m & ~current & select).sum())}
        summary[name] = rows
    with targets[0].open("x", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["native_id", "x_m", "z_m", "FSType_native", "PosDiv_native", "current_FS2_or_3",
                         "V_native_m2", "self_VW"] + ["D_" + v for v in VARIANTS]
                        + ["Eq68_" + v for v in VARIANTS] + list(bands)[1:])
        for k, idx in enumerate(range(2060, 7060)):
            writer.writerow([idx, x[k], z[k], int(a["FSType"][idx]), float(a["PosDiv"][idx]), int(current[k]),
                             volumes[idx], self_terms[k]] + ds[k].tolist() + masks[k].astype(int).tolist()
                            + [int(bands[key][k]) for key in list(bands)[1:]])
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.6), sharex=True, sharey=True)
    colors = ListedColormap(["#d2d2d2", "#149065", "#db8c24", "#296ea6"])
    for col, (ax, variant) in enumerate(zip(axes.flat, VARIANTS)):
        label = np.where(masks[:, col], np.where(current, 1, 2), np.where(current, 3, 0))
        ax.scatter(x, z, c=label, cmap=colors, vmin=-.5, vmax=3.5, s=4, marker="s", linewidths=0)
        ax.set(xlim=(-.02, 4.02), ylim=(-.02, 2.02), xlabel="x [m]", ylabel="z [m]", aspect="equal")
        counts = summary["all"][variant]
        ax.set_title(f"{variant.replace('_', ' ')}: Eq68={counts['Eq68_count']}, current={current.sum()}\n"
                     f"Eq68 only={counts['Eq68_only']}; current only={counts['current_only']}", fontsize=10)
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], color=colors(n), marker="s", linestyle="", label=t) for n, t in enumerate(
        ["Both interior", "Both surface", "Eq68 only", "Current only"])]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False)
    fig.suptitle("C08 actual initial frame: Eq68 sum(Vj W_ij)<0.95 vs native FS2/3\n"
                 "Wall/self definitions shown separately; no tuned threshold or boundary acceptance", fontsize=12)
    fig.tight_layout(rect=(0, .045, 1, .92))
    fig.savefig(targets[1], dpi=180)
    plt.close(fig)
    check = {"stage": "upl_c08_fsmask_r1", "analysis_completed": True, "physical_acceptance": False,
             "input_native": str(native.resolve()), "input_companion": str(companion.resolve()),
             "initial_frame_only": True, "native_IDs": 7060, "soil_IDs_compared": 5000,
             "wall_IDs_as_optional_sources": 2060, "threshold_unchanged": .95, "material": material,
             "kernel": "FunSphKernel.h GetKernelCubic_Wab float expression; double offline accumulation; not bit-equivalence",
             "definitions": "Eq68 has no explicit j!=i; Eq33/Eq68 do not unambiguously specify N's wall/self membership. Four sensitivity definitions are retained without selecting/tuning one.",
             "wall_volume": "V0*actual initial wall J, matching current FS quadrature; saved fixed PoroCurrentVolume=0 is a marker and is not used as wall volume.",
             "regions": "Overlapping true-plane-distance <=2h bands at x=0,4,z=0,2, and their corner intersections; interior excludes all four. Not a wetness/contact mask.",
             "native_FSType_histogram_soil": {str(n): int((a['FSType'][2060:] == n).sum()) for n in range(5)},
             "D_ranges": {v: [float(ds[:, k].min()), float(ds[:, k].max())] for k, v in enumerate(VARIANTS)},
             "self_VW_range": [float(self_terms.min()), float(self_terms.max())], "regions_and_masks": summary,
             "solver_decoder_build_git_SHA_invocations": 0}
    targets[2].write_text(json.dumps(check, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"stage": check["stage"], "analysis_completed": True, "all": summary["all"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--companion", type=Path, required=True)
    parser.add_argument("--out-prefix", type=Path, required=True)
    args = parser.parse_args()
    run(args.native, args.companion, args.out_prefix)

"""Post-process completed explicit C08 runs into separated VTK series, histories and figures."""
import argparse
import csv
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import cKDTree

# Unmodified standalone reader from case 02 tests/support, included alongside this script for server use.
from upl_tpi_partial_bi4_r1 import read as read_bi4

ROOT = Path(__file__).resolve().parents[1]

GROUPS = {"psi0": (0.0, 5000.0, 0.0), "psi2p5": (2.5, 5000.0, 0.2),
          "psim5": (-5.0, 7500.0, 0.2)}
DP = 0.04
DT = 5e-6
SOIL_IDS = np.arange(2060, 7060, dtype=np.uint32)
PRE_IDS = np.arange(7060, dtype=np.uint32)
RELEASE_IDS = np.r_[PRE_IDS[:1805], SOIL_IDS]
FIELD_NAMES = ("id x_m z_m ux_m uz_m vx_m_s vz_m_s p_kPa p0_kPa excess_kPa "
               "sigma_eff_xx_kPa sigma_eff_zz_kPa sigma_total_zz_kPa kappa J porosity "
               "k_m_s rho_mix_kg_m3 fs_type").split()
PRE_SLICES = {0, 100, 500, 1000}
RELEASE_SLICES = {0, 1, 20, 30, 50, 60, 90, 120, 160, 300}


def require(value, message):
    if not value:
        raise ValueError(message)


def write_json(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def native(path):
    frame = read_bi4(path)
    meta = frame["part"]["values"]
    source = frame["arrays"]
    types = {8: ("Idp", "FSType"), 22: ("Vel", "Sigma_kk", "Sigma_ij", "FSNormal", "HydroMechLoadAce"),
             23: ("Posd", "SigmaState_kk", "SigmaState_ij"),
             11: ("Rhop", "Kplastic", "PorePress", "PorePress0", "ExcessPorePress", "PosDiv"),
             12: ("PoroVolumeRatio", "PoroPorosity", "PoroThetaLastStage", "PoroCurrentVolume",
                  "PoroMixtureDensity", "PoroHydraulicConductivity")}
    require(all(frame["types"][name]["type_id"] == typ for typ, names in types.items() for name in names),
            f"Native 22-array layout differs in {path.name}")
    header = frame["root"]["values"]
    require(header["Npiece"] == 1 and header["Piece"] == 0 and header["CaseNfixed"] == 2060
            and header["CaseNp"] == 7060 and header["CaseNfluid"] == 5000 and header["Data2d"]
            and not header["PeriMode"] and not header["CaseNmoving"] and not header["CaseNfloat"]
            and header["Dp"] == DP and header["H"] == np.float32(.072)
            and header["Rhop0"] == 2072.5 and header["MassFluid"] == np.float32(3.316),
            f"Native registry or reference geometry differs in {path.name}")
    order = np.argsort(source["Idp"])
    fields = {key: value[order] for key, value in source.items()}
    return meta, fields


def verify_source_material(meta, group):
    degree, cohesion, decay = GROUPS[group]
    require(meta["GravityPreloadHandoffSchema"] == 2 and not meta["GravityPreloadElasticSource"]
            and meta["GravityPreloadSourceCohesion"] == cohesion, "PRE handoff material or schema mismatch")
    material, tail = meta["GravityPreloadHandoffContract"].split(" material ")[1].split(" law ")
    values = material.split()
    require(len(values) == 9 and float(values[3]) == cohesion and float(values[4]) == 1000
            and float(values[5]) == 5 and np.isclose(float(values[6]), np.deg2rad(degree), atol=5e-9)
            and float(values[7]) == np.float32(decay)
            and tail.strip() == "2 trigger PartBeginSoftening 0 tension JointExistingApexCap history KappaDeviatoric",
            f"PRE material contract differs for {group}")


def stat_id(path):
    st = path.stat()
    return [st.st_size, st.st_mtime_ns]


def inventory(out, pre):
    files = sorted((out / "data").glob("Part_*.bi4"))
    total = 1001 if pre else 301
    require(len(files) == total and all(p.name == f"Part_{i:04d}.bi4" for i, p in enumerate(files)),
            f"Expected {total} consecutive native saves in {out}")
    with (out / "Run.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader((line for line in f if line.strip()), delimiter=";"))
    require(len(rows) == 1, "Expected one completed run in Run.csv")
    summary = rows[0]
    # The configuration string itself can contain semicolons. Use only preceding columns.
    require(int(summary["Steps"]) == (2000000 if pre else 2600000)
            and int(summary["PartFiles"]) == total and int(summary["PartsOut"]) == 0,
            f"Runtime summary differs from the full {'preload' if pre else 'collapse'} plan")
    require("Finished execution (code=0)." in (out / "Run.out").read_text(errors="replace"),
            "Run.out has no successful solver completion")
    return files, summary


def check_frame(meta, a, idx, pre, ref, prev_kappa, stage0, group):
    native_ids = PRE_IDS if pre else RELEASE_IDS
    require(np.array_equal(a["Idp"], native_ids) and len(a) == 22, f"IDs or field count, PART {idx}")
    require(meta["Cpart"] == idx and meta["Nout"] == 0 and meta["GravityPreloadPhase"] == int(not pre)
            and meta["MaterialLawVersion"] == 2 and meta["SymplecticDtPre"] == DT
            and -np.finfo(np.float64).max < meta["dterror"] <= 1e-14
            and meta["DilationDecay"] == np.float32(GROUPS[group][2]),
            f"Native phase/clock/step diagnostic, PART {idx}")
    require(all(np.isfinite(arr).all() for arr in a.values()), f"Nonfinite native field, PART {idx}")
    require(int(meta.get("HydroMechModel", meta.get("HydroMechDynamicSeepage", -1))) == 1
            and int(meta.get("HydroMechDynamicSeepage", 1)) == 1
            and int(meta["HydroMechConductivityModel"]) == 1 and meta["HydroMechConductivityCk"] == 2
            and meta["SoilDampingActive"] == int(pre) and meta["PoreShepardActive"] == int(pre),
            f"Hydromechanics or release policy, PART {idx}")
    soil = slice(-len(SOIL_IDS), None)
    J, n = a["PoroVolumeRatio"][soil], a["PoroPorosity"][soil]
    k, volume = a["PoroHydraulicConductivity"][soil], a["PoroCurrentVolume"][soil]
    rho = a["PoroMixtureDensity"][soil]
    require(np.all(J > 0) and np.all((n > 0) & (n < 1)) and np.all((k > 0) & (volume > 0))
            and np.array_equal(rho.astype("f4"), a["Rhop"][soil])
            and np.allclose(n, 1 - (1 - float(np.float32(.35)))/J, atol=1e-14, rtol=0)
            and np.allclose(rho, 1000+(2072.5-1000)/J, rtol=2e-14, atol=0)
            and np.allclose(volume, float(np.float32(3.316))/2072.5*J, rtol=2e-14, atol=0)
            and np.allclose(k, float(np.float32(2e-4))*np.exp((J-1)/(2*(1-float(np.float32(.35))))),
                            rtol=2e-14, atol=0),
            f"Volume/porosity/density state, PART {idx}")
    require(np.array_equal(a["PorePress0"].view("u4"), ref["PorePress0"][native_ids].view("u4"))
            and np.array_equal(a["ExcessPorePress"], a["PorePress"] - a["PorePress0"]),
            f"Frozen P0 or native excess, PART {idx}")
    fixed = slice(None, -5000)
    require(np.all((a["Rhop"] >= 700) & (a["Rhop"] <= 3000)) and np.all(a["FSType"] <= 4)
            and np.all(a["Posd"][:, 1] == 0) and np.all(a["HydroMechLoadAce"] == 0)
            and np.array_equal(a["Sigma_kk"], a["SigmaState_kk"].astype("f4"))
            and np.array_equal(a["Sigma_ij"], a["SigmaState_ij"].astype("f4")),
            f"Density, free surface, plane or stress display, PART {idx}")
    require(np.array_equal(a["Posd"][fixed], ref["Posd"][native_ids[fixed]]) and not np.any(a["Vel"][fixed])
            and np.all(a["PoroVolumeRatio"][fixed] > 1-float(np.float32(.35)))
            and not any(np.any(a[name][fixed]) for name in ("PoroThetaLastStage", "PoroPorosity",
                "PoroCurrentVolume", "PoroMixtureDensity", "PoroHydraulicConductivity")),
            f"Fixed-boundary state, PART {idx}")
    kap = a["Kplastic"][soil]
    require(np.all(kap >= prev_kappa) and np.all(a["Kplastic"][:-5000] == 0),
            f"Plastic history decreased or fixed history changed, PART {idx}")
    if pre and idx == 1000:
        verify_source_material(meta, group)
    if not pre:
        require(meta["GravityPreloadActualTime"] == stage0 and meta["GravityPreloadTargetIdBegin"] == 1805
                and meta["GravityPreloadTargetIdCount"] == 255 and meta["DynamicNoPenetrationActive"]
                and meta["DynamicNoPenetrationPolicy"] == "FixedPlaneStageProjectionReleaseOnly"
                and not meta["DynamicNoPenetrationReactionClosed"]
                and meta["DynamicArtificialStressActive"] and meta["DynamicArtificialStressPolicy"] == "ReleaseOnly"
                and meta["DynamicArtificialStressCoef"] == np.float32(0.3)
                and meta["DynamicArtificialStressExp"] == np.float32(2.55),
                f"Contact or artificial stress policy, PART {idx}")
        drained = np.isin(a["FSType"][soil], [2, 3])
        require((a["PorePress"][soil][drained] <= 0).all()
                and a["Posd"][soil][:, [0, 2]].min() >= -4e-8, f"FS/plane condition, PART {idx}")
    return kap


def vtk_particles(path, positions, fields):
    """Legacy binary POLYDATA with POINT_DATA and vertex cells for ParaView."""
    n = len(positions)
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as stream:
        def line(text):
            stream.write((text + "\n").encode("ascii"))

        def binary(array, dtype):
            arr = np.asarray(array, dtype=dtype, order="C")
            stream.write(memoryview(arr).cast("B"))
            stream.write(b"\n")

        line("# vtk DataFile Version 3.0")
        line("C08 saved material particles; SI units")
        line("BINARY")
        line("DATASET POLYDATA")
        line(f"POINTS {n} double")
        binary(positions, ">f8")
        line(f"VERTICES {n} {2*n}")
        binary(np.column_stack((np.ones(n, dtype=np.int32), np.arange(n))), ">i4")
        line(f"POINT_DATA {n}")
        line(f"FIELD FieldData {len(fields)}")
        for name, values in fields.items():
            comps = 1 if values.ndim == 1 else values.shape[1]
            vt, dt = {"u": ("unsigned_int", ">u4"), "f": ("float", ">f4")}[values.dtype.kind]
            if values.dtype.kind == "f" and values.dtype.itemsize == 8:
                vt, dt = "double", ">f8"
            line(f"{name} {comps} {n} {vt}")
            binary(values, dt)
    tmp.replace(path)


def make_series(folder, name, times):
    write_json(folder / f"{name}.vtk.series", {
        "file-series-version": "1.0",
        "files": [{"name": f"{name}_{i:04d}.vtk", "time": float(t)} for i, t in enumerate(times)]})


def measures(a, ref, top, bot, pno, time, tau):
    ids = SOIL_IDS
    soil = slice(-len(ids), None)
    pos = a["Posd"][soil]
    vel = a["Vel"][soil]
    displacement = pos - ref["Posd"][ids]
    speed2 = np.einsum("ij,ij->i", vel, vel, dtype=np.float64)
    mass = a["PoroCurrentVolume"][soil] * a["PoroMixtureDensity"][soil]
    pressure = a["PorePress"][soil].astype("f8") * .001
    excess = a["ExcessPorePress"][soil].astype("f8") * .001
    effective = a["SigmaState_kk"][soil] * .001
    total_zz = effective[:, 2] - pressure
    kappa = a["Kplastic"][soil]
    J, n, k = (a[key][soil] for key in ("PoroVolumeRatio", "PoroPorosity", "PoroHydraulicConductivity"))
    nearest = cKDTree(pos[:, [0, 2]]).query(pos[:, [0, 2]], k=2)[0][:, 1] / DP
    front = pos[:, 0].max()
    h = dict(part=pno, time_s=time, tau_s=tau, front_x_m=front,
             runout_m=front - ref["Posd"][ids, 0].max(), height_m=pos[:, 2].max(),
             top_settlement_mm=-1000*displacement[top, 2].mean(),
             bottom_settlement_mm=-1000*displacement[bot, 2].mean(),
             mean_settlement_mm=-1000*displacement[:, 2].mean(),
             p_min_kPa=pressure.min(), p_max_kPa=pressure.max(), p_mean_kPa=pressure.mean(),
             excess_min_kPa=excess.min(), excess_max_kPa=excess.max(), excess_mean_kPa=excess.mean(),
             total_zz_min_kPa=total_zz.min(), total_zz_max_kPa=total_zz.max(),
             effective_zz_mean_kPa=effective[:, 2].mean(), kappa_mean=kappa.mean(dtype="f8"),
             kappa_max=kappa.max(), kappa_nonzero=np.count_nonzero(kappa),
             J_min=J.min(), J_max=J.max(), porosity_min=n.min(), porosity_max=n.max(),
             k_min_m_s=k.min(), k_max_m_s=k.max(), speed_max_m_s=np.sqrt(speed2.max()),
             speed_rms_m_s=np.sqrt(speed2.mean()), kinetic_energy_J_per_m=0.5*np.dot(mass, speed2),
             nearest_min_dp=nearest.min(), nearest_p05_dp=np.quantile(nearest, .05),
             nearest_below_half_dp=np.count_nonzero(nearest < .5))
    return h, displacement, effective, total_zz, pressure, excess


def write_particles(location, idx, a, disp):
    soil = slice(-5000, None)
    fixed = slice(None, -5000)
    names = ("Idp", "Vel", "PorePress", "PorePress0", "ExcessPorePress", "Kplastic",
             "SigmaState_kk", "SigmaState_ij", "PoroVolumeRatio", "PoroPorosity",
             "PoroHydraulicConductivity", "PoroMixtureDensity", "FSType")
    fields = {key: a[key][soil] for key in names}
    fields["Displacement"] = disp
    vtk_particles(location/"PartFluid"/f"PartFluid_{idx:04d}.vtk", a["Posd"][soil], fields)
    ids = a["Idp"][fixed]
    bfields = {"Idp": ids, "MkBound": np.searchsorted([255, 1805], ids, side="right").astype("u4")}
    vtk_particles(location/"PartBound"/f"PartBound_{idx:04d}.vtk", a["Posd"][fixed], bfields)


def retained_series(files, group, pre):
    # Only reuse existing native products when all adopted BI4 are the same physical files.
    registered = {
        ("psi0", True): ("c08_h18_wend_psi0_pre_r2", "native_r1"),
        ("psi0", False): ("c08_h18_as03n255_full3_r1", "native_r1"),
        ("psi2p5", True): ("c08_h18_wend_branches_psi2p5_pre_r1", "native_r2"),
    }
    if (group, pre) not in registered:
        return None
    case, native_dir = registered[group, pre]
    old = ROOT / "tests/outputs" / case
    folder = old / native_dir
    if not (folder/"completion.json").exists() or not (old/"data"/files[0].name).exists():
        return None
    if not all((old/"data"/file.name).is_file() and file.samefile(old/"data"/file.name) for file in files):
        return None
    check = json.loads((folder/"completion.json").read_text(encoding="utf-8-sig"))
    require(check.get("passed") and check["group"] == group and check["samples"] == len(files)
            and check["typed_arrays"] == 22, f"Incomplete retained native results in {folder}")
    n = 7060 if pre else 6805
    spec = [("time", "<f8")]
    with (folder/"typed22_layout.csv").open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            comp = int(row["components"])
            spec.append((row["array"], np.dtype(row["type"]).newbyteorder("<"), (n,) if comp == 1 else (n, comp)))
    dtype = np.dtype(spec)
    binfile = folder/"typed22.bin"
    require(len(spec) == 23 and dtype.itemsize == n*212+8 and
            np.array_equal(np.fromfile(binfile, "<u4", count=3), [n, 22, len(files)]) and
            binfile.stat().st_size == 12 + dtype.itemsize*len(files), f"Native layout is inconsistent in {folder}")
    with (folder/"clocks.csv").open(encoding="utf-8-sig") as f:
        clocks = list(csv.DictReader(f))
    require(len(clocks) == len(files), f"Native clock count in {folder}")

    def frames():
        # Contiguous chunks avoid interleaving hundreds of page faults with small VTK writes on HDDs.
        with binfile.open("rb") as stream:
            stream.seek(12)
            for start in range(0, len(files), 12):
                records = np.fromfile(stream, dtype=dtype, count=min(12, len(files)-start))
                for i, record in enumerate(records, start):
                    clock = clocks[i]
                    fields = {("Rhop" if key == "native_Rhop" else key): record[key] for key in dtype.names[1:]}
                    require(clock["file"] == files[i].name and float(clock["time_s"]) == record["time"]
                            and np.array_equal(fields["Idp"], PRE_IDS if pre else RELEASE_IDS),
                            f"Retained native identity or clock, PART {i}")
                    yield float(clock["time_s"]), int(clock["saved_step"]), float(clock["signed_dterror_s"]), fields
    return frames(), str(folder)


def history_plot(figdir, group, pre, rows):
    t = [r["tau_s"] for r in rows]
    panels = [
        ("Pore pressure (kPa)", [("p_min_kPa", "Minimum"), ("p_mean_kPa", "Mean"), ("p_max_kPa", "Maximum")]),
        ("Settlement (mm, down +)", [("top_settlement_mm", "Top material row"), ("bottom_settlement_mm", "Bottom material row")]),
        ("Front and height (m)", [("front_x_m", "Front x"), ("height_m", "Maximum z")]),
        ("Total vertical stress (kPa)", [("total_zz_min_kPa", "Minimum"), ("total_zz_max_kPa", "Maximum")]),
        ("Plastic history κ", [("kappa_mean", "Mean"), ("kappa_max", "Maximum")]),
        ("Nearest neighbour / dp", [("nearest_min_dp", "Minimum"), ("nearest_p05_dp", "5th percentile")])
    ]
    fig, axes = plt.subplots(2, 3, figsize=(14, 7.4), constrained_layout=True)
    for ax, (name, series) in zip(axes.flat, panels):
        for key, label in series:
            ax.plot(t, [r[key] for r in rows], label=label, linewidth=1.6)
        ax.set(xlabel="Time since preload began (s)" if pre else "Time since wall removal (s)", ylabel=name)
        ax.grid(alpha=.23)
        ax.legend(fontsize=8)
    fig.suptitle(f"C08   ψ = {GROUPS[group][0]:g}°   |   {'Gravity preload' if pre else 'Column collapse'}")
    fig.savefig(figdir/"history.png", dpi=170)
    plt.close(fig)


def field_plot(figdir, snapshots, group, pre):
    from matplotlib.colors import Normalize
    columns = [("p_kPa", "Pore pressure (kPa)", "viridis"),
               ("uz_m", "Vertical displacement (m)", "cividis"),
               ("kappa", "Plastic history κ", "magma")]
    fig, axes = plt.subplots(len(snapshots), 3, figsize=(14, 2.45*len(snapshots)+.9),
                             sharex=True, sharey=True, constrained_layout=True)
    labels = {name: i for i, name in enumerate(FIELD_NAMES)}
    for col, (key, title, cmap) in enumerate(columns):
        norm = Normalize(min(arr[:, labels[key]].min() for _, arr in snapshots),
                         max(arr[:, labels[key]].max() for _, arr in snapshots))
        for i, (tau, arr) in enumerate(snapshots):
            ax = axes[i, col]
            cloud = ax.scatter(arr[:, labels["x_m"]], arr[:, labels["z_m"]], c=arr[:, labels[key]],
                               s=2, linewidths=0, cmap=cmap, norm=norm, rasterized=True)
            ax.set_aspect("equal", adjustable="box")
            if not i:
                ax.set_title(title)
            if not col:
                ax.set_ylabel(f"{tau:.5g} s\nz (m)")
            if i == len(snapshots)-1:
                ax.set_xlabel("x (m)")
        fig.colorbar(cloud, ax=list(axes[:, col]), orientation="horizontal", shrink=.83, pad=.02)
    fig.suptitle(f"ψ = {GROUPS[group][0]:g}°  |  {'Preload' if pre else 'Collapse'}   •   native soil particles")
    fig.savefig(figdir/"particle_fields.png", dpi=155)
    plt.close(fig)


def process(group, out, preload_path, pre):
    files, run = inventory(out, pre)
    receipt = json.loads((out/"provenance.json").read_text(encoding="utf-8-sig"))
    require(receipt["group"] == group and receipt["stage"] == ("preload" if pre else "collapse")
            and (receipt["state"] == "completed" or receipt.get("method") == "fresh"),
            "Provenance does not identify this group and phase")
    particles = out/"particles"
    figdir = ROOT/"figures/validation_explicit"/group
    if pre:
        figdir = figdir/"preload"
    figdir.mkdir(parents=True, exist_ok=True)
    marker = figdir/"postprocess.json"
    refpath = preload_path/"data"/("Part_0000.bi4" if pre else "Part_1000.bi4")
    signature = {"folder": str(out), "run": stat_id(out/"Run.csv"), "reference": stat_id(refpath),
                 "native_files": [stat_id(f) for f in files]}
    if marker.exists():
        prior = json.loads(marker.read_text(encoding="utf-8"))
        require(prior["inputs"] == signature, f"Existing published outputs belong to different inputs: {figdir}")
        collections_complete = all((particles/name/(name+".vtk.series")).is_file()
            and all((particles/name/f"{name}_{i:04d}.vtk").is_file() for i in range(len(files)))
            for name in ("PartFluid", "PartBound"))
        if collections_complete and all((figdir/file).is_file() for file in
                ("history.csv", "fields.csv", "history.png", "particle_fields.png")):
            print(f"Verified existing {group} {'PRE' if pre else 'collapse'} products", flush=True)
            return
    # Only this publication's own files may be resumed after interruption.
    lock = out/"validation_post.lock"
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"Existing postprocessing lock: {lock}") from exc
    os.close(lock_fd)
    try:
        start = out/"validation_post.inputs.json"
        if start.exists():
            require(json.loads(start.read_text(encoding="utf-8")) == signature, "Prior partial output has different inputs")
        else:
            require(not any((particles/name).exists() for name in ("PartFluid", "PartBound"))
                    and not (figdir/"history.csv").exists(), "Unowned existing particle or plot outputs")
            write_json(start, signature)
        for name in ("PartFluid", "PartBound"):
            (particles/name).mkdir(parents=True, exist_ok=True)
        refmeta, ref = native(refpath)
        require(np.array_equal(ref["Idp"], PRE_IDS), "Material reference has a different particle registry")
        cert = native(files[-1])[0] if pre else refmeta
        verify_source_material(cert, group)
        stage0 = float(refmeta["TimeStep"])
        # Select material rows from initial gravity geometry, then retain their IDs throughout.
        initial = ref if pre else native(preload_path/"data/Part_0000.bi4")[1]
        z0 = initial["Posd"][SOIL_IDS, 2]
        top = np.abs(z0 - z0.max()) < DP/4
        bot = np.abs(z0 - z0.min()) < DP/4
        prev_kappa = ref["Kplastic"][-5000:].copy()
        cached = retained_series(files, group, pre)

        def raw_frames():
            nonlocal prev_kappa
            for i, file in enumerate(files):
                meta, a = native(file)
                prev_kappa = check_frame(meta, a, i, pre, ref, prev_kappa, stage0, group)
                yield float(meta["TimeStep"]), int(meta["Step"]), float(meta["dterror"]), a

        frames, source = cached if cached is not None else (raw_frames(), "Original BI4")
        rows, snapshots = [], []
        # Start the scalar recurrence at the native PRE, preserving its accumulated rounding.
        clocks = np.cumsum(np.r_[stage0, np.full(2000000 if pre else 600000, DT)])
        ids = SOIL_IDS
        for i, (time, step, interval, a) in enumerate(frames):
            complete = (0 if pre and i == 0 else step+1)
            expected_t = clocks[complete-(0 if pre else 2000000)]
            require(time == expected_t and (not rows or step > rows[-1]["saved_step"]), f"Native clock, PART {i}")
            require(interval <= 1e-14 and np.isfinite(interval), f"Signed dterror, PART {i}")
            tau = time-stage0
            h, disp, eff, total, p, excess = measures(a, ref, top, bot, i, time, tau)
            h.update(saved_step=step, completed_step=complete, signed_dterror_s=interval)
            rows.append(h)
            # Successful writes are atomic. A second attempt may reuse these owned particle outputs.
            if not all((particles/name/f"{name}_{i:04d}.vtk").is_file() for name in ("PartFluid", "PartBound")):
                write_particles(particles, i, a, disp)
            if i in (PRE_SLICES if pre else RELEASE_SLICES):
                subset = slice(-5000, None)
                pos, vel = a["Posd"][subset], a["Vel"][subset]
                data = np.column_stack((ids, pos[:, 0], pos[:, 2], disp[:, 0], disp[:, 2],
                    vel[:, 0], vel[:, 2], p, a["PorePress0"][subset]*.001, excess,
                    eff[:, 0], eff[:, 2], total, a["Kplastic"][subset], a["PoroVolumeRatio"][subset],
                    a["PoroPorosity"][subset], a["PoroHydraulicConductivity"][subset],
                    a["PoroMixtureDensity"][subset], a["FSType"][subset]))
                snapshots.append((tau, data))
        expect = 2000000 if pre else 2600000
        require(rows[-1]["completed_step"] == expect, "Final native update differs")
        with (figdir/"history.csv").open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        with (figdir/"fields.csv").open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["part", "time_s", "tau_s", *FIELD_NAMES])
            for (tau, arr), idx in zip(snapshots, sorted(PRE_SLICES if pre else RELEASE_SLICES)):
                for values in arr:
                    writer.writerow([idx, rows[idx]["time_s"], tau, int(values[0]), *values[1:-1], int(values[-1])])
        for name in ("PartFluid", "PartBound"):
            make_series(particles/name, name, [r["time_s"] for r in rows])
        history_plot(figdir, group, pre, rows)
        display = PRE_SLICES if pre else ({20, 50, 160, 300} if group == "psim5" else {30, 60, 120, 300})
        snapshot_ids = sorted(PRE_SLICES if pre else RELEASE_SLICES)
        field_plot(figdir, [snap for idx, snap in zip(snapshot_ids, snapshots) if idx in display], group, pre)
        write_json(marker, {"inputs": signature, "group": group, "stage": "preload" if pre else "collapse",
                   "native_input": source, "frames": len(rows), "soil_count": 5000,
                   "boundary_count": 2060 if pre else 1805, "time_origin_s": stage0, "end_s": rows[-1]["time_s"],
                   "loop_wall_s": float(run["TSimul"]), "hardware": run["Hardware"],
                   "material_top_count": int(top.sum()), "material_bottom_count": int(bot.sum()),
                   "reference_for_displacement": str(refpath), "physical_acceptance": False})
        print(f"Published {group} {'PRE' if pre else 'collapse'}: {len(rows)} native frames in {figdir}", flush=True)
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", required=True, choices=GROUPS)
    parser.add_argument("--preload", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--preload-only", action="store_true")
    args = parser.parse_args()
    if not args.preload_only and not args.output:
        parser.error("--output must identify the finished collapse run")
    pre = args.preload.resolve(strict=True)
    process(args.group, pre, pre, True)
    if not args.preload_only:
        process(args.group, args.output.resolve(strict=True), pre, False)


if __name__ == "__main__":
    main()

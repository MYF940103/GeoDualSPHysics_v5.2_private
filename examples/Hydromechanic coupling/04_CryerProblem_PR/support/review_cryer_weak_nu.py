"""Audit one completed fixed-reference weak Cryer trajectory and export its native material fields."""
import csv
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys

import numpy as np
from scipy.optimize import minimize_scalar

from plot_cryer_formal_four_nu_r1 import Reference
from plot_cryer_weak_full import material_fields, vtk_blocks, check_vtk

sys.path.insert(0, str(Path(__file__).resolve().parent / "weak_full_r1"))
from cryer_weak_full_review import determinants, residuals


N = 37173
R = .05
Q = 10000.
DT = 2.**-19
OPEN = 4096
TD = OPEN*DT
VARIANTS = (.10, .20, .45)
CLOSED = (3904, 3968, 4032, OPEN)
CLOSED_LIMITS = dict(rms_p_to_10000_Pa=100., rms_total_to_10000_Pa=100., max_speed_m_s=1e-5,
                     rms_displacement_mm=1e-5, rms_surface_displacement_mm=1e-5)
DENSE_FIELDS = ("step", "time_s", "center18_Pa", "surface_inward_mm", "p_min_Pa", "p_max_Pa", "max_speed_m_s")
MATERIAL_FIELDS = ("nu_nominal", "nu_effective", "young_Pa", "mu_Pa", "lambda_Pa", "sound_m_s",
                   "base_sound_m_s", "av_scale", "dt_s", "damping_s_inv")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def identity(path):
    st = path.stat()
    return dict(path=str(path.resolve()), bytes=st.st_size, mtime_ns=st.st_mtime_ns)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, value):
    with path.open("x", encoding="utf8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def read_csv(path, fields=None):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        table = csv.DictReader(stream)
        if fields:
            require(tuple(table.fieldnames) == fields, f"Unexpected columns in {path.name}")
        return list(table)


def write_csv(path, rows):
    with path.open("x", newline="", encoding="utf8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_mesh(package):
    path = package / "inputs/reference_mesh.npz"
    binding = identity(path)
    with np.load(path, allow_pickle=False) as z:
        mesh = {key: z[key] for key in ("native_ids", "x0", "tets", "material_shell", "native_surface")}
    require(identity(path) == binding, "Reference mesh changed while reading")
    ids, x, tets, shell, fs = (mesh[k] for k in ("native_ids", "x0", "tets", "material_shell", "native_surface"))
    require(np.array_equal(ids, np.arange(8, 37181)) and x.shape == (N, 3) and np.isfinite(x).all()
            and tets.shape == (209117, 4) and tets.min() >= 0 and tets.max() < N
            and shell.shape == (N,) and np.all((shell >= 1) & (shell <= 20))
            and len(fs) == 5153 and np.array_equal(fs, np.flatnonzero(shell == 20)),
            "Original material, tetrahedron or drain registry differs")
    radius = np.linalg.norm(x, axis=1)
    centre = np.flatnonzero(shell == 1)
    require(len(centre) == 18 and abs(radius.max()-R) < 1e-14
            and np.max(np.abs(radius-shell*.0025)) < 1e-14, "Original radial geometry differs")
    det0 = determinants(x, tets)
    require(np.isfinite(det0).all() and np.all(det0!=0.), "Degenerate reference tetrahedron")
    return mesh, binding, centre, radius, det0


def step_at_tv(target, cv):
    step = OPEN + math.floor(target*R**2/cv/DT)
    if (step-OPEN)*DT*cv/R**2 < target:
        step += 1
    return step


def schedule(planned, dense, cv):
    targets = {step_at_tv(i/200, cv):i/200 for i in range(201)}
    standard = set(range(0, OPEN, 64)) | set(targets)
    require(list(planned) == sorted(set(planned)) and len(planned) == 269
            and planned[-1] == step_at_tv(1., cv) and standard <= set(planned)
            and {OPEN+1, OPEN+64, OPEN+128} <= set(planned),
            "Full plan must have 265 scheduled states and four prescribed extra states")
    endpoint = step_at_tv(.12, cv)
    expected_dense = sorted({OPEN, OPEN+1, endpoint, *range(OPEN+32, endpoint, 32)})
    require(list(dense) == expected_dense, "Dense startup/peak plan differs")
    return targets


@lru_cache(maxsize=4)
def package_digest(path, length, mtime_ns):
    with path.open("rb") as stream:
        value = hashlib.file_digest(stream, "sha256").hexdigest()
    st = path.stat()
    require((st.st_size, st.st_mtime_ns) == (length,mtime_ns), "Manifest changed while hashing")
    return value


def verify_seal(package, output, nu, planned, dense, cv):
    seal_path = output / "server_run.json"
    binding = identity(seal_path)
    seal = read_json(seal_path)
    require(seal["mode"] == "full" and seal["returncode"] == 0 and seal["nu"] == nu
            and (output / "complete.txt").read_text(encoding="ascii").strip() == "full",
            "A normally completed owned solve for this Poisson ratio is required")
    package_path = package / "manifest.json"
    package_id = identity(package_path)
    profile = seal["profile"]
    require(seal["package"] == package_digest(package_path,package_id["bytes"],package_id["mtime_ns"])
            and identity(seal_path) == binding and profile["nu"]==nu and profile["dt_s"]==DT
            and profile["drain_step"]==OPEN and profile["drainage_time_s"]==TD
            and profile["end_step"]==planned[-1] and profile["end_s"]==planned[-1]*DT
            and profile["saved_steps"]==planned and profile["dense_steps"]==dense
            and math.isclose(profile["legacy_cv_m2_s"],cv,rel_tol=2e-15,abs_tol=0.),
            "The owned solve used a different frozen reference package")
    expected = {f"state_{step}.bin" for step in planned}
    require({p.name for p in output.glob("state_*.bin")} == expected, "Wrong raw-state sequence")
    controls = {"complete.txt", "actual_clock.csv", "peak_history.csv", "closed_gate.csv", "material.csv"}
    records = {entry["name"]:dict(path=str(output / entry["name"]), bytes=entry["bytes"],
                                  mtime_ns=entry["mtime_ns"]) for entry in seal["files"]}
    require(len(records) == len(seal["files"]) and set(records) == expected | controls,
            "Raw frame or clock inventory differs")
    require(all(records[name]["bytes"] == 15*N*8 for name in expected), "Wrong frozen raw field size")
    return binding, package_id, records


def inspect_material(package, output, nu):
    row, = read_csv(output/"material.csv", MATERIAL_FIELDS)
    values = {key:float(value) for key,value in row.items()}
    nu_eff = float(np.float32(nu))
    base_nu = float(np.float32(.30))
    e = 2e6
    mu = e/(2*(1+nu_eff))
    lam = e*nu_eff/((1+nu_eff)*(1-2*nu_eff))
    sound = math.sqrt((lam+2*mu)/2100.)
    base_sound = math.sqrt((e*(1-base_nu)/((1+base_nu)*(1-2*base_nu)))/2100.)
    with (package/"inputs/operators.bin").open("rb") as stream:
        _, _, _, damping = struct.unpack("<4d",stream.read(32))
    expected = (nu,nu_eff,e,mu,lam,sound,base_sound,sound/base_sound,DT,damping)
    require(all(math.isclose(values[key],expected_value,rel_tol=3e-15,abs_tol=0.)
                for key,expected_value in zip(MATERIAL_FIELDS,expected,strict=True)),
            "Reported material factors, damping or viscosity scaling differ from the planned material")
    return values


def inspect_closed(output, independent):
    rows = read_csv(output/"closed_gate.csv", ("step","time_s",*CLOSED_LIMITS,"passed"))
    for row, expected in zip(rows,CLOSED,strict=True):
        require(int(row["step"]) == expected and float(row["time_s"])==expected*DT
                and row["passed"]=="1", "Host did not pass the original closed-state gate")
        for key, limit in CLOSED_LIMITS.items():
            reported = float(row[key])
            require(0.<=reported<=limit and math.isclose(reported,independent[expected][key],
                    rel_tol=1e-12,abs_tol=1e-10 if key.endswith("_Pa") else 1e-12),
                    f"Saved and host closed reductions differ for {key} at {expected}")


def read_frame(record):
    path = Path(record["path"])
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        require((before.st_size, before.st_mtime_ns) == (record["bytes"], record["mtime_ns"]),
                f"Native input changed: {path.name}")
        raw = np.fromfile(stream, dtype="<f8")
        after = os.fstat(stream.fileno())
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
            and identity(path) == record, f"Native input changed during read: {path.name}")
    require(raw.shape == (15*N,) and np.isfinite(raw).all(), f"Malformed native field payload: {path.name}")
    return raw


def theory_curves(ref, times):
    tau = np.asarray(times)
    centre = ref.pressure(tau)
    mean = np.full(tau.shape, np.nan)
    positive = tau > 0
    mean[positive] = Q * (ref.mean*ref.amplitude) @ np.exp(-ref.decay[:, None]*tau[positive])
    mean[tau==0.] = Q
    inward = 1000.*R*(Q-mean)/(3.*ref.K)
    return centre, inward


def dense_review(raw, dense_steps, ref):
    actual = []
    for line, expected in zip(raw, dense_steps, strict=True):
        step = int(line["step"])
        row = dict(step=step, **{key:float(line[key]) for key in DENSE_FIELDS[1:]})
        require(step == expected and row["time_s"] == step*DT and np.isfinite(list(row.values())).all()
                and row["p_min_Pa"] <= row["center18_Pa"] <= row["p_max_Pa"]
                and row["max_speed_m_s"] >= 0., "Invalid dense solver sample or actual clock")
        actual.append(row)
    tau = np.array([r["time_s"]-TD for r in actual])
    target = tau*ref.legacy_cv/R**2
    mandel = np.flatnonzero(target>=.005)
    require(len(mandel) > 10, "Missing Mandel dense window")
    pressures = np.array([r["center18_Pa"] for r in actual])
    ref_p, ref_surface = theory_curves(ref, tau)
    peak = mandel[int(np.argmax(pressures[mandel]))]
    bracketed = bool(mandel[0] < peak < mandel[-1])
    probe = np.geomspace(.005, .12, 200)*R**2/ref.legacy_cv
    point = int(np.argmax(ref.pressure(probe)))
    require(0 < point < len(probe)-1, "Theoretical peak differs from declared Mandel window")
    t = minimize_scalar(lambda s: -float(ref.pressure([s])[0]),
                        bounds=(probe[point-1],probe[point+1]), method="bounded",
                        options=dict(xatol=1.e-14))
    require(t.success, "Continuous M0 peak optimizer failed")
    amplitude = float(100*(pressures[peak]/(-t.fun)-1.))
    timing = float(100*(tau[peak]/t.x-1.))
    start = [r for r, tv in zip(actual,target,strict=True) if 0.<tv<.005]
    require(start, "Missing post-opening startup samples")
    result = dict(peak_frame_step=actual[peak]["step"], center_peak_Pa=float(pressures[peak]),
                  peak_tau_s=float(tau[peak]), peak_Tv=float(target[peak]), dense_frames=len(actual),
                  mandel_frames=len(mandel), matched_ref_Pa=float(ref_p[peak]),
                  continuous_theory_peak_Pa=float(-t.fun), continuous_theory_peak_tau_s=float(t.x),
                  amplitude_error_pct=amplitude, timing_error_pct=timing, strict_amplitude_pct=1.,
                  strict_timing_pct=2., sampled_peak_bracketed=bracketed,
                  peak_bounds_pass=bracketed and abs(amplitude)<=1. and abs(timing)<=2.,
                  mandel_center_errors_Pa=residuals(pressures[mandel]-ref_p[mandel]),
                  mandel_surface_errors_mm=residuals(
                      np.array([r["surface_inward_mm"] for r in actual])[mandel]-ref_surface[mandel]),
                  startup_frames=len(start),
                  startup_center_peak_Pa=max(r["center18_Pa"] for r in start),
                  startup_material_max_Pa=max(r["p_max_Pa"] for r in start),
                  scope="18 fixed material IDs, M0 r0=2.5 mm, actual dense clock. Startup retained separately.")
    return actual, result


def native_rows(planned, records, targets, mesh, centre, radius, det0, dense, ref, peak):
    x, tets, shell, fs = (mesh[k] for k in ("x0", "tets", "material_shell", "native_surface"))
    t = np.asarray(planned)*DT
    tau = t-TD
    cv = ref.legacy_cv
    ref_p, ref_u = theory_curves(ref, tau)
    rows, profiles, closed = [], [], {}
    sample_steps = {OPEN+1, OPEN+64, OPEN+128, planned[-1],
                    step_at_tv(.1,cv), step_at_tv(.5,cv)}
    sample_steps.add(min((step for step in planned if step>OPEN),
                         key=lambda step:abs(step*DT-TD-peak["peak_tau_s"])))
    shared = {r["step"]: r for r in dense}
    overlap = 0
    for i, step in enumerate(planned):
        raw = read_frame(records[f"state_{step}.bin"])
        pos, fields = material_fields(raw, mesh)
        p, prev = fields["PorePress"], fields["PorePressPrevious"]
        u, v, s, j = (fields[k] for k in ("Displacement", "Vel", "SigmaEffective_xx_yy_zz_xy_yz_xz", "J"))
        radial = np.linalg.norm(pos, axis=1)
        jac = determinants(pos, tets)/det0
        porosity = 1.-(1.-float(np.float32(.3)))/j
        require(np.isfinite(jac).all() and np.all(jac>0.) and np.all((0.<porosity)&(porosity<1.))
                and radial.max()<.0525, f"Invalid saved geometry or saturation: {step}")
        if step>OPEN:
            require(not np.any(p[fs]) and not np.any(prev[fs]), f"Current or previous surface pressure at {step}")
        speed = np.linalg.norm(v, axis=1)
        displacement = np.linalg.norm(u, axis=1)
        surface_delta = 1000.*(radius[fs]-radial[fs])
        if step in CLOSED:
            radial_projection = 1000.*np.einsum("ij,ij->i",u[fs],x[fs])/radius[fs]
            closed[step] = dict(rms_p_to_10000_Pa=residuals(p-Q)["rms"],
                rms_total_to_10000_Pa=residuals(p-s[:,:3].mean(axis=1)-Q)["rms"],
                max_speed_m_s=float(speed.max()), rms_displacement_mm=residuals(1000.*displacement)["rms"],
                rms_surface_displacement_mm=residuals(radial_projection)["rms"])
        tv = float(tau[i]*cv/R**2)
        target = targets.get(step) if step>=OPEN else None
        if target is not None:
            require(-1e-14<=tv-target < DT*cv/R**2, f"Not the first saved numerical step at Tv={target}")
        row = dict(step=step, time_s=float(t[i]), tau_s=float(tau[i]), legacy_Tv=tv, target_Tv=target,
                   center18_Pa=float(p[centre].mean()), M0_center18_Pa=None if tau[i]<0 else float(ref_p[i]),
                   surface_inward_mm=float(surface_delta.mean()),
                   M0_surface_inward_mm=None if tau[i]<0 else float(ref_u[i]),
                   min_Pa=float(p.min()), max_Pa=float(p.max()), max_surface_abs_Pa=float(abs(p[fs]).max()),
                   max_speed_m_s=float(speed.max()), max_displacement_m=float(displacement.max()),
                   max_radius_m=float(radial.max()), min_J=float(j.min()), max_J=float(j.max()),
                   min_det_F=float(jac.min()), max_det_F=float(jac.max()), max_abs_stress_Pa=float(abs(s).max()))
        if step in shared:
            d = shared[step]
            for scalar, native, tol in (("center18_Pa","center18_Pa",1e-7),
                                        ("surface_inward_mm","surface_inward_mm",1e-10),
                                        ("p_min_Pa","min_Pa",1e-7), ("p_max_Pa","max_Pa",1e-7),
                                        ("max_speed_m_s","max_speed_m_s",1e-12)):
                require(abs(row[native]-d[scalar])<=tol, f"Dense/native independent reduction differs {step} {scalar}")
            overlap += 1
        rows.append(row)
        if step in sample_steps:
            for level in range(1,21):
                p_shell = p[shell==level]
                profiles.append(dict(step=step,time_s=row["time_s"],legacy_Tv=tv,r_over_a=level/20,
                    count=len(p_shell),p_mean_Pa=float(p_shell.mean()),p_sd_Pa=float(p_shell.std()),
                    p_min_Pa=float(p_shell.min()),p_max_Pa=float(p_shell.max())))
    require(set(closed)==set(CLOSED) and all(value<=CLOSED_LIMITS[k] for state in closed.values()
            for k,value in state.items()), "Original closed-pressure, stress, speed or displacement gate")
    require(overlap==len(set(planned)&set(shared)), "Missing actual native/dense overlap")
    return rows, profiles, closed, overlap


def figures(dest, rows, profiles, dense, ref, nu):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    positive = [r for r in rows if r["tau_s"]>0]
    history_plot = dest/"pressure_settlement_profiles.png"
    peak_plot = dest/"peak_history.png"
    if history_plot.exists() and peak_plot.exists():
        return
    fig, axes = plt.subplots(1,3,figsize=(13,4.1),layout="constrained")
    for ax, native, theory, label in zip(axes[:2], ("center18_Pa","surface_inward_mm"),
            ("M0_center18_Pa","M0_surface_inward_mm"), ("Center pressure (Pa)","Surface inward displacement (mm)")):
        tv = [r["legacy_Tv"] for r in positive]
        ax.plot(tv,[r[theory] for r in positive],"k--",label="M0 at actual time")
        ax.plot(tv,[r[native] for r in positive],".",ms=3,label="Weak 3D GPU")
        ax.set(xscale="log",xlim=(1e-4,5),xlabel="Tv after drainage",ylabel=label)
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
    for step in sorted({r["step"] for r in profiles}):
        group = [r for r in profiles if r["step"]==step]
        axes[2].plot([r["r_over_a"] for r in group],[r["p_mean_Pa"] for r in group],".-",
                     lw=1,label=f"Tv={group[0]['legacy_Tv']:.4g}")
    axes[2].set(xlabel="Reference radius / a",ylabel="Shell mean pressure (Pa)")
    axes[2].legend(fontsize=7)
    axes[2].grid(alpha=.2)
    fig.suptitle(f"Cryer fixed-reference weak 3D, Poisson ratio {nu:g}")
    if not history_plot.exists():
        fig.savefig(history_plot,dpi=170)
    plt.close(fig)
    fig,ax = plt.subplots(figsize=(7.5,4),layout="constrained")
    tau = np.array([r["time_s"]-TD for r in dense])
    ax.plot(1000*tau,ref.pressure(tau),"k--",label="M0 at actual time")
    ax.plot(1000*tau,[r["center18_Pa"] for r in dense],".",ms=3,label="Weak 3D, dense samples")
    ax.set(xlabel="Time after drainage (ms)",ylabel="Center pressure (Pa)")
    ax.legend()
    ax.grid(alpha=.2)
    if not peak_plot.exists():
        fig.savefig(peak_plot,dpi=170)
    plt.close(fig)


def publish_figures(dest, ref, nu):
    marker = dest/"figures.json"
    if marker.exists():
        require(all(identity(Path(p["path"]))==p for p in read_json(marker)["files"]),
                "Existing figure files changed")
        return

    def numbers(path):
        return [{k:(int(v) if k=="step" else float(v)) for k,v in row.items() if v!=""}
                for row in read_csv(path)]

    figures(dest,numbers(dest/"actual_vs_theory.csv"),numbers(dest/"shell_profiles.csv"),
            numbers(dest/"peak_history.csv"),ref,nu)
    files = [dest / name for name in ("pressure_settlement_profiles.png","peak_history.png")]
    for path in files:
        with path.open("rb") as stream:
            require(stream.read(8)==b"\x89PNG\r\n\x1a\n" and path.stat().st_size>1000,
                    f"Invalid derived figure: {path}")
    save(marker,dict(files=[identity(path) for path in files]))


def export_particles(package, output, report=None):
    """Emit all saved material frames using the existing weak VTK representation."""
    package, output = Path(package).resolve(), Path(output).resolve()
    receipt = output/"review/review.json"
    report = read_json(receipt) if report is None else report
    require(report["full_cycle_measured"] and report["native_passed"]
            and report["input_seal"]==identity(output/"server_run.json")
            and report["package_manifest"]==identity(package/"manifest.json")
            and report["history"]==identity(output/"review/actual_vs_theory.csv"),
            "A sealed native review is required before export")
    mesh, binding, *_ = load_mesh(package)
    require(binding==report["mesh"], "Material coordinates changed after native review")
    folder = output/"particles"
    folder.mkdir(exist_ok=True)
    rows = read_csv(output/"review/actual_vs_theory.csv")
    history = [(int(row["step"]),float(row["time_s"]),float(row["tau_s"]),float(row["legacy_Tv"])) for row in rows]
    require([x[0] for x in history]==report["planned_steps"], "Particle clocks changed after review")
    expect = {f"PartFluid_{i:04d}.vtk" for i in range(len(history))}
    require({p.name for p in folder.glob("*.vtk")} <= expect, "Unreviewed VTK exists in release directory")
    entries, clocks = [], []
    for i, (step, t, tau, tv) in enumerate(history):
        raw = read_frame(report["input_files"][f"state_{step}.bin"])
        pos, fields = material_fields(raw,mesh)
        path = folder/f"PartFluid_{i:04d}.vtk"
        if not path.exists():
            temporary = path.with_suffix(".vtk.writing")
            with temporary.open("xb") as stream:
                for block in vtk_blocks(pos,fields):
                    stream.write(block)
            temporary.rename(path)
        with path.open("rb") as stream:
            check_vtk(stream,pos,fields)
        entries.append(dict(name=path.name,time=t))
        clocks.append(dict(part=i,step=step,time_s=t,tau_s=tau,Tv=tv,file=path.name))
    series = folder/"PartFluid.vtk.series"
    expected = {"file-series-version":"1.0", "files":entries}
    if series.exists():
        require(read_json(series)==expected, "Existing particle series differs")
    else:
        save(series,expected)
    sidecar = folder/"actual_times.csv"
    if sidecar.exists():
        require(read_csv(sidecar)==[{k:str(v) for k,v in r.items()} for r in clocks],
                "Existing particle clock sidecar differs")
    else:
        write_csv(sidecar,clocks)
    done = dict(nu=report["nu"],frames=len(history),materials=N,original_id_range=[8,37180],
                first_time_s=history[0][1],last_time_s=history[-1][1],fields=list(fields),
                native_review=identity(receipt),source=report["input_seal"],physical_acceptance=False,
                boundary_series=None,scope="No native Bound population. The drained surface belongs to PartFluid.")
    marker = folder/"postprocess_weak_vtk.json"
    if marker.exists():
        require(read_json(marker)==done, "Existing particle receipt differs")
    else:
        save(marker,done)
    return marker


def review(package:Path, output:Path, nu:float, planned_steps:list[int], dense_steps:list[int], *, particles=True):
    """Read actual raw states once for validation. Optional VTK export checks the same immutable inputs."""
    package, output = Path(package).resolve(), Path(output).resolve()
    require(nu in VARIANTS,"This reviewer covers the three new Poisson ratios")
    planned, dense_plan = list(planned_steps), list(dense_steps)
    dest = output/"review"
    ref = Reference(nu,modes=720,finite=False)
    targets = schedule(planned,dense_plan,ref.legacy_cv)
    seal, package_id, records = verify_seal(package,output,nu,planned,dense_plan,ref.legacy_cv)
    if (dest/"review.json").exists():
        result = read_json(dest/"review.json")
        require(result["input_seal"]==seal and result["package_manifest"]==package_id
                and result["input_files"]==records and result["nu"]==nu and result["planned_steps"]==planned
                and result["dense_steps"]==dense_plan and result["history"]==identity(dest/"actual_vs_theory.csv")
                and result["native_passed"] and all(identity(Path(x["path"]))==x for x in records.values())
                and all(identity(Path(x["path"]))==x for x in result["artifacts"]),
                "Existing native review differs from current inputs")
    else:
        require(not dest.exists(), "Preserve partial offline review before choosing a fresh revision")
        for n in ("complete.txt","actual_clock.csv","peak_history.csv","closed_gate.csv","material.csv"):
            require(identity(output/n)==records[n], f"Owned saved control changed: {n}")
        material = inspect_material(package,output,nu)
        ticks = read_csv(output/"actual_clock.csv", ("step","time_s","elapsed_s"))
        elapsed = [float(r["elapsed_s"]) for r in ticks]
        require(list(map(lambda r:int(r["step"]),ticks))==planned
                and all(float(r["time_s"])==step*DT for r,step in zip(ticks,planned,strict=True))
                and all(math.isfinite(t) and t>=0. for t in elapsed)
                and all(a<b for a,b in zip(elapsed,elapsed[1:])), "Actual solver clock differs from the plan")
        dense, peak = dense_review(read_csv(output/"peak_history.csv",DENSE_FIELDS),dense_plan,ref)
        mesh, mesh_id, centre, radius, det0 = load_mesh(package)
        rows, profiles, closed, overlap = native_rows(planned,records,targets,mesh,centre,radius,det0,dense,ref,peak)
        inspect_closed(output,closed)
        tail = [r for r in rows if r["target_Tv"] is not None and r["target_Tv"]>=.5]
        require(len(tail)==101 and tail[-1]["target_Tv"]==1.,"Incomplete full consolidation decay")
        p = np.array([r["center18_Pa"] for r in tail])
        u = np.array([r["surface_inward_mm"] for r in tail])
        require(identity(output/"server_run.json")==seal and identity(package/"manifest.json")==package_id
                and identity(package/"inputs/reference_mesh.npz")==mesh_id
                and all(identity(Path(x["path"]))==x for x in records.values()),"Inputs changed during review")
        dest.mkdir()
        write_csv(dest/"actual_vs_theory.csv",rows)
        write_csv(dest/"shell_profiles.csv",profiles)
        write_csv(dest/"peak_history.csv",dense)
        result = dict(mode="full",nu=nu,dt_s=DT,drainage_time_s=TD,full_cycle_measured=True,native_passed=True,
            physical_acceptance=False,steps=planned[-1],frames=len(rows),native_materials=N,
            drained_materials=len(mesh["native_surface"]),fixed_center_ids=mesh["native_ids"][centre].tolist(),
            actual_end_s=rows[-1]["time_s"],actual_end_legacy_Tv=rows[-1]["legacy_Tv"],actual_endpoint=rows[-1],
            minimum_tet_det_F=min(r["min_det_F"] for r in rows),maximum_tet_det_F=max(r["max_det_F"] for r in rows),
            legacy_cv_m2_s=ref.legacy_cv,peak_qualification=peak,closed_limits=CLOSED_LIMITS,closed_actual=closed,
            closed_pass=True,material=material,dense_and_native_common_samples=overlap,tail_frames=len(tail),
            tail_center_errors_Pa=residuals(p-[r["M0_center18_Pa"] for r in tail]),
            tail_surface_errors_mm=residuals(u-[r["M0_surface_inward_mm"] for r in tail]),
            center_rebound_intervals=int(np.sum(np.diff(p)>0)),largest_tail_pressure_rise_Pa=float(max(0.,np.diff(p).max())),
            settlement_decrease_intervals=int(np.sum(np.diff(u)<0)),ultimate_drained_surface_displacement_mm=1000.*R*Q/(3.*ref.K),
            planned_steps=planned,dense_steps=dense_plan,input_seal=seal,package_manifest=package_id,
            mesh=mesh_id,input_files=records,history=identity(dest/"actual_vs_theory.csv"),
            artifacts=[identity(path) for path in sorted(dest.iterdir())],
            scope="Fixed-reference small-strain M0, native masses, constant k. Geometry and drain checks are saved-state checks; no startup or tail accuracy threshold was added.")
        save(dest/"review.json",result)
    publish_figures(dest,ref,nu)
    if particles:
        export_particles(package,output,result)
    return result

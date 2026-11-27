"""Verify and publish the three C08 formal TPI collapse trajectories."""
import argparse
import csv
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from compare_lian_release import compare, front_panel, summarize
from plot_lian_release_fields import PANELS, plot_group
from postprocess_lian_release import (
    DP, FIELD_NAMES, GROUPS, PRE_IDS, RELEASE_IDS, SOIL_IDS, field_plot, history_plot,
    measures, native, require, stat_id, verify_source_material, vtk_particles, write_json,
)

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT/"figures/validation_tpi"
sys.path.insert(0, str(ROOT/"tests/support"))
from c08_psi25_tpi_native import DT, OPEN, SOURCE, check_state, expected_steps, inspect_log, read_frame

CAPS = {"short": OPEN+8, "fixture": OPEN+240_000, "full": OPEN+600_000}
RECEIPT = "postprocess_tpi.native.json"
HISTORY_SCHEME = "P3_B_alpha_half_beta_0p04"


def inspect_output(output, steps, cap, clock_end):
    files = sorted((output/"data").glob("Part_????.bi4"))
    require([p.name for p in files] == [f"Part_{i:04d}.bi4" for i in range(1, len(steps)+1)],
            "Incomplete or incompatible saved PART sequence")
    require((output/"data/Part_Head.ibi4").is_file(), "Missing original solver particle header")
    with (output/"Run.csv").open(encoding="utf-8-sig", newline="") as stream:
        summary, = csv.DictReader(stream, delimiter=";")
    require((int(summary["Steps"]), int(summary["PartFiles"]), int(summary["PartsOut"])) ==
            (cap, len(files)+1, 0) and abs(float(summary["PhysicalTime"])-clock_end) <= 5.01e-7,
            "Run.csv does not confirm the exact completed target")
    return files, summary


def identities(files):
    return [[str(p), *stat_id(p)] for p in files]


def read_original_pre(group):
    pre = ROOT/f"CaseLianCollapse_{group}_pre_GPU_out"
    prov = json.loads((pre/"provenance.json").read_text(encoding="utf-8-sig"))
    require((prov.get("group"), prov.get("stage"), prov.get("state")) == (group,"preload","completed"),
            "Unbound original preload provenance")
    refpath = pre/"data/Part_1000.bi4"
    m, a = native(refpath)
    verify_source_material(m, group)
    require(m["Cpart"]==1000 and m["Step"]+1==SOURCE and m["TimeStep"]==9.999999999706008 and
            m["GravityPreloadPhase"]==0 and m["GravityPreloadTargetIdBegin"]==1805 and
            m["GravityPreloadTargetIdCount"]==255 and m["GravityPreloadReleaseMkBound"]==2 and
            m["Npok"]==len(PRE_IDS) and m["Nout"]==0 and np.array_equal(a["Idp"], PRE_IDS),
            "Wrong closed wall handoff identity or phase")
    initial_path = pre/"data/Part_0000.bi4"
    origin, landmarks = native(initial_path)
    require(origin["Cpart"]==0 and origin["TimeStep"]==0 and np.array_equal(landmarks["Idp"],PRE_IDS),
            "Invalid initial material registration")
    z = landmarks["Posd"][SOIL_IDS,2]
    top, bottom = (abs(z-v)<DP/4 for v in (z.max(),z.min()))
    require(top.sum()==bottom.sum()==100, "Unexpected initial boundary soil rows")
    return refpath, initial_path, m, a, top, bottom


def verify_frame(m, hist, group, step, part, clock, reference, *, dt=DT, open_step=OPEN):
    active = step>open_step
    require(m["Cpart"]==part and m["Step"]+1==step and m["TimeStep"]==clock[step-SOURCE] and
            m["HydroMechModel"]==2 and m.get("HydroMechTpiR",1.0)==1.0 and m["MaterialLawVersion"]==2 and
            m["DilationDecay"]==np.float32(GROUPS[group][2]) and m["HydroMechFreeSeepage"] and
            m["HydroMechConductivityModel"]==1 and m["HydroMechConductivityCk"]==2 and
            m["SymplecticDtPre"]==m["dtmin"]==m["dtmax"]==dt and
            -np.finfo(float).max<m["dterror"]<=1e-14, f"Material, case or signed timing at PART {part}")
    require(m["GravityPreloadPhase"]==active and m["GravityPreloadEventCompletedStep"]==open_step and
            m["GravityPreloadReleaseMkBound"]==2 and m["GravityPreloadTargetIdBegin"]==1805 and
            m["GravityPreloadTargetIdCount"]==255 and not m.get("GravityPreloadKeepBedOverlap",False) and
            (ROOT/Path(m["GravityPreloadStateFile"])).resolve()==reference and
            m["SoilDampingActive"]==(not active) and m["PoreShepardActive"]==(not active) and
            m["DynamicArtificialStressPolicy"]=="ReleaseOnly" and
            m["DynamicArtificialStressActive"]==active and
            m["DynamicArtificialStressCoef"]==np.float32(.3) and
            m["DynamicArtificialStressExp"]==np.float32(2.55) and
            m["DynamicNoPenetrationPolicy"]=="FixedPlaneStageProjectionReleaseOnly" and
            m["DynamicNoPenetrationActive"]==active and not m["DynamicNoPenetrationReactionClosed"],
            f"Free surface policy, released MK or PRE/SOIL binding at PART {part}")
    if active:
        require(m["GravityPreloadActualTime"]==clock[open_step-SOURCE] and
                m["GravityPreloadActualCompletedStep"]==open_step, "Unexpected actual wall release")
    require(hist["CompletedUpdates"]==step and hist["Dt"]==dt and hist["Valid"] and hist["Schema"]==1 and
            hist["Scheme"]==HISTORY_SCHEME and hist["PreviousTime"]==clock[step-SOURCE-1] and
            hist["SavedTime"]==m["TimeStep"], "Native TPI pressure history scheme or clock differs")


def short_prefix(path, group, reference):
    receipt = json.loads((path/RECEIPT).read_text(encoding="utf8"))
    count = len(expected_steps(CAPS["short"]))
    require((receipt["passed"], receipt["group"], receipt["window"], receipt["preload"], receipt["frames"]) ==
            (True, group, "short", str(reference), count), "Standalone TPI short review does not match")
    original = [Path(item[0]) for item in receipt["inputs"]]
    files = sorted((path/"data").glob("Part_????.bi4"))
    require(receipt["inputs"]==identities(original) and len(files)==count and
            all(p in original for p in files), "Reviewed short-window artifacts changed")
    return files


def review(group, output, window="full", short=None):
    """Return full native history and its receipt after read-only verification."""
    output = Path(output).resolve()
    cap = CAPS[window]
    steps = expected_steps(cap)
    refpath, initial_path, prem, ref, top, bottom = read_original_pre(group)
    clock = np.cumsum(np.r_[prem["TimeStep"], np.full(cap-SOURCE, DT)])
    release_time = float(clock[OPEN-SOURCE])
    files, run = inspect_output(output, steps, cap, float(clock[-1]))
    if window=="full":
        require(short is not None, "Full review needs the same branch's completed independent short window")
    prefix = short_prefix(Path(short).resolve(), group, refpath) if short else []
    sealed = [refpath, initial_path, output/"Run.csv", output/"Run.out", output/"data/Part_Head.ibi4", *files]
    binding = identities(sealed)
    prior_p = ref["PorePress"][SOIL_IDS]
    prior_k = ref["Kplastic"][SOIL_IDS]
    last, adjacent = SOURCE, 0
    rows = []
    for part, (file, step) in enumerate(zip(files, steps, strict=True), 1):
        m, a, hist, prev = read_frame(file)
        verify_frame(m, hist, group, step, part, clock, refpath)
        active = step>OPEN
        fs = check_state(m, a, ref, prior_k, active)
        require(fs.any(), f"Missing active free surface in {file.name}")
        if last+1==step:
            require(prev.tobytes()==prior_p.tobytes(), f"Previous pressure does not match adjacent {file.name}")
            adjacent += 1
        if part<=len(prefix):
            old, old_a, old_hist, old_prev = read_frame(prefix[part-1])
            keys = ("Step","TimeStep","dterror","dtmin","dtmax","SymplecticDtPre")
            require(all(np.asarray(old[k]).tobytes()==np.asarray(m[k]).tobytes() for k in keys) and
                    all(np.asarray(old_hist[k]).tobytes()==np.asarray(hist[k]).tobytes() for k in
                        ("PreviousTime","SavedTime","Dt","CompletedUpdates","Scheme")) and
                    all(value.tobytes()==old_a[k].tobytes() for k,value in a.items()) and
                    old_prev.tobytes()==prev.tobytes(), f"Short/full trajectory mismatch at {file.name}")
        time = float(m["TimeStep"])
        row, _, _, _, pressure, _ = measures(a,ref,top,bottom,part,time,time-release_time)
        area = a["PoroCurrentVolume"][-len(SOIL_IDS):]
        perm = np.argsort(pressure, kind="stable")
        cum = np.cumsum(area[perm])
        row.update(completed_step=step, saved_step=step-1, released=int(active), signed_dterror_s=float(m["dterror"]),
                   p_area_p05_kPa=pressure[perm[np.searchsorted(cum,.05*cum[-1])]],
                   p_negative_area_pct=100*area[pressure<0].sum()/cum[-1],
                   p_below_minus5_area_pct=100*area[pressure<-5].sum()/cum[-1],
                   free_surface_count=int(fs.sum()), free_surface_negative_count=int(np.sum(pressure[fs]<0)),
                   free_surface_min_kPa=pressure[fs].min(), free_surface_max_kPa=pressure[fs].max())
        rows.append(row)
        prior_p, prior_k, last = a["PorePress"][-len(SOIL_IDS):], a["Kplastic"][-len(SOIL_IDS):], step
    stats = inspect_log(output/"Run.out", cap)
    require(identities(sealed)==binding and adjacent==11, "Inputs changed or adjacent pressure history is missing")
    receipt = dict(passed=True, group=group, window=window, inputs=binding, preload=str(refpath),
                   frames=len(rows), source_time_s=float(clock[0]), release_time_s=release_time,
                   end_s=float(clock[-1]), cap=cap, adjacent_history=adjacent, prefix_frames=len(prefix),
                   beta=.04, pressure_surface_policy="PositiveOnlyCap", physical_acceptance=False,
                   hardware=run["Hardware"], loop_wall_s=float(run["TSimul"]), **stats)
    return rows, receipt


def write_csv(path, rows):
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def verify_particle_vtk(path, positions, fields):
    """Compare the existing binary VTK to native geometry, cells and every field."""
    with path.open("rb") as stream:
        def line(expected):
            require(stream.readline().rstrip(b"\r\n")==expected.encode("ascii"),
                    f"VTK header differs: {path}: {expected}")

        def payload(values, dtype):
            expected = np.asarray(values, dtype=dtype, order="C").tobytes()
            require(stream.read(len(expected))==expected and stream.read(1)==b"\n",
                    f"VTK payload differs: {path}")

        n = len(positions)
        for text in ("# vtk DataFile Version 3.0", "C08 saved material particles; SI units",
                     "BINARY", "DATASET POLYDATA", f"POINTS {n} double"):
            line(text)
        payload(positions, ">f8")
        line(f"VERTICES {n} {2*n}")
        payload(np.column_stack((np.ones(n, dtype="i4"), np.arange(n, dtype="i4"))), ">i4")
        line(f"POINT_DATA {n}")
        line(f"FIELD FieldData {len(fields)}")
        for name, values in fields.items():
            comps = 1 if values.ndim==1 else values.shape[1]
            typ = {"u4":"unsigned_int", "f4":"float", "f8":"double"}[values.dtype.str[1:]]
            line(f"{name} {comps} {n} {typ}")
            payload(values, values.dtype.newbyteorder(">"))
        require(not stream.read(1), f"Unexpected trailing VTK data: {path}")


def export_particles(group, output, receipt, check_only=False, *, dt=DT, open_step=OPEN, planned_steps=None):
    """Resume flat Fluid/Bound VTKs; verify and migrate retained nested files without overwriting."""
    output = Path(output).resolve()
    require(receipt["passed"] and receipt["group"]==group and receipt["window"]=="full",
            "Particle export needs this group's completed native review")
    bound = [Path(item[0]) for item in receipt["inputs"]]
    require(identities(bound)==receipt["inputs"], "Native output changed since review")
    refpath, _, prem, ref, _, _ = read_original_pre(group)
    cap = receipt["cap"]
    require((dt==DT and open_step==OPEN and cap==CAPS["full"]) or planned_steps is not None,
            "A different full-run clock needs its explicit saved-step sequence")
    steps = expected_steps(cap) if planned_steps is None else planned_steps
    require(dt>0 and SOURCE<open_step<cap and len(steps)>0 and steps[-1]==cap and
            all(SOURCE<=a<b for a,b in zip([SOURCE,*steps[:-1]],steps,strict=True)),
            "Invalid full-run saved-step sequence")
    clock = np.cumsum(np.r_[prem["TimeStep"], np.full(cap-SOURCE, dt)])
    release_time = float(clock[open_step-SOURCE])
    files, _ = inspect_output(output, steps, cap, float(clock[-1]))
    require(receipt["frames"]==len(files) and receipt["preload"]==str(refpath) and
            receipt["release_time_s"]==release_time and receipt["end_s"]==float(clock[-1]),
            "Particle export clock or source differs from reviewed run")
    dest = output/"particles"
    manifests = {"PartFluid":[], "PartBound":[]}
    names = ("Idp", "Vel", "PorePress", "PorePress0", "ExcessPorePress", "Kplastic",
             "SigmaState_kk", "SigmaState_ij", "PoroVolumeRatio", "PoroPorosity",
             "PoroHydraulicConductivity", "PoroMixtureDensity", "FSType")
    if not check_only:
        dest.mkdir(parents=True, exist_ok=True)
    for label in manifests:
        expected = {f"{label}_{part:04d}.vtk" for part in range(1,len(files)+1)}
        require({p.name for p in dest.glob(f"{label}_*.vtk")}<=expected,
                f"Unexpected particle frames in {dest}")
    created = moved = duplicates = 0
    for part, (file, step) in enumerate(zip(files, steps, strict=True), 1):
        m, a, hist, _ = read_frame(file)
        verify_frame(m,hist,group,step,part,clock,refpath,dt=dt,open_step=open_step)
        require(np.array_equal(a["Idp"], RELEASE_IDS if step>open_step else PRE_IDS),
                f"Particle registry differs: {file}")
        soil, fixed = slice(-len(SOIL_IDS),None), slice(None,-len(SOIL_IDS))
        fluid = {name:a[name][soil] for name in names}
        fluid["Displacement"] = a["Posd"][soil]-ref["Posd"][SOIL_IDS]
        ids = a["Idp"][fixed]
        boundary = {"Idp":ids, "MkBound":np.searchsorted([255,1805],ids,side="right").astype("u4")}
        for label, subset, fields in (("PartFluid",soil,fluid), ("PartBound",fixed,boundary)):
            path = dest/f"{label}_{part:04d}.vtk"
            legacy = dest/label/path.name
            if path.exists():
                verify_particle_vtk(path,a["Posd"][subset],fields)
            if legacy.exists():
                verify_particle_vtk(legacy,a["Posd"][subset],fields)
                require(not check_only, f"Verified nested VTK still needs migration: {legacy}")
                if path.exists():
                    legacy.unlink()  # Both files were compared to the same native payload above.
                    duplicates += 1
                else:
                    legacy.rename(path)
                    moved += 1
            if not path.exists():
                require(not check_only, f"Missing particle VTK: {path}")
                vtk_particles(path,a["Posd"][subset],fields)
                verify_particle_vtk(path,a["Posd"][subset],fields)
                created += 1
            manifests[label].append({"name":path.name,"time":float(m["TimeStep"])-release_time})
        if part%50==0 or part==len(files):
            print(f"  Particle VTK verified {part}/{len(files)} frames",flush=True)
    require(identities(bound)==receipt["inputs"], "Native input changed during particle export")
    for label, items in manifests.items():
        series = dest/f"{label}.vtk.series"
        legacy = dest/label/series.name
        expected = {"file-series-version":"1.0", "files":items}
        lookup = {item["name"]:item for item in items}
        current = None
        for path in (series,legacy):
            if path.exists():
                saved = json.loads(path.read_text(encoding="utf8"))
                require(saved.get("file-series-version")=="1.0" and
                        all(lookup.get(item["name"])==item for item in saved["files"]),
                        f"Existing series has incompatible times or names: {path}")
                if path==series:
                    current = saved
        if check_only:
            require(current==expected and not legacy.exists(), f"Incomplete flat particle series: {series}")
        else:
            if current!=expected:
                write_json(series,expected)
            if legacy.exists():
                legacy.unlink()  # A matching flat collection now covers every retained frame.
            folder = dest/label
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
    result = dict(group=group,layout="flat",frames_per_series=len(files),first_part=1,last_part=len(files),
                  dt_s=dt,release_completed_step=open_step,completed_step=cap,
                  time_origin_s=release_time,first_tau_s=manifests["PartFluid"][0]["time"],
                  last_tau_s=manifests["PartFluid"][-1]["time"],
                  verification="All coordinates, vertex cells and point fields match native values byte for byte.")
    if not check_only:
        marker = dest/"postprocess_tpi.vtk.json"
        if not marker.exists() or json.loads(marker.read_text(encoding="utf8"))!=result:
            write_json(marker,result)
    print(json.dumps(dict(**result,new_vtk_files=created,moved_vtk_files=moved,
                          removed_verified_duplicates=duplicates),indent=2))

def material_snapshots(group, output, rows, figdir):
    _, _, _, ref, top, bottom = read_original_pre(group)
    requested = set((*PANELS[group][2], .01, .30, .50, .60, .88, 1.20))
    if abs(rows[-1]["tau_s"]-3.0)<1e-8:
        requested.add(3.0)
    requested = sorted(requested)
    chosen = [min(rows, key=lambda r: abs(r["tau_s"]-time)) for time in requested]
    require(all(abs(row["tau_s"]-time)<1e-8 for time,row in zip(requested,chosen,strict=True)),
            "Missing published or diagnostic save time")
    snapshots, fields = [], []
    for row in chosen:
        part, time, tau = (row[k] for k in ("part","time_s","tau_s"))
        _, a, _, _ = read_frame(output/"data"/f"Part_{part:04d}.bi4")
        _, disp, eff, total, p, excess = measures(a,ref,top,bottom,part,time,tau)
        t = slice(-len(SOIL_IDS), None)
        pos, vel = a["Posd"][t], a["Vel"][t]
        payload = np.column_stack((SOIL_IDS,pos[:,0],pos[:,2],disp[:,0],disp[:,2],vel[:,0],vel[:,2],
            p,a["PorePress0"][t]*.001,excess,eff[:,0],eff[:,2],total,a["Kplastic"][t],a["PoroVolumeRatio"][t],
            a["PoroPorosity"][t],a["PoroHydraulicConductivity"][t],a["PoroMixtureDensity"][t],a["FSType"][t]))
        fields.extend(dict(part=part,time_s=time,tau_s=tau,**dict(zip(FIELD_NAMES,
                      [int(values[0]),*map(float,values[1:-1]),int(values[-1])],strict=True))) for values in payload)
        if any(abs(tau-v)<1e-8 for v in {*PANELS[group][2],3.0}):
            snapshots.append((tau,payload))
    write_csv(figdir/"fields.csv", fields)
    return snapshots


def plots(group, rows, figdir):
    with (ROOT/"support/lian_collapse_fronts.csv").open(encoding="utf-8-sig",newline="") as f:
        refs = list(csv.DictReader(f))
    h = np.genfromtxt(figdir/"history.csv",delimiter=",",names=True,encoding="utf8")
    comparisons = compare(group,h,refs)
    fig, ax = plt.subplots(figsize=(6.2,3.8),layout="constrained")
    front_panel(ax,group,h,comparisons)
    fig.savefig(figdir/"paper_front.png",dpi=180)
    plt.close(fig)
    write_csv(figdir/"paper_front.csv",comparisons)
    write_csv(figdir/"release_summary.csv",[summarize(group,h)])
    plot_group(group,figdir)
    if group=="psi2p5":
        paper_gauge_pressure(figdir)


def paper_gauge_pressure(figdir):
    """Use the printed colorbar for the gauge-pressure panels in Fig. 16."""
    from matplotlib.colors import ListedColormap, Normalize
    from c08_psi25_tpi_fields import CACHE, FIG16_TIMES, PDF, load_pages, palette_limits, paper_panels

    page, _ = load_pages(CACHE, PDF)
    fields = np.genfromtxt(figdir/"fields.csv", delimiter=",", names=True, encoding="utf8",
                           usecols=("part","time_s","tau_s","x_m","z_m","p_kPa"))
    times = np.unique(fields["tau_s"])
    paper_times = tuple(FIG16_TIMES)
    fig, axes = plt.subplots(len(paper_times), 3, figsize=(11.8,6.1), layout="constrained",
                             sharex=True, sharey=True)
    records = []
    for row, (time, row_axes) in enumerate(zip(paper_times, axes, strict=True)):
        tau = times[np.argmin(abs(times-time))]
        saved = fields[fields["tau_s"]==tau]
        require(abs(tau-time)<1e-8 and saved.size==len(SOIL_IDS), "Fig. 16 needs the exact saved soil frame")
        pressure = saved["p_kPa"]
        palette, lo, hi = palette_limits(page,"p",time)
        cmap, norm = ListedColormap(palette/255), Normalize(lo,hi)
        for ax, (label,image,extent) in zip(row_axes[:2],paper_panels(page,"p",time),strict=True):
            ax.imshow(image,extent=extent,origin="upper",interpolation="nearest")
            if row==0:
                ax.set_title(label)
        cloud = row_axes[2].scatter(saved["x_m"],saved["z_m"],c=pressure,s=1.5,linewidths=0,cmap=cmap,norm=norm)
        if row==0:
            row_axes[2].set_title("C08 TPI  β = 0.04")
        for ax in row_axes:
            ax.set_aspect("equal", adjustable="box")
            ax.set_xlim(-.08,8.08)
            ax.set_ylim(-.04,2.12)
            if row==len(paper_times)-1:
                ax.set_xlabel("x (m)")
        row_axes[0].set_ylabel(f"{time:g} s\nz (m)")
        records.append(dict(paper_tau_s=time,native_tau_s=tau,part=int(saved["part"][0]),
                            actual_time_s=saved["time_s"][0],native_min_kPa=pressure.min(),
                            native_max_kPa=pressure.max(),display_min_kPa=lo,display_max_kPa=hi,
                            below_count=int(np.sum(pressure<lo)),above_count=int(np.sum(pressure>hi)),
                            outside_plot_xz_count=int(np.sum((saved["x_m"]<-.08)|(saved["x_m"]>8.08)|
                                                            (saved["z_m"]<-.04)|(saved["z_m"]>2.12))),
                            soil_count=len(pressure)))
    fig.suptitle("Gauge pore pressure  |  ψ = +2.5°  |  Lian et al. (2023), Fig. 16")
    fig.colorbar(cloud,ax=axes.flatten(),orientation="horizontal",pad=.015,shrink=.59,
                 ticks=(-10,0,10,20),extend="both",label="Gauge pore pressure (kPa)")
    fig.savefig(figdir/"lian_fig16_gauge_pressure.png",dpi=180)
    plt.close(fig)
    write_csv(figdir/"lian_fig16_gauge_pressure.csv",records)


def publish(output, rows, receipt):
    group = receipt["group"]
    figdir = FIGURES/group
    output = Path(output).resolve()
    bound = [Path(item[0]) for item in receipt["inputs"]]
    require(identities(bound)==receipt["inputs"], "Native output changed before publication")
    figdir.mkdir(parents=True,exist_ok=True)
    marker = figdir/"postprocess.json"
    start = output/"postprocess_tpi.inputs.json"
    if start.exists():
        require(json.loads(start.read_text(encoding="utf8"))==receipt, "Derived output binds a different native run")
    else:
        require(not any(figdir.iterdir()) and not (output/"particles").exists(),
                "Unexpected existing figure or particle outputs")
        write_json(start,receipt)
    write_csv(figdir/"history.csv",rows)
    snapshots = material_snapshots(group,output,rows,figdir)
    history_plot(figdir,group,False,rows)
    field_plot(figdir,snapshots,group,False)
    plots(group,rows,figdir)
    require(identities(bound)==receipt["inputs"], "Native input changed during publication")
    export_particles(group,output,receipt)
    write_json(marker,receipt)


def publish_all():
    """Use only previously published and bound formal histories."""
    from compare_lian_release import GROUPS as PRESENTATION
    groups = tuple(GROUPS)
    histories, matches, summaries, step_sizes = {},{},[],{}
    smaller_step = FIGURES/"psim5_dt25"
    for group in groups:
        dest = smaller_step if group=="psim5" and (smaller_step/"postprocess.json").is_file() else FIGURES/group
        audit = json.loads((dest/"postprocess.json").read_text(encoding="utf8"))
        require(audit["group"]==group and audit["window"]=="full" and audit["passed"] and
                identities([Path(item[0]) for item in audit["inputs"]])==audit["inputs"],
                f"Missing or changed completed formal trajectory for {group}")
        histories[group] = np.genfromtxt(dest/"history.csv",delimiter=",",names=True,encoding="utf8")
        require(histories[group].size==audit["frames"] and
                histories[group][-1]["time_s"]==audit["end_s"], "Invalid published history")
        with (dest/"paper_front.csv").open(encoding="utf8",newline="") as f:
            matches[group] = [{**r, **{k:float(r[k]) for k in
                ("requested_tau_s","published_extent_m","paper_digitization_scale_m")}} for r in csv.DictReader(f)]
        step_sizes[group] = float(audit.get("dt_s",DT))
        require(step_sizes[group]==(DT/2 if dest==smaller_step else DT),
                f"Unexpected fixed step for {group}")
        summaries.append(dict(**summarize(group,histories[group]),dt_s=step_sizes[group]))
    fig, axes = plt.subplots(1,3,figsize=(13.2,4),sharex=True,layout="constrained")
    for ax,g in zip(axes,groups,strict=True):
        front_panel(ax,g,histories[g],matches[g])
        ax.set_title(f"{ax.get_title()} ({step_sizes[g]*1e6:g} ?s)")
    fig.savefig(FIGURES/"paper_fronts.png",dpi=180)
    plt.close(fig)
    panels = {"top_settlement_mm":"Top material settlement (mm)",
              "p_area_p05_kPa":"Area-weighted pressure P05 (kPa)",
              "p_below_minus5_area_pct":"Soil area below −5 kPa (%)",
              "nearest_below_half_dp":"Soil particles with nearest spacing < 0.5 dp"}
    fig, axes = plt.subplots(2,2,figsize=(10.8,7),sharex=True,layout="constrained")
    for ax, (key,label) in zip(axes.flat,panels.items(),strict=True):
        for g,h in histories.items():
            angle,color = PRESENTATION[g]
            ax.plot(h["tau_s"],h[key],color=color,lw=1.4,label=f"{angle}, {step_sizes[g]*1e6:g} ?s")
        ax.set_ylabel(label)
        ax.grid(alpha=.2)
    axes[0,0].legend(frameon=False)
    for ax in axes[-1]:
        ax.set_xlabel("Time since wall release (s)")
    fig.savefig(FIGURES/"material_histories.png",dpi=180)
    plt.close(fig)
    write_csv(FIGURES/"paper_fronts.csv",[row for group in groups for row in matches[group]])
    write_csv(FIGURES/"release_summary.csv",summaries)
    write_csv(FIGURES/"material_histories.csv",[dict(group=g,tau_s=row["tau_s"],**{k:row[k] for k in panels})
                                                    for g,h in histories.items() for row in h])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group",choices=(*GROUPS,"all"))
    parser.add_argument("output",type=Path,nargs="?")
    parser.add_argument("--window",choices=CAPS,default="full")
    parser.add_argument("--short",type=Path)
    particles = parser.add_mutually_exclusive_group()
    particles.add_argument("--particles-only",action="store_true",
                           help="Resume all VTK frames from an existing native receipt; do not rewrite figures")
    particles.add_argument("--check-particles",action="store_true",
                           help="Read-only byte verification of all VTK frames and their actual-time series")
    args = parser.parse_args()
    if args.group=="all":
        require(args.output is None and args.short is None and args.window=="full" and
                not (args.particles_only or args.check_particles), "all combines existing groups")
        publish_all()
        return
    require(args.output is not None,"Select a bound output directory")
    output = args.output.resolve()
    if args.particles_only or args.check_particles:
        require(args.window=="full" and args.short is None, "Particle-only modes use a completed full native receipt")
        receipt = json.loads((output/RECEIPT).read_text(encoding="utf8"))
        export_particles(args.group,output,receipt,check_only=args.check_particles)
        return
    if args.window=="fixture":
        require(args.group=="psi2p5","The retained paper-window fixture is for +2.5 degrees")
    rows, receipt = review(args.group,output,args.window,args.short)
    if args.window=="fixture":
        print({k:v for k,v in receipt.items() if k!="inputs"})
        return
    marker = output/RECEIPT
    if marker.exists():
        require(json.loads(marker.read_text(encoding="utf8"))==receipt,"Existing native receipt changed")
    else:
        write_json(marker,receipt)
    if args.window=="full":
        publish(output,rows,receipt)
    print(marker)


if __name__=="__main__":
    main()

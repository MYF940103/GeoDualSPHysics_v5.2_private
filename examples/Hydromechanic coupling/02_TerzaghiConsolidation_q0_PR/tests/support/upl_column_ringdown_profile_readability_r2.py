"""Style-only profile redraw from the sealed r1 CSV; no native data reduction or new result."""
import csv, hashlib, json
from pathlib import Path
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG = "upl_column_ringdown_profile_readability_r2"
PARENT = T / "logs/upl_column_ringdown_on_off_r1.check.json"
CSV = T / "figures/upl_column_ringdown_on_off_r1_profiles.csv"
PINS = {str(PARENT): "a7fcdf76854994c35549b5a13eb60759dffa1a82ac0cb0a324a5ba9e2a6dd971",
        str(CSV): "1a31069a85c2cbd0ff18f8dd71177bc8fbc751fcda31e9bc80d6421b087b9caf"}
TIMES = (0.015625, 0.0625, 0.125)
SERIES = (("ON", "coarse", "#2166ac", "-", "ON coarse"), ("ON", "half", "#67a9cf", "--", "ON half"),
          ("OFF", "coarse", "#b35806", "-", "OFF coarse"), ("OFF", "half", "#e08214", "--", "OFF half"))
FIELDS = ("model", "grid", "part", "actual_time_s", "initial_material_layer", "initial_z_m", "pressure_mean_Pa", "settlement_mean_mm", "stored_compression_zz_mean_Pa", "velocity_XYZ_RMS_m_s")
TRACKED = {}

def need(ok, why):
    if not bool(ok): raise ValueError(why)
def entry(path):
    p = Path(path).resolve(); digest = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""): digest.update(block)
    return dict(path=str(p), bytes=p.stat().st_size, sha256=digest.hexdigest())
def bind(e):
    p = str(Path(e["path"]).resolve())
    if p not in TRACKED: TRACKED[p] = entry(p)
    need(TRACKED[p] == e, "Changed/conflicting bound input: " + p)
    return Path(p)
def adopt(path):
    e = entry(path); bind(e); return e

def main():
    png = T / "figures" / (TAG + "_profiles.png"); check = T / "logs" / (TAG + ".check.json")
    need(not png.exists() and not check.exists(), "Retained output protected")
    result = dict(stage=TAG, passed=False, physical_acceptance=False, style_only=True, solver_reader_or_build_invoked=False,
                  fresh_raw_reduction_performed=False, inherited_r1_visual_tick_issue_only=True, failure=None)
    parent_entry = csv_entry = None; local_inputs = []
    try:
        local_inputs = [adopt(__file__), adopt(T / "notes" / (TAG + ".json"))]
        parent_entry = adopt(PARENT); need(parent_entry["sha256"] == PINS[str(PARENT)], "Sealed r1 check changed")
        proof = json.loads(bind(parent_entry).read_text(encoding="utf-8-sig"))
        need(proof["stage"] == "upl_column_ringdown_on_off_r1" and proof["passed"] is True and proof["physical_acceptance"] is False and proof["descriptive_framework_comparison_only"] is True and proof["new_ON_OFF_accuracy_gate"] is False, "Accepted descriptive r1 prerequisite rejected")
        need(proof["trajectories"] == 4 and proof["samples_each"] == 1277 and proof["native_count"] == 1000 and proof["profile_rows"] == 1200 and proof["actual_profile_times_s"] == list(TIMES), "Sealed profile coverage differs")
        for e in proof["inputs"] + proof["files"]: bind(e)
        matches = [e for e in proof["files"] if Path(e["path"]).resolve() == CSV.resolve()]
        need(len(matches) == 1, "Profile CSV not uniquely owned by r1 check")
        csv_entry = matches[0]; need(csv_entry["sha256"] == PINS[str(CSV)], "Sealed r1 CSV changed")
        groups = {(model, grid, time): [] for model, grid, *_ in SERIES for time in TIMES}
        with bind(csv_entry).open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f); need(tuple(reader.fieldnames) == FIELDS, "Original profile CSV header differs")
            for row in reader:
                time = float(row["actual_time_s"]); key = (row["model"], row["grid"], time)
                need(key in groups and int(row["part"]) == {TIMES[0]:380, TIMES[1]:764, TIMES[2]:1276}[time], "Actual profile time/part/series differs")
                groups[key].append([int(row["initial_material_layer"])] + [float(row[k]) for k in FIELDS[5:]])
        for key, rows in groups.items():
            a = np.asarray(rows, dtype=float)
            need(a.shape == (100,6) and np.isfinite(a).all() and np.array_equal(a[:,0], np.arange(100)), "Complete original100-layer profile missing")
            groups[key] = a
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.ticker import MaxNLocator, ScalarFormatter
        plt.rcParams.update({"font.size":10, "axes.grid":True, "grid.alpha":0.25})
        fig, axes = plt.subplots(4,3,figsize=(13,11),sharey=True)
        variables = ((2,"Pore pressure (Pa)"), (3,"Settlement, down positive (mm)"), (4,"Stored compression -sigma_zz (Pa)"), (5,"Layer XYZ speed RMS (m/s)"))
        for col, time in enumerate(TIMES):
            axes[0,col].set_title("Actual t = " + format(time,".6g") + " s")
            for model, grid, color, style, label in SERIES:
                a = groups[model,grid,time]
                for row, (column, xlabel) in enumerate(variables):
                    line, = axes[row,col].plot(a[:,column],a[:,1],color=color,linestyle=style,linewidth=1.3,label=label)
                    need(np.array_equal(line.get_xdata(),a[:,column]) and np.array_equal(line.get_ydata(),a[:,1]), "Rendered data changed")
            for row, (_, xlabel) in enumerate(variables):
                ax = axes[row,col]; ax.set_xlabel(xlabel); ax.xaxis.set_major_locator(MaxNLocator(nbins=3,min_n_ticks=2))
                formatter = ScalarFormatter(useOffset=False,useMathText=True)
                if row == 3: formatter.set_powerlimits((0,0))
                ax.xaxis.set_major_formatter(formatter); ax.tick_params(axis="x",labelsize=9,pad=3)
        for ax in axes[:,0]: ax.set_ylabel("Initial material height z0 (m)")
        fig.suptitle("Same-setting ON/OFF: actual saved-time material-layer profiles",y=0.995)
        fig.legend(*axes[0,0].get_legend_handles_labels(),ncol=4,loc="upper center",bbox_to_anchor=(0.5,0.967))
        fig.text(0.5,0.012,"Each point is the arithmetic mean (speed: RMS) of the10 original material IDs in one layer; no time interpolation/smoothing.\nMaster switch changes full J-inertia/quadrature, Darcy and closed-FS closure together. No ON/OFF accuracy gate.",ha="center",fontsize=9)
        fig.tight_layout(rect=(0,0.06,1,0.925)); fig.canvas.draw()
        visible_ticks = [sum(ax.get_xlim()[0] <= tick <= ax.get_xlim()[1] for tick in ax.get_xticks()) for ax in axes.flat]
        for col, time in enumerate(TIMES):
            for row, (column, _) in enumerate(variables):
                values = np.concatenate([groups[model,grid,time][:,column] for model,grid,*_ in SERIES]); lo,hi=axes[row,col].get_xlim()
                need(lo <= float(values.min()) and hi >= float(values.max()), "Autoscale clips original profile values")
        fig.savefig(png,dpi=180); plt.close(fig)
        for e in TRACKED.values(): need(entry(e["path"]) == e, "Input changed during style-only render")
        result.update(passed=True,source_check=parent_entry,source_csv=csv_entry,source_rows=1200,profiles=12,layers_each=100,actual_profile_times_s=list(TIMES),
                      inherited_binding_count=len(TRACKED)-len(local_inputs)-1,all_parent_flat_inputs_and_files_rehashed_before_and_after=True,
                      unchanged_source_csv=True,duplicate_CSV_created=False,r1_history_unchanged=True,r1_PNGs_unchanged=True,
                      locator_nbins=3,visible_x_ticks_by_row_major_axis=list(map(int,visible_ticks)),velocity_scientific_notation=True,offset_disabled=True,
                      all_original_profile_values_rendered=True,smoothing_interpolation_or_clipping=False,new_numerical_or_physical_gate=False,visual_review_performed=False)
    except Exception as exc: result["failure"] = str(exc)
    result.update(inputs=local_inputs+([parent_entry] if parent_entry else [])+([csv_entry] if csv_entry else []),files=[entry(png)] if png.exists() else [])
    with check.open("x",encoding="utf-8") as f: json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
    print(json.dumps(dict(passed=result["passed"],check=str(check))))
    return 0 if result["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())

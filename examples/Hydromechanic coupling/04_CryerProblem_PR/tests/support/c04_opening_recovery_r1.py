"""Compare the actual native-mass weak and original P3 fields through the saved peak window."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from time import perf_counter

from cryer_shell_equilibrium import TESTS, Q, R, Reference, need, np, pd, plt, reference_fields
from cryer_weak_angular_fields import native

TAG = "c04_opening_recovery_r1"
FIG = TESTS / "figures"
OUT = TESTS / "outputs"
RUN = "CaseCryer_TPI_P3_nu030_peak_r1_GPU_out"
PHYS = FIG / "cryer_p3_server_peak_actual_r1/physical"
SHELL_FILES = [OUT / name / "shells.csv" for name in ("cryer_weak_open_r1", "cryer_weak_peak_r1")]
PAIR = FIG / "cryer_weak_3d_peak_r1.csv"
EARLY = FIG / "cryer_weak_geovol_open_r1.csv"
GEOM = OUT / "cryer_tet_reference_r1.npz"
DT = 2.0**-19


def table(path):
    return pd.read_csv(path, float_precision="round_trip")


def rms(values):
    return float(np.sqrt(np.mean(np.square(values))))


def reconstruction():
    a, b = (table(path) for path in SHELL_FILES)
    need(np.array_equal(a[a.step == 4160].values, b[b.step == 4160].values), "Shell restart seam")
    weak = pd.concat((a[(a.step >= 4096) & (a.step < 4160)], b))
    pair = table(PAIR).set_index("step")
    first = table(EARLY).query("step == 4097").set_index("source")
    with np.load(GEOM) as z:
        shell = z["material_shell"]
        need(np.array_equal(z["native_ids"], np.arange(8, 37181)), "Original material IDs")
    count = np.bincount(shell)[1:]
    ref = Reference(.3, modes=1440, finite=False)
    ref.cv = ref.H * ref.kappa
    ref.decay = ref.xi**2 * ref.cv / R**2
    rows, hashes = [], {}
    radii = np.arange(1, 21) * .0025
    for step, frame in weak.groupby("step", sort=True):
        frame = frame.sort_values("material_shell")
        need(np.array_equal(frame["count"], count) and np.array_equal(frame.material_shell, np.arange(1, 21)), "20 material shells")
        tau = (step - 4096) * DT
        part = 65 if step == 4097 else step // 64
        source = OUT / "cryer_p3_gpu_drain4097_r1" if step == 4097 else TESTS.parent / RUN / RUN
        p, fs = native(source / "data" / f"Part_{part:04d}.bi4", part, step)
        need(np.array_equal(fs, shell == 20) and (not tau or np.all(p[fs] == 0)), "Original drains")
        hashes.setdefault(source.name, hashlib.sha256()).update(p.astype("<f4").tobytes())
        pmean = np.bincount(shell, weights=p)[1:] / count
        pstd = np.sqrt(np.bincount(shell, weights=(p - pmean[shell - 1])**2)[1:] / count)
        wp = frame.p_mean_Pa.to_numpy()
        ws = frame.p_std_Pa.to_numpy()
        theory, pbar, _ = reference_fields(ref, tau, radii)
        true_surface = 1000 * R * (Q - pbar) / (3 * ref.K)
        if step == 4097:
            surface = [first.loc[k, "surface_inward_mm"] for k in ("retained local P3", "native-mass weak")]
        else:
            s = pair.loc[step]
            need(abs(pmean[0] - s.p_center_old_Pa) < 1e-7 and abs(wp[0] - s.p_center_candidate_Pa) < 1e-7, "Center identity")
            need(abs(theory[0] - s.p_center_theory_Pa) < 1e-6, "Matched actual M0 diffusivity")
            surface = [s.surface_old_mm, s.surface_candidate_mm]
        row = dict(step=int(step), time_s=step * DT, tau_s=tau, Tv=tau * ref.legacy_cv / R**2,
                   center_M0_Pa=theory[0], shell17_minus18_M0_Pa=theory[16]-theory[17],
                   surface_M0_mm=true_surface)
        for key, mu, sd, u in zip(("P3", "weak"), (pmean, wp), (pstd, ws), surface):
            angular = np.sqrt(np.average(sd**2, weights=count))
            radial = np.sqrt(np.average((mu - theory)**2, weights=count))
            fields = dict(center_Pa=mu[0], center_error_Pa=mu[0] - theory[0],
                          angular_rms_Pa=angular, radial_mean_error_rms_Pa=radial,
                          all_point_error_rms_Pa=np.hypot(angular, radial),
                          shell17_minus18_Pa=mu[16]-mu[17], shell17_std_Pa=sd[16], shell18_std_Pa=sd[17],
                          surface_mm=u, surface_error_mm=u-true_surface)
            row.update({key + "_" + k: v for k, v in fields.items()})
        rows.append(row)
    data = pd.DataFrame(rows)
    steps = sorted([4097, *range(4096, 36865, 64)])
    need(list(data.step) == steps and count[0] == 18 and count[-1] == 5153, "Full clock and population")
    for filename in ("cryer_weak_angular_opening_r1_summary.csv", "cryer_weak_angular_final_r1_summary.csv"):
        for rec in table(FIG / filename).itertuples():
            key = "P3" if rec.model == "original_P3" else "weak"
            row = data[data.step == rec.step].iloc[0]
            need(abs(row[key + "_angular_rms_Pa"] - rec.all_within_shell_angular_rms_Pa) < 1e-8, "Sealed angular measurement")
    return data, {key: h.hexdigest() for key, h in hashes.items()}


def first_sustained(frame, mask):
    """First observed sample whose entire remaining suffix satisfies this condition."""
    sustained = np.logical_and.accumulate(np.asarray(mask, dtype=bool)[::-1])[::-1]
    if not np.any(sustained):
        return None
    j = int(np.flatnonzero(sustained)[0])
    return dict(step=int(frame.step.iloc[j]), tau_s=float(frame.tau_s.iloc[j]),
                previous_saved_tau_s=float(frame.tau_s.iloc[j - 1]) if j else None)


def describe(data):
    original = json.loads((PHYS / "physical_review.json").read_text())
    # Use the archived opening/peak contract and the unchanged 64-step common output schedule.
    regular = data[(data.step % 64 == 0) & (data.tau_s > 0)]
    before = regular[regular.Tv < original["peak_window_start_Tv"]]
    peak = regular[regular.Tv >= original["peak_window_start_Tv"]]
    need((len(regular), len(peak)) == (512, original["window_rows"]), "Predeclared peak coverage")
    result = {}
    for key in ("P3", "weak"):
        row = peak.loc[peak[key + "_center_Pa"].idxmax()]
        ep = 100 * (row[key + "_center_Pa"] / original["theoretical_peak_Pa"] - 1)
        et = row.tau_s - original["theoretical_tau_s"]
        gap = float(np.max(np.diff(peak.tau_s)))
        result[key] = dict(peak_Pa=row[key + "_center_Pa"], peak_tau_s=row.tau_s,
                           amplitude_pct=ep, phase_error_s=et, phase_error_pct=100*et/original["theoretical_tau_s"],
                           passes=dict(sampling=gap <= .01*original["theoretical_tau_s"], amplitude=abs(ep) <= 1,
                               relative_to_A=abs(ep) <= abs(original["original_A_amplitude_error_pct"])+.10,
                               phase=abs(et) <= max(gap/2, .02*original["theoretical_tau_s"])))
        for name, part in (("pre_Mandel", before), ("Mandel", peak)):
            result[key][name] = {c: rms(part[key+"_"+c]) for c in (
                "center_error_Pa", "angular_rms_Pa", "radial_mean_error_rms_Pa", "all_point_error_rms_Pa", "surface_error_mm")}
            result[key][name]["samples"] = len(part)
        result[key]["angular_below_Pa_until_endpoint"] = {
            str(limit): first_sustained(regular, regular[key + "_angular_rms_Pa"] <= limit)
            for limit in (100, 10, 2)}
    result["weak_at_or_below_original_until_endpoint"] = {
        field: first_sustained(regular, abs(regular["weak_"+field]) <= abs(regular["P3_"+field]))
        for field in ("angular_rms_Pa", "radial_mean_error_rms_Pa", "all_point_error_rms_Pa",
                      "surface_error_mm", "center_error_Pa")}
    result["surface_reference_max_difference_from_archived_mm"] = float(np.max(abs(
        table(PAIR).surface_theory_mm.to_numpy() - data[data.step % 64 == 0].surface_M0_mm.to_numpy())))
    return result


def plot(data, dest):
    d = data[data.tau_s > 0]
    fig, axes = plt.subplots(1, 3, figsize=(12.2, 3.7), layout="constrained")
    for ax, field, title, unit in zip(axes, ("angular_rms_Pa", "radial_mean_error_rms_Pa", "surface_error_mm"),
                                      ("Within-shell angular RMS", "Shell-mean error RMS", "Surface motion error"),
                                      ("Pa", "Pa", "µm")):
        for k, color, label in (("P3", "#a45126", "Original P3"), ("weak", "#176783", "Native-mass weak")):
            ax.plot(1000*d.tau_s, d[k+"_"+field]*(1000 if unit == "µm" else 1),
                    ".-", color=color, ms=2.2, lw=.85, label=label)
        ax.set(xscale="log", xlabel="Time since opening (ms)", ylabel=unit, title=title)
        if unit == "Pa":
            ax.set_yscale("log")
        else:
            ax.axhline(0, c="#777", lw=.65)
        ax.axvline(1000*d[d.Tv >= .005].tau_s.iloc[0], c="#777", ls=":", label="First Mandel sample")
        ax.grid(alpha=.16)
    axes[0].legend(fontsize=8)
    fig.savefig(dest, dpi=160)
    plt.close(fig)


def main():
    csv_path = FIG / (TAG + ".csv")
    image_path = csv_path.with_suffix(".png")
    receipt = TESTS / "logs" / (TAG + ".json")
    need(not any(path.exists() for path in (csv_path, image_path, receipt)), "Preserve completed result")
    start = perf_counter()
    date = datetime.now().astimezone().isoformat()
    data, raw_hashes = reconstruction()
    results = describe(data)
    data.to_csv(csv_path, index=False)
    plot(data, image_path)
    sources = [*SHELL_FILES, PAIR, EARLY, GEOM, PHYS/"physical_review.json",
               TESTS/"notes/cryer_p3_local_r1.md", Path(__file__), csv_path, image_path]
    hashes = {p.relative_to(TESTS).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    record = dict(started=date, wall_seconds=perf_counter()-start, inputs_and_outputs_sha256=hashes,
        original_sorted_f32_pressure_sequence_sha256=raw_hashes, steps=[4096, 36864], actual_time_s=[4096*DT, 36864*DT],
        frames=len(data), regular_shared_frames=513, independent_local_first_update=4097,
        recovery_definition="Each save from first reported tau through 62.5 ms satisfies the indicated level. The 100, 10 and 2 Pa levels are descriptive, not acceptance limits.",
        criteria_source="cryer_p3_return_r1.py and frozen physical_review.json; original accepted sampling clock; two pressure models use their own reference for A-relative check.",
        reference="Quasistatic M0, r_i/a=i/20, 1440 modes; physical g=9.80665 for decay, legacy g=9.81 for Tv; 10 kPa at last closed state.",
        results=results)
    with receipt.open("x", encoding="utf8") as f:
        json.dump(record, f, indent=2, allow_nan=False, default=lambda v: v.item())
    print(json.dumps(results, indent=2, default=lambda v: v.item()))


if __name__ == "__main__":
    main()

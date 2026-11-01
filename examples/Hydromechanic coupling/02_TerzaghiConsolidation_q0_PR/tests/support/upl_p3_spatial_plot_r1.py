"""Offline three-grid review of actual material fields; never starts a solver."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import expm

TESTS = Path(__file__).resolve().parent.parent


def entry(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest.hexdigest())


def fields(folder, nx, frozen):
    folder = Path(folder).resolve()
    bindings = [entry(folder / name) for name in ("complete.json", "physical.bin", "modes.csv")]
    for current in bindings:
        saved = frozen[str(Path(current["path"]).resolve()).casefold()]
        assert current["bytes"] == saved["bytes"] and current["sha256"] == saved["sha256"], "Frozen run output changed"
    done = json.loads((folder / "complete.json").read_text(encoding="utf-8-sig"))
    assert done["passed"] and done["actual_ComputeStep_Sym"]
    assert done["actual_end_s"] == 2.0 ** -15 and done["native_ids"] == nx * nx // 2
    path = folder / "physical.bin"
    with path.open("rb") as stream:
        header = np.fromfile(stream, dtype="<u4", count=3)
    assert tuple(header) == (nx * nx // 2, 26, 257)
    width = 1 + int(header[0]) * 26
    assert path.stat().st_size == 12 + 257 * width * 8
    data = np.memmap(path, dtype="<f8", mode="r", offset=12, shape=(257, width))
    assert np.array_equal(data[:, 0], np.arange(257) / 8388608.0)
    rows = data[:, 1:].reshape(257, int(header[0]), 26)
    assert np.isfinite(rows).all()
    modes = np.genfromtxt(folder / "modes.csv", delimiter=",", names=True)
    assert np.array_equal(modes["time_s"], data[:, 0])
    return rows, modes, bindings


def main():
    parser = argparse.ArgumentParser()
    for name in ("c32", "h32", "c64", "h64", "run_check"):
        parser.add_argument("--" + name.replace("_", "-"), required=True, type=Path)
    args = parser.parse_args()
    run = json.loads(args.run_check.read_text(encoding="utf-8-sig"))
    baseline_path = TESTS / "logs" / "upl_p3_time_wave_ReleaseCPU_r1.check.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8-sig"))
    assert run["passed"] and baseline["passed"]
    frozen = {str(Path(item["path"]).resolve()).casefold(): item for item in run["files"] + baseline["files"]}
    stem = "upl_p3_spatial_r1"
    outputs = [TESTS / "figures" / (stem + suffix) for suffix in (".png", "_history.csv", "_summary.csv")]
    receipt = TESTS / "logs" / (stem + ".check.json")
    assert not any(path.exists() for path in outputs + [receipt]), "Retained analysis protected"
    controls = TESTS / "outputs"
    folders = [(16, controls / "upl_p3_time_wave_ReleaseCPU_r1_k1_c_actual", controls / "upl_p3_time_wave_ReleaseCPU_r1_k1_h_actual"),
               (32, args.c32, args.h32), (64, args.c64, args.h64)]
    inputs = [entry(__file__), entry(args.run_check), entry(baseline_path)]
    history, summary, curves = [], [], []
    amplitude, wave_number = 2.0 ** -9, 2 * np.pi / .125
    bulk = 89478488.0 + 4 * 134217728.0 / 3
    storage_bulk, rho, rhow = 2.0 ** 28, 2048.0, 1000.0
    cu_reference = np.sqrt((bulk + storage_bulk) / rho)
    pstar = storage_bulk * amplitude / cu_reference
    ustar = amplitude / (cu_reference * wave_number)
    diffusion = storage_bulk * float(np.float32(.0001)) / (rhow * 9.80665)
    a = wave_number * pstar / (rho * amplitude)
    t = diffusion * rhow * wave_number * amplitude / pstar * a
    matrix = np.array([[0, amplitude / ustar, 0, 0], [0, 0, -a, a],
                       [0, bulk * wave_number * amplitude / pstar, 0, 0],
                       [0, -storage_bulk * wave_number * amplitude / pstar, -t, -diffusion * wave_number ** 2 + t]])
    # Independently scaled augmented [u,v,sigma,p] exponential, not stored RK4 columns.
    reference = np.array([(expm(matrix * time) @ np.array([0., 1., 0., 0.]))[[3, 1, 0]]
                          for time in np.arange(257) / 8388608.0])
    for nx, coarse, half in folders:
        c, cm, cb = fields(coarse, nx, frozen)
        h, hm, hb = fields(half, nx, frozen)
        inputs += cb + hb
        assert np.array_equal(c[0], h[0]), "Same-grid material initial states changed"
        cu = float(hm["cu_actual"][0])
        assert abs(cu - cu_reference) <= 1e-13 * cu_reference
        theory = np.column_stack((hm["p_continuum"] / pstar, hm["v_continuum"] / amplitude, hm["u_continuum"] / ustar))
        assert np.max(np.abs(theory - reference)) <= 1e-10, "Stored reference differs from independent exponential"
        phase = wave_number * h[0, :, 0]
        sn, cs = np.sin(phase), np.cos(phase)
        errors, pair = [], []
        for i in range(257):
            dp = c[i, :, 6] - h[i, :, 6]
            dv = c[i, :, 3:6] - h[i, :, 3:6]
            du = c[i, :, :3] - h[i, :, :3]
            pair.append([np.sqrt(np.mean(dp * dp)) / pstar,
                         np.sqrt(np.mean(np.sum(dv * dv, axis=1))) / amplitude,
                         np.sqrt(np.mean(np.sum(du * du, axis=1))) / ustar])
            assert np.sqrt(np.mean(dp * dp)) <= 5 and 1000 * np.max(np.linalg.norm(du, axis=1)) <= .005
            velocity = h[i, :, 3:6].copy() / amplitude
            displacement = (h[i, :, :3] - h[0, :, :3]) / ustar
            velocity[:, 0] -= reference[i, 1] * sn
            displacement[:, 0] -= reference[i, 2] * sn
            pressure = h[i, :, 6] / pstar - reference[i, 0] * cs
            error = [np.sqrt(np.mean(pressure * pressure)),
                     np.sqrt(np.mean(np.sum(velocity * velocity, axis=1))),
                     np.sqrt(np.mean(np.sum(displacement * displacement, axis=1)))]
            errors.append(error)
            history.append([nx, float(hm["time_s"][i]), hm["p_cosine"][i] / pstar, reference[i, 0],
                            hm["v_sine"][i] / amplitude, reference[i, 1], hm["u_sine"][i] / ustar, reference[i, 2], *error, *pair[-1]])
        maximum, half_max = np.max(errors, axis=0), np.max(pair, axis=0)
        assert np.max(half_max) <= 1e-4, "Additional normalized time-isolation gate failed"
        endpoint = (hm["p_cosine"][-1] / pstar) / reference[-1, 0] - 1
        summary.append(dict(nx=nx, native=nx * nx // 2, pressure_RMS_over_Pstar=float(maximum[0]),
                            velocity_RMS_over_A=float(maximum[1]), displacement_RMS_over_Ustar=float(maximum[2]),
                            combined_max=float(max(maximum)), endpoint_pressure_relative_error=float(endpoint),
                            half_p=float(half_max[0]), half_v=float(half_max[1]), half_u=float(half_max[2])))
        curves.append(np.column_stack((hm["p_cosine"] / pstar, hm["v_sine"] / amplitude, hm["u_sine"] / ustar)))
    monotone = summary[0]["combined_max"] > summary[1]["combined_max"] > summary[2]["combined_max"]
    finest = summary[2]
    accuracy = max(finest["combined_max"], abs(finest["endpoint_pressure_relative_error"])) <= .01
    outputs[0].parent.mkdir(exist_ok=True)
    with outputs[1].open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["nx", "time_s", "p_mode_over_Pstar", "p_continuum", "v_mode_over_A", "v_continuum", "u_mode_over_Ustar", "u_continuum", "p_field_RMS", "v_vector_RMS", "u_vector_RMS", "half_p_RMS", "half_v_RMS", "half_u_RMS"])
        writer.writerows(history)
    with outputs[2].open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader(); writer.writerows(summary)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), constrained_layout=True)
    time_us = np.arange(257) / 8388608.0 * 1e6
    for component, ax in enumerate(axes.flat[:3]):
        ax.plot(time_us, reference[:, component], "k--", lw=2, label="Continuum linear reference", zorder=5)
        for nx, curve, color, marker in zip((16, 32, 64), curves, ("#9b4f96", "#2474b5", "#2b9561"), ("o", "s", "^")):
            ax.plot(time_us, curve[:, component], color=color, marker=marker, markevery=32, ms=4, lw=1.2, label=f"Actual {nx} x {nx//2}, half dt")
        ax.set(xlabel="Time [microseconds]", ylabel=("Pressure mode / P*", "Velocity mode / A", "Material displacement mode / U*")[component])
        ax.grid(alpha=.25)
    axes.flat[0].legend(fontsize=8)
    for key, label, marker in (("pressure_RMS_over_Pstar", "Pressure", "o"), ("velocity_RMS_over_A", "Velocity vector", "s"), ("displacement_RMS_over_Ustar", "Displacement vector", "^")):
        axes.flat[3].plot((16, 32, 64), [100 * row[key] for row in summary], marker=marker, label=label)
    axes.flat[3].axhline(1, color="k", ls="--", lw=1, label="Bounded-wave 1% objective")
    axes.flat[3].set(xlabel="Cells along x", ylabel="Maximum full-field normalized RMS [%]", yscale="log", xticks=(16, 32, 64))
    axes.flat[3].legend(fontsize=8); axes.flat[3].grid(alpha=.25)
    fig.suptitle("Private CPU dynamic-P3 spatial refinement: same physical weak-wave problem\nFixed h/dp=1.8; finite window only, not general poromechanical accuracy", fontsize=12)
    fig.savefig(outputs[0], dpi=180); plt.close(fig)
    result = dict(passed=bool(monotone and accuracy), scope="Bounded actual periodic weak-wave spatial accuracy", grids=summary,
                  monotone_combined_error=bool(monotone), finest_one_percent_objective=bool(accuracy),
                  inputs=inputs, outputs=[entry(path) for path in outputs], physical_acceptance=False,
                  reference="Independent scaled augmented 4x4 matrix exponential with the actual fixed material constants",
                  raw_trajectories_cloud_backed=False, interpolation=False)
    receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("passed", "grids", "monotone_combined_error", "finest_one_percent_objective")}))
    if not result["passed"]:
        raise SystemExit("Accuracy objective held; completed solvers and review artifacts preserved")


if __name__ == "__main__":
    main()

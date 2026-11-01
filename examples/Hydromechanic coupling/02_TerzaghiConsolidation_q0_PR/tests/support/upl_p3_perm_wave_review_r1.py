"""Independent saved-data review/plots; never runs a physical program."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG = "upl_p3_perm_wave_ReleaseCPU_r2"
TARGET = T / "logs/upl_p3_perm_wave_review_r1.check.json"
HISTORY = T / "figures/upl_p3_perm_wave_r1_history.csv"
FIGURE = T / "figures/upl_p3_perm_wave_r1.png"
for path in (TARGET, HISTORY, FIGURE):
    if path.exists():
        raise RuntimeError(f"Retained artifact protected: {path}")


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


bindings = {}


def entry(path):
    sha = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024*1024), b""):
            sha.update(block)
    row = {"path": str(path), "bytes": path.stat().st_size, "sha256": sha.hexdigest()}
    bindings[str(path)] = row
    return row


def verify(value):
    if isinstance(value, dict):
        if {"path", "bytes", "sha256"} <= value.keys():
            actual = entry(Path(value["path"]))
            assert actual["bytes"] == value["bytes"] and actual["sha256"] == value["sha256"].lower()
        for item in value.values():
            verify(item)
    elif isinstance(value, list):
        for item in value:
            verify(item)


final_path = T / f"logs/{TAG}.check.json"
final = load(final_path)
assert final["passed"] and final["solver_jobs"] == 5 and not final["physical_acceptance"]
verify(final)
build = load(Path(final["build"]["path"]))
verify(build)
for receipt in final["receipts"]:
    actual = load(Path(receipt["path"]))
    assert actual["exit_code"] == 0 and actual["owned_call_exited"]
    verify(actual)
entry(final_path)


def binary(directory, frames):
    path = directory / "physical.bin"
    with path.open("rb") as source:
        assert np.array_equal(np.fromfile(source, "<u4", 3), [512, 26, frames])
        values = np.fromfile(source, np.dtype([("time", "<f8"), ("state", "<f8", (512, 26))]))
    assert len(values) == frames and np.isfinite(values["state"]).all()
    entry(path)
    return values


jobs = {}
K0 = float(np.float32(.0001))
ALPHA = 1 / (.75 / 1024)
DP = 1/256
KH = float(np.float32(1.8*DP))
KW, RW = 67108864., 1000.
for label, step, enabled in (("on_c", 2**-24, True), ("on_h", 2**-25, True), ("off_c", 2**-24, False)):
    directory = T / f"outputs/{TAG}_{label}"
    done = load(directory / "complete.json")
    assert done["passed"] and done["dt_actual"] == step
    data = binary(directory, 257)
    clock, state = data["time"], data["state"]
    assert np.array_equal(clock, np.arange(257)*2**-23)
    ids = np.genfromtxt(directory/"native_ids.csv", delimiter=",", names=True)
    assert np.array_equal(ids["native_id"], np.arange(512))
    xref = np.column_stack([ids[axis] for axis in ("X", "Y", "Z")])
    phase = 2*np.pi*xref[:, 0]/.125
    assert np.max(abs(state[0, :, 0]-xref[:, 0]-2**-15/(2*np.pi/.125)*np.sin(phase))) < 2e-17
    assert np.max(abs(state[0, :, 8]-1-2**-15*np.cos(phase))) < 3e-16
    j = state[:, :, 8]
    n = 1-.75/j
    volume = DP**2*j
    rho = RW+(2048-RW)/j
    kval = K0*np.exp(ALPHA*(j-1)) if enabled else np.full_like(j, K0)
    mode = np.genfromtxt(directory/"modes.csv", delimiter=",", names=True)
    assert len(mode) == 257 and np.array_equal(mode["time_s"], clock)
    assert np.allclose(np.min(kval, axis=1), mode["min_k"], rtol=5e-13, atol=0)
    assert np.allclose(np.max(kval, axis=1), mode["max_k"], rtol=5e-13, atol=0)
    assert np.allclose(np.mean(state[:, :, 6], axis=1), mode["mean_p"], rtol=1e-12, atol=1e-12)
    assert np.allclose(np.mean(j, axis=1), mode["mean_J"], rtol=1e-12, atol=0)
    sig = state[:, :, 10:16]
    tr = sig[:, :, 0]+sig[:, :, 3]+sig[:, :, 5]
    mean = tr/3
    dev = sum((sig[:, :, k]-mean)**2 for k in (0, 3, 5))+2*sum(sig[:, :, k]**2 for k in (1, 2, 4))
    # Existing harness computes 18*K in float before the double division.
    # Preserve that recorded diagnostic arithmetic, not a different double-only energy.
    bulk_denominator = float(np.float32(18)*np.float32(89478488.))
    energy = np.sum(volume*(.5*rho*np.sum(state[:, :, 3:6]**2, axis=2)+dev/(4*134217728.)+tr**2/bulk_denominator+n*state[:, :, 6]**2/(2*KW)), axis=1)
    energy /= energy[0]
    assert np.max(energy) <= 1.1
    assert np.allclose(energy, mode["energy_ratio"], rtol=1e-12, atol=1e-12)
    ledger_count, max_gradient = 0, 0.
    with (directory/"ledger.csv").open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            frame, native = divmod(ledger_count, 512)
            assert int(row["native_id"]) == native and float(row["time_s"]) == clock[frame]
            assert int(row["step"]) == frame*int(2**-23/step)
            assert float(row["J"]) == j[frame, native]
            for column, expected in (("n", n), ("V", volume), ("rho", rho), ("actual_k", kval), ("reference_k", kval)):
                assert abs(float(row[column])-expected[frame, native]) <= 5e-13*abs(expected[frame, native])
            gradient = np.array([float(row[f"endpoint_GJ_{axis}"]) for axis in "xyz"])
            uk = KW/n[frame, native]*np.linalg.norm(gradient)*(ALPHA*kval[frame, native] if enabled else 0)/(RW*9.80665)
            courant = uk*step/KH
            assert abs(float(row["necessary_gradient_speed"])-uk) <= 5e-13*max(abs(uk), 1e-300)
            assert abs(float(row["gradient_dt_over_h"])-courant) <= 5e-13*max(abs(courant), 1e-300)
            assert courant <= .01
            max_gradient = max(max_gradient, courant)
            ledger_count += 1
    assert ledger_count == 257*512
    assert abs(max_gradient-done["max_necessary_gradient_k_CFL"]) <= 1e-12
    source_rows = np.genfromtxt(directory/"initial_source.csv", delimiter=",", names=True)
    assert len(source_rows) == 512
    assert np.all(abs(source_rows["rate_difference"]-source_rows["reference_difference"]) <= source_rows["reference_limit"])
    if enabled:
        budget = done["initial_max_single_rate_roundoff_budget_Pa_s"]
        for column, multiple in (("rate_difference", 100), ("chain_total_rate", 100), ("chain_pressure_rate", 10), ("chain_acceleration_rate", 10)):
            assert np.sqrt(np.mean(source_rows[column]**2)) > multiple*budget
    jobs[label] = {"state": state, "time": clock, "k": kval, "mode": mode, "done": done,
                   "X": xref, "energy": energy, "max_gradient": max_gradient}

c, h, off = (jobs[key] for key in ("on_c", "on_h", "off_c"))
assert np.array_equal(c["state"][0], h["state"][0]) and np.array_equal(c["state"][0], off["state"][0])
delta = c["state"]-h["state"]
hp = np.sqrt(np.mean(delta[:, :, 6]**2, axis=1))
hu = 1000*np.max(np.linalg.norm(delta[:, :, :3], axis=2), axis=1)
hv = np.sqrt(np.mean(np.sum(delta[:, :, 3:6]**2, axis=2), axis=1))
hurms = np.sqrt(np.mean(np.sum(delta[:, :, :3]**2, axis=2), axis=1))
assert hp.max() <= 5 and hu.max() <= .005
assert hp.max()/c["done"]["Pstar"] <= 1e-4
assert hv.max()/2**-9 <= 1e-4 and hurms.max()/c["done"]["Ustar"] <= 1e-4
effect = np.sqrt(np.mean((c["state"][:, :, 6]-off["state"][:, :, 6])**2, axis=1))
assert effect.max() > max(.001, 10*hp.max())
zero_off = binary(T/f"outputs/{TAG}_k0_off", 17)
zero_on = binary(T/f"outputs/{TAG}_k0_on", 17)
assert zero_off.tobytes() == zero_on.tobytes()

with HISTORY.open("w", newline="", encoding="utf-8") as out:
    writer = csv.writer(out)
    writer.writerow(["actual_time_s", "pressure_mode_ON_Pa", "pressure_mode_constant_OFF_Pa", "ON_OFF_pressure_RMS_Pa", "half_pressure_RMS_Pa", "half_max_vector_displacement_mm", "ON_min_k_over_k0", "ON_max_k_over_k0", "ON_energy_ratio"])
    for i, time in enumerate(c["time"]):
        writer.writerow([time, c["mode"]["p_material_cosine"][i], off["mode"]["p_material_cosine"][i], effect[i], hp[i], hu[i], c["k"][i].min()/K0, c["k"][i].max()/K0, c["energy"][i]])

fig, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)
time_us = c["time"]*1e6
axes[0, 0].plot(time_us, off["mode"]["p_material_cosine"], "--", label="constant k control")
axes[0, 0].plot(time_us, c["mode"]["p_material_cosine"], label="k(J), coarse")
axes[0, 0].plot(time_us[::16], h["mode"]["p_material_cosine"][::16], ".", label="k(J), half")
axes[0, 0].set(ylabel="Pressure material cosine mode [Pa]", title="Actual coupled trajectories; no theory claim")
axes[0, 1].semilogy(time_us[1:], effect[1:], label="ON vs constant OFF")
axes[0, 1].semilogy(time_us[1:], np.maximum(hp[1:], 1e-16), label="independent half difference")
axes[0, 1].set(ylabel="Native pressure RMS difference [Pa]", title="Resolved variable-k effect")
axes[1, 0].plot(time_us, c["k"].min(axis=1)/K0, label="minimum k/k0")
axes[1, 0].plot(time_us, c["k"].max(axis=1)/K0, label="maximum k/k0")
axes[1, 0].axhline(1, color="0.5", linestyle="--", linewidth=.7)
axes[1, 0].set(ylabel="Current hydraulic conductivity / k0", title="Same-stage J-derived conductivity")
axes[1, 1].plot(time_us, c["energy"], label="k(J), coarse")
axes[1, 1].plot(time_us, off["energy"], "--", label="constant k control")
axes[1, 1].set(ylabel="Recorded mechanical/storage energy / initial", title="Finite diagnostic window, not general stability")
for ax in axes.flat:
    ax.set_xlabel("Actual time [microseconds]")
    ax.grid(alpha=.25)
    ax.legend(fontsize=8)
fig.suptitle("Private CPU smooth-k integration: manufactured nonequilibrium initial state\nCk=2^-10 is a test parameter, not a calibrated soil value", fontsize=11)
fig.savefig(FIGURE, dpi=160)
plt.close(fig)
report = {"passed": True, "scope": "Independent full native saved-state/ledger review; not physical theory or sufficient stability acceptance",
          "samples": 257, "native_ids": 512, "actual_end_s": float(c["time"][-1]),
          "half_max_pressure_RMS_Pa": float(hp.max()), "half_max_vector_displacement_mm": float(hu.max()),
          "half_max_normalized_p_v_u": [float(hp.max()/c["done"]["Pstar"]), float(hv.max()/2**-9), float(hurms.max()/c["done"]["Ustar"])],
          "ON_OFF_max_pressure_RMS_Pa": float(effect.max()), "effect_over_measured_half": float(effect.max()/hp.max()),
          "initial_k_over_k0_range": [float(c["k"][0].min()/K0), float(c["k"][0].max()/K0)],
          "final_max_k_change_over_initial_k0": float(np.max(abs(c["k"][-1]-c["k"][0]))/K0),
          "max_energy_ratio": float(c["energy"].max()), "max_saved_necessary_gradient_k_CFL": c["max_gradient"],
          "all_394752_ledger_records_recomputed": True, "k0_native_and_clocks_exact": True,
          "offline_reference_repair": "Initial review used double18*K instead of the harness float18*K diagnostic denominator. Correcting that reference reduces maximum energy-ratio difference to approximately7e-15; no solver/source/gate change or rerun.",
          "figure": entry(FIGURE), "history": entry(HISTORY), "verified_bindings": list(bindings.values()),
          "limitations": "One weak elastic periodic short window, manufactured mapped initial state; no variable-k wall/interface/GPU/public model/long-time/physical accuracy acceptance. Saved gradient screen is not direct observation of all force stages. Conditional storage is not exact fluid mass."}
TARGET.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
print(json.dumps({key: value for key, value in report.items() if key != "verified_bindings"}, indent=2))

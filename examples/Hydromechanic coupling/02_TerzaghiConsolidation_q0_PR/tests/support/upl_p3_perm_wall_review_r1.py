"""Offline full-native smooth-k wall review; no program or solver invocation."""
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG = "upl_p3_perm_wall_ReleaseCPU_r1"
REPORT = T/"logs/upl_p3_perm_wall_review_r1.check.json"
FIG = T/"figures/upl_p3_perm_wall_r1.png"
CSV = T/"figures/upl_p3_perm_wall_r1_history.csv"
for p in (REPORT, FIG, CSV):
    if p.exists():
        raise RuntimeError(f"Retained artifact protected: {p}")
bindings = {}


def entry(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024*1024), b""):
            h.update(chunk)
    row = {"path": str(path), "bytes": path.stat().st_size, "sha256": h.hexdigest()}
    bindings[str(path)] = row
    return row


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def verify(value):
    if isinstance(value, dict):
        if {"path", "bytes", "sha256"} <= value.keys():
            a = entry(Path(value["path"]))
            assert a["bytes"] == value["bytes"] and a["sha256"] == value["sha256"].lower()
        for x in value.values():
            verify(x)
    elif isinstance(value, list):
        for x in value:
            verify(x)


final_path = T/f"logs/{TAG}.check.json"
final = load(final_path)
assert final["passed"] and final["solver_jobs"] == 3 and not final["physical_acceptance"]
verify(final)
verify(load(Path(final["build"]["path"])))
entry(final_path)
for receipt in final["receipts"]:
    r = load(Path(receipt["path"]))
    assert r["exit_code"] == 0 and r["owned_call_exited"]
    verify(r)

K0 = float(np.float32(.0001))
ALPHA = 1/(.75/8192)
KH = float(np.float32(1.8/512))
jobs = {}
for label, dt, enabled in (("on_c", 2**-25, True), ("on_h", 2**-26, True), ("off_c", 2**-25, False)):
    folder = T/f"outputs/{TAG}_{label}"
    done = load(folder/"complete.json")
    with (folder/"physical.bin").open("rb") as stream:
        assert np.array_equal(np.fromfile(stream, "<u4", 3), [1024, 26, 257])
        data = np.fromfile(stream, dtype=np.dtype([("time", "<f8"), ("state", "<f8", (1024, 26))]))
    assert len(data) == 257 and np.array_equal(data["time"], np.arange(257)*2**-23)
    state = data["state"]
    assert np.isfinite(state).all()
    native = np.genfromtxt(folder/"native_ids.csv", delimiter=",", names=True)
    assert np.array_equal(native["row"], np.arange(1024))
    assert np.array_equal(native["native_id"], np.arange(256, 1280))
    j = state[:, :, 8]
    assert np.array_equal(j[0], np.ones(1024))
    n, volume, rho = 1-.75/j, j/512**2, 1000+1048/j
    kval = K0*np.exp(ALPHA*(j-1)) if enabled else np.full_like(j, K0)
    modes = np.genfromtxt(folder/"modes.csv", delimiter=",", names=True)
    sources = np.genfromtxt(folder/"source_summary.csv", delimiter=",", names=True)
    wall = np.genfromtxt(folder/"wall_audit.csv", delimiter=",", names=True)
    assert len(modes) == len(sources) == 257 and len(wall) == 514
    assert np.array_equal(modes["time_s"], data["time"])
    sums = np.zeros((257, 4))
    max_gradient = count = 0
    with (folder/"conductivity_ledger.csv").open(newline="", encoding="utf-8-sig") as source:
        for r in csv.DictReader(source):
            f, node = divmod(count, 1024)
            assert int(r["native_id"]) == node+256 and float(r["time_s"]) == data["time"][f]
            assert int(r["step"]) == f*int(2**-23/dt) and float(r["J"]) == j[f, node]
            for name, expected in (("n", n), ("V", volume), ("rho", rho), ("actual_k", kval), ("reference_k", kval)):
                assert abs(float(r[name])-expected[f, node]) <= 5e-13*abs(expected[f, node])
            gj = np.array([float(r[f"force_audit_GJ_{axis}"]) for axis in "xyz"])
            uk = 67108864/n[f, node]*np.linalg.norm(gj)*(ALPHA*kval[f, node] if enabled else 0)/(1000*9.80665)
            courant = uk*dt/KH
            assert abs(float(r["gradient_dt_over_h"])-courant) <= 5e-13*max(abs(courant), 1e-300)
            assert courant <= .01
            max_gradient = max(max_gradient, courant)
            difference = float(r["rate_ON"])-float(r["rate_constant_OFF"])
            assert difference == float(r["source_difference"])
            assert abs(difference-float(r["reference_difference"])) <= float(r["reference_limit"])
            pc, ac = float(r["pressure_chain_rate"]), float(r["acceleration_chain_rate"])
            sums[f] += np.array([difference, pc+ac, pc, ac])**2
            count += 1
    assert count == 257*1024
    for col, name in enumerate(("source_RMS", "chain_RMS", "pressure_chain_RMS", "acceleration_chain_RMS")):
        assert np.allclose(np.sqrt(sums[:, col]/1024), sources[name], rtol=5e-13, atol=1e-12)
    if enabled:
        for name in ("source_RMS", "chain_RMS", "pressure_chain_RMS", "acceleration_chain_RMS"):
            assert np.max(sources[name]/sources["max_single_rate_roundoff"]) > 10
    assert np.all(abs(wall["face_vn"]) <= wall["vn_bound"])
    assert np.all(abs(wall["face_qn"]) <= wall["qn_bound"])
    assert np.all(wall["force_residual"] <= wall["force_bound"])
    kface = K0*np.exp(ALPHA*(wall["physical_face_J"]-1)) if enabled else np.full(514, K0)
    assert np.allclose(kface, wall["physical_face_k"], rtol=5e-13, atol=0)
    physical_q = wall["face_qn"]*kface/K0
    assert np.allclose(physical_q, wall["physical_face_qn"], rtol=1e-12, atol=1e-24)
    assert np.all(abs(physical_q) <= wall["qn_bound"])
    for name, key in (("wrong_zero_mirror_ace_face_qn", "physical_wrong_zero_detected"), ("wrong_copy_mirror_ace_face_qn", "physical_wrong_copy_detected")):
        detected = np.count_nonzero((wall["step"] > 0) & (abs(wall[name]*kface/K0) > wall["qn_bound"]))
        assert detected > 0 and detected == done[key]
    assert np.max(modes["energy_ratio"]) <= 1.1
    jobs[label] = dict(state=state, time=data["time"], k=kval, modes=modes, wall=wall, done=done,
                       max_gradient=max_gradient)

c, h, off = (jobs[x] for x in ("on_c", "on_h", "off_c"))
assert np.array_equal(c["state"][0], h["state"][0]) and np.array_equal(c["state"][0], off["state"][0])
diff = c["state"]-h["state"]
hp = np.sqrt(np.mean(diff[:, :, 6]**2, axis=1))
hu = 1000*np.max(np.linalg.norm(diff[:, :, :3], axis=2), axis=1)
hv = np.sqrt(np.mean(np.sum(diff[:, :, 3:6]**2, axis=2), axis=1))
hurms = np.sqrt(np.mean(np.sum(diff[:, :, :3]**2, axis=2), axis=1))
assert hp.max() <= 5 and hu.max() <= .005
assert hp.max()/c["done"]["Pstar"] <= 1e-4 and hv.max()/2**-9 <= 1e-4 and hurms.max()/c["done"]["Ustar"] <= 1e-4
effect = np.sqrt(np.mean((c["state"][:, :, 6]-off["state"][:, :, 6])**2, axis=1))
assert effect.max() > max(.001, 10*hp.max())
old = T/"outputs/upl_p3_wall_wave_ReleaseCPU_r4_k1_c"
current = T/f"outputs/{TAG}_off_c"
for leaf in ("physical.bin", "native_ids.csv", "fixed_ids.csv"):
    assert entry(old/leaf)["sha256"] == entry(current/leaf)["sha256"]
ratio = np.max(abs(c["wall"]["physical_face_qn"])/c["wall"]["qn_bound"])

with CSV.open("w", newline="", encoding="utf-8") as target:
    out = csv.writer(target)
    out.writerow(["actual_time_s", "pressure_mode_ON_Pa", "pressure_mode_constant_OFF_Pa", "ON_OFF_pressure_RMS_Pa", "half_pressure_RMS_Pa", "half_max_vector_displacement_mm", "ON_min_k_over_k0", "ON_max_k_over_k0", "ON_max_face_physical_qn_over_original_bound"])
    for i, time in enumerate(c["time"]):
        out.writerow([time, c["modes"]["p_cosine"][i], off["modes"]["p_cosine"][i], effect[i], hp[i], hu[i], c["k"][i].min()/K0, c["k"][i].max()/K0, np.max(abs(c["wall"]["physical_face_qn"][2*i:2*i+2])/c["wall"]["qn_bound"][2*i:2*i+2])])
fig, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)
time = c["time"]*1e6
axes[0, 0].plot(time, off["modes"]["p_cosine"], "--", label="constant k control")
axes[0, 0].plot(time, c["modes"]["p_cosine"], label="k(J), coarse")
axes[0, 0].plot(time[::16], h["modes"]["p_cosine"][::16], ".", label="k(J), half")
axes[0, 0].set(ylabel="Pressure material cosine mode [Pa]", title="Actual trajectories; no constant-k theory claim")
axes[0, 1].semilogy(time[1:], effect[1:], label="ON vs constant OFF")
axes[0, 1].semilogy(time[1:], np.maximum(hp[1:], 1e-16), label="independent half difference")
axes[0, 1].set(ylabel="Native pressure RMS difference [Pa]", title="Resolved variable-k effect")
axes[1, 0].plot(time, c["k"].min(axis=1)/K0, label="minimum k/k0")
axes[1, 0].plot(time, c["k"].max(axis=1)/K0, label="maximum k/k0")
axes[1, 0].set(ylabel="Current hydraulic conductivity / k0", title="Uniform initial k; natural J evolution")
axes[1, 1].semilogy(time[1:], np.max((abs(c["wall"]["physical_face_qn"])/c["wall"]["qn_bound"]).reshape(257, 2), axis=1)[1:], label="physical wall flux / original bound")
axes[1, 1].axhline(1, color="black", linestyle="--", label="unchanged acceptance bound")
axes[1, 1].set(ylabel="Maximum of two face |q normal| / bound", title="Reconstructed physical-plane no-flow check")
for ax in axes.flat:
    ax.set_xlabel("Actual time [microseconds]")
    ax.grid(alpha=.25)
    ax.legend(fontsize=8)
fig.suptitle("Private CPU smooth-k fixed-wall integration\nCk=2^-13 is a manufacturing parameter; static parallel FreeSlip planes, zero gravity", fontsize=11)
fig.savefig(FIG, dpi=160)
plt.close(fig)
report = {"passed": True, "scope": "Independent saved native/ledger/source/face/hash review of a bounded private CPU wall test",
          "samples": 257, "native_ids": 1024, "actual_end_s": float(c["time"][-1]),
          "half_max_pressure_RMS_Pa": float(hp.max()), "half_max_vector_displacement_mm": float(hu.max()),
          "ON_OFF_max_pressure_RMS_Pa": float(effect.max()), "effect_over_measured_half": float(effect.max()/hp.max()),
          "k_over_k0_range": [float(c["k"].min()/K0), float(c["k"].max()/K0)],
          "max_physical_face_qn_m_s": float(np.max(abs(c["wall"]["physical_face_qn"]))),
          "max_physical_qn_over_original_bound": float(ratio), "max_saved_necessary_gradient_k_CFL": c["max_gradient"],
          "all_789504_ledger_rows_recomputed": True, "constant_OFF_raw_and_ID_ledgers_exact_old_r4": True,
          "figure": entry(FIG), "history": entry(CSV), "bindings": list(bindings.values()),
          "physical_acceptance": False, "limits": "Only small-motion static two-plane FreeSlip g0 smooth-k CPU window. Physical-plane reconstructed q is not a conservative interface flux proof; saved audits are not direct observations of every automatic force stage. No public/GPU/formal/theory/general stability acceptance."}
REPORT.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
print(json.dumps({k: v for k, v in report.items() if k != "bindings"}, indent=2))

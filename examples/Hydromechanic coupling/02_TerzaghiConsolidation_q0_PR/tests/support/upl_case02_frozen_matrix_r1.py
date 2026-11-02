"""Read-only nominal-grid diagnostic, NOT a C++ Jacobian or numerical admission.

Only this script's fresh JSON/CSV targets are written. No native program is called.
The failed trajectory stays failed. CSV clocks/positions are diagnostic text, not
decoded binary clocks/positions. See the adjacent notes declaration before use.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

# Bound numerical-library parallelism in this analysis process only.
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import numpy as np
import scipy
from scipy.linalg import eig
from scipy.optimize import least_squares

T = Path(__file__).resolve().parents[1]
SOURCE = T.parents[3] / "src" / "source"
SOURCE_SHA = {
    "JSph.cpp": "a2c4342ef140820fa31aa9f48b132bd7d68e8785df596dbe164d6500056ce7cf",
    "JSphCpu.cpp": "3fed0edf70aff9735a498c26edc921dd8436deb76f03afc11f43e213d5c9a08e",
    "JSphCpuSingle.cpp": "1b2aa2741338c2046380727a680420a8df3bc1d2fedc071f8e3b2bfeaf41f394",
    "FunSphKernel.h": "a4cc4a372c9c1bd40ed4d1f4b993564b2c26510143b06049a08c9cb9f66cb44d",
}
FIELDS = ["Pos.x [m]", "Pos.z [m]", "PorePress", "Vel.z [m/s]",
          "PoroVolumeRatio", "PoroThetaLastStage", "Kplastic"]


def entry(path):
    p = Path(path).resolve()
    return {"path": str(p), "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def recorded_entries(value, result):
    if isinstance(value, dict):
        if {"path", "bytes", "sha256"} <= value.keys():
            result[str(Path(value["path"]).resolve()).lower()] = value
        for child in value.values():
            recorded_entries(child, result)
    elif isinstance(value, list):
        for child in value:
            recorded_entries(child, result)


def verify_recorded(path, recorded):
    got = entry(path)
    ref = recorded[str(Path(path).resolve()).lower()]
    if got["bytes"] != ref["bytes"] or got["sha256"] != ref["sha256"].lower():
        raise ValueError("Consumed input does not match retained receipt: " + str(path))
    return got


def parameters(xml):
    root = ET.parse(xml).getroot()
    c = root.find("execution/constants")
    soil = root.find("execution/special/soils")
    hydro = root.find("execution/special/hydromechanics")
    get = lambda node, name: float(node.find(name).attrib["value"])
    f = np.float32
    dp, h = get(c, "dp"), f(get(c, "h"))
    E, nu = f(get(soil, "ModulusE")), f(get(soil, "PRvs"))
    K = f(E / f(f(3) * f(f(1) - f(f(2) * nu))))
    G = f(E / f(f(2) * f(f(1) + nu)))
    M = float(f(float(K) + 4. * float(G) / 3.))  # actual elastic K4G3 float
    rho = float(f(get(c, "rhop0")))
    p = {"dp": dp, "h": float(h), "bwen": float(f(-2.7852 / float(h)**3)),
         "awen": float(f(.557 / float(h)**2)), "Eta2": float(f((float(h)*.1)**2)),
         "KernelSize2": float(f(f(h*f(2)) * f(h*f(2)))),
         "V0": float(f(get(c, "massfluid"))) / rho, "rho0": rho,
         "K": float(K), "G": float(G), "M": M,
         "n0": float(f(get(hydro, "Porosity"))),
         "Kw": float(f(get(hydro, "PoreWaterBulkModulus"))),
         "rhow": float(f(get(hydro, "PoreWaterRho"))),
         "k": float(f(get(hydro, "HydraulicConductivity")))}
    p["B"] = p["Kw"] / p["n0"]
    p["gamma"] = p["rhow"] * 9.80665
    p["dt"] = float(root.find("execution/parameters/parameter[@key='DtFixed']").attrib["value"])
    if root.find("execution/particles").attrib["np"] != "1040":
        raise ValueError("Only the declared 40 fixed + 1000 soil column is modeled")
    if any(float(c.find("gravity").attrib[a]) != 0 for a in "xyz"):
        raise ValueError("This frozen model is g=0 only")
    return p


def matrices(p):
    """100 layer invariant subspace; horizontal offsets sum the 10-column periodic grid.

    Bottom slots -4..-1 mirror fluid 3..0: p/sigma/C even, v/Ace odd.
    Top is truncated, exactly as the modeled initial neighbor set; no added ghost.
    Pair coefficients follow float kernel paths, but subsequent linear algebra and
    accumulation are binary64: this is NOT the nonsmooth float C++ Jacobian.
    """
    f, n = np.float32, 100
    dp, V, rho = p["dp"], p["V0"], p["rho0"]
    z = (np.arange(-4, n) + .5) * dp
    h, b, limit = f(p["h"]), f(p["bwen"]), f(p["KernelSize2"])

    def fac(rr):
        rad = f(np.sqrt(f(rr)))
        q = f(rad/h)
        w = f(f(1)-f(f(.5)*q))
        return float(f(f(f(f(f(b*q)*w)*w)*w)/rad))

    def neighbors(i):
        for jj, zj in enumerate(z):
            j = jj-4
            owner = j if j >= 0 else -j-1
            for sx in range(-3, 4):
                d = np.array([sx*dp, z[i+4]-zj])
                rr = float(d@d)
                if f(rr) <= limit and f(rr) >= 1e-18:
                    yield owner, (1 if j >= 0 else -1), d, rr

    C = np.empty((n, 2, 2))
    for i in range(n):
        moment = np.zeros((2, 2))
        for _, _, d, rr in neighbors(i):
            moment -= V*fac(rr)*np.outer(d, d)
        C[i] = np.linalg.inv(moment)
    H, Dt, Ds, Da, Lp, Gp = [np.zeros((n, n)) for _ in range(6)]
    Lx = np.zeros(n)
    for i in range(n):
        for j, parity, d, rr in neighbors(i):
            g = fac(rr)*d
            cj = C[j].copy()
            if parity < 0:  # Q*C*Q; diagonal parity is even, x-z entries odd.
                cj[0, 1] *= -1
                cj[1, 0] *= -1
            gi, gj = C[i]@g, cj@g
            df = d.astype("float32")
            rf = f(f(df[0]*df[0])+f(df[1]*df[1]))
            gf = f(fac(rf))*df  # momentum raw float grad_i W
            hz = V/rho*float(gf[1])
            H[i, i] += hz
            H[i, j] += hz  # H acts on tensile-positive sigma_zz-p
            dfd = df.astype("float64")
            gt = fac(dfd@dfd)*dfd  # theta: float displacement -> double, CPU path
            wt = V*(C[i]@gt)[1]
            ws = float(f(V))*float(gf[1])*C[i, 1, 1]  # float volume stress gradient
            wa = V*gi[1]  # complete rate: double-position corrected divergence
            for matrix, weight in ((Dt, wt), (Ds, ws), (Da, wa)):
                matrix[i, i] -= weight
                matrix[i, j] += parity*weight
            weight = V*(d@(gi+gj))/(rr+p["Eta2"])
            Lp[i, i] += weight
            Lp[i, j] -= weight
            Gp[i, i] -= V*gi[1]
            Gp[i, j] += V*gi[1]
            Lx[i] += d[1]*weight
    return H, Dt, Ds, Da, Lp, Lp-Lx[:, None]*Gp, C, Lx


def spectra(p):
    H, Dt, Ds, Da, Lp, L, C, Lx = matrices(p)
    Z = np.zeros_like(H)
    variants = [("modeled_current", L, Da), ("diagnostic_no_acceleration", L, Z),
                ("diagnostic_raw_Lp", Lp, Da), ("diagnostic_compatible_rhoDH", p["rho0"]*Da@H, Da)]
    values, modes, summaries = [], [], []
    for name, lap, div_a in variants:
        factor = p["B"]*p["k"]/p["gamma"]
        dh = div_a@H
        A = np.block([[Z, H, -H], [p["M"]*Ds, Z, Z],
                      [-p["B"]*Dt, factor*p["rhow"]*dh, factor*(lap-p["rhow"]*dh)]])
        eigen, vectors = eig(A)
        if not np.isfinite(eigen).all():
            raise ValueError("Nonfinite offline eigenvalue")
        order = np.lexsort((eigen.imag, eigen.real))
        index = order[-1]
        lam, vec = eigen[index], vectors[:, index]
        vp = vec[200:]
        vec = vec*np.exp(-1j*np.angle(vp[np.argmax(abs(vp))]))/max(abs(vp))
        gain = 1+p["dt"]*lam+.5*(p["dt"]*lam)**2
        summaries.append({"variant": name, "max_real_s-1": float(lam.real),
                          "imag_rad_s": float(lam.imag),
                          "period_us": float(2*np.pi/abs(lam.imag)*1e6) if lam.imag else None,
                          "top10_pressure_energy_fraction": float(np.sum(abs(vp[-10:])**2)/np.sum(abs(vp)**2)),
                          "formal_midpoint_log_gain_s-1": float(np.log(abs(gain))/p["dt"])})
        values.extend([name, rank, float(eigen[j].real), float(eigen[j].imag)] for rank, j in enumerate(order))
        modes.extend([name, i, (i+.5)*p["dp"], *[float(q) for q in (vec[i].real, vec[i].imag, vec[100+i].real, vec[100+i].imag, vec[200+i].real, vec[200+i].imag)]] for i in range(100))
    return summaries, values, modes, {"Czz_bottom_inner_top": C[[0, 50, 99], 1, 1].tolist(),
                                     "Lx_top4_per_m": Lx[-4:].tolist(),
                                     "theta_vs_complete_divergence_relative_norm": float(np.linalg.norm(Dt-Da)/np.linalg.norm(Da))}


def exported_history(folder, p, recorded):
    history, top_values, used, initial = [], [], [], None
    for part in range(76):
        path = folder/f"native_{part:04d}.csv"
        used.append(verify_recorded(path, recorded))
        with path.open(newline="", encoding="utf-8-sig") as stream:
            rows = csv.reader(stream)
            next(rows)
            label = float(next(rows)[0])  # PartVTK display time, NOT native binary clock
            next(rows)
            body = list(csv.DictReader(stream))
        body.sort(key=lambda row: int(row["Idp"]))
        if [int(row["Idp"]) for row in body] != list(range(1040)):
            raise ValueError("Native diagnostic CSV ID set differs")
        a = np.array([[float(row[key]) for key in FIELDS] for row in body[40:]])
        if not np.isfinite(a).all():
            raise ValueError("Nonfinite diagnostic CSV")
        if initial is None:
            initial = a.copy()
            iz = np.rint(initial[:, 1]/p["dp"]-.5).astype(int)
            ix = np.rint(initial[:, 0]/p["dp"]-.5).astype(int)
            order = np.lexsort((ix, iz))
            if sorted(zip(iz, ix)) != [(i, j) for i in range(100) for j in range(10)]:
                raise ValueError("Initial CSV does not describe the nominal 100x10 grid")
            top = np.flatnonzero((iz == 99) & (ix == 0)).item()
        layer = a[order].reshape(100, 10, len(FIELDS))
        pressure, velocity = a[:, 2], a[:, 3]
        energy = np.sum(pressure**2)
        history.append([part, label, 10*part, 10*part*p["dt"],
                        float(np.sqrt(np.mean(pressure**2))), float(np.sqrt(np.mean(velocity**2))),
                        float(np.sum(layer[-10:, :, 2]**2)/energy) if energy else 0.,
                        float(np.sum(layer[:10, :, 2]**2)/energy) if energy else 0.,
                        *[float(np.max(abs(layer[:, :, k]-layer[:, :1, k]))) for k in (2, 3, 4, 5)],
                        float(a[:, 4].min()), float(a[:, 4].max()), float(a[:, 6].max())])
        top_values.append([label, pressure[top], velocity[top]])
    return history, np.array(top_values), used


def fit_history(top, history):
    """Independent CSV fit: FFT frequency seed and whole-column RMS growth seed.

    No matrix eigenvalue or previously observed growth/frequency is used as a seed.
    Fit window 20..55 was specified before this persisted analysis is executed.
    """
    rows = slice(20, 56)
    t = top[rows, 0]
    tc, duration = t-t[-1], t[-1]-t[0]
    step = float(np.median(np.diff(t)))
    result, curves = [], []
    for col, name, rmscol in ((1, "top_pressure_Pa", 4), (2, "top_velocity_z_m_s", 5)):
        raw = top[rows, col]
        scale = float(max(abs(raw)))
        y = raw/scale
        fft = abs(np.fft.rfft(y-y.mean()))
        frequency = np.fft.rfftfreq(len(y), step)[1+np.argmax(fft[1:])]
        growth = float(np.polyfit(tc, np.log(np.array(history)[rows, rmscol]), 1)[0])
        lo, hi = np.array([-1/duration, 2*np.pi/duration]), np.array([100/duration, np.pi/step])

        def predicted(par):
            decay = np.exp(par[0]*tc)
            X = np.column_stack((decay*np.cos(par[1]*tc), decay*np.sin(par[1]*tc), np.ones_like(tc), tc/duration))
            return X@np.linalg.lstsq(X, y, rcond=None)[0]

        seed = np.clip([growth, 2*np.pi*frequency], lo+1e-8, hi-1e-8)
        fit = least_squares(lambda par: predicted(par)-y, seed, bounds=(lo, hi),
                            ftol=1e-12, xtol=1e-12, gtol=1e-12, max_nfev=500)
        fitted = predicted(fit.x)*scale
        result.append({"field": name, "parts_inclusive": [20, 55],
                       "optimizer_success": bool(fit.success), "FFT_seed_rad_s": float(seed[1]),
                       "RMS_growth_seed_s-1": float(seed[0]), "growth_s-1": float(fit.x[0]),
                       "omega_rad_s": float(fit.x[1]), "period_us": float(2*np.pi/fit.x[1]*1e6),
                       "R_squared": float(1-np.sum((fitted-raw)**2)/np.sum((raw-raw.mean())**2))})
        curves.extend([name, part, float(time), float(obs), float(pred)] for part, time, obs, pred in zip(range(20, 56), t, raw, fitted))
    return result, curves


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Fresh diagnostic JSON")
    parser.add_argument("--csv-prefix", type=Path, required=True, help="Fresh figures CSV basename")
    args = parser.parse_args()
    targets = [args.out] + [Path(str(args.csv_prefix)+suffix) for suffix in ("_history.csv", "_eigen.csv", "_mode.csv", "_fit.csv")]
    if any(path.exists() for path in targets):
        raise FileExistsError("Refusing to overwrite any diagnostic target")
    note = T/"notes/upl_case02_frozen_matrix_r1.json"
    paths = [T/"logs/upl_case02_short_failure_r1.export.json", T/"logs/upl_case02_short_failure_r1.review.json", T/"logs/upl_case02_short_coarse_r1.run.json", T/"logs/upl_case02_short_r1.inputs.json"]
    records = [json.loads(path.read_text(encoding="utf-8-sig")) for path in paths]
    recorded = {}
    for value in records:
        recorded_entries(value, recorded)
    if records[2]["exit_code"] != 1 or records[2]["passed"] is not False or records[0]["exit_code"] != 0:
        raise ValueError("Expected retained failed solver and successful diagnostic converter")
    if not records[1]["analysis_completed"] or records[1]["retained_frames"] != 76:
        raise ValueError("Expected the existing independent diagnostic export review")
    xml = T/"outputs/upl_case02_short_r1_seed/upl_case02_short_coarse_r1.xml"
    used = [entry(Path(__file__)), entry(note), *[entry(path) for path in paths]]
    used += [verify_recorded(xml, recorded), verify_recorded(paths[0], recorded),
             verify_recorded(paths[2], recorded), verify_recorded(paths[3], recorded)]
    source = []
    for name, sha in SOURCE_SHA.items():
        got = entry(SOURCE/name)
        if got["sha256"] != sha:
            raise ValueError("Formula source changed; use a new declared revision: " + name)
        source.append(got)
    used += source
    p = parameters(xml)
    history, top, csv_inputs = exported_history(T/"outputs/upl_case02_short_failure_r1_export", p, recorded)
    used += csv_inputs
    fits, curves = fit_history(top, history)
    spectral, eigen, modes, matrix_diagnostics = spectra(p)
    if any(entry(ref["path"]) != ref for ref in used):
        raise ValueError("Consumed source/input changed during offline analysis")
    for target, header, rows in zip(targets[1:], [
            ["part", "CSV_display_time_s", "nominal_completed_steps", "nominal_time_s", "pressure_RMS_Pa", "vz_RMS_m_s", "top10_pressure_energy_fraction", "bottom10_pressure_energy_fraction", "within_layer_p_spread_Pa", "within_layer_vz_spread_m_s", "within_layer_J_spread", "within_layer_theta_spread_s-1", "Jmin", "Jmax", "Kplasticmax"],
            ["variant", "rank_real_then_imag", "real_s-1", "imag_rad_s"],
            ["variant", "layer", "nominal_z_m", "v_real", "v_imag", "sigma_real", "sigma_imag", "p_real", "p_imag"],
            ["field", "part", "CSV_display_time_s", "observed", "fitted"]], [history, eigen, modes, curves]):
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(rows)
    result = {"stage": "upl_case02_frozen_matrix_r1", "analysis_completed": True,
              "physical_acceptance": False, "actual_CPP_Jacobian": False,
              "failed_trajectory_reclassified_as_passed": False, "native_program_invoked": False,
              "hypothesis_requires_actual_operator_verification": True,
              "clock_is_CSV_display_or_nominal_not_decoded_binary": True,
              "CSV_frames": 76, "soil_layers": 100, "soil_columns": 10,
              "fit_window_parts": [20, 55], "parameters": p, "spectral_diagnostics": spectral,
              "matrix_diagnostics": matrix_diagnostics, "independent_CSV_fits": fits,
              "formula_locations_at_authoring": json.loads(note.read_text(encoding="utf-8-sig"))["formula_locations_at_authoring"],
              "max_CSV_display_minus_nominal_time_s": max(abs(row[1]-row[3]) for row in history),
              "current_formula_sources": source, "inputs": used, "files": [entry(q) for q in targets[1:]],
              "provenance_scope": "Consumed CSV/XML/source and metadata hashes only; not a new full raw-BI4/build/object audit",
              "versions": {"Python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__},
              "limitations": ["Nominal decimal grid, x-invariant linear subspace, J=1 fixed coefficients, no actual C++ accumulation/Jacobian.",
                              "No load-ramp forcing or position/normal/C state evolution is integrated; eigenvectors are diagnostic only.",
                              "Formal midpoint polynomial is not a rerun or proof of the production integrator.",
                              "Removing acceleration/compensation or substituting rhoDH are counterfactual diagnostics, not proposed admitted physical models.",
                              "No conclusion about the unsaved failure particle/stage or its plastic/J/nonfinite branch.",
                              "No GPU, half-step, drained-event, continuum accuracy, long-time stability or public-path acceptance."]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"analysis_completed": True, "physical_acceptance": False, "out": str(args.out)}))


if __name__ == "__main__":
    main()

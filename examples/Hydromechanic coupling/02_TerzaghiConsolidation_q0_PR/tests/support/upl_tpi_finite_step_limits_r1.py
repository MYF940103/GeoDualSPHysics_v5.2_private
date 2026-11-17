"""Reproduce the already identified finite-h algebraic counterexamples only; not a solver."""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG = "upl_tpi_finite_step_limits_r1"
NOTE = T / "notes" / (TAG + ".md")
BASE = T / "configs/upl_bigstep_c625_r1.xml"
OUT = T / "outputs" / TAG
CHECK = T / "logs" / (TAG + ".check.json")


def need(q, text):
    if not bool(q):
        raise ValueError(text)


def stat(path):
    p = Path(path).resolve(); s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def write_json(path, value):
    with path.open("x", encoding="utf8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write("\n")


def fixed_parameters():
    xml = ET.parse(BASE).getroot()
    val = lambda name: float(next(xml.iter(name)).get("value"))
    E, nu, rho = val("ModulusE"), val("PRvs"), float(next(xml.iter("rhop0")).get("value"))
    water, k, event = val("PoreWaterRho"), val("HydraulicConductivity"), val("HydroMechDrainageStartTime")
    need((E, nu, rho, water, k, event) == (2e6, .3, 2100., 1000., 1e-4, .010000228881835938), "Original XML example changed")
    return dict(M=E*(1-nu)/((1+nu)*(1-2*nu)), rho=rho, water=water, k=k,
                gamma=water*9.80665, event=event, dp=.01)


def step(y, q, mu, h, kind, c):
    """State=(sigma,v,p,p_previous[,actual_previous_F0_acceleration])."""
    sigma, velocity, pressure, previous = y[:4]
    iq = 1j*q
    an = iq*(sigma-pressure)/c["rho"]
    vh = velocity+.5*h*an
    sh = sigma+.5*h*c["M"]*iq*velocity
    guess = pressure+.5*(pressure-previous)
    if kind == "H3":
        source_acceleration = iq*(sh-guess)/c["rho"]
    elif kind == "old_a":
        source_acceleration = an
    elif kind == "extrap_a":
        source_acceleration = 1.5*an-.5*y[4]
    else:
        raise ValueError("No additional candidate admitted")
    S = c["k"]*q*q/(1-mu)
    ph = (-c["gamma"]*iq*vh+c["water"]*c["k"]*iq*source_acceleration+S*mu*guess)/S
    final = [sigma+h*c["M"]*iq*vh, velocity+h*iq*(sh-ph)/c["rho"], 2*ph-pressure, pressure]
    if kind == "extrap_a":
        final.append(an)
    return np.array(final, dtype=complex)


def calculations(c):
    tau = c["k"]*(c["rho"]-c["water"])/c["gamma"]
    r = c["water"]/c["rho"]
    rows = []
    trial4 = np.array((1+.2j, .3-.1j, -.4+.7j, .2+.5j))
    for q in (math.pi/2, math.pi/c["dp"]):
      for mu in (.2, .8):
        t = 1-mu; e = r*t; delta = (1-r)*t; m = 1-delta
        for divisor in (1000., 500.):
          h = c["event"]/divisor
          C = delta*h/tau
          row = dict(q_m_inv=q, mu_prescribed=mu, dt_s=h, Omega_squared=c["M"]*q*q*h*h/c["rho"],
              m=m, delta=delta, C=C, tau_s=tau,
              H3_low_Omega_h_limit_s=tau*delta/m,
              old_a_low_Omega_h_limit_s=tau*(1-mu)/mu,
              H3_low_Omega_Schur_primary_passed=m*C < delta*delta,
              old_a_low_Omega_Schur_primary_passed=mu*C < t*delta)
          for kind in ("H3", "old_a", "extrap_a"):
            n = 5 if kind == "extrap_a" else 4
            A = np.column_stack([step(v, q, mu, h, kind, c) for v in np.eye(n, dtype=complex)])
            trial = np.r_[trial4, .125-.25j] if n == 5 else trial4
            direct = step(trial, q, mu, h, kind, c)
            tol = 256*np.finfo(float).eps*(abs(A)@abs(trial)+abs(direct))+256*float(np.nextafter(0., 1.))
            need(np.all(abs(A@trial-direct) <= tol), "Declared finite-h map is not linear")
            scale = [c["M"], math.sqrt(c["M"]/c["rho"]), c["M"], c["M"]]
            if n == 5:
                scale.append(math.sqrt(c["M"]/c["rho"])/tau)
            scaled = A*np.array(scale)[None, :]/np.array(scale)[:, None]
            roots, vectors = np.linalg.eig(scaled)
            error = np.max(abs(scaled@vectors-vectors*roots[None, :]), axis=0)
            budget = 4096*np.finfo(float).eps*(np.linalg.norm(scaled, np.inf)+abs(roots))*np.max(abs(vectors), axis=0)
            budget += 4096*float(np.nextafter(0., 1.))
            need(np.all(error <= budget), "Finite-h eigensystem arithmetic failed")
            row[kind+"_nominal_spectral_radius"] = float(max(abs(roots)))
            row[kind+"_nominal_roots"] = n
          rows.append(row)
    need(len(rows) == 8, "Only the eight existing inline combinations are reproduced")
    need(all(any(x[k+"_nominal_spectral_radius"] > 1 for x in rows) for k in ("H3", "old_a", "extrap_a")), "Recorded counterexamples differ; preserve and review")
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--execution-authorized", action="store_true")
    need(p.parse_args().execution_authorized, "Root full-read single algebra execution required")
    need(not OUT.exists() and not CHECK.exists(), "Existing/partial outputs protected")
    before = [stat(x) for x in (Path(__file__), NOTE, BASE)]
    result = dict(stage=TAG, passed=False, consumed=before, solver_invocations=0, native_invocations=0,
        old_script_invocations=0, build_invocations=0, SHA_scans=0, physical_acceptance=False,
        actual_SPH_spectrum_proven=False, actual_timestep_admission=False, candidate_selected=False,
        H3_author_HOLD=True, P1_loadclock_homogeneous_map_changed=False)
    try:
        c = fixed_parameters(); rows = calculations(c); OUT.mkdir()
        product = OUT/"finite_h.csv"
        with product.open("x", encoding="utf8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        need(all(stat(x["path"]) == x for x in before), "Consumed algebra author/input changed")
        result.update(passed=True, algebra_complete=True, constants_XML_example=c, combinations=8,
            small_matrices=24, roots=104, file=stat(product),
            interpretation="Finite-h algebraic counterexamples only; no reflected candidate selected")
    except Exception as exc:
        result.update(first_failure=str(exc), partial_outputs_preserved=True); raise
    finally:
        write_json(CHECK, result)
    print(str(CHECK))


if __name__ == "__main__":
    main()

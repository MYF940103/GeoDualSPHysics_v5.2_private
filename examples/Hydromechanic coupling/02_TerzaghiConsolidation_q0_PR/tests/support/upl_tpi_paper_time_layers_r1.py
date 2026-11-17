"""Author-only fixed-mode pressure-time-layer design; no SPH/reader/build/old component."""
from __future__ import annotations
import argparse
import cmath
import csv
import itertools
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

T = Path(__file__).resolve().parents[1]
R = T.parents[3]
TAG = "upl_tpi_paper_time_layers_r1"
NOTE = T / "notes" / (TAG + ".md")
BASE = T / "configs/upl_bigstep_c625_r1.xml"
P1 = T / "support/upl_tpi_time_layers_r1.py"
PAPER = R / "src/papers/u-pw/Lian 2023 u-pl.md"
OUT = T / "outputs" / TAG
CHECK = T / "logs" / (TAG + ".check.json")
EPS = np.finfo(float).eps
TINY = float(np.nextafter(0., 1.))
ALPHA = .5
H_PROBES = (1e-8, 2e-8, 4e-8, 8e-8)


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def stat(path):
    path = Path(path).resolve()
    s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def write_json(path, value):
    with path.open("x", encoding="utf8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def write_csv(path, rows):
    with path.open("x", encoding="utf8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def constants():
    root = ET.parse(BASE).getroot()
    val = lambda name: float(next(root.iter(name)).get("value"))
    E, nu = val("ModulusE"), val("PRvs")
    rho = float(next(root.iter("rhop0")).get("value"))
    water, k = val("PoreWaterRho"), val("HydraulicConductivity")
    need((E, nu, rho, water, k) == (2e6, .3, 2100., 1000., 1e-4), "Frozen XML example constants differ")
    return dict(M=E*(1-nu)/((1+nu)*(1-2*nu)), rho=rho, water=water,
                k=k, gamma=water*9.80665, dp=.01)


def operators(c, q, mu):
    """Homogeneous Fourier model only; mu is prescribed, not an observed SPH eigenvalue."""
    iq = 1j*q
    r = c["water"]/c["rho"]
    delta = (1-r)*(1-mu)
    m = 1-delta
    P = np.array((-r/(1-r), -c["gamma"]*iq/(c["k"]*q*q*(1-r))), dtype=complex)
    L = np.array(((0, c["M"]*iq), (iq/(c["rho"]-c["water"]),
                   -c["gamma"]/(c["k"]*(c["rho"]-c["water"])))), dtype=complex)
    D = c["water"]*iq/(q*q*(1-r))
    return P, L, D, m, delta


def row(c, q, mu, solid, guess, force_source=0.):
    """Same leading-LP defect step, including acceleration feedback; no beta or rescaled S."""
    sigma, velocity = solid
    iq = 1j*q
    acceleration = iq*(sigma-guess)/c["rho"] + force_source
    diagonal = c["k"]*q*q/(1-mu)
    source = -c["gamma"]*iq*velocity + c["water"]*c["k"]*iq*acceleration
    return (source+diagonal*mu*guess)/diagonal


def current4(y, c, q, mu, h):
    """Literal P1 four-state map with case02 XML constants: (sigma,v,p,p_previous)."""
    sigma, velocity, pressure, previous = y
    iq = 1j*q
    acceleration = iq*(sigma-pressure)/c["rho"]
    vh = velocity + .5*h*acceleration
    sh = sigma + .5*h*c["M"]*iq*velocity
    guess = pressure + ALPHA*(pressure-previous)
    ah = iq*(sh-guess)/c["rho"]
    sf = sigma + h*c["M"]*iq*vh
    vf = velocity + h*ah
    pf = row(c, q, mu, (sf, vf), guess)
    return np.array((sf, vf, pf, pressure), dtype=complex)


def midpoint_reflect4(y, c, q, mu, h):
    """New mathematical H3 design; p_endpoint is a reflection, not an endpoint row solve."""
    sigma, velocity, pressure, previous = y
    iq = 1j*q
    acceleration = iq*(sigma-pressure)/c["rho"]
    vh = velocity + .5*h*acceleration
    sh = sigma + .5*h*c["M"]*iq*velocity
    guess = pressure + ALPHA*(pressure-previous)
    ph = row(c, q, mu, (sh, vh), guess)
    ah = iq*(sh-ph)/c["rho"]
    sf = sigma + h*c["M"]*iq*vh
    vf = velocity + h*ah
    return np.array((sf, vf, 2*ph-pressure, pressure), dtype=complex)


def with_position(step, z, c, q, mu, h):
    """Private/current elastic corrector position rule: xnew=xn+h*(vn+vnew)/2."""
    ynew = step(z[:4], c, q, mu, h)
    return np.r_[ynew, z[4]+.5*h*(z[1]+ynew[1])]


def matrix(step, c, q, mu, h, dimension=4):
    eye = np.eye(dimension, dtype=complex)
    if dimension == 4:
        return np.column_stack([step(e, c, q, mu, h) for e in eye])
    return np.column_stack([with_position(step, e, c, q, mu, h) for e in eye])


def eigen(A, c):
    scales = np.array((c["M"], math.sqrt(c["M"]/c["rho"]), c["M"], c["M"]))
    scaled = A*scales[None, :]/scales[:, None]
    z, v = np.linalg.eig(scaled)
    err = np.max(abs(scaled@v-v*z[None, :]), axis=0)
    scale = (np.linalg.norm(scaled, np.inf)+abs(z))*np.max(abs(v), axis=0)
    budget = 4096*EPS*scale+4096*TINY
    need(np.all(err <= budget), "New small-matrix eigensystem arithmetic failed")
    return z, float(np.max(err/budget))


def calculations(c):
    methods = []
    modes = []
    ramps = []
    identities = []
    trial = np.array((1+.2j, .3-.1j, -.4+.7j, .2+.5j))
    ztrial = np.r_[trial, .1-.2j]
    definitions = (("current_P1_endpoint", current4), ("H3_half_reflect_autonomous_design", midpoint_reflect4))
    for qname, q in (("pi_over_2", math.pi/2), ("pi_over_dp", math.pi/c["dp"])):
      for mu in (.2, .8):
        P, L, D, m, delta = operators(c, q, mu)
        need(0 < m < 1, "Only this nominal positive-real fast-block fixture is selected")
        lam = np.linalg.eigvals(L)
        guess = trial[2]+ALPHA*(trial[2]-trial[3])
        for name, step in definitions:
          zero = step(trial, c, q, mu, 0.)
          expected = delta*(P@trial[:2])+m*guess
          if step is midpoint_reflect4:
              expected = 2*expected-trial[2]
          budget = 256*EPS*(abs(zero[2])+abs(expected)+abs(delta*(P@trial[:2]))+abs(m*guess))+256*TINY
          need(abs(zero[2]-expected) <= budget and np.array_equal(zero[[0, 1, 3]], trial[[0, 1, 2]]),
               "New h0 map identity differs")
          trace, determinant = (m*(1+ALPHA), m*ALPHA) if step is current4 else (2*m*(1+ALPHA)-1, 2*m*ALPHA)
          root = cmath.sqrt(trace*trace-4*determinant)
          fast = ((trace+root)/2, (trace-root)/2)
          identities.append(dict(method=name, q_name=qname, mu=mu, m=m, delta=delta,
              h0_pressure_identity_error=abs(zero[2]-expected), arithmetic_budget=budget,
              history_trace=trace, history_determinant=determinant, nominal_fast_radius=max(map(abs, fast)),
              fast_root1_real=fast[0].real, fast_root1_imag=fast[0].imag,
              fast_root2_real=fast[1].real, fast_root2_imag=fast[1].imag))
          last_error = last_h = None
          for h in H_PROBES:
            A = matrix(step, c, q, mu, h)
            A5 = matrix(step, c, q, mu, h, 5)
            direct = step(trial, c, q, mu, h)
            direct5 = with_position(step, ztrial, c, q, mu, h)
            tol = 256*EPS*(abs(A)@abs(trial)+abs(direct))+256*TINY
            tol5 = 256*EPS*(abs(A5)@abs(ztrial)+abs(direct5))+256*TINY
            need(np.all(abs(A@trial-direct) <= tol) and np.all(abs(A5@ztrial-direct5) <= tol5),
                 "Declared four/five-state map is not linear")
            z, eig_ratio = eigen(A, c)
            exact = np.exp(lam*h)
            order = min(itertools.permutations(range(4)), key=lambda p: sum(abs(z[p[i]]-exact[i])**2 for i in range(2)))
            associations = {order[i]: i for i in range(2)}
            errors = []
            for j, value in enumerate(z):
                generator = cmath.log(value)/h if value != 0 else None
                error = abs(generator-lam[associations[j]]) if j in associations and generator is not None else None
                if error is not None:
                    errors.append(error)
                modes.append(dict(method=name, q_name=qname, mu=mu, h_algebra_s=h, mode=j,
                    z_real=value.real, z_imag=value.imag, abs_z=abs(value), matched_physical=j in associations,
                    generator_error=error, reference_lambda_real=lam[associations[j]].real if j in associations else None,
                    reference_lambda_imag=lam[associations[j]].imag if j in associations else None))
            error = max(errors)
            observed = math.log(error/last_error)/math.log(h/last_h) if last_error and error else None
            lag = -m*(1-ALPHA)/delta if step is current4 else m*(ALPHA-.5)/delta
            methods.append(dict(method=name, q_name=qname, mu=mu, m=m, h_algebra_s=h,
                pressure_leading_h_PL_coefficient=lag,
                mechanical_modified_generator_h_bPL_coefficient=ALPHA-.5+lag if step is current4 else lag,
                physical_generator_max_error=error, observed_generator_error_order=observed,
                nominal_spectral_radius=float(max(abs(z))), eigensystem_arithmetic_ratio=eig_ratio,
                actual_position_rule="xnew=xn+h*(vn+vnew)/2", matrix5_neutral_x_preserved=True))
            last_error, last_h = error, h
        for source_fraction in (0., .5):
            # p*=P*y+D*f(t). These are closed first-jet coefficients, not a physical ramp simulation.
            lag_D_fdot = source_fraction-.5
            local_D_fdot = delta*(2*source_fraction-1)
            local_direct = 2*(delta*source_fraction+m*ALPHA)-1
            rb = 256*EPS*(abs(local_direct)+abs(local_D_fdot)+1.)
            need(abs(local_direct-local_D_fdot) <= rb, "Affine-ramp first-jet identity differs")
            slow_left = 2*delta*lag_D_fdot
            slow_right = 2*delta*source_fraction+2*m*ALPHA-1
            need(abs(slow_left-slow_right) <= rb, "Established-history affine-ramp lag identity differs")
            ramps.append(dict(q_name=qname, mu=mu, m=m, source_fraction=source_fraction, D_real=D.real, D_imag=D.imag,
                exact_history_single_step_endpoint_h_D_fdot_coefficient=local_D_fdot,
                established_slow_manifold_pressure_h_D_fdot_coefficient=lag_D_fdot,
                first_jet_arithmetic_budget=rb, established_lag_identity_error=abs(slow_left-slow_right),
                mechanical_forcing_first_order_defect_present=source_fraction != .5,
                physical_ramp_or_startup_accuracy_proven=False))
    need((len(identities), len(methods), len(modes), len(ramps)) == (8, 32, 128, 8), "New algebra coverage differs")
    return identities, methods, modes, ramps


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execution-authorized", action="store_true")
    need(p.parse_args().execution_authorized, "Root full-read unique algebra-only authorization required")
    need(not OUT.exists() and not CHECK.exists(), "Existing/partial results protected; never overwrite")
    before = [stat(p) for p in (Path(__file__), NOTE, BASE, P1, PAPER)]
    c = constants()
    result = dict(stage=TAG, passed=False, author_only_design=True, physical_acceptance=False,
        solver_invocations=0, native_invocations=0, old_component_invocations=0, build_invocations=0,
        physical_steps=0, SHA_scans=0, actual_SPH_spectrum_proven=False, actual_timestep_admission=False,
        paper_literal_LF_claimed=False, source_time_or_BC_change_implemented=False, constants_XML_example=c, consumed=before)
    try:
        values = calculations(c)
        OUT.mkdir()
        names = ("identities", "methods", "modes", "ramp_first_jets")
        for name, rows in zip(names, values):
            write_csv(OUT/(name+".csv"), rows)
        need(all(stat(q["path"]) == q for q in before), "Consumed author/reference changed during algebra")
        result.update(passed=True, analysis_complete=True, new_matrices=32, new_roots=128,
            source_ramp_cases=8, autonomous_only_order_diagnostics=True, beta=0, alpha=ALPHA,
            actual_HG_or_boundary_or_loading_closure_proven=False,
            files=[stat(OUT/(n+".csv")) for n in names])
    except Exception as exc:
        result.update(first_failure=str(exc), partial_outputs_preserved=True)
        raise
    finally:
        write_json(CHECK, result)
    print(str(CHECK))


if __name__ == "__main__":
    main()

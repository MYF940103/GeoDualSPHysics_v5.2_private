"""Ideal drained M0 sphere. Run with --write once to archive, or without it to check."""
import argparse
import ast
import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mpmath as mp
import numpy as np
from scipy.optimize import brentq
from scipy.special import spherical_jn


TESTS = Path(__file__).resolve().parents[1]
CASE = TESTS.parent
TAG = "c04_m0_radial_inertia_r1"
RETURN = TESTS / "figures/cryer_p3_server_peak_actual_r1/physical"
XML = CASE / "CaseCryer_TPI_P3_nu030_peak_r1_Def.xml"
REFERENCE = CASE / "support/plot_cryer_formal_four_nu_r1.py"
RADIUS = .05
CENTER_R = .0025
Q = 10000.


def read_reference():
    # Import only the existing mathematical class, without invoking the plot/solver workflow.
    nodes = ast.parse(REFERENCE.read_text(encoding="utf-8-sig")).body
    classes = [item for item in nodes if isinstance(item, ast.ClassDef) and item.name == "Reference"]
    assert len(classes) == 1
    scope = dict(R=RADIUS, Q=Q, np=np, brentq=brentq)
    exec(compile(ast.Module(body=classes, type_ignores=[]), str(REFERENCE), "exec"), scope)
    ref = scope["Reference"](.3, finite=False)
    ref.cv = ref.kappa * ref.H
    ref.decay = ref.xi**2 * ref.cv / RADIUS**2
    return ref


def material(xml):
    root = ET.parse(xml).getroot()
    value = lambda name: float(root.find(".//" + name).get("value"))
    assert root.find(".//drawsphere").get("radius") == "#radius"
    radii = [float(node.get("radius")) for node in root.findall(".//newvarcte") if node.get("radius")]
    assert radii == [RADIUS]
    assert value("ModulusE") == 2e6 and value("PRvs") == .3 and value("HydroMechTopLoadQ0") == Q
    assert value("HydroMechDrainageStartTime") == 1/128
    rho, water, k = value("rhop0"), value("PoreWaterRho"), value("HydraulicConductivity")
    assert (rho, water, k) == (2100, 1000, 1e-5)
    return rho, water, k


def modal(ref, n, b, d):
    decay = ref.decay[:n]
    amp = Q * ref.amplitude[:n] * (np.sinc(ref.xi[:n] * CENTER_R / (np.pi * RADIUS)) - ref.sx[:n])
    disc = np.sqrt((1 - 4*b*decay).astype(complex))
    slow = -2*decay/(1+disc)
    fast = -(1+disc)/(2*b)
    # Both residues of (1+(b-d)s)/(b*s**2+s+decay); non-real poles occur in pairs.
    slow_res = (1+(b-d)*slow)/(b*(slow-fast))
    fast_res = (1+(b-d)*fast)/(b*(fast-slow))

    def pressure(tau, order=0, dynamic=True):
        if not dynamic:
            return float(np.sum(amp * (-decay)**order * np.exp(-decay*tau)))
        values = slow_res * slow**order * np.exp(slow*tau) + fast_res * fast**order * np.exp(fast*tau)
        total = np.sum(amp * values)
        assert abs(total.imag) < 1e-8
        return float(total.real)

    return pressure


def invert_boundary(ref, r, t, b, d, degree):
    # Direct spherical boundary-value solution on the Laplace contour.
    # No modal roots, amplitudes, residues or quasi-static evaluation in this path.
    def transform(s):
        z = RADIUS * mp.sqrt(s * (1+b*s)/ref.cv)
        y = z*r/RADIUS
        center_i0 = mp.sinh(y)/y if y else 1
        i0 = mp.sinh(z)/z
        i1 = (mp.cosh(z)-i0)/z
        radial = (i0-center_i0)/(i0 - 4*ref.G/ref.H*i1/z)
        return Q/s * (1-d*s/(1+b*s)) * radial
    return float(mp.invertlaplace(transform, t, method="dehoog", degree=degree))


def summarize(ref, sample, b, d):
    test_tau = np.array([r["tau_s"] for r in sample])
    theory = np.array([r["M0_r18_Pa"] for r in sample])
    native = np.array([r["center18_Pa"] for r in sample])
    conv = []
    for count in (8, 16, 32, 64, 128, 360):
        func = modal(ref, count, b, d)
        peak0 = brentq(lambda t: func(t, 1, False), .035, .05, xtol=5e-15)
        peak1 = brentq(lambda t: func(t, 1), .035, .05, xtol=5e-15)
        p0, p1 = func(peak0, 0, False), func(peak1)
        quasi = np.array([func(t, 0, False) for t in test_tau])
        dynamic = np.array([func(t) for t in test_tau])
        delta = dynamic - quasi
        conv.append(dict(modes=count, quasi_peak_Pa=p0, quasi_tau_s=peak0, dyn_peak_Pa=p1, dyn_tau_s=peak1,
                         peak_change_Pa=p1-p0, peak_time_change_us=(peak1-peak0)*1e6,
                         static_vs_saved_ref_max_Pa=float(max(abs(quasi-theory))),
                         corr_max_Pa=float(max(abs(delta))), corr_rms_Pa=float(np.sqrt(np.mean(delta**2)))))
    assert conv[-1]["static_vs_saved_ref_max_Pa"] < 1e-8
    for field in ("peak_change_Pa", "peak_time_change_us", "corr_max_Pa", "corr_rms_Pa"):
        assert max(abs(row[field]-conv[-1][field]) for row in conv[-4:]) < 1e-8
    rows = [dict(part=int(row["part"]), actual_tau_s=t, simulated_Pa=p, quasistatic_Pa=q,
                 ideal_dynamic_Pa=v, inertia_minus_quasistatic_Pa=v-q) for row,t,p,q,v in zip(
                     sample,test_tau,native,quasi,dynamic)]
    peakrow = int(np.argmax(native))
    measures = dict(native_peak_Pa=float(native[peakrow]), native_peak_actual_tau_s=float(test_tau[peakrow]),
                    vs_ideal_dynamic_amplitude_Pa=float(native[peakrow]-p1),
                    vs_ideal_dynamic_phase_s=float(test_tau[peakrow]-peak1),
                    native_rows=len(native), tau_first_s=float(test_tau[0]), tau_last_s=float(test_tau[-1]),
                    sampled_quasi_peak_part=int(rows[int(np.argmax(quasi))]["part"]),
                    sampled_dynamic_peak_part=int(rows[int(np.argmax(dynamic))]["part"]))
    return conv, rows, measures, func


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    rho, water, k = material(XML)
    ref = read_reference()
    assert abs(ref.kappa-k/(water*9.80665)) < 1e-24
    b, d = ref.kappa*(rho-water), ref.kappa*rho
    with (RETURN/"native_and_theory.csv").open(newline="") as f:
        sample = [{key:float(row[key]) for key in ("part","time_s","tau_s","center18_Pa","M0_r18_Pa")}
                  for row in csv.DictReader(f) if float(row["legacy_Tv"]) >= .005 and float(row["tau_s"]) <= .0625]
    assert len(sample) == 475 and all(r["time_s"]-1/128==r["tau_s"] for r in sample)
    traction_res = max(abs(spherical_jn(0,ref.xi) - 4*ref.G/ref.H*spherical_jn(1,ref.xi)/ref.xi))
    assert traction_res < 1e-12
    conv, rows, measures, func = summarize(ref,sample,b,d)
    checks = []
    for t in [sample[0]["tau_s"], .01, conv[-1]["quasi_tau_s"], conv[-1]["dyn_tau_s"], sample[-1]["tau_s"]]:
        for dynamic in (False, True):
            bb, dd = (b,d) if dynamic else (0.,0.)
            direct = invert_boundary(ref,CENTER_R,t,bb,dd,48)
            direct32 = invert_boundary(ref,CENTER_R,t,bb,dd,32)
            root_sum = func(t,0,dynamic)
            assert abs(direct-root_sum)<1e-7 and abs(direct32-direct)<1e-7
            checks.append(dict(tau_s=t, dynamic=dynamic, root_sum_Pa=root_sum, inverse_Pa=direct,
                               inverse_minus_sum_Pa=direct-root_sum,inverse_32_minus_48_Pa=direct32-direct))
    # Near the start of the Mandel window the 360th mode is underdamped.
    # These modes have real part -1/(2*b), so their contribution there is exponentially small.
    assert 4*b*ref.decay[-1] > 1
    report = dict(tag=TAG, ideal_M0_only=True, sphere_radius_m=RADIUS, material_radius_m=CENTER_R,
                  D_m2_s=ref.cv, b_s=b, d_s=d, mixture_rho_kg_m3=rho, water_rho_kg_m3=water,
                  first_three_decay_per_s=ref.decay[:3].tolist(),
                  traction_eigencondition_max=traction_res, convergence=conv, independent_inversions=checks,
                  physical_observations=measures)
    if args.write:
        out_json = TESTS/"logs"/(TAG+".json")
        out_csv = TESTS/"figures"/(TAG+".csv")
        out_png = out_csv.with_suffix(".png")
        if any(p.exists() for p in (out_json,out_csv,out_png)):
            raise FileExistsError("New results only. Run without --write for independent recalculation.")
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2,1,figsize=(8,5.4),sharex=True,constrained_layout=True)
        t_ms = np.array([row["actual_tau_s"] for row in rows])*1000
        axes[0].plot(t_ms, [row["simulated_Pa"]-row["quasistatic_Pa"] for row in rows], color="#24537a")
        axes[0].set_ylabel("P3 minus quasi-static [Pa]")
        axes[1].plot(t_ms, [row["inertia_minus_quasistatic_Pa"] for row in rows],color="#ac480c")
        axes[1].set_ylabel("Ideal inertial correction [Pa]")
        axes[1].set_xlabel("Time after drainage opens [ms]")
        for ax in axes:
            ax.axhline(0,c="0.5",ls="--",lw=.8)
            ax.grid(alpha=.22)
        fig.suptitle("Cryer sphere at r/a = 0.05, M0, Poisson's ratio 0.30")
        fig.savefig(out_png,dpi=170)
        plt.close(fig)
        with out_csv.open("x",newline="") as f:
            writer = csv.DictWriter(f,fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        with out_json.open("x") as f:
            json.dump(report,f,indent=2)
    print(json.dumps(dict(peak=conv[-1], measures=measures,
        max_inverse_error_Pa=max(abs(row["inverse_minus_sum_Pa"]) for row in checks))))


if __name__=="__main__":
    main()

"""Offline continuous-model algebra only; never imports or launches the SPH solver."""
import argparse
import itertools
import json
import math
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser()
    for name in ("xml", "run-out", "completion", "run-receipt", "declaration"):
        p.add_argument("--" + name, required=True, type=pathlib.Path)
    args = p.parse_args()
    declaration = json.loads(args.declaration.read_text(encoding="utf-8-sig"))
    require(not declaration["production_guard_implemented"], "Unexpected production gate declaration")
    x = ET.parse(args.xml).getroot()
    execution = x.find("execution")
    constants = execution.find("constants")
    soil = execution.find("special/soils")
    hydro = execution.find("special/hydromechanics")
    f32 = lambda node, key: np.float32(node.find(key).attrib["value"])
    rho0, n0, rw, kw, kh = (float(v) for v in (f32(constants, "rhop0"), f32(hydro, "Porosity"), f32(hydro, "PoreWaterRho"), f32(hydro, "PoreWaterBulkModulus"), f32(hydro, "HydraulicConductivity")))
    E, nu = f32(soil, "ModulusE"), f32(soil, "PRvs")
    K = float(E / (np.float32(3) * (np.float32(1) - np.float32(2) * nu)))
    G = float(E / (np.float32(2) * (np.float32(1) + nu)))
    run_text = args.run_out.read_text(encoding="utf-8-sig")
    logged = lambda label: float(re.search(r"^\s*" + re.escape(label) + r":\s*([-+0-9.eE]+)", run_text, re.M).group(1))
    require(K == logged("Bulk Modulus") and G == logged("Shear Modulus"), "Loaded float moduli do not match actual run")
    gravity = constants.find("gravity").attrib
    require(all(float(gravity[a]) == 0 for a in ("x", "y", "z")), "Only retained gravity-off wave admitted")
    require(0 < n0 < 1 and rho0 > rw > 0 and kw > 0 and kh > 0, "Unexpected retained material")
    domain = execution.find("parameters/simulationdomain")
    width = float(domain.find("posmax").attrib["x"]) - float(domain.find("posmin").attrib["x"])
    dt = float(next(e.attrib["value"] for e in execution.findall("parameters/parameter") if e.attrib["key"] == "DtFixed"))
    completion = json.loads(args.completion.read_text(encoding="utf-8-sig"))
    receipt = json.loads(args.run_receipt.read_text(encoding="utf-8-sig"))
    require(completion["passed"] and completion["hydraulic_conductivity"] == kh and completion["native_ids"] == 128, "Wrong completed-wave material/identity")
    require(receipt["exit_code"] == 0 and receipt["owned_call_exited"] and receipt["arguments"][:4] == ["--job", "actual", "0", "256"], "Wrong completed-wave control")
    require(pathlib.Path(str(receipt["arguments"][7]) + ".xml") == args.xml, "XML is not the actual run input")
    M, gamma, kappa = K + 4 * G / 3, rw * 9.80665, 2 * math.pi / width
    solid0 = 1 - n0
    jcrit = solid0 + (rho0 - rw) * kw / (rw * M)
    epsilon, factor = np.finfo(np.float64).eps, 32768
    cases = [("J1", 1.0, kh, "stable"), ("J1p01", 1.01, kh, "stable"), ("below_Jcrit", jcrit - 1e-6, kh, "stable"), ("at_Jcrit", jcrit, kh, "marginal"), ("above_Jcrit", jcrit + 1e-6, kh, "unstable"), ("J1p02", 1.02, kh, "unstable"), ("k0_J1", 1.0, 0.0, "neutral"), ("k0_J1p02", 1.02, 0.0, "neutral")]
    results = []
    for label, J, k, expected in cases:
        n, rho = 1 - solid0 / J, rw + (rho0 - rw) / J
        B, r = kw / n, rw / rho
        D = B * k / gamma
        cu = math.sqrt((M + B) / rho)
        omega, Z = cu * kappa, rho * cu
        A = np.array([[0, -kappa / rho, kappa / rho], [M * kappa, 0, 0], [-B * kappa, -D * r * kappa**2, -D * (1 - r) * kappa**2]])
        scaling = np.array([1.0, Z, Z])
        H = A * scaling[None, :] / scaling[:, None] / omega
        coefficients = np.array([1.0, D * (1 - r) * kappa**2 / omega, (M + B) * kappa**2 / (rho * omega**2), D * M * kappa**4 / (rho * omega**3)])
        eig = np.linalg.eigvals(H)
        roots = np.roots(coefficients)
        physical = np.linalg.eigvals(A) / omega
        match = lambda values: min(max(abs(eig[i] - values[j]) for i, j in enumerate(order)) for order in itertools.permutations(range(3)))
        tolerance = factor * epsilon * max(1, np.linalg.norm(H, 2), sum(abs(coefficients)))
        require(match(roots) <= tolerance and match(physical) <= tolerance, "Matrix/cubic roots disagree")
        residuals = [abs(np.polyval(coefficients, z)) / max(1, sum(abs(c) * abs(z) ** (3 - i) for i, c in enumerate(coefficients))) for z in eig]
        require(max(residuals) <= factor * epsilon, "Polynomial residual exceeded predeclared scale")
        margin = rho * B - rw * (M + B)
        identity_error = abs((J - solid0) * margin - rw * M * (jcrit - J))
        identity_scale = max(1, abs((rho0 - rw) * kw), abs(rw * M * (J - solid0)))
        require(identity_error <= factor * epsilon * identity_scale and abs((1 - n) * J - solid0) <= 5e-13, "Closed-J/Routh algebra failed")
        maximum_real = float(max(eig.real))
        if expected == "stable":
            require(margin > 0 and maximum_real < -tolerance, "Declared strictly stable sample disagrees")
        elif expected == "unstable":
            require(margin < 0 and maximum_real > tolerance, "Declared unstable sample disagrees")
        else:
            require(abs(maximum_real) <= tolerance and max(abs(eig.imag)) > 0.5, "Marginal/neutral pair missing")
            if k == 0:
                require(match(np.array([0, 1j, -1j])) <= tolerance, "k0 is not the undamped degenerate spectrum")
            else:
                require(abs(margin) <= factor * epsilon * max(1, abs(rho * B), abs(rw * (M + B))), "Jcrit is not the continuous boundary")
        growth = float(maximum_real * omega)
        increments = [math.expm1(growth * step) for step in (dt, dt / 2)]
        if expected == "unstable":
            require(all(v > 0 for v in increments), "Smaller positive step concealed continuous growth")
        results.append(dict(label=label, expected=expected, J=J, n=n, rho_t_kg_m3=rho, k_m_s=k, B_Pa=B, D_m2_s=D, cu_m_s=cu, strict_RH_applicable=k > 0, RH_margin_Pa_kg_m3=margin, storage_weighted_margin_kg_m3=rho * B / (M + B) - rw, max_real_pole_per_s=growth, poles_per_s=[dict(real=float(z.real * omega), imag=float(z.imag * omega)) for z in eig], normalized_root_match_error=match(roots), normalized_physical_match_error=match(physical), normalized_tolerance=float(tolerance), polynomial_scaled_residual_max=float(max(residuals)), closed_J_identity_scaled_error=identity_error / identity_scale, exact_continuous_growth_expm1_coarse_half=increments))
    print(json.dumps(dict(passed=True, scope="Frozen continuous low-frequency finite-Kw model, not discrete operator/time-policy acceptance", python_version=sys.version, numpy_version=np.__version__, material=dict(rho0_kg_m3=rho0, n0=n0, rho_water_kg_m3=rw, Kw_Pa=kw, E_loaded_float_Pa=float(E), nu_loaded_float=float(nu), K_loaded_float_Pa=K, G_loaded_float_Pa=G, M_double_Pa=M, k_loaded_float_m_s=kh, physical_gravity_m_s2=[0, 0, 0], g_reference_m_s2=9.80665, gamma_N_m3=gamma), periodic_width_m=width, kappa_per_m=kappa, original_fixed_dt_s=dt, Jcrit=jcrit, positive_k_samples=6, k0_samples=2, cases=results, smaller_dt_repairs_continuous_instability=False, new_solver_started=False, production_guard_implemented=False, physical_acceptance=False), indent=2))


if __name__ == "__main__":
    main()

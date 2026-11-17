"""Author-only nominal-interior C02 TPI timestep algebra; never a physical stability certificate."""
from __future__ import annotations
import argparse
import ast
import cmath
import csv
import itertools
import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
TAG = "upl_tpi_case02_step_spectrum_r2"
NOTE = T / "notes" / (TAG + ".md")
OUT = T / "outputs" / TAG
CHECK = T / "logs" / (TAG + ".check.json")
XML = T / "configs/upl_bigstep_c625_r1.xml"
P1 = T / "support/upl_tpi_time_layers_r1.py"
P1_NOTE = T / "notes/upl_tpi_time_layers_r1.md"
SOURCE = T / "outputs/upl_tpi_gpu_full2tv_r1_source"
SOURCE_NAMES = ("JSph.cpp", "JSphGpu_ker.cu", "FunSphKernel_iker.h", "upl_tpi_gpu_r1.h")


def need(ok, message):
    if not bool(ok): raise ValueError(message)


def stat(path):
    p = Path(path).resolve(); s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def write_json(path, value):
    with path.open("x", encoding="utf8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write("\n")


def write_csv(path, rows):
    need(bool(rows), "Empty component table")
    with path.open("x", encoding="utf8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


class Admission:
    def __init__(self, path):
        self.entry = stat(path); self.data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        need(self.data.get("stage") == TAG + ".admission" and self.data.get("passed") is True and
             self.data.get("algebra_only") is True, "Root full-read, unique algebra-only admission required")
        self.frozen = {str(Path(x["path"]).resolve()): x for x in self.data["inputs"]}
        need(len(self.frozen) == len(self.data["inputs"]), "Duplicated frozen input")
        self.used = {}
        for p in (Path(__file__), NOTE, XML, P1, P1_NOTE, *[SOURCE / n for n in SOURCE_NAMES]): self.pin(p)

    def pin(self, path):
        key = str(Path(path).resolve()); need(key in self.frozen, "Consumed input absent from admission: " + key)
        expected = {k: self.frozen[key][k] for k in ("path", "bytes", "mtime_ns")}
        need(stat(key) == expected, "Frozen stat changed: " + key); self.used[key] = expected
        return Path(key)

    def finish(self):
        for x in self.used.values(): need(stat(x["path"]) == x, "Consumed source changed during algebra")
        need(stat(self.entry["path"]) == self.entry, "Admission changed")


def material(ad):
    root = ET.parse(ad.pin(XML)).getroot(); val = lambda n: float(next(root.iter(n)).get("value"))
    E, nu, rho, water, k, kw, n, h, dp, td = [val(nm) for nm in ("ModulusE", "PRvs", "rhop0", "PoreWaterRho",
        "HydraulicConductivity", "PoreWaterBulkModulus", "Porosity", "h", "dp", "HydroMechDrainageStartTime")]
    need((E, nu, rho, water, k, kw, n, h, dp, td) ==
         (2e6, .3, 2100., 1000., 1e-4, 2e8, .3, .018, .01, .010000228881835938), "Actual retained C02 XML constants changed")
    fixed = float(next(p for p in root.iter("parameter") if p.get("key") == "DtFixed").get("value"))
    need(fixed == td/1600., "Original event-commensurate fixed step differs")
    params = {v.get("name"): float(v.get("value")) for v in root.iter("varnum")}
    need(params["sizefx"] == .1 and params["sizefz"] == 1., "Actual width/height differs")
    # Literal all-float material initialization in JSph.cpp3753-54, then double Mc in the current step code.
    ef, nf = f32(E), f32(nu)
    bulk = f32(ef/f32(f32(3.)*f32(f32(1.)-f32(f32(2.)*nf))))
    shear = f32(ef/f32(f32(2.)*f32(f32(1.)+nf)))
    mc = bulk+4.*shear/3.; hf = f32(h); gamma = f32(water)*9.80665
    return dict(E_XML_Pa=E, nu_XML=nu, Mc_XML_reference_Pa=E*(1-nu)/((1+nu)*(1-2*nu)),
        K_loaded_float_Pa=bulk, G_loaded_float_Pa=shear, Mc_loaded_double_Pa=mc,
        rho_kg_m3=rho, rhow_kg_m3=f32(water), k_XML_m_s=k, k_loaded_float_m_s=f32(k),
        Kw_XML_Pa=kw, n_XML=n, gamma_dynamic_Pa_m=gamma, reference_gravity_m_s2=9.80665,
        dp_m=dp, h_loaded_float_m=hf, Eta2_loaded_float_m2=f32((hf*.1)*(hf*.1)),
        domain_height_m=1., periodic_width_m=.1, material_layers=100, periodic_X_columns=10,
        dt_original_s=fixed, drain_time_s=td, dt_candidate_1_s=td/1000., dt_candidate_2_s=td/500.,
        tau_M0_initial_s=f32(k)*(rho-f32(water))/gamma,
        bone_wave_m_s=math.sqrt(mc/rho), M0_longitudinal_wave_m_s=math.sqrt(mc/(rho-f32(water))))


def source_definitions(ad):
    text = {n: ad.pin(SOURCE / n).read_text(encoding="utf-8-sig") for n in SOURCE_NAMES}
    tokens = {"JSph.cpp": ("const double h=KernelH;", "Eta2=float((h*0.1)*(h*0.1));",
                           "SoilCte.ModulusK = float(SoilCte.ModulusE / (3.f*(1.f - 2.f*SoilCte.PRvs)));",
                           "SoilCte.ModulusG = float(SoilCte.ModulusE / (2.f*(1.f + SoilCte.PRvs)));"),
        "FunSphKernel_iker.h": ("return(bwen*qq*wqq1*wqq1*wqq1/rad);",),
        "JSphGpu_ker.cu": ("const double w=vol2*(d.x*(gi.x+gj.x)+d.y*(gi.y+gj.y)+d.z*(gi.z+gj.z))/(rr2+double(CTE.eta2));",
                           "const double lap=lp-gpcorr.x*lx.x-gpcorr.y*lx.y-gpcorr.z*lx.z+rhow*da;"),
        "upl_tpi_gpu_r1.h": ("double time,unsigned long long step,double dt,bool drain,unsigned loadmode);",)}
    for name, values in tokens.items():
        for token in values: need(token in text[name], "Retained definition absent: " + name + "/" + token)
    old = ast.parse(ad.pin(P1).read_text(encoding="utf-8-sig"))
    current = ast.parse(ad.pin(Path(__file__)).read_text(encoding="utf-8-sig"))
    old_step = [n for n in ast.walk(old) if isinstance(n, ast.FunctionDef) and n.name == "step"]
    new_step = [n for n in ast.walk(current) if isinstance(n, ast.FunctionDef) and n.name == "step"]
    need(len(old_step) == len(new_step) == 1 and
         [ast.dump(n, include_attributes=False) for n in old_step[0].body] ==
         [ast.dump(n, include_attributes=False) for n in new_step[0].body], "Original P1 complete step-map operations changed")
    return dict(source_tokens_present=True, original_P1_step_body_AST_identical=True,
        original_P1_component_imported_or_executed=False, float_CUDA_kernel_replay_claimed=False)


def make_step(p):
    H, RHO, RHOW, K, GAMMA = (p[k] for k in ("Mc_loaded_double_Pa", "rho_kg_m3", "rhow_kg_m3", "k_loaded_float_m_s", "gamma_dynamic_Pa_m"))

    def step(y,q,mu,h,alpha,half):
        """State=(sigma,v,p,p_previous); h=0 is only a closed-map identity probe."""
        sn,vn,pn,previous=y;iq=1j*q
        an=iq*(sn-pn)/RHO
        vh,sh=vn+h*.5*an,sn+h*.5*H*iq*vn
        ph=pn if half==0 else pn+half*(pn-previous)
        ah=iq*(sh-ph)/RHO
        sf,vf=sn+h*H*iq*vh,vn+h*ah
        guess=pn if alpha==0 else pn+alpha*(pn-previous)
        ae=iq*(sf-guess)/RHO
        S=K*q*q/(1-mu)
        B=-GAMMA*iq*vf+RHOW*K*iq*ae
        pf=(B+S*mu*guess)/S
        return np.array((sf,vf,pf,pn),dtype=complex)
    return step


def kernel_neighbors(p):
    """Nominal infinite-lattice interior, analytic radial shape, NOT GPU float instruction replay."""
    dp, h, eta = p["dp_m"], p["h_loaded_float_m"], p["Eta2_loaded_float_m2"]
    pairs = []
    for iz in range(-4, 5):
        for ix in range(-4, 5):
            x, z = ix*dp, iz*dp; rr = x*x+z*z
            if not rr or rr > (2*h)**2: continue
            shape = (1-math.sqrt(rr)/(2*h))**3
            pairs.append(dict(ix=ix, iz=iz, dx_m=x, dz_m=z, r2_m2=rr, shape_cubed=shape,
                              unnormalized_positive_LP_weight=shape*rr/(rr+eta)))
    need(len(pairs) == 36 and (2*h) < p["periodic_width_m"]/2, "Nominal fixed-neighbor support differs")
    # For uniform isotropic C=cI, bwen/h, c and V cancel. The corrected first moment fixes the remaining scale.
    m2 = sum(v["dz_m"]**2*v["shape_cubed"] for v in pairs)
    need(m2 > 0 and math.isfinite(m2), "Nominal interior correction moment is singular")
    for v in pairs:
        v["a_positive_m_inv2"] = 2*v["unnormalized_positive_LP_weight"]/m2
        need(v["a_positive_m_inv2"] > 0, "Nominal positive LP weight required")
    total = sum(v["a_positive_m_inv2"] for v in pairs)
    need(all(any(w["ix"] == -v["ix"] and w["iz"] == -v["iz"] and w["a_positive_m_inv2"] == v["a_positive_m_inv2"] for w in pairs) for v in pairs), "Nominal inversion symmetry differs")
    return pairs, total


def nominal_modes(p, pairs, diagonal, np):
    modes = []
    def add(family, ix, iz, qx, qz):
        phases = [qx*v["dx_m"]+qz*v["dz_m"] for v in pairs]
        ell = sum(v["a_positive_m_inv2"]*(1-math.cos(a)) for v, a in zip(pairs, phases))
        direct = sum(v["a_positive_m_inv2"]*math.cos(a) for v, a in zip(pairs, phases))/diagonal
        mu = 1-ell/diagonal
        need(ell > 0 and math.isfinite(ell) and -1 <= mu < 1 and abs(mu-direct) <= 128*np.finfo(float).eps,
             "Positive normalized nominal LP symbol arithmetic differs")
        q = math.sqrt(ell); S = p["k_loaded_float_m_s"]*q*q/(1-mu)
        nominalS = p["k_loaded_float_m_s"]*diagonal
        bound = 128*np.finfo(float).eps*(1+1/(1-mu))*max(S, nominalS)
        need(abs(S-nominalS) <= bound, "Common-symbol ell/S dimensions or roundoff identity differs")
        modes.append(dict(mode=len(modes), family=family, X_mode=ix, Z_mode=iz, qx_geometric_m_inv=qx, qz_geometric_m_inv=qz,
            q_geometric_m_inv=math.hypot(qx,qz), q_P1_common_symbol_m_inv=q, ell_nominal_m_inv2=ell,
            LP_positive_diagonal_m_inv2=diagonal, mu_normalized_neighbor_symbol=mu, mu_direct_cosine_sum=direct,
            m_density_shifted=p["rhow_kg_m3"]/p["rho_kg_m3"]+(1-p["rhow_kg_m3"]/p["rho_kg_m3"])*mu,
            S_P1_per_m_s=S, S_nominal_k_times_weight_sum_per_m_s=nominalS,
            S_roundoff_relative_difference=abs(S-nominalS)/nominalS,
            actual_C02_boundary_or_full_Rgamma_symbol=False))
    for iz in range(100): add("postdrain_Neumann_Dirichlet_Z_nominal", 0, iz, 0., (iz+.5)*math.pi/p["domain_height_m"])
    for ix in range(1, 6): add("periodic_X_interior_only", ix, -1, 2*math.pi*ix/p["periodic_width_m"], 0.)
    for ix in range(1, 6):
        for iz in (0, 49, 99): add("mixed_longitudinal_interior_only", ix, iz, 2*math.pi*ix/p["periodic_width_m"], (iz+.5)*math.pi/p["domain_height_m"])
    need(len(modes) == 120, "Declared nominal wavevector count differs")
    return modes


def reference(q, p, np):
    rho, water, mc, k, gamma = (p[v] for v in ("rho_kg_m3", "rhow_kg_m3", "Mc_loaded_double_Pa", "k_loaded_float_m_s", "gamma_dynamic_Pa_m"))
    r = water/rho; iq = 1j*q; dr = rho-water
    P = np.array((-r/(1-r), -gamma*iq/(k*q*q*(1-r))), dtype=complex)
    tr, det = -gamma/(k*dr), mc*q*q/dr
    root = cmath.sqrt(tr*tr-4*det); fast = (tr-root)/2; slow = det/fast
    return P, np.array((slow, fast), dtype=complex)


def calculate(p, modes, step, np):
    eps, tiny = np.finfo(float).eps, float(np.nextafter(0., 1.)); matrices, roots = [], []
    probe = np.array((1+.2j, .3-.1j, -.4+.7j, .2+.5j), dtype=complex)
    scales = np.array((p["Mc_loaded_double_Pa"], math.sqrt(p["Mc_loaded_double_Pa"]/p["rho_kg_m3"]), p["Mc_loaded_double_Pa"], p["Mc_loaded_double_Pa"]))
    steps = (("old_same_dt", p["dt_original_s"]), ("candidate_td_over_1000", p["dt_candidate_1_s"]), ("candidate_td_over_500", p["dt_candidate_2_s"]))
    for mode in modes:
        q, mu, m = mode["q_P1_common_symbol_m_inv"], mode["mu_normalized_neighbor_symbol"], mode["m_density_shifted"]
        P, lam = reference(q, p, np)
        zero = step(probe, q, mu, 0., .5, .5); guess = probe[2]+.5*(probe[2]-probe[3])
        r = p["rhow_kg_m3"]/p["rho_kg_m3"]
        delta = (1-r)*(1-mu)
        m_stable = mu+r*(1-mu)
        expected = delta*(P@probe[:2])+m_stable*guess
        need(abs(zero[2]-expected) <= 256*eps*(abs(zero[2])+abs(expected)+abs(m*guess))+256*tiny,
             "P1 h0 pressure-constraint identity differs")
        for name, dt in steps:
            A = np.column_stack([step(v,q,mu,dt,.5,.5) for v in np.eye(4,dtype=complex)])
            direct = step(probe,q,mu,dt,.5,.5)
            need(np.all(abs(A@probe-direct) <= 256*eps*(abs(A)@abs(probe)+abs(direct))+256*tiny), "Complete four-state map arithmetic differs")
            scaled = A*scales[None,:]/scales[:,None]; z, vectors = np.linalg.eig(scaled)
            err = np.max(abs(scaled@vectors-vectors*z[None,:]),axis=0)
            budget = 4096*eps*(np.linalg.norm(scaled,np.inf)+abs(z))*np.max(abs(vectors),axis=0)+4096*tiny
            need(np.all(np.isfinite(z)) and np.all(err <= budget), "Four-root eigensystem arithmetic residual failed")
            exact = np.exp(lam*dt)
            order = min(itertools.permutations(range(4)), key=lambda v: sum(abs(z[v[j]]-exact[j])**2 for j in range(2)))
            roles = {order[j]:j for j in range(2)}
            for j, value in enumerate(z):
                reference_index = roles.get(j); generator = cmath.log(value)/dt if value != 0 else None
                roots.append(dict(mode=mode["mode"], dt_name=name, dt_s=dt, root=j, real=value.real, imag=value.imag, abs_z=abs(value),
                    role="unmatched_history" if reference_index is None else ("closest_slow_M0_common_symbol" if reference_index == 0 else "closest_fast_M0_common_symbol"),
                    reference_exp_real=None if reference_index is None else exact[reference_index].real,
                    reference_exp_imag=None if reference_index is None else exact[reference_index].imag,
                    generator_real_s_inv=None if generator is None else generator.real, generator_imag_rad_s=None if generator is None else generator.imag,
                    matching_is_diagnostic_not_actual_SPH_mode_proof=True))
            radius = float(max(abs(z)))
            matrices.append(dict(mode=mode["mode"], family=mode["family"], dt_name=name, dt_s=dt, dt_over_old=dt/p["dt_original_s"],
                dt_over_tau=dt/p["tau_M0_initial_s"], q_common_symbol_m_inv=q, mu=mu, spectral_radius=radius,
                spectral_radius_minus_one=radius-1., strict_computed_radius_le_one=radius <= 1.,
                eigensystem_arithmetic_ratio=float(np.max(err/budget)),
                max_closest_physical_exp_absolute_difference=float(max(abs(z[order[j]]-exact[j]) for j in range(2))),
                pressure_lag_first_coefficient_m_over_2_one_minus_m=m/(2*(1-m)),
                coupled_fast_scale_is_not_a_hard_two_tau_guard=True,
                **{"A_%d%d_real"%(i,j): float(A[i,j].real) for i in range(4) for j in range(4)},
                **{"A_%d%d_imag"%(i,j): float(A[i,j].imag) for i in range(4) for j in range(4)}))
    need(len(matrices) == 360 and len(roots) == 1440, "Declared120-mode/three-step/four-root coverage differs")
    return matrices, roots


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--execution-authorized", action="store_true")
    parser.add_argument("--admission", required=True, type=Path); args = parser.parse_args()
    need(args.execution_authorized, "Explicit root unique algebra-only admission required")
    need(not OUT.exists() and not CHECK.exists(), "Existing/partial component output protected; no rerun")
    ad = Admission(args.admission)
    result = dict(stage=TAG, passed=False, algebra_completed=False, root_admission=ad.entry, physical_acceptance=False,
        solver_invocations=0, native_reads=0, build_invocations=0, old_component_invocations=0, SHA_scans=0,
        actual_SPH_spectrum_proven=False, timestep_admission=False, automatic_follow_up=False)
    try:
        global np
        import numpy as np
        p = material(ad); provenance = source_definitions(ad); pairs, diagonal = kernel_neighbors(p)
        modes = nominal_modes(p, pairs, diagonal, np); step = make_step(p); matrices, roots = calculate(p, modes, step, np)
        summary = dict(stage=TAG, algebra_completed=True, parameters=p, source=provenance, nominal_neighbors=len(pairs),
            nominal_modes=len(modes), four_state_matrices=len(matrices), all_roots=len(roots), step_reports={},
            mu_is_derived_nominal_positive_LP_not_arbitrary_grid=True, P1_common_symbol_q_equals_sqrt_ell=True,
            S_nominal_equals_k_times_positive_weight_sum_mathematically=True,
            original_P1_entire_step_map_preserved=True, alpha_neighbor=.5, mechanical_half_predictor=.5, beta=0,
            actual_GPU_float_kernel_arithmetic_replayed=False, actual_SPH_full_spectrum_proven=False, timestep_admission=False,
            unresolved=["Nominal uniform interior C=cI/positive LP is not the bounded-column wall/free-surface row.",
                "Actual Kr/Ks/Ksigma/Ka are not one common sqrt(ell); the model does not silently claim otherwise.",
                "Full Taylor/Neumann pressure defect and actual pressure-to-acceleration feedback symbols are not measured here.",
                "Current J, AV, damping, HG force/cache/spin, and force-bound restrictions are not included in this four-state spectrum.",
                "Closed-startup uniform pressure/load constraint and the neutral q=0 gauge are not qualified by post-drain mode labels.",
                "Existing old300-layer Jacobian/no-stabilizer and other-material periodic P3 symbols do not establish this actual full operator."],
            continuous_tau_is_scale_only_no_two_tau_gate=True, paper_R_or_capacity_multiplier_used=False,
            same_geometry_h_materials_and_default_A_unchanged=True, physical_acceptance=False)
        for name in ("old_same_dt", "candidate_td_over_1000", "candidate_td_over_500"):
            rows = [r for r in matrices if r["dt_name"] == name]
            summary["step_reports"][name] = dict(dt_s=rows[0]["dt_s"], dt_over_old=rows[0]["dt_over_old"],
                maximum_computed_radius=max(r["spectral_radius"] for r in rows), minimum_computed_radius=min(r["spectral_radius"] for r in rows),
                strict_float_radius_above_one_count=sum(not r["strict_computed_radius_le_one"] for r in rows),
                maximum_radius_mode=max(rows, key=lambda r:r["spectral_radius"])["mode"],
                this_is_reported_not_an_automatic_stability_or_physical_gate=True)
        ad.finish(); OUT.mkdir()
        for name, rows in (("neighbors.csv", pairs), ("nominal_modes.csv", modes), ("matrices.csv", matrices), ("roots.csv", roots)):
            write_csv(OUT / name, rows)
        write_json(OUT / "summary.json", summary); ad.finish()
        result.update(passed=True, algebra_completed=True, files=[stat(OUT / n) for n in ("neighbors.csv", "nominal_modes.csv", "matrices.csv", "roots.csv", "summary.json")])
    except Exception as exc:
        result.update(first_failure=str(exc), partial_outputs_preserved=True); raise
    finally:
        result["consumed"] = list(ad.used.values()); write_json(CHECK, result)
    print(str(CHECK)); return 0


if __name__ == "__main__":
    raise SystemExit(main())

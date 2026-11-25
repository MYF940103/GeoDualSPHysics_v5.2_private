"""Fixed-PRE material mobilization in C08 +2.5 degree explicit and private TPI runs."""
import argparse
import csv
from pathlib import Path

import numpy as np

from c08_psi25_tpi_native import CASE, PRE, DT, PRE_IDS, RELEASE_IDS, SOIL_IDS, native, read_frame, require, verify_source_material

DEFAULT_TIMES = (.01, .10, .20, .30, .60, 1.20)


def source_properties(meta):
    verify_source_material(meta, "psi2p5")
    before, rest = meta["GravityPreloadHandoffContract"].split(" material ")
    values = list(map(float, rest.split(" law ")[0].split()))
    # The v1 prefix contains the public soil constants, including phi_peak, phi_residual and n_phi.
    constants = before.split(" normals ")[0].split()
    require(constants[:2] == ["gravity-preload-2", "gravity-preload-1"]
            and list(map(float, constants[13:16])) == [float(np.float32(np.deg2rad(25)))]*2+[0.]
            and values[0] == 3 and values[3:6] == [5000., 1000., 5.]
            and "law 2 trigger PartBeginSoftening 0 " in rest, "Unexpected DP fit, friction, strength or trigger")
    return float(constants[13]), *values[3:6]


def invariant_fields(a, props):
    """FunSoilMaterial.h GetInvariants and UpdateDPvars, DP_PS (fit 3), tension-positive stress."""
    phi, c_peak, c_residual, nc = props
    normal = a["SigmaState_kk"]
    shear = a["SigmaState_ij"]
    xx, yy, zz = normal.T
    p_eff = -(xx+yy+zz)/3
    q = np.sqrt(((xx-yy)**2+(yy-zz)**2+(zz-xx)**2)/6 + np.sum(shear**2, axis=1))
    kappa = np.asarray(a["Kplastic"], dtype=np.float64)
    tanphi = np.tan(phi)
    den = np.sqrt(9+12*tanphi**2)
    cohesion = c_residual+(c_peak-c_residual)*np.exp(-nc*kappa)
    capacity = 3*cohesion/den + 3*tanphi/den*p_eff
    # The original return uses a 1e-5 Pa yield tolerance. q/q_yield is undefined at the cone apex.
    return p_eff, q, capacity


def material(a, ids):
    require(np.array_equal(a["Idp"], ids) and np.array_equal(ids[-5000:], SOIL_IDS),
            "Material ID or fixed boundary ownership differs")
    return {k:v[-5000:] for k,v in a.items()}


def cohorts(pre):
    x, _, z = pre["Posd"].T
    middle = (z>.25)&(z<1.75)
    return {"right_x3_4": middle&(x>=3)&(x<=4),
            "left_interior_x1_2": middle&(x>=1)&(x<=2),
            "whole": np.ones(len(x), dtype=bool)}


def summarize(row, region, sel, metrics, mobil_defined):
    result = dict(row, region=region, material_count=int(sel.sum()),
                  defined_q_over_yield_count=int((sel&mobil_defined).sum()))
    require(result["material_count"]>0, "Empty material cohort")
    for name, values in metrics.items():
        mask = (sel&mobil_defined) if name=="q_over_yield" else sel
        require(np.isfinite(values[mask]).all(), "Nonfinite native metric: "+name)
        quantiles = np.quantile(values[mask], (.05,.50,.95)) if mask.any() else ("","","")
        result.update({name+suffix: value for suffix,value in zip(("_p05","_p50","_p95"),quantiles)})
    return result


def run(label, folder, times, pre, props):
    folder = folder.resolve()
    require((folder/"data").is_dir(), "Expected native data directory under "+str(folder))
    # The private TPI plan saves its first released update at PART 5, then subcycles to 12.
    # Its first nominal .01 s is PART 13. The explicit plan saves .01 s at PART 1.
    explicit = (folder/"data/Part_0000.bi4").is_file()
    masks = cohorts(pre)
    pre_peff, _, _ = invariant_fields(pre, props)
    results = []
    for tau in times:
        index = round(tau/.01)
        require(index>0 and abs(index*.01-tau)<1e-12, "Expected a positive multiple of .01 s")
        part = index if explicit else index+12
        f = folder/"data"/f"Part_{part:04d}.bi4"
        if explicit:
            m, a = native(f)
            scheme = "explicit"
        else:
            m, a, h, _ = read_frame(f)
            scheme = h["Scheme"]
            require(scheme in ("P3_B_alpha_half_beta_zero", "P3_B_alpha_half_beta_0p04")
                    and h["SavedTime"]==m["TimeStep"], "Unexpected TPI scheme or history clock")
        step = m["Step"]+1
        owner = Path(m["GravityPreloadStateFile"])
        require((folder/owner).resolve()==PRE or (CASE/owner).resolve()==PRE,
                "This run descends from another PRE: "+str(owner))
        dtau = m["TimeStep"]-m["GravityPreloadActualTime"]
        expected_updates = index*2000+(1 if explicit else 0)
        model = m.get("HydroMechModel", m.get("HydroMechDynamicSeepage"))
        require(m["Cpart"]==part and m["Nout"]==0 and m["GravityPreloadPhase"]==1
                and m["GravityPreloadTargetIdBegin"]==1805 and m["GravityPreloadTargetIdCount"]==255
                and m["GravityPreloadActualCompletedStep"]==(2000000 if explicit else 2000200)
                and step-m["GravityPreloadActualCompletedStep"]==expected_updates
                and abs(dtau-tau)<=DT*1.01 and m["SymplecticDtPre"]==DT
                and model==(1 if explicit else 2) and m["MaterialLawVersion"]==2
                and m["DilationDecay"]==np.float32(.2), "Unexpected clock, model or release in "+f.name)
        a = material(a, RELEASE_IDS)
        require(a["PorePress0"].tobytes()==pre["PorePress0"].tobytes(), "Soil pressure reference mismatch")
        dp = a["PorePress"].astype(np.float64)-pre["PorePress"]
        u = a["Posd"]-pre["Posd"]
        peff, q, cap = invariant_fields(a, props)
        mobil_defined = cap>1e-5
        mobil = np.divide(q,cap,out=np.full_like(q,np.nan),where=mobil_defined)
        dpeff = peff-pre_peff
        metrics = {"p_minus_pre_kPa":dp/1000, "eff_compression_kPa":peff/1000,
                   "eff_compression_minus_pre_kPa":dpeff/1000, "total_compression_minus_pre_kPa":(dpeff+dp)/1000,
                   "q_sqrtJ2_kPa":q/1000, "yield_q_kPa":cap/1000, "q_over_yield":mobil,
                   "kappa":a["Kplastic"], "vx_m_s":a["Vel"][:,0], "ux_m":u[:,0],
                   "displacement_xz_m":np.hypot(u[:,0],u[:,2])}
        info = dict(label=label, scheme=scheme, native_file=str(f.relative_to(CASE)), part=part,
                    completed_step=step, nominal_tau_s=tau, actual_time_s=m["TimeStep"],
                    actual_release_s=m["GravityPreloadActualTime"], actual_tau_s=dtau)
        for region, sel in masks.items():
            results.append(summarize(info, region, sel, metrics, mobil_defined))
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", nargs=2, action="append", required=True, metavar=("LABEL","DIRECTORY"))
    ap.add_argument("--times", nargs="+", type=float, default=DEFAULT_TIMES)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    require(len(set(label for label,_ in args.run))==len(args.run), "Duplicate run labels")
    sm, fields = native(PRE)
    props = source_properties(sm)
    require(sm["Step"]+1==2000000 and sm["GravityPreloadPhase"]==0, "Wrong source stage")
    pre = material(fields, PRE_IDS)
    rows = []
    for label, folder in args.run:
        rows.extend(run(label, Path(folder), args.times, pre, props))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x",encoding="utf-8",newline="") as out:
        writer = csv.DictWriter(out,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} rows: {args.output}")


if __name__=="__main__":
    main()

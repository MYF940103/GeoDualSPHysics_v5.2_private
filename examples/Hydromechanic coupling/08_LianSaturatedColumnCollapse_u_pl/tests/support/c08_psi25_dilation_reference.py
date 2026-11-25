"""Compare the two explicit C08 pressures by common original material ID."""
import csv
import numpy as np

from c08_psi25_tpi_mobilization import CASE, PRE_IDS, RELEASE_IDS, cohorts, material, native, require, verify_source_material


def compare():
    groups = ("psi0", "psi2p5")
    pre = {}
    for group in groups:
        m, a = native(CASE/f"CaseLianCollapse_{group}_pre_GPU_out/data/Part_1000.bi4")
        verify_source_material(m, group)
        require(m["Step"]+1 == 2_000_000 and np.array_equal(a["Idp"], PRE_IDS), "Invalid 10 s PRE")
        pre[group] = (m, a)
    m0, a0 = pre["psi0"]
    m25, a25 = pre["psi2p5"]
    require(m0["TimeStep"] == m25["TimeStep"] and len(a0)==len(a25)==22 and set(a0)==set(a25)
            and all(a25[k].tobytes()==v.tobytes() for k,v in a0.items()), "Common PRE arrays or wall clock differ")
    base = material(a0, PRE_IDS)
    fixed = cohorts(base)
    result = []
    for part in (1,30,60,120):
        values = []
        saved = []
        for group in groups:
            where = CASE/f"CaseLianCollapse_{group}_GPU_out"
            m, a = native(where/"data"/f"Part_{part:04d}.bi4")
            require(m["Nout"]==0 and m["Cpart"]==part and m["Step"]+1==2000001+2000*part
                    and m["GravityPreloadActualTime"]==m0["TimeStep"] and m["GravityPreloadPhase"]==1
                    and m["GravityPreloadTargetIdCount"]==255 and not m["SoilDampingActive"] and not m["PoreShepardActive"]
                    and m.get("HydroMechModel",m.get("HydroMechDynamicSeepage"))==1
                    and m["DynamicArtificialStressCoef"]==np.float32(.3) and m["DynamicArtificialStressExp"]==np.float32(2.55),
                    "Explicit case or clock differs")
            soil = material(a, RELEASE_IDS)
            require(np.array_equal(soil["PorePress0"],base["PorePress0"])
                    and np.array_equal(soil["ExcessPorePress"],soil["PorePress"]-soil["PorePress0"]),
                    "Reference pressure changed")
            saved.append(m["TimeStep"])
            values.append(soil)
        require(saved[1]==saved[0], "Unequal actual clocks")
        different_psi = values[1]["PorePress"].astype(float)-values[0]["PorePress"]
        separation = np.linalg.norm(values[1]["Posd"]-values[0]["Posd"],axis=1)
        front0,front25 = [float(v["Posd"][:,0].max()) for v in values]
        same_fs = values[0]["FSType"]==values[1]["FSType"]
        cohorts_at_time = dict(fixed)
        cohorts_at_time["right_within_half_dp"] = fixed["right_x3_4"]&(separation<=.02)
        for region, mask in cohorts_at_time.items():
            count = int(mask.sum())
            row = dict(nominal_tau_s=part*.01,actual_tau_s=saved[0]-m0["TimeStep"],absolute_s=saved[0],
                       completed_step=m["Step"]+1, region=region, count=count, front0_m=front0,front25_m=front25,
                       separated_half_dp_count=int(np.count_nonzero((separation>.02)&mask)),
                       separated_H_count=int(np.count_nonzero((separation>.072)&mask)),
                       same_FS_count=int(np.count_nonzero(same_fs&mask)))
            data = dict(psi0_p_minus_p0_kPa=values[0]["ExcessPorePress"].astype(float)/1000,
                        psi25_p_minus_p0_kPa=values[1]["ExcessPorePress"].astype(float)/1000,
                        psi25_minus_psi0_p_kPa=different_psi/1000, separation_m=separation)
            for label, field in data.items():
                require(np.isfinite(field).all(), "Nonfinite native difference")
                quantiles = np.quantile(field[mask], (.05,.5,.95)) if count else ("","","")
                row.update({label+s:n for s,n in zip(("_p05","_p50","_p95"),quantiles)})
            result.append(row)
    return result


if __name__=="__main__":
    rows = compare()
    out = CASE/"tests/figures/c08_psi25_dilation_reference.csv"
    with out.open("x",newline="",encoding="utf8") as f:
        writer = csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(out)

"""Evaluate the hydraulic multiplier needed by the actual saved C02 and C04 TPI profiles."""
import argparse
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RESULT=Path(__file__).with_suffix(".csv")
JOBS=(
    ("02_TerzaghiConsolidation_q0_PR","upl_tpi_p3_B10us_full2tv_GPU_r1"),
    ("04_CryerProblem_PR","cryer_p3_gpu_drain4097_r1"),
)


def audit(case,tag,output=None):
    if output is None:
        output=ROOT/case/"tests/outputs"/tag
    summary=json.loads((output/"UplTpiP3DtR1.summary.json").read_text(encoding="utf-8-sig"))
    assert summary["completed"] and summary["R_h"]==1
    with (output/"UplTpiP3DtR1.csv").open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    nonempty=[r for r in rows if r["interval_empty"]=="0"]
    assert len(nonempty)+1==len(rows)==summary["saved_intervals_including_initial"]
    assert sum(int(r["interval_pre"]) for r in nonempty)==summary["updates"]
    largest=0.
    for r in nonempty:
        counts=[int(r["interval_"+s]) for s in ("pre","cor","endpoint1","endpoint2","endpoint3")]
        assert min(counts)>0 and min(counts)==max(counts)
        dt=float(r["dt_s"])
        hydraulic=float(r["min_Rh_hydro_s"])
        mechanical=min(float(r[k]) for k in ("min_force_CFL_s","min_skeleton_wave_AV_CFL_s","min_HG_limit_reference_s"))
        assert dt==summary["fixed_dt_s"] and hydraulic>0 and mechanical>=dt
        largest=max(largest,dt/hydraulic)
    assert largest==summary["fixed_dt_s"]/summary["min_Rh_hydro_s"]
    lines=(output/"Run.out").read_text(encoding="utf-8",errors="replace").splitlines()
    def parameter(label):
        return float(next(line.split(":",1)[1] for line in lines if line.strip().startswith(label+":")))
    return dict(case=case,run=tag,updates=summary["updates"],nonempty_intervals=len(nonempty),
        k_m_s=parameter("HydraulicConductivity"),pore_dt_safety=parameter("PoreDtSafety"),
        dt_us=1e6*dt,min_hydraulic_us=1e6*summary["min_Rh_hydro_s"],
        min_skeleton_wave_AV_us=1e6*summary["min_skeleton_wave_AV_CFL_s"],
        min_legacy_Kw_wave_us=1e6*summary["min_legacy_Kw_wave_CFL_reference_s"],
        configured_R=1,worst_hydraulic_ratio=largest,amplification_needed_above_unity=max(1.,largest))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-peak",type=Path,help="Returned Cryer P3 peak output containing Run.out and the five-phase ledger")
    args=parser.parse_args()
    if args.server_peak:
        stat=audit("04_CryerProblem_PR","Cryer_TPI_P3_nu030_peak",args.server_peak)
        if (stat["updates"],stat["nonempty_intervals"],stat["dt_us"])!=(36864,576,1e6*2.**-19):
            raise ValueError("Returned run does not match the peak-window stage")
        stats=[stat]
        target=RESULT.with_name("upl_tpi_r_selection_server_peak_r1.csv")
    else:
        stats=[audit(*job) for job in JOBS]
        target=RESULT
    with target.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(stats[0]));w.writeheader();w.writerows(stats)
    for row in stats: print(row)

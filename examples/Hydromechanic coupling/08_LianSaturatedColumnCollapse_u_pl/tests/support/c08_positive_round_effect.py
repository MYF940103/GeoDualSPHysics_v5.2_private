"""Measure pressure changes between actual TPI rounds on the same C08 trajectory."""
import argparse
import csv
import json

import numpy as np

from c08_positive_actual_rows import OUT, STEPS, read_capture
from c08_positive_round_observation import BASE, FOLDER, LOG
from c08_psi25_tpi_native import CASE, SOIL_IDS, TESTS, expected_steps, read_frame, require


def group_summary(meta, group, mask, ids, p1, p2, p3, cap1, final):
    result = dict(step=meta["step"], time_start_s=meta["time_start_s"],
                  time_end_s=meta["time_start_s"]+meta["dt_s"], group=group, count=int(mask.sum()))
    q1, q2, q3 = (p[mask].astype(float) for p in (p1,p2,p3))
    diff = (final[mask].astype(float)-cap1[mask])/1000
    raw = (q3-q1)/1000
    for name,values in (("raw_rounds_2_3",raw),("with_same_final_cap",diff)):
        result[name+"_median_kPa"] = float(np.median(values)) if len(values) else None
        result[name+"_p95_abs_kPa"] = float(np.quantile(abs(values),.95)) if len(values) else None
        result[name+"_max_abs_kPa"] = float(np.max(abs(values))) if len(values) else None
    result["median_abs_round2_minus_1_Pa"] = float(np.median(abs(q2-q1))) if len(q1) else None
    result["median_abs_round3_minus_2_Pa"] = float(np.median(abs(q3-q2))) if len(q1) else None
    result["more_negative_raw"] = int((raw<0).sum())
    result["unchanged_raw"] = int((raw==0).sum())
    result["greatest_capped_difference_id"] = int(ids[mask][np.argmax(abs(diff))]) if len(diff) else None
    return result


def examine(step):
    receipt = json.loads((LOG/(BASE+".native_review.json")).read_text(encoding="utf8"))
    require(receipt["passed"] and receipt["beta"]==.04 and receipt["frames"]==132,
            "Missing positive-only control")
    plan = expected_steps(STEPS[-1])
    part = plan.index(step)+1
    path = TESTS/"outputs"/BASE/"data"/f"Part_{part:04d}.bi4"
    stat = path.stat()
    require([str(path.relative_to(CASE)),stat.st_size,stat.st_mtime_ns] in receipt["files"],
            "Changed retained control frame")
    m,native,history,prev = read_frame(path)
    b = len(native["Idp"])-len(SOIL_IDS)
    require(m["Step"]+1==history["CompletedUpdates"]==step and np.array_equal(native["Idp"][b:],SOIL_IDS),
            "Native clock or particle registry mismatch")
    press = []
    for rnd in (1,2,3):
        header,fields = read_capture(FOLDER/f"C08TpiRow_{step}_r{rnd}.bin",step,rnd)
        require(header["time_start_s"]+header["dt_s"]==m["TimeStep"],"Round clock differs from native clock")
        order = np.argsort(fields["id"][b:])
        require(np.array_equal(fields["id"][b:][order],SOIL_IDS),"Pressure owners changed")
        if rnd==1:
            initial = fields["source"].copy()
            previous = fields["previous"].copy()
        else:
            require(np.array_equal(fields["source"],initial) and np.array_equal(fields["previous"],previous)
                    and np.array_equal(fields["p"][b:][order],press[-1]),"Round link changed")
        require(np.isfinite(fields["next"]).all(),"Nonfinite endpoint pressure")
        press.append(fields["next"].copy())
    require(np.array_equal(prev,initial),"History of saved baseline changed")
    fs = np.isin(native["FSType"][b:],[2,3])
    saved = native["PorePress"][b:]
    cap1 = np.where(fs,np.minimum(press[0],0),press[0])
    cap3 = np.where(fs,np.minimum(press[2],0),press[2])
    require(np.array_equal(cap3,saved),"Final pressure disagrees with retained baseline")
    masks = dict(all=np.ones(len(initial),bool),free_surface=fs,interior=(~fs),
                 interior_previous_negative=(~fs)&(initial<0),interior_previous_nonnegative=(~fs)&(initial>=0),
                 interior_below_minus20kPa=(~fs)&(saved < -20000),all_below_minus20kPa=(saved < -20000),
                 material_6918=(SOIL_IDS==6918))
    return [group_summary(header,g,mask,SOIL_IDS,*press,cap1,saved) for g,mask in masks.items()]


if __name__=="__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("step",type=int,choices=STEPS)
    args = ap.parse_args()
    rows = examine(args.step)
    OUT.mkdir(parents=True,exist_ok=True)
    path = OUT/f"round_effect_{args.step}.csv"
    with path.open("x",newline="",encoding="utf8") as f:
        w = csv.DictWriter(f,fieldnames=rows[0])
        w.writeheader()
        w.writerows(rows)
    for row in rows:
        if row["group"] in ("all","interior_below_minus20kPa","material_6918"):
            print(row["group"],row["count"],row["raw_rounds_2_3_median_kPa"],
                  row["raw_rounds_2_3_p95_abs_kPa"],row["raw_rounds_2_3_max_abs_kPa"])

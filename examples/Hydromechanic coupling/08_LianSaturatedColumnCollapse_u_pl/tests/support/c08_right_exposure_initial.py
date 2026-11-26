"""Compare native just-before/after right-wall release states in the retained three TPI runs."""
import csv
import json

import numpy as np
from c08_psi25_tpi_native import CASE, DT, OPEN, PRE, PRE_IDS, RELEASE_IDS, SOIL_IDS, TESTS, native, read_frame, require


RUNS = {
    "positive_beta0": "c08_psi25_tpi_paper_b0_r1",
    "positive_beta004": "c08_psi25_tpi_paper_b004_r1",
    "both_beta004": "c08_psi25_tpi_surface_zero_r1",
}
OUT = TESTS / "figures/c08_right_exposure"
KW = 1e9  # Pa; verify independently against all three physical run log headers


def publish(name, rows):
    with (OUT/name).open("x", newline="", encoding="utf8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def input_stat(path):
    s = path.stat()
    return [str(path.relative_to(CASE)), s.st_size, s.st_mtime_ns]


def run():
    initial_file = PRE.with_name("Part_0000.bi4")
    _, initial = native(initial_file)
    soil_xz = initial["Posd"][SOIL_IDS][:, [0,2]]
    right = np.isclose(soil_xz[:,0], soil_xz[:,0].max(), atol=1e-8, rtol=0)
    right_ids = SOIL_IDS[right]
    require(np.array_equal(right_ids, np.arange(7010,7060)), "Wrong right material column")
    sm, source = native(PRE)
    require(np.array_equal(source["Idp"], PRE_IDS), "Wrong preload IDs")
    stats, points, agreements = [], [], []
    first_equal = {}
    for label, tag in RUNS.items():
        path = TESTS/"outputs"/tag
        rec = json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text(encoding="utf8"))
        require(rec["passed"] and rec["tag"]==tag, "Missing native review")
        require(input_stat(PRE) in rec["files"] and input_stat(path/"Run.out") in rec["files"], "Changed source/log")
        with (path/"Run.out").open(encoding="utf8", errors="replace") as log:
            require(any("PoreWaterBulkModulus: 1e+09" in line for line in (log.readline() for _ in range(250))),
                    "Wrong reference Kw in run log")
        if label == "both_beta004":
            require(input_stat(initial_file) in rec["files"], "Original material positions changed")
        histories = [(0, sm, source, None)]
        for part in range(1,14):
            file = path/"data"/f"Part_{part:04}.bi4"
            require(input_stat(file) in rec["files"], "Native frame binding changed")
            meta,a,h,prev = read_frame(file)
            require(meta["TimeStep"]==h["SavedTime"] and h["Dt"]==DT, "Unexpected time/step")
            histories.append((part,meta,a,prev))
        last_step = None
        last_pressure = None
        at_open = None
        was_surface = None
        for part,m,a,prev in histories:
            step = m["Step"]+1
            time = m["TimeStep"]
            tau = time-rec["release_time_s"]
            require(np.array_equal(a["Idp"], RELEASE_IDS if step>OPEN else PRE_IDS), "Wrong stage IDs")
            sl = slice(-len(SOIL_IDS),None)
            soil_pressure = a["PorePress"][sl]
            p = soil_pressure[right].astype(float)
            f = a["FSType"][sl]
            fs = np.isin(f,[2,3])
            if last_step is not None and last_step==step-1:
                require(prev.tobytes()==last_pressure.tobytes(), "Adjacent previous pressure mismatch")
            if step==OPEN:
                at_open = p.copy()
                was_surface = fs[right].copy()
                require(was_surface.sum()==1 and right_ids[was_surface][0]==7059, "Unexpected old upper corner")
            if step==OPEN+1:
                require(fs[right].all(), "Expected newly exposed original right column")
            nv = (a["PoroPorosity"][sl]*a["PoroCurrentVolume"][sl])[right]
            values = dict(run=label, part=part, step=step, time_s=time, tau_s=tau)
            compared = first_equal.get(part)
            if label=="positive_beta004":
                first_equal[part]=(step,time,soil_pressure.copy(),f.copy())
            elif label=="both_beta004":
                bs,bt,bp,bf = compared
                require((step,time)==(bs,bt), "Compared unequal saved times")
                delta=soil_pressure.astype(float)-bp
                agreements.append(dict(**values,right_diff=int(np.sum(delta[right]!=0)),
                                       all_soil_diff=int(np.sum(delta!=0)),
                                       fs_class_diff=int(np.sum(f!=bf)), max_delta_Pa=np.max(abs(delta))))
            stats.append(dict(**values,n_positive_right=int((p>0).sum()), n_zero_right=int((p==0).sum()),
                              n_negative_right=int((p<0).sum()), n_fs_right=int(fs[right].sum()),
                              min_right_kPa=p.min()/1000,median_right_kPa=np.median(p)/1000,
                              mean_right_kPa=p.mean()/1000,max_right_kPa=p.max()/1000,
                              right_pore_volume_m2=nv.sum(), storage_proxy_m2=nv@p/KW,
                              delta_p_column_mean_kPa="" if at_open is None else (p-at_open).mean()/1000,
                              n_negative_fs_all=int(((soil_pressure<0)&fs).sum()),
                              n_negative_interior_all=int(((soil_pressure<0)&~fs).sum()),
                              all_soil_min_kPa=float(soil_pressure.min())/1000))
            for j,rid in enumerate(right_ids):
                si = int(rid - SOIL_IDS[0])
                points.append(dict(**values, id=int(rid), origin_z_m=soil_xz[si,1],
                                   z_m=a["Posd"][sl][si,2],fs=int(f[si]),p_kPa=p[j]/1000,
                                   prev_kPa="" if prev is None else float(prev[si])/1000,
                                   dstep_kPa="" if prev is None else (p[j]-float(prev[si]))/1000,
                                   p0_kPa=float(a["PorePress0"][sl][si])/1000,
                                   nV_m2=nv[j],storage_proxy_m2=nv[j]*p[j]/KW))
            last_step,last_pressure=step,soil_pressure
    OUT.mkdir(exist_ok=True)
    publish("initial_right_summary.csv",stats)
    publish("initial_right_points.csv",points)
    publish("initial_policies_compared.csv",agreements)


if __name__=="__main__":
    run()

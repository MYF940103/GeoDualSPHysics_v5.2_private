"""Read live optional P3 histories, native arrays and existing pressure-round traces offline."""
import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from cryer_p3_verify_r1 import EXPECTED_TYPES, TESTS, TOTAL, physical
from upl_tpi_partial_bi4_r1 import _Cursor, _name, _numeric, _values, read as old_read

OUTPUT = TESTS / "outputs"
MATERIAL = np.arange(8, TOTAL, dtype="<u4")
CHILD = "TpiPressureHistory"
FIELDS = {"Schema":8, "Scheme":1, "RunCode":1, "CompletedUpdates":8,
          "PreviousTime":12, "SavedTime":12, "Dt":12, "Valid":2}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def exact(a, b, label):
    first, second = np.asarray(a), np.asarray(b)
    require(first.shape == second.shape and first.dtype == second.dtype
            and first.tobytes() == second.tobytes(), label)


def double_bits(a, b, label):
    exact(np.array(a, np.float64), np.array(b, np.float64), label)


def read_item(cursor, depth, expected_history):
    d = cursor.block(cursor.uint())
    require(d.string() == "\nITEM\n", "JBD item marker")
    name = _name(d.string())
    hidden, hidden_values = d.boolean(), d.boolean()
    d.string()
    d.string()
    count, nested, value_size = d.uint(), d.uint(), d.uint()
    d.finish("item")
    shapes = ((0,1), (22,int(expected_history)), (2,0))
    require(depth < 3 and (count,nested) == shapes[depth], "Unexpected BI4 arrays or children: "+name)
    values, types = _values(cursor.block(value_size))
    arrays, array_types = {}, {}
    for _ in range(count):
        info = cursor.block(cursor.uint())
        require(info.string() == "\nARRAY", "JBD array marker")
        key = _name(info.string())
        require(key not in arrays, "Duplicate array "+key)
        info.boolean()
        type_id, size, byte_count = info.integer(), info.uint(), info.uint()
        info.finish("array header")
        array, spec = _numeric(cursor,type_id,size)
        require(byte_count == spec["data_bytes"], "JBD array length")
        arrays[key], array_types[key] = array, spec["type_name"]
    children = [read_item(cursor,depth+1,expected_history) for _ in range(nested)]
    return dict(name=name, hidden=hidden, hidden_values=hidden_values, values=values, types=types,
                arrays=arrays, array_types=array_types, children=children)


def read_frame(path, part, completed, dt, history, *, sorted_history=True):
    before = path.stat()
    raw = path.read_bytes()
    require(path.stat().st_mtime_ns == before.st_mtime_ns and len(raw)==before.st_size, "PART changed during read")
    require(raw[:9] == b"#FileJBD " and raw[9:58].rstrip(b" ") == b"JPartDataBi4"
            and raw[58:64] == b"\n\x00\x00\x00\x00\x00", "Unexpected file identity/order")
    cursor = _Cursor(raw,64)
    root = read_item(cursor,0,history)
    cursor.finish("PART file")
    p = root["children"][0]
    require(root["name"] == "JPartDataBi4" and p["name"]==f"PART_{part:04}", "Wrong native location")
    rv, pv = root["values"], p["values"]
    for key, value in {"Npiece":1, "CaseNfixed":8, "CaseNfluid":len(MATERIAL), "CaseNp":TOTAL,
                       "NpDynamic":0, "ReuseIds":0}.items():
        require(rv[key]==value, "Unexpected original owner or piece contract "+key)
    require(pv["Npok"]==TOTAL and pv["Nout"]==0 and pv["Cpart"]==part and pv["Step"]==max(0,completed-1),
            "Wrong native frame or zero-based step")
    double_bits(pv["SymplecticDtPre"],dt,"Step length")
    double_bits(pv["TimeStep"],completed*dt,"Dyadic native clock")
    require(p["array_types"]==EXPECTED_TYPES, "Original 22 types")
    a = p["arrays"]
    require(all(len(x)==TOTAL and np.isfinite(x).all() for x in a.values()), "Native extent or nonfinite value")
    order = np.argsort(a["Idp"])
    exact(a["Idp"][order],np.arange(TOTAL,dtype="<u4"),"Original native IDs")
    by_id = {k:x[order] for k,x in a.items()}
    saved = None
    if history:
        h = p["children"][0]
        require(h["name"]==CHILD and h["types"]==FIELDS and h["array_types"]=={"Idp":"DatUint","PorePressPrev":"DatFloat"},
                "Pressure-history typed schema")
        hv = h["values"]
        require(hv["Schema"]==1 and hv["Scheme"]=="P3_B_alpha_half_beta_zero" and hv["Valid"]==1
                and hv["RunCode"]==rv["RunCode"] and hv["CompletedUpdates"]==completed, "History identity or ownership")
        for key, ref in (("Dt",dt),("PreviousTime",pv["TimeStep"]-dt),("SavedTime",pv["TimeStep"])):
            double_bits(hv[key],ref,"Typed history time "+key)
        owners = h["arrays"]["Idp"]
        perm = np.argsort(owners)
        exact(owners[perm],MATERIAL,"History particle owners")
        if sorted_history:
            exact(owners,MATERIAL,"Writer must use ascending material IDs")
        saved = h["arrays"]["PorePressPrev"][perm]
        require(len(saved)==len(MATERIAL) and np.isfinite(saved).all(),"Invalid pressure history")
        # Exercise arbitrary receiving slots using owner IDs (never the payload index).
        ids = np.roll(a["Idp"][::-1],137)
        slots = ids[ids>=8]
        recovered = saved[np.searchsorted(MATERIAL,slots)]
        exact(recovered[np.argsort(slots)],saved,"Permuted owner gather")
    return root, p, by_id, saved


def rows(folder, backend):
    cpu = backend=="cpu"
    files = [folder/"UplTpiP3CpuR1.csv"] if cpu else [folder/f"UplTpiP3GpuR1.round{r}.csv" for r in range(1,4)]
    r_key = "pressure_round" if cpu else "round"
    final = "actual_after_BC_float_Pa" if cpu else "final_field_float_Pa"
    core = ["part",r_key,"native_id","source_step_zero_based","completed_step","source_time_s","actual_save_time_s",
            "dt_s","pn_Pa","previous_Pa","prediction_double_Pa","mechanical_half_actual_float_Pa" if cpu
            else "half_actual_float_Pa"]
    half = core[-1]
    tables = []
    for i, file in enumerate(files):
        keep = core+[final] if cpu or i==2 else core
        # All-zero pressure columns can be inferred as int64. Parse their declared
        # floating types, retaining signed zero and exact round-trip values.
        floating = {k:np.float64 for k in keep if k.endswith("_Pa") or k.endswith("_s")}
        table = pd.read_csv(file,usecols=keep,dtype=floating,float_precision="round_trip")
        table = table[table.part>0]
        if not cpu:
            require((table[r_key]==i+1).all(),"Wrong GPU trace round")
        tables.append(table)
    data = pd.concat(tables,ignore_index=True)
    return {(int(p),int(r)):g.sort_values("native_id") for (p,r),g in data.groupby(["part",r_key])},final,half


def f32(series, label):
    numbers = series.to_numpy(dtype=np.float64)
    flt = numbers.astype(np.float32)
    exact(flt.astype(np.float64),numbers,label+" must be exact binary32")
    return flt


def predict(pn, previous):
    now = pn.astype(np.float64)
    return now + .5 * (now - previous.astype(np.float64))


def compare_control(folder, part, actual_root, actual_part):
    control = old_read(folder / "data" / f"Part_{part:04}.bi4")
    for key in EXPECTED_TYPES:
        exact(actual_part["arrays"][key],control["arrays"][key],"Native slot-order field "+key)
    require(control["root"]["types"]==actual_root["types"] and control["part"]["types"]==actual_part["types"],
            "Ordinary native metadata schema changed")
    # File identity strings, measured wall time and memory use may differ across executables.
    cost = {"RunCode","Date","AppName","RunTime","timesim","cpualloc","npalloc","npused"}
    differences = {}
    for section, reference, actual in (("root",control["root"],actual_root),("part",control["part"],actual_part)):
        for key in reference["types"]:
            v,w = reference["values"][key],actual["values"][key]
            if isinstance(v,str):
                same = v==w
            else:
                same = np.asarray(v).tobytes()==np.asarray(w).tobytes()
            if not same:
                require(key in cost, "Native metadata differs: "+key)
                differences[section+"."+key] = [str(v),str(w)]
    double_bits(actual_part["values"]["dterror"],control["part"]["values"]["dterror"],"Original signed interval")
    return differences


def audit(backend, profile):
    base = OUTPUT / f"cryer_livehist_{backend}_r1_{profile}"
    reference = OUTPUT / f"cryer_drain_schema_{backend}_r1_{'model1' if profile=='model1' else 'model2'}"
    dense = profile=="dense4"
    enabled = profile!="model1"
    steps = [0,1,2,3,4] if dense else [0,2]
    call = json.loads((TESTS/"logs"/(base.name+".call.json")).read_text(encoding="utf-8-sig"))
    require(call["popen_exit"]==call["win32_exit"]==0,"No successful solver completion")
    with (base/"Run.csv").open(encoding="utf-8-sig",newline="") as f:
        run, = csv.DictReader(f, delimiter=";")
    require((int(run["Steps"]),int(run["PartFiles"]),int(run["PartsOut"]),int(run["Np"]))
            == (steps[-1],len(steps),0,TOTAL), "Native/solver extent disagreement")
    dt = float(old_read(reference/"data/Part_0001.bi4")["part"]["values"]["SymplecticDtPre"])
    require(dt in (2.**-20,2.**-19), "Unexpected dyadic profile")
    require(sorted(p.name for p in (base/"data").glob("Part_*.bi4"))==[f"Part_{j:04}.bi4" for j in range(len(steps))],
            f"Incomplete native files for {backend}/{profile}")
    reports = []
    if enabled:
        table, final_key, half_key = rows(base,backend)
        require(set(table)=={(j,r) for j in range(1,len(steps)) for r in range(1,4)},"Unexpected round/frame coverage")
    last_p = last_prev = last_prediction = None
    for part, step in enumerate(steps):
        root, frame, native, previous = read_frame(base/"data"/f"Part_{part:04}.bi4",part,step,dt,enabled and part>0)
        if part==0:
            initial = native["Posd"]
        physical(native,initial,False)
        current = native["PorePress"][8:]
        result = dict(part=part, step=step, history_present=previous is not None,
                      signed_dterror_s=float(frame["values"]["dterror"]), id_count=len(current))
        err = result["signed_dterror_s"]
        require(np.isfinite(err) and err<=1e-14 and (part==0 or err!=-sys.float_info.max),"Signed dt guard")
        if not dense:
            result["runtime_metadata_differences"]=compare_control(reference,part,root,frame)
            result["raw_slot_arrays_equal"]=22
        if previous is not None:
            if dense:
                exact(previous,last_p,"Previous committed PART differs by ID")
                result["previous_part_bit_checks"]=len(previous)
                result["next_trace_predictor_per_round_bit_checks"]=len(previous)
                result["cold_substitution_changes_actual_input_ids"]=int(np.count_nonzero(last_prediction!=last_p))
            for r in range(1,4):
                g = table[part,r]
                exact(g.native_id.to_numpy().astype("<u4"),MATERIAL,"Trace ID set")
                for k,v in (("completed_step",step),("source_step_zero_based",step-1),("source_time_s",(step-1)*dt),
                            ("actual_save_time_s",step*dt),("dt_s",dt)):
                    require((g[k]==v).all(),"Trace time/step differs: "+k)
                qn, old = f32(g.pn_Pa,"pn"),f32(g.previous_Pa,"previous")
                exact(qn,previous,"Serialized history vs genuine update pn")
                pred = predict(qn,old)
                exact(pred,g.prediction_double_Pa.to_numpy(),"Linear historical pressure predictor")
                exact(pred.astype("f4"),f32(g[half_key],"half"),"Intermediate mechanical pressure")
                if dense:
                    exact(qn,last_p,"Source pressure vs preceding dense PART")
                    exact(old,last_p if last_prev is None else last_prev,"Older committed pressure or initial cold")
                    exact(pred,last_prediction,"Live next-step predictor and trace")
                if r==3:
                    exact(f32(g[final_key],"committed"),current,"Committed endpoint vs native")
            result["all_round_source_pressure_and_prediction_checks"]=3*len(MATERIAL)
            next_pred = predict(current,previous)
            result["cold_would_change_next_predictor_ids"]=int(np.count_nonzero(next_pred!=current))
        else:
            next_pred = predict(current,current)
        last_prev,last_p,last_prediction = previous,current,next_pred
        reports.append(result)
    if dense:
        require(any(r.get("cold_substitution_changes_actual_input_ids",0)>0 for r in reports),
                "Dense run did not distinguish real history from cold substitution")
    return dict(profile=profile,dt_s=dt,original_run=str(reference),observed_run=str(base),parts=reports)


def same_file(a, b):
    require(a.stat().st_size==b.stat().st_size and a.stat().st_size>0,"Different or empty sidecar "+a.name)
    with a.open("rb") as left,b.open("rb") as right:
        while True:
            chunk=left.read(1024*1024)
            require(chunk==right.read(1024*1024),"Sidecar content differs: "+a.name)
            if not chunk:
                return a.stat().st_size


def audit_restore(backend):
    reference=OUTPUT/f"cryer_livehist_{backend}_r1_dense4"
    candidate=OUTPUT/f"cryer_hist_restore_{backend}_r1_dense4"
    passed=json.loads((TESTS/"logs"/f"cryer_livehist_{backend}_r1.history_review.json").read_text())
    require(passed["passed"] and passed["profiles"]["dense4"]["observed_run"]==str(reference),
            "Original writer history review required")
    dt=passed["profiles"]["dense4"]["dt_s"]
    call=json.loads((TESTS/"logs"/(candidate.name+".call.json")).read_text(encoding="utf-8-sig"))
    require(call["win32_exit"]==call["popen_exit"]==0,"Restore solver did not complete")
    with (candidate/"Run.csv").open(encoding="utf-8-sig",newline="") as f:
        run,=csv.DictReader(f,delimiter=";")
    require((int(run["Steps"]),int(run["PartFiles"]),int(run["PartsOut"]),int(run["Np"]))
            == (4,5,0,TOTAL), "Restore work and saved frame counts")
    key="Restored committed pressure history by native ID at PART 2."
    for folder,count in ((reference,0),(candidate,1)):
        require((folder/"Run.out").read_text(errors="replace").count(key)==count,"Incorrect restore hook count")
        require(sorted(p.name for p in (folder/"data").glob("Part_*.bi4"))
                ==[f"Part_{j:04}.bi4" for j in range(5)],"Unexpected dense native saves")
    frames=[]
    for j in range(5):
        name=f"Part_{j:04}.bi4"
        _,p,a,h=read_frame(candidate/"data"/name,j,j,dt,j>0)
        _,old,_,old_h=read_frame(reference/"data"/name,j,j,dt,j>0)
        for field in EXPECTED_TYPES:
            exact(old["arrays"][field],p["arrays"][field],"Restored native field or slot order: "+field)
        double_bits(p["values"]["dterror"],old["values"]["dterror"],"Restored signed dt")
        double_bits(p["values"]["TimeStep"],old["values"]["TimeStep"],"Restored native clock")
        if j:
            exact(h,old_h,"Restored history payload")
            exact(h,previous,"Restored history vs previous dense PART")
        previous=a["PorePress"][8:]
        changes=int(np.count_nonzero(predict(previous,h)!=previous)) if j else 0
        if j==2:
            require(changes>0,"Restore at step 2 did not distinguish cold from recovered pressure")
        frames.append(dict(part=j,signed_dterror_s=float(p["values"]["dterror"]),raw_slot_arrays_equal=22,
                           history_ids_and_pressures_equal=len(h) if j else 0,
                           next_prediction_ids_different_from_cold=changes))
    files={"UplTpiP3DtR1.csv"}
    if backend=="cpu":
        files.add("UplTpiP3CpuR1.csv")
    else:
        files.update(f"UplTpiP3GpuR1.{s}.csv" for s in ("round1","round2","round3","body"))
    for folder in (candidate,reference):
        require({p.name for p in folder.glob("UplTpi*.csv")}==files,"Incomplete pressure/dt trace set")
    exact_file_bytes={name:same_file(candidate/name,reference/name) for name in sorted(files)}
    with (candidate/"UplTpiP3DtR1.csv").open(newline="") as f:
        ticks=list(csv.DictReader(f))
    require(len(ticks)==5,"Five dt records required")
    for j,tick in enumerate(ticks):
        require(int(tick["part"])==j and int(tick["completed_updates"])==j,"Five-phase step")
        for stage in ("pre","cor","endpoint1","endpoint2","endpoint3"):
            require(int(tick["total_"+stage])==j and int(tick["interval_"+stage])==(j>0),"Phase total "+stage)
        double_bits(float(tick["actual_save_time_s"]),j*dt,"Phase time")
        if j:
            double_bits(float(tick["max_dt_minus_bound_s"]),frames[j]["signed_dterror_s"],"Phase signed dt")
    return dict(passed=True,backend=backend,writer=str(reference),restored_run=str(candidate),restore_calls=1,
                restored_at_completed_step=2,updates_after_restore=2,parts=frames,
                original_three_round_and_five_phase_files_equal_bytes=exact_file_bytes,
                pressure_buffer_reloaded_same_live_solver=True,independent_process_restart_tested=False,solver_runs=0)


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("backend",choices=("cpu","gpu"))
    ap.add_argument("--restore",action="store_true",help="Review the separate in-process dense4 restoration")
    args=ap.parse_args()
    if args.restore:
        result=audit_restore(args.backend)
        name=f"cryer_hist_restore_{args.backend}_r1.history_review.json"
    else:
        profiles={p:audit(args.backend,p) for p in ("model1","model2","dense4")}
        result=dict(passed=True,backend=args.backend,profiles=profiles,solver_runs=0,full_restart_tested=False)
        name=f"cryer_livehist_{args.backend}_r1.history_review.json"
    receipt=TESTS/"logs"/name
    with receipt.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,allow_nan=False)
    print(receipt)

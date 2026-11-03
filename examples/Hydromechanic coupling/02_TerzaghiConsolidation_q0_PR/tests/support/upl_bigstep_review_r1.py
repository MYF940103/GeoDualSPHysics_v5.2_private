"""Two explicit offline phases: decode once, then describe the bounded larger-step result."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
NAME, TAG, SHORT = "upl_bigstep_review_r1", "upl_bigstep_c625_r1", "upl_spr_av_new_requested_ON_r1"
FINE = "upl_spr_av_2tv_CPU1_r1"
PREFIX_CSV = T / "logs/upl_bigstep_fine_prefix_r1.clock.csv"
DIRS = {"candidate": T / "outputs" / (TAG + "_native_r1"), "fine": T / "outputs/upl_bigstep_fine_prefix_r1_native"}
LEAVES = set("original15.bin physical.bin clock.bin common_j_theta.bin soil_n.bin native_ids.csv fixed_ids.csv history.csv ledger.csv fixed_samples.csv last_poro.csv columns.csv completion.json".split())
PINS = {
    "support/upl_bigstep_r1_run.py": (17705, "2afaa01622314a0f04e4be81dff26b32bc3d5b0becdfd47c4d0a061b925b125c"),
    "notes/upl_bigstep_r1_run.json": (4575, "3c721c5762048fcc4add85044430dc78d2cdfb82108b51d5051329512f75e44f"),
    "logs/upl_bigstep_native_r1.build.json": (76173, "7b1fa0a394503685e9dc27f4b3c25b3410d3b8ec1c36c5b04e5b9814eb46c942"),
    "logs/upl_bigstep_old_full_stop_r1.completion.json": (1897, "c2d2fedaf7d4d680e5543cd5f4fde0575b0fedb24fb00bc173c4852de922ee18"),
    "logs/upl_spr_av_new_requested_ON_r1.native_r2.json": (405811, "3701178a2fd96e6b91ef00f3ed169d152ed03dec0badffd50ef633fe88f99f05"),
}


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def definitions():
    sys.dont_write_bytecode = True
    path = T / "support/upl_bigstep_r1_run.py"
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    need((path.stat().st_size, digest) == PINS["support/upl_bigstep_r1_run.py"], "Frozen candidate owner changed")
    spec = importlib.util.spec_from_file_location("bigstep_offline_owner_definitions", path)
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    u, p = b.definitions()  # File/plan definitions only; never run(), main() or the prelaunch live fine-control guard.
    for name, (size, sha) in PINS.items():
        u.bind(dict(path=str(T / name), bytes=size, sha256=sha))
    for path in (__file__, T / "notes" / (NAME + ".json"), sys.executable):
        u.adopt(path)
    return u, p, b


def pinned(u, name):
    size, sha = PINS[name]
    return dict(path=str(u.bind(dict(path=str(T / name), bytes=size, sha256=sha))), bytes=size, sha256=sha)


def rows(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, values):
    with Path(path).open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]))
        writer.writeheader()
        writer.writerows(values)


def raw(u, run, count):
    directory = Path(run["job"]["output_directory"]).resolve()
    paths = [Path(e["path"]).resolve() for e in run["files"]]
    need(len(paths) == len(set(paths)) and all(v.is_relative_to(directory) for v in paths) and
         {v for v in directory.rglob("*") if v.is_file()} == set(paths) and
         sorted(v.name for v in paths if v.parent.name == "data" and v.name.startswith("Part_") and v.suffix == ".bi4") ==
         ["Part_%04d.bi4" % i for i in range(count)], "Sealed raw inventory/precise PART sequence differs")
    for e in run["files"]:
        u.bind(e)


def sources(u, p, b):
    ctx = b.context(u, p)  # Pure completed input/clock closure; never the live prelaunch guard.
    e = u.adopt(T / "logs" / (TAG + ".run.json"))
    run = u.read(e)
    need(run.get("stage") == TAG + ".run" and run.get("passed") is True and run.get("failure") is None and
         run.get("bindings_unchanged") is True and run.get("independent_final_rehash_performed") is True and
         run.get("steps") == 320000 and run.get("native_frames") == 1292 and run["job"] == ctx["job"] and
         run["program"] == ctx["program"] and run["source_input_manifest"] == ctx["manifest"] and
         run.get("physical_acceptance") is False and run.get("native_decoder_invoked") is False,
         "Genuine passed candidate Run required before any decode")
    call, start = u.owned(run["call"], TAG + ".run_call"), u.read(run["start_record"])
    need(call["program"] == run["program"] and call["arguments"] == ctx["job"]["arguments"] and
         call["start_record"] == run["start_record"] and call["solver"] == run["solver"] == start["solver"] and
         call.get("actual_solver_call") is True and call.get("public_project_main") is True and call.get("shell") is False and
         call.get("fixture_or_Run_override") is False and start.get("stage") == TAG + ".start" and
         start.get("actual_solver_identity_verified") is True and start["owner_script"] == u.adopt(T / "support/upl_bigstep_r1_run.py") and
         start["job"] == run["job"] and start["program"] == run["program"], "Original candidate solver/start ownership differs")
    need(b.check_output()["HG"] == run["HG"], "Original candidate HG/tau/spin guards changed")
    for v in run["inputs"]:
        u.bind(v)
    raw(u, run, 1292)
    stop_e = pinned(u, "logs/upl_bigstep_old_full_stop_r1.completion.json")
    stop = u.read(stop_e)
    fine_e, fine = stop["original_run"], u.read(stop["original_run"])
    stopped = u.read(stop["original_call"])
    need(stop.get("stage") == "upl_bigstep_old_full_stop_r1.completion" and stop.get("passed") is True and
         stop.get("original_native_exit_code") == 15 and stop.get("old_owner_solver_watcher_absent") is True and
         stop.get("retained_raw_files") == 469 and stop.get("retained_PART_frames") == 461 and
         stop.get("retained_output_hashes_independently_reverified") is True and stop.get("physical_acceptance") is False and
         fine.get("stage") == FINE + ".run" and fine.get("passed") is False and fine["call"] == stop["original_call"] and
         fine.get("bindings_unchanged") is True and fine.get("independent_final_rehash_performed") is True and
         stopped.get("stage") == FINE + ".run_call" and stopped.get("direct_native_call") is True and
         stopped.get("typed_returncode_captured_immediately") is True and stopped.get("owned_call_exited") is True and
         type(stopped.get("exit_code")) is int and stopped["exit_code"] == 15 and stopped.get("invocation_failure") is None and
         stopped["program"] == fine["program"] == run["program"] and stopped["arguments"] == fine["job"]["arguments"] and
         stopped["start_record"] == fine["start_record"], "Intentional stopped fine reference is not a completed full run")
    for v in (stop["stop_intent"], stop["stop_audit"], stopped["log"], fine["start_record"], fine["source_build"]):
        u.bind(v)
    fm = u.read(fine["source_input_manifest"])
    need(fm.get("passed") is True and fm["jobs"] == [fine["job"]] and len(fine["files"]) == 469, "Original fine full plan differs")
    table = [{k: (int(r[k]) if k == "post_open_by_completed_step" else r[k]) for k in p.HEADER[:-1]} | {"forced_final": 0}
             for r in fm["jobs"][0]["saved_clock_table"][:461]]
    need(table[-1]["completed_steps"] == 299674 and table[-1]["time_s"] == .5715827941894531 and
         all(r["time_s"] == r["completed_steps"] * 2. ** -19 and r["dt_s"] == 2. ** -19 for r in table), "Actual461 dyadic prefix plan differs")
    raw(u, fine, 461)
    return ctx, dict(candidate=dict(run=e, record=run, table=ctx["job"]["saved_clock_table"], window="candidate2s", csv=ctx["clock_CSV"]),
        fine=dict(run=fine_e, record=fine, table=table, window="reference_prefix", stop_completion=stop_e))


def helper(u, source_build):
    e = pinned(u, "logs/upl_bigstep_native_r1.build.json")
    h = u.read(e)
    need(h.get("stage") == "upl_bigstep_native_r1.build" and h.get("passed") is True and h["source_build"] == source_build and
         h.get("private_offline_reader") is True and h.get("solver_started") is False and h.get("reader_executed") is False and
         h.get("physical_acceptance") is False and h.get("independent_final_rehash_performed") is True and
         (h["program"]["bytes"], h["program"]["sha256"]) ==
         (541184, "ba95f78036e3ce10724b1c1457d9b136ec3ef709573d02add5d0ad298255a157"), "Actual fresh reader build required")
    for v in [*h["inputs"], h["source"], h["note"], h["neutral_include"], h["program"], h["object"], h["compiler_dependencies"],
              *h["actual_archived_headers"], *h["runtime"]]:
        u.bind(v)
    cc, lc = u.owned(h["compile_call"], "upl_bigstep_native_r1.Compile"), u.owned(h["link_call"], "upl_bigstep_native_r1.Link")
    build = u.read(source_build)
    expected = [v for v in build["objects"] if Path(v["path"]).name.casefold() != "main.obj"] + [h["object"]]
    actual = [str(Path(v.strip('"')).resolve()).casefold() for v in lc["arguments"] if Path(v.strip('"')).suffix.lower() == ".obj"]
    need(len(expected) == len(actual) == len(set(actual)) == 86 and set(actual) == {str(Path(v["path"]).resolve()).casefold() for v in expected} and
         [Path(v.strip('"')).name for v in cc["arguments"] if Path(v.strip('"')).suffix.lower() == ".cpp"] == ["upl_bigstep_native_r1.cpp"] and
         len(h["runtime"]) == 4 and len(h["actual_archived_headers"]) == 8, "Actual85+reader object/archive header closure differs")
    return e, h


def exports(u, directory, files, completion, table, window, fresh_reader=True):
    import numpy as np
    u.adopt(np.__file__)
    leaves = {Path(v["path"]).name: v for v in files}
    need(set(leaves) == LEAVES and len(files) == 13 and all(Path(v["path"]).resolve().parent == directory.resolve() for v in files), "Exact13 export closure required")
    for v in files:
        u.bind(v)
    c, count = u.read(completion), len(table)
    need(c.get("passed") is True and c.get("physical_acceptance") is False and c["samples"] == count and
         c["native_total_arrays"] == 22 and c["total_native_count"] == 1040 and c["physical_columns"] == 26 and
         c["physical_schema"] == "case02_common26_col21_ExcessPorePress_NOT_wave26" and c["dt_s"] == table[0]["dt_s"] and
         c["actual_end_s"] == table[-1]["time_s"] and c["planned_completed_steps"] == table[-1]["completed_steps"] and
         c["soil_ledger_checks"] == count*1000 and c["fixed_public_zero_marker_checks"] == count*40 and
         c["all_native_J_theta_rows"] == count*1040 and c["noninitial_signed_dterror_intervals"] == count-1 and
         c["max_noninitial_signed_dterror_s"] <= 1e-14 and c["max_ledger_relative_error"] <= 5e-13 and
         c["post_open_frames"] == sum(r["post_open_by_completed_step"] for r in table) and
         c["post_open_drained_particle_checks"] == 10*c["post_open_frames"] and c["max_activeDrainCount"] == 10,
         "Typed native count/clock/ledger/signed-error/drain summaries differ")
    flags = "native_PosDiv_present native_PosDiv_is_float native_V_rho_k_present PART_typed_public_metadata_verified public_master_on declared_saved_completed_steps_exact actual_time_step_locked_dt_exact initial_dterror_excluded_from_noninitial_summary fixed_J_theta_original15_not_zeroed_or_masked no_exclusions initial_rest_and_decimal_lattice_verified double_stress_and_float_display_verified all_exported_physical_fields_finite common26_column21_is_actual_ExcessPorePress post_open_native_receiver_coverage_verified".split()
    need(all(c.get(k) is True for k in flags) and c.get("PosDiv_fabricated_or_derived") is False, "Original typed native safety/schema flags required")
    if fresh_reader:
        need(c.get("stage") == "upl_bigstep_native_r1" and c.get("window") == window and c.get("declared_window_complete") is True and
             c.get("scalar_clock_plan_verified") is True and c.get("scalar_time_not_replaced_by_steps_times_dt") is True,
             "Honest new scalar-clock/reference-prefix schema required")
    else:
        need(c.get("stage") == "upl_hg_column_short_native_r1" and c.get("window") == "dyadic_short458", "Genuine458 short schema differs")
    specs = {"original15.bin": ((1040,15,count), 166408), "physical.bin": ((1000,26,count),208008),
             "common_j_theta.bin": ((1040,2,count),16648), "soil_n.bin": ((1000,1,count),8008), "clock.bin": ((count,28),28)}
    for name, (head, stride) in specs.items():
        with u.bind(leaves[name]).open("rb") as stream:
            need(struct.unpack("<"+"I"*len(head), stream.read(4*len(head))) == head and leaves[name]["bytes"] == 4*len(head)+count*stride, "Binary header/length differs: "+name)
    physical = np.memmap(leaves["physical.bin"]["path"], mode="r", offset=12, shape=(count,), dtype=[("t","<f8"),("q","<f8",(1000,26))])
    clock = np.memmap(leaves["clock.bin"]["path"], mode="r", offset=8, shape=(count,), dtype=[("t","<f8"),("step","<u4"),("dt","<f8"),("error","<f8")])
    porosity = np.memmap(leaves["soil_n.bin"]["path"], mode="r", offset=12, shape=(count,), dtype=[("t","<f8"),("n","<f8",(1000,))])
    jt = np.memmap(leaves["common_j_theta.bin"]["path"], mode="r", offset=12, shape=(count,), dtype=[("t","<f8"),("q","<f8",(1040,2))])
    ts = np.array([v["time_s"] for v in table])
    need(np.array_equal(clock["t"].view("u8"),ts.view("u8")) and all(np.array_equal(v["t"].view("u8"),ts.view("u8")) for v in (physical,porosity,jt)) and
         np.array_equal(clock["step"],[v["saved_step"] for v in table]) and np.all(clock["dt"] == table[0]["dt_s"]) and
         np.isfinite(clock["error"]).all() and np.all(clock["error"][1:] != -sys.float_info.max) and np.all(clock["error"][1:] <= 1e-14), "Original scalar clocks/signed intervals differ")
    history, ids = rows(u.bind(leaves["history.csv"])), rows(u.bind(leaves["native_ids.csv"]))
    need(len(history)==count and len(ids)==1000 and [int(v["id"]) for v in ids]==list(range(40,1040)) and
         all(float(h["time_s"])==r["time_s"] and int(h["completed_step"])==r["completed_steps"] and
             int(h["activeDrainCount"]) == 10*int(r["post_open_by_completed_step"]) for h,r in zip(history,table)), "Actual per-frame drainage/history/ID rows differ")
    for name, nrows in (("ledger.csv",count*1000),("fixed_samples.csv",count*40),("fixed_ids.csv",40),("last_poro.csv",1000),("columns.csv",26)):
        with u.bind(leaves[name]).open("rb") as stream:
            need(sum(1 for _ in stream)-1 == nrows, "Export row coverage differs: "+name)
    x0 = np.array([[float(v[k]) for k in ("x0","y0","z0")] for v in ids])
    layer, column = np.rint(x0[:,2]/.01-.5).astype(int), np.rint(x0[:,0]/.01-.5).astype(int)
    need(np.array_equal(np.sort(10*layer+column),np.arange(1000)) and np.all(x0[:,1]==0), "Original100x10 material lattice differs")
    for i in range(count):
        q,n,j = physical["q"][i],porosity["n"][i],jt["q"][i]
        need(np.isfinite(q).all() and np.isfinite(j).all() and np.isfinite(n).all() and np.array_equal(q[:,8:10],j[40:]) and
             np.all(q[:,8] > 1-float(np.float32(.3))) and np.all(np.abs(n-(1-(1-float(np.float32(.3)))/q[:,8])) <= 5e-13*np.abs(n)), "Exported unmasked J/theta/porosity ledger differs")
    return dict(p=physical,clock=clock,n=porosity,x0=x0,layer=layer,column=column,history=history,leaves=leaves,table=table,completion=c)


def native(u, p, b, result):
    ctx, source = sources(u,p,b)
    helper_e,h = helper(u,ctx["source_build"])
    u.fresh(PREFIX_CSV,*DIRS.values(),*(T/"logs"/("upl_bigstep_r1_"+k+s) for k in source for s in (".reader.call.json",".reader.log")))
    import psutil
    u.adopt(psutil.__file__)
    need(not [v.info for v in psutil.process_iter(["name"]) if (v.info["name"] or "").lower().startswith("dualsphysics") or
              (v.info["name"] or "").lower()==Path(h["program"]["path"]).name.lower()], "Solver or this reader remains active")
    write_csv(PREFIX_CSV,source["fine"]["table"])
    source["fine"]["csv"] = u.adopt(PREFIX_CSV)
    result.update(reader_helper=helper_e,datasets={},reader_attempts=0)
    u.final_bindings()
    for key,v in source.items():
        args=["--read","CPU",str(Path(v["record"]["job"]["output_directory"])/"data"),v["csv"]["path"],v["window"],str(DIRS[key])]
        call_path,log=(T/"logs"/("upl_bigstep_r1_"+key+s) for s in (".reader.call.json",".reader.log"))
        code=failure=None
        started,wall=u.utc(),time.perf_counter()
        result["reader_attempts"]+=1
        try:
            with log.open("xb") as stream:
                completed=subprocess.run([h["program"]["path"],*args],cwd=T.parent,stdout=stream,stderr=subprocess.STDOUT,shell=False,creationflags=subprocess.CREATE_NO_WINDOW)
                code=completed.returncode
        except Exception as exc:
            failure=str(exc)
        u.seal(call_path,dict(stage=NAME+"."+key+".reader_call",program=h["program"],target_program=h["program"],arguments=args,target_arguments=args,
            working_directory=str(T.parent),started_utc=started,ended_utc=u.utc(),direct_native_call=True,shell=False,owned_call_exited=type(code)is int,
            typed_returncode_captured_immediately=type(code)is int,exit_code=code,invocation_failure=failure,log=u.entry(log) if log.exists() else None,
            invocation_wall_seconds=time.perf_counter()-wall,physical_acceptance=False))
        item=dict(source_run=v["run"],source_solver_call=v["record"]["call"],window=v["window"],clock_CSV=v["csv"],reader_call=u.adopt(call_path),directory=str(DIRS[key]))
        result["datasets"][key]=item
        u.owned(item["reader_call"],NAME+"."+key+".reader_call")  # Seal actual typed exit before any export postcheck.
        item.update(files=[u.adopt(path) for path in sorted(DIRS[key].iterdir()) if path.is_file()],completion=u.adopt(DIRS[key]/"completion.json"))
        exports(u,DIRS[key],item["files"],item["completion"],v["table"],v["window"])
    result.update(original_native_guards_passed=True,candidate_counts=dict(samples=1292,post_frames=1174,drains=11740),
        fine_prefix_counts=dict(samples=461,post_frames=257,drains=2570),fine_reference_is_intentionally_stopped_partial=True)


def review(u,p,b,result):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    u.adopt(np.__file__);u.adopt(matplotlib.__file__)
    ctx,source=sources(u,p,b)
    he,h=helper(u,ctx["source_build"])
    native_e=u.adopt(T/"logs/upl_bigstep_r1.native.json")
    receipt=u.read(native_e)
    need(receipt.get("stage")==NAME+".native" and receipt.get("passed")is True and receipt.get("reader_attempts")==2 and
         receipt.get("bindings_unchanged")is True and receipt.get("independent_final_rehash_performed")is True and receipt["reader_helper"]==he,
         "Passed two-call native phase required; review never decodes")
    data={}
    for key,v in source.items():
        item=receipt["datasets"][key]
        call=u.owned(item["reader_call"],NAME+"."+key+".reader_call")
        need(item["source_run"]==v["run"] and item["source_solver_call"]==v["record"]["call"] and item["window"]==v["window"] and
             call["program"]==h["program"] and call["arguments"]==["--read","CPU",str(Path(v["record"]["job"]["output_directory"])/"data"),item["clock_CSV"]["path"],v["window"],str(DIRS[key])], "Original native program/CLI/source differs")
        need(rows(u.bind(item["clock_CSV"]))==[{k:str(v) for k,v in r.items()} for r in v["table"]], "Consumed prefix/candidate scalar CSV differs")
        data[key]=exports(u,DIRS[key],item["files"],item["completion"],v["table"],v["window"])
    short_e=pinned(u,"logs/upl_spr_av_new_requested_ON_r1.native_r2.json");s=u.read(short_e)
    sr=u.read(s["source_run"]);sc=u.owned(s["reader_call"],SHORT+".reader_r2_call");u.owned(sr["call"],SHORT+".run_call")
    need(s.get("passed")is True and s.get("original_native_guards_passed")is True and s.get("bindings_unchanged")is True and
         s.get("independent_final_rehash_performed")is True and sr.get("passed")is True and sr["program"]==ctx["program"] and
         (sr["job"]["SPR"],sr["job"]["Visco"],sr["job"]["eta"],sr["job"]["HG"])==(1,.1,.04,.1) and sc["program"]==u.read(s["reader_helper"])["program"], "Genuine matched requested458 short required")
    data["short"]=exports(u,Path(s["paths"]["native_dir"]),s["files"],s["completion"],sr["job"]["saved_clock_table"],"dyadic_short458",False)
    products={k:T/"figures"/("upl_bigstep_r1."+k) for k in ("history.csv","layers.csv","nearest.csv","theory.csv","history.png","modes.png")}
    u.fresh(*products.values())
    history,layer_rows,nearest=[],[],[]
    for key,d in data.items():
        need(np.array_equal(d["x0"],data["candidate"]["x0"]) and np.array_equal(d["p"]["q"][0].view("u8"),data["candidate"]["p"]["q"][0].view("u8")), "Actual initial ID-aligned common26 state differs")
        order=np.argsort(10*d["layer"]+d["column"]);sign=np.where(np.arange(10)%2,-1.,1.)
        for i,q in enumerate(d["p"]["q"]):
            uz=1000*(q[:,2]-d["x0"][:,2]);total=q[:,10:16].copy();total[:,[0,3,5]]-=q[:,6,None]
            uzg=uz[order].reshape(100,10);tg=total[order].reshape(100,10,6)
            a=((uzg-uzg.mean(axis=1,keepdims=True))*sign).mean(axis=1);at=((tg-tg.mean(axis=1,keepdims=True))*sign[None,:,None]).mean(axis=1)
            J=q[order,8].reshape(100,10);n=d["n"]["n"][i][order].reshape(100,10);rho=1000+1100/J;P=q[order,6].reshape(100,10)
            row=dict(series=key,part=i,time_s=float(d["clock"]["t"][i]),pressure_mean_Pa=float(P.mean()),top_pressure_Pa=float(P[-1].mean()),bottom_pressure_Pa=float(P[0].mean()),
                top_settlement_mm=float(-uzg[-1].mean()),bottom_settlement_mm=float(-uzg[0].mean()),J_min=float(J.min()),J_mean=float(J.mean()),J_max=float(J.max()),
                n_min=float(n.min()),n_mean=float(n.mean()),n_max=float(n.max()),rho_min=float(rho.min()),rho_mean=float(rho.mean()),rho_max=float(rho.max()),
                A_pi_Uz_RMS_mm=float(np.sqrt(np.mean(a*a))),A_pi_total_sigma_RMS_Pa=float(np.sqrt(np.mean(at*at))),total_compression_mean_Pa=float(-total[:,5].mean()))
            history.append(row)
            for level in range(100):
                layer_rows.append(dict(series=key,part=i,time_s=row["time_s"],initial_layer=level,z0_m=.005+.01*level,A_pi_Uz_signed_mm=float(a[level]),
                    **{"A_pi_total_sigma_"+k+"_Pa":float(at[level,j]) for j,k in enumerate(("xx","xy","xz","yy","yz","zz"))},
                    settlement_mean_mm=float(-uzg[level].mean()),P_mean_Pa=float(P[level].mean()),J_mean=float(J[level].mean()),n_mean=float(n[level].mean()),rho_from_verified_J_mean=float(rho[level].mean())))
    candidate=data["candidate"];t=candidate["clock"]["t"]
    coverage={}
    for key in ("short","fine"):
        ref=data[key];rt=ref["clock"]["t"];indices=[]
        for i in np.flatnonzero(t<=rt[-1]):
            j=int(np.argmin(np.abs(rt-t[i])));indices.append(j);a=candidate["p"]["q"][i];z=ref["p"]["q"][j]
            nearest.append(dict(reference=key,candidate_part=int(i),reference_part=j,candidate_time_s=float(t[i]),reference_time_s=float(rt[j]),signed_gap_s=float(t[i]-rt[j]),
                same_event_phase=int(candidate["table"][i]["post_open_by_completed_step"]==ref["table"][j]["post_open_by_completed_step"]),
                pressure_difference_RMS_Pa=float(np.sqrt(np.mean((a[:,6]-z[:,6])**2))),Uz_difference_RMS_mm=float(1000*np.sqrt(np.mean((a[:,2]-z[:,2])**2))),
                total_sigma_zz_difference_RMS_Pa=float(np.sqrt(np.mean(((a[:,15]-a[:,6])-(z[:,15]-z[:,6]))**2)))))
        selected=[v for v in nearest if v["reference"]==key]
        coverage[key]=dict(overlap_pairs=len(indices),distinct_reference_frames=len(set(indices)),duplicate_reference_uses=len(indices)-len(set(indices)),
            exact_clock_pairs=sum(v["signed_gap_s"]==0 for v in selected),max_abs_gap_s=max(abs(v["signed_gap_s"])for v in selected),phase_mismatches=sum(not v["same_event_phase"]for v in selected))
    xml=ET.parse(u.bind(ctx["job"]["runtime"])).getroot()
    value=lambda name:float(next(xml.iter(name)).get("value"))
    E,nu,k,water,Kw,n0,q0,tD=value("ModulusE"),value("PRvs"),value("HydraulicConductivity"),value("PoreWaterRho"),value("PoreWaterBulkModulus"),value("Porosity"),value("HydroMechTopLoadQ0"),value("HydroMechDrainageStartTime")
    M=E*(1-nu)/((1+nu)*(1-2*nu));Cv=k*M/(water*9.81);B=1/(1+n0*M/Kw)
    theory=[];lam=(np.arange(512)+.5)*np.pi;z=.995
    for clock in t[t>=tD]:
        decay=np.exp(-Cv*lam*lam*(clock-tD));finite=np.exp(-(Cv*B)*lam*lam*(clock-tD));coef=2*(-1.)**np.arange(512)/lam
        theory.append(dict(time_s=float(clock),legacy_Tv=float(Cv*(clock-tD)),classical_mean_P_Pa=float(q0*np.sum(2*decay/lam**2)),
            classical_material_top_settlement_mm=float(1000*q0/M*(z-np.sum(coef*np.sin(lam*z)/lam*decay))),
            finite_Kw_quasistatic_mean_P_Pa=float(B*q0*np.sum(2*finite/lam**2)),finite_Kw_material_top_settlement_mm=float(1000*q0/M*(z-B*np.sum(coef*np.sin(lam*z)/lam*finite)))))
    for key,values in (("history.csv",history),("layers.csv",layer_rows),("nearest.csv",nearest),("theory.csv",theory)):
        write_csv(products[key],values)
    fig,axes=plt.subplots(3,2,figsize=(12,10),constrained_layout=True)
    for ax,(field,label) in zip(axes.flat,(("pressure_mean_Pa","Mean P (Pa)"),("top_settlement_mm","Material top settlement (mm)"),("J_mean","Mean J"),("n_mean","Mean n"),("rho_mean","Mean current rho (kg/m3)"),("total_compression_mean_Pa","Mean total compression zz (Pa)"))):
        for key in data:
            values=[v for v in history if v["series"]==key];ax.plot([v["time_s"]for v in values],[v[field]for v in values],label=key)
        ax.set(xlabel="Actual saved time (s)",ylabel=label);ax.grid(True)
    axes[0,0].plot([v["time_s"]for v in theory],[v["classical_mean_P_Pa"]for v in theory],"--",label="classical quasi-static")
    axes[0,0].plot([v["time_s"]for v in theory],[v["finite_Kw_quasistatic_mean_P_Pa"]for v in theory],":",label="finite-Kw quasi-static")
    axes[0,1].plot([v["time_s"]for v in theory],[v["finite_Kw_material_top_settlement_mm"]for v in theory],":",label="finite-Kw quasi-static")
    axes[0,0].legend();axes[0,1].legend();fig.suptitle("Actual saved fields; unfitted quasi-static companions, no physical acceptance");fig.savefig(products["history.png"],dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(11,8),constrained_layout=True)
    for level in range(100):
        rr=[v for v in layer_rows if v["series"]=="candidate" and v["initial_layer"]==level]
        axes[0].plot([v["time_s"]for v in rr],[v["A_pi_Uz_signed_mm"]for v in rr],lw=.6,alpha=.45)
        axes[1].plot([v["time_s"]for v in rr],[v["A_pi_total_sigma_zz_Pa"]for v in rr],lw=.6,alpha=.45)
    axes[0].set_ylabel("Signed alternating Uz (mm)");axes[1].set_ylabel("Signed alternating total sigma zz (Pa)")
    for ax in axes:ax.set_xlabel("Actual saved time (s)");ax.grid(True);ax.axvspan(1.5,2.,alpha=.1)
    fig.suptitle("All100 original material layers; alternating original X columns, saved states only");fig.savefig(products["modes.png"],dpi=160);plt.close(fig)
    late=[v for v in history if v["series"]=="candidate" and 1.5<=v["time_s"]<=2.]
    result.update(source_native=native_e,source_requested_short=short_e,nearest_actual_time_coverage=coverage,
        late_1p5_to_2s={field:dict(first=late[0][field],last=late[-1][field],max=max(v[field]for v in late),last_over_first=late[-1][field]/late[0][field] if late[0][field]>0 else None)
            for field in ("A_pi_Uz_RMS_mm","A_pi_total_sigma_RMS_Pa")},late_actual_time_bounds_s=[late[0]["time_s"],late[-1]["time_s"]],
        theory_constants=dict(E=E,nu=nu,M=M,k=k,rho_w=water,g_reference=9.81,Kw=Kw,n0=n0,q0=q0,H=1.,tD=tD,Cv_legacy=Cv,B_finite_Kw=B,Cv_finite_Kw=Cv*B,modes=512),
        theory_limits="Unfitted quasi-static single-drainage sealed-loading companions, original event and material z=.995. Dynamic inertia, finite ramp transient, top-kernel traction, J evolution and current limiter remain distinct; no fitted H/load or theory acceptance.",
        files=[u.adopt(path)for path in products.values()],all100_material_layers_exported=True,interpolation_or_clock_rewrite=False,
        comparison_is_descriptive_not_5Pa_or_0p005mm_equivalence=True,reference_is_461_saved_frames_not_full_or_unknown_unsaved_stop_state=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase",choices=("native","review"),required=True)
    parser.add_argument("--execution-authorized",action="store_true")
    args=parser.parse_args()
    if not args.execution_authorized:parser.error("Explicit invocation of this one offline phase required")
    record=T/"logs"/("upl_bigstep_r1."+args.phase+".json")
    need(not record.exists(),"Retained phase receipt protected; no retry or rearm")
    u=None
    result=dict(stage=NAME+"."+args.phase,passed=False,failure=None,physical_acceptance=False,solver_build_Git_queue_or_watcher_invoked=False,
        automatic_full_restart=False,old_control_resumed=False,current_dynamic_step_handler_retained=True)
    try:
        u,p,b=definitions();(native if args.phase=="native" else review)(u,p,b,result);result["passed"]=True
    except Exception as exc:result["failure"]=str(exc)
    try:
        need(u is not None,"Pinned definitions not initialized")
        result["inputs"]=u.final_bindings();result["bindings_unchanged"]=result["independent_final_rehash_performed"]=True
    except Exception as exc:
        result["inputs"]=list(u.BOUND.values())if u else []
        result["passed"]=result["bindings_unchanged"]=result["independent_final_rehash_performed"]=False
        result["failure"]=(result["failure"]+"; "if result["failure"]else "")+str(exc)
    with record.open("x",encoding="utf-8",newline="\n")as stream:json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write("\n")
    print(json.dumps(dict(passed=result["passed"],phase=args.phase,receipt=str(record),failure=result["failure"])))
    return 0 if result["passed"]else 1


if __name__=="__main__":
    raise SystemExit(main())

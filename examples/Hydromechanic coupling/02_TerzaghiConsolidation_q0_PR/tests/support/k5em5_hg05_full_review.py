"""Offline audit of the completed uniform-grid 2Tv run; never starts a solver."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import numpy as np
import pandas as pd
import psutil
from k5em5_hg05_full import completion, TAG, FOLDER, FORMAL, STATE, ADMISSION, STEPS, END
from formal_release_sequence import CASE, TESTS, save, utc
from mdbc_gpu_vector_run import bound, read, verify
import k5_guard_probe as probe
from release_case import model, inspect, pressure_theory

TARGETS = (.005,.05,.1,.25,.4,.5,.7,1.,1.5,2.)


def main():
    destination = TESTS/"logs"/(TAG+".review.numeric.json")
    assert not destination.exists()
    r, q = read(STATE), read(TESTS/"logs"/(TAG+".queue_attempt.json"))
    assert r["status"] == "cpu_uniform_2tv_completed_pending_physical_review"
    assert r["owned_exited"] and r["exit_code"] == r["bat_exit_code"] == 0 and r["solver_completed"]
    assert q["terminal"]["completion"] == r["completion"] and q["terminal"]["outputs"] == r["outputs"]
    for owner in r.get("owned_solver_processes", [])+[{"pid":r["owned_cmd_pid"],"created":r["owned_cmd_created"]}]:
        try: assert psutil.Process(owner["pid"]).create_time() != owner["created"], "Owned process is still alive"
        except psutil.NoSuchProcess: pass
    admission = read(ADMISSION)
    assert admission["passed"] and admission["visual_inspected"] and admission["next_run_admitted"] == TAG
    assert admission["pressure_half_max_pa"] <= 5 and admission["settlement_half_max_mm"] <= .005
    verify(admission["evidence"])
    publication = CASE/"figures/full_validation_release_k5em5_uniform_CPU.check.json"
    published = read(publication)
    assert published["passed"] and published["frames"] == 402 and published["load_measured"]
    hashes = r["inputs"]+r["outputs"]+published["evidence"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda x:verify([x]), hashes))
    info = completion(FOLDER, STEPS, END, 402)
    assert info == r["completion"]
    m = model(FOLDER/(FORMAL+".xml"))
    assert m["dp"] == .01 and m["width"] == .1 and m["k"] == 5e-5
    initial = probe.native(FOLDER,0)
    z0 = initial.z.to_numpy().reshape(10,100).mean(axis=0)
    history = pd.read_csv(TESTS/"figures"/(TAG+"_runtime.csv"),float_precision="round_trip")
    assert len(history) == 402 and r["checked_frames"] == 402
    native_paths = sorted((FOLDER/"data").glob("Part_*.bi4"))
    assert [int(p.stem.split("_")[-1]) for p in native_paths] == list(range(402))

    def sample(i):
        a = probe.native(FOLDER,i)
        assert np.array_equal(a.id,np.arange(40,1040)) and a.load_available.eq(1).all()
        value = inspect(a,initial,m)
        value.update(native_part=i,step=int(a.step.iloc[0]))
        # Check the actual native material coordinates directly, not moving layers.
        assert abs(value["top_settlement_mm"]-1000*float((initial.z.iloc[99::100]-a.z.iloc[99::100]).mean())) < 1e-10
        for key in ("time_s","mean_pressure_pa","top_settlement_mm","bottom_settlement_mm","max_layer_total_error_pa","top_gap_pa","Q_pa"):
            assert abs(value[key]-history.iloc[i][key]) < 1e-7, (i,key)
        if value["time_s"] >= m["tD"]:
            pressure = a.pressure.to_numpy().reshape(10,100).mean(axis=0)
            truth = pressure_theory(z0,value["tv"],m)
            value.update(pressure_theory_rmse_pa=float(np.sqrt(np.mean((pressure-truth)**2))),
                         mean_theory_pa=float(truth.mean()),mean_pressure_error_pa=float(pressure.mean()-truth.mean()),
                         top_theory_error_mm=value["top_settlement_mm"]-value["classical_top_mm"],
                         bottom_theory_error_mm=value["bottom_settlement_mm"]-value["classical_bottom_mm"])
        else:
            pressure, truth = a.pressure.to_numpy().reshape(10,100).mean(axis=0), np.full(100,np.nan)
        shared = value["step"] <= 1500000 and value["step"] % 100 == 0
        if shared:
            b = probe.native(TESTS/"outputs/k5em5_hg05_15s_cpu_r1_c",value["step"]//100)
            columns = a.select_dtypes(include="number").columns
            assert a[columns].to_numpy(dtype="<f8").tobytes() == b[columns].to_numpy(dtype="<f8").tobytes()
            assert a.drop(columns=columns).equals(b.drop(columns=columns))
        return value,pressure,truth,shared

    with ThreadPoolExecutor(max_workers=4) as pool:
        sampled = list(pool.map(sample,range(402)))
    frame = pd.DataFrame([item[0] for item in sampled])
    assert frame.time_s.diff().iloc[1:].gt(0).all() and frame.step.iloc[-1] == STEPS
    assert abs(frame.time_s.iloc[-1]-END) < 1e-7 and frame.tv.iloc[-1] >= 2-1e-6
    shared = [i for i,item in enumerate(sampled) if item[3]]
    assert len(shared) == r["same_step_saved_prefix_matches"]
    post = frame[frame.time_s >= .1-1e-7]
    active = frame[frame.tv >= .1]
    late = frame[frame.tv >= 1]
    assert post.max_layer_total_error_pa.le(100).all() and post.top_gap_pa.le(100).all()
    assert abs(post.load_resultant_N_m+1000).lt(.001).all()
    assert active.pressure_theory_rmse_pa.le(100).all() and abs(active.mean_pressure_error_pa).le(100).all()
    ultimate_top = m["q0"]*z0[-1]/m["M"]*1000
    assert abs(active.top_theory_error_mm).le(.01*ultimate_top).all()
    assert late.pressure_theory_rmse_pa.le(50).all()
    first = frame.iloc[int(abs(frame.tv-1).idxmin())]
    final = frame.iloc[-1]
    actual_ratio = float(final.mean_pressure_pa/first.mean_pressure_pa)
    ideal_ratio = float(final.mean_theory_pa/first.mean_theory_pa)
    assert abs(actual_ratio/ideal_ratio-1) <= .1
    assert late.mean_pressure_pa.diff().iloc[1:].lt(0).all(), "Late pressure is not strictly decreasing"
    profiles,targets = [],[]
    for target in TARGETS:
        i = int(abs(frame.tv-target).idxmin())
        value,pressure,truth,_ = sampled[i]
        targets.append(dict(target_tv=target,**value))
        profiles.extend(dict(case="k5em5",k_m_s=m["k"],target_tv=target,actual_tv=value["tv"],time_s=value["time_s"],native_part=i,
            layer=j,z0_H=float(z0[j]/m["H"]),pressure_pa=float(pressure[j]),classical_pa=float(truth[j])) for j in range(100))
    artifacts=[]
    for suffix,data in (("_review_history",frame),("_review_profiles",pd.DataFrame(profiles)),("_review_targets",pd.DataFrame(targets))):
        path=TESTS/"figures"/(TAG+suffix+".csv")
        data.to_csv(path,index=False,mode="x")
        artifacts.append(path)
    result=dict(passed=True,visual_inspected=False,physical_scope="Provisional 1D elastic pressure/settlement acceptance; residual spatial stress/Q disclosed",utc=utc(),
        completion=info,native_frames_independently_reviewed=402,hash_verified_entries=len(hashes),model=m,final=final.to_dict(),
        actual_shared_saved_parts_with_15s=shared,full_cycle_half_step_validated=False,
        maxima=dict(stress_pa=float(post.max_layer_total_error_pa.max()),top_gap_pa=float(post.top_gap_pa.max()),force_error_N_m=float(abs(post.load_resultant_N_m+1000).max()),
            dx_mm=float(frame.max_dx_mm.max()),layer_span_mm=float(frame.max_layer_span_mm.max()),Q_pa=float(post.Q_pa.max()),
            pressure_rmse_Tv_ge_point1_pa=float(active.pressure_theory_rmse_pa.max()),top_error_Tv_ge_point1_mm=float(abs(active.top_theory_error_mm).max())),
        late=dict(start_actual_tv=float(first.tv),numeric_remaining_ratio=actual_ratio,theory_remaining_ratio=ideal_ratio,
            remaining_ratio_relative_error_pct=100*(actual_ratio/ideal_ratio-1),all_saved_means_strictly_decreasing=True,
            Q_at_Tv1=float(first.Q_pa),Q_at_Tv2=float(final.Q_pa)),
        final_top_settlement_error_pct=float(100*(final.top_settlement_mm/final.classical_top_mm-1)),
        evidence=[bound(p) for p in [Path(__file__),STATE,TESTS/"logs"/(TAG+".queue_attempt.json"),publication,ADMISSION]+artifacts],
        limitations=["Q rises to12.45Pa; not a proof that all spatial stress errors are removed. Old late-Q does not indefinitely block the user's provisional 1D pressure/settlement delivery.",
            "Same-step sparse saved prefix has only the actually shared frames; not an identical15-s full trajectory.",
            "Only15-s dt/half evidence. No plasticity, complex-boundary, large-rotation or exact-HG-restart acceptance.",
            "Ideal instantaneous-load theory uses g=9.81; Darcy fallback9.80665 differs by0.03417%; .01-s ramp/finiteKw remain numerical differences.",
            "k3/k4 use xi=.1; k5e-5 uses xi=.05, so this is not a permeability-only controlled comparison."])
    save(destination,result)
    print(json.dumps({k:v for k,v in result.items() if k!='evidence'},indent=2),flush=True)


if __name__ == "__main__":
    main()

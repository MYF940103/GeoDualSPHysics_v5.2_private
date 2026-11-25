"""Read a sealed +2.5-degree private TPI release, including its previous-pressure child."""
import argparse
import csv
import json
import math
from pathlib import Path
import struct
import sys

import numpy as np

TESTS = Path(__file__).resolve().parents[1]
CASE = TESTS.parent
sys.path.insert(0, str(CASE / "support"))
from postprocess_lian_release import native, PRE_IDS, RELEASE_IDS, SOIL_IDS, require, verify_source_material
sys.path.insert(0, str(CASE.parent / "04_CryerProblem_PR/tests/support"))
from cryer_live_history_review import _Cursor, read_item, EXPECTED_TYPES, CHILD, FIELDS

PRE = CASE / "CaseLianCollapse_psi2p5_pre_GPU_out/data/Part_1000.bi4"
SOURCE = 2_000_000
OPEN = SOURCE + 200
CAP = {"short": OPEN+8, "w30": OPEN+60_000, "paper": OPEN+240_000}
DT = 5e-6


def expected_steps(cap):
    return [SOURCE+1, SOURCE+2, OPEN-1, OPEN, *range(OPEN+1, OPEN+9), *range(OPEN+2000, cap+1, 2000)]


def read_frame(path):
    data = path.read_bytes()
    require(data.startswith(b"#FileJBD "), "Wrong BI4 header: "+str(path))
    cursor = _Cursor(data, 64)
    root = read_item(cursor, 0, True)
    cursor.finish("C08 native frame")
    part, = root["children"]
    m = part["values"]
    require(part["name"] == path.stem.upper() and part["array_types"] == EXPECTED_TYPES,
            "Unexpected native item or field types: "+path.name)
    hv = root["values"]
    require(root["name"] == "JPartDataBi4" and hv["Npiece"] == 1 and hv["Piece"] == 0 and hv["Data2d"]
            and hv["CaseNfixed"] == 2060 and hv["CaseNfluid"] == 5000 and hv["CaseNp"] == 7060
            and hv["Dp"] == .04 and hv["H"] == np.float32(.072) and not hv["PeriMode"],
            "Unexpected case geometry: "+path.name)
    order = np.argsort(part["arrays"]["Idp"])
    require(all(len(v) == len(order) and np.isfinite(v).all() for v in part["arrays"].values()),
            "Inconsistent native array sizes or nonfinite fields: "+path.name)
    a = {k:v[order] for k,v in part["arrays"].items()}
    h, = part["children"]
    require(h["name"] == CHILD and h["types"] == FIELDS
            and h["array_types"] == {"Idp":"DatUint", "PorePressPrev":"DatFloat"}
            and h["values"]["RunCode"] == hv["RunCode"] and np.array_equal(h["arrays"]["Idp"], SOIL_IDS),
            "Wrong TPI history schema, owner or IDs: "+path.name)
    prev = h["arrays"]["PorePressPrev"]
    require(prev.shape == (len(SOIL_IDS),) and np.isfinite(prev).all(), "Invalid pressure history: "+path.name)
    return m, a, h["values"], prev


def inspect_log(path, cap):
    dt_rows = rounds = filters = switches = 0
    min_bound = float("inf")
    imported = finished = False
    with path.open(encoding="utf8", errors="replace") as stream:
        for line in stream:
            if line.startswith("C08M0Dt "):
                step, stage, fixed, bound, *other = map(float, line.split()[1:])
                require(step == SOURCE+1+dt_rows//5 and stage == (0,1,0,0,0)[dt_rows%5]
                        and bound >= fixed == DT and len(other) == 4 and all(map(math.isfinite,(bound,*other))),
                        f"Invalid dt evaluation at {step:g}")
                min_bound = min(min_bound, bound)
                dt_rows += 1
            elif line.startswith("C08GpuRound "):
                step, r, filt = map(int, line.split()[1:])
                require(step == SOURCE+1+rounds//3 and r == rounds%3+1
                        and filt == int(r == 3 and step%40 == 0 and step <= OPEN), f"Invalid round at {step}")
                rounds += 1
                filters += filt
            elif line.startswith("C08M0Release "):
                items = line.split()
                require(int(items[1]) == OPEN and list(map(int, items[3:6])) == [255,5000,1805],
                        "Unexpected number of released wall or surviving particles")
                switches += 1
            elif "C08Mature imported 7060 fixed 2060 material 5000" in line:
                imported = True
            elif "Finished execution (code=0)" in line:
                finished = True
    require(imported and finished and switches == 1 and dt_rows == 5*(cap-SOURCE)
            and rounds == 3*(cap-SOURCE) and filters == 5, "Incomplete run/phase telemetry")
    return dict(dt_checks=dt_rows, min_allowed_dt_s=min_bound, pressure_rounds=rounds, pre_shepard_calls=filters)


def check_state(m, a, source, prior_kappa, active):
    ids = RELEASE_IDS if active else PRE_IDS
    b = len(ids) - len(SOIL_IDS)
    soil = slice(b,None)
    n0 = float(np.float32(.35))
    require(np.array_equal(a["Idp"], ids) and m["Npok"] == len(ids) and m["Nout"] == 0, "Native IDs or exclusion")
    require(a["Posd"][:b].tobytes() == source["Posd"][:b].tobytes() and not np.any(a["Vel"][:b]),
            "Fixed particle moved")
    require(a["PorePress0"].tobytes() == source["PorePress0"][ids].tobytes()
            and np.array_equal(a["ExcessPorePress"], a["PorePress"] - a["PorePress0"]), "P0 or excess differs")
    J = a["PoroVolumeRatio"][soil]
    n = a["PoroPorosity"][soil]
    rho = a["PoroMixtureDensity"][soil]
    kval = a["PoroHydraulicConductivity"][soil]
    V0 = source["PoroCurrentVolume"][SOIL_IDS]/source["PoroVolumeRatio"][SOIL_IDS]
    require(np.all(J>1-n0) and np.all((n>0)&(n<1)) and np.allclose(n,1-(1-n0)/J,atol=1e-14,rtol=0)
            and np.allclose(rho,1000+1072.5/J,rtol=2e-14,atol=0) and np.array_equal(a["Rhop"][soil],rho.astype("f4"))
            and np.allclose(a["PoroCurrentVolume"][soil],V0*J,rtol=2e-14,atol=0)
            and np.allclose(kval,float(np.float32(.0002))*np.exp((J-1)/(2*(1-n0))),rtol=2e-14,atol=0),
            "J, n, volume, density or conductivity ledger differs")
    require(np.all((a["Rhop"]>=700)&(a["Rhop"]<=3000)) and np.all(a["FSType"]<=4)
            and not np.any(a["Posd"][:,1]) and not np.any(a["HydroMechLoadAce"])
            and all(np.array_equal(a["Sigma_"+s],a["SigmaState_"+s].astype("f4")) for s in ("kk","ij"))
            and not np.any(a["Kplastic"][:b]) and np.all(a["Kplastic"][soil]>=prior_kappa),
            "Density, geometry, load or material history differs")
    fs = np.isin(a["FSType"][soil],[2,3])
    require(np.all(a["PorePress"][soil][fs]<=0) and np.all(a["Posd"][soil][:,[0,2]]>=-4e-8),
            "Free seepage or plane geometry failed")
    return fs


def run(tag, window, beta, prefix):
    label = "b004" if beta else "b0"
    require(tag == f"c08_psi25_tpi_{window}_{label}_r1", "Tag does not match the selected window/branch")
    folder = TESTS/"outputs"/tag
    callpath = TESTS/"logs"/(tag+".call.json")
    result = TESTS/"logs"/(tag+".native_review.json")
    output = TESTS/"figures"/(tag+"_native.csv")
    cap = CAP[window]
    steps = expected_steps(cap)
    files = sorted((folder/"data").glob("Part_????.bi4"))
    bound = [PRE, callpath, folder/"Run.out", *files]
    def binding():
        return [[str(f.relative_to(CASE)), f.stat().st_size, f.stat().st_mtime_ns] for f in bound]
    first = binding()
    if result.exists():
        prior = json.loads(result.read_text())
        require(prior["passed"] is True and prior["tag"]==tag and prior["prefix_tag"]==prefix and prior["files"]==first and output.is_file(),
                "Existing native review input or publication differs")
        print(result)
        return
    require(not output.exists(), "Partial prior review exists: "+str(output))
    call = json.loads(callpath.read_text())
    require(call["returncode"] == 0 and call["cap"] == cap and call["beta"] == beta
            and Path(call["PRE"]).resolve()==PRE and "-nsteps:"+str(cap) in call["command"]
            and str(folder) in call["command"], "Wrong completed call, branch, cap or PRE")
    require([f.name for f in files] == [f"Part_{i:04d}.bi4" for i in range(1,len(steps)+1)], "Incomplete save plan")
    sm, source = native(PRE)
    verify_source_material(sm, "psi2p5")
    require(sm["Step"]+1 == SOURCE and np.array_equal(source["Idp"], PRE_IDS), "Wrong time or owners in PRE")
    clock = np.cumsum(np.r_[sm["TimeStep"], np.full(cap-SOURCE, DT)])
    release_time = clock[OPEN-SOURCE]
    if window != "short":
        allowed = [f"c08_psi25_tpi_short_{label}_r1"]
        if window == "paper":
            allowed.append(f"c08_psi25_tpi_w30_{label}_r1")
        require(prefix in allowed, "The longer trajectory must supply the reviewed same-branch prefix")
    prefix_parts = []
    if prefix:
        previous = json.loads((TESTS/"logs"/(prefix+".native_review.json")).read_text())
        require(previous["passed"] is True and previous["tag"]==prefix, "Wrong prefix review")
        prefix_parts = sorted((TESTS/"outputs"/prefix/"data").glob("Part_????.bi4"))
        sealed = {name:(size,mtime) for name,size,mtime in previous["files"]}
        require(len(prefix_parts)==previous["frames"] and all(
            sealed.get(str(f.relative_to(CASE)))==(f.stat().st_size,f.stat().st_mtime_ns) for f in prefix_parts),
            "Incomplete or changed prefix")
    prior_p = source["PorePress"][SOIL_IDS]
    prior_kappa = source["Kplastic"][SOIL_IDS]
    last_step = SOURCE
    adjacent = 0
    rows = []
    prefront = float(source["Posd"][SOIL_IDS,0].max())
    for i,(path,step) in enumerate(zip(files, steps)):
        m, a, h, prev = read_frame(path)
        active = step>OPEN
        require(m["Cpart"]==i+1 and m["Step"]+1==step and m["TimeStep"]==clock[step-SOURCE]
                and m["HydroMechModel"]==2 and m["DilationDecay"]==np.float32(.2) and m["MaterialLawVersion"]==2
                and m["HydroMechFreeSeepage"] and m["HydroMechConductivityModel"]==1 and m["HydroMechConductivityCk"]==2
                and m["SymplecticDtPre"]==m["dtmin"]==m["dtmax"]==DT and -np.finfo(float).max<m["dterror"]<=1e-14,
                f"Native scheme, clock or material in {path.name}")
        require(m["GravityPreloadPhase"]==active and m["GravityPreloadEventCompletedStep"]==OPEN
                and m["GravityPreloadTargetIdBegin"]==1805 and m["GravityPreloadTargetIdCount"]==255
                and Path(m["GravityPreloadStateFile"]).resolve()==PRE
                and m["SoilDampingActive"]==(not active) and m["PoreShepardActive"]==(not active)
                and m["DynamicArtificialStressPolicy"]=="ReleaseOnly" and m["DynamicArtificialStressActive"]==active
                and m["DynamicArtificialStressCoef"]==np.float32(.3) and m["DynamicArtificialStressExp"]==np.float32(2.55)
                and m["DynamicNoPenetrationPolicy"]=="FixedPlaneStageProjectionReleaseOnly"
                and m["DynamicNoPenetrationActive"]==active and not m["DynamicNoPenetrationReactionClosed"],
                f"Wall or stage policy in {path.name}")
        if active:
            require(m["GravityPreloadActualTime"]==release_time and m["GravityPreloadActualCompletedStep"]==OPEN,
                    "Wrong actual wall release")
        require(h["CompletedUpdates"]==step and h["Dt"]==DT and h["Valid"] and h["Schema"]==1
                and h["Scheme"]==("P3_B_alpha_half_beta_0p04" if beta else "P3_B_alpha_half_beta_zero")
                and h["PreviousTime"]==clock[step-SOURCE-1] and h["SavedTime"]==m["TimeStep"], "TPI history clock/scheme")
        if last_step+1==step:
            require(prev.tobytes()==prior_p.tobytes(), f"Previous pressure does not match adjacent native save at {step}")
            adjacent += 1
        fs = check_state(m, a, source, prior_kappa, active)
        if i < len(prefix_parts):
            om, oa, oh, op = read_frame(prefix_parts[i])
            require(om["Step"]==m["Step"] and struct.pack("<dd",om["TimeStep"],om["dterror"])==
                    struct.pack("<dd",m["TimeStep"],m["dterror"]) and h["Scheme"]==oh["Scheme"]
                    and all(v.tobytes()==oa[k].tobytes() for k,v in a.items()) and op.tobytes()==prev.tobytes(),
                    "Same-branch native prefix mismatch in "+path.name)
        prior_p = a["PorePress"][-5000:]
        prior_kappa = a["Kplastic"][-5000:]
        x = a["Posd"][-5000:,0]
        rows.append(dict(part=i+1,completed_step=step,time_s=m["TimeStep"],tau_s=m["TimeStep"]-release_time,
                         released=int(active),signed_dterror_s=m["dterror"],n_FS=int(fs.sum()),
                         n_negative_p=int((prior_p<0).sum()),p_min_Pa=float(prior_p.min()),p_max_Pa=float(prior_p.max()),
                         p_mean_Pa=float(prior_p.mean(dtype=float)),kappa_max=float(prior_kappa.max()),
                         kappa_mean=float(prior_kappa.mean(dtype=float)),front_x_m=float(x.max()),
                         advance_from_pre_m=float(x.max())-prefront,
                         speed_max_m_s=float(np.linalg.norm(a["Vel"][-5000:],axis=1).max())))
        last_step = step
    log = inspect_log(folder/"Run.out", cap)
    require(binding()==first and adjacent==11, "Inputs changed or adjacent-history samples missing")
    report = dict(passed=True, tag=tag, beta=beta, source_time_s=float(clock[0]), release_time_s=float(release_time),
                  end_s=float(clock[-1]), final_completed_step=cap, frames=len(rows), adjacent_history=adjacent,
                  prefix_tag=prefix,prefix_equal_frames=len(prefix_parts),files=first,physical_acceptance=False,**log)
    with output.open("x",encoding="utf8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    with result.open("x",encoding="utf8") as stream:
        json.dump(report,stream,indent=2,allow_nan=False)
    print(result)


if __name__=="__main__":
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument("tag")
    args.add_argument("--window",choices=tuple(CAP),required=True)
    args.add_argument("--beta",type=float,choices=(0.,.04),required=True)
    args.add_argument("--prefix")
    opt=args.parse_args()
    run(opt.tag,opt.window,opt.beta,opt.prefix)

"""Same-backend regression of the C08 wall retirement, seepage and material return."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import regression as reg

OUT = reg.C08 / "outputs"


def case(lane):
    if lane == "short_cpu":
        return ("upl_preload_handoff_receive_CPU_r1_seed",
                "upl_preload_handoff_source_CPU_r1", "Part_0010.bi4", 420, "0.000025")
    if lane == "plastic":
        return ("c08_h18_as03_n255_r1", "c08_h18_wend_psi0_pre_r2",
                "Part_1000.bi4", 2002001, "0.002")
    raise ValueError(lane)


def prepare(lane):
    directory, preload, frame, _, interval = case(lane)
    source = OUT / directory
    xml, = source.glob("*.xml")
    doc = ET.parse(xml)
    special = doc.find("execution/special")
    h = special.find("hydromechanics")
    for key, value in (("HydroMechTopLoadMode", "0"), ("HydroMechDrainage", "0"), ("HydroMechFreeSeepage", "1")):
        node = h.find(key)
        reg.require(node is not None and node.get("value") == value, key)
        h.remove(node)
    flag = h.find("HydroMechDynamicSeepage")
    reg.require(flag.get("value") == "1", "Explicit u-pl required")
    flag.tag = "HydroMechModel"
    ET.SubElement(special, "drainage", mode="freeSeepage")
    handoff=special.find("gravitypreload")
    pre=(OUT/preload/"data"/frame).resolve()
    reg.require(Path(handoff.get("statefile")).parts[-3:] == (preload,"data",frame) and pre.is_file(),
                "Retained native PRE")
    handoff.set("statefile",str(pre))
    reg.parameter(doc, "TimeOut", interval)
    dst = HERE / "seeds" / lane
    dst.mkdir(parents=True, exist_ok=True)
    data = ET.tostring(doc.getroot(), xml_declaration=True, encoding="utf-8")
    for name, payload in [(xml.name, data), *[(xml.stem + ext, (source / (xml.stem + ext)).read_bytes())
                                               for ext in (".bi4", "_Normals.nbi4")]]:
        t = dst / name
        if t.exists():
            reg.require(t.read_bytes() == payload, "Existing input differs " + name)
        else:
            t.write_bytes(payload)
    return dst / xml.stem, pre


def execute(lane, backend, version):
    seed, pre = prepare(lane)
    exe = HERE.parent / version / reg.EXECUTABLE[backend]
    cap = case(lane)[3]
    dst = HERE / "runs" / f"{lane}_{backend}_{version}"
    reg.require(exe.is_file(), "Missing captured " + str(exe))
    dst.mkdir(parents=True)
    flags = ["-" + backend, "-stable"]
    if backend == "cpu":
        flags.append("-ompthreads:1")
    flags.append("-mdbc_freeslip:1" if lane == "plastic" else "-mdbc_freeslip")
    args = [str(exe), *flags, str(seed), str(dst), "-dirdataout", "data", "-svres", f"-nsteps:{cap}"]
    env = os.environ.copy()
    env["PATH"] = str(reg.BIN) + os.pathsep + env["PATH"]
    with (dst / "console.log").open("xb") as log:
        job = subprocess.run(args, cwd=reg.BIN, env=env, stdout=log, stderr=subprocess.STDOUT,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    print(lane, backend, version, job.returncode, flush=True)
    receipt = dict(args=args, exit=job.returncode, program_bytes=exe.stat().st_size,
                   program_mtime_ns=exe.stat().st_mtime_ns, preload=str(pre),
                   preload_bytes=pre.stat().st_size, preload_mtime_ns=pre.stat().st_mtime_ns)
    (dst / "call.json").write_text(json.dumps(receipt, indent=2), encoding="utf8")
    if job.returncode:
        raise RuntimeError(str(dst) + "\n" + (dst/"console.log").read_text(errors="replace")[-1300:])


def statistics_for(lane, backend, version):
    directory,preload,frame,cap,_ = case(lane)
    root = reg.unpack(OUT / preload / "data" / frame)
    source = root[5][0]
    sv, sa = source[2], source[4]
    xml, = (HERE/"seeds"/lane).glob("*.xml")
    h = ET.parse(xml).find("execution/special/hydromechanics")
    def scalar(k):
        return float(np.float32(h.find(k).get("value")))
    n0, rhow, k0 = map(scalar, ("Porosity","PoreWaterRho","HydraulicConductivity"))
    rho0, mass = float(root[2]["Rhop0"]), float(root[2]["MassFluid"])
    ordered = np.argsort(sa["Idp"][1])
    srcids = sa["Idp"][1][ordered]
    p0 = sa["PorePress0"][1][ordered]
    soilids = np.arange(2060,7060)
    begin, count = sv["GravityPreloadTargetIdBegin"], sv["GravityPreloadTargetIdCount"]
    expected_ids = np.setdiff1d(srcids, np.arange(begin, begin+count))
    dt = 2.5e-6 if lane == "short_cpu" else 5e-6
    base_step = sv["Step"]+1
    clocks = [float(sv["TimeStep"])]
    for _ in range(cap-base_step):
        clocks.append(clocks[-1]+dt)
    dst = HERE / "runs" / f"{lane}_{backend}_{version}"
    runlog=(dst/"Run.out").read_text(encoding="utf8", errors="replace")
    reg.require("phase=released" in runlog and "damping=OFF Shepard=OFF FreeSeepage=ON" in runlog,"No real release transition")
    frames = []
    for f in sorted((dst/"data").glob("Part_????.bi4")):
        node = reg.unpack(f)[5][0]; v,a = node[2], node[4]
        ids = a["Idp"][1]; active = np.argsort(ids); ix = np.flatnonzero(ids>=2060)
        reg.require(len(a)==22 and v["Nout"]==0 and np.array_equal(ids[active],expected_ids)
                    and np.array_equal(np.sort(ids[ix]),soilids), "Retired or material IDs")
        step = v["Step"]+1; t = float(v["TimeStep"])
        reg.require(0<step-base_step<len(clocks) and t==clocks[step-base_step], "Actual scalar clock")
        reg.require(np.array_equal(a["PorePress0"][1][active],p0[np.searchsorted(srcids,expected_ids)]), "Original P0 inheritance")
        reg.require(v["GravityPreloadPhase"]==1 and v["GravityPreloadActualCompletedStep"]==base_step, "PRE handoff")
        reg.require(v["HydroMechFreeSeepage"] and not v["SoilDampingActive"] and not v["PoreShepardActive"]
                    and v["dterror"]<=1.e-14, "Free seepage or necessary step")
        if lane == "plastic":
            reg.require(v['DynamicNoPenetrationActive'] and v['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly'
                        and not v['DynamicNoPenetrationReactionClosed'], "Fixed-plane stage policy")
            reg.require(v['DynamicArtificialStressActive'] and v['DynamicArtificialStressPolicy']=='ReleaseOnly'
                        and v['DynamicArtificialStressCoef']==np.float32(.3) and v['DynamicArtificialStressExp']==np.float32(2.55),
                        "Released artificial stress")
        fs = a["FSType"][1][ix]; pressure = a["PorePress"][1][ix]; sf=(fs==2)|(fs==3)
        reg.require(sf.any() and np.all(pressure[sf]<=0), "Completed-step positive seepage pressure")
        kap=a["Kplastic"][1][ix]; reg.require((kap>=0).all(),"Negative kappa")
        j=a["PoroVolumeRatio"][1][ix]
        n=a["PoroPorosity"][1][ix]; volume=a["PoroCurrentVolume"][1][ix]; rho=a["PoroMixtureDensity"][1][ix]
        reg.require((j>0).all() and (n>0).all() and (n<1).all() and (volume>0).all() and (rho>0).all()
                    and (a["PoroHydraulicConductivity"][1][ix]>0).all(),"Invalid volume/storage state")
        for observed, expected in ((n,1.-(1.-n0)/j), (volume,(mass/rho0)*j),
                                   (rho,rhow+(rho0-rhow)/j),
                                   (a["PoroHydraulicConductivity"][1][ix],k0*np.exp((j-1.)/((1.-n0)*float(v["HydroMechConductivityCk"]))))):
            reg.require(np.allclose(observed,expected,rtol=1e-13,atol=0), "Constitutive ledger differs")
        reg.require(np.array_equal(a["Rhop"][1][ix],rho.astype("float32"))
                    and np.array_equal(a["ExcessPorePress"][1][ix],pressure-a["PorePress0"][1][ix]),"Density/excess write-back")
        frames.append(dict(step=step,time_s=t,active_ids=len(ids),soil=len(ix),free_surface=int(sf.sum()),
                           positive_on_fs=int((pressure[sf]>0).sum()),kappa_positive=int((kap>0).sum()),
                           kappa_max=float(kap.max()),min_z=float(a["Posd"][1][ix,2].min()),
                           min_x=float(a["Posd"][1][ix,0].min()),pmin_pa=float(pressure.min()),
                           pmax_pa=float(pressure.max()),Jmin=float(j.min()),Jmax=float(j.max()),
                           signed_dterror=float(v['dterror'])))
    reg.require(bool(frames) and frames[-1]['step']==cap, "Completed cap")
    if lane=="plastic":
        reg.require(frames[-1]["kappa_positive"]>0,"No real plastic update")
        reg.require("FixedPlaneStageProjectionReleaseOnly" in runlog or "certified PRE uses NoPen off" in runlog,"No fixed-plane stage projection")
        reg.require(all(x['min_x']>=0 and x['min_z']>=0 for x in frames),"Fixed-plane penetration")
    return dict(source=preload,pre_schema=sv["GravityPreloadHandoffSchema"],
                source_step=base_step,source_actual_time_s=sv["TimeStep"],pre_kappa_max=float(sa['Kplastic'][1].max()),
                retired_begin=begin,retired_count=count,frames=frames)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=("run","compare","physical"))
    p.add_argument("lane",choices=("short_cpu","plastic"));p.add_argument("backend",choices=("cpu","gpu"))
    p.add_argument("version")
    args=p.parse_args()
    if args.action=="run":execute(args.lane,args.backend,args.version)
    elif args.action=="physical":
        out=statistics_for(args.lane,args.backend,args.version)
        raw=json.dumps(out,indent=2,allow_nan=False,default=lambda value:value.item())
        with (HERE/f"{args.lane}_{args.backend}_{args.version}.physical.json").open("x",encoding="utf8") as f:
            f.write(raw+"\n")
    else:
        reg.BASE=HERE
        cmp=reg.compare(args.lane,args.backend,"old",args.version)
        result=dict(comparison=cmp,profiles=statistics_for(args.lane,args.backend,args.version))
        payload=json.dumps(result,indent=2,allow_nan=False,default=lambda value:value.item())
        with (HERE/f"{args.lane}_{args.backend}_{args.version}.json").open("x",encoding="utf8") as f:
            f.write(payload+"\n")

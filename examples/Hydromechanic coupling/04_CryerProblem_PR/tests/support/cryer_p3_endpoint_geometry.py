"""Build and audit same-round surface tracking reuse in the private Cryer GPU solver."""
import argparse
import csv
import filecmp
import os
from pathlib import Path
import shutil

from cryer_drain_schema_r1 import old
from cryer_p3_verify_r1 import audit
from cryer_row_gpu_r1 import call, load, need, save

BASE = "cryer_drain_schema_gpu_r1"
TAG = "cryer_endpoint_geom_r1"
OUT, LOG = old.OUT, old.LOG

COPY = """
#include <cstdlib>
#include <vector>

template<class T> static void CopyCryerTracking(const T* device,unsigned n,std::vector<unsigned char>& bytes){
  const size_t at=bytes.size(),length=sizeof(T)*size_t(n);
  bytes.resize(at+length);
  if(cudaMemcpy(bytes.data()+at,device,length,cudaMemcpyDeviceToHost)!=cudaSuccess)
    throw std::runtime_error("Failed to read Cryer tracking fields.");
}
"""
TARGET = """          upl_tpi_cryer_gpu_r1::WriteFinal(UPL_TPI_CRYER_GPU_VIEW);
          ApplyPorePressureBoundaries();"""
REUSE = """          upl_tpi_cryer_gpu_r1::WriteFinal(UPL_TPI_CRYER_GPU_VIEW);
          // This round already tracked its current geometry inside Interaction_Forces.
          // A wall fit or periodic remap would require the full boundary path.
          if(!DynamicPoreFreeBody || DynamicPoreWall || PeriActive || Simulate2D)
            ApplyPorePressureBoundaries();
          else{
            static const bool verifyGeometry=std::getenv("CRYER_CHECK_TRACKING")!=NULL;
            if(verifyGeometry && (Nstep==0 || Nstep==63 || Nstep==4096)){
              auto readTracking=[&](std::vector<unsigned char>& bytes){
                CopyCryerTracking(CorrMatg,Np,bytes);
                CopyCryerTracking(FSTypeg,Np,bytes);
                CopyCryerTracking(FSNormalg,Np,bytes);
                CopyCryerTracking(PosDivg,Np,bytes);
              };
              std::vector<unsigned char> before,after;
              readTracking(before);
              ComputeFreeSurfaceTracking();
              readTracking(after);
              if(before!=after)Run_Exceptioon("Endpoint surface geometry changed within the pressure round.");
              Log->Printf("Endpoint geometry exact: step=%u round=%u particles=%u bytes=%llu",
                unsigned(Nstep),round+1,Np,(unsigned long long)before.size());
            }
            ApplyFreeSurfacePorePressure();
          }"""


def build():
    source = OUT/(TAG+"_source")
    shutil.copytree(OUT/(BASE+"_source"), source)
    unit = source/"JSphGpuSingle.cpp"
    raw = unit.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    def replace(a, b):
        nonlocal raw
        a, b = (x.replace("\n",newline).encode("ascii") for x in (a,b))
        need(raw.count(a)==1,"Expected one patch location")
        raw=raw.replace(a,b)
    replace("#include <map>", "#include <map>\n#include <stdexcept>\n"+COPY)
    replace(TARGET,REUSE)
    unit.write_bytes(raw)
    old.build("gpu",TAG,source)


def run(profile):
    label=TAG+"_"+profile
    out=OUT/label
    need(not out.exists() and not (LOG/(label+".call.json")).exists(),"Output exists")
    config = {"explicit2":("model1",2), "p3_2":("model2",2),
              "p3_64":("model2",64), "p3_4097":("model2",4097)}
    model,n=config[profile]
    if n>2:
        earlier="p3_2" if n==64 else "p3_64"
        need(load(LOG/(TAG+"_"+earlier+".check.json"))["passed"],"Previous candidate qualification")
    product=load(LOG/(TAG+"_Release.build.json"))
    exe=Path(product["program"]["path"])
    need(product["passed"] and exe.stat().st_size==product["program"]["bytes"], "Private build")
    prefix=OUT/(BASE+"_"+model+"_seed")/old.SEED_NAME
    argv=[str(exe),"-gpu","-stable",str(prefix),str(out),"-dirdataout","data","-svres","-nsteps:"+str(n)]
    env={k:v for k,v in os.environ.items() if not k.upper().startswith("UPL_TPI")}
    if n>2 or profile=="p3_2":
        env["CRYER_CHECK_TRACKING"]="1"
    rec=call(argv,exe.parent,env,LOG/(label+".console.log"))
    save(LOG/(label+".call.json"),rec)
    need(rec["win32_exit"]==rec["popen_exit"]==0,"Solver failed: "+str(out))


def review(profile):
    n={"explicit2":2,"p3_2":2,"p3_64":64,"p3_4097":4097}[profile]
    model="model1" if profile=="explicit2" else "model2"
    ref=OUT/(BASE+"_"+model if n==2 else "cryer_p3_gpu_"+("b64" if n==64 else "drain4097")+"_r1")
    label=TAG+"_"+profile
    out=OUT/label
    rec=load(LOG/(label+".call.json"))
    need(rec["win32_exit"]==rec["popen_exit"]==0,"Incomplete solver")
    with (out/"Run.csv").open(encoding="utf-8-sig",newline="") as stream:
        summary,=csv.DictReader(stream,delimiter=";")
    need(int(summary["Steps"])==n and int(summary["PartsOut"])==0,"Run extent")
    steps=[0,n] if n<=64 else [*range(0,4097,64),4097]
    tpi=model=="model2"
    rows=audit(out/"data",steps,2.**(-19 if tpi else -20),ref/"data",exact=True,p3_sidecars=tpi)
    files=sorted(f.name for f in ref.glob("UplTpi*") if f.is_file())
    need(files==sorted(f.name for f in out.glob("UplTpi*") if f.is_file()) and bool(files)==tpi,"ledger schema")
    for name in files:
        need(filecmp.cmp(out/name,ref/name,shallow=False),"Different pressure/force/step ledger "+name)
    actual=[line.strip() for line in (out/"Run.out").read_text(errors="replace").splitlines() if line.startswith("Endpoint geometry exact:")]
    selected=[i for i in (0,63,4096) if i<n] if tpi else []
    expected=[f"Endpoint geometry exact: step={i} round={r} particles=37181 bytes={37181*92}" for i in selected for r in (1,2,3)]
    need(actual==expected,"Wrong intra-round geometry record: "+str(actual[:3]))
    save(LOG/(label+".check.json"),dict(passed=True,reference=ref.name,steps=n,frames=len(rows),
         exact_native_arrays=22,ids=37181,exact_signed_clock=True,identical_ledgers=files,
         checked_geometry=actual,tracking_traversals_avoided=3*n-len(actual) if tpi else 0,
         loop_s=float(summary["TSimul"]),last=rows[-1]))



def timing():
    """Compare the actual pressure solver with identical reduced output in alternating order."""
    from statistics import median
    import xml.etree.ElementTree as ET
    need(load(LOG/(TAG+"_p3_64.check.json"))["passed"], "Short trajectory required")
    seed=OUT/(BASE+"_model2_seed")/old.SEED_NAME
    cfg=ET.parse(seed.with_suffix(".xml"))
    need(float(cfg.find(".//parameter[@key='TimeOut']").get("value"))==2.**-13,"Output interval")
    env={k:v for k,v in os.environ.items() if not k.upper().startswith(("UPL_TPI","CRYER_CHECK_TRACKING"))}
    results=[]
    for repeat in range(3):
        groups=("original","reuse") if repeat%2==0 else ("reuse","original")
        for group in groups:
            label=f"{TAG}_t65_{repeat}_{group}"
            out=OUT/label
            record=LOG/(label+".call.json")
            program=Path(load(LOG/((BASE if group=="original" else TAG)+"_Release.build.json"))["program"]["path"])
            if not record.exists():
                need(not out.exists() and not (LOG/(label+".console.log")).exists(),"Partial timing run")
                argv=[str(program),"-gpu","-stable",str(seed),str(out),"-dirdataout","data","-svres","-nsteps:65"]
                rec=call(argv,program.parent,env,LOG/(label+".console.log"))
                save(record,rec)
            rec=load(record)
            need(rec["win32_exit"]==rec["popen_exit"]==0 and Path(rec["argv"][0])==program,"Timing solver")
            with (out/"Run.csv").open(encoding="utf-8-sig",newline="") as stream:
                row,=csv.DictReader(stream,delimiter=";")
            need((int(row["Steps"]),int(row["PartsOut"]),int(row["PartFiles"]))==(65,0,3),"Timing output")
            results.append(dict(repeat=repeat,group=group,loop_s=float(row["TSimul"]),total_s=float(row["TTotal"]),
                                part_s=float(row["SU-SavePart"]),device=row["Hardware"]))
        baseline,candidate=[OUT/f"{TAG}_t65_{repeat}_{k}" for k in ("original","reuse")]
        audit(candidate/"data",[0,64,65],2.**-19,baseline/"data",exact=True,p3_sidecars=True)
        files=sorted(p.name for p in baseline.glob("UplTpi*"))
        need(len(files)==9 and all(filecmp.cmp(baseline/n,candidate/n,shallow=False) for n in files),"Timing ledgers")
    pairs=[next(r["loop_s"] for r in results if r["repeat"]==i and r["group"]=="original")/
           next(r["loop_s"] for r in results if r["repeat"]==i and r["group"]=="reuse") for i in range(3)]
    save(LOG/(TAG+"_timing.check.json"),dict(results=results,paired_loop_speedups=pairs,
         median_paired_loop_speedup=median(pairs),new_updates_each=65,full_checks_per_pair=3,
         tracked_geometry_refreshes_removed_per_update=3,physical_acceptance=False))

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=["build","run","review","timing"])
    p.add_argument("profile",nargs="?",choices=["explicit2","p3_2","p3_64","p3_4097"])
    args=p.parse_args()
    if args.action=="build": build()
    elif args.action=="timing": timing()
    elif args.action=="run": run(args.profile)
    else: review(args.profile)

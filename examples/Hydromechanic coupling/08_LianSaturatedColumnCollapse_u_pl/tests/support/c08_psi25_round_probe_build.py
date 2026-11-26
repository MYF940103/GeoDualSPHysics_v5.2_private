"""Build only the private output-only C08 pressure-round observer on the sealed b004 receiver."""
import difflib
import json
from pathlib import Path
import re
import shutil
import subprocess

from c08_m0_coupled_baseline_gpu_r1 import BUILD as SINGLE
from c08_m0_gpu_coupled_r1 import BUILD as GPU, CUDA, SRC, once
from c08_psi25_tpi_build import OUT as CONTROL, RUNTIME, digest
from c08_psi25_tpi_run import PRE, TESTS, identity, now, record

BUILD=TESTS/"outputs/c08_psi25_round_probe_build_r1"
PROGRAM=BUILD/"C08Psi25RoundProbe.exe"
HEADER=Path(__file__).with_name("c08_psi25_tpi_round_probe.h")


def required(check, message):
    if not check:
        raise ValueError(message)


def build():
    cl,link=shutil.which("cl.exe"),shutil.which("link.exe")
    required(cl and link,"Use the MSVC x64 developer shell")
    parent=json.loads((CONTROL/"build.json").read_text())
    baseline=Path(parent["exe"])
    source=SINGLE/"JSphGpuSingle.cpp"
    single_receipt=json.loads((SINGLE/"build.json").read_text())
    required(digest(source)==single_receipt["changed"]["JSphGpuSingle"]["changed"],"Frozen host source differs")
    rsp0=CONTROL/"link.rsp"
    rsp=rsp0.read_text(encoding="utf8").splitlines()
    objects=[Path(x.strip('"')) for x in rsp[1:]]
    original_obj=SINGLE/"JSphGpuSingle.obj"
    required(len(objects)==113 and objects.count(original_obj)==1 and all(
        p.is_file() and p.stat().st_mtime_ns <= baseline.stat().st_mtime_ns for p in objects),
        "Incomplete or changed baseline objects")
    before=[identity(p) for p in (source,original_obj,HEADER,rsp0,baseline,PRE)]
    headers=CONTROL/"src/source"
    original=source.read_text(encoding="utf8")
    inc='#include "FunctionsCuda.h"'
    candidate=once(original,inc,inc+'\n#include "c08_psi25_tpi_round_probe.h"')
    begin=candidate.index("void JSphGpuSingle::CorrectTpiPressure(double dt){")
    end=candidate.index("void JSphGpuSingle::Run(std::string appname",begin)
    body=candidate[begin:end]
    body=once(body,"  TpiEndpoint=true;",'''  static c08round::Observer observer;
  TpiEndpoint=true;''')
    old="      Interaction_Forces(INTERSTEP_SymCorrector);"
    body=once(body,old,old+'''
      if(c08round::sample(Nstep+1))observer.before(DirOut,unsigned(Nstep+1),round+1,TimeStep,dt,Np,Npb,
        Idpg,Posxyg,Poszg,Codeg,FSTypeg,CorrMatg,PoroJg,PorePressg,Aceg,FSNormalg,BoundModeg,
        PoroThetag,PorePressRateg,TpiSourceg,TpiPreviousg,TpiNextg,1.-double(SoilCte.Porosity),
        double(SoilCte.PoreWaterBulkModulus),double(SoilCte.PoreWaterRho),double(SoilCte.HydraulicConductivity),
        DynamicPoreConductivityCk,double(MassFluid)/double(RhopZero),double(KernelH),double(Eta2),double(KernelSize2));''')
    emission='      Log->Printf("C08GpuRound'
    body=once(body,emission,'      if(c08round::sample(Nstep+1))observer.after(DirOut,Np,Idpg,FSTypeg,PorePressg);\n'+emission)
    candidate=candidate[:begin]+body+candidate[end:]
    BUILD.mkdir()
    private=BUILD/source.name
    private.write_text(candidate,encoding="utf8")
    shutil.copy2(HEADER,BUILD/HEADER.name)
    (BUILD/"changes.diff").write_text("".join(difflib.unified_diff(
        original.splitlines(True),candidate.splitlines(True),"original/JSphGpuSingle.cpp","observer/JSphGpuSingle.cpp")),encoding="utf8")
    includes=[GPU,TESTS/"support",headers,CUDA/"include"]
    cmd=[cl,"/c","/nologo","/W3","/O2","/Zi","/D_WITHGPU","/DWIN32","/D_CONSOLE","/D_VC80_UPGRADE=0x0710",
         "/D_MBCS","/Gm-","/EHsc","/MT","/GS","/fp:precise","/Zc:wchar_t","/Zc:forScope","/Zc:inline",
         "/openmp","/external:W3","/Gd","/TP","/FC",*["/I"+str(p) for p in includes],
         "/Fo"+str(private.with_suffix(".obj")),"/Fd"+str(BUILD/"host.pdb"),str(private)]
    def invoke(command,kind):
        with (BUILD/(kind+".log")).open("xb") as stdout:
            rc=subprocess.run(command,cwd=SRC/"VS",stdout=stdout,stderr=subprocess.STDOUT).returncode
        record(BUILD/(kind+".json"),dict(command=command,returncode=rc,ended_utc=now()))
        required(rc==0,"Build failed at "+kind)
    invoke(cmd,"compile")
    objects[objects.index(original_obj)]=private.with_suffix(".obj")
    head=rsp[0]
    for key,suffix in (("OUT",".exe"),("PDB",".pdb"),("LTCGOUT",".iobj"),("IMPLIB",".lib")):
        head,n=re.subn("/"+key+r':"[^"]+"',lambda _: '/'+key+':"'+str(PROGRAM.with_suffix(suffix))+'"',head)
        required(n==1,"Unexpected linker output switch")
    target=BUILD/"link.rsp"
    target.write_text("\n".join([head,*['"'+str(p)+'"' for p in objects]]),encoding="utf8")
    invoke([link,"@"+str(target)],"link")
    for name in RUNTIME:
        shutil.copy2(CONTROL/name,BUILD/name)
    required(all(identity(Path(s["path"]))==s for s in before),"An original input changed during build")
    record(BUILD/"build.json",dict(built_utc=now(),program=str(PROGRAM),executable=identity(PROGRAM),
        private_sources=[identity(private),identity(BUILD/HEADER.name)],input_files=before,
        unchanged_objects=112,changed_host_objects=1,changed_cuda_objects=0,header_commit=parent["header_commit"],
        full_steps=[2060200,2176200,2240200],probe_ids=[6868,6918,6919,6920,7010],
        mandatory_headers=["C08TpiRoundProbe.csv","C08TpiRow1"],solver_launched=False))


if __name__=="__main__":
    build()

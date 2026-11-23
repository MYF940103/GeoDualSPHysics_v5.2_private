"""Build and run the private C08 coupled GPU startup with the official Release objects."""
import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from c08_m0_coupled_r1 import T, SRC, RELEASE, SEED, TAG as CPU_TAG, modify, once, sha

TAG = "c08_m0_gpu_coupled_r1"
BUILD = T / "outputs" / (TAG + "_build")
EXE = BUILD / "C08GpuPressure.exe"
CUDA = Path(os.environ.get("CUDA_PATH_V11_7", r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7"))
BETA = '''#include <cstdlib>
#include <cstring>
#include <stdexcept>
static double C08Beta(){
  const char* b=std::getenv("C08_PRIVATE_BETA");
  if(b && std::strcmp(b,"0")==0)return 0.;
  if(b && std::strcmp(b,"0.04")==0)return .04;
  throw std::runtime_error("Select private C08 beta 0 or .04.");
}
'''

def translate(name, code):
    if name == "JSph.cpp":
        return BETA+once(modify("JSph", code), "&& gravitycontainer && Cpu &&", "&& gravitycontainer && !Cpu &&")
    if name == "JSphGpu_ker.h":
        return once(code, "float *next; unsigned total; };",
                    "float *next; unsigned total; const float *source,*previous; double beta,dt; };")
    if name == "JSphGpu_ker.cu":
        code = '#include "c08_m0_pressure_row.cuh"\n'+code
        code = once(code,"#ifdef C08_STAGE_TRACE\n    double c08chain=0.;\n#endif","    double c08chain=0.;")
        code = once(code,"#ifdef C08_STAGE_TRACE\n      c08chain=chain;\n#endif","      c08chain=chain;")
        pos=code.index("      const double diagonal=-__dmul_rn(khyd,sumw);")
        end=code.index("\n    }",pos)
        return code[:pos]+'''      const unsigned id=tpi.idp[p1];
      const double diagonal=-__dmul_rn(ki,sumw);
      const double residual=__dadd_rn(__dadd_rn(-__dmul_rn(gamma,theta[p1]),__dmul_rn(ki,lap)),c08chain);
      float next=0.f;
      if(!c08_m0::Correct(false,tpi.source[id],tpi.previous[id],porepress[p1],
        diagonal,residual,tpi.beta,tpi.dt,next)){atomicMin(invalid,p1);return;}
      tpi.next[id]=next;'''+code[end:]
    if name == "JSphGpu.cpp":
        code = once(code,"(TpiEndpoint? TpiNextg: NULL),CaseNp};",
                    "(TpiEndpoint? TpiNextg: NULL),CaseNp,TpiSourceg,TpiPreviousg,C08Beta(),SymplecticDtPre};")
        return BETA+once(code,"    dt=(FixedDt? FixedDt->GetDt(TimeStep,bound): bound);",'''    Log->Printf("C08M0Dt %u %u %.17g %.17g %.17g %.17g %.17g %.17g",unsigned(Nstep+1),unsigned(final),
      SymplecticDtPre,bound,CFLnumber*dt1,CFLnumber*dt2,dtw,DynamicConductivitySpeedMax);
    dt=(FixedDt? FixedDt->GetDt(TimeStep,bound): bound);''')
    code=once(code,"    ApplyPorePressureBoundaries();\n    if(!PorePressPreg && PoreShepardRegularization",
        "    if(HydroMechTpi && TpiEndpoint)ComputeFreeSurfaceTracking();\n    else ApplyPorePressureBoundaries();\n    if(!HydroMechTpi && !PorePressPreg && PoreShepardRegularization")
    code=once(code,"    RunGaugeSystem(TimeStep+stepdt);","    if(!HydroMechTpi)RunGaugeSystem(TimeStep+stepdt);")
    code=once(code,"    else RunCellDivide(true);\n    if(HydroMechTpi)CorrectTpiPressure(stepdt);",
        """    else{
      TpiEndpoint=HydroMechTpi;
      RunCellDivide(true);
      TpiEndpoint=false;
    }
    if(HydroMechTpi){CorrectTpiPressure(stepdt);RunGaugeSystem(TimeStep+stepdt);}""")
    return once(code,"      WriteTpiPressure(PorePressg,TpiNextg,Posxyg,false);\n      ApplyPorePressureBoundaries();",'''      WriteTpiPressure(PorePressg,TpiNextg,Posxyg,false);
      const bool filtered=round==2 && PoreShepardRegularization && (Nstep+1)%PoreShepardInterval==0;
      if(round==2){
        ApplyPorePressureBoundaries();
        if(filtered){
          ComputeDynamicPoreWallStateGpu();ShepardRegularizePorePressure();ComputeDynamicPoreWallStateGpu();
        }
      }
      Log->Printf("C08GpuRound %u %u %u",Nstep+1,round+1,unsigned(filtered));''')

def build():
    BUILD.mkdir()
    command=SRC/"VS/Intermediate/PublicTPI_Release_r1/DualSPHysics.tlog/link.command.1.tlog"
    lines=command.read_text(encoding="utf-16").splitlines()
    head,first=lines[1].rsplit(" ",1)
    objects=[Path(first),*map(Path,lines[2:])]
    assert len(objects)==113 and all(p.is_file() for p in objects)
    cl=shutil.which("cl.exe"); link=shutil.which("link.exe")
    assert cl and link and Path(cl).is_file()
    build_sources={}
    for name in ("JSphGpu_ker.h","JSph.cpp","JSphGpu.cpp","JSphGpuSingle.cpp","JSphGpu_ker.cu"):
        src=SRC/"source"/name
        dst=BUILD/name
        dst.write_text(translate(name,src.read_text(encoding="utf-8-sig")),encoding="utf-8")
        build_sources[name]={"base":sha(src),"private":sha(dst)}
        if dst.suffix==".h":continue
        obj=BUILD/(name+".obj") if dst.suffix==".cu" else dst.with_suffix(".obj")
        include=[str(BUILD),str(T/"support"),str(SRC/"source"),str(CUDA/"include")]
        if dst.suffix==".cu":
            cmd=[str(CUDA/"bin/nvcc.exe"),"-gencode=arch=compute_86,code=sm_86","-gencode=arch=compute_86,code=compute_86",
                 "--use-local-env","-ccbin",str(Path(cl).parent),"-x","cu",*["-I"+p for p in include],"-maxrregcount=0",
                 "--machine","64","--compile","-cudart","static","-use_fast_math","-Xcompiler","/wd4267","-Wno-deprecated-gpu-targets",
                 "-D_WITHGPU","-DWIN32","-D_CONSOLE","-D_VC80_UPGRADE=0x0710","-D_MBCS","-Xcompiler","/EHsc /W3 /nologo /O2 /FS /MT",
                 "-o",str(obj),str(dst)]
        else:
            cmd=[cl,"/c","/nologo","/W3","/O2","/Zi","/D_WITHGPU","/DWIN32","/D_CONSOLE","/D_VC80_UPGRADE=0x0710","/D_MBCS",
                 "/Gm-","/EHsc","/MT","/GS","/fp:precise","/Zc:wchar_t","/Zc:forScope","/Zc:inline","/openmp",
                 "/external:W3","/Gd","/TP","/FC",*["/I"+p for p in include],"/Fo"+str(obj),"/Fd"+str(BUILD/"C08.pdb"),str(dst)]
        with (BUILD/(name+".log")).open("xb") as out:
            subprocess.run(cmd,cwd=SRC/"VS",stdout=out,stderr=subprocess.STDOUT,check=True)
        i=[p.name.lower() for p in objects].index(obj.name.lower())
        objects[i]=obj
    for key,suffix in (("OUT","exe"),("PDB","pdb"),("LTCGOUT","iobj"),("IMPLIB","lib")):
        head,n=re.subn("/"+key+r':"[^"]+"',lambda _: '/'+key+':"'+str(EXE.with_suffix("."+suffix))+'"',head)
        assert n==1
    rsp=BUILD/"link.rsp"
    rsp.write_text(head+"\n"+"\n".join('"'+str(p)+'"' for p in objects),encoding="utf-8")
    with (BUILD/"link.log").open("xb") as out:
        subprocess.run([link,"@"+str(rsp)],cwd=SRC/"VS",stdout=out,stderr=subprocess.STDOUT,check=True)
    for name in ("ChronoEngine.dll","dsphchrono.dll","vcomp140.dll","DsphConfig.xml"):
        shutil.copy2(RELEASE/name,BUILD/name)
    (BUILD/"build.json").write_text(json.dumps(dict(executable=sha(EXE),sources=build_sources,
        gpu_row=sha(T/"support/c08_m0_pressure_row.cuh"),link_project=str(command),objects=len(objects)),indent=2))

def run(action):
    beta="0.04" if action=="b004" else "0"
    steps=2 if action=="memcheck" else 42
    dest=T/"outputs"/(TAG+"_"+action)
    log=T/"logs"/(dest.name+".console.log")
    if dest.exists() or log.exists():raise FileExistsError(dest)
    cmd=[str(EXE),"-gpu","-stable","-mdbc_freeslip",str(T/"outputs"/(CPU_TAG+"_seed")/SEED.name),
         str(dest),"-dirdataout","data","-svres","-nsteps:"+str(steps)]
    if action=="memcheck":
        cmd=[str(CUDA/"compute-sanitizer/compute-sanitizer.exe"),"--tool","memcheck","--error-exitcode","93",*cmd]
    with log.open("xb") as stream:
        r=subprocess.run(cmd,cwd=T.parent,env=dict(os.environ,C08_PRIVATE_BETA=beta),stdout=stream,stderr=subprocess.STDOUT)
    (T/"logs"/(dest.name+".call.json")).write_text(json.dumps(dict(command=cmd,returncode=r.returncode,beta=beta),indent=2))
    r.check_returncode()

if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",choices=("build","memcheck","b0","b004"))
    args=ap.parse_args()
    if args.action=="build":build()
    else:run(args.action)


"""Private coupled C08 M0 gravity-start window, built from the official CPU Release objects."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
REPO = T.parents[3]
SRC = REPO / "src"
INT = SRC / "VS/Intermediate/PublicTPI_ReleaseCPU_r1"
TAG = "c08_m0_coupled_r1"
BUILD = T / "outputs" / (TAG + "_build")
SEED = T / "outputs/c08_h18_wend_psi0_pre_r2"
EXE = BUILD / "C08Pressure.exe"
RELEASE = REPO / "bin/windows"


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Source context changed: " + old[:100])
    return text.replace(old, new)


def modify(name, text):
    if name == "JSph":
        # The candidate may run only the actual unreleased gravity container,
        # with a bounded step cap and the original materials, grid and switches.
        at = "    if(HydroMechTpi){\n      const bool column="
        return once(text, at, '''    const bool c08Probe=HydroMechTpi && gravitycontainer && Cpu && !WithMpi
      && TStep==STEP_Symplectic && TKernel==KERNEL_Wendland && !PartBegin && !InOut
      && GravityPreload && GravityPreloadTime==10. && !GravityPreloadReleased && !IsGravityPreloadHandoff()
      && !GravityPreloadKeepBedOverlap && !GravityPreloadElasticSource
      && HydroMechFreeSeepage && !HydroMechDrainage && !NoPenetration && !ArtificialStress && !SoilHourglassXi
      && HydroMechConductivityModel==1 && HydroMechConductivityCk==2. && SoilCte.dlt==0
      && PoreShepardRegularization && PoreShepardInterval==40 && SoilDamping && HydroMechInitMode==HMINIT_ConstantZ
      && CaseNfluid==5000 && CaseNfixed==2060 && CaseNp==7060 && FixedDt->GetFixedValue()==5e-6
      && cfg->NstepsBreak>0 && cfg->NstepsBreak<=42;
    if(!c08Probe)Run_Exceptioon("Private C08 check requires its closed-wall bounded PRE.");
    if(HydroMechTpi && !c08Probe){
      const bool column=''').replace('history->SetvText("Scheme","P3_B_alpha_half_beta_zero");',
           'history->SetvText("Scheme",C08Beta() ? "P3_B_alpha_half_beta_0p04" : "P3_B_alpha_half_beta_zero");')
    if name == "JSphCpu":
        start=text.index("    if(TpiEndpoint){\n      //-The complete M=0")
        end=text.index("    double rate=",start)
        text=text[:start]+'''    double chain=0.;
'''+text[end:]
        text=once(text,"      const double chain=scale*", "      chain=scale*")
        old="    if(!std::isfinite(rate) || fabs(rate)>FLT_MAX)invalid++;"
        start=text.index(old,text.index("void JSphCpu::ComputeDynamicPorePressureRateCpuT"))
        text=text[:start]+'''    if(TpiEndpoint){
      const unsigned id=Idpc[p1];
      const double q=double(PorePressc[p1]), diagonal=-ki*sumweights;
      const double residual=-gamma*PoroThetac[p1]+ki*lap+chain;
      const double capacity=(TpiSource[id]<0.f ? C08Beta()/SymplecticDtPre : 0.);
      double predicted;
      if(!tpi_pressure::Predict(tpi_pressure::Predictor::Linear,TpiSource[id],TpiPrevious[id],predicted)
        || diagonal<=0. || !tpi_pressure::Endpoint(false,q,diagonal+capacity,
           residual+capacity*(predicted-q),TpiNext[id]))invalid++;
    }
'''+text[start:]
        return once(text,"    dt=(FixedDt? FixedDt->GetDt(TimeStep,bound): bound);",'''    Log->Printf("C08M0Dt %u %u %.17g %.17g %.17g %.17g %.17g %.17g",unsigned(Nstep+1),unsigned(final),
      SymplecticDtPre,bound,CFLnumber*dt1,CFLnumber*dt2,dtw,DynamicConductivitySpeedMax);
    dt=(FixedDt? FixedDt->GetDt(TimeStep,bound): bound);''')
    # Avoid a pressure projection/filter at the temporary endpoint guess.
    # Half-time RunCellDivide keeps the ordinary classification and wall refresh.
    text=once(text,"    ApplyPorePressureBoundaries();\n    if(!PorePressPrec && PoreShepardRegularization",'''    if(HydroMechTpi && TpiEndpoint)ComputeFreeSurfaceTracking();
    else ApplyPorePressureBoundaries();
    if(!HydroMechTpi && !PorePressPrec && PoreShepardRegularization''')
    text=once(text,"    else RunCellDivide(true);\n    if(HydroMechTpi){",'''    else{
      TpiEndpoint=HydroMechTpi;
      RunCellDivide(true);
      TpiEndpoint=false;
    }
    if(HydroMechTpi){''')
    start=text.index("      ApplyPorePressureBoundaries();",text.index("void JSphCpuSingle::CorrectTpiPressure("))
    end=text.index("\n    }\n  }\n  catch",start)
    return text[:start]+'''      unsigned count=0,negative=0,fs=0,positive=0;
      for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p])){
        count++;
        const unsigned id=Idpc[p];
        if(!std::isfinite(PorePressc[p]) || PorePressc[p]!=TpiNext[id])
          Run_Exceptioon("C08 endpoint lost its updated soil pressure.");
        if(TpiSource[id]<0.f)negative++;
        if(IsFreeSurfaceParticle(p,Codec,FSTypec)){
          fs++; if(PorePressc[p]>0.f)positive++;
        }
      }
      if(count!=CaseNfluid)Run_Exceptioon("C08 endpoint material count.");
      const bool filtered=(round==2 && PoreShepardRegularization && (Nstep+1)%PoreShepardInterval==0);
      if(round==2){
        ApplyPorePressureBoundaries();
        for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p])){
          const float q=TpiNext[Idpc[p]];
          const float expected=IsFreeSurfaceParticle(p,Codec,FSTypec) && q>0 ? 0.f : q;
          if(PorePressc[p]!=expected)Run_Exceptioon("C08 completed seepage projection mismatch.");
        }
        if(filtered){
          ComputeDynamicPoreWallStateCpu();ShepardRegularizePorePressure();ComputeDynamicPoreWallStateCpu();
        }
      }
      Log->Printf("C08M0Round %u %u %.17g %u %u %u %u %u %u",unsigned(Nstep+1),round+1,C08Beta(),
        count,negative,fs,positive,(round==2 ? positive : 0u),unsigned(filtered));'''+text[end:]


def sha(p):
    with p.open("rb") as fin:
        return hashlib.file_digest(fin, "sha256").hexdigest()


def build():
    BUILD.mkdir()
    command = INT / "DualSPHysics.tlog/link.command.1.tlog"
    lines = command.read_text(encoding="utf-16").splitlines()
    head,first = lines[1].rsplit(" ",1)
    objects=[Path(first), *map(Path,lines[2:])]
    assert len(objects)==87 and all(x.is_file() for x in objects)
    header = '''#include <cstdlib>
#include <cstring>
#include <stdexcept>
static double C08Beta(){
  const char* value=std::getenv("C08_PRIVATE_BETA");
  if(value && !std::strcmp(value,"0"))return 0.;
  if(value && !std::strcmp(value,"0.04"))return 0.04;
  throw std::runtime_error("Private C08 beta must be 0 or 0.04.");
}
'''
    cl = shutil.which("cl.exe"); link = shutil.which("link.exe")
    assert cl and link and os.environ.get("LIB") and os.environ.get("INCLUDE")
    provenance={}
    for name in ("JSph","JSphCpu","JSphCpuSingle"):
        baseline=SRC/"source"/(name+".cpp")
        translated=BUILD/(name+".cpp")
        translated.write_text(header+modify(name,baseline.read_text(encoding="utf-8-sig")),"utf-8")
        obj=BUILD/(name+".obj")
        cmd=[cl,"/c","/nologo","/W3","/O2","/Zi","/DWIN32","/D_CONSOLE","/D_VC80_UPGRADE=0x0710","/D_MBCS",
             "/Gm-","/EHsc","/MT","/GS","/fp:precise","/Zc:wchar_t","/Zc:forScope","/Zc:inline","/openmp",
             "/external:W3","/Gd","/TP","/FC","/I"+str(SRC/"source"),"/Fo"+str(obj),"/Fd"+str(BUILD/"C08.pdb"),str(translated)]
        with (BUILD/(name+".log")).open("xb") as log:
            subprocess.run(cmd,cwd=SRC/"VS",stdout=log,stderr=subprocess.STDOUT,check=True)
        idx=[p.name.lower() for p in objects].index(obj.name.lower())
        objects[idx]=obj
        provenance[name]={"public":sha(baseline),"test":sha(translated)}
    # Reuse the authoritative object order and libraries; redirect all mutable linker outputs.
    import re
    for key,suffix in (("OUT","exe"),("PDB","pdb"),("LTCGOUT","iobj"),("IMPLIB","lib")):
        head,n=re.subn("/"+key+r':"[^"]+"',lambda _: '/'+key+':"'+str(EXE.with_suffix("."+suffix))+'"',head)
        assert n==1
    rsp=BUILD/"link.rsp"
    rsp.write_text(head+"\n"+"\n".join('"'+str(o)+'"' for o in objects),"utf-8")
    with (BUILD/"link.log").open("xb") as log:
        subprocess.run([link,"@"+str(rsp)],cwd=SRC/"VS",stdout=log,stderr=subprocess.STDOUT,check=True)
    for name in ("ChronoEngine.dll","dsphchrono.dll","vcomp140.dll","DsphConfig.xml"):
        shutil.copy2(RELEASE/name,BUILD/name)
    (BUILD/"build.json").write_text(json.dumps({"git":subprocess.check_output(["git","rev-parse","HEAD"],cwd=SRC,text=True).strip(),
        "executable":sha(EXE),"sources":provenance,"objects":len(objects),"original_link_command":str(command)},indent=2))


def prepare():
    seed=T/"outputs"/(TAG+"_seed")
    seed.mkdir()
    name=SEED.name
    tree=ET.parse(SEED/(name+".xml"))
    special=tree.find("execution/special"); hydro=special.find("hydromechanics")
    hydro.find("HydroMechDynamicSeepage").tag="HydroMechModel"
    hydro.find("HydroMechModel").set("value","2")
    for tag,value in (("HydroMechTopLoadMode","0"),("HydroMechDrainage","0"),("HydroMechFreeSeepage","1")):
        e=hydro.find(tag); assert e.get("value")==value; hydro.remove(e)
    ET.SubElement(special,"drainage",mode="freeSeepage")
    tree.find("execution/parameters/parameter[@key='TimeOut']").set("value","0.000001")
    xml=T/"configs"/(TAG+".xml")
    if xml.exists():raise FileExistsError(xml)
    tree.write(xml,encoding="utf-8",xml_declaration=True)
    shutil.copy2(xml,seed/(name+".xml"))
    for suffix in (".bi4","_Normals.nbi4"):
        shutil.copy2(SEED/(name+suffix),seed/(name+suffix))


def run(beta):
    dest=T/"outputs"/(TAG+("_b0" if beta=="0" else "_b004"))
    log=T/"logs"/(dest.name+".console.log")
    if dest.exists() or log.exists():raise FileExistsError(dest)
    env=dict(os.environ,C08_PRIVATE_BETA=beta)
    cmd=[str(EXE),"-cpu","-ompthreads:1","-stable","-mdbc_freeslip",
         str(T/"outputs"/(TAG+"_seed")/SEED.name),str(dest),"-dirdataout","data","-svres","-nsteps:42"]
    with log.open("xb") as stream:
        p=subprocess.run(cmd,cwd=T.parent,env=env,stdout=stream,stderr=subprocess.STDOUT)
    (T/"logs"/(dest.name+".call.json")).write_text(json.dumps(dict(command=cmd,returncode=p.returncode,beta=beta),indent=2))
    p.check_returncode()


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",choices=("build","prepare","b0","b004"))
    action=ap.parse_args().action
    if action=="build":build()
    elif action=="prepare":prepare()
    else:run("0" if action=="b0" else "0.04")

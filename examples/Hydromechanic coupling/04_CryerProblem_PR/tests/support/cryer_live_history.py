"""Attach the live committed pressure history to private CPU and GPU Cryer PARTs."""
import argparse
import csv
import os
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from cryer_drain_schema_r1 import old, private_source, tag as base_tag
from cryer_row_gpu_r1 import call, load, need, save
from cryer_xml_prepare_r1 import edit, replace

NAME = "cryer_livehist_{}_r1"
SUPPORT = Path(__file__).resolve().parent
INCLUDE = '#include "CryerTpiPartHistory.h"'
CPU = """
bool cryer_history::Attach(JPartDataBi4& file,bool noRtimes){
  using namespace upl_tpi_cpu_r1;
  if(!Enabled())return false;
  const State& s=state;
  Require(s.ready && !s.pending && !s.endpoint && !s.initialStep,"CPU pressure transaction open");
  if(!s.commits){
    Require(file.GetPart()->GetvUint("Cpart")==0,"Cold history after initial frame");
    return false;
  }
  Require(s.endpointWrites==3*s.commits && s.soilCount==file.Get_CaseNfluid()
    && s.previous.size()==s.nativeCount && s.fixedCount==file.Get_CaseNfixed(),
    "CPU pressure history owner set or completed rounds differ");
  std::vector<unsigned> ids(s.soilCount);
  for(unsigned i=0;i<ids.size();i++){
    ids[i]=s.fixedCount+i;
    Require(IsSoil(ids[i]),"Missing CPU material owner");
  }
  Write(file,noRtimes,s.commits,s.sourceTime,s.lastEnd,s.dt,ids,
    s.previous.data()+s.fixedCount,s.soilCount);
  return true;
}
"""
GPU = """
bool cryer_history::Attach(JPartDataBi4& file,bool noRtimes){
  using namespace upl_tpi_cryer_gpu_r1;
  if(!Enabled())return false;
  const State& s=state;
  Require(s.ready && !s.pending && !s.endpoint,"GPU pressure transaction open");
  if(!s.commits){
    Require(file.GetPart()->GetvUint("Cpart")==0,"Cold history after initial frame");
    return false;
  }
  Require(s.endpointWrites==3*s.commits && s.d.fixed==file.Get_CaseNfixed()
    && s.d.total==file.Get_Npok(),"GPU pressure history owner set or completed rounds differ");
  const unsigned count=s.d.total-s.d.fixed;
  std::vector<unsigned> ids(count);
  for(unsigned i=0;i<count;i++)ids[i]=s.d.fixed+i;
  std::vector<float> previous(count);
  Cuda(cudaMemcpy(previous.data(),s.d.previous+s.d.fixed,sizeof(float)*count,cudaMemcpyDeviceToHost));
  Write(file,noRtimes,s.commits,s.sourceTime,s.lastEnd,s.dt,ids,previous.data(),count);
  return true;
}
"""


def build(backend):
    name=NAME.format(backend)
    source=old.OUT/(name+"_source")
    shutil.copytree(private_source(backend),source)
    units=source/"source" if backend=="cpu" else source
    shutil.copyfile(SUPPORT/"CryerTpiPartHistory.h",units/"CryerTpiPartHistory.h")
    def insert_writer(text):
        hook="""      const bool hasHistory=cryer_history::Attach(*DataBi4,NoRtimes);
      DataBi4->SaveFilePart();
      if(hasHistory)DataBi4->GetPart()->RemoveItem("TpiPressureHistory");"""
        text=replace(text,'#include "JPartDataBi4.h"', '#include "JPartDataBi4.h"\n'+INCLUDE)
        return replace(text,"      DataBi4->SaveFilePart();",hook)
    edit(units/"JSph.cpp",insert_writer)
    unit=units/("JSphCpuSingle.cpp" if backend=="cpu" else "JSphGpu.cpp")
    edit(unit,lambda text:text+"\n"+INCLUDE+"\n"+(CPU if backend=="cpu" else GPU))
    old.build(backend,name,source)


def run(backend,profile):
    name=NAME.format(backend)
    label=name+"_"+profile
    out=old.OUT/label
    record=old.LOG/(label+".call.json")
    console=old.LOG/(label+".console.log")
    need(not out.exists() and not record.exists() and not console.exists(),"Existing run or output")
    model="model1" if profile=="model1" else "model2"
    prefix=old.OUT/(base_tag(backend)+"_"+model+"_seed")/old.SEED_NAME
    steps=4 if profile=="dense4" else 2
    if steps==4:
        target=old.OUT/(label+"_seed")/old.SEED_NAME
        target.parent.mkdir()
        tree=ET.parse(prefix.with_suffix(".xml"))
        par=tree.find("execution/parameters/parameter[@key='TimeOut']")
        need(float(par.get("value"))==2.**-13,"Original 64-step output interval")
        par.set("value",str(2.**-19))
        tree.write(target.with_suffix(".xml"),encoding="utf-8",xml_declaration=True)
        shutil.copyfile(prefix.with_suffix(".bi4"),target.with_suffix(".bi4"))
        prefix=target
    suffix="_DebugCPU" if backend=="cpu" else "_Release"
    product=load(old.LOG/(name+suffix+".build.json"))
    exe=Path(product["program"]["path"])
    need(product["passed"] and exe.stat().st_size==product["program"]["bytes"],"Private build")
    cmd=[str(exe),"-"+backend]
    if backend=="cpu":cmd.append("-ompthreads:8")
    cmd.extend(["-stable",str(prefix),str(out),"-dirdataout","data","-svres","-nsteps:"+str(steps)])
    env={k:v for k,v in os.environ.items() if not k.upper().startswith("UPL_TPI")}
    result=call(cmd,exe.parent,env,console)
    save(record,result)
    need(result["win32_exit"]==result["popen_exit"]==0,"Solver failed: "+str(console))
    with (out/"Run.csv").open(encoding="utf-8-sig",newline="") as f:
        row,=csv.DictReader(f,delimiter=";")
    need(int(row["Steps"])==steps and int(row["PartsOut"])==0,"Wrong solver extent")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=["build","run"])
    p.add_argument("backend",choices=["cpu","gpu"])
    p.add_argument("profile",nargs="?",choices=["model1","model2","dense4"])
    args=p.parse_args()
    if args.action=="build":build(args.backend)
    elif args.profile:run(args.backend,args.profile)
    else:p.error("run requires a profile")

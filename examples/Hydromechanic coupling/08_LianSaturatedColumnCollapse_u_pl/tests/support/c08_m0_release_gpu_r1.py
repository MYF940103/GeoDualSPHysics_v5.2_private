"""C08 real GPU wall retirement. Retain coupled CUDA objects; change two host TUs."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import c08_m0_gpu_coupled_r1 as gpu
import c08_m0_release_short_r1 as cpu

TAG="c08_m0_release_gpu_r1"
ROOT=gpu.T/"outputs"/(TAG+"_build")
EXE=ROOT/"C08GpuReleaseWall.exe"
ONCE=gpu.once

OBS=r"""  struct Row {float pressure,previous,p0,kappa; double J;tsymatrix3d stress;unsigned fs;};
  const auto snapshot=[&](){
    std::vector<unsigned> ids(Np),fs(Np);
    std::vector<float> pressure(Np),previous(CaseNp),p0(Np),kappa(Np);
    std::vector<double> j(Np);
    std::vector<tsymatrix3d> stress(Np);
    const auto get=[&](void* host,const void* device,size_t bytes){
      const auto err=cudaMemcpy(host,device,bytes,cudaMemcpyDeviceToHost);
      if(err!=cudaSuccess)Run_Exceptioon(std::string("C08 release snapshot: ")+cudaGetErrorString(err));
    };
    get(ids.data(),Idpg,Np*sizeof(unsigned));get(fs.data(),FSTypeg,Np*sizeof(unsigned));
    get(pressure.data(),PorePressg,Np*sizeof(float));get(previous.data(),TpiPreviousg,CaseNp*sizeof(float));
    get(p0.data(),PorePress0g,Np*sizeof(float));get(kappa.data(),Kplasticg,Np*sizeof(float));
    get(j.data(),PoroJg,Np*sizeof(double));get(stress.data(),Sigmag,Np*sizeof(tsymatrix3d));
    std::vector<Row> result(CaseNfluid);
    std::vector<byte> seen(CaseNfluid,0);
    for(unsigned p=Npb;p<Np;p++){
      const unsigned id=ids[p],slot=id-(CaseNp-CaseNfluid);
      if(slot>=CaseNfluid || seen[slot])Run_Exceptioon("C08 material owner missing or duplicated at release.");
      seen[slot]=1;result[slot]={pressure[p],previous[id],p0[p],kappa[p],j[p],stress[p],fs[p]};
    }
    if(Np-Npb!=CaseNfluid)Run_Exceptioon("C08 release material count.");
    return result;
  };
  const auto before=snapshot();
  TpiEndpoint=true;
  try{BoundChanged=true;RunCellDivide(true);}
  catch(...){TpiEndpoint=false;throw;}
  TpiEndpoint=false;
  const auto after=snapshot();
  unsigned newfs=0,waiting=0;
  for(unsigned i=0;i<CaseNfluid;i++){
    const auto &a=before[i],&b=after[i];
    if(memcmp(&a.pressure,&b.pressure,sizeof(a.pressure)) || memcmp(&a.previous,&b.previous,sizeof(a.previous))
      || memcmp(&a.p0,&b.p0,sizeof(a.p0)) || memcmp(&a.kappa,&b.kappa,sizeof(a.kappa))
      || memcmp(&a.J,&b.J,sizeof(a.J)) || memcmp(&a.stress,&b.stress,sizeof(a.stress)))
      Run_Exceptioon("C08 topology refresh changed committed soil state.");
    if((a.fs!=2 && a.fs!=3) && (b.fs==2 || b.fs==3)){newfs++;if(b.pressure>0.f)waiting++;}
  }
  Log->Printf("C08M0Release %u %.17g %u %u %u %u %u",unsigned(Nstep),TimeStep,retired,Np-Npb,Npb,newfs,waiting);"""


def edit(name,code):
    if name=="JSph":
        return ONCE(cpu.release_modify(name,code),"&& gravitycontainer && Cpu &&","&& gravitycontainer && !Cpu &&")
    coupled=gpu.translate(name+".cpp",code)
    return ONCE(coupled,"  BoundChanged=true;RunCellDivide(true);\n  if(Np!=oldnp-retired",OBS+"\n  if(Np!=oldnp-retired")


def build():
    # Use the already built baseline physical CUDA and host objects. No GPU runtime work here.
    orig=gpu.BUILD
    receipt=json.loads((orig/"build.json").read_text())
    assert receipt["objects"]==113 and (orig/"JSphGpu_ker.cu.obj").is_file()
    ROOT.mkdir()
    cmd=(orig/"link.rsp").read_text().splitlines()
    assert len(cmd)==114
    head=cmd[0]
    for key,suffix in (("OUT","exe"),("PDB","pdb"),("LTCGOUT","iobj"),("IMPLIB","lib")):
        head,count=re.subn("/"+key+r':"[^"]+"',lambda _: '/'+key+':"'+str(EXE.with_suffix("."+suffix))+'"',head)
        assert count==1
    objects=[Path(v.strip('"')) for v in cmd[1:]]
    assert all(obj.is_file() for obj in objects)
    cl=shutil.which("cl.exe");link=shutil.which("link.exe")
    assert cl and link
    recorded={}
    for name in ("JSph","JSphGpuSingle"):
        public=gpu.SRC/"source"/(name+".cpp")
        private=ROOT/(name+".cpp")
        code=edit(name,public.read_text(encoding="utf-8-sig"))
        private.write_text((gpu.BETA if name=="JSph" else "")+code,"utf-8")
        recorded[name]={"original":gpu.sha(public),"changed":gpu.sha(private)}
        obj=private.with_suffix(".obj")
        args=[cl,"/c","/nologo","/W3","/O2","/Zi","/D_WITHGPU","/DWIN32","/D_CONSOLE","/D_VC80_UPGRADE=0x0710","/D_MBCS",
              "/Gm-","/EHsc","/MT","/GS","/fp:precise","/Zc:wchar_t","/Zc:forScope","/Zc:inline","/openmp","/external:W3",
              "/Gd","/TP","/FC","/I"+str(orig),"/I"+str(gpu.SRC/"source"),"/I"+str(gpu.CUDA/"include"),
              "/Fo"+str(obj),"/Fd"+str(ROOT/"private.pdb"),str(private)]
        with (ROOT/(name+".log")).open("xb") as log:
            subprocess.run(args,cwd=gpu.SRC/"VS",stdout=log,stderr=subprocess.STDOUT,check=True)
        index=objects.index(orig/obj.name)
        objects[index]=obj
    rsp=ROOT/"link.rsp"
    rsp.write_text(head+"\n"+"\n".join('"'+str(obj)+'"' for obj in objects),"utf-8")
    with (ROOT/"link.log").open("xb") as log:
        subprocess.run([link,"@"+str(rsp)],cwd=gpu.SRC/"VS",stdout=log,stderr=subprocess.STDOUT,check=True)
    for filename in ("ChronoEngine.dll","dsphchrono.dll","vcomp140.dll","DsphConfig.xml"):
        shutil.copy2(orig/filename,ROOT/filename)
    (ROOT/"build.json").write_text(json.dumps(dict(original_build=str(orig/"build.json"),original_objects_reused=111,
        total=113,exe=gpu.sha(EXE),changed=recorded),indent=2))


def run(label):
    beta="0.04" if label=="b004" else "0"
    dest=gpu.T/"outputs"/(TAG+"_"+label)
    out=gpu.T/"logs"/(dest.name+".console.log")
    if dest.exists() or out.exists():raise FileExistsError(dest)
    args=[str(EXE),"-gpu","-stable","-mdbc_freeslip",str(gpu.T/"outputs"/(cpu.TAG+"_seed")/gpu.SEED.name),
          str(dest),"-dirdataout","data","-svres","-nsteps:"+str(cpu.STEPS)]
    if label=="memcheck":
        args=[str(gpu.CUDA/"compute-sanitizer/compute-sanitizer.exe"),"--tool","memcheck","--error-exitcode","93",*args]
    with out.open("xb") as log:
        proc=subprocess.run(args,cwd=gpu.T.parent,env=dict(os.environ,C08_PRIVATE_BETA=beta),stdout=log,stderr=subprocess.STDOUT)
    (gpu.T/"logs"/(dest.name+".call.json")).write_text(json.dumps(dict(command=args,returncode=proc.returncode,beta=beta),indent=2))
    proc.check_returncode()


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("build","memcheck","b0","b004"))
    action=parser.parse_args().action
    if action=="build":build()
    else:run(action)

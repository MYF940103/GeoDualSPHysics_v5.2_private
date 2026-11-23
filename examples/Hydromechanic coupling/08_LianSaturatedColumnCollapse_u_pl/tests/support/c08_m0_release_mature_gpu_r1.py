"""Transfer the certified 10 s finite-Kw C08 PRE, cold-start M0, hold 1 ms, then remove the true wall."""
import argparse
import json
import os
import subprocess
import c08_m0_coupled_hold_r1 as hold
import c08_m0_release_gpu_r1 as rel
import c08_m0_gpu_coupled_r1 as gpu

TAG="c08_m0_release_mature_gpu_r1"
ROOT=gpu.T/"outputs"/(TAG+"_build")
EXE=ROOT/"C08MatureWall.exe"
original_edit=rel.edit
ONCE=gpu.once
SOURCE=2_000_000
OPEN=SOURCE+200
CAPS={"short":OPEN+8,"w03":OPEN+6000}


def edit(name,code):
    text=original_edit(name,code)
    if name=="JSph":
        text=ONCE(text,"GravityPreloadTime==.0002","GravityPreloadTime==10.")
        text=ONCE(text,"cfg->NstepsBreak==48","(cfg->NstepsBreak==2000208 || cfg->NstepsBreak==2006200)")
        text=ONCE(text,"40-step PRE plus 8-step release.","same-material PRE plus 200-step M0 hold and bounded release.")
        text=ONCE(text,"; next loop releases the right wall once.",". Cold M0 holds the wall for 200 complete steps.")
        return ONCE(text,"if(!GravityPreloadElasticSource && !IsGravityPreloadHandoff() && !GravityPreloadReleased",
                    "if(!HydroMechTpi && !GravityPreloadElasticSource && !IsGravityPreloadHandoff() && !GravityPreloadReleased")
    text=ONCE(text,"  RestoreGravityPreloadClock(source);",r"""  // Verify the actual sorted device state after the final primary-state restoration.
  ParticlesDataDown(Np,0,true,false);
  const auto get=[&](void* dst,const void* ptr,size_t bytes){
    const auto e=cudaMemcpy(dst,ptr,bytes,cudaMemcpyDeviceToHost);if(e!=cudaSuccess)
      Run_Exceptioon(std::string("C08 PRE verification download: ")+cudaGetErrorString(e));
  };
  std::vector<double> j(Np),theta(Np);std::vector<unsigned> fs(Np);std::vector<float> div(Np),p0(Np),pore(Np),kp(Np);
  std::vector<tfloat3> normal_read(Np);std::vector<tsymatrix3d> stress(Np);
  get(j.data(),PoroJg,Np*sizeof(double));get(theta.data(),PoroThetag,Np*sizeof(double));get(fs.data(),FSTypeg,Np*sizeof(unsigned));
  get(normal_read.data(),FSNormalg,Np*sizeof(tfloat3));get(div.data(),PosDivg,Np*sizeof(float));
  get(p0.data(),PorePress0g,Np*sizeof(float));get(pore.data(),PorePressg,Np*sizeof(float));
  get(kp.data(),Kplasticg,Np*sizeof(float));get(stress.data(),Sigmag,Np*sizeof(tsymatrix3d));
  for(unsigned p=0;p<Np;p++){
    const unsigned s=source.ById.at(Idp[p]);
    const tdouble3 pos={Posxy[p].x,Posxy[p].y,Posz[p]};
    const tdouble3 kk={stress[p].xx,stress[p].yy,stress[p].zz},ij={stress[p].xy,stress[p].yz,stress[p].xz};
    if(memcmp(&pos,&source.Pos[s],sizeof(pos)) || memcmp(Velrhop+p,&source.VelRhop[s],sizeof(tfloat4))
       || memcmp(&kk,&source.SigmaKK[s],sizeof(kk)) || memcmp(&ij,&source.SigmaIJ[s],sizeof(ij))
       || memcmp(&kp[p],&source.Kplastic[s],sizeof(float)) || memcmp(&pore[p],&source.PorePress[s],sizeof(float))
       || memcmp(&p0[p],&source.PorePress0[s],sizeof(float)) || memcmp(&j[p],&source.J[s],sizeof(double))
       || memcmp(&theta[p],&source.Theta[s],sizeof(double)) || fs[p]!=source.FSType[s]
       || memcmp(&normal_read[p],&source.FSNormal[s],sizeof(tfloat3)) || memcmp(&div[p],&source.PosDiv[s],sizeof(float)))
      Run_Exceptioon("C08 device PRE differs before first M0 substage.");
  }
  Log->Printf("C08Mature imported %u fixed %u material %u",Np,Npb,Np-Npb);
  RestoreGravityPreloadClock(source);""")
    text=ONCE(text,"  if(HydroMechTpi)PrepareTpiPressure(PorePressg,Posxyg,true);\n  RunGravityPreloadHandoffGpu();",r"""  GravityPreloadStateFile=std::getenv("C08_MATURE_PRE");
  if(GravityPreloadStateFile.empty())Run_Exceptioon("C08 requires the schema2 PRE.");
  RunGravityPreloadHandoffGpu();
  GravityPreloadStateFile.clear();
  if(Nstep!=2000000 || GravityPreloadReleased || Np!=7060 || Npb!=2060 || SymplecticDtPre!=5e-6)
    Run_Exceptioon("C08 original PRE clock or registry changed.");
  PrepareTpiPressure(PorePressg,Posxyg,true); // Equal p_n / p_previous from the imported finite-Kw material.
  GravityPreloadStep=2000200;GravityPreloadTime=TimeStep;
  for(unsigned i=0;i<200;i++)GravityPreloadTime+=SymplecticDtPre;
  Log->Printf("C08Mature history=cold_actual_p source=%.17g M0_wall_hold=200 release=%.17g",TimeStep,GravityPreloadTime);""")
    text=ONCE(text,"  if(!IsGravityPreloadHandoff())SaveData();","  // The certified PRE is the initial physical record.")
    text=ONCE(text,"  if(!IsGravityPreloadHandoff()){PartNstep=-1;Part++;}","  PartNstep=int(Nstep)-1;Part++;")
    # Record all source endpoints enclosing the wall event and regular 0.5ms after the event.
    return ONCE(text,"if(TimeStep>=TimePartNext || partoutstop || TimeStep>=TimeMax || (NstepsBreak",
        "if(Nstep<2000208 || (Nstep+1-2000200)%100==0 || partoutstop || TimeStep>=TimeMax || (NstepsBreak")


def run(beta,window):
    cap=CAPS[window]
    tag=TAG+"_"+window+("_b004" if beta else "_b0")
    out=gpu.T/"outputs"/tag
    console=gpu.T/"logs"/(tag+".console.log")
    if out.exists() or console.exists():raise FileExistsError(out)
    args=[str(EXE),"-gpu","-stable","-mdbc_freeslip",str(hold.SRC/gpu.SEED.name),str(out),
          "-dirdataout","data","-svres","-nsteps:"+str(cap)]
    with console.open("xb") as log:
        result=subprocess.run(args,cwd=gpu.T.parent,env=dict(os.environ,C08_PRIVATE_BETA="0.04" if beta else "0",
                              C08_MATURE_PRE=str(hold.PRE)),stdout=log,stderr=subprocess.STDOUT)
    (gpu.T/"logs"/(tag+".call.json")).write_text(json.dumps(dict(command=args,PRE=str(hold.PRE),
        capped_step=cap,returncode=result.returncode,negative_storage_beta=beta),indent=2))
    result.check_returncode()


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("build","short","w03"))
    parser.add_argument("--beta",choices=("0","0.04"),default="0")
    args=parser.parse_args()
    if args.action=="build":
        rel.ROOT,rel.EXE,rel.edit=ROOT,EXE,edit
        rel.build()
    else:
        run(float(args.beta),args.action)

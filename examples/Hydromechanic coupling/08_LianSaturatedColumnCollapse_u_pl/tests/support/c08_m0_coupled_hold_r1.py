"""Continue gravity with the wall retained for 1 ms, cold M0, certified finite-Kw PRE."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

import c08_m0_coupled_r1 as base

TAG="c08_m0_coupled_hold_r1"
BUILD=base.T/"outputs"/(TAG+"_build")
OUT=base.T/"outputs"/TAG
PRE=base.SEED/"data/Part_1000.bi4"
SRC=base.T/"outputs"/(TAG+"_seed")
CAP=2000200
modify_cold=base.modify
once=base.once


def modify(name, original):
    text=modify_cold(name,original)
    if name=="JSph":
        text=once(text,"cfg->NstepsBreak>0 && cfg->NstepsBreak<=42","cfg->NstepsBreak==2000200")
        return once(text,"; next loop releases the right wall once.",". Private M0 hold retains the full wall.")
    if name=="JSphCpuSingle":
        text=once(text,"  copystate();\n  RestoreGravityPreloadClock(source);",'''  copystate();
  for(unsigned p=0;p<Np;p++){
    const unsigned s=source.ById[Idpc[p]];
    const tdouble3 kk={Sigmac[p].xx,Sigmac[p].yy,Sigmac[p].zz};
    const tdouble3 ij={Sigmac[p].xy,Sigmac[p].yz,Sigmac[p].xz};
    if(memcmp(Posc+p,&source.Pos[s],sizeof(tdouble3)) || memcmp(Velrhopc+p,&source.VelRhop[s],sizeof(tfloat4))
      || memcmp(&kk,&source.SigmaKK[s],sizeof(kk)) || memcmp(&ij,&source.SigmaIJ[s],sizeof(ij))
      || memcmp(Kplasticc+p,&source.Kplastic[s],sizeof(*Kplasticc))
      || memcmp(PorePressc+p,&source.PorePress[s],sizeof(float)) || memcmp(PorePress0c+p,&source.PorePress0[s],sizeof(float))
      || memcmp(PoroJc+p,&source.J[s],sizeof(double)) || memcmp(PoroThetac+p,&source.Theta[s],sizeof(double))
      || FSTypec[p]!=source.FSType[s] || memcmp(FSNormalc+p,&source.FSNormal[s],sizeof(*FSNormalc))
      || memcmp(PosDivc+p,&source.PosDiv[s],sizeof(*PosDivc)))
      Run_Exceptioon("C08 imported PRE state changed before the first M0 force evaluation.");
  }
  Log->Printf("C08M0Hold import_exact all=%u fixed=%u source_order=by_id before_first_M0_force",Np,Npb);
  RestoreGravityPreloadClock(source);''')
        text=once(text,"  InitRunCpu();\n  RunGravityPreloadHandoffCpu();",'''  InitRunCpu();
  GravityPreloadStateFile=std::getenv("C08_HOLD_SOURCE");
  RunGravityPreloadHandoffCpu();
  GravityPreloadStateFile.clear();
  if(Nstep!=2000000 || GravityPreloadReleased || Npb!=2060 || Np!=7060 || OmpThreads!=1)
    Run_Exceptioon("C08 hold did not recover the original closed PRE.");
  Log->Printf("C08M0Hold imported_completed=%u source_t=%.17g right_wall=retained history=cold_actual_p",unsigned(Nstep),TimeStep);''')
        text=once(text,"  if(!IsGravityPreloadHandoff())SaveData();","  // The original PRE itself is the initial physical record.")
        text=once(text,"  if(!IsGravityPreloadHandoff()){PartNstep=-1;Part++;}","  PartNstep=int(Nstep)-1;Part++;")
        text=once(text,"    if(GravityPreload && !GravityPreloadReleased)RunGravityPreloadRelease();",
             '''    if(!GravityPreload || GravityPreloadReleased || Npb!=2060 || Np!=7060)
      Run_Exceptioon("Unexpected geometry in the 1 ms closed-wall M0 hold.");''')
        # Preserve first two real steps and both sides of the first Shepard update.
        return once(text,"if(TimeStep>=TimePartNext || partoutstop || TimeStep>=TimeMax || (NstepsBreak",
            "if(Nstep==2000000 || Nstep==2000001 || Nstep==2000038 || Nstep==2000040 || Nstep==2000198 || TimeStep>=TimePartNext || partoutstop || TimeStep>=TimeMax || (NstepsBreak")
    begin=text.index("  unsigned invalid=0;",text.index("void JSphCpu::ComputeDynamicPorePressureRateCpuT"))
    text=text[:begin]+text[begin:].replace("  unsigned invalid=0;",'''  unsigned invalid=0,interior=0;
  double sumA2=0.,maxA=0.,sumR2=0.,maxR=0.,sumDp2=0.,maxDp=0.,maxG=0.,minK=DBL_MAX,maxK=0.;
  if(OmpThreads!=1)Run_Exceptioon("The private diagnostic reductions require one CPU thread.");''',1)
    start=text.index("    if(TpiEndpoint){\n      const unsigned id=",begin)
    text=text[:start]+'''    const double R=-gamma*PoroThetac[p1]+ki*lap+chain;
    const double S=-ki*sumweights;
    if(!(S>0.) || !std::isfinite(R))invalid++;
    else{
      const double ax=double(Acec[p1].x)+Gravity.x,ay=double(Acec[p1].y)+Gravity.y,az=double(Acec[p1].z)+Gravity.z;
      const double a2=ax*ax+ay*ay+az*az;sumA2+=a2;maxA=max(maxA,sqrt(a2));
      minK=min(minK,ki);maxK=max(maxK,ki);maxG=max(maxG,fabs(chain));
      if(!IsFreeSurfaceParticle(unsigned(p1),Codec,FSTypec)){
        const double dp=R/S;interior++;sumR2+=R*R;maxR=max(maxR,fabs(R));
        sumDp2+=dp*dp;maxDp=max(maxDp,fabs(dp));
      }
    }
'''+text[start:]
    text=once(text,"          if(TpiEndpoint)sumweights+=w;","          sumweights+=w;")
    start=text.index("  if(ridp){",text.index("PorePressRatec[p1]=float(rate); //-Replace",begin))
    return text[:start]+'''  if(!interior || invalid)Run_Exceptioon("Invalid M0 hold phase.");
  Log->Printf("C08M0HoldR %u %u %u %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g",
    unsigned(Nstep+1),unsigned(TpiEndpoint),interior,sqrt(sumA2/CaseNfluid),maxA,
    sqrt(sumR2/interior),maxR,sqrt(sumDp2/interior),maxDp,maxG,minK,maxK);
'''+text[start:]


def prepare():
    if SRC.exists():raise FileExistsError(SRC)
    SRC.mkdir()
    seed=base.T/"outputs"/("c08_m0_coupled_r1_seed")
    name=base.SEED.name
    root=ET.parse(seed/(name+".xml"))
    root.find("execution/parameters/parameter[@key='TimeOut']").set("value","0.00005")
    xml=base.T/"configs"/(TAG+".xml")
    if xml.exists():raise FileExistsError(xml)
    root.write(xml,encoding="utf-8",xml_declaration=True)
    shutil.copy2(xml,SRC/(name+".xml"))
    for suffix in (".bi4","_Normals.nbi4"):
        shutil.copy2(seed/(name+suffix),SRC/(name+suffix))


def run():
    log=base.T/"logs"/(TAG+".console.log")
    if OUT.exists() or log.exists():raise FileExistsError(OUT)
    env=dict(os.environ,C08_PRIVATE_BETA="0",C08_HOLD_SOURCE=str(PRE))
    cmd=[str(BUILD/"C08Pressure.exe"),"-cpu","-ompthreads:1","-stable","-mdbc_freeslip",
         str(SRC/base.SEED.name),str(OUT),"-dirdataout","data","-svres","-nsteps:"+str(CAP)]
    with log.open("xb") as stream:
        proc=subprocess.run(cmd,cwd=base.T.parent,env=env,stdout=stream,stderr=subprocess.STDOUT)
    (base.T/"logs"/(TAG+".call.json")).write_text(json.dumps(
        dict(command=cmd,PRE=str(PRE),beta=0,returncode=proc.returncode),indent=2))
    proc.check_returncode()


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",choices=("build","prepare","run"))
    act=ap.parse_args().action
    if act=="build":
        base.BUILD=BUILD;base.EXE=BUILD/"C08Pressure.exe";base.modify=modify;base.build()
    elif act=="prepare":prepare()
    else:run()

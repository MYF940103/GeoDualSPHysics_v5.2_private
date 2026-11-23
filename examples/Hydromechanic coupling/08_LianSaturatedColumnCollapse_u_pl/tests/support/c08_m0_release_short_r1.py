"""C08 single-process early right-wall release. Private 48-step CPU test."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

import c08_m0_coupled_r1 as base

TAG = "c08_m0_release_short_r1"
STEPS = 48
TESTS = base.T
BUILD = TESTS / "outputs" / (TAG + "_build")
EXE = BUILD / "C08Pressure.exe"
original_modify = base.modify


def release_modify(name, text):
    text = original_modify(name, text)
    if name == "JSph":
        text = base.once(text, "GravityPreloadTime==10.", "GravityPreloadTime==.0002")
        text = base.once(text, "cfg->NstepsBreak>0 && cfg->NstepsBreak<=42", "cfg->NstepsBreak==48")
        text = base.once(text, "closed-wall bounded PRE.", "bounded 40-step PRE plus 8-step release.")
        text = base.once(text, "  if(!previous || !CaseNfluid || npok!=CaseNp || nout", """  const unsigned removed=GravityPreloadReleased? GravityPreloadIdCount:0;
  if((removed && (GravityPreloadKeepBedOverlap || GravityPreloadIdBegin!=1805 || removed!=255))
    || npok!=CaseNp-removed)Run_Exceptioon("C08: invalid TPI active registry size or boundary.");
  std::vector<byte> seen(CaseNp,0);
  for(unsigned p=0;p<npok;p++){
    const unsigned id=idp[p];
    if(id>=CaseNp || seen[id] || (removed && id>=GravityPreloadIdBegin && id-GravityPreloadIdBegin<removed))
      Run_Exceptioon("C08: absent, duplicate or retired ID in TPI PART.");
    seen[id]=1;
  }
  if(!previous || !CaseNfluid || nout""")
    if name == "JSphCpuSingle":
        old = "  BoundChanged=true;RunCellDivide(true);\n  if(Np!=oldnp-retired"
        text = base.once(text, old, """  struct Committed {float pressure,previous,kappa,p0;double J;tsymatrix3d stress;bool fs;};
  std::vector<Committed> before(CaseNp);
  for(unsigned p=Npb;p<Np;p++){
    const unsigned id=Idpc[p];
    before.at(id)={PorePressc[p],TpiPrevious.at(id),Kplasticc[p],PorePress0c[p],PoroJc[p],Sigmac[p],IsFreeSurfaceParticle(p,Codec,FSTypec)};
  }
  // Refresh topology only. The final pressure round projects the newly exposed material.
  TpiEndpoint=true;
  try{BoundChanged=true;RunCellDivide(true);}
  catch(...){TpiEndpoint=false;throw;}
  TpiEndpoint=false;
  unsigned newfs=0,waiting=0;
  for(unsigned p=Npb;p<Np;p++){
    const unsigned id=Idpc[p];
    const auto& row=before.at(id);
    if(memcmp(&row.pressure,PorePressc+p,sizeof(float)) || memcmp(&row.previous,&TpiPrevious.at(id),sizeof(float))
      || memcmp(&row.kappa,Kplasticc+p,sizeof(float)) || memcmp(&row.p0,PorePress0c+p,sizeof(float))
      || memcmp(&row.J,PoroJc+p,sizeof(double)) || memcmp(&row.stress,Sigmac+p,sizeof(row.stress)))
      Run_Exceptioon("C08: topology refresh changed a committed soil state.");
    if(!row.fs && IsFreeSurfaceParticle(p,Codec,FSTypec)){
      ++newfs;if(PorePressc[p]>0.f)++waiting;
    }
  }
  Log->Printf("C08M0Release %u %.17g %u %u %u %u %u",unsigned(Nstep),TimeStep,retired,Np-Npb,Npb,newfs,waiting);
  if(Np!=oldnp-retired""")
    return text


def prepare():
    seed = TESTS / "outputs" / (TAG + "_seed")
    seed.mkdir()
    xml = TESTS / "configs" / (TAG + ".xml")
    tree = ET.parse(TESTS / "configs/c08_m0_coupled_r1.xml")
    event = tree.find("execution/special/gravitypreload")
    assert event.get("time") == "10.0"
    event.set("time", "0.0002")
    event.set("comment", "Private startup regression: right-wall retirement after 40 completed steps")
    if xml.exists():
        raise FileExistsError(xml)
    tree.write(xml, encoding="utf-8", xml_declaration=True)
    name = base.SEED.name
    shutil.copy2(xml, seed / (name + ".xml"))
    for suffix in (".bi4", "_Normals.nbi4"):
        shutil.copy2(base.SEED / (name + suffix), seed / (name + suffix))


def run(beta):
    label = TAG + ("_b0" if beta == "0" else "_b004")
    dest = TESTS / "outputs" / label
    log = TESTS / "logs" / (label + ".console.log")
    if dest.exists() or log.exists():
        raise FileExistsError(dest)
    args = [str(EXE), "-cpu", "-ompthreads:1", "-stable", "-mdbc_freeslip",
            str(TESTS / "outputs" / (TAG + "_seed") / base.SEED.name),
            str(dest), "-dirdataout", "data", "-svres", "-nsteps:" + str(STEPS)]
    with log.open("xb") as out:
        proc = subprocess.run(args, cwd=TESTS.parent, env=dict(os.environ, C08_PRIVATE_BETA=beta),
                              stdout=out, stderr=subprocess.STDOUT)
    receipt = TESTS / "logs" / (label + ".call.json")
    receipt.write_text(json.dumps(dict(command=args, beta=beta, returncode=proc.returncode), indent=2))
    proc.check_returncode()


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "prepare", "b0", "b004"))
    action=parser.parse_args().action
    if action=="build":
        base.BUILD, base.EXE, base.modify=BUILD, EXE, release_modify
        base.build()
    elif action=="prepare":
        prepare()
    else:
        run("0" if action=="b0" else "0.04")

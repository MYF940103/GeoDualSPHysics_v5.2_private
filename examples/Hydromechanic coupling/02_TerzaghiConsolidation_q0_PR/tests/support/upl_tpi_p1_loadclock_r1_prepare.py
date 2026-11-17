"""Prepare one private CPU/GPU P1 staged-load source tree only; no build or solver."""
from __future__ import annotations
import argparse
import difflib
import json
from pathlib import Path
T=Path(__file__).resolve().parents[1]
L=T/'logs';STAGE='upl_tpi_p1_loadclock_r1'
HEADER=T/'support'/f'{STAGE}.h';NOTE=T/'notes'/f'{STAGE}.md'
BASE={
 'CPU':('upl_tpi_m0_dt_CPU_r2.prepare.json','upl_tpi_m0_dt_DebugCPU_r3.build.json',267),
 'GPU':('upl_tpi_m0_dt_GPU_r2.prepare.json','upl_tpi_m0_dt_Release_r2.build.json',270)}
def need(q,m):
 if not q:raise RuntimeError(m)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def same(e):
 a=stat(e['path']);need(a=={k:e[k]for k in ('path','bytes','mtime_ns')},'Frozen source stat changed: '+e['path']);return a
def write_json(p,d):
 with Path(p).open('x',encoding='utf-8',newline='\n')as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
class Admission:
 def __init__(self,p,backend):
  self.entry=stat(p);self.data=read(p)
  need(self.data.get('stage')==STAGE+'.prepare_admission' and self.data.get('passed')is True
   and self.data.get('prepare_only')is True and self.data.get('backend')==backend,'Independent root source-only admission required')
  self.frozen={str(Path(e['path']).resolve()):e for e in self.data['inputs']};self.used={}
  need(len(self.frozen)==len(self.data['inputs']),'Duplicate admitted input')
 def pin(self,p):
  key=str(Path(p).resolve());need(key in self.frozen,'Consumed input absent from admission: '+key)
  self.used[key]=same(self.frozen[key]);return self.used[key]
 def finish(self):
  for e in self.used.values():same(e)
  same(self.entry);return list(self.used.values())
def once(s,old,new):
 need(s.count(old)==1,'Exact one source anchor required: '+old[:120]);return s.replace(old,new)
def names(backend):
 cpu=backend=='CPU';return ('JSphCpu'if cpu else'JSphGpu','upl_tpi_cpu_r1'if cpu else'upl_tpi_gpu_r1')
def enabled(backend):return STAGE+'::Enabled('+names(backend)[1]+'::Enabled())'
def patch_base(s,backend):
 cls,pressure=names(backend);active=enabled(backend)
 s=once(s,'#include "'+pressure+'.h"','#include "'+pressure+'.h"\n#include "'+STAGE+'.h"')
 old='const double q=(tramp>0 && TimeStep<tramp? q0*max(0.0,TimeStep)/tramp: q0);'
 need(s.count(old)==2,'Both paired load evaluations must be present')
 # CPU source order direct/raw; GPU source order ConstantDataUp(raw)/direct.
 for site in ([0,1]if backend=='CPU'else[1,0]):
  replacement='const double q=('+active+'? '+STAGE+'::Evaluate(this,TimeStep,q0,tramp,'+str(site)+'u): (tramp>0 && TimeStep<tramp? q0*max(0.0,TimeStep)/tramp: q0));'
  s=s.replace(old,replacement,1)
 need(old not in s,'Unpatched paired load site')
 return s
def patch_single(s,backend):
 cls,pressure=names(backend);active=enabled(backend);owner='static_cast<'+cls+'*>(this)'
 s=once(s,'#include "'+pressure+'.h"','#include "'+pressure+'.h"\n#include "'+STAGE+'.h"')
 def hook(phase,dt,enter):
  return '  if('+active+')'+STAGE+'::'+('Enter'if enter else'Leave')+'('+owner+','+str(phase)+'u,TimeStep,Nstep,'+dt+');'
 old='  Interaction_Forces(INTERSTEP_SymPredictor);  //-Interaction.\n  const double ddt_p=DtVariable(false);        //-Calculate dt of predictor step.'
 s=once(s,old,hook(0,'dt',True)+'\n'+old+'\n'+hook(0,'dt',False))
 old='  Interaction_Forces(INTERSTEP_SymCorrector);  //-Interaction.\n  const double ddt_c=DtVariable(true);         //-Calculate dt of corrector step.'
 s=once(s,old,hook(1,'dt',True)+'\n'+old+'\n'+hook(1,'dt',False))
 if backend=='CPU':
  old='        Interaction_Forces(INTERSTEP_SymCorrector); // Extra endpoint evaluation; no solid/J/material update.\n        const double endpointdt=DtVariable(false); // Existing necessary limits retained for this same-dt P1 prototype.'
  new='        if('+active+')'+STAGE+'::Enter('+owner+',2u,TimeStep,Nstep,stepdt);\n'+old+'\n        if('+active+')'+STAGE+'::Leave('+owner+',2u,TimeStep,Nstep,stepdt);'
 else:
  old='        scratch=true;Interaction_Forces(INTERSTEP_SymCorrector);\n        const double endpointdt=DtVariable(false);'
  new='        if('+active+')'+STAGE+'::Enter('+owner+',2u,TimeStep,Nstep,stepdt);\n'+old+'\n        if('+active+')'+STAGE+'::Leave('+owner+',2u,TimeStep,Nstep,stepdt);'
 s=once(s,old,new)
 scheme='std::getenv("UPL_TPI_'+backend+'_R1")'
 old='    if(upl_tpi_m0_dt_r2::Enabled('+pressure+'::Enabled()))upl_tpi_m0_dt_r2::Init('+owner+',DirOut,"'+backend+'",'+scheme+',TimeStep,Nstep,SymplecticDtPre,HydroMechDrainageStartTime);'
 new=old+'\n    if('+active+'){\n      '+STAGE+'::Need(upl_tpi_m0_dt_r2::Enabled('+pressure+'::Enabled()),"Staged load requires the admitted M0 method-specific dt policy");\n      '+STAGE+'::Init('+owner+',DirOut,"'+backend+'",'+scheme+',TimeStep,Nstep,SymplecticDtPre,HydroMechDrainageStartTime);\n      Log->Print("UplTpiP1LoadClockR1: private B load evaluation at original/half/endpoint times; global clock, original P1 pressure, HG and J schedule retained; physical acceptance pending.");\n    }'
 s=once(s,old,new)
 for method,args in [('Saved',owner+',Part,TimeStep,Nstep'),('Finish',owner+',Nstep,TimeStep')]:
  old='  if(upl_tpi_m0_dt_r2::Enabled('+pressure+'::Enabled()))upl_tpi_m0_dt_r2::'+method+'('+args+');'
  s=once(s,old,old+'\n  if('+active+')'+STAGE+'::'+method+'('+args+');')
 return s
def patched_bytes(raw,backend,single):
 text=raw.decode('utf-8');newline='\r\n'if b'\r\n'in raw else'\n';normal=text.replace('\r\n','\n')
 new=patch_single(normal,backend)if single else patch_base(normal,backend)
 return new.replace('\n',newline).encode('utf-8')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--backend',choices=BASE,required=True);p.add_argument('--admission',required=True);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args()
 need(a.execution_authorized,'Root full-read source-only authorization required');backend=a.backend
 out=T/'outputs'/f'upl_tpi_p1_loadclock_{backend}_r1_source';receipt=L/f'upl_tpi_p1_loadclock_{backend}_r1.prepare.json';diff=L/f'upl_tpi_p1_loadclock_{backend}_r1.source.diff'
 need(not out.exists()and not receipt.exists()and not diff.exists(),'Existing candidate/partial protected; never overwrite')
 adm=Admission(a.admission,backend);result=dict(stage=STAGE+'.prepare',backend=backend,passed=False,build_invocations=0,help_invocations=0,solver_invocations=0,native_invocations=0,VTK_invocations=0,Git_invocations=0,SHA_scans=0,physical_acceptance=False,automatic_follow_up=False,root_admission=adm.entry)
 try:
  authors=[adm.pin(Path(__file__)),adm.pin(HEADER),adm.pin(NOTE)]
  prep_path,build_path,count=BASE[backend];prep_entry=adm.pin(L/prep_path);build_entry=adm.pin(L/build_path);base=read(prep_entry['path']);build=read(build_entry['path'])
  need(base.get('passed')is True and base.get('backend')==backend and base.get('stage')=='upl_tpi_m0_dt_r2.prepare','Actual M0 r2 source preparation is not passed')
  need(build.get('passed')is True,'Actual admitted M0 base build is not passed')
  root=Path(base['source_root']).resolve();need(len(base['files'])==count,'Complete M0 source count changed')
  old={};originals=[]
  for e in base['files']:
   q=adm.pin(e['path']);same(e);path=Path(q['path']).resolve();need(path.parent==root and path.name not in old,'Flat source closure path/identity changed');old[path.name]=path.read_bytes();originals.append(q)
  cls,_=names(backend);changed=[cls+'.cpp',cls+'Single.cpp'];new=dict(old)
  new[changed[0]]=patched_bytes(old[changed[0]],backend,False);new[changed[1]]=patched_bytes(old[changed[1]],backend,True)
  need(STAGE+'.h'not in new,'Base already includes new stage helper');new[STAGE+'.h']=HEADER.read_bytes()
  need(all(new[n]==raw for n,raw in old.items()if n not in changed),'Unexpected old source/header change')
  out.mkdir();files=[];entries=[];diffs=[]
  for name,raw in new.items():
   path=out/name
   with path.open('xb')as f:f.write(raw)
   q=stat(path);files.append(q)
   if name in old:
    source=next(e for e in originals if Path(e['path']).name==name);entries.append(dict(original=source,pinned_snapshot=q))
   if name in changed or name==STAGE+'.h':
    before=old.get(name,b'').decode('utf-8').splitlines(True);after=raw.decode('utf-8').splitlines(True)
    diffs.extend(difflib.unified_diff(before,after,fromfile='frozen_M0_r2/'+name,tofile='private_loadclock/'+name))
  with diff.open('x',encoding='utf-8',newline='\n')as f:f.writelines(diffs)
  consumed=adm.finish();result.update(passed=True,source_root=str(out.resolve()),base_prepare=prep_entry,base_build=build_entry,base_source_entries=entries,files=files,source_diff=stat(diff),changed_sources=changed,changed_headers=[STAGE+'.h'],recompile_sources=changed,other_base_files_byte_identical=True,pressure_helpers_and_schema_byte_identical=True,M0_policy_header_byte_identical=True,CUDA_source_and_cuh_byte_identical=True,public_class_or_virtual_ABI_changed=False,shared_device_structures_or_inline_tokens_changed=False,public_source_changed=False,policy_environment={'UPL_TPI_P1_LOADCLOCK_R1':'STAGED'},load_time_fractions=[0,.5,1],global_source_clock_and_Dirichlet_policy_changed=False,admitted_dt_seconds=.0100002288818359375/1000.,default_A_zero_ULP_regression_pending=True,new_policy_component_and_physical_review_pending=True,author_files=authors,consumed=consumed,consumed_stats_unchanged=True)
 except Exception as exc:
  result.update(first_failure=str(exc),partial_outputs_preserved=True);raise
 finally:write_json(receipt,result)
 print(str(receipt))
if __name__=='__main__':main()

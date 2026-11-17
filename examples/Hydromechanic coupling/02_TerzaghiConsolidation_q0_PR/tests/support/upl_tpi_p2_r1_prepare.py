"""Prepare one private P2 host-only source snapshot; never build or run a program."""
from __future__ import annotations
import argparse,difflib,json
from pathlib import Path
import upl_tpi_p1_loadclock_r1_prepare as old
T,L=old.T,old.L
TAG='upl_tpi_p2_r1';NOTE=T/'notes'/(TAG+'.md')
need,read,stat,same,write_json=old.need,old.read,old.stat,old.same,old.write_json
BASE=old.BASE
class Admission:
 def __init__(self,path,backend):
  self.entry=stat(path);self.data=read(path);self.used={}
  need(self.data.get('stage')==TAG+'.prepare_admission' and self.data.get('passed')is True and self.data.get('prepare_only')is True and self.data.get('backend')==backend,'One root-read source-only P2 admission required')
  self.frozen={str(Path(e['path']).resolve()):e for e in self.data['inputs']};need(len(self.frozen)==len(self.data['inputs']),'Duplicate admitted input')
 def pin(self,path):
  key=str(Path(path).resolve());need(key in self.frozen,'Unadmitted source input: '+key);self.used[key]=same(self.frozen[key]);return self.used[key]
 def finish(self):
  for e in self.used.values():same(e)
  same(self.entry);return list(self.used.values())
def patch_base(text,backend):
 pressure='upl_tpi_cpu_r1'if backend=='CPU'else'upl_tpi_gpu_r1'
 a=pressure+('::state.endpoint?2u:0u'if backend=='CPU'else'::EndpointActive()?2u:0u')
 z=pressure+('::state.endpoint?'if backend=='CPU'else'::EndpointActive()?')+pressure+'::EndpointPhase():0u'
 return old.once(text,a,z)
def cpu_block():
 return '''    if(upl_tpi_cpu_r1::Enabled()){
      bool forceScratch=false;
      try{
        upl_tpi_cpu_r1::Endpoint(this,Np,Idpc,Codec,Posc,Velrhopc,Sigmac,Kplasticc,PorePress0c,PorePressc,PoroJc,TimeStep,Nstep,stepdt);
        upl_tpi_cpu_r1::CaptureHG(HourglassCpu);
        for(unsigned round=0;round<2;round++){
          if(round)upl_tpi_cpu_r1::SecondEndpoint(this,Np,Idpc,Codec,Posc,Velrhopc,Sigmac,Kplasticc,PorePress0c,PorePressc,PoroJc,TimeStep,Nstep,stepdt,HourglassCpu);
          forceScratch=true;Interaction_Forces(INTERSTEP_SymCorrector);
          const double endpointdt=DtVariable(false);
          upl_tpi_cpu_r1::Need(endpointdt==stepdt,"P2 endpoint fixed dt changed");
          upl_tpi_cpu_r1::CheckHG(HourglassCpu);
          upl_tpi_cpu_r1::PrepareFinal(this,Np,Idpc,Codec,Posc,Velrhopc,Sigmac,Kplasticc,PorePress0c,PorePressc,PoroJc);
          PosInteraction_Forces();forceScratch=false;
          upl_tpi_cpu_r1::WriteFinal(Np,Npb,Idpc,Codec,PorePressc);
          if(round){upl_tpi_cpu_r1::state.endpoint=false;upl_tpi_cpu_r1::state.temporary=false;}
          ApplyPorePressureBoundaries();
          const bool drain=IsHydroMechDrainageActive();
          if(!round)upl_tpi_cpu_r1::ValidateFirstEndpoint(this,Np,Idpc,Codec,PorePressc,PorePress0c,PoroJc,
            [&](unsigned p){return drain && IsHydroMechDrainedParticle(p,Posc,Codec,FSTypec);});
          else{
            for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p]))
              upl_tpi_cpu_r1::SetCommitDrained(Idpc[p],drain && IsHydroMechDrainedParticle(p,Posc,Codec,FSTypec));
            upl_tpi_cpu_r1::Commit(this,Np,Idpc,Codec,PorePressc,PorePress0c,PoroJc);
          }
        }
      }catch(...){
        upl_tpi_cpu_r1::state.endpoint=false;upl_tpi_cpu_r1::state.temporary=false;
        if(forceScratch){try{PosInteraction_Forces();}catch(...){}}
        throw;
      }
    }
'''
def gpu_block():
 return '''    if(upl_tpi_gpu_r1::Enabled()){
      bool scratch=false;
      try{
        for(unsigned round=0;round<2;round++){
          if(!round)upl_tpi_gpu_r1::StartEndpoint(UPL_TPI_GPU_OWNER,UPL_TPI_GPU_VIEW,TimeStep,Nstep,stepdt,HourglassGpu);
          else upl_tpi_gpu_r1::SecondEndpoint(UPL_TPI_GPU_OWNER,UPL_TPI_GPU_VIEW,TimeStep,Nstep,stepdt,HourglassGpu);
          scratch=true;Interaction_Forces(INTERSTEP_SymCorrector);
          const double endpointdt=DtVariable(false);
          upl_tpi_gpu_r1::Require(endpointdt==stepdt,"P2 endpoint fixed dt changed");
          upl_tpi_gpu_r1::PrepareFinal(UPL_TPI_GPU_OWNER,UPL_TPI_GPU_VIEW,HourglassGpu);
          PosInteraction_Forces();scratch=false;
          upl_tpi_gpu_r1::WriteFinal(UPL_TPI_GPU_VIEW);
          ApplyPorePressureBoundaries();
          if(!round)upl_tpi_gpu_r1::ValidateFirstEndpoint(UPL_TPI_GPU_OWNER,UPL_TPI_GPU_VIEW,IsHydroMechDrainageActive(),unsigned(HydroMechTopLoadMode));
          else upl_tpi_gpu_r1::Commit(UPL_TPI_GPU_OWNER,UPL_TPI_GPU_VIEW,IsHydroMechDrainageActive(),unsigned(HydroMechTopLoadMode));
        }
      }catch(...){upl_tpi_gpu_r1::AbortEndpoint();if(scratch){try{PosInteraction_Forces();}catch(...){}}throw;}
    }
'''
def patch_single(text,backend):
 pressure='upl_tpi_cpu_r1'if backend=='CPU'else'upl_tpi_gpu_r1'
 begin=text.index('    if('+pressure+'::Enabled()){',text.index('  while(TimeStep<TimeMax){'))
 end=text.index('    TimeStep+=stepdt;',begin);prior=text[begin:end]
 need(prior.count('::Commit(')==1 and prior.count('Interaction_Forces(INTERSTEP_SymCorrector)')==1,'Original single endpoint block differs')
 text=text[:begin]+(cpu_block()if backend=='CPU'else gpu_block())+text[end:]
 banner=next(x for x in text.splitlines()if 'Log->Print("UplTpi'+('Cpu'if backend=='CPU'else'Gpu')+'R1:'in x)
 return old.once(text,banner,'    Log->Print("UplTpiP2'+backend+'R1: private two complete endpoint defects, one solid/J/HG/history commit; old source clock; not LF/implicit/second-order/restart/physics acceptance.");')
def patch(raw,backend,single):
 newline='\r\n'if b'\r\n'in raw else'\n';text=raw.decode('utf8').replace('\r\n','\n')
 return (patch_single(text,backend)if single else patch_base(text,backend)).replace('\n',newline).encode('utf8')
def gpu_prefix(old_header,new_header):
 marker=b'#ifdef UPL_TPI_GPU_R1_IMPLEMENTATION';a=old_header.split(marker,1)[0];z=new_header.split(marker,1)[0]
 first=b'// P2_HOST_API_R1_BEGIN\n';last=b'// P2_HOST_API_R1_END\n'
 need(z.count(first)==z.count(last)==1,'Unique host-only declaration block required')
 i=z.index(first);j=z.index(last,i)+len(last);block=z[i:j]
 need(b'#ifndef __CUDACC__\n'in block and b'#endif\n'in block,'New API must be excluded from CUDA')
 need(z[:i]+z[j:]==a,'Original CUDA-visible prefix changed outside explicit host-only API')
 return len(a)
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--backend',choices=BASE,required=True);ap.add_argument('--admission',type=Path,required=True);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args()
 need(args.execution_authorized,'Root full-read prepare-only authorization required');backend=args.backend;ad=Admission(args.admission,backend)
 out=T/'outputs'/('upl_tpi_p2_'+backend+'_r1_source');receipt=L/('upl_tpi_p2_'+backend+'_r1.prepare.json');diff=L/('upl_tpi_p2_'+backend+'_r1.source.diff')
 need(not out.exists()and not receipt.exists()and not diff.exists(),'Existing candidate/partial protected')
 result=dict(stage=TAG+'.prepare',backend=backend,passed=False,root_admission=ad.entry,build_invocations=0,solver_invocations=0,reader_invocations=0,SHA_scans=0,physical_acceptance=False)
 try:
  pressure='upl_tpi_cpu_r1.h'if backend=='CPU'else'upl_tpi_gpu_r1.h';cls='JSphCpu'if backend=='CPU'else'JSphGpu'
  authors=[ad.pin(Path(__file__)),ad.pin(NOTE),ad.pin(Path(old.__file__))]
  replacements={pressure:T/'support'/('upl_tpi_p2_'+backend.lower()+'_r1.h'),'upl_tpi_m0_dt_r2.h':T/'support/upl_tpi_p2_dt_r1.h'}
  for p in replacements.values():authors.append(ad.pin(p))
  for name in('upl_tpi_p2_'+backend.lower()+'_r1.md','upl_tpi_p2_dt_r1.md','upl_tpi_p2_reuse_contract_r1.md','upl_tpi_endpoint_defect_scalar_fixture_r1.md'):authors.append(ad.pin(T/'notes'/name))
  pp,bp,count=BASE[backend];pe=ad.pin(L/pp);be=ad.pin(L/bp);base,build=read(pe['path']),read(be['path'])
  need(base.get('passed')is True and base.get('stage')=='upl_tpi_m0_dt_r2.prepare'and base.get('backend')==backend and build.get('passed')is True,'Genuine passed original M0 source/build required')
  root=Path(base['source_root']).resolve();need(len(base['files'])==count,'Complete original source count differs')
  raw={};originals=[]
  for e in base['files']:
   q=ad.pin(e['path']);same(e);p=Path(q['path']);need(p.parent==root and p.name not in raw,'Flat source identity differs');raw[p.name]=p.read_bytes();originals.append(q)
  changed=[cls+'.cpp',cls+'Single.cpp'];new=dict(raw)
  new[changed[0]]=patch(raw[changed[0]],backend,False);new[changed[1]]=patch(raw[changed[1]],backend,True)
  for name,p in replacements.items():need(name in raw,'Missing original helper');new[name]=p.read_bytes()
  prefix=gpu_prefix(raw[pressure],new[pressure])if backend=='GPU'else None
  modified=set(changed)|set(replacements);need(all(new[n]==v for n,v in raw.items()if n not in modified),'Unexpected unrelated source change')
  out.mkdir();files=[];entries=[];lines=[]
  for name,data in new.items():
   p=out/name
   with p.open('xb')as f:f.write(data)
   e=stat(p);files.append(e);entries.append(dict(original=next(x for x in originals if Path(x['path']).name==name),pinned_snapshot=e))
   if name in modified:lines.extend(difflib.unified_diff(raw[name].decode('utf8').splitlines(True),data.decode('utf8').splitlines(True),fromfile='frozen_M0_r2/'+name,tofile='private_P2/'+name))
  with diff.open('x',encoding='utf8',newline='\n')as f:f.writelines(lines)
  result.update(passed=True,source_root=str(out.resolve()),base_prepare=pe,base_build=be,base_source_entries=entries,files=files,source_diff=stat(diff),changed_sources=changed,recompile_sources=changed,changed_headers=list(replacements),other_base_files_byte_identical=True,spatial_operator_sources_byte_identical=True,four_phase_original_bound_arithmetic_retained=True,CUDA_source_and_cuh_byte_identical=True,public_class_or_virtual_ABI_changed=False,shared_device_structures_or_inline_tokens_changed=False,GPU_original_prefix_bytes_after_removing_host_only_block=prefix,material_J_HG_update_order_retained=True,old_source_clock_retained=True,endpoint_defect_rounds=2,actual_full_forces_per_update=4,public_source_changed=False,default_A_native_regression_pending=True,author_files=authors,consumed=ad.finish(),consumed_stats_unchanged=True)
 except Exception as e:result.update(first_failure=str(e),partials_preserved=True);raise
 finally:write_json(receipt,result)
 print(receipt)
if __name__=='__main__':main()

"""Authorised source preparation only; one CPU or GPU candidate, no build/run."""
from __future__ import annotations
import argparse
import difflib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
T=Path(__file__).resolve().parents[1];L=T/'logs';STAGE='upl_tpi_m0_dt_r2'
HEADER=T/'support/upl_tpi_m0_dt_r2.h';NOTE=T/'notes/upl_tpi_m0_dt_r2.md'
BASE={
 'CPU':('upl_tpi_cpu_r1.prepare.json','upl_tpi_cpu_release_link_r3.build.json'),
 'GPU':('upl_tpi_gpu_full2tv_r1.prepare.json','upl_tpi_gpu_full2tv_Release_r1.build.json')}
def need(q,m):
    if not q:raise RuntimeError(m)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def same(e):
    a=stat(e['path']);need(a=={k:e[k]for k in ('path','bytes','mtime_ns')},'Frozen stat changed: '+e['path']);return a
def write(p,d):
    with Path(p).open('x',encoding='utf-8',newline='\n')as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
class Admission:
    def __init__(self,p,backend):
        self.entry=stat(p);self.data=read(p)
        need(self.data.get('stage')==STAGE+'.prepare_admission'and self.data.get('passed')is True
             and self.data.get('prepare_only')is True and self.data.get('backend')==backend,'Independent source-only backend admission required')
        self.frozen={str(Path(e['path']).resolve()):e for e in self.data['inputs']};self.consumed={}
        need(len(self.frozen)==len(self.data['inputs']),'Duplicate admitted input')
    def pin(self,p):
        k=str(Path(p).resolve());need(k in self.frozen,'Consumed input absent from admission: '+k)
        self.consumed[k]=same(self.frozen[k]);return self.consumed[k]
    def finish(self):
        for e in self.consumed.values():same(e)
        same(self.entry);return list(self.consumed.values())
def replace(s,old,new):
    need(s.count(old)==1,'Exact one patch anchor required: '+old[:100]);return s.replace(old,new)
def policy_enabled(backend):return 'upl_tpi_m0_dt_r2::Enabled(upl_tpi_'+backend.lower()+'_r1::Enabled())'
def patch_step(s,backend):
    cpu=backend=='CPU';cls='JSphCpu'if cpu else'JSphGpu';ns='upl_tpi_cpu_r1'if cpu else'upl_tpi_gpu_r1'
    if cpu:s=replace(s,'#include "upl_tpi_cpu_r1.h"','#include "upl_tpi_cpu_r1.h"\n#include "upl_tpi_m0_dt_r2.h"')
    # GPU gets the new header only inside the existing host IMPLEMENTATION block.
    s=replace(s,'double '+cls+'::DtVariable(bool final){','double '+cls+'::DtVariable(bool final){\n  const bool m0dt='+policy_enabled(backend)+';\n  double legacyWave=0.;')
    anchor='    GetDynamicStepScales'+('Cpu'if cpu else'Gpu')+'(dt2,dtw);'
    if cpu:
        block='''
    if(m0dt){
      legacyWave=dt2;double skeleton2max=0.;
      const double m=double(SoilCte.ModulusK)+4.*double(SoilCte.ModulusG)/3.;
      for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p])&&CODE_IsFluid(Codec[p])){
        double n,volume,rho;GetPorosityFeedbackStateCpu(p,n,volume,rho);
        const double c2=m/rho;
        upl_tpi_m0_dt_r2::Need(n>0.&&n<1.&&std::isfinite(c2)&&c2>0.,"M0 current-J skeleton state invalid");
        skeleton2max=max(skeleton2max,c2);
      }
      upl_tpi_m0_dt_r2::Need(skeleton2max>0.,"M0 skeleton native set empty");
      dt2=double(KernelH)/(max(sqrt(skeleton2max),VelMax*10.)+double(KernelH)*ViscDtMax);
    }'''
    else:
        block='''
    if(m0dt){
      legacyWave=dt2;double skeleton2max=0.;unsigned invalid=Np;
      double* waveg=NULL;unsigned* invalidg=NULL;
      try{
        waveg=ArraysGpu->ReserveDouble();invalidg=ArraysGpu->ReserveUint();
        cudaMemset(waveg,0,sizeof(double));cudaMemcpy(invalidg,&invalid,sizeof(unsigned),cudaMemcpyHostToDevice);
        const double m=double(SoilCte.ModulusK)+4.*double(SoilCte.ModulusG)/3.;
        // kw=0 applies ONLY to this necessary scale call, never to physical pressure or AV.
        cusph::ComputePorosityWaveSpeed2(Np,Npb,1.-double(SoilCte.Porosity),double(RhopZero)
          ,double(SoilCte.PoreWaterRho),m,0.,Codeg,PoroJg,waveg,invalidg,0.,1.,NULL,false,0.);
        cudaMemcpy(&skeleton2max,waveg,sizeof(double),cudaMemcpyDeviceToHost);
        cudaMemcpy(&invalid,invalidg,sizeof(unsigned),cudaMemcpyDeviceToHost);
      }catch(...){if(waveg)ArraysGpu->Free(waveg);if(invalidg)ArraysGpu->Free(invalidg);throw;}
      ArraysGpu->Free(waveg);ArraysGpu->Free(invalidg);
      Check_CudaErroor("Failed computing private M0 skeleton timestep scale.");
      upl_tpi_m0_dt_r2::Need(invalid==Np&&std::isfinite(skeleton2max)&&skeleton2max>0.,"M0 current-J skeleton state invalid");
      dt2=double(KernelH)/(max(sqrt(skeleton2max),VelMax*10.)+double(KernelH)*ViscDtMax);
    }'''
    s=replace(s,anchor,anchor+block)
    phase='upl_tpi_cpu_r1::state.endpoint'if cpu else'upl_tpi_gpu_r1::EndpointActive()'
    hg='HourglassCpu'if cpu else'HourglassGpu'
    anchor='  double dt=CFLnumber*min(dt1,dt2);'
    s=replace(s,anchor,anchor+'''
  if(m0dt)dt=upl_tpi_m0_dt_r2::Record(this,final?1u:('''+phase+'''?2u:0u),TimeStep,Nstep,SymplecticDtPre,
    CFLnumber*dt1,CFLnumber*dt2,dtw,CFLnumber*legacyWave,DBL_MAX /* HG reference unavailable in base; original derived guard retained. */);''')
    return s
def patch_single(s,backend):
    cpu=backend=='CPU';ns='upl_tpi_cpu_r1'if cpu else'upl_tpi_gpu_r1';cl='JSphCpu'if cpu else'JSphGpu'
    enabled=policy_enabled(backend);owner='static_cast<'+cl+'*>(this)'
    s=replace(s,'#include "'+ns+'.h"','#include "'+ns+'.h"\n#include "upl_tpi_m0_dt_r2.h"')
    if cpu:
        s=replace(s,'TimeMax>0. && TimeMax<=.15','TimeMax>0. && ('+enabled+'?TimeMax<=2.:TimeMax<=.15)')
        s=replace(s,'FixedDt && FixedDt->GetFixedValue()==6.2501430511474609e-06 && SymplecticDtPre==6.2501430511474609e-06',
          'FixedDt && ('+enabled+'?upl_tpi_m0_dt_r2::AllowedDt(FixedDt->GetFixedValue(),HydroMechDrainageStartTime):FixedDt->GetFixedValue()==6.2501430511474609e-06) && SymplecticDtPre==FixedDt->GetFixedValue()')
        init='    upl_tpi_cpu_r1::Init(this,DirOut,Np,Idpc,Codec,PorePressc,PorePress0c,PoroJc,Kplasticc,TimeStep,Nstep,SymplecticDtPre);'
        saved='  if(upl_tpi_cpu_r1::Enabled())upl_tpi_cpu_r1::Saved(this,Part,TimeStep,Nstep,Np,Idpc,Codec,PorePressc,PoroJc);'
        finish='  if(upl_tpi_cpu_r1::Enabled())upl_tpi_cpu_r1::Finish(this,Nstep,TimeStep);'
    else:
        old='(TimeMax<=.15 || (TimeMax==72.88428690075874 && NstepsBreak==11661219))'
        s=replace(s,old,'('+enabled+'?TimeMax<=2.:'+old+')')
        s=replace(s,'FixedDt && FixedDt->GetFixedValue()==6.2501430511474609e-6\n      && SymplecticDtPre==6.2501430511474609e-6',
          'FixedDt && ('+enabled+'?upl_tpi_m0_dt_r2::AllowedDt(FixedDt->GetFixedValue(),HydroMechDrainageStartTime):FixedDt->GetFixedValue()==6.2501430511474609e-6)\n      && SymplecticDtPre==FixedDt->GetFixedValue()')
        init='    upl_tpi_gpu_r1::Init(UPL_TPI_GPU_OWNER,DirOut,UPL_TPI_GPU_VIEW,TimeStep,Nstep,SymplecticDtPre);'
        saved='  if(upl_tpi_gpu_r1::Enabled())upl_tpi_gpu_r1::Saved(UPL_TPI_GPU_OWNER,Part,TimeStep,Nstep,UPL_TPI_GPU_VIEW);'
        finish='  if(upl_tpi_gpu_r1::Enabled())upl_tpi_gpu_r1::Finish(UPL_TPI_GPU_OWNER,Nstep,TimeStep);'
    s=replace(s,init,init+'\n    if('+enabled+')upl_tpi_m0_dt_r2::Init('+owner+',DirOut,"'+backend+'",std::getenv("UPL_TPI_'+backend+'_R1"),TimeStep,Nstep,SymplecticDtPre,HydroMechDrainageStartTime);')
    s=replace(s,saved,saved+'\n  if('+enabled+')upl_tpi_m0_dt_r2::Saved('+owner+',Part,TimeStep,Nstep);')
    s=replace(s,finish,finish+'\n  if('+enabled+')upl_tpi_m0_dt_r2::Finish('+owner+',Nstep,TimeStep);')
    return s
def patch_gpu_header(s):
    prefix=s.split('#ifdef UPL_TPI_GPU_R1_IMPLEMENTATION',1)[0]
    s=replace(s,'#ifdef UPL_TPI_GPU_R1_IMPLEMENTATION\n','#ifdef UPL_TPI_GPU_R1_IMPLEMENTATION\n#include "upl_tpi_m0_dt_r2.h"\n')
    s=replace(s,'step==0&&dt==6.2501430511474609e-6,','step==0&&(upl_tpi_m0_dt_r2::Enabled(Enabled())?upl_tpi_m0_dt_r2::AllowedDt(dt,.0100002288818359375):dt==6.2501430511474609e-6),')
    need(s.split('#ifdef UPL_TPI_GPU_R1_IMPLEMENTATION',1)[0]==prefix,'GPU device/API prefix changed')
    return s
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--backend',choices=BASE,required=True)
    ap.add_argument('--admission',type=Path,required=True);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args()
    need(a.execution_authorized,'One explicit source-only root action required')
    out=T/'outputs'/('upl_tpi_m0_dt_'+a.backend+'_r2_source');receipt=L/('upl_tpi_m0_dt_'+a.backend+'_r2.prepare.json')
    need(not out.exists()and not receipt.exists(),'Existing candidate/receipt protected; do not retry or overwrite')
    result=dict(stage=STAGE+'.prepare',backend=a.backend,passed=False,build_invocations=0,solver_invocations=0,
      help_invocations=0,native_invocations=0,VTK_invocations=0,Git_invocations=0,hash_scans=0,public_source_changed=False,
      physical_acceptance=False,automatic_follow_up=False,partial_output_preserved=False)
    try:
        ad=Admission(a.admission,a.backend);result['root_admission']=ad.entry
        for p in [Path(__file__),HEADER,NOTE,sys.executable]:ad.pin(p)
        bp,bb=[L/n for n in BASE[a.backend]];ad.pin(bp);ad.pin(bb);prep,built=read(bp),read(bb)
        need(prep['passed']and built['passed'],'Both frozen source preparation and actual Release build must pass')
        base=Path(prep['source_root']);entries=prep['files'];need(len(entries)==(266 if a.backend=='CPU'else 269),'Frozen source membership differs')
        originals={}
        for e in entries:
            ad.pin(e['path']);same(e);p=Path(e['path']);need(p.is_relative_to(base),'Base source entry escaped frozen root')
            key=p.relative_to(base);need(key not in originals,'Duplicate base source member');originals[key]=p.read_bytes()
        need(all(len(k.parts)==1 for k in originals),'Expected original flat frozen source layout')
        changes={};cl='JSphCpu'if a.backend=='CPU'else'JSphGpu'
        for name,fn in [(cl+'.cpp',lambda s:patch_step(s,a.backend)),(cl+'Single.cpp',lambda s:patch_single(s,a.backend))]:
            changes[Path(name)]=fn(originals[Path(name)].decode('utf-8-sig')).encode('utf-8')
        if a.backend=='GPU':changes[Path('upl_tpi_gpu_r1.h')]=patch_gpu_header(originals[Path('upl_tpi_gpu_r1.h')].decode('utf-8-sig')).encode('utf-8')
        need(Path(HEADER.name)not in originals,'New shared policy header collides with frozen member')
        ad.finish();out.mkdir()
        for key,old in originals.items():
            data=changes.get(key,old);p=out/key
            with p.open('xb')as f:f.write(data)
            need(p.read_bytes()==data,'New frozen copy differs')
        with(out/HEADER.name).open('xb')as f:f.write(HEADER.read_bytes())
        need((out/HEADER.name).read_bytes()==HEADER.read_bytes(),'Shared policy copy differs')
        differences={str(k):''.join(difflib.unified_diff(originals[k].decode('utf-8-sig').splitlines(True),v.decode('utf-8-sig').splitlines(True),fromfile='base/'+str(k),tofile='candidate/'+str(k)))for k,v in changes.items()}
        diff=out/'source_diff.json';write(diff,dict(stage=STAGE+'.source_diff',passed=True,backend=a.backend,exact_diffs=differences,
          only_changed_base_files=[str(k)for k in changes],new_header=HEADER.name,public_class_headers_unchanged=True,
          CUDA_external_signatures_unchanged=True,CUDA_source_and_cuh_unchanged=True,GPU_header_device_API_prefix_unchanged=True,
          existing_CPU_private_inline_helper_unchanged=True,default_A_numerical_regression_pending=True))
        result.update(passed=True,source_root=str(out),base_prepare=stat(bp),base_build=stat(bb),
          base_source_entries=[dict(original=e,pinned_snapshot=stat(out/Path(e['path']).relative_to(base)))for e in entries],
          files=[stat(out/k)for k in originals]+[stat(out/HEADER.name)],source_diff=stat(diff),
          changed_sources=[stat(out/k)for k in changes if k.suffix=='.cpp'],changed_headers=[stat(out/k)for k in changes if k.suffix=='.h']+[stat(out/HEADER.name)],
          recompile_sources=[stat(out/(cl+'.cpp')),stat(out/(cl+'Single.cpp'))],
          other_base_files_byte_identical=True,public_class_or_virtual_ABI_changed=False,CUDA_source_and_cuh_byte_identical=True,
          shared_device_structures_or_inline_tokens_changed=False,policy_environment='UPL_TPI_M0_DT_R1=EQ40_RH1',R_h=1,
          admitted_dt_seconds=[.0100002288818359375/1000.,.0100002288818359375/500.],bounded_TimeMax_upper_s=2.,
          new_policy_guard_regression_pending=True,default_A_zero_ULP_regression_pending=True,
          author_files=[stat(p)for p in [Path(__file__),HEADER,NOTE]],consumed=ad.finish(),consumed_stats_unchanged=True)
    except Exception as e:result.update(passed=False,first_error=str(e),partial_output_preserved=out.exists())
    write(receipt,result);print(json.dumps(dict(passed=result['passed'],receipt=str(receipt),first_error=result.get('first_error')),ensure_ascii=False))
    return 0 if result['passed']else 1
if __name__=='__main__':raise SystemExit(main())

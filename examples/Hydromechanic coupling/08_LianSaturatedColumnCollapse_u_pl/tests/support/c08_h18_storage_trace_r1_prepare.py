"""Author-only source preparation: one reversible host overlay and an independent read-only CUDA module."""
import argparse, copy, difflib, zipfile
from pathlib import Path
import c08_h18_late_rhs_r1_build as original
m,T,L,S=original.m,original.T,original.L,original.S
TAG='c08_h18_storage_trace_r1';CAP=T/'outputs/c08_h18_storage_trace_source_r1'
BASE=L/'c08_preload_schema2_Release_r1.build.json';NOTE=T/'notes'/(TAG+'.md')
HEADER=T/'support'/(TAG+'.h');CUDA=T/'support'/(TAG+'.cu')

INCLUDES='''#ifdef C08_STORAGE_TRACE
#include "C08StorageTrace.h"
#include <fstream>
#include <iomanip>
#include <vector>
#include <stdexcept>
#endif
'''
HOST='''#ifdef C08_STORAGE_TRACE
namespace{
  bool C08StorageStarted=false;
  unsigned C08StorageWritten=UINT_MAX;
  std::string C08StorageOutput;
  void C08StorageRequire(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
  void C08StorageWriteRows(const std::string& dir,unsigned hoststep,double time){
    if(!C08StorageStarted)return;
    std::vector<C08StorageRow> rows(5000);unsigned errors=0;
    C08StorageRequire(cusph::C08StorageRead(rows.data(),&errors)&&!errors,"Storage observer read/identity failed.");
    const unsigned count=rows[0].updates;
    for(unsigned s=0;s<5000;s++)C08StorageRequire(rows[s].native_id==2060+s&&rows[s].inits==1&&!rows[s].errors&&rows[s].rhs_h==count&&rows[s].updates==count&&rows[s].last_step==2000000+count,"Storage observer unique per-ID stage coverage failed.");
    if(!count||count==C08StorageWritten)return;
    C08StorageRequire(C08StorageWritten==UINT_MAX||count>C08StorageWritten,"Storage observer completed count regressed.");
    C08StorageRequire(rows[0].last_step==hoststep+1,"Storage observer saved completed-step identity failed.");
    const std::string path=fun::GetDirWithSlash(dir)+"C08StorageTrace.csv";
    if(C08StorageWritten==UINT_MAX){std::string normalized=path;for(char& c:normalized)if(c=='\\\\')c='/';C08StorageRequire(normalized.find("/tests/outputs/")!=std::string::npos&&!fun::FileExists(path),"Storage observer requires a fresh tests/outputs sidecar.");C08StorageOutput=path;}
    C08StorageRequire(C08StorageOutput==path,"Storage observer output owner changed.");
    std::ofstream file(path,std::ios::out|std::ios::app);file<<std::setprecision(17);
    if(C08StorageWritten==UINT_MAX)file<<"native_id,inits,rhs_h,updates,cap_calls,cap_changes,release_cap_calls,release_cap_changes,errors,last_completed_step,actual_saved_time_s,initial_S,last_S,sum_dt_s,weighted_pressure_delta,compression,Darcy_remainder_including_rate_quantization,source_split_roundoff,pressure_commit_roundoff,weight_change,cap_change,sum_abs_increments,local_budget_sum,rate_quantization_bound_only,endpoint_residual,endpoint_arithmetic_budget\\n";
    for(const auto& r:rows){
      C08StorageRequire(r.last_time==time,"Storage observer actual scalar clock differs from save.");
      const double u=.5*DBL_EPSILON,operations=16.*double(r.updates)+8.*double(r.cap_calls)+128.,g=operations*u/(1.-operations*u);
      const double ledger=((((r.compression+r.Darcy_remainder)+r.source_split_roundoff)+r.pressure_commit_roundoff)+r.weight_change)+r.cap_change;
      const double residual=(r.last_S-r.initial_S)-ledger,budget=r.local_budget_sum+g*(r.abs_increments+fabs(r.initial_S)+fabs(r.last_S));
      for(double v:{r.initial_S,r.last_S,r.sum_dt,r.weighted_pressure_delta,r.compression,r.Darcy_remainder,r.source_split_roundoff,r.pressure_commit_roundoff,r.weight_change,r.cap_change,r.abs_increments,r.local_budget_sum,r.rate_quantization_bound,residual,budget})C08StorageRequire(std::isfinite(v),"Storage observer nonfinite cumulative field.");
      C08StorageRequire(operations*u<1.&&budget>=0&&fabs(residual)<=budget,"Storage observer endpoint arithmetic identity failed.");
      file<<r.native_id<<','<<r.inits<<','<<r.rhs_h<<','<<r.updates<<','<<r.cap_calls<<','<<r.cap_changes<<','<<r.release_cap_calls<<','<<r.release_cap_changes<<','<<r.errors<<','<<r.last_step<<','<<time<<','<<r.initial_S<<','<<r.last_S<<','<<r.sum_dt<<','<<r.weighted_pressure_delta<<','<<r.compression<<','<<r.Darcy_remainder<<','<<r.source_split_roundoff<<','<<r.pressure_commit_roundoff<<','<<r.weight_change<<','<<r.cap_change<<','<<r.abs_increments<<','<<r.local_budget_sum<<','<<r.rate_quantization_bound<<','<<residual<<','<<budget<<'\\n';
    }
    file.flush();C08StorageRequire(bool(file),"Storage observer CSV write failed.");C08StorageWritten=count;
  }
}
#endif
'''
INITIALISE='''#ifdef C08_STORAGE_TRACE
  // Release RunCellDivide has sorted/retired255, but GravityPreloadReleased is set only after this call returns.
  if(!C08StorageStarted && IsGravityPreloadHandoff() && unsigned(Nstep)==2000000 && Np==6805 && Npb==1805){
    if(GravityPreloadElasticSource || GravityPreloadKeepBedOverlap || !GravityPreloadBedIds.empty()
      || GravityPreloadIdBegin!=1805 || GravityPreloadIdCount!=255 || PorePressPreg || PoroJPreg
      || !IsDynamicPorePlasticConfig() || !PorosityFeedback || !DynamicPoreWall || !DynamicPoreConductivity
      || DynamicPoreConductivityCk!=2. || !HydroMechFreeSeepage || HydroMechDrainage
      || TKernel!=KERNEL_Wendland || Dp!=.04 || KernelH!=.072f || !FixedDt || FixedDt->GetFixedValue()!=.000005 || SymplecticDtPre!=.000005
      || !ArtificialStress || ArtificialStressCoef!=.3f || ArtificialStressExp!=2.55f || Visco!=.1f || ViscoTime
      || SoilDamping || PoreShepardRegularization || !NoPenetration || !HydroMechDynamicSeepage || !GravityPreload || PeriActive || !Simulate2D
      || !PoroJg || !PorePressg || !FSTypeg || !Idpg || !Codeg)
      Run_Exceptioon("Storage observer requires the exact original AS03 H1.8/5us released bed-role candidate.");
    C08StorageRequire(cusph::C08StorageInit(Np,Npb,Idpg,Codeg,PoroJg,PorePressg,double(MassFluid)/double(RhopZero),1.-double(SoilCte.Porosity),double(SoilCte.PoreWaterBulkModulus),unsigned(Nstep),TimeStep),"Storage observer initialization launch failed.");
    C08StorageStarted=true;
  }
#endif
'''
BEFORE_CAP='''#ifdef C08_STORAGE_TRACE
    if(C08StorageStarted)C08StorageRequire(cusph::C08StorageCapBefore(Np,Npb,Idpg,Codeg,PoroJg,PorePressg,unsigned(Nstep),TimeStep,!GravityPreloadReleased),"Storage observer pre-cap launch failed.");
#endif
'''
AFTER_CAP='''#ifdef C08_STORAGE_TRACE
    if(C08StorageStarted)C08StorageRequire(cusph::C08StorageCapAfter(Np,Npb,Idpg,Codeg,PoroJg,PorePressg,FSTypeg,double(MassFluid)/double(RhopZero),1.-double(SoilCte.Porosity),double(SoilCte.PoreWaterBulkModulus)),"Storage observer post-cap launch failed.");
#endif
'''
RHS='''#ifdef C08_STORAGE_TRACE
  if(IsGravityPreloadHandoff() && GravityPreloadReleased && (!C08StorageStarted || !UseDynamicPorePlaneContact()))Run_Exceptioon("Storage observer missed pre-cap initialization or the configured released contact is inactive.");
  if(C08StorageStarted && InterStep==INTERSTEP_SymCorrector){
    if(!PoroJPreg || !PorePressPreg)Run_Exceptioon("Storage observer lost the real corrector Jn/pn before their original release.");
    C08StorageRequire(cusph::C08StorageRhs(Np,Npb,Idpg,Codeg,PoroJPreg,PoroJg,PorePressPreg,PoroThetag,PorePressRateg,double(MassFluid)/double(RhopZero),1.-double(SoilCte.Porosity),double(SoilCte.PoreWaterBulkModulus),unsigned(Nstep),TimeStep,SymplecticDtPre),"Storage observer force_h launch failed.");
  }
#endif
'''
UPDATE='''#ifdef C08_STORAGE_TRACE
  if(C08StorageStarted)C08StorageRequire(cusph::C08StorageUpdate(Np,Npb,Idpg,Codeg,PorePressPreg,PoroJg,PorePressg,double(MassFluid)/double(RhopZero),1.-double(SoilCte.Porosity),double(SoilCte.PoreWaterBulkModulus),unsigned(Nstep),TimeStep,dt),"Storage observer accepted-pressure launch failed.");
#endif
'''
SAVE='''#ifdef C08_STORAGE_TRACE
  C08StorageWriteRows(DirOut,unsigned(Nstep),TimeStep);
#endif
'''

def overlay(raw):
    nl=b'\r\n' if b'\r\n' in raw else b'\n';changed=raw;inserted=[]
    def add(anchor,text,after=False,count=1):
        nonlocal changed
        a=anchor.encode('ascii').replace(b'\n',nl);q=text.encode('ascii').replace(b'\n',nl)
        m.need(raw.count(a)==count and q not in raw,'Unique frozen host anchor required: '+anchor[:90])
        changed=changed.replace(a,a+q if after else q+a);inserted.append((q,count))
    add('#include <limits>\n',INCLUDES,True)
    add('using namespace std;\n',HOST,True)
    add('  if(!HydroMech || !PorePressg || !DivData.beginendcell)return;\n',INITIALISE,True)
    cap='    cusph::ApplyFreeSurfacePorePressure(Np,Npb,false,HydroMechTopLoadMode,Posxyg,Codeg,FSTypeg,PorePressg,NULL,true);\n'
    add(cap,BEFORE_CAP,count=2);add(cap,AFTER_CAP,True,count=2)
    add('  DynamicConductivitySpeedMax=maxspeed;\n',RHS,True)
    update='    cusph::UpdatePorePressureSymplectic(Np,Npb,dt,Codeg,PorePressPreg,PorePressRateg,PorePressg\n      ,IsHydroMechDrainageActive(),HydroMechTopLoadMode,Posxyg,FSTypeg);\n'
    add(update,UPDATE,True)
    add('unsigned JSphGpu::ParticlesDataDown(unsigned n,unsigned pini,bool code,bool onlynormal){\n',SAVE,True)
    inverse=changed
    for fragment,count in inserted:
        m.need(inverse.count(fragment)==count,'Observer insertion count differs');inverse=inverse.replace(fragment,b'')
    m.need(inverse==raw,'Removing private observer hooks must restore all original host bytes')
    return changed

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();m.need(a.execution_authorized,'Root full read and source-preparation admission required')
    check=L/(TAG+'.prepare.json');m.need(not CAP.exists() and not check.exists(),'Existing complete/partial observer preparation protected');before=[]
    try:
        base=m.read(BASE);m.need(base['passed'] and base['configuration']=='Release' and base['consumed_stats_unchanged'],'Original macro-off schema2 Release required')
        before=[m.stat(q) for q in (Path(__file__),HEADER,CUDA,NOTE,BASE,Path(original.__file__),Path(m.__file__))]+[m.bind(base[k]) for k in ('actual_call','program','source_capture','source_archive')]
        capture=m.read(m.bind(base['source_capture'])['path']);m.need(capture['archive']==base['source_archive'],'Original schema2 archive differs');m.verify(before)
        with zipfile.ZipFile(base['source_archive']['path']) as z:
            inventory=z.infolist();names=[q.filename for q in inventory];m.need(len(set(names))==len(names) and 'src/source/C08StorageTrace.h' not in names and 'src/source/C08StorageTrace.cu' not in names,'Unique original archive without new observer files required')
            old=z.read('src/source/JSphGpu.cpp');new=overlay(old);private=CAP/'src/source';private.mkdir(parents=True)
            materials={'src/source/JSphGpu.cpp':new,'src/source/C08StorageTrace.cu':CUDA.read_bytes(),'src/source/C08StorageTrace.h':HEADER.read_bytes()}
            for name,data in materials.items():
                with (CAP/name).open('xb') as f:f.write(data)
            archive=CAP/'source.zip'
            with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as out:
                for q in inventory:out.writestr(copy.copy(q),new if q.filename=='src/source/JSphGpu.cpp' else z.read(q.filename))
                for name in ('src/source/C08StorageTrace.cu','src/source/C08StorageTrace.h'):out.writestr(name,materials[name])
            with zipfile.ZipFile(archive) as out:
                m.need(out.namelist()==names+['src/source/C08StorageTrace.cu','src/source/C08StorageTrace.h'],'Observer archive inventory changed beyond declared additions')
                for name in names:m.need(out.read(name)==(new if name=='src/source/JSphGpu.cpp' else z.read(name)),'Unrelated original archive bytes changed')
                for name,data in materials.items():m.need(out.read(name)==data,'Private source/archive differs')
            diff=CAP/'source.patch';diff.write_text(''.join(difflib.unified_diff(old.decode('utf-8-sig').splitlines(True),new.decode('utf-8-sig').splitlines(True),fromfile='original/src/source/JSphGpu.cpp',tofile='observer/src/source/JSphGpu.cpp')),encoding='utf8',newline='')
        m.verify(before);record=dict(stage=TAG+'.source',passed=True,prepared_only=True,baseline_source_build=m.stat(BASE),baseline_source_capture=base['source_capture'],baseline_source_archive=base['source_archive'],archive=m.stat(archive),files=[m.stat(CAP/q) for q in materials],diff=m.stat(diff),modified_original_members=['src/source/JSphGpu.cpp'],added_members=['src/source/C08StorageTrace.cu','src/source/C08StorageTrace.h'],exact_inverse_original_bytes=True,all_other_archived_bytes_identical=True,primary_expression_bytes_retained=True,macro='C08_STORAGE_TRACE',class_layout_changed=False,public_interfaces_changed=False,physical_equations_changed=False,original_physical_CUDA_recompiled=0,consumed=before,consumed_stats_unchanged=True,build_invocations=0,solver_invocations=0,native_decodes=0,SHA_scans=0,physical_acceptance=False)
        m.save(CAP/'source.json',record);m.save(check,dict(stage=TAG+'.prepare',passed=True,source_capture=m.stat(CAP/'source.json'),source_archive=m.stat(archive),consumed=before,consumed_stats_unchanged=True,build_invocations=0,solver_invocations=0,native_decodes=0,SHA_scans=0,physical_acceptance=False));print('STORAGE_OBSERVER_SOURCE_PREPARED',str(check),flush=True)
    except Exception as error:
        if not check.exists():m.save(check,dict(stage=TAG+'.prepare',passed=False,first_failure=str(error),partial_outputs_preserved=True,consumed=before,build_invocations=0,solver_invocations=0,native_decodes=0,physical_acceptance=False))
        raise
if __name__=='__main__':main()

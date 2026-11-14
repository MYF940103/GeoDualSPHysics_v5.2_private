"""Prepare only a reversible one-host overlay and standalone RV CUDA source."""
import argparse
import difflib
import json
import zipfile
from pathlib import Path

T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='c08_h18_rv_gpu_r1'
OUT=T/'outputs'/(TAG+'_source');NOTE=T/'notes'/(TAG+'.md')
AUTHOR={k:T/'support'/(TAG+suffix) for k,suffix in [('CUDA','.cu'),('header','.h')]}

def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def need(v,s):
    if not v:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def bind(e):need(stat(e['path'])==e,'Consumed stat changed: '+e['path']);return e
def save(p,j):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(j,f,ensure_ascii=False,indent=2);f.write('\n')

HOST=r'''
#include "JDsFixedDt.h"
#include "c08_h18_rv_gpu_r1.h"
#include <array>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <stdexcept>
namespace {
struct C08H18Phase {
  unsigned long long Calls=0,Commits=0;
  unsigned Step=~0u,CudaStatus=0;
  double Time=0,Dt=0,MaxLambda=0,MaxBound=0;
  double Running[10]={};
  c08h18rv::Result Value={};
};
struct C08H18Counter {
  const void* Owner=nullptr;unsigned StartStep=0,LastSavedStep=0,ManufacturedCalls=0;
  C08H18Phase Pre,Cor;
};
static C08H18Counter C08H18Count;
static bool C08H18Requested(){
  static const bool requested=[](){const char* p=std::getenv("C08_RV_H18");if(!p)return false;
    if(std::strcmp(p,"1"))throw std::runtime_error("C08_RV_H18 must be absent or exactly1");return true;}();return requested;
}
static double C08H18Ratio(double x,double b){return b>0?std::fabs(x)/b:(x==0?0:std::numeric_limits<double>::infinity());}
static void C08H18Update(C08H18Phase& p,const c08h18rv::Result& r){
  p.Value=r;p.MaxLambda=(std::max)(p.MaxLambda,r.lambda_max);p.MaxBound=(std::max)(p.MaxBound,r.isolated_bound);
  if(!r.certificates_passed)return;
  const double values[]={r.max_normal_budget_ratio,r.max_commit_budget_ratio,
    C08H18Ratio(r.work_certificate_error,r.work_certificate_budget),
    (std::max)(C08H18Ratio(r.work+2*r.form,r.work_budget),C08H18Ratio((std::max)(r.work,0.),r.work_budget)),
    C08H18Ratio(r.net_force_norm,r.net_force_budget),C08H18Ratio(r.torque_certificate_error,r.torque_certificate_budget),
    C08H18Ratio(r.torque,r.torque_budget),C08H18Ratio((std::max)(r.committed_work,0.),r.committed_work_budget),
    C08H18Ratio(r.committed_net_force_norm,r.committed_net_force_budget),C08H18Ratio(r.committed_torque,r.committed_torque_budget)};
  for(unsigned i=0;i<10;i++)p.Running[i]=(std::max)(p.Running[i],values[i]);
}
static void C08H18Raw(std::ostream& f,const c08h18rv::Result& r){
  f<<','<<r.directed_edges<<','<<r.reverse_memberships<<','<<r.max_degree<<','<<r.gamma64<<','<<r.max_condition
   <<','<<r.max_normal_budget_ratio<<','<<r.max_commit_budget_ratio
   <<','<<r.work<<','<<r.form<<','<<r.work_defect_prediction<<','<<r.work_certificate_error<<','<<r.work_certificate_budget<<','<<r.work_budget
   <<','<<r.net_force_norm<<','<<r.net_force_budget<<','<<r.torque<<','<<r.torque_defect_prediction<<','<<r.torque_certificate_error<<','<<r.torque_certificate_budget<<','<<r.torque_budget
   <<','<<r.committed_work<<','<<r.committed_work_budget<<','<<r.committed_net_force_norm<<','<<r.committed_net_force_budget<<','<<r.committed_torque<<','<<r.committed_torque_budget;
}
static void C08H18Null(std::ostream& f,const c08h18rv::Result& r){f<<','<<r.max_residual<<','<<r.residual_budget<<','<<r.max_force<<','<<r.force_budget;}
static bool C08H18Init(const void* owner,const std::string& dir,unsigned step,float h,double dp){
  if(C08H18Count.Owner)return C08H18Count.Owner==owner;
  for(const char* file:{"C08H18ResidualViscosityPolicy.json","C08H18ResidualViscosity.csv","C08H18ResidualManufactured.csv"})
    if(std::ifstream((dir+file).c_str()).good())return false;
  std::ofstream policy((dir+"C08H18ResidualViscosityPolicy.json").c_str());policy<<std::setprecision(17)
    <<"{\"policy\":\"C08H18ResidualViscosityPolicy\",\"schema\":2,\"phase_policy\":\"ReleaseOnly\",\"active\":true,\"alpha\":"<<c08h18rv::Alpha
    <<",\"main_columns\":66,\"main_schema\":\"C08H18RV66-r1\",\"manufactured_columns\":40,\"kernel\":\"Wendland\",\"kernel_h_sph_float\":"<<double(h)<<",\"dp_m\":"<<dp
    <<",\"requested_hdp\":1.8,\"operator_dt_s\":0.000005,\"source_schema\":2,\"keep_bed_overlap\":false,\"geometry_profile\":\"bedroles\",\"first_stage_global_step\":"<<step
    <<",\"retired_begin\":1805,\"retired_count\":255,\"force_clock\":\"original_TimeStep_both_stages\",\"reaction_closed\":false,\"BI4_metadata\":false,\"native_22_schema_changed\":false"
    <<",\"manufactured_mode_count\":3,\"synthetic_velocity_coordinates\":\"global\",\"manufactured_first_force_scratch_only\":true,\"host_gate_before_Ace_commit\":true"
    <<",\"ephemeral_buffers_per_helper\":5,\"neighbor_kernels_per_helper\":2,\"summary_kernels_per_helper\":2,\"serial_O_N_summaries\":true,\"reverse_cell_membership_each_positive_neighbor\":true"
    <<",\"per_stage_mechanical_certificates\":true,\"save_rows_are_not_all_stage_trace\":true,\"running_ratios_are_per_phase_maxima\":true,\"budget_formed_by_bound_source_not_rebuilt_offline_from_all_neighbors\":true"
    <<",\"LS_regularized\":false,\"wall_bonds\":false,\"full_coupled_stability_claimed\":false,\"physical_acceptance\":false}\n";
  policy.flush();if(!policy)return false;
  std::ofstream csv((dir+"C08H18ResidualViscosity.csv").c_str());csv<<c08h18rv::TelemetryHeader()<<'\n';csv.flush();if(!csv)return false;
  std::ofstream mfg((dir+"C08H18ResidualManufactured.csv").c_str());mfg<<c08h18rv::ManufacturedHeader()<<'\n';mfg.flush();if(!mfg)return false;
  C08H18Count.Owner=owner;C08H18Count.StartStep=step;return true;
}
static bool C08H18Row(const std::string& dir,const char* record,const char* phase,const C08H18Phase& q,unsigned completed,double saved){
  const auto& s=C08H18Count;const auto& r=q.Value;std::ofstream f((dir+"C08H18ResidualViscosity.csv").c_str(),std::ios::out|std::ios::app);
  f<<std::setprecision(17)<<record<<','<<phase<<",1,"<<c08h18rv::Alpha<<','<<q.Step<<','<<completed<<','<<q.Time<<','<<q.Time<<','<<saved<<','<<q.Dt
   <<','<<q.Calls<<','<<q.Commits<<','<<s.Pre.Calls<<','<<s.Cor.Calls<<','<<s.Pre.Commits<<','<<s.Cor.Commits
   <<','<<r.lambda_max<<','<<q.MaxLambda<<','<<r.isolated_bound<<','<<q.MaxBound<<','<<r.validated_soil<<','<<r.committed
   <<','<<r.error_bits<<','<<r.invalid_sorted<<','<<r.invalid_native_id<<','<<q.CudaStatus;
  C08H18Raw(f,r);for(double x:q.Running)f<<','<<x;C08H18Null(f,r);f<<'\n';f.flush();return bool(f);
}
static bool C08H18Manufactured(const std::string& dir,unsigned mode,unsigned step,double time,double dt,const c08h18rv::Result& r,unsigned status){
  const char* names[]={"actual","translation","full_affine","rigid_rotation"};
  std::ofstream f((dir+"C08H18ResidualManufactured.csv").c_str(),std::ios::out|std::ios::app);
  f<<std::setprecision(17)<<mode<<','<<names[mode]<<','<<step<<','<<time<<','<<dt;C08H18Raw(f,r);C08H18Null(f,r);
  f<<','<<r.committed<<','<<r.certificates_passed<<','<<r.manufactured_passed<<','<<r.error_bits<<','<<status<<'\n';f.flush();return bool(f);
}
static bool C08H18Save(const void* owner,const std::string& dir,unsigned completed,double time){
  const auto& s=C08H18Count;if(s.Owner!=owner||s.LastSavedStep==completed)return false;
  if(s.ManufacturedCalls!=3||s.Pre.Calls!=s.Cor.Calls||s.Pre.Commits!=s.Pre.Calls||s.Cor.Commits!=s.Cor.Calls
    ||s.Pre.Step+1!=completed||s.Cor.Step+1!=completed||s.Pre.Calls!=completed-s.StartStep)return false;
  if(!C08H18Row(dir,"save","Pre",s.Pre,completed,time)||!C08H18Row(dir,"save","Cor",s.Cor,completed,time))return false;
  C08H18Count.LastSavedStep=completed;return true;
}
}
'''

HOOK=r'''
  if(C08H18Requested()){
    if(!GravityPreloadReleased || !GravityPreload || !IsGravityPreloadHandoff() || GravityPreloadElasticSource
      || GravityPreloadKeepBedOverlap || !GravityPreloadBedIds.empty() || GravityPreloadActualStep!=2000000
      || GravityPreloadIdBegin!=1805 || GravityPreloadIdCount!=255 || Np!=6805 || Npb!=1805 || NpbOk>Npb
      || CaseNp!=7060 || CaseNpb!=2060 || CaseNfixed!=2060 || CaseNfluid!=5000 || PartBegin
      || CaseNmoving || CaseNfloat || InOut || Symmetry || PeriActive || Shifting || Damping || RelaxZones || UseDEM || AccInput
      || !UseDynamicPorePlaneContact() || !NoPenetration || TMdbc2!=MDBC2_NoPen || TBoundary!=BC_MDBC || !UseNormals
      || !HydroMech || !HydroMechDynamicSeepage || !PorosityFeedback || !DynamicPorePressure || !DynamicPoreWall
      || !DynamicPoreConductivity || HydroMechConductivityModel!=1 || DynamicPoreConductivityCk!=2.
      || !Simulate2D || TKernel!=KERNEL_Wendland || TStep!=STEP_Symplectic || Dp!=.04 || KernelH!=.072f
      || !FixedDt || FixedDt->GetFixedValue()!=.000005 || SymplecticDtPre!=.000005
      || (interstep!=INTERSTEP_SymPredictor && interstep!=INTERSTEP_SymCorrector)
      || !PoroJg || !Aceg || HourglassGpu || SoilHourglassXi || SoilDamping || PoreShepardRegularization || SoilBoundaryDerivativeSPR
      || !ArtificialStress || ArtificialStressCoef!=.3f || ArtificialStressExp!=2.55f || TVisco!=VISCO_Artificial || Visco!=.1f || ViscoTime
      || TDensity!=DDT_None || !SoilStressRateGradCorr || !HydroMechFreeSeepage || HydroMechDrainage
      || HydroMechTopLoadMode!=HMLOAD_None || RhopZero!=2072.5f || SoilCte.PoreWaterRho!=1000.f
      || SoilCte.PoreWaterBulkModulus!=1e9f || SoilCte.Porosity!=.35f || SoilCte.HydraulicConductivity!=.0002f
      || SoilCte.ModulusE!=20e6f || SoilCte.PRvs!=.33f || DPCtes!=DP_PS || !StrainSoftening
      || SoilCte.dlt!=0.f || SoilCte.psiDecay!=0.f || SoilCte.coh!=5000.f || SoilCte.coh_r!=1000.f || SoilCte.n_coh!=5.f
      || SoilCte.n_phi!=0.f || SoilCte.phi!=SoilCte.phi_r || Gravity.x!=0 || Gravity.y!=0 || Gravity.z!=-9.81f)
      Run_Exceptioon("Private H1.8 RV requires unchanged schema2 psi0 Wendland/AS.3n2.55/5us/bedroles released target.");
    if(!C08H18Init(this,DirOut,Nstep,KernelH,Dp))Run_Exceptioon("Private H1.8 RV policy/counter output exists or initialization failed.");
    C08H18Counter& count=C08H18Count;const bool predictor=(interstep==INTERSTEP_SymPredictor);
    if((predictor && (count.Pre.Calls!=count.Cor.Calls || Nstep!=count.StartStep+count.Cor.Calls))
      ||(!predictor && (count.Pre.Calls!=count.Cor.Calls+1 || Nstep!=count.StartStep+count.Cor.Calls)))
      Run_Exceptioon("Private H1.8 RV actual Pre/Cor order changed.");
    const auto evaluate=[&](unsigned mode,bool commit,c08h18rv::Result& r){return c08h18rv::Add(Np,Npb,DivData,Dcellg,Idpg,
      Posxyg,Poszg,Velrhopg,Codeg,PoroJg,1.-double(SoilCte.Porosity),double(RhopZero),double(SoilCte.PoreWaterRho),
      double(MassFluid)/double(RhopZero),KernelH,CSP.kwend.bwen,SoilCte.ModulusG,SymplecticDtPre,mode,commit,Aceg,r);};
    if(!count.ManufacturedCalls){
      if(!predictor || Nstep!=2000000)Run_Exceptioon("Manufactured graph must be the first genuine released force graph.");
      for(unsigned mode=1;mode<=3;mode++){
        c08h18rv::Result r={};const cudaError_t status=evaluate(mode,false,r);count.ManufacturedCalls++;
        if(!C08H18Manufactured(DirOut,mode,Nstep,TimeStep,SymplecticDtPre,r,unsigned(status)))Run_Exceptioon("Failed preserving real manufactured metrics.");
        if(status!=cudaSuccess || r.error_bits || r.committed || !r.certificates_passed || !r.manufactured_passed || r.validated_soil!=5000)
          Run_Exceptioon("Private H1.8 RV manufactured graph/affine-null/mechanical certificate failed; actual Ace not committed.");
      }
    }
    C08H18Phase& record=predictor?count.Pre:count.Cor;record.Calls++;record.Step=Nstep;record.Time=TimeStep;record.Dt=SymplecticDtPre;
    c08h18rv::Result r={};const cudaError_t status=evaluate(0,true,r);record.CudaStatus=unsigned(status);C08H18Update(record,r);if(r.committed)record.Commits++;
    if(status!=cudaSuccess || r.error_bits || !r.committed || !r.certificates_passed || r.validated_soil!=5000){
      if(!C08H18Row(DirOut,"failure",predictor?"Pre":"Cor",record,Nstep,TimeStep))Run_Exceptioon("Failed preserving real residual-viscosity failure metrics.");
      Log->Printf("Private H1.8 RV rejected: phase=%s Nstep=%u id=%u sorted=%u bits=%u CUDA=%u committed=%u dt=%.17g lambda=%.17g isolated=%.17g.",
        predictor?"Pre":"Cor",Nstep,r.invalid_native_id,r.invalid_sorted,r.error_bits,unsigned(status),unsigned(r.committed),SymplecticDtPre,r.lambda_max,r.isolated_bound);
      Run_Exceptioon("Private H1.8 RV rank/finite/mechanical/coupled-path diagnostic rejected; preserve partial evidence.");
    }
  }
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args()
    need(a.execution_authorized,'Separate root source-preparation admission required')
    check=L/(TAG+'.prepare.json');need(not OUT.exists() and not check.exists(),'Existing complete/partial source preparation protected')
    paths=[L/('c08_preload_schema2_'+q+'_r1.build.json') for q in ('Debug','Release')];builds=[read(p) for p in paths]
    need(all(b['passed'] and b['consumed_stats_unchanged'] for b in builds) and builds[0]['source_archive']==builds[1]['source_archive']
         and builds[0]['source_capture']==builds[1]['source_capture'],'Same successful original Debug/Release schema2 archive required')
    before=[stat(q)for q in [Path(__file__),NOTE,*AUTHOR.values(),*paths]]
    for b in builds:before += [bind(b[k]) for k in ('program','source_capture','source_archive','actual_call')]
    archive=bind(builds[0]['source_archive'])
    with zipfile.ZipFile(archive['path'])as z:original=z.read('src/source/JSphGpuSingle.cpp')
    nl=b'\r\n' if b'\r\n' in original else b'\n'
    def text(s):return s.replace('\n',nl.decode()).encode('utf-8')
    anchors=[(b'#include "JSphGpuSingle.h"'+nl,b'#include "JSphGpuSingle.h"'+nl+text(HOST)),
      (b'  if(DynamicPorePressure)ComputeDynamicPorePressureRateGpu(dynamicridpg);',text(HOOK)+b'  if(DynamicPorePressure)ComputeDynamicPorePressureRateGpu(dynamicridpg);'),
      (b'  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);',b'  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);'+text('\n  if(C08H18Requested() && GravityPreloadReleased && !C08H18Save(this,DirOut,Nstep+1,TimeStep))\n    Run_Exceptioon("Private H1.8 RV actual saved phase counters failed.");'))]
    overlay=original
    for old,new in anchors:need(overlay.count(old)==1,'Unique original host source anchor differs');overlay=overlay.replace(old,new,1)
    inverse=overlay
    for old,new in reversed(anchors):need(inverse.count(new)==1,'Ambiguous reverse overlay anchor');inverse=inverse.replace(new,old,1)
    need(inverse==original,'Unexpected original source body edit')
    for e in before:bind(e)
    OUT.mkdir();sources={}
    for key,leaf,content in [('host','JSphGpuSingle.cpp',overlay),*[(k,p.name,p.read_bytes())for k,p in AUTHOR.items()]]:
        q=OUT/leaf
        with q.open('xb')as f:f.write(content)
        sources[key]=stat(q)
    diff=OUT/'host.diff';diff.write_text(''.join(difflib.unified_diff(original.decode('utf-8').splitlines(True),overlay.decode('utf-8').splitlines(True),fromfile='schema2/JSphGpuSingle.cpp',tofile='private/JSphGpuSingle.cpp')),encoding='utf-8')
    capture=OUT/'source.json';save(capture,dict(stage=TAG+'.source',passed=True,prepared_only=True,private_sources=sources,
      source_archive=archive,baseline_source_capture=builds[0]['source_capture'],baseline_builds=[stat(p)for p in paths],host_diff=stat(diff),
      exact_reverse_original_host_bytes=True,original_CUDA_members_unchanged=True,public_source_changed=False,class_or_CTE_layout_changed=False,
      default_OFF_env_absent=True,explicit_ON_env='C08_RV_H18=1',alpha=.1,main_columns=66,manufactured_columns=40,policy_schema=2,
      physical_objects_retained=112,private_objects_required=2,actual_link_objects_required=114,budget_formed_by_bound_source=True,
      all_stage_trace_claimed=False,physical_acceptance=False,SHA_scans=0))
    for e in before:bind(e)
    save(check,dict(stage=TAG+'.prepare',passed=True,source_capture=stat(capture),source_archive=archive,private_sources=sources,
      host_diff=stat(diff),consumed=before,consumed_stats_unchanged=True,compiler_invocations=0,solver_invocations=0,reader_invocations=0,
      original_CUDA_objects_not_recompiled=True,public_source_changed=False,physical_acceptance=False,SHA_scans=0))

if __name__=='__main__':main()

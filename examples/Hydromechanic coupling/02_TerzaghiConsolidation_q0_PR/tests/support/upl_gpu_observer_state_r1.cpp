// Private GPU J-observer lifecycle component. No force or physical time step.
// Uses actual allocation, periodic duplication, cell sorting, resize and J helpers.
#include "JSphGpuSingle.h"
#include "JSphCfgRun.h"
#include "JSphGpu_ker.h"
#include "JAppInfo.h"
#include "JArraysGpu.h"
#include "JCellDivGpuSingle.h"
#include "JDsTimersGpu.h"
#include "JLog2.h"
#include <cuda_runtime_api.h>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("GpuObserverStateComponent","r1","02-11-2026");
namespace fs=std::filesystem;
static void Need(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
static void Cu(cudaError_t e){Need(e==cudaSuccess,cudaGetErrorString(e));}
template<class T>static std::vector<T> Download(const T* ptr,unsigned n){
  Need(ptr!=nullptr,"Missing actual device array");std::vector<T> result(n);
  if(n)Cu(cudaMemcpy(result.data(),ptr,sizeof(T)*n,cudaMemcpyDeviceToHost));return result;
}
template<class T>static void Upload(T* ptr,const std::vector<T>& values){
  Need(ptr!=nullptr,"Missing upload device array");
  if(!values.empty())Cu(cudaMemcpy(ptr,values.data(),sizeof(T)*values.size(),cudaMemcpyHostToDevice));
}
static bool Bits(double a,double b){return std::memcmp(&a,&b,sizeof(a))==0;}
static bool Close(double a,double b){
  const double scale=(std::max)(1.,(std::max)(fabs(a),fabs(b)));
  return std::isfinite(a)&&std::isfinite(b)&&fabs(a-b)<=16.*std::numeric_limits<double>::epsilon()*scale;
}
class StateFixture:public JSphGpuSingle{
  struct View{
    std::vector<unsigned> id,cell;std::vector<typecode> code;
    std::vector<double2> xy;std::vector<double> z,j,theta,pre;
  };
  struct Ref{double j,theta,pre;};
  std::vector<Ref> reference;
  std::ofstream csv;
  unsigned stateChecks=0,cloneWitnesses=0,extraDivides=0;
  static double Tag(unsigned id){return 1.+double(id+1)/65536.;}
  static double Rate(unsigned id){return double(int(id%9)-4)/32.;}
  View Read()const{
    View v;v.id=Download(Idpg,Np);v.cell=Download(Dcellg,Np);v.code=Download(Codeg,Np);
    v.xy=Download(Posxyg,Np);v.z=Download(Poszg,Np);v.j=Download(PoroJg,Np);v.theta=Download(PoroThetag,Np);
    if(PoroJPreg)v.pre=Download(PoroJPreg,Np);return v;
  }
  std::map<unsigned,unsigned> Natives(const View& v)const{
    std::map<unsigned,unsigned> result;
    for(unsigned p=0;p<Np;p++){
      Need(v.id[p]<512&&CODE_IsFluid(v.code[p]),"Unexpected native identity/type");
      Need(CODE_IsNormal(v.code[p])||CODE_IsPeriodic(v.code[p]),"Excluded/nonperiodic-abnormal particle");
      if(CODE_IsNormal(v.code[p]))Need(result.emplace(v.id[p],p).second,"Duplicate normal ID");
    }
    Need(result.size()==512&&Npb==0&&CellDivSingle->GetNpfOut()==0,"Native count/exclusion changed");
    return result;
  }
  std::vector<unsigned> NativeOrder(const View& v)const{
    std::vector<unsigned> ids;for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(v.code[p]))ids.push_back(v.id[p]);return ids;
  }
  void CaptureReference(const View& v,bool pre){
    const auto natives=Natives(v);reference.assign(512,Ref{0,0,0});
    for(const auto& a:natives){const unsigned p=a.second;reference[a.first]=Ref{v.j[p],v.theta[p],pre?v.pre[p]:0.};}
  }
  void ExactState(const char* stage,bool pre){
    const auto v=Read();const auto native=Natives(v);Need(v.pre.empty()!=pre,"Live predictor history expectation changed");
    unsigned periodic=0,corners=0;
    for(unsigned p=0;p<Np;p++){
      const Ref& r=reference[v.id[p]];
      Need(Bits(v.j[p],r.j)&&Bits(v.theta[p],r.theta)&&(!pre||Bits(v.pre[p],r.pre)),"ID-tagged J/theta/Jpre bits changed");
      if(CODE_IsPeriodic(v.code[p])){
        periodic++;const unsigned q=native.at(v.id[p]);
        const double dx=v.xy[p].x-v.xy[q].x,dz=v.z[p]-v.z[q];
        if(Close(fabs(dx),fabs(PeriXinc.x))&&Close(fabs(dz),fabs(PeriZinc.z)))corners++;
      }
    }
    Need(periodic>0&&corners>0,"XZ clone-of-clone corner witness is empty");
    cloneWitnesses+=corners;stateChecks+=Np;
    csv<<stage<<','<<Np<<",512,"<<periodic<<','<<corners<<','<<(pre?1:0)<<",true\n";
  }
  void Initialize(const JSphCfgRun* cfg,JLog2* log){
    PorosityObserver=true;AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;
    SelecDevice(cfg->GpuId);Timersg->Config(false);Timersg->TmStart(TMG_Init,false);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunGpu();FreePartsInit();
    Need(HydroMech&&!HydroMechDynamicSeepage&&Simulate2D&&TStep==STEP_Symplectic&&CaseNfluid==512&&CaseNpb==0,"Only existing OFF512 private 2-D observer seed admitted");
    Need(PeriX&&PeriZ&&!PeriY&&PeriXinc.y==0&&PeriXinc.z==0&&PeriZinc.x==0&&PeriZinc.y==0,"Only axis XZ periodic seed admitted");
    Need(PoroJg&&PoroThetag&&PoroJ&&PoroTheta&&!PoroJPreg&&!PosxyPreg&&!PoszPreg&&!VelrhopPreg,"Initial observer/predictor allocation wrong");
    const auto v=Read();Natives(v);
    for(unsigned p=0;p<Np;p++)Need(Bits(v.j[p],1.)&&Bits(v.theta[p],0.),"Fresh J/theta initialization is not exactly1/0");
    Need(TimeStep==0.&&Nstep==0,"Initialization advanced physical time");
  }
  void RecoverRejected(){
    Need(PoroJPreg!=nullptr,"Rejected observer did not retain its old full J");
    ArraysGpu->Free(PoroJg);PoroJg=PoroJPreg;PoroJPreg=nullptr;
    const auto v=Read();std::vector<double> j(Np),theta(Np,0.);
    for(unsigned p=0;p<Np;p++)j[p]=Tag(v.id[p]);Upload(PoroJg,j);Upload(PoroThetag,theta);
    std::vector<float> plastic(Np,0.f);Upload(Kplasticg,plastic);
  }
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    Initialize(cfg,log);const fs::path out(cfg->DirOut);
    csv.open(out/"state.csv");csv<<"stage,total_slots,native_ids,periodic_slots,corner_clone_witnesses,live_Jpre,all_tagged_bits_exact\n";
    const double dt=1./1024.;auto v=Read();std::vector<double> j(Np),theta(Np);
    for(unsigned p=0;p<Np;p++){j[p]=Tag(v.id[p]);theta[p]=Rate(v.id[p]);}
    Upload(PoroJg,j);Upload(PoroThetag,theta);
    ComputeSymplecticPorosity(false,dt*.5); // Actual host reserve/swap and actual CUDA predictor.
    Need(PoroJPreg&&!PosxyPreg&&!PoszPreg&&!VelrhopPreg,"Jpre must be live independently of physical PRE arrays");
    v=Read();unsigned recurrence=0;
    for(unsigned p=0;p<Np;p++){
      const double expected=Tag(v.id[p])+(dt*.5)*Tag(v.id[p])*Rate(v.id[p]);
      Need(Close(v.j[p],expected)&&Bits(v.pre[p],Tag(v.id[p]))&&Bits(v.theta[p],Rate(v.id[p])),"Actual predictor recurrence differs");
      recurrence++;
    }
    CaptureReference(v,true);ExactState("predictor",true);
    // Swap only two native positions/cells. No ID/J/theta move: real Divide must align them.
    const auto natives=Natives(v);const unsigned a=natives.at(0),b=natives.at(511);
    Need(a!=b&&v.cell[a]!=v.cell[b],"Distant native cell witness absent");
    std::swap(v.xy[a],v.xy[b]);std::swap(v.z[a],v.z[b]);std::swap(v.cell[a],v.cell[b]);
    Upload(Posxyg,v.xy);Upload(Poszg,v.z);Upload(Dcellg,v.cell);
    const auto before=NativeOrder(v);RunCellDivide(true);extraDivides++;
    v=Read();Need(before!=NativeOrder(v),"Actual native cell reorder was vacuous");
    ExactState("actual_cell_reorder_and_periodic",true);
    RunCellDivide(true);extraDivides++;ExactState("repeat_periodic_Jpre_PosPre_NULL",true);
    // Actual pool resize while Jpre is live. Preserve all active slots, then regenerate ghosts normally.
    const unsigned oldSize=GpuParticlesSize;
    ResizeParticlesSize(oldSize+1,0.f,false);Need(GpuParticlesSize>oldSize,"Actual GPU pool did not grow");
    ExactState("live_Jpre_resize",true);
    RunCellDivide(true);extraDivides++;ExactState("after_resize_periodic",true);
    v=Read();theta.resize(Np);std::vector<float> plastic(Np,0.f);
    unsigned poison=0;for(unsigned p=0;p<Np;p++){
      theta[p]=-.75*Rate(v.id[p]);
      if(CODE_IsPeriodic(v.code[p])){plastic[p]=123.f;poison++;}
    }
    Need(poison>0,"Periodic plastic negative control is empty");
    Upload(PoroThetag,theta);Upload(Kplasticg,plastic);
    // Persistent-array tail guard, valid only across the isolated corrector (no later sorting).
    constexpr unsigned guard=7;Need(GpuParticlesSize>=Np+guard,"No room for bounded tail guards");
    std::vector<double> tailJ(guard),tailTheta(guard);
    for(unsigned p=0;p<guard;p++){tailJ[p]=32.+double(p)/8.;tailTheta[p]=-16.-double(p)/8.;}
    Cu(cudaMemcpy(PoroJg+Np,tailJ.data(),sizeof(double)*guard,cudaMemcpyHostToDevice));
    Cu(cudaMemcpy(PoroThetag+Np,tailTheta.data(),sizeof(double)*guard,cudaMemcpyHostToDevice));
    ComputeSymplecticPorosity(true,dt);Need(!PoroJPreg,"Actual corrector did not release Jpre");
    const auto after=Read();Natives(after);double maxError=0.;
    for(unsigned p=0;p<Np;p++){
      const Ref& old=reference[after.id[p]];const double expected=old.pre+dt*old.j*(-.75*Rate(after.id[p]));
      Need(Close(after.j[p],expected),"Actual corrector recurrence differs");maxError=(std::max)(maxError,fabs(after.j[p]-expected));recurrence++;
      const double n=1.-(1.-double(SoilCte.Porosity))/after.j[p];
      Need(std::isfinite(n)&&n>0.&&n<1.&&fabs((1.-n)*after.j[p]-(1.-double(SoilCte.Porosity)))<=5e-13,"Single-J solid-volume ledger failed");
    }
    const auto tj=Download(PoroJg+Np,guard),tt=Download(PoroThetag+Np,guard);
    Need(!std::memcmp(tj.data(),tailJ.data(),sizeof(double)*guard)&&!std::memcmp(tt.data(),tailTheta.data(),sizeof(double)*guard),"Corrector wrote persistent-array tail guards");
    CaptureReference(after,false);ExactState("corrector",false);
    // Guard rejection is diagnostic recovery of private J state, never a solver retry.
    const auto native=Natives(after);const unsigned nativeSlot=native.at(0);
    theta.assign(Np,0.);Upload(PoroThetag,theta);plastic.assign(Np,0.f);Upload(Kplasticg,plastic);
    ComputeSymplecticPorosity(false,dt*.5);plastic[nativeSlot]=1.f;Upload(Kplasticg,plastic);
    bool rejected=false;
    try{ComputeSymplecticPorosity(true,dt);}catch(const std::exception& e){rejected=std::string(e.what()).find("finite saturated elastic")!=std::string::npos;}
    Need(rejected,"Nonzero normal-native plastic state was not rejected");RecoverRejected();
    unsigned domain=0;
    for(double bad:{1.-double(SoilCte.Porosity),std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity()}){
      const auto current=Read();auto badJ=current.j;badJ[nativeSlot]=bad;Upload(PoroJg,badJ);rejected=false;
      try{ComputeSymplecticPorosity(false,dt*.5);}catch(const std::exception& e){rejected=std::string(e.what()).find("finite saturated elastic")!=std::string::npos;}
      Need(rejected,"Boundary/nonfinite J was not rejected");domain++;RecoverRejected();
    }
    Need(!PoroJPreg&&TimeStep==0.&&Nstep==0,"State component advanced physics or leaked predictor history");
    csv.flush();Need(bool(csv),"State CSV failed");
    int device=0;Cu(cudaGetDevice(&device));cudaDeviceProp props{};Cu(cudaGetDeviceProperties(&props,device));
    std::ofstream complete(out/"state_complete.json");complete<<std::setprecision(17)
      <<"{\"passed\":true,\"native_count\":512,\"fixed_count\":0,\"state_slot_bit_checks\":"<<stateChecks
      <<",\"real_cell_reorder\":true,\"actual_nonzero_prefix_cell_division\":false,\"periodic_forces_full_division\":true"
      <<",\"component_extra_RunCellDivide_calls\":"<<extraDivides<<",\"periodic_JPre_with_PosPre_NULL\":true,\"clone_of_clone_checks\":"<<cloneWitnesses
      <<",\"clone_of_clone_scope\":\"Same-ID double-axis image witnesses plus frozen RunPeriodic ordering, not an inserted kernel counter\""
      <<",\"live_JPre_resize_preserved\":true,\"old_GPU_capacity\":"<<oldSize<<",\"new_GPU_capacity\":"<<GpuParticlesSize
      <<",\"predictor_and_corrector_slot_checks\":"<<recurrence<<",\"corrector_recurrence_checked\":true,\"max_corrector_abs_error\":"<<maxError
      <<",\"recurrence_tolerance_DBL_EPSILON_multiple\":16,\"copy_sort_resize_bit_exact\":true,\"corrector_tail_guard_slots\":"<<guard
      <<",\"predictor_history_released\":true,\"invalid_J_rejections\":"<<domain<<",\"native_plastic_rejected\":true,\"periodic_plastic_poison_ignored\":true"
      <<",\"periodic_plastic_poison_slots\":"<<poison<<",\"actual_LoadConfig_ConfigDomain_InitRunGpu\":true,\"actual_J_host_and_CUDA_helpers\":true"
      <<",\"actual_force_calls\":0,\"completed_physics_steps\":0,\"actual_time_s\":"<<TimeStep<<",\"Nstep\":"<<Nstep
      <<",\"device_name\":\""<<props.name<<"\",\"public_GPU_dynamic_mode\":false,\"feedback\":false,\"physical_acceptance\":false}\n";
    complete.flush();Need(bool(complete),"State completion write failed");
  }
};
int main(int argc,char** argv){
  try{
    Need(argc>=6&&std::string(argv[1])=="--state","Use --state followed by ordinary -gpu arguments and a fresh output");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=2;i<argc;i++)args.push_back(argv[i]);
    JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(!cfg.Cpu&&!cfg.PrintInfo,"Only a GPU state component is admitted");
    Need(!fs::exists(cfg.DirOut),"Retained output protected");
    cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    StateFixture fixture;fixture.Execute(&cfg,AppInfo.LogPtr());return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(const std::string& e){std::cerr<<e<<'\n';return 1;}
  catch(const char* e){std::cerr<<e<<'\n';return 1;}
  catch(...){std::cerr<<"GPU observer state component rejected; preserve evidence\n";return 2;}
}


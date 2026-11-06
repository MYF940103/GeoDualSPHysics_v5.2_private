// Actual GPU fixed-ID retirement/divide only. No Run, step, production event or new kernel.
#include "JSphGpuSingle.h"
#include "JSphCfgRun.h"
#include "JSphMk.h"
#include "JCellDivGpuSingle.h"
#include "JDsTimersGpu.h"
#include "JDsDcellDef.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "JException.h"
#include <cuda_runtime.h>
#include <algorithm>
#include <climits>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("WallRetireGpu","r1","07-11-2026");
namespace fs=std::filesystem;
static constexpr unsigned Total=7060,Fixed=2060,Soil=5000;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static void Cu(cudaError_t e){Need(e==cudaSuccess,cudaGetErrorString(e));}
template<class T>static std::vector<T> Down(const T* p,unsigned n){Need(p!=nullptr,"Device source absent");std::vector<T> a(n);Cu(cudaMemcpy(a.data(),p,n*sizeof(T),cudaMemcpyDeviceToHost));return a;}
template<class T>static void Up(T* p,const std::vector<T>& a){Need(p!=nullptr,"Device destination absent");Cu(cudaMemcpy(p,a.data(),a.size()*sizeof(T),cudaMemcpyHostToDevice));}
template<class T>static bool Bits(const T& a,const T& b){return !std::memcmp(&a,&b,sizeof(T));}
static_assert(sizeof(double2)==16&&sizeof(float4)==16&&sizeof(float3)==12&&sizeof(tsymatrix3d)==48,"Typed member representation differs");
struct BorrowDerivative{
  float3*& pointer;float3* old;float3* owned=nullptr;
  BorrowDerivative(float3*& p,unsigned n):pointer(p),old(p){Need(!p,"Derivative scratch already owned");Cu(cudaMalloc(reinterpret_cast<void**>(&owned),n*sizeof(float3)));pointer=owned;}
  void Release(){pointer=old;float3* p=owned;owned=nullptr;Cu(cudaFree(p));}
  ~BorrowDerivative(){pointer=old;if(owned)cudaFree(owned);}
};
struct Flags{bool &f,&d,&w,&free;bool a,b,c,e;~Flags(){f=a;d=b;w=c;free=e;}};
struct State{
  std::vector<unsigned> id,cell,fs;std::vector<typecode> code;std::vector<double2> xy;std::vector<double> z,j,theta;
  std::vector<float4> v;std::vector<float> p,p0,k,dk,rate;std::vector<tsymatrix3d> sigma;
  std::vector<float3> load,normal,ace;std::vector<byte> slip,mode;std::vector<tmatrix3d> c;
};
static bool Surface(const State& a,unsigned q){return CODE_IsFluid(a.code[q])&&(a.fs[q]==FST_FreeSurface||a.fs[q]==FST_Isolated);}
static bool Equal(const State& a,unsigned x,const State& b,unsigned y,bool pressure){
  return Bits(a.id[x],b.id[y])&&Bits(a.xy[x],b.xy[y])&&Bits(a.z[x],b.z[y])&&Bits(a.v[x],b.v[y])&&Bits(a.sigma[x],b.sigma[y])&&Bits(a.j[x],b.j[y])&&Bits(a.theta[x],b.theta[y])&&(!pressure||Bits(a.p[x],b.p[y]))&&Bits(a.p0[x],b.p0[y])&&Bits(a.k[x],b.k[y])&&Bits(a.dk[x],b.dk[y])&&Bits(a.rate[x],b.rate[y])&&Bits(a.load[x],b.load[y])&&Bits(a.code[x],b.code[y]);
}
class Probe:public JSphGpuSingle{
  unsigned First=0,Count=0;
  bool Retired(unsigned id)const{return id>=First&&id<First+Count;}
  void NoStep()const{Need(TimeStep==0&&Nstep==0&&!PosxyPreg&&!PoszPreg&&!VelrhopPreg&&!SigmaPreg&&!PorePressPreg&&!PoroJPreg,"A predictor or physical update was entered");}
  State Capture(bool acceleration=false)const{
    State a;a.id=Down(Idpg,Np);a.cell=Down(Dcellg,Np);a.fs=Down(FSTypeg,Np);a.code=Down(Codeg,Np);a.xy=Down(Posxyg,Np);a.z=Down(Poszg,Np);a.v=Down(Velrhopg,Np);a.sigma=Down(Sigmag,Np);a.j=Down(PoroJg,Np);a.theta=Down(PoroThetag,Np);a.p=Down(PorePressg,Np);a.p0=Down(PorePress0g,Np);a.k=Down(Kplasticg,Np);a.dk=Down(KplasticDkg,Np);a.rate=Down(PorePressRateg,Np);a.load=Down(HydroMechLoadAceg,Np);a.normal=Down(BoundNormalg,Npb);a.slip=Down(BoundSlipModeg,Npb);a.mode=Down(BoundModeg,Npb);a.c=Down(CorrMatg,Npb);if(acceleration)a.ace=Down(Aceg,Np);return a;
  }
  std::vector<unsigned> Map(const State& a,bool after)const{
    Need(Np==(after?Total-Count:Total)&&Npb==(after?Fixed-Count:Fixed),"Actual compacted GPU counts differ");std::vector<unsigned> m(Total,UINT_MAX);unsigned soil=0,wall=0;
    for(unsigned q=0;q<Np;q++){const unsigned id=a.id[q];Need(id<Total&&m[id]==UINT_MAX&&CODE_IsNormal(a.code[q]),"Unknown/duplicate/non-normal native ID");Need(!after||!Retired(id),"Retired ID remains active");m[id]=q;
      if(id>=Fixed){Need(q>=Npb&&CODE_IsFluid(a.code[q]),"Soil lost native fluid prefix/type");soil++;}else{Need(q<Npb&&CODE_IsFixed(a.code[q]),"Remaining wall lost fixed prefix/type");wall++;}}
    for(unsigned id=0;id<Total;id++)Need((m[id]==UINT_MAX)==(after&&Retired(id)),"An unselected ID disappeared or selected ID survived");
    Need(soil==Soil&&wall==(after?Fixed-Count:Fixed)&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Native soil/exclusion accounting changed");return m;
  }
  unsigned long long BoundaryCandidates(const State& a)const{
    Need(DivData.axis==MGDIV_Z&&DivData.domcellcode==DomCellCode&&DivData.nc.w==DivData.nc.x*DivData.nc.y&&(DivData.scelldiv==1||DivData.scelldiv==2),"Actual GPU cell layout differs");
    const auto cells=Down(DivData.beginendcell,unsigned(2*CellDivSingle->GetNct()+5));const auto n=DivData.nc;const int d=DivData.scelldiv;unsigned long long count=0;
    for(unsigned i=Npb;i<Np;i++){
      const int x=int(DCEL_Cellx(DomCellCode,a.cell[i]))-DivData.cellzero.x,y=int(DCEL_Celly(DomCellCode,a.cell[i]))-DivData.cellzero.y,z=int(DCEL_Cellz(DomCellCode,a.cell[i]))-DivData.cellzero.z;
      Need(CODE_IsFluid(a.code[i])&&x>=0&&x<n.x&&y>=0&&y<n.y&&z>=0&&z<n.z,"Native fluid cell outside actual table");
      for(int cz=z-(std::min)(z,d);cz<=z+(std::min)(n.z-z-1,d);cz++)for(int cy=y-(std::min)(y,d);cy<=y+(std::min)(n.y-y-1,d);cy++)for(int cx=x-(std::min)(x,d);cx<=x+(std::min)(n.x-x-1,d);cx++){
        const unsigned cell=unsigned(cx+cy*n.x+cz*n.w);Need(cell<cells.size(),"Boundary cell index invalid");const auto r=cells[cell];if(!r.y)continue;
        Need(r.x>=0&&r.y>=r.x&&unsigned(r.y)<=Npb,"Actual boundary cell range exposes inactive/nonboundary slots");for(unsigned b=unsigned(r.x);b<unsigned(r.y);b++){Need(CODE_IsFixed(a.code[b])&&!Retired(a.id[b]),"Actual cell query exposes a retired source");count++;}
      }
    }return count;
  }
public:
  Probe(){PorosityObserver=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    Need(!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall,"Genuine observer-only InitRun required");AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;SelecDevice(cfg->GpuId);Timersg->Config(false);Timersg->TmStart(TMG_Init,false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunGpu();FreePartsInit();Cu(cudaDeviceSynchronize());
    Need(PorosityObserver&&HydroMech&&!HydroMechDynamicSeepage&&Simulate2D&&TStep==STEP_Symplectic&&TKernel==KERNEL_Cubic&&TBoundary==BC_MDBC&&UseNormals&&BoundModeg&&BoundSlipModeg&&TangenVelg&&KplasticDkg,"Retained observer scope differs");
    Need(CaseNp==Total&&CaseNpb==Fixed&&CaseNfixed==Fixed&&CaseNfluid==Soil&&Dp==.04&&KernelH==float(.048)&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&Gravity==TFloat3(0,0,-9.81f),"Retained native geometry/material differs");
    Need(TimeMax==0&&!PartBegin&&!PeriActive&&!CaseNmoving&&!CaseNfloat&&!HydroMechDrainage&&!HydroMechFreeSeepage&&HydroMechTopLoadMode==HMLOAD_None&&!PoreShepardRegularization&&!SoilDamping&&!SoilBoundaryDerivativeSPR&&!SoilHourglassXi&&!HourglassGpu&&!Shifting&&!Damping&&!NoPenetration&&!Aceg&&!BoundDerivativeVelg,"Zero-step retirement scope differs");NoStep();
    const unsigned block=MkInfo->GetMkBlockByMkBound(2);Need(block<MkInfo->Size(),"Right MK block absent");const auto* mk=MkInfo->Mkblock(block);First=mk->Begin;Count=mk->Count;Need(mk->Bound&&CODE_IsFixed(mk->Code)&&mk->Mk==12&&First==1800&&Count==260,"Actual right native MK interval differs");
    State input=Capture();const auto initial=Map(input,false);
    // SAME ID-based CPU transport fields; GPU-only dk adds an explicit sort canary, not a material update.
    for(unsigned q=0;q<Np;q++){const unsigned id=input.id[q];const bool soil=id>=Fixed;const double j=1.+double(id%11)/65536.;input.j[q]=j;input.theta[q]=soil?(int(id%7)-3)/1024.:0.;
      input.v[q]=make_float4(soil?float(int(id%3)-1)/4096.f:0.f,0,soil?float(int(id%5)-2)/8192.f:0.f,float(double(SoilCte.PoreWaterRho)+(double(RhopZero)-SoilCte.PoreWaterRho)/j));
      const double a=double(id%13)/128.;input.sigma[q]=TSymMatrix3d(-32-a,8+a,16-a,-48+a,4-a,-64-a);input.k[q]=soil?float(id%17)/4096.f:0.f;input.dk[q]=soil?float(id%19)/8192.f:0.f;
      input.p0[q]=float(double(SoilCte.PoreWaterRho)*double(Gravity.z)*(input.z[q]-2.));input.p[q]=input.p0[q]+float(int(id%5)-2)*16.f;input.rate[q]=float(1024+id);input.load[q]=make_float3(0,0,0);}
    Up(Velrhopg,input.v);Up(Sigmag,input.sigma);Up(PoroJg,input.j);Up(Kplasticg,input.k);Up(KplasticDkg,input.dk);Up(PorePressg,input.p);Up(PorePress0g,input.p0);Up(HydroMechLoadAceg,input.load);
    std::ofstream retired(fs::path(cfg->DirOut)/"retired.csv"),soil(fs::path(cfg->DirOut)/"soil.csv"),walls(fs::path(cfg->DirOut)/"walls.csv");for(auto* f:{&retired,&soil,&walls})*f<<std::setprecision(17);
    retired<<"native_id,mk,original_slot,x,z,normal_x,normal_z,code_before,code_marked_ignore\n";
    soil<<"native_id,before_slot,after_slot,p_before,p_after_divide,p_after_projection,p0,J,kappa,sigma_xx,sigma_zz,initial_FS,after_retire_FS,new_surface,positive_projection,all_persistent_bits_before_projection,all_nonpressure_bits_after_projection,kappa_dk_before,kappa_dk_after\n";
    walls<<"native_id,slot,in_NpbOk,mode,x,z,slip,J,p,C11,C13,C31,C33,Ace_x,Ace_y,Ace_z,original_geometry_bits\n";
    unsigned marked=0,preserved=0,projected=0,newProjected=0,remainingRows=0,activeWalls=0;unsigned long long candidates=0;const auto oldInter=InterStep;InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();Need(Aceg&&!BoundDerivativeVelg,"Observer scratch allocation changed");
    Up(PoroThetag,input.theta);Up(PorePressRateg,input.rate); // Observer Pre clears these; retain nonuniform transport witnesses.
    try{
      {BorrowDerivative borrow(BoundDerivativeVelg,Np);Flags flags{PorosityFeedback,DynamicPorePressure,DynamicPoreWall,HydroMechFreeSeepage,PorosityFeedback,DynamicPorePressure,DynamicPoreWall,HydroMechFreeSeepage};PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;HydroMechFreeSeepage=false;
        ComputeFreeSurfaceTracking();Cu(cudaDeviceSynchronize());const State before=Capture();Map(before,false);
        // One event-only boundary Id/Code download and Code-prefix upload; no production CUDA kernel/API.
        const auto boundaryIds=Down(Idpg,Npb);auto boundaryCode=Down(Codeg,Npb);
        for(unsigned q=0;q<Npb;q++)if(Retired(boundaryIds[q])){Need(boundaryIds[q]==before.id[q]&&Bits(boundaryCode[q],before.code[q])&&CODE_IsFixed(boundaryCode[q])&&CODE_IsNormal(boundaryCode[q]),"Selected current boundary identity differs");const typecode old=boundaryCode[q];boundaryCode[q]=CODE_SetOutIgnore(old);marked++;retired<<boundaryIds[q]<<','<<mk->Mk<<','<<q<<','<<before.xy[q].x<<','<<before.z[q]<<','<<before.normal[q].x<<','<<before.normal[q].z<<','<<unsigned(old)<<','<<unsigned(boundaryCode[q])<<'\n';}
        Need(marked==Count,"Full current Npb selection did not find all target IDs");Up(Codeg,boundaryCode);BoundChanged=true;RunCellDivide(true);Cu(cudaDeviceSynchronize());NoStep();State after=Capture();const auto map=Map(after,true);
        Need(CellDivSingle->GetNpbOutIgnore()==Count&&!CellDivSingle->GetNpbOut()&&!CellDivSingle->GetNpfOut()&&!CellDivSingle->GetNpfOutIgnore(),"GPU divide did not use only intentional boundary-ignore retirement");
        Need(CaseNp==Total&&CaseNpb==Fixed&&CaseNfixed==Fixed&&CaseNfluid==Soil,"Original case/MK registry was rewritten");
        for(unsigned id=Fixed;id<Total;id++){Need(Equal(before,initial[id],after,map[id],true),"Soil persistent bits changed before free projection");preserved++;}
        HydroMechFreeSeepage=true;ApplyPorePressureBoundaries();Cu(cudaDeviceSynchronize());const State projection=Capture();Map(projection,true);
        for(unsigned id=Fixed;id<Total;id++){const unsigned q=map[id],old=initial[id];const bool sf=Surface(projection,q),was=Surface(before,old),clip=sf&&std::isfinite(after.p[q])&&after.p[q]>0;const float expected=clip?0.f:after.p[q];Need(Equal(before,old,projection,q,false)&&Bits(projection.p[q],expected),"Projection changed protected state or an unexpected pressure");projected+=unsigned(clip);newProjected+=unsigned(clip&&!was);
          soil<<id<<','<<old<<','<<q<<','<<before.p[old]<<','<<after.p[q]<<','<<projection.p[q]<<','<<projection.p0[q]<<','<<projection.j[q]<<','<<projection.k[q]<<','<<projection.sigma[q].xx<<','<<projection.sigma[q].zz<<','<<before.fs[old]<<','<<projection.fs[q]<<','<<(sf&&!was)<<','<<clip<<",1,1,"<<before.dk[old]<<','<<projection.dk[q]<<'\n';}
        candidates=BoundaryCandidates(projection);Need(preserved==Soil&&projected>0&&newProjected>0&&candidates>0,"Retirement/projection/remaining-source witnesses are empty");
        // Prescribed Ace=-g tests only remaining wall closure, never actual momentum/Darcy balance.
        Up(Aceg,std::vector<float3>(Np,make_float3(-Gravity.x,-Gravity.y,-Gravity.z)));ComputeDynamicPoreWallStateGpu();ComputeDynamicPoreWallMatrixGpu();ComputeDynamicPoreWallAccelerationGpu();Cu(cudaDeviceSynchronize());const State closed=Capture(true);
        for(unsigned id=0;id<Fixed;id++)if(!Retired(id)){const unsigned q=map[id],old=initial[id];Need(Bits(input.xy[old],closed.xy[q])&&Bits(input.z[old],closed.z[q])&&Bits(input.normal[old],closed.normal[q])&&input.slip[old]==closed.slip[q]&&Bits(input.code[old],closed.code[q]),"Remaining wall geometry/code/selector changed");remainingRows++;
          if(q<NpbOk&&closed.mode[q]==BMODE_MDBC2){activeWalls++;const auto c=closed.c[q];const auto ac=closed.ace[q];for(double v:{closed.j[q],double(closed.p[q]),c.a11,c.a12,c.a13,c.a21,c.a22,c.a23,c.a31,c.a32,c.a33,double(ac.x),double(ac.y),double(ac.z)})Need(std::isfinite(v),"Refreshed active GPU closure is nonfinite");walls<<id<<','<<q<<",1,"<<unsigned(closed.mode[q])<<','<<closed.xy[q].x<<','<<closed.z[q]<<','<<unsigned(closed.slip[q])<<','<<closed.j[q]<<','<<closed.p[q]<<','<<c.a11<<','<<c.a13<<','<<c.a31<<','<<c.a33<<','<<ac.x<<','<<ac.y<<','<<ac.z<<",1\n";}
          else{walls<<id<<','<<q<<','<<(q<NpbOk)<<','<<unsigned(closed.mode[q])<<','<<closed.xy[q].x<<','<<closed.z[q]<<','<<unsigned(closed.slip[q]);for(unsigned c=0;c<9;c++)walls<<',';walls<<",1\n";}}
        for(unsigned id=Fixed;id<Total;id++)Need(Equal(projection,map[id],closed,map[id],true),"Remaining wall closure changed soil persistent state");
        Need(remainingRows==1800&&activeWalls>0,"Remaining wall coverage incomplete");NoStep();borrow.Release();
      }
    }catch(...){PosInteraction_Forces();InterStep=oldInter;throw;}
    PosInteraction_Forces();InterStep=oldInter;Cu(cudaDeviceSynchronize());Need(!Aceg&&!BoundDerivativeVelg&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&!HydroMechFreeSeepage,"Private flags/scratch not restored");NoStep();
    for(auto* f:{&retired,&soil,&walls}){f->flush();Need(bool(*f),"CSV write failed");}
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<"{\"stage\":\"upl_wall_retire_gpu_r1\",\"passed\":true,\"retired_native_begin\":"<<First<<",\"retired_native_count\":"<<marked<<",\"active_native_count\":"<<Np<<",\"remaining_fixed\":"<<Npb<<",\"remaining_NpbOk\":"<<NpbOk<<",\"preserved_soil_IDs\":"<<preserved<<",\"GPU_kappa_dk_transport_checks\":"<<preserved<<",\"remaining_wall_rows\":"<<remainingRows<<",\"active_remaining_wall_closures\":"<<activeWalls<<",\"positive_projection_rows\":"<<projected<<",\"new_surface_positive_projection_rows\":"<<newProjected<<",\"actual_boundary_cell_candidates\":"<<candidates<<",\"retired_boundary_candidates\":0,\"boundary_Id_Code_download_mark_Code_upload\":true,\"new_production_CUDA_kernel_or_interface\":false,\"original_case_ID_registry_unchanged\":true,\"typed_member_bits_not_State_padding_compared\":true,\"geometry_compacted_not_restored\":true,\"borrowed_derivative_NULL_before_free_Pos\":true,\"prescribed_Ace_not_actual_force\":true,\"physical_steps\":0,\"production_release_event_tested\":false,\"prestress_or_restart_claimed\":false,\"new_numerical_tolerance\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=6&&std::string(argv[1])=="--retire","Use --retire -gpu:0 -stable -mdbc_freeslip SAME_OBSERVER_SEED FRESH_RESULT");AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=2;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(!cfg.Cpu&&cfg.GpuId==0&&cfg.Stable&&!cfg.PrintInfo&&!cfg.PartBegin&&!fs::exists(cfg.DirOut),"Fresh actualGPU0 stable zero-step output required");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr());return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"GPU wall retirement component failed; preserve partial output\n";return 2;}}

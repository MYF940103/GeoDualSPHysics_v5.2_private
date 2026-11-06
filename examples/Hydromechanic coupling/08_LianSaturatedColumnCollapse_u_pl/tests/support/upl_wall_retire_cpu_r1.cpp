// Actual case08 fixed-ID retirement and divide; zero steps, no production release control.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JSphMk.h"
#include "JCellDivCpuSingle.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "JCellSearch_inline.h"
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
JAppInfo AppInfo("WallRetireCpu","r1","07-11-2026");
namespace fs=std::filesystem;
static constexpr unsigned Total=7060,Fixed=2060,Soil=5000;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
template<class T>static bool Bits(const T& a,const T& b){return !std::memcmp(&a,&b,sizeof(T));}
struct BorrowDerivative{tfloat3*& p;tfloat3* old;BorrowDerivative(tfloat3*& a,tfloat3* b):p(a),old(a){Need(!a,"Derivative scratch already owned");p=b;}~BorrowDerivative(){p=old;}};
struct Flags{bool &f,&d,&w,&free;bool a,b,c,e;~Flags(){f=a;d=b;w=c;free=e;}};
struct State{tdouble3 x; tfloat4 v;tsymatrix3d sigma;double j,theta;float p,p0,k,rate;tfloat3 load;typecode code;};

class Probe:public JSphCpuSingle{
  unsigned First=0,Count=0;
  bool Retired(unsigned id)const{return id>=First&&id<First+Count;}
  void NoStep()const{Need(TimeStep==0&&Nstep==0&&!PosPrec&&!VelrhopPrec&&!PorePressPrec&&!PoroJPrec,"A predictor or physical step was entered");}
  std::vector<unsigned> Map(bool after)const{
    Need(Np==(after?Total-Count:Total)&&Npb==(after?Fixed-Count:Fixed),"Actual retained count differs");std::vector<unsigned> m(Total,UINT_MAX);unsigned soil=0,wall=0;
    for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(id<Total&&m[id]==UINT_MAX&&CODE_IsNormal(Codec[q]),"Unknown/duplicate/non-normal active ID");Need(!after||!Retired(id),"Retired native ID remains active");m[id]=q;
      if(id>=Fixed){Need(q>=Npb&&CODE_IsFluid(Codec[q]),"Soil moved into boundary prefix or changed type");soil++;}else{Need(q<Npb&&CODE_IsFixed(Codec[q]),"Remaining wall lost fixed prefix/type");wall++;}}
    for(unsigned id=0;id<Total;id++)Need((m[id]==UINT_MAX)==(after&&Retired(id)),"An unselected ID disappeared or a retired ID survived");
    Need(soil==Soil&&wall==(after?Fixed-Count:Fixed)&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Native soil/exclusion accounting changed");return m;
  }
  State Capture(unsigned q)const{return{Posc[q],Velrhopc[q],Sigmac[q],PoroJc[q],PoroThetac[q],PorePressc[q],PorePress0c[q],Kplasticc[q],PorePressRatec[q],HydroMechLoadAcec[q],Codec[q]};}
  bool Equal(const State& a,unsigned q,bool pressure)const{
    return Bits(a.x,Posc[q])&&Bits(a.v,Velrhopc[q])&&Bits(a.sigma,Sigmac[q])&&Bits(a.j,PoroJc[q])&&Bits(a.theta,PoroThetac[q])&&(!pressure||Bits(a.p,PorePressc[q]))&&Bits(a.p0,PorePress0c[q])&&Bits(a.k,Kplasticc[q])&&Bits(a.rate,PorePressRatec[q])&&Bits(a.load,HydroMechLoadAcec[q])&&Bits(a.code,Codec[q]);
  }
public:
  Probe(){PorosityObserver=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    Need(!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall,"Legitimate observer-only InitRun required");AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Need(PorosityObserver&&HydroMech&&!HydroMechDynamicSeepage&&Simulate2D&&TStep==STEP_Symplectic&&TKernel==KERNEL_Cubic&&TBoundary==BC_MDBC&&UseNormals&&BoundModec&&BoundSlipModec&&TangenVelc,"Retained case08 observer scope differs");
    Need(CaseNp==Total&&CaseNpb==Fixed&&CaseNfixed==Fixed&&CaseNfluid==Soil&&Dp==.04&&KernelH==float(.048)&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&Gravity==TFloat3(0,0,-9.81f),"Retained native geometry/material differs");
    Need(TimeMax==0&&!PartBegin&&!PeriActive&&!CaseNmoving&&!CaseNfloat&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!PoreShepardRegularization&&!SoilDamping&&!SoilBoundaryDerivativeSPR&&!SoilHourglassXi&&!HourglassCpu&&!Shifting&&!Damping&&!NoPenetration&&!Acec&&!BoundDerivativeVelc,"Zero-step retirement scope differs");NoStep();
    const unsigned block=MkInfo->GetMkBlockByMkBound(2);Need(block<MkInfo->Size(),"Designated right MK block absent");const auto* mk=MkInfo->Mkblock(block);First=mk->Begin;Count=mk->Count;
    Need(mk->Bound&&CODE_IsFixed(mk->Code)&&mk->Mk==12&&First==1800&&Count==260,"Actual right-wall native MK interval differs");const auto initial=Map(false);
    std::vector<tdouble3> wallPositions(Fixed);std::vector<tfloat3> wallNormals(Fixed);std::vector<byte> wallSlip(Fixed);
    for(unsigned id=0;id<Fixed;id++){const unsigned q=initial[id];wallPositions[id]=Posc[q];wallNormals[id]=BoundNormalc[q];wallSlip[id]=BoundSlipModec[q];}
    // Nonuniform transport canaries only: no geostatic state or material return is constructed.
    for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];const bool soil=id>=Fixed;const double j=1.+double(id%11)/65536.;PoroJc[q]=j;PoroThetac[q]=soil?(int(id%7)-3)/1024.:0.;
      Velrhopc[q]=TFloat4(soil?float(int(id%3)-1)/4096.f:0.f,0,soil?float(int(id%5)-2)/8192.f:0.f,float(double(SoilCte.PoreWaterRho)+(double(RhopZero)-SoilCte.PoreWaterRho)/j));
      const double a=double(id%13)/128.;Sigmac[q]=TSymMatrix3d(-32-a,8+a,16-a,-48+a,4-a,-64-a);Kplasticc[q]=soil?float(id%17)/4096.f:0.f;
      PorePress0c[q]=float(double(SoilCte.PoreWaterRho)*double(Gravity.z)*(Posc[q].z-2.));PorePressc[q]=PorePress0c[q]+float(int(id%5)-2)*16.f;PorePressRatec[q]=float(1024+id);HydroMechLoadAcec[q]=TFloat3(0);}
    std::ofstream retired(fs::path(cfg->DirOut)/"retired.csv"),soil(fs::path(cfg->DirOut)/"soil.csv"),walls(fs::path(cfg->DirOut)/"walls.csv");for(auto* f:{&retired,&soil,&walls})*f<<std::setprecision(17);
    retired<<"native_id,mk,original_slot,x,z,normal_x,normal_z,code_before,code_marked_ignore\n";
    soil<<"native_id,before_slot,after_slot,p_before,p_after_divide,p_after_projection,p0,J,kappa,sigma_xx,sigma_zz,initial_FS,after_retire_FS,new_surface,positive_projection,all_persistent_bits_before_projection,all_nonpressure_bits_after_projection\n";
    walls<<"native_id,slot,in_NpbOk,mode,x,z,slip,J,p,C11,C13,C31,C33,Ace_x,Ace_y,Ace_z,original_geometry_bits\n";
    unsigned marked=0,preserved=0,projected=0,newProjected=0,remainingRows=0,activeWalls=0;unsigned long long boundaryCandidates=0;
    const auto oldInter=InterStep;InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();Need(Acec&&!BoundDerivativeVelc,"Ordinary observer scratch allocation changed");
    try{
      std::vector<tfloat3> derivative(Total,TFloat3(0));
      {BorrowDerivative borrow(BoundDerivativeVelc,derivative.data());Flags flags{PorosityFeedback,DynamicPorePressure,DynamicPoreWall,HydroMechFreeSeepage,PorosityFeedback,DynamicPorePressure,DynamicPoreWall,HydroMechFreeSeepage};PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;HydroMechFreeSeepage=false;
        ComputeFreeSurfaceTracking();std::vector<State> before(Total);std::vector<unsigned> oldFS(Total);std::vector<bool> oldSurface(Total);
        for(unsigned id=0;id<Total;id++){before[id]=Capture(initial[id]);oldFS[id]=FSTypec[initial[id]];oldSurface[id]=IsFreeSurfaceParticle(initial[id],Codec,FSTypec);}
        for(unsigned q=0;q<Npb;q++)if(Retired(Idpc[q])){Need(CODE_IsFixed(Codec[q])&&CODE_IsNormal(Codec[q]),"Selected wall is not native fixed");const typecode old=Codec[q];Codec[q]=CODE_SetOutIgnore(old);marked++;retired<<Idpc[q]<<','<<mk->Mk<<','<<q<<','<<Posc[q].x<<','<<Posc[q].z<<','<<BoundNormalc[q].x<<','<<BoundNormalc[q].z<<','<<unsigned(old)<<','<<unsigned(Codec[q])<<'\n';}
        Need(marked==Count,"Whole Npb selection did not find all designated IDs");BoundChanged=true;RunCellDivide(true);NoStep();const auto after=Map(true);
        Need(CellDivSingle->GetNpbOutIgnore()==Count&&!CellDivSingle->GetNpbOut()&&!CellDivSingle->GetNpfOut()&&!CellDivSingle->GetNpfOutIgnore(),"Actual divide did not use only intentional boundary-ignore retirement");
        Need(CaseNp==Total&&CaseNpb==Fixed&&CaseNfixed==Fixed&&CaseNfluid==Soil,"Original case/MK ID registry was rewritten");std::vector<float> unprojected(Total);
        for(unsigned id=Fixed;id<Total;id++){const unsigned q=after[id];Need(Equal(before[id],q,true),"Soil persistent data changed before free projection");unprojected[id]=PorePressc[q];preserved++;}
        HydroMechFreeSeepage=true;ApplyPorePressureBoundaries();std::vector<float> projectedPressure(Total); // Actual new open-face mask and lawful completed-state projection.
        for(unsigned id=Fixed;id<Total;id++){const unsigned q=after[id];const bool sf=IsFreeSurfaceParticle(q,Codec,FSTypec),was=oldSurface[id];const bool clip=sf&&std::isfinite(unprojected[id])&&unprojected[id]>0;const float expected=(clip?0.f:unprojected[id]);projectedPressure[id]=PorePressc[q];
          Need(Equal(before[id],q,false)&&Bits(PorePressc[q],expected),"Projection changed protected state or an unexpected pressure");projected+=unsigned(clip);newProjected+=unsigned(clip&&!was);
          soil<<id<<','<<initial[id]<<','<<q<<','<<before[id].p<<','<<unprojected[id]<<','<<PorePressc[q]<<','<<PorePress0c[q]<<','<<PoroJc[q]<<','<<Kplasticc[q]<<','<<Sigmac[q].xx<<','<<Sigmac[q].zz<<','<<oldFS[id]<<','<<FSTypec[q]<<','<<(sf&&!was)<<','<<clip<<",1,1\n";
          const auto ngs=nsearch::Init(Dcellc[q],true,DivData);for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){const auto range=nsearch::ParticleRange(y,z,ngs,DivData);for(unsigned b=range.x;b<range.y;b++){Need(b<Npb&&CODE_IsFixed(Codec[b])&&!Retired(Idpc[b]),"Actual boundary cell query still exposes a retired source");boundaryCandidates++;}}
        }
        Need(preserved==Soil&&projected>0&&newProjected>0&&boundaryCandidates>0,"Retirement/projection/remaining-source witnesses are empty");
        // Prescribed native acceleration is only for the wall extension; no actual momentum or Darcy solve.
        for(unsigned q=0;q<Np;q++)Acec[q]=TFloat3(-Gravity.x,-Gravity.y,-Gravity.z);ComputeDynamicPoreWallStateCpu();ComputeDynamicPoreWallMatrixCpu();ComputeDynamicPoreWallAccelerationCpu();
        for(unsigned id=0;id<Fixed;id++)if(!Retired(id)){const unsigned q=after[id];const bool geometry=Bits(wallPositions[id],Posc[q])&&Bits(wallNormals[id],BoundNormalc[q])&&wallSlip[id]==BoundSlipModec[q]&&Bits(before[id].code,Codec[q]);Need(geometry,"Remaining wall geometry, code or selector changed");remainingRows++;
          if(q<NpbOk&&BoundModec[q]==BMODE_MDBC2){activeWalls++;const auto c=CorrMatc[q];for(double v:{PoroJc[q],double(PorePressc[q]),c.a11,c.a12,c.a13,c.a21,c.a22,c.a23,c.a31,c.a32,c.a33,double(Acec[q].x),double(Acec[q].y),double(Acec[q].z)})Need(std::isfinite(v),"Refreshed active closure is nonfinite");walls<<id<<','<<q<<",1,"<<unsigned(BoundModec[q])<<','<<Posc[q].x<<','<<Posc[q].z<<','<<unsigned(BoundSlipModec[q])<<','<<PoroJc[q]<<','<<PorePressc[q]<<','<<c.a11<<','<<c.a13<<','<<c.a31<<','<<c.a33<<','<<Acec[q].x<<','<<Acec[q].y<<','<<Acec[q].z<<",1\n";}
          else{walls<<id<<','<<q<<','<<(q<NpbOk)<<','<<unsigned(BoundModec[q])<<','<<Posc[q].x<<','<<Posc[q].z<<','<<unsigned(BoundSlipModec[q]);for(unsigned c=0;c<9;c++)walls<<',';walls<<",1\n";}
        }
        for(unsigned id=Fixed;id<Total;id++)Need(Equal(before[id],after[id],false)&&Bits(PorePressc[after[id]],projectedPressure[id]),"Wall closure changed soil persistent state");
        Need(remainingRows==1800&&activeWalls>0,"Remaining wall coverage is incomplete");NoStep();
      }
    }catch(...){PosInteraction_Forces();InterStep=oldInter;throw;}
    PosInteraction_Forces();InterStep=oldInter;Need(!Acec&&!BoundDerivativeVelc&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&!HydroMechFreeSeepage,"Scratch/private selectors not restored");NoStep();
    for(auto* f:{&retired,&soil,&walls}){f->flush();Need(bool(*f),"CSV write failed");}
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<"{\"stage\":\"upl_wall_retire_cpu_r1\",\"passed\":true,\"retired_native_begin\":"<<First<<",\"retired_native_count\":"<<marked<<",\"active_native_count\":"<<Np<<",\"remaining_fixed\":"<<Npb<<",\"remaining_NpbOk\":"<<NpbOk<<",\"preserved_soil_IDs\":"<<preserved<<",\"remaining_wall_rows\":"<<remainingRows<<",\"active_remaining_wall_closures\":"<<activeWalls<<",\"positive_projection_rows\":"<<projected<<",\"new_surface_positive_projection_rows\":"<<newProjected<<",\"actual_boundary_cell_candidates\":"<<boundaryCandidates<<",\"retired_boundary_candidates\":0,\"original_case_ID_registry_unchanged\":true,\"persistent_member_bits_not_struct_padding_compared\":true,\"geometry_compacted_not_restored\":true,\"prescribed_Ace_not_actual_force\":true,\"physical_steps\":0,\"production_release_event_tested\":false,\"prestress_or_restart_claimed\":false,\"new_numerical_tolerance\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=6&&std::string(argv[1])=="--retire","Use --retire -cpu -ompthreads:1 -stable -mdbc_freeslip SAME_OBSERVER_SEED FRESH_RESULT");AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=2;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!fs::exists(cfg.DirOut),"Fresh CPU zero-step result required");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr());return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Wall retirement component failed; preserve actual partial output\n";return 2;}}

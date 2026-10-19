// Manufactured fields through real production mDBC entry points. No copied MLS.
// This tests scalar reconstruction and field isolation, not physical acceptance.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <vector>

JAppInfo AppInfo("MdbcScalarCheck","v1","17-10-2026");
namespace fs=std::filesystem;
static void Check(bool okay,const char* message){if(!okay)throw std::runtime_error(message);}
template<class T> static bool Same(const std::vector<T>& saved,const T* current){
  return std::memcmp(saved.data(),current,saved.size()*sizeof(T))==0;
}

class MdbcScalarCheck:public JSphCpuSingle{
  std::ofstream Rows;
  unsigned Trials=0,NativeWalls=0,PeriodicWalls=0;
  double MaxVelocityError=0,MaxPressureError=0,MaxVelocityRelative=0,MaxPressureRelative=0;
  struct Wall{unsigned p,neighbors;tdouble3 ghost;};
  std::vector<Wall> Walls;

  void SelectWalls(){
    std::map<unsigned,unsigned> native;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p]))
      Check(native.emplace(Idpc[p],p).second,"Duplicate native particle ID");
    Check(native.size()==1040,"Expected case-02 1040 native particles");
    for(unsigned p=0;p<NpbOk;p++){
      if(CODE_IsFluid(Codec[p])||BoundNormalc[p]==TFloat3(0))continue;
      Check(CODE_IsFixed(Codec[p]),"Only stationary native/periodic walls are admitted");
      tdouble3 g=Posc[p]+ToTDouble3(BoundNormalc[p]);
      if(PeriActive)g=UpdatePeriodicPos(g);
      // Independent geometric support check; deliberately no kernel/matrix copy.
      // This does not assert the production determinant branch. All selected
      // walls still have to reproduce the affine field in the actual function.
      std::vector<tdouble3> support;
      for(unsigned q=0;q<Np;q++)if(CODE_IsFluid(Codec[q])&&Velrhopc[q].w>0){
        const double dx=g.x-Posc[q].x,dz=g.z-Posc[q].z;
        if(dx*dx+dz*dz<double(KernelSize2))support.push_back(Posc[q]);
      }
      bool noncollinear=false;
      for(unsigned a=1;a<support.size()&&!noncollinear;a++)
        for(unsigned b=a+1;b<support.size();b++){
          const auto u=support[a]-support[0],v=support[b]-support[0];
          if(std::fabs(u.x*v.z-u.z*v.x)>1e-6*Dp*Dp){noncollinear=true;break;}
        }
      Check(support.size()>=3&&noncollinear,"Unsupported or rank-deficient wall: no affine claim allowed");
      Walls.push_back({p,unsigned(support.size()),g});
      if(CODE_IsNormal(Codec[p]))NativeWalls++;
      else if(CODE_IsPeriodic(Codec[p]))PeriodicWalls++;
      else Check(false,"Unexpected selected wall special code");
    }
    Check(NativeWalls==40&&!Walls.empty(),"Expected all 40 native case-02 walls to be supported");
    Check(!PeriActive||PeriodicWalls>0,"Periodic-wall coverage missing");
  }

  void Trial(const char* name,bool pressure,double slope,double intercept){
    // Only manufactured values are changed. Geometry/density/normal/code and
    // the production configuration remain those of the validated case.
    for(unsigned p=0;p<Np;p++){
      Velrhopc[p].x=Velrhopc[p].y=0;
      Velrhopc[p].z=(CODE_IsFluid(Codec[p])?float(slope*Posc[p].z+intercept):0.f);
      PorePress0c[p]=32.f+float(Idpc[p]%8);
      PorePressc[p]=(CODE_IsFluid(Codec[p])?float(double(PorePress0c[p])+slope*Posc[p].z+intercept):-321.f);
    }
    const std::vector<tfloat4> velocity(Velrhopc,Velrhopc+Np);
    const std::vector<float> pore(PorePressc,PorePressc+Np),pore0(PorePress0c,PorePress0c+Np);
    const std::vector<tdouble3> positions(Posc,Posc+Np);
    PreInteraction_Forces();
    Check(BoundDerivativeVzc!=NULL,"SPR force-stage auxiliary array was not allocated");
    for(unsigned p=0;p<Npb;p++)BoundDerivativeVzc[p]=123.f;
    const std::vector<float> auxiliary(BoundDerivativeVzc,BoundDerivativeVzc+Npb);
    if(pressure)InteractionPorePressureMdbcCorrection();
    else ComputeBoundaryDerivativeVelocity();
    Check(Same(velocity,Velrhopc)&&Same(pore0,PorePress0c)&&Same(positions,Posc),"Reconstruction altered physical velocity/reference pore pressure/geometry");
    if(pressure){
      Check(Same(auxiliary,BoundDerivativeVzc),"Pore reconstruction altered derivative velocity");
      for(unsigned p=0;p<Np;p++)if(CODE_IsFluid(Codec[p]))
        Check(std::memcmp(&pore[p],PorePressc+p,sizeof(float))==0,"Pore reconstruction altered soil pressure");
    }
    else Check(Same(pore,PorePressc),"Velocity reconstruction altered pore pressure");
    for(const auto& wall:Walls){
      const unsigned p=wall.p;
      const double scalar=slope*wall.ghost.z+intercept;
      const double expected=(pressure?double(PorePress0c[p])+scalar:-scalar);
      const double actual=(pressure?double(PorePressc[p]):double(BoundDerivativeVzc[p]));
      // Predeclared absolute-plus-relative float-roundoff allowance. No fitted
      // tolerance and no acceptance relaxation for a fallback wall.
      const double tolerance=32.*FLT_EPSILON*(std::max)(1.,std::fabs(expected));
      const double error=std::fabs(actual-expected);
      const double relative=error/std::fabs(expected); // All admitted fields are nonzero here.
      Rows<<name<<','<<p<<','<<Idpc[p]<<','<<(CODE_IsPeriodic(Codec[p])?1:0)
        <<','<<wall.neighbors<<','<<Posc[p].x<<','<<Posc[p].z
        <<','<<wall.ghost.x<<','<<wall.ghost.z<<','<<actual<<','<<expected
        <<','<<error<<','<<relative<<','<<tolerance<<'\n';
      Rows.flush();Check(bool(Rows),"Manufactured-field row write failed");
      Check(std::isfinite(actual)&&error<=tolerance,"Manufactured scalar reproduction failed; see scalar_rows.csv");
      double& maximum=(pressure?MaxPressureError:MaxVelocityError);
      maximum=(std::max)(maximum,error);
      double& maxrelative=(pressure?MaxPressureRelative:MaxVelocityRelative);
      maxrelative=(std::max)(maxrelative,relative);
    }
    PosInteraction_Forces();Trials++;
  }

  void Disabled(){
    const std::vector<tfloat4> velocity(Velrhopc,Velrhopc+Np);
    const std::vector<float> pore(PorePressc,PorePressc+Np),pore0(PorePress0c,PorePress0c+Np);
    PreInteraction_Forces();
    Check(BoundDerivativeVzc==NULL,"Disabled SPR allocated derivative velocity");
    ComputeBoundaryDerivativeVelocity();
    Check(BoundDerivativeVzc==NULL&&Same(velocity,Velrhopc)&&Same(pore,PorePressc)&&Same(pore0,PorePress0c),"Disabled SPR was not a no-op");
    PosInteraction_Forces();Trials++;
  }
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(cfg->SvTimers);Timersc->TmStart(TMC_Init);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunCpu();
    Check(HydroMech&&Simulate2D&&TKernel==KERNEL_Wendland&&TStep==STEP_Symplectic&&!PartBegin&&TimeStep==0,"Requires fresh 2D Wendland Symplectic case-02 input");
    Check(!CaseNmoving&&!CaseNfloat&&UseNormals&&BoundNormalc&&PorePressc&&PorePress0c,"Requires supported fixed mDBC pore geometry");
    FreePartsInit();SelectWalls();
    const fs::path out(cfg->DirOut);
    Rows.open(out/"scalar_rows.csv");Rows<<std::setprecision(17)
      <<"trial,index,native_id,periodic,support_count,x,z,ghost_x,ghost_z,actual,expected,error,relative_error,tolerance\n";
    if(SoilBoundaryDerivativeSPR){
      Trial("velocity_constant",false,0.,.25);
      Trial("velocity_affine_z",false,.125,.5);
      Trial("pore_constant",true,0.,64.);
      Trial("pore_affine_z",true,3.,64.);
    }
    else Disabled();
    std::ofstream done(out/"scalar_complete.json");done<<std::setprecision(17)
      <<"{\"passed\":true,\"spr_enabled\":"<<(SoilBoundaryDerivativeSPR?"true":"false")
      <<",\"trials\":"<<Trials<<",\"native_walls\":"<<NativeWalls<<",\"periodic_walls\":"<<PeriodicWalls
      <<",\"max_velocity_error\":"<<MaxVelocityError<<",\"max_pressure_error\":"<<MaxPressureError
      <<",\"max_velocity_relative_error\":"<<MaxVelocityRelative<<",\"max_pressure_relative_error\":"<<MaxPressureRelative
      <<",\"tolerance\":\"32*FLT_EPSILON*max(1,abs(expected))\",\"copied_mls\":false"
      <<",\"time_integrated\":false,\"physical_acceptance\":false,\"scope\":\"case02_horizontal_2d_scalar_only\"}\n";
    done.flush();Check(bool(done),"Manufactured-field completion write failed");
    std::cout<<"PASS scalar trials="<<Trials<<" native_walls="<<NativeWalls<<" periodic_walls="<<PeriodicWalls<<'\n';
  }
};

int main(int argc,char** argv){
  try{
    AppInfo.ConfigRunPaths(argv[0]);JSphCfgRun cfg;cfg.LoadArgv(argc,argv);cfg.Cpu=true;
    cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;
    Check(!fs::exists(cfg.DirOut),"Output exists; choose a new label");
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);
    AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    MdbcScalarCheck fixture;fixture.Execute(&cfg,AppInfo.LogPtr());return 0;
  }
  catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Production exception; inspect Run.out\n";return 2;}
}

// All-wall multi-plane counterpart to spr_planes_test.cpp. Real GPU MLS/consumers.
#include "JSphGpuSingle.h"
#include "JSphGpu_ker.h"
#include "JSphCfgRun.h"
#include "JDsTimersGpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include <cuda_runtime.h>
#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>

JAppInfo AppInfo("SprGpuPlanesCheck","v1","24-10-2026");
namespace fs=std::filesystem;
static void Check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
static void Cu(cudaError_t e){Check(e==cudaSuccess,cudaGetErrorString(e));}
template<class T> static std::vector<T> Down(const T* p,unsigned n){std::vector<T> v(n);Cu(cudaMemcpy(v.data(),p,n*sizeof(T),cudaMemcpyDeviceToHost));return v;}
template<class T> static void Up(T* p,const std::vector<T>& v){Cu(cudaMemcpy(p,v.data(),v.size()*sizeof(T),cudaMemcpyHostToDevice));}
template<class T> static bool Same(const std::vector<T>& a,const std::vector<T>& b){return a.size()==b.size()&&!memcmp(a.data(),b.data(),a.size()*sizeof(T));}

class SprGpuPlanesCheck:public JSphGpuSingle{
  std::vector<tdouble3> Position;
  std::vector<float3> Normals;
  std::vector<unsigned> Id;
  std::vector<typecode> Codes;
  std::vector<byte> Modes;
  std::vector<float4> Physical;
  bool Active(unsigned p)const{return p<NpbOk&&(SlipMode==SLIP_Vel0||Modes[p]!=BMODE_MDBC2OFF);}
  float3 Oracle(unsigned p,bool affine)const{
    if(!Active(p))return make_float3(Physical[p].x,Physical[p].y,Physical[p].z);
    const auto b=Normals[p];const double len=sqrt(double(b.x)*b.x+double(b.y)*b.y+double(b.z)*b.z);
    const tdouble3 n=TDouble3(b.x/len,b.y/len,b.z/len),g=Position[p]+TDouble3(b.x,b.y,b.z);
    const tdouble3 v=(affine?g*.4:TDouble3(.5,Simulate2D?0.:.25,.75));
    const double vn=v.x*n.x+v.y*n.y+v.z*n.z;
    const tdouble3 expected=(SlipMode==SLIP_NoSlip?v*(-1.):(SlipMode==SLIP_FreeSlip?v-n*(2*vn):n*(-vn)));
    return make_float3(float(expected.x),float(expected.y),float(expected.z));
  }
  void ClearRates(){
    Cu(cudaMemset(Arg,0,Np*sizeof(float)));Cu(cudaMemset(PorePressRateg,0,Np*sizeof(float)));
    Cu(cudaMemset(Rsigmag,0,Np*sizeof(tsymatrix3f)));Cu(cudaMemset(Aceg,0,Np*sizeof(float3)));Cu(cudaMemset(ViscDtg,0,Np*sizeof(float)));
  }
  void Interaction(){
    ClearRates();
    const StInterParmsg p=StrInterParmsg(Simulate2D,false,TKernel,FtMode,false,TDensity,ShiftingMode,TMdbc2,
      Visco*ViscoBoundFactor,Visco,BlockSizes.forcesbound,BlockSizes.forcesfluid,Np,Npb,NpbOk,0,Nstep,DivData,Dcellg,
      Posxyg,Poszg,PosCellg,Velrhopg,Idpg,Codeg,FtoMasspg,SpsTaug,NULL,CorrMatg,BoundModeg,BoundSlipModeg,TangenVelg,
      MotionVelg,BoundNormalg,NoPenShiftg,ViscDtg,Arg,Aceg,Deltag,SpsGradvelg,Sigmag,Rsigmag,ArtificialStressg,
      PorePressg,PorePressRateg,FSTypeg,FSNormalg,false,HydroMechLoadAceg,HydroMechTopLoadRawg,ShiftPosfsg,NULL,NULL,BoundDerivativeVelg);
    cusph::Interaction_Forces(p);Cu(cudaDeviceSynchronize());
  }
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;SelecDevice(cfg->GpuId);Timersg->Config(false);Timersg->TmStart(TMG_Init,false);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunGpu();FreePartsInit();
    Check(SoilBoundaryDerivativeSPR&&!HourglassGpu&&!PeriActive&&!NoPenetration,"Unexpected fixture options");
    Check(!SoilDamping&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None,"Fixture isolation failed");
    Id=Down(Idpg,Np);Codes=Down(Codeg,Np);Normals=Down(BoundNormalg,Np);
    const auto xy=Down(Posxyg,Np);const auto z=Down(Poszg,Np);Position.resize(Np);
    for(unsigned p=0;p<Np;p++)Position[p]=TDouble3(xy[p].x,xy[p].y,z[p]);
    std::vector<double3> fit;
    if(BoundDerivativeFitShiftg)fit=Down(BoundDerivativeFitShiftg,CaseNpb);
    std::ofstream wall(fs::path(cfg->DirOut)/"wall.csv"),soil(fs::path(cfg->DirOut)/"soil.csv");
    wall<<std::setprecision(17)<<"trial,id,x,y,z,gx,gy,gz,fx,fy,fz,active,component,actual,oracle,error,tolerance\n";
    soil<<std::setprecision(17)<<"id,component,mls,oracle,difference,tolerance\n";
    unsigned bad[2]={0,0},active=0;double maxerror[2]={0,0},maxrate[3]={0,0,0};bool consumers=true;
    for(unsigned trial=0;trial<2;trial++){
      std::vector<float4> field(Np);
      for(unsigned p=0;p<Np;p++){
        const tdouble3 v=(CODE_IsFluid(Codes[p])?(trial?Position[p]*.4:TDouble3(.5,Simulate2D?0.:.25,.75)):TDouble3(0));
        field[p]=make_float4(float(v.x),float(v.y),float(v.z),RhopZero);
      }
      Up(Velrhopg,field);Cu(cudaMemset(PorePressg,0,Np*sizeof(float)));Cu(cudaMemset(PorePress0g,0,Np*sizeof(float)));
      Cu(cudaMemset(Sigmag,0,Np*sizeof(tsymatrix3d)));Cu(cudaMemset(Kplasticg,0,Np*sizeof(float)));
      InterStep=INTERSTEP_SymPredictor;MdbcBoundCorrection();PreInteraction_Forces();ComputeFreeSurfaceTracking();
      Physical=Down(Velrhopg,Np);if(BoundModeg)Modes=Down(BoundModeg,Np);
      const auto pressure=Down(PorePressg,Np);ComputeBoundaryDerivativeVelocity();Cu(cudaDeviceSynchronize());
      Check(Same(Physical,Down(Velrhopg,Np))&&Same(pressure,Down(PorePressg,Np))&&Same(xy,Down(Posxyg,Np))&&Same(z,Down(Poszg,Np)),"Reconstruction altered physical state");
      const auto actual=Down(BoundDerivativeVelg,Npb);std::vector<float3> oracle(Npb);
      for(unsigned p=0;p<Npb;p++){
        oracle[p]=Oracle(p,trial!=0);const auto a=actual[p],b=oracle[p];const auto normal=Normals[p];
        const tdouble3 g=Position[p]+TDouble3(normal.x,normal.y,normal.z);
        const auto shift=(fit.empty()?make_double3(0,0,0):fit[Id[p]]);const tdouble3 centre=g+TDouble3(shift.x,shift.y,shift.z);
        if(trial&&Active(p))active++;
        for(unsigned j=0;j<3;j++){
          const double av=(j==0?a.x:(j==1?a.y:a.z)),bv=(j==0?b.x:(j==1?b.y:b.z));
          const double error=fabs(av-bv),tol=32*FLT_EPSILON*(std::max)(.125,fabs(bv));Check(std::isfinite(av),"Nonfinite auxiliary velocity");
          wall<<trial<<','<<Id[p]<<','<<Position[p].x<<','<<Position[p].y<<','<<Position[p].z<<','<<g.x<<','<<g.y<<','<<g.z<<','<<centre.x<<','<<centre.y<<','<<centre.z<<','<<Active(p)<<','<<j<<','<<av<<','<<bv<<','<<error<<','<<tol<<'\n';
          if(error>tol)bad[trial]++;maxerror[trial]=(std::max)(maxerror[trial],error);
        }
      }
      if(trial){
        Interaction();const auto rm=Down(Arg,Np),pm=Down(PorePressRateg,Np);const auto sm=Down(Rsigmag,Np);
        Up(BoundDerivativeVelg,oracle);Interaction();const auto ro=Down(Arg,Np),po=Down(PorePressRateg,Np);const auto so=Down(Rsigmag,Np);
        for(unsigned p=Npb;p<Np;p++){
          const double a[8]={sm[p].xx,sm[p].yy,sm[p].zz,sm[p].xy,sm[p].yz,sm[p].xz,pm[p],rm[p]};
          const double b[8]={so[p].xx,so[p].yy,so[p].zz,so[p].xy,so[p].yz,so[p].xz,po[p],ro[p]};
          for(unsigned j=0;j<8;j++){
            const unsigned group=(j<6?0:(j==6?1:2));const double tol=(group==0?20:(group==1?2000:.02))+2e-5*fabs(b[j]);
            const double diff=fabs(a[j]-b[j]);Check(std::isfinite(a[j])&&std::isfinite(b[j]),"Nonfinite consumer");
            consumers=consumers&&diff<=tol;maxrate[group]=(std::max)(maxrate[group],diff);
            soil<<Id[p]<<','<<j<<','<<a[j]<<','<<b[j]<<','<<diff<<','<<tol<<'\n';
          }
        }
      }
      PosInteraction_Forces();
    }
    const bool passed=(!bad[0]&&!bad[1]&&consumers&&active==Npb);
    std::ofstream done(fs::path(cfg->DirOut)/"planes_complete.json");
    done<<std::setprecision(17)<<"{\"diagnostic_completed\":true,\"passed\":"<<(passed?"true":"false")<<",\"native_count\":"<<Np<<",\"wall_count\":"<<Npb
      <<",\"active_wall_count\":"<<active<<",\"constant_bad_components\":"<<bad[0]<<",\"affine_bad_components\":"<<bad[1]
      <<",\"max_constant_error\":"<<maxerror[0]<<",\"max_affine_error\":"<<maxerror[1]<<",\"consumer_max\":["<<maxrate[0]<<','<<maxrate[1]<<','<<maxrate[2]
      <<"],\"time_integrated\":false,\"physical_acceptance\":false}\n";
    done.flush();wall.flush();soil.flush();Check(bool(done)&&bool(wall)&&bool(soil),"Diagnostic write failed");
    std::cout<<"GPU planes complete, passed="<<passed<<'\n';
  }
};

int main(int argc,char** argv){
  try{
    AppInfo.ConfigRunPaths(argv[0]);JSphCfgRun cfg;cfg.LoadArgv(argc,argv);cfg.Cpu=false;cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;
    Check(!fs::exists(cfg.DirOut),"Choose a new output label");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    SprGpuPlanesCheck fixture;fixture.Execute(&cfg,AppInfo.LogPtr());return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Production exception; inspect Run.out\n";return 2;}
}

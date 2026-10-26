// Multiple fixed-plane diagnostic: production initialization, MLS and S/P/R.
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
#include <stdexcept>
#include <vector>

JAppInfo AppInfo("SprPlanesCheck","v1","24-10-2026");
namespace fs=std::filesystem;
static void Check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}

class SprPlanesCheck:public JSphCpuSingle{
  tfloat3 Oracle(unsigned p,bool affine)const{
    const TpSlipMode mode=GetMdbcSlipModeByCode(Codec[p]);
    const tdouble3 g=Posc[p]+ToTDouble3(BoundNormalc[p]);
    const tdouble3 vg=(affine? g*.4: TDouble3(.5,Simulate2D?0.:.25,.75));
    if(mode>=SLIP_NoSlip&&BoundModec[p]==BMODE_MDBC2OFF)
      return TFloat3(Velrhopc[p].x,Velrhopc[p].y,Velrhopc[p].z);
    const tdouble3 b=ToTDouble3(BoundNormalc[p]);
    const tdouble3 n=b/sqrt(b.x*b.x+b.y*b.y+b.z*b.z);
    const double vn=vg.x*n.x+vg.y*n.y+vg.z*n.z;
    if(mode==SLIP_NoSlip)return ToTFloat3(vg*(-1.));
    return ToTFloat3(mode==SLIP_FreeSlip? vg-n*(2*vn): n*(-vn));
  }
  void Interaction(){
    memset(Arc,0,Np*sizeof(float));memset(PorePressRatec,0,Np*sizeof(float));
    memset(Rsigmac,0,Np*sizeof(tsymatrix3f));memset(Acec,0,Np*sizeof(tfloat3));
    const stinterparmsc p=StInterparmsc(Np,Npb,NpbOk,DivData,Dcellc,Posc,Velrhopc,Idpc,Codec,Pressc,
      PorePressc,PorePressRatec,FSTypec,FSNormalc,NULL,CorrMatc,Arc,Acec,Deltac,ShiftingMode,ShiftPosfsc,
      SpsTauc,SpsGradvelc,Sigmac,Rsigmac,ArtificialStressc);
    StInterResultc result;result.viscdt=0;JSphCpu::Interaction_Forces_ct(p,result);
  }
public:
  void Execute(const JSphCfgRun *cfg,JLog2 *log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(cfg->SvTimers);Timersc->TmStart(TMC_Init);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunCpu();FreePartsInit();
    Check(SoilBoundaryDerivativeSPR&&!HourglassCpu&&!PeriActive&&!NoPenetration,"Unexpected fixture options");
    std::ofstream rows(fs::path(cfg->DirOut)/"wall.csv"),soil(fs::path(cfg->DirOut)/"soil.csv");
    rows<<std::setprecision(17)<<"trial,id,x,y,z,gx,gy,gz,fx,fy,fz,active,component,actual,oracle,error,tolerance\n";
    soil<<std::setprecision(17)<<"id,component,mls,oracle,difference,tolerance,affine_theory\n";
    unsigned bad[2]={0,0},active=0;double maxerror[2]={0,0},maxrate[3]={0,0,0};bool consumers=true;
    for(unsigned trial=0;trial<2;trial++){
      for(unsigned p=0;p<Np;p++){
        const tdouble3 v=(CODE_IsFluid(Codec[p])? (trial?Posc[p]*.4:TDouble3(.5,Simulate2D?0.:.25,.75)):TDouble3(0));
        Velrhopc[p]=TFloat4(float(v.x),float(v.y),float(v.z),RhopZero);
        PorePressc[p]=PorePress0c[p]=0;Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;
      }
      InterStep=INTERSTEP_SymPredictor;MdbcBoundCorrection();PreInteraction_Forces();ComputeFreeSurfaceTracking();
      const std::vector<tfloat4> physical(Velrhopc,Velrhopc+Np);
      const std::vector<tdouble3> positions(Posc,Posc+Np);
      ComputeBoundaryDerivativeVelocity();
      Check(!memcmp(physical.data(),Velrhopc,Np*sizeof(tfloat4))&&!memcmp(positions.data(),Posc,Np*sizeof(tdouble3)),"Reconstruction altered physical state");
      for(unsigned p=0;p<Npb;p++){
        const tfloat3 expected=Oracle(p,trial!=0),actual=BoundDerivativeVelc[p];
        const tdouble3 g=Posc[p]+ToTDouble3(BoundNormalc[p]);
        const tdouble3 fit=g+(BoundDerivativeFitShift.empty()? TDouble3(0): BoundDerivativeFitShift[Idpc[p]]);
        const bool use=(GetMdbcSlipModeByCode(Codec[p])==SLIP_Vel0||BoundModec[p]!=BMODE_MDBC2OFF);
        if(trial&&use)active++;
        for(unsigned j=0;j<3;j++){
          const double a=(j==0?actual.x:(j==1?actual.y:actual.z)),b=(j==0?expected.x:(j==1?expected.y:expected.z));
          const double error=fabs(a-b),tol=32*FLT_EPSILON*(std::max)(.125,fabs(b));
          Check(std::isfinite(a),"Nonfinite derivative velocity");
          rows<<trial<<','<<Idpc[p]<<','<<Posc[p].x<<','<<Posc[p].y<<','<<Posc[p].z<<','<<g.x<<','<<g.y<<','<<g.z<<','<<fit.x<<','<<fit.y<<','<<fit.z<<','<<use<<','<<j<<','<<a<<','<<b<<','<<error<<','<<tol<<'\n';
          if(error>tol)bad[trial]++;maxerror[trial]=(std::max)(maxerror[trial],error);
        }
      }
      if(trial){
        Interaction();
        const std::vector<float> rho(Arc,Arc+Np),pw(PorePressRatec,PorePressRatec+Np);
        const std::vector<tsymatrix3f> sigma(Rsigmac,Rsigmac+Np);
        for(unsigned p=0;p<Npb;p++)BoundDerivativeVelc[p]=Oracle(p,true);
        Interaction();
        for(unsigned p=Npb;p<Np;p++){
          const double a[8]={sigma[p].xx,sigma[p].yy,sigma[p].zz,sigma[p].xy,sigma[p].yz,sigma[p].xz,pw[p],rho[p]};
          const double b[8]={Rsigmac[p].xx,Rsigmac[p].yy,Rsigmac[p].zz,Rsigmac[p].xy,Rsigmac[p].yz,Rsigmac[p].xz,PorePressRatec[p],Arc[p]};
          const double div=(Simulate2D?.8:1.2),lambda=double(SoilCte.ModulusK)-2*double(SoilCte.ModulusG)/3;
          const double normal=.8*double(SoilCte.ModulusG)+lambda*div;
          const double analytic[8]={normal,(Simulate2D?lambda*div:normal),normal,0,0,0,-double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity*div,-RhopZero*div};
          for(unsigned j=0;j<8;j++){
            const unsigned group=(j<6?0:(j==6?1:2));const double tol=(group==0?20:(group==1?2000:.02))+2e-5*fabs(b[j]);
            const double diff=fabs(a[j]-b[j]);Check(std::isfinite(a[j])&&std::isfinite(b[j]),"Nonfinite consumer");
            consumers=consumers&&diff<=tol;maxrate[group]=(std::max)(maxrate[group],diff);
            soil<<Idpc[p]<<','<<j<<','<<a[j]<<','<<b[j]<<','<<diff<<','<<tol<<','<<analytic[j]<<'\n';
          }
        }
      }
      PosInteraction_Forces();
    }
    std::ofstream done(fs::path(cfg->DirOut)/"planes_complete.json");
    done<<std::setprecision(17)<<"{\"diagnostic_completed\":true,\"passed\":"<<(!bad[0]&&!bad[1]&&consumers?"true":"false")
      <<",\"native_count\":"<<Np<<",\"wall_count\":"<<Npb<<",\"active_wall_count\":"<<active
      <<",\"constant_bad_components\":"<<bad[0]<<",\"affine_bad_components\":"<<bad[1]
      <<",\"max_constant_error\":"<<maxerror[0]<<",\"max_affine_error\":"<<maxerror[1]
      <<",\"consumer_max\":["<<maxrate[0]<<','<<maxrate[1]<<','<<maxrate[2]<<"],\"time_integrated\":false,\"physical_acceptance\":false}\n";
    std::cout<<"DIAGNOSTIC complete, affine bad="<<bad[1]<<" consumers="<<consumers<<'\n';
  }
};

int main(int argc,char** argv){
  try{
    AppInfo.ConfigRunPaths(argv[0]);JSphCfgRun cfg;cfg.LoadArgv(argc,argv);cfg.Cpu=true;
    cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;
    Check(!fs::exists(cfg.DirOut),"Choose a new output label");
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    SprPlanesCheck fixture;fixture.Execute(&cfg,AppInfo.LogPtr());return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Production exception; inspect Run.out\n";return 2;}
}

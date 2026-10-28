// A single frozen radial field through the real CPU fused loop. No integration.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
JAppInfo AppInfo("CryerRadialForce","r1","28-10-2026");
namespace fs=std::filesystem;
static void Check(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
struct Field{bool present=false;double value[13]={};};
struct Observation{std::vector<float> rate;std::vector<tfloat3> ace;std::vector<byte> surface;};
class CryerRadialForce:public JSphCpuSingle{
  Observation Observe(){
    InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();ComputeFreeSurfaceTracking();
    ApplyFreeSurfacePorePressure();
    const stinterparmsc p=StInterparmsc(Np,Npb,NpbOk,DivData,Dcellc,Posc,Velrhopc,Idpc,Codec,Pressc,
      PorePressc,PorePressRatec,FSTypec,FSNormalc,NULL,CorrMatc,Arc,Acec,Deltac,ShiftingMode,ShiftPosfsc,
      SpsTauc,SpsGradvelc,Sigmac,Rsigmac,ArtificialStressc);
    StInterResultc result;result.viscdt=0;JSphCpu::Interaction_Forces_ct(p,result);
    Observation s;s.rate.assign(PorePressRatec,PorePressRatec+Np);s.ace.assign(Acec,Acec+Np);
    s.surface.assign(FSTypec,FSTypec+Np);unsigned drained=0;
    for(unsigned i=Npb;i<Np;i++)if(IsHydroMechDrainedParticle(i,Posc,Codec,FSTypec)){
      drained++;Check(PorePressc[i]==0&&PorePressRatec[i]==0,"Actual drained receiver not zero");
    }
    Check(drained==5153,"Unexpected actual drained mask");PosInteraction_Forces();return s;
  }
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,const char* input){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(cfg->SvTimers);Timersc->TmStart(TMC_Init);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunCpu();FreePartsInit();
    Check(HydroMech&&!Simulate2D&&TKernel==KERNEL_Wendland&&!HourglassCpu&&!SoilBoundaryDerivativeSPR&&!PeriActive,"Unexpected fixture");
    Check(Np-Npb==37173&&PoreCompressionSourceMode==0&&PoreCompressionGradCorr&&SoilStressRateGradCorr,"Unexpected operator/ID count");
    Check(HydroMechDrainage&&HydroMechDrainageFixedGrid&&HydroMechTopLoadMode==HMLOAD_FlexibleConfinement&&HydroMechTopLoadQ0==10000,"Unexpected drainage/load");
    Check(Gravity.x==0&&Gravity.y==0&&Gravity.z==0,"Unexpected head/gravity term");
    std::ifstream in(input,std::ios::binary);unsigned magic=0,count=0;double tau=0;
    in.read((char*)&magic,4);in.read((char*)&count,4);in.read((char*)&tau,8);
    Check(magic==0x43524631&&count==37173&&tau>0,"Invalid manufactured field header");
    std::vector<Field> fields(Np);unsigned readcount=0;
    for(unsigned i=0;i<count;i++){
      unsigned id=0;in.read((char*)&id,4);Check(id<Np&&!fields[id].present,"Invalid/duplicate input ID");
      in.read((char*)fields[id].value,13*sizeof(double));Check(bool(in),"Truncated manufactured field");
      fields[id].present=true;readcount++;
    }
    Check(in.peek()==EOF&&readcount==count,"Unexpected field tail");
    const std::vector<tdouble3> pos(Posc,Posc+Np);const std::vector<unsigned> ids(Idpc,Idpc+Np);
    TimeStep=HydroMechDrainageStartTime+tau;Check(IsHydroMechDrainageActive(),"Post-opening observation inactive");
    const float originalvisco=Visco;std::vector<Observation> observations;
    for(unsigned trial=0;trial<4;trial++){
      // Full, p=0 compression, v=0 Darcy, then full with viscosity disabled.
      Visco=(trial==3?0:originalvisco);
      for(unsigned p=0;p<Np;p++){
        const bool soil=CODE_IsFluid(Codec[p]);const Field& f=fields[Idpc[p]];
        Check(soil==f.present,"Native identity mismatch");const double* a=f.value;
        if(soil)Check(fabs(Posc[p].x-a[0])<1e-14&&fabs(Posc[p].y-a[1])<1e-14&&fabs(Posc[p].z-a[2])<1e-14,"Frozen native position mismatch");
        Velrhopc[p]=TFloat4(float(trial==2?0:a[4]),float(trial==2?0:a[5]),float(trial==2?0:a[6]),2100);
        PorePressc[p]=PorePress0c[p]=float(trial==1?0:a[3]);Kplasticc[p]=0;
        Sigmac[p]=tsymatrix3d{};
        if(soil){Sigmac[p].xx=a[7];Sigmac[p].yy=a[8];Sigmac[p].zz=a[9];Sigmac[p].xy=a[10];Sigmac[p].yz=a[11];Sigmac[p].xz=a[12];}
      }
      observations.push_back(Observe());
      Check(!memcmp(pos.data(),Posc,Np*sizeof(tdouble3))&&!memcmp(ids.data(),Idpc,Np*sizeof(unsigned)),"A frozen state was advanced/reordered");
      std::cout<<"Finished nonintegrating fused observation "<<trial<<'\n';
    }
    Visco=originalvisco;
    std::ofstream out(fs::path(cfg->DirOut)/"radial_rates.csv");out<<std::setprecision(17);
    out<<"id,x,y,z,fstype,pressure_rate_pa_s,compression_rate_pa_s,darcy_rate_pa_s,novisc_pressure_rate_pa_s,ax,ay,az,raw_ax,raw_ay,raw_az\n";
    for(unsigned p=Npb;p<Np;p++){
      for(unsigned trial=1;trial<4;trial++)Check(observations[trial].surface[p]==observations[0].surface[p],"FSType changed across frozen probes");
      out<<Idpc[p]<<','<<Posc[p].x<<','<<Posc[p].y<<','<<Posc[p].z<<','<<unsigned(observations[0].surface[p]);
      for(unsigned trial=0;trial<4;trial++)out<<','<<observations[trial].rate[p];
      for(unsigned trial: {0u,3u}){const tfloat3 a=observations[trial].ace[p];out<<','<<a.x<<','<<a.y<<','<<a.z;}out<<'\n';
    }
    Check(bool(out),"Observation output failed");
    std::ofstream done(fs::path(cfg->DirOut)/"radial_summary.json");done<<std::setprecision(17)
      <<"{\"completed\":true,\"integrated_steps\":0,\"native_soil_count\":"<<count
      <<",\"tau_s\":"<<tau<<",\"source_clock_s\":"<<TimeStep<<",\"original_viscosity\":"<<originalvisco
      <<",\"actual_drainage_active\":true,\"drained_count\":5153,\"geometry_unchanged\":true,\"physical_acceptance\":false}\n";
  }
};
int main(int argc,char** argv){
  try{
    Check(argc>3,"Usage: companion field.bin -cpu input-case fresh-output [options]");
    AppInfo.ConfigRunPaths(argv[0]);JSphCfgRun cfg;cfg.LoadArgv(argc-1,argv+1);cfg.Cpu=true;
    cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;Check(!fs::exists(cfg.DirOut),"Refusing retained output");
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    CryerRadialForce diagnostic;diagnostic.Execute(&cfg,AppInfo.LogPtr(),argv[1]);return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Production exception; inspect new retained Run.out\n";return 2;}
}

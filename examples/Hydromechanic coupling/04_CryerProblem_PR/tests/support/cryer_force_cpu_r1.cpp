// Frozen manufactured fields through the actual CPU force/rate functions; no integration.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "JCellSearch_inline.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>

JAppInfo AppInfo("CryerForceCheck","v1","27-10-2026");
namespace fs=std::filesystem;
static void Check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
static double Norm(tdouble3 a){return sqrt(a.x*a.x+a.y*a.y+a.z*a.z);}
static tdouble3 Cross(tdouble3 a,tdouble3 b){return TDouble3(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x);}
static const double L[3][3]={{.7,-.3,.2},{.4,-.5,.1},{-.2,.6,.9}};
struct SavedForce{
  std::vector<tfloat3> ace,load;std::vector<tsymatrix3f> rate;std::vector<float> pore,ar;
};

class CryerForceCheck:public JSphCpuSingle{
  SavedForce Force(){
    InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();ComputeFreeSurfaceTracking();
    Check(HydroMechLoadAcec&&PorePressc&&PorePressRatec,"Missing real load/pore arrays");
    const stinterparmsc p=StInterparmsc(Np,Npb,NpbOk,DivData,Dcellc,Posc,Velrhopc,Idpc,Codec,Pressc,
      PorePressc,PorePressRatec,FSTypec,FSNormalc,NULL,CorrMatc,Arc,Acec,Deltac,ShiftingMode,ShiftPosfsc,
      SpsTauc,SpsGradvelc,Sigmac,Rsigmac,ArtificialStressc);
    StInterResultc result;result.viscdt=0;JSphCpu::Interaction_Forces_ct(p,result);
    SavedForce s;s.ace.assign(Acec,Acec+Np);s.load.assign(HydroMechLoadAcec,HydroMechLoadAcec+Np);
    s.rate.assign(Rsigmac,Rsigmac+Np);s.pore.assign(PorePressRatec,PorePressRatec+Np);s.ar.assign(Arc,Arc+Np);
    PosInteraction_Forces();return s;
  }
  tdouble3 OfflineA(unsigned p,double q)const{
    tdouble3 stress=TDouble3(0),load=TDouble3(0),pore=TDouble3(0);
    const double ri=Velrhopc[p].w,h=KernelH;
    const StNgSearch ngs=nsearch::Init(Dcellc[p],false,DivData);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 range=nsearch::ParticleRange(y,z,ngs,DivData);
      for(unsigned j=range.x;j<range.y;j++)if(j!=p&&CODE_IsFluid(Codec[j])){
        const tdouble3 d=Posc[p]-Posc[j];const double rr=d.x*d.x+d.y*d.y+d.z*d.z;
        if(rr<=double(KernelSize2)&&rr>=ALMOSTZERO){
          const double r=sqrt(rr),f=-2.08891/pow(h,5)*pow(1-.5*r/h,3),rj=Velrhopc[j].w;
          const tdouble3 g=d*f;
          // Static manufactured stresses are isotropic. Sum all three terms independently.
          stress=stress+g*(double(MassFluid)*(Sigmac[p].xx/(ri*ri)+Sigmac[j].xx/(rj*rj)));
          load=load+g*(q*double(MassFluid)*(1/(ri*ri)+1/(rj*rj)));
          pore=pore+g*(-double(MassFluid)*(double(PorePressc[p])+double(PorePressc[j]))/(ri*rj));
        }
      }
    }
    return stress+load+pore;
  }
public:
  void Execute(const JSphCfgRun *cfg,JLog2 *log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(cfg->SvTimers);Timersc->TmStart(TMC_Init);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();VisuParticleSummary();InitRunCpu();FreePartsInit();
    Check(HydroMech&&!Simulate2D&&TKernel==KERNEL_Wendland&&!HourglassCpu&&!SoilBoundaryDerivativeSPR&&!PeriActive,"Unexpected Cryer fixture");
    Check(Np-Npb==37173&&PoreCompressionSourceMode==0&&PoreCompressionGradCorr,"Unexpected IDs/pore-source fixture");
    const float q=HydroMechTopLoadQ0;Check(q>0&&HydroMechTopLoadMode==HMLOAD_FlexibleConfinement,"Expected original raw confinement");
    // Harness-only overrides: zero damping/viscosity/gravity and disabled drainage; no state is advanced.
    HydroMechDrainage=false;Visco=0;Gravity=TFloat3(0);SoilDamping=false;
    const std::vector<tdouble3> positions(Posc,Posc+Np);
    std::vector<unsigned> ids(Idpc,Idpc+Np),ordered=ids;std::sort(ordered.begin(),ordered.end());
    for(unsigned p=0;p<Np;p++)Check(ordered[p]==p,"Native identity set is not complete/unique");
    const double trace=L[0][0]+L[1][1]+L[2][2],lambda=double(SoilCte.ModulusK)-2*double(SoilCte.ModulusG)/3;
    const double theory[8]={2*SoilCte.ModulusG*L[0][0]+lambda*trace,2*SoilCte.ModulusG*L[1][1]+lambda*trace,
      2*SoilCte.ModulusG*L[2][2]+lambda*trace,SoilCte.ModulusG*(L[0][1]+L[1][0]),
      SoilCte.ModulusG*(L[1][2]+L[2][1]),SoilCte.ModulusG*(L[0][2]+L[2][0]),
      -double(SoilCte.PoreWaterBulkModulus)/SoilCte.Porosity*trace,-double(RhopZero)*trace};
    const char* labels[6]={"static_p0_uniform","static_p0_smoothrho","static_p06q_uniform","static_p06q_smoothrho","affine_grad0","affine_grad1"};
    std::ofstream done(fs::path(cfg->DirOut)/"force_summary.json");done<<std::setprecision(17)<<"{\"time_integrated\":false,\"physical_acceptance\":false,\"pore_feedback_pointer_present\":true,\"drainage_runtime\":false,\"pressure_state_float\":true,\"persistent_stress_double\":true,\"native_soil_count\":"<<Np-Npb<<",\"q_input_pa\":"<<q<<",\"cases\":[\n";
    for(unsigned trial=0;trial<6;trial++){
      const bool affine=trial>=4,variable=!affine&&(trial%2),shared=trial==2||trial==3;
      HydroMechTopLoadQ0=(affine?0:q);SoilStressRateGradCorr=(trial==5);
      for(unsigned p=0;p<Np;p++){
        const bool soil=CODE_IsFluid(Codec[p]);const tdouble3 x=Posc[p];
        const float rho=float(double(RhopZero)*(variable&&soil?1+.01*(x.x+.3*x.y+.2*x.z)/.05:1));
        const tfloat3 v=(affine&&soil?TFloat3(float(L[0][0]*x.x+L[0][1]*x.y+L[0][2]*x.z),float(L[1][0]*x.x+L[1][1]*x.y+L[1][2]*x.z),float(L[2][0]*x.x+L[2][1]*x.y+L[2][2]*x.z)):TFloat3(0));
        Velrhopc[p]=TFloat4(v.x,v.y,v.z,rho);PorePressc[p]=PorePress0c[p]=(shared&&soil?.6f*q:0);Kplasticc[p]=0;
        Sigmac[p]=tsymatrix3d{};if(soil&&!affine)Sigmac[p].xx=Sigmac[p].yy=Sigmac[p].zz=-(double(q)-double(PorePressc[p]));
      }
      const SavedForce full=Force();SavedForce probe;
      if(!affine){
        const std::vector<tsymatrix3d> stress(Sigmac,Sigmac+Np);const std::vector<float> pore(PorePressc,PorePressc+Np);
        for(unsigned p=0;p<Np;p++){Sigmac[p]=tsymatrix3d{};PorePressc[p]=0;}
        probe=Force();std::copy(stress.begin(),stress.end(),Sigmac);std::copy(pore.begin(),pore.end(),PorePressc);
      }
      std::ofstream rows(fs::path(cfg->DirOut)/(std::string(labels[trial])+".csv"));
      rows<<std::setprecision(17)<<"id,x,y,z,rho,pore_pa,sigma_xx,ax,ay,az,full_load_ax,full_load_ay,full_load_az,probe_load_ax,probe_load_ay,probe_load_az,offline_ax,offline_ay,offline_az,rsxx,rsyy,rszz,rsxy,rsyz,rsxz,pore_rate,ar,theory_rsxx,theory_rsyy,theory_rszz,theory_rsxy,theory_rsyz,theory_rsxz,theory_pore_rate,theory_ar\n";
      double sum2=0,maxnorm=0,refdiff2=0,loadgap2=0,rate2[8]={0,0,0,0,0,0,0,0};tdouble3 net=TDouble3(0),moment=TDouble3(0);
      for(unsigned p=Npb;p<Np;p++){
        Check(CODE_IsFluid(Codec[p])&&Velrhopc[p].w>0,"Invalid manufactured fluid/density");
        const tdouble3 a=ToTDouble3(full.ace[p]),load=ToTDouble3(full.load[p]),lp=(affine?TDouble3(0):ToTDouble3(probe.ace[p]));
        const tdouble3 reference=(affine?TDouble3(0):OfflineA(p,q));
        const double values[8]={full.rate[p].xx,full.rate[p].yy,full.rate[p].zz,full.rate[p].xy,full.rate[p].yz,full.rate[p].xz,full.pore[p],full.ar[p]};
        Check(std::isfinite(Norm(a))&&std::isfinite(Norm(load))&&std::isfinite(Norm(lp))&&std::isfinite(Norm(reference)),"Nonfinite force");
        sum2+=Norm(a)*Norm(a);maxnorm=(std::max)(maxnorm,Norm(a));refdiff2+=Norm(a-reference)*Norm(a-reference);loadgap2+=Norm(load-lp)*Norm(load-lp);
        net=net+a*double(MassFluid);moment=moment+Cross(Posc[p],a*double(MassFluid));
        for(unsigned k=0;k<8;k++){Check(std::isfinite(values[k]),"Nonfinite rate");const double d=values[k]-(affine?theory[k]:0);rate2[k]+=d*d;}
        rows<<Idpc[p]<<','<<Posc[p].x<<','<<Posc[p].y<<','<<Posc[p].z<<','<<Velrhopc[p].w<<','<<PorePressc[p]<<','<<Sigmac[p].xx<<','<<a.x<<','<<a.y<<','<<a.z<<','<<load.x<<','<<load.y<<','<<load.z<<','<<lp.x<<','<<lp.y<<','<<lp.z<<','<<reference.x<<','<<reference.y<<','<<reference.z;
        for(unsigned k=0;k<8;k++)rows<<','<<values[k];for(unsigned k=0;k<8;k++)rows<<','<<(affine?theory[k]:0);rows<<'\n';
      }
      Check(!memcmp(positions.data(),Posc,Np*sizeof(tdouble3))&&!memcmp(ids.data(),Idpc,Np*sizeof(unsigned)),"Frozen position/identity changed");
      const double n=double(Np-Npb);if(trial)done<<",\n";
      done<<"{\"label\":\""<<labels[trial]<<"\",\"soil_count\":"<<Np-Npb<<",\"runtime_gradcorr\":"<<(SoilStressRateGradCorr?"true":"false")<<",\"runtime_q_pa\":"<<HydroMechTopLoadQ0
        <<",\"force_component_rms_m_s2\":"<<sqrt(sum2/(3*n))<<",\"force_vector_max_m_s2\":"<<maxnorm<<",\"offlineA_difference_component_rms_m_s2\":"<<sqrt(refdiff2/(3*n))
        <<",\"full_load_vs_independent_probe_component_rms_m_s2\":"<<sqrt(loadgap2/(3*n))<<",\"net_force_N\":["<<net.x<<','<<net.y<<','<<net.z<<"],\"torque_N_m\":["<<moment.x<<','<<moment.y<<','<<moment.z<<"],\"rate_minus_target_rms\":[";
      for(unsigned k=0;k<8;k++){if(k)done<<',';done<<sqrt(rate2[k]/n);}done<<"]}";
      std::cout<<"Frozen diagnostic completed: "<<labels[trial]<<" forceRMS="<<sqrt(sum2/(3*n))<<'\n';
    }
    done<<"],\"diagnostic_completed\":true}\n";
  }
};

int main(int argc,char** argv){
  try{
    AppInfo.ConfigRunPaths(argv[0]);JSphCfgRun cfg;cfg.LoadArgv(argc,argv);cfg.Cpu=true;
    cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;Check(!fs::exists(cfg.DirOut),"Choose a fresh output label");
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    CryerForceCheck fixture;fixture.Execute(&cfg,AppInfo.LogPtr());return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(...){std::cerr<<"Production exception; inspect retained Run.out\n";return 2;}
}

// New bounded CPU trajectory from one sealed n4 full-step state; original integrator unchanged.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JCellDivCpuSingle.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "JException.h"
#include "JDsFixedDt.h"
#include "FunSphKernel.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <climits>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("C08ASN4CoupledCpu","r1","09-11-2026");
namespace pathfs=std::filesystem;
static_assert(sizeof(unsigned)==4&&sizeof(tfloat3)==12&&sizeof(tdouble3)==24&&sizeof(tsymatrix3d)==48,"Frozen typed22 and named stress layout required");
static constexpr unsigned Original=7060,Total=6805,Fixed=1805,Soil=5000,Samples=66;
static constexpr unsigned Parts[1]={64},Focus[4]={7013,7015,6963,7014},Bed[5]={1800,1852,1904,1956,2008};
static void Need(bool x,const char* s){if(!x)throw std::runtime_error(s);}
template<class T>static bool Bits(const T& a,const T& b){return !memcmp(&a,&b,sizeof(T));}
static bool Finite(float x){return std::isfinite(x);}static bool Finite(double x){return std::isfinite(x);}static bool Finite(unsigned){return true;}
static bool Finite(tfloat3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}static bool Finite(tdouble3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static tdouble3 Product(const tmatrix3d& c,tdouble3 g){return TDouble3(c.a11*g.x+c.a12*g.y+c.a13*g.z,c.a21*g.x+c.a22*g.y+c.a23*g.z,c.a31*g.x+c.a32*g.y+c.a33*g.z);}
template<class T>static std::vector<T> ReadArray(std::ifstream& f){std::vector<T> v(Total);f.read(reinterpret_cast<char*>(v.data()),sizeof(T)*Total);Need(bool(f),"Truncated native array");for(const auto& x:v)Need(Finite(x),"Nonfinite native array");return v;}
struct Snapshot{
  unsigned part,completed;double time;std::vector<unsigned> id,fstype,byid;
  std::vector<tdouble3> pos,sk,si;std::vector<tfloat3> vel,legacykk,legacyij,fsnormal,load;
  std::vector<float> rhop,kap,p,p0,excess,posdiv;std::vector<double> j,n,theta,volume,rho,k;
  Snapshot(const pathfs::path& folder,unsigned selected):part(selected),completed(4000000+4000*(selected+1)),byid(Original,UINT_MAX){
    std::ifstream f(folder/"typed22.bin",std::ios::binary);unsigned h[3]={};f.read(reinterpret_cast<char*>(h),12);const std::uintmax_t stride=8+std::uintmax_t(Total)*212;
    Need(bool(f)&&h[0]==Total&&h[1]==22&&h[2]==Samples&&pathfs::file_size(folder/"typed22.bin")==12+Samples*stride,"Actual66/6805/22 native extent differs");
    Need(selected==Parts[0],"Only original n4 saved part64 is admitted");f.seekg(std::streamoff(12+selected*stride));f.read(reinterpret_cast<char*>(&time),8);Need(bool(f)&&Finite(time),"Invalid native clock");
    id=ReadArray<unsigned>(f);pos=ReadArray<tdouble3>(f);vel=ReadArray<tfloat3>(f);legacykk=ReadArray<tfloat3>(f);legacyij=ReadArray<tfloat3>(f);fsnormal=ReadArray<tfloat3>(f);load=ReadArray<tfloat3>(f);
    rhop=ReadArray<float>(f);kap=ReadArray<float>(f);p=ReadArray<float>(f);p0=ReadArray<float>(f);excess=ReadArray<float>(f);sk=ReadArray<tdouble3>(f);si=ReadArray<tdouble3>(f);fstype=ReadArray<unsigned>(f);
    j=ReadArray<double>(f);n=ReadArray<double>(f);theta=ReadArray<double>(f);volume=ReadArray<double>(f);rho=ReadArray<double>(f);k=ReadArray<double>(f);posdiv=ReadArray<float>(f);
    unsigned fixed=0,soil=0;for(unsigned q=0;q<Total;q++){const unsigned a=id[q];const bool bed=std::find(std::begin(Bed),std::end(Bed),a)!=std::end(Bed);Need(a<Original&&byid[a]==UINT_MAX&&(a<1800||bed||a>=2060),"Unexpected/duplicate/retired native ID");byid[a]=q;if(a<2060)fixed++;else{soil++;Need(kap[q]>=0&&j[q]>1.-double(.35f)&&n[q]>0&&n[q]<1&&rho[q]>0&&k[q]>0,"Invalid soil native ledger domain");if(fstype[q]==2||fstype[q]==3)Need(p[q]<=0,"Closed saved FS2/3 has positive pressure");}}
    Need(fixed==Fixed&&soil==Soil,"Actual fixed/soil ownership differs");for(unsigned a:Focus)Need(byid[a]!=UINT_MAX,"Explicit focus missing");
  }
};
class Probe:public JSphCpuSingle{
  std::vector<typecode> releasedCode;std::vector<tfloat3> releasedNormal;std::vector<byte> releasedSlip;
  std::vector<unsigned> Map()const{
    Need(Np==Total&&Npb==Fixed&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Full released-state allocation differs");std::vector<unsigned> b(Original,UINT_MAX);unsigned soil=0,fixed=0;
    for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(id<Original&&b[id]==UINT_MAX&&CODE_IsNormal(Codec[q]),"Changed/duplicate native identity");b[id]=q;if(id>=2060){Need(q>=Npb&&CODE_IsFluid(Codec[q]),"Soil ownership differs");soil++;}else{Need(q<Npb&&CODE_IsFixed(Codec[q])&&(id<1800||IsGravityPreloadBedId(id)),"Fixed ownership differs");fixed++;}}
    Need(soil==Soil&&fixed==Fixed,"Released counts differ");return b;
  }
  void StaticRoles()const{for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(Bits(Codec[q],releasedCode[id]),"ID-owned code changed");if(q<Npb){Need(Bits(BoundNormalc[q],releasedNormal[id])&&Bits(BoundSlipModec[q],releasedSlip[id]),"ID-owned wall normal/slip changed");if(IsGravityPreloadBedId(id))Need(BoundNormalc[q]==TFloat3(0,0,float(Dp))&&BoundSlipModec[q]==byte(SLIP_NoSlip),"Kept bed override differs");}}}
  void CopySaved(const Snapshot& a){for(unsigned q=0;q<Np;q++){const unsigned s=a.byid[Idpc[q]];Need(s!=UINT_MAX,"Snapshot/current ID mismatch");Posc[q]=a.pos[s];Velrhopc[q]=TFloat4(a.vel[s].x,a.vel[s].y,a.vel[s].z,a.rhop[s]);const auto kk=a.sk[s],ij=a.si[s];Sigmac[q]=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);Kplasticc[q]=a.kap[s];PorePressc[q]=a.p[s];PorePress0c[q]=a.p0[s];PoroJc[q]=a.j[s];PoroThetac[q]=a.theta[s];FSTypec[q]=a.fstype[s];FSNormalc[q]=a.fsnormal[s];PosDivc[q]=a.posdiv[s];HydroMechLoadAcec[q]=a.load[s];}}
  void Ledger(const Snapshot& a)const{for(unsigned q=Npb;q<Np;q++){const unsigned s=a.byid[Idpc[q]];double n,v,rho;GetPorosityFeedbackStateCpu(q,n,v,rho);const double k=GetDynamicConductivityCpu(q);Need(Bits(n,a.n[s])&&Bits(v,a.volume[s])&&Bits(rho,a.rho[s])&&Bits(k,a.k[s])&&Bits(float(rho),a.rhop[s]),"Original soil J/n/V/rho/k/cache ledger differs");}}
  void Restore(const Snapshot& a){
    Need(!Acec&&!Rsigmac&&!BoundDerivativeVelc&&!ArtificialStressc,"Previous force scratch still owned");Map();CopySaved(a);LoadDcellParticles(Np,Codec,Posc,Dcellc);
    const bool free=HydroMechFreeSeepage,shep=PoreShepardRegularization;HydroMechFreeSeepage=PoreShepardRegularization=false;
    try{BoundChanged=true;RunCellDivide(false);}catch(...){HydroMechFreeSeepage=free;PoreShepardRegularization=shep;throw;}HydroMechFreeSeepage=free;PoreShepardRegularization=shep;
    Need(!CellDivSingle->GetNpbOut()&&!CellDivSingle->GetNpfOut()&&!CellDivSingle->GetNpbOutIgnore()&&!CellDivSingle->GetNpfOutIgnore(),"Snapshot cell rebuild excluded a particle");Map();CopySaved(a);StaticRoles();Ledger(a);TimeStep=a.time;Nstep=a.completed;
  }
  void InitialUnchanged(const Snapshot& a)const{for(unsigned q=Npb;q<Np;q++){const unsigned s=a.byid[Idpc[q]];const tfloat4 v=TFloat4(a.vel[s].x,a.vel[s].y,a.vel[s].z,a.rhop[s]);const auto kk=a.sk[s],ij=a.si[s];const auto stress=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);Need(Bits(Posc[q],a.pos[s])&&Bits(Velrhopc[q],v)&&Bits(Sigmac[q],stress)&&Bits(Kplasticc[q],a.kap[s])&&Bits(PorePressc[q],a.p[s])&&Bits(PorePress0c[q],a.p0[s])&&Bits(PoroJc[q],a.j[s]),"Force evaluation changed a soil primary state");}StaticRoles();Ledger(a);Need(TimeStep==a.time&&unsigned(Nstep)==a.completed&&!PosPrec&&!PoroJPrec,"Zero-step evaluation advanced the state");}

  unsigned lastCompleted=0,written=0;double lastTime=0;std::string phase="initialization";
  static std::string Json(const std::string& s){std::string r;for(unsigned char c:s){if(c=='"'||c=='\\'){r+='\\';r+=char(c);}else if(c=='\n')r+="\\n";else if(c=='\r')r+="\\r";else if(c=='\t')r+="\\t";else if(c<32)r+='?';else r+=char(c);}return r;}
  void Failure(const std::string& why)const{
    // No primary/predictor/corrector array is read after a failed substage.
    std::ofstream f(pathfs::path(CfgRun->DirOut)/"failure.json");f<<std::setprecision(17)<<"{\"stage\":\"upl_c08_asn4_coupled_cpu_r1\",\"passed\":false,\"failed_phase\":\""<<phase<<"\",\"first_exception\":\""<<Json(why)<<"\",\"has_completed_row\":"<<(written?"true":"false")<<",\"last_output_completed_step\":";
    if(written)f<<lastCompleted;else f<<"null";f<<",\"last_output_time_s\":";if(written)f<<lastTime;else f<<"null";f<<",\"completed_rows\":"<<written<<",\"unsaved_failure_state_read\":false,\"unsaved_failure_time_inferred\":false,\"physical_acceptance\":false}\n";f.flush();
  }
  void Output(const Snapshot& a,unsigned completed,unsigned updates,double sourceTime,double error,std::vector<float>& previousK,std::ofstream& states,std::ofstream& points){
    Map();StaticRoles();Need(Finite(error)&&error!=-DBL_MAX&&error<=1e-14,"Original signed necessary-step interval failed/empty");Need(!CellDivSingle->GetNpbOut()&&!CellDivSingle->GetNpfOut()&&!CellDivSingle->GetNpbOutIgnore()&&!CellDivSingle->GetNpfOutIgnore(),"Completed step excluded a particle");
    constexpr unsigned F=13;double lo[F],hi[F];unsigned lid[F]={},hid[F]={};for(unsigned j=0;j<F;j++){lo[j]=DBL_MAX;hi[j]=-DBL_MAX;}double p2=0,v2=0,maxLedger=0;unsigned fs23=0;
    const double solid=1.-double(SoilCte.Porosity),v0=double(MassFluid)/double(RhopZero),k0=double(SoilCte.HydraulicConductivity),water=double(SoilCte.PoreWaterRho),rho0=double(RhopZero),tol=1e-6*Dp;
    for(unsigned q=0;q<Np;q++){
      const unsigned id=Idpc[q],s=a.byid[id];Need(s!=UINT_MAX&&Bits(PorePress0c[q],a.p0[s]),"Fixed native P0 changed");const auto x=Posc[q];const auto v=Velrhopc[q];const auto sigma=Sigmac[q];Need(Finite(x)&&Finite(v.x)&&Finite(v.y)&&Finite(v.z)&&Finite(v.w)&&Finite(PorePressc[q])&&Finite(Kplasticc[q])&&Finite(PoroJc[q])&&Finite(PoroThetac[q])&&Finite(sigma.xx)&&Finite(sigma.yy)&&Finite(sigma.zz)&&Finite(sigma.xy)&&Finite(sigma.yz)&&Finite(sigma.xz),"Nonfinite completed primary state");
      if(q<Npb){Need(Bits(x,a.pos[s])&&v.x==0&&v.y==0&&v.z==0&&Kplasticc[q]==0,"Fixed geometry/velocity/kappa changed");continue;}
      Need(PoroJc[q]>solid&&Kplasticc[q]>=previousK[id]&&x.x>=-tol&&x.z>=-tol&&x.y==0,"Original saturated/monotone-kappa/fixed-plane domain failed");previousK[id]=Kplasticc[q];if(IsFreeSurfaceParticle(q,Codec,FSTypec)){fs23++;Need(PorePressc[q]<=0,"Completed FS2/3 retained positive p");}
      double n,volume,rho;GetPorosityFeedbackStateCpu(q,n,volume,rho);const double k=GetDynamicConductivityCpu(q),expected[]={1.-solid/PoroJc[q],v0*PoroJc[q],water+(rho0-water)/PoroJc[q],k0*exp((PoroJc[q]-1.)/(solid*DynamicPoreConductivityCk))},actual[]={n,volume,rho,k};double ledger=0;for(unsigned j=0;j<4;j++){Need(Finite(actual[j]),"Nonfinite completed ledger");ledger=(std::max)(ledger,fabs(actual[j]-expected[j])/(std::max)(1.,fabs(expected[j])));}Need(n>0&&n<1&&rho>0&&k>0&&ledger<=5e-13&&Bits(float(rho),v.w),"Original n/V/rho/k ledger/cache bits failed");maxLedger=(std::max)(maxLedger,ledger);Need(Finite(PorePressRatec[q]),"Nonfinite last Cor pressure rate");
      const double vv=double(v.x)*v.x+double(v.y)*v.y+double(v.z)*v.z,tr=sigma.xx+sigma.yy+sigma.zz,values[]={double(PorePressc[q]),double(PorePressRatec[q]),PoroThetac[q],PoroJc[q],n,rho,k,double(Kplasticc[q]),sqrt(vv),tr,tr-3.*PorePressc[q],x.x,x.z};p2+=double(PorePressc[q])*PorePressc[q];v2+=vv;
      for(unsigned j=0;j<F;j++){Need(Finite(values[j]),"Nonfinite completed diagnostic field");if(values[j]<lo[j]){lo[j]=values[j];lid[j]=id;}if(values[j]>hi[j]){hi[j]=values[j];hid[j]=id;}}
    }
    states<<completed<<','<<TimeStep<<','<<TimeStep-sourceTime<<','<<updates<<','<<LastDt<<','<<error<<','<<fs23<<','<<maxLedger<<','<<sqrt(p2/Soil)<<','<<sqrt(v2/Soil);for(unsigned j=0;j<F;j++)states<<','<<lo[j]<<','<<lid[j]<<','<<hi[j]<<','<<hid[j];states<<'\n';
    const auto byid=Map();for(unsigned id:Focus){const unsigned q=byid[id];const auto x=Posc[q];const auto v=Velrhopc[q];const auto s=Sigmac[q];double n,volume,rho;GetPorosityFeedbackStateCpu(q,n,volume,rho);points<<completed<<','<<TimeStep<<','<<TimeStep-sourceTime<<','<<updates<<','<<id<<','<<PorePressc[q]<<','<<PorePressRatec[q]<<','<<PoroThetac[q]<<','<<PoroJc[q]<<','<<n<<','<<rho<<','<<GetDynamicConductivityCpu(q)<<','<<Kplasticc[q]<<','<<s.xx+s.yy+s.zz<<','<<s.xx+s.yy+s.zz-3.*PorePressc[q]<<','<<x.x<<','<<x.y<<','<<x.z<<','<<v.x<<','<<v.y<<','<<v.z<<','<<FSTypec[q]<<','<<PorePress0c[q]<<'\n';}
    states.flush();points.flush();Need(bool(states)&&bool(points),"Completed CSV flush failed");lastCompleted=completed;lastTime=TimeStep;written=updates;std::cout<<"C08Coupled completed="<<completed<<" time="<<std::setprecision(17)<<TimeStep<<" updates="<<updates<<'\n'<<std::flush;
  }
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,const Snapshot& a){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;
    try{
      Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();RunGravityPreloadHandoffCpu();FreePartsInit();
      Need(IsGravityPreloadHandoff()&&GravityPreload&&!GravityPreloadElasticSource&&!GravityPreloadReleased&&unsigned(Nstep)==4000000&&GravityPreloadKeepBedOverlap&&GravityPreloadBedIds==std::vector<unsigned>(std::begin(Bed),std::end(Bed)),"Actual certified PRE/keep5 initialization differs");RunGravityPreloadRelease();Map();
      Need(GravityPreloadReleased&&GravityPreloadActualStep==4000000&&DynamicPorePressure&&PorosityFeedback&&DynamicPoreWall&&DynamicPoreConductivity&&DynamicPoreConductivityCk==2.&&HydroMechFreeSeepage&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilDamping&&!PoreShepardRegularization,"Released dynamic controls differ");
      Need(Simulate2D&&!PeriActive&&TKernel==KERNEL_Cubic&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundSlipModec&&SoilStressRateGradCorr&&!SoilBoundaryDerivativeSPR&&!HourglassCpu&&!SoilHourglassXi&&!WithFloating&&!UseDEM&&!AccInput&&!Shifting&&!Damping&&TDensity==DDT_None&&NoPenetration&&TMdbc2==MDBC2_NoPen&&UseDynamicPorePlaneContact()&&!CaseNmoving&&!CaseNfloat,"Frozen coupled scope/history exclusions differ");
      Need(ArtificialStress&&ArtificialStressCoef==.2f&&ArtificialStressExp==4.f&&Dp==.04&&KernelH==.048f&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==.0002f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&TVisco==VISCO_Artificial&&Visco==.1f&&Gravity==TFloat3(0,0,-9.81f),"Frozen material/kernel/AS4/AV differs");
      releasedCode.resize(Original);releasedNormal.resize(Original);releasedSlip.resize(Original);for(unsigned q=0;q<Np;q++){releasedCode[Idpc[q]]=Codec[q];if(q<Npb){releasedNormal[Idpc[q]]=BoundNormalc[q];releasedSlip[Idpc[q]]=BoundSlipModec[q];}}StaticRoles();const double sourceTime=GravityPreloadActualTime;
      phase="restore_part64_once";Restore(a);InitialUnchanged(a);Need(a.part==64&&a.completed==4260000&&unsigned(Nstep)==4260000,"Only actual n4 part64 full-step start is admitted");Need(FixedDt&&Bits(FixedDt->GetFixedValue(),.0000025),"Original fixed2.5us value required");SymplecticDtPre=LastDt=.0000025;
      // Only clear the output-statistical interval for this NEW diagnostic window; GetDt/bounds are unchanged.
      FixedDt->GetDtError(true);std::vector<float> previousK(Original);for(unsigned id=2060;id<Original;id++)previousK[id]=a.kap[a.byid[id]];
      std::ofstream states(pathfs::path(cfg->DirOut)/"states.csv"),points(pathfs::path(cfg->DirOut)/"focus.csv");states<<std::setprecision(17);points<<std::setprecision(17);
      states<<"completed_step,time_s,tau_s,updates,dt_s,signed_dterror_new_window_s,FS23_count,max_ledger_relative_error,p_RMS_Pa,velocity_RMS_m_s";for(const char* name:{"p_Pa","last_cor_rate_Pa_s","last_cor_theta_s","J","n","rho","k","kappa","speed_m_s","effective_trace_Pa","total_trace_Pa","x_m","z_m"})states<<','<<name<<"_min,"<<name<<"_min_ID,"<<name<<"_max,"<<name<<"_max_ID";states<<'\n';points<<"completed_step,time_s,tau_s,updates,native_id,p_Pa,last_cor_rate_Pa_s,last_cor_theta_s,J,n,rho,k,kappa,effective_trace_Pa,total_trace_Pa,x,y,z,vx,vy,vz,completed_FS,P0_Pa\n";double scalar=a.time;
      for(unsigned update=1;update<=4000;update++){
        Need(unsigned(Nstep)==4260000+update-1&&Bits(SymplecticDtPre,.0000025),"Full-step counter/next fixed dt differs");InterStep=INTERSTEP_SymPredictor;phase="ComputeStep_Sym";const double dt=ComputeStep_Sym();Need(Bits(dt,.0000025),"Real integrator returned another step");phase="completed_RunCellDivide";RunCellDivide(true);TimeStep+=dt;LastDt=dt;scalar+=dt;Need(Bits(TimeStep,scalar),"Actual scalar+=dt clock differs");const unsigned completed=unsigned(Nstep+1);phase="completed_output";Output(a,completed,update,sourceTime,FixedDt->GetDtError(false),previousK,states,points);Nstep++;
      }
      Need(unsigned(Nstep)==4264000&&written==4000&&lastCompleted==4264000&&!Acec&&!Rsigmac&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Actual4000 full steps incomplete");phase="completion";
      std::ofstream f(pathfs::path(cfg->DirOut)/"completion.json");f<<std::setprecision(17)<<"{\"stage\":\"upl_c08_asn4_coupled_cpu_r1\",\"passed\":true,\"source_part\":64,\"source_completed_step\":4260000,\"source_saved_time_s\":"<<a.time<<",\"elastic_PRE_actual_time_s\":"<<sourceTime<<",\"physical_updates\":4000,\"completed_step\":4264000,\"actual_end_s\":"<<TimeStep<<",\"states_rows\":4000,\"focus_rows\":16000,\"native_IDs\":6805,\"soil\":5000,\"fixed\":1805,\"Restore_calls\":1,\"uses_real_ComputeStep_Sym\":true,\"necessary_DtVariable_both_stages_unchanged\":true,\"AS_exponent\":4,\"all_completed_original_guards_passed\":true,\"signed_interval_is_new_diagnostic_window\":true,\"last_cor_rate_is_not_completed_state_RHS\":true,\"Ace_Rsigma_after_cleanup_read\":false,\"GPU_exact_restart_or_replay\":false,\"physical_acceptance\":false}\n";f.flush();Need(bool(f),"Completion write failed");
    }catch(const JException& e){Failure(e.ToStr());throw;}catch(const std::exception& e){Failure(e.what());throw;}catch(...){Failure("Unknown component exception");throw;}
  }
};
int main(int argc,char** argv){try{
  Need(argc>=9&&std::string(argv[1])=="--trajectory"&&std::string(argv[2])=="--snapshot","Use --trajectory --snapshot CLOSED_N4_NATIVE -cpu -ompthreads:1 -stable -mdbc_freeslip:1 EXISTING_N4_SEED FRESH_OUT");const pathfs::path folder=pathfs::absolute(argv[3]),tests=pathfs::path(__FILE__).parent_path().parent_path();Need(pathfs::equivalent(folder,tests/"outputs/upl_c08_asn4_window_GPU_r1/native_partial_r1"),"Only closed n4 partial input is admitted");Snapshot a(folder,64);
  AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!pathfs::exists(cfg.DirOut),"Fresh CPU trajectory output required");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr(),a);return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"CPU coupled diagnostic failed; preserve first result\n";return 2;}}


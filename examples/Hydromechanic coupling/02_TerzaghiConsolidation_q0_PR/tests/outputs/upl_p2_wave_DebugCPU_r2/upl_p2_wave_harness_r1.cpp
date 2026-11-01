// Bounded k=0 periodic wave. Uses actual initialization, cell division and steps.
// The audited replay must match ComputeStep_Sym before its stage audit is used.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include <algorithm>
#include <array>
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
JAppInfo AppInfo("PorosityWaveCpu","r1","01-11-2026");
namespace fs=std::filesystem;
static void Check(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
static constexpr unsigned Native=128,Columns=26,Samples=257;
static constexpr double End=1./32768.,Lx=.125,Lz=.0625,Amplitude=1./512.;
using Row=std::array<double,Columns>;
struct Frame{double time;std::array<Row,Native> rows;};
static void WriteFrame(std::ofstream& file,const Frame& f){file.write(reinterpret_cast<const char*>(&f.time),sizeof(double));for(const auto& r:f.rows)file.write(reinterpret_cast<const char*>(r.data()),sizeof(double)*Columns);Check(bool(file),"Frame write failed");}
static Frame ReadFrame(std::ifstream& file){Frame f{};file.read(reinterpret_cast<char*>(&f.time),sizeof(double));for(auto& r:f.rows)file.read(reinterpret_cast<char*>(r.data()),sizeof(double)*Columns);Check(bool(file),"Frame read failed");return f;}
class Wave:public JSphCpuSingle{
  std::array<tdouble3,Native> Initial;
  double InitialEnergy=0,MaxCfl=0,MaxEos=0,MaxEnergy=0,MaxForce=0;
  unsigned StageCount=0;
  std::array<unsigned,Native> Indices()const{
    std::array<unsigned,Native> ids;ids.fill(~0u);unsigned count=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){
      Check(CODE_IsFluid(Codec[p])&&Idpc[p]<Native&&ids[Idpc[p]]==~0u,"Wrong native identity");ids[Idpc[p]]=p;count++;
    }
    Check(count==Native&&!OutPosCount&&!OutRhopCount&&!OutMoveCount,"Native exclusion/count changed");return ids;
  }
  double Energy()const{
    double energy=0;
    for(unsigned p:Indices()){
      double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);const auto s=Sigmac[p];const auto v=Velrhopc[p];
      const double tr=s.xx+s.yy+s.zz,mean=tr/3.;
      const double dev=(s.xx-mean)*(s.xx-mean)+(s.yy-mean)*(s.yy-mean)+(s.zz-mean)*(s.zz-mean)+2*(s.xy*s.xy+s.xz*s.xz+s.yz*s.yz);
      energy+=V*(.5*rho*(double(v.x)*v.x+double(v.y)*v.y+double(v.z)*v.z)+dev/(4*SoilCte.ModulusG)+tr*tr/(18*SoilCte.ModulusK)+n*double(PorePressc[p])*PorePressc[p]/(2*SoilCte.PoreWaterBulkModulus));
    }
    return energy;
  }
  void StateGuard(double dt){
    const double n0=SoilCte.Porosity,kw=SoilCte.PoreWaterBulkModulus;
    const auto ids=Indices();
    for(unsigned p:ids){
      double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);const double j=PoroJc[p];
      Check(std::isfinite(j)&&std::isfinite(n)&&std::isfinite(V)&&std::isfinite(rho)&&j>1-n0&&V>0&&rho>0&&fabs(j-1)<=1e-4,"Invalid or out-of-window physical ledger");
      Check(fabs((1-n)*j-(1-n0))<=5e-13,"Solid-volume invariant failed");
      Check(std::isfinite(Velrhopc[p].w)&&Velrhopc[p].w>=RhopOutMin&&Velrhopc[p].w<=RhopOutMax,"Passive legacy rho left numerical-validity range");
      Check(Kplasticc[p]==0&&PorePress0c[p]==0,"Plasticity/reference pressure changed");
      const auto s=Sigmac[p];for(double x:{s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,double(Velrhopc[p].x),double(Velrhopc[p].y),double(Velrhopc[p].z),Posc[p].x,Posc[p].y,Posc[p].z,PoroThetac[p]})Check(std::isfinite(x),"Nonfinite physical state");
      const double eos=fabs(double(PorePressc[p])+kw*log((j-1+n0)/n0));MaxEos=(std::max)(MaxEos,eos);Check(eos<=.5,"Local k=0 storage/log consistency exceeded .5 Pa");
      const double cu=sqrt((double(SoilCte.ModulusK)+4*double(SoilCte.ModulusG)/3+kw/n)/rho),cfl=cu*dt/KernelH;
      MaxCfl=(std::max)(MaxCfl,cfl);Check(std::isfinite(cfl)&&cfl<=.01,"Manual coupled wave CFL exceeds .01");
    }
    for(unsigned p=0;p<Np;p++)if(CODE_IsPeriodic(Codec[p])){
      Check(Idpc[p]<Native&&PoroJc[p]==PoroJc[ids[Idpc[p]]],"Periodic J differs from owner at audited geometry");
      if(PoroJPrec)Check(PoroJPrec[p]==PoroJPrec[ids[Idpc[p]]],"Periodic Jpre differs from owner");
    }
    const double e=Energy()/InitialEnergy;MaxEnergy=(std::max)(MaxEnergy,e);Check(std::isfinite(e)&&e<=1.1,"Perturbation energy exceeds 1.1 initial");
  }
  void ForceGuard(double dt,const char* stage,std::ofstream& out){
    StateGuard(dt);double fx=0,fy=0,fz=0,scale=0;
    for(unsigned p:Indices()){
      double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);const auto a=Acec[p];const double mass=rho*V;
      Check(std::isfinite(a.x)&&std::isfinite(a.y)&&std::isfinite(a.z)&&std::isfinite(PorePressRatec[p]),"Nonfinite force/rate");
      fx+=mass*a.x;fy+=mass*a.y;fz+=mass*a.z;scale+=mass*sqrt(double(a.x)*a.x+double(a.y)*a.y+double(a.z)*a.z);
    }
    const double relative=sqrt(fx*fx+fy*fy+fz*fz)/(std::max)(1.,scale);MaxForce=(std::max)(MaxForce,relative);
    Check(relative<=256*FLT_EPSILON,"Instantaneous internal force budget failed");
    out<<Nstep<<','<<TimeStep<<','<<stage<<','<<Np<<','<<relative<<','<<Energy()/InitialEnergy<<','<<MaxCfl<<','<<MaxEos<<'\n';StageCount++;
  }
  double AuditedStep(std::ofstream& out){
    const double dt=SymplecticDtPre;
    DemDtForce=dt*.5;Interaction_Forces(INTERSTEP_SymPredictor);ForceGuard(dt,"predictor",out);const double dp=DtVariable(false);
    ComputeSymplecticPre(dt);PosInteraction_Forces();RunCellDivide(true);
    DemDtForce=dt;Interaction_Forces(INTERSTEP_SymCorrector);ForceGuard(dt,"corrector",out);const double dc=DtVariable(true);
    ComputeSymplecticCorr(dt);PosInteraction_Forces();SymplecticDtPre=(std::min)(dp,dc);return dt;
  }
  Frame Snapshot()const{
    Frame f{};f.time=TimeStep;const auto ids=Indices();
    for(unsigned id=0;id<Native;id++){
      const unsigned p=ids[id];const auto x=Posc[p];const auto v=Velrhopc[p];const auto s=Sigmac[p];const auto n=FSNormalc[p];const auto load=HydroMechLoadAcec[p];
      f.rows[id]={x.x,x.y,x.z,double(v.x),double(v.y),double(v.z),double(PorePressc[p]),double(PorePress0c[p]),PoroJc[p],PoroThetac[p],s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,double(Kplasticc[p]),double(FSTypec[p]),double(n.x),double(n.y),double(n.z),double(PosDivc[p]),double(load.x),double(load.y),double(load.z),double(v.w)};
      for(double q:f.rows[id])Check(std::isfinite(q),"Nonfinite serialized state");
    }
    return f;
  }
  void Modes(std::ofstream& out){
    const double k=2*acos(-1.)/Lx,n0=SoilCte.Porosity,kw=SoilCte.PoreWaterBulkModulus;
    const double cu=sqrt((double(SoilCte.ModulusK)+4*double(SoilCte.ModulusG)/3+kw/n0)/RhopZero),omega=k*cu;
    double vs=0,pc=0,us=0;
    const auto ids=Indices();for(unsigned id=0;id<Native;id++){
      const unsigned p=ids[id];const double phase=k*Initial[id].x;
      vs+=2.*Velrhopc[p].x*sin(phase)/Native;pc+=2.*PorePressc[p]*cos(phase)/Native;us+=2.*(Posc[p].x-Initial[id].x)*sin(phase)/Native;
    }
    out<<Nstep<<','<<TimeStep<<','<<cu<<','<<vs<<','<<Amplitude*cos(omega*TimeStep)<<','<<pc<<','<<-kw/n0*(Amplitude/cu)*sin(omega*TimeStep)<<','<<us<<','<<Amplitude/omega*sin(omega*TimeStep)<<','<<atan2(-n0*cu*pc/kw,vs)<<','<<omega*TimeStep<<','<<Energy()/InitialEnergy<<'\n';
  }
public:
  Wave(){PorosityObserver=true;PorosityFeedback=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log,bool audit,bool poison,unsigned steps){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);
    LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Check(HydroMech&&Simulate2D&&TStep==STEP_Symplectic&&!CaseNpb&&CaseNfluid==Native&&PeriX&&PeriZ&&!PeriY,"Expected 16x8 no-wall periodic 2D geometry");
    Check(!CaseNmoving&&!CaseNfloat&&!HourglassCpu&&!Shifting&&!Damping&&!RelaxZones&&!InOut&&!AccInput,"Audited replay does not admit auxiliary paths");
    Check(MapRealSize.x==Lx&&MapRealSize.z==Lz&&Dp==1./128.&&TimeStep==0&&FixedDt,"Unexpected geometry/clock/fixed-step input");
    const double dt=End/steps;Check(SymplecticDtPre==dt&&(steps==256||steps==512),"Only the declared dyadic coarse/half step admitted");
    auto ids=Indices();for(unsigned id=0;id<Native;id++)Initial[id]=Posc[ids[id]];
    for(unsigned p=0;p<Np;p++){
      Velrhopc[p].x=float(Amplitude*sin(2*acos(-1.)*Initial[Idpc[p]].x/Lx));Velrhopc[p].y=Velrhopc[p].z=0;
      if(poison)Velrhopc[p].w=float(1400+100*(Idpc[p]%7));
      Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;PorePressc[p]=PorePress0c[p]=0;PoroJc[p]=1;PoroThetac[p]=0;
    }
    InitialEnergy=Energy();Check(InitialEnergy>0,"Zero initial wave energy");StateGuard(dt);
    std::ofstream binary(fs::path(cfg->DirOut)/"physical.bin",std::ios::binary),mode(fs::path(cfg->DirOut)/"modes.csv"),stage(fs::path(cfg->DirOut)/"stages.csv");
    const unsigned header[3]={Native,Columns,Samples};binary.write(reinterpret_cast<const char*>(header),sizeof(header));
    mode<<std::setprecision(17)<<"step,time_s,cu_actual,v_sine,v_linear,p_cosine,p_linear,u_sine,u_linear,mode_phase,linear_phase,energy_ratio\n";
    stage<<std::setprecision(17)<<"step,source_clock_s,force_stage,np_with_clones,force_budget_relative,energy_ratio,max_coupled_CFL,max_EOS_error_Pa\n";
    WriteFrame(binary,Snapshot());Modes(mode);unsigned samples=1;
    for(unsigned it=0;it<steps;it++){
      InterStep=INTERSTEP_SymPredictor;
      const double used=audit?AuditedStep(stage):ComputeStep_Sym();Check(used==dt,"Fixed step unexpectedly changed");
      RunCellDivide(true);TimeStep+=used;LastDt=used;UpdateMaxValues();Nstep++;StateGuard(dt);
      if((it+1)%(steps/256)==0){WriteFrame(binary,Snapshot());Modes(mode);samples++;}
    }
    Check(TimeStep==End&&Nstep==steps&&samples==Samples&&!PoroJPrec,"Incomplete dyadic trajectory");
    Check(StageCount==(audit?2*steps:0),"Unexpected stage audit count");binary.flush();mode.flush();stage.flush();Check(bool(binary)&&bool(mode)&&bool(stage),"Diagnostic output failed");
    std::ofstream done(fs::path(cfg->DirOut)/"complete.json");done<<std::setprecision(17)<<"{\"passed\":true,\"native_ids\":128,\"samples\":257,\"steps\":"<<steps<<",\"actual_end_s\":"<<TimeStep<<",\"audited_replay\":"<<(audit?"true":"false")<<",\"actual_ComputeStep_Sym\":"<<(audit?"false":"true")<<",\"rho_poison\":"<<(poison?"true":"false")<<",\"force_stage_audits\":"<<StageCount<<",\"max_coupled_CFL\":"<<MaxCfl<<",\"max_EOS_error_Pa\":"<<MaxEos<<",\"max_energy_ratio\":"<<MaxEnergy<<",\"max_force_budget_relative\":"<<MaxForce<<",\"physical_acceptance\":false}\n";
    done.flush();Check(bool(done),"Completion write failed");
  }
};
static void Compare(const fs::path& left,const fs::path& right,const std::string& comparison,const fs::path& target){
  const bool half=comparison=="half",rhoTwin=comparison=="rho";
  Check(!fs::exists(target),"Retained comparison protected");std::ifstream a(left,std::ios::binary),b(right,std::ios::binary);unsigned ha[3],hb[3];a.read(reinterpret_cast<char*>(ha),sizeof(ha));b.read(reinterpret_cast<char*>(hb),sizeof(hb));
  Check(a&&b&&!memcmp(ha,hb,sizeof(ha))&&ha[0]==Native&&ha[1]==Columns&&ha[2]==Samples,"Snapshot header mismatch");double maxp=0,maxu=0,maxj=0;
  for(unsigned sample=0;sample<Samples;sample++){
    const Frame x=ReadFrame(a),y=ReadFrame(b);Check(!memcmp(&x.time,&y.time,sizeof(double)),"Actual sample clocks differ");double sum=0;
    for(unsigned id=0;id<Native;id++){
      if(!half)Check(!memcmp(x.rows[id].data(),y.rows[id].data(),sizeof(double)*(rhoTwin?Columns-1:Columns)),"Same-dt state differs");
      const auto& p=x.rows[id];const auto& q=y.rows[id];const double dp=p[6]-q[6];sum+=dp*dp;
      const double du=1000*sqrt((p[0]-q[0])*(p[0]-q[0])+(p[1]-q[1])*(p[1]-q[1])+(p[2]-q[2])*(p[2]-q[2]));
      maxu=(std::max)(maxu,du);maxj=(std::max)(maxj,fabs(p[8]-q[8]));Check(du<=.005,"Half material displacement exceeds .005 mm");
    }
    const double rms=sqrt(sum/Native);maxp=(std::max)(maxp,rms);Check(rms<=5,"Half pressure RMS exceeds5 Pa");
  }
  Check(a.peek()==std::char_traits<char>::eof()&&b.peek()==std::char_traits<char>::eof(),"Extra unreviewed samples");
  std::ofstream out(target);out<<std::setprecision(17)<<"{\"passed\":true,\"samples\":257,\"native_ids\":128,\"columns\":26,\"half_comparison\":"<<(half?"true":"false")<<",\"legacy_rho_excluded\":"<<(rhoTwin?"true":"false")<<",\"same_dt_bitwise_equal_except_declared_rho\":"<<(half?"false":"true")<<",\"max_pressure_RMS_Pa\":"<<maxp<<",\"max_material_displacement_mm\":"<<maxu<<",\"max_J_difference\":"<<maxj<<",\"physical_acceptance\":false}\n";out.flush();Check(bool(out),"Comparison write failed");
}
int main(int argc,char** argv){
  try{
    Check(argc>=2,"Use --job audit|actual POISON STEPS solverargs or --compare A B exact|rho|half NEW_JSON");
    if(std::string(argv[1])=="--compare"){Check(argc==6,"Missing comparison arguments");Check(std::string(argv[4])=="exact"||std::string(argv[4])=="rho"||std::string(argv[4])=="half","Invalid comparison mode");Compare(argv[2],argv[3],argv[4],argv[5]);return 0;}
    Check(std::string(argv[1])=="--job"&&argc>8,"Missing wave job arguments");const bool audit=std::string(argv[2])=="audit";Check(audit||std::string(argv[2])=="actual","Invalid step engine");
    const bool poison=std::string(argv[3])=="1";Check(poison||std::string(argv[3])=="0","Invalid poison flag");const unsigned steps=unsigned(std::stoul(argv[4]));Check(steps==256||steps==512,"Invalid bounded step count");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> arguments{argv[0]};for(int i=5;i<argc;i++)arguments.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(arguments.size()),arguments.data());cfg.Cpu=true;
    Check(!fs::exists(cfg.DirOut),"Retained job output protected");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Wave wave;wave.Execute(&cfg,AppInfo.LogPtr(),audit,poison,steps);return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Wave rejected; preserve partial outputs and Run.out\n";return 2;}
}

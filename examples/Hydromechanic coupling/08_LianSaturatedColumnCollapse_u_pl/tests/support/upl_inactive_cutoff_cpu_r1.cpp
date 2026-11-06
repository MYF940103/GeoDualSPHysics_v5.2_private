// Real case08 observer seed: actual CPU Darcy cutoff predicate, no force/integration.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "JException.h"
#include "JCellSearch_inline.h"
#include <algorithm>
#include <climits>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>
JAppInfo AppInfo("UplInactiveCutoffCpu","r1","06-11-2026");
namespace fs=std::filesystem;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static constexpr unsigned Fixed=2060,Soil=5000,Total=Fixed+Soil;
template<class T>struct Copy{
  T* p;std::vector<T> v;Copy(T* a,unsigned n):p(a){if(p)v.assign(a,a+n);}
  void Restore()const{if(p&&!v.empty())memcpy(p,v.data(),sizeof(T)*v.size());}
  bool Equal()const{return !p||v.empty()||!memcmp(p,v.data(),sizeof(T)*v.size());}
  ~Copy(){Restore();}
};
struct RestoreFlags{
  unsigned& count;bool& feedback;bool& dynamic;bool& wall;unsigned n;bool f,d,w;
  ~RestoreFlags(){count=n;feedback=f;dynamic=d;wall=w;}
};
struct Visits{unsigned pairs=0,receivers=0,inrange=0;double minrr=std::numeric_limits<double>::infinity();};
class Probe:public JSphCpuSingle{
  std::vector<unsigned> Map()const{
    Need(Np==Total&&Npb==Fixed,"Wrong retained count");std::vector<unsigned> m(Total,UINT_MAX);unsigned soil=0,fixed=0;
    for(unsigned p=0;p<Np;p++){Need(Idpc[p]<Total&&m[Idpc[p]]==UINT_MAX,"Duplicate/unknown retained ID");m[Idpc[p]]=p;
      if(CODE_IsFluid(Codec[p])){Need(CODE_IsNormal(Codec[p])&&Idpc[p]>=Fixed,"Native fluid code changed");soil++;}else{Need(CODE_IsFixed(Codec[p])&&Idpc[p]<Fixed,"Nonfixed retained wall");fixed++;}}
    Need(soil==Soil&&fixed==Fixed&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Native identity/exclusion mismatch");return m;
  }
  Visits Search(unsigned target,std::ostream& csv)const{
    Visits v;
    for(unsigned p1=Npb;p1<Np;p1++)if(CODE_IsNormal(Codec[p1])&&CODE_IsFluid(Codec[p1])){
      bool seen=false;const StNgSearch ngs=nsearch::Init(Dcellc[p1],true,DivData);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
        const tuint2 range=nsearch::ParticleRange(y,z,ngs,DivData);
        for(unsigned p2=range.x;p2<range.y;p2++)if(p2==target&&CODE_IsFixed(Codec[p2])){
          const auto d=Posc[p1]-Posc[p2];const double rr=d.x*d.x+d.z*d.z;const bool in=(rr<=double(KernelSize2)&&rr>=ALMOSTZERO);
          v.pairs++;v.inrange+=unsigned(in);v.minrr=(std::min)(v.minrr,rr);seen=true;csv<<Idpc[p2]<<','<<Idpc[p1]<<','<<rr<<','<<KernelSize2<<','<<in<<'\n';
        }
      }v.receivers+=unsigned(seen);
    }return v;
  }
  void NoStep()const{Need(TimeStep==0&&Nstep==0&&!PoroJPrec&&!PosPrec,"Predicate fixture advanced time/predictor");}
public:
  Probe(){PorosityObserver=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    Need(!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall,"Constructor is not observer-only");AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Need(PorosityObserver&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&!HydroMechDynamicSeepage&&HydroMech&&TKernel==KERNEL_Cubic&&Simulate2D&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&!PeriActive&&BoundModec&&BoundSlipModec&&PoroJc&&PoroThetac,"Actual case08 observer-only init failed");
    Need(Dp==.04&&KernelH==float(.048)&&RhopZero==2072.5f&&Gravity==TFloat3(0,0,-9.81f)&&TimeMax==0&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!DynamicPoreConductivity&&!StrainSoftening&&!SoilBoundaryDerivativeSPR&&!SoilHourglassXi&&!Damping&&!SoilDamping&&!NoPenetration&&!Acec&&!BoundDerivativeVelc,"Wrong zero-step actual geometry scope");
    const auto map=Map();NoStep();
    const Copy<unsigned> ids(Idpc,Np),cells(Dcellc,Np),fstype(FSTypec,Np);const Copy<typecode> codes(Codec,Np);const Copy<tdouble3> pos(Posc,Np);const Copy<tfloat3> normal(BoundNormalc,Np),tan(TangenVelc,Np),load(HydroMechLoadAcec,Np),fsnormal(FSNormalc,Np);
    const Copy<tfloat4> vel(Velrhopc,Np);const Copy<tsymatrix3d> sigma(Sigmac,Np);const Copy<byte> modes(BoundModec,Np),selectors(BoundSlipModec,Np);const Copy<tmatrix3d> corr(CorrMatc,Np);const Copy<double> j(PoroJc,Np),theta(PoroThetac,Np);const Copy<float> p(PorePressc,Np),p0(PorePress0c,Np),rate(PorePressRatec,Np),plastic(Kplasticc,Np),posdiv(PosDivc,Np);
    const unsigned initialNpbOk=NpbOk;const auto oldInter=InterStep;const double oldSpeed=DynamicConductivitySpeedMax;const double oldVelMax=VelMax;const float oldVisc=ViscDtMax;
    for(unsigned q=0;q<Np;q++){Velrhopc[q]=TFloat4(0,0,0,RhopZero);Sigmac[q]=tsymatrix3d{};PorePressc[q]=128;PorePress0c[q]=PorePressRatec[q]=0;PoroJc[q]=1;PoroThetac[q]=0;}
    MdbcBoundCorrection();const std::vector<byte> legacy(BoundModec,BoundModec+Np);const unsigned farSlot=map[791],nearSlot=map[254];
    Need(farSlot<initialNpbOk&&legacy[farSlot]==BMODE_MDBC2OFF&&legacy[nearSlot]==BMODE_MDBC2,"Retained original inactive791/active254 observation changed");
    std::ofstream pairs(fs::path(cfg->DirOut)/"pairs.csv");pairs<<std::setprecision(17)<<"fixed_native_id,fluid_native_id,rr2,stored_R2,in_actual_Darcy_support\n";
    const Visits farVisits=Search(farSlot,pairs),nearVisits=Search(nearSlot,pairs);Need(farVisits.pairs>0&&farVisits.inrange==0&&farVisits.minrr>double(KernelSize2)&&nearVisits.inrange>0,"Actual nsearch does not distinguish false candidate from true in-range wall");pairs.flush();Need(bool(pairs),"Pair CSV write failed");
    // Observer allocation budget includes Ace/ordinary force scratch, but not dynamic derivative scratch.
    // Allocate only while all feedback/dynamic/wall flags remain false; no interaction force is called.
    InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();Need(Acec&&BoundDerivativeVelc==nullptr,"Pre-allocation did not preserve observer scratch budget");
    unsigned successfulRows=0;bool negativeRejected=false;
    try{
      RestoreFlags restore{NpbOk,PorosityFeedback,DynamicPorePressure,DynamicPoreWall,NpbOk,PorosityFeedback,DynamicPorePressure,DynamicPoreWall};
      NpbOk=0;PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true; // State/Ace wall reconstruction is intentionally not part of this predicate check.
      for(unsigned q=0;q<Np;q++){PoroJc[q]=1;PoroThetac[q]=0;PorePressc[q]=128;PorePressRatec[q]=1234567.f;CorrMatc[q]=TMatrix3d(1,0,0,0,0,0,0,0,1);Acec[q]=TFloat3(0);BoundModec[q]=legacy[q];}
      const Copy<double> validj(PoroJc,Np),validtheta(PoroThetac,Np);const Copy<float> validp(PorePressc,Np);const Copy<tmatrix3d> validc(CorrMatc,Np);const Copy<tfloat3> valida(Acec,Np);const Copy<byte> validm(BoundModec,Np);
      std::ofstream values(fs::path(cfg->DirOut)/"rates.csv");values<<std::setprecision(17)<<"case,native_soil_id,actual_rate_Pa_s\n";
      for(unsigned trial=0;trial<2;trial++){
        validj.Restore();validp.Restore();validc.Restore();valida.Restore();validm.Restore();
        if(trial){const double nan=std::numeric_limits<double>::quiet_NaN();const float fnan=std::numeric_limits<float>::quiet_NaN();PoroJc[farSlot]=nan;CorrMatc[farSlot]=TMatrix3d(nan);PorePressc[farSlot]=fnan;Acec[farSlot]=TFloat3(fnan);}
        const Copy<double> inputj(PoroJc,Np);const Copy<float> inputp(PorePressc,Np);const Copy<tmatrix3d> inputc(CorrMatc,Np);const Copy<tfloat3> inputa(Acec,Np);
        ComputeDynamicPorePressureRateCpu();
        Need(inputj.Equal()&&inputp.Equal()&&inputc.Equal()&&inputa.Equal()&&validtheta.Equal()&&validm.Equal(),"Actual rate changed prescribed inputs");
        for(unsigned id=Fixed;id<Total;id++){const unsigned q=map[id];Need(std::isfinite(PorePressRatec[q])&&PorePressRatec[q]==0.f,"Out-of-support poison or inactive candidate changed native zero rate");values<<(trial?"poison791":"finite")<<','<<id<<','<<PorePressRatec[q]<<'\n';successfulRows++;}
      }
      validj.Restore();validp.Restore();validc.Restore();valida.Restore();validm.Restore();BoundModec[nearSlot]=BMODE_MDBC2OFF;
      try{ComputeDynamicPorePressureRateCpu();}
      catch(const JException& e){negativeRejected=e.ToStr().find("Dynamic Darcy fixture produced a nonfinite pressure rate or conductivity-gradient speed.")!=std::string::npos;Need(negativeRejected,"Unexpected in-support negative exception");}
      Need(negativeRejected,"Actual in-range inactive254 was silently accepted"); // Partial rate writes before rejection are deliberately unrestricted.
      values.flush();Need(bool(values),"Rate CSV write failed");
    }catch(...){PosInteraction_Forces();InterStep=oldInter;throw;}
    PosInteraction_Forces();InterStep=oldInter;DynamicConductivitySpeedMax=oldSpeed;VelMax=oldVelMax;ViscDtMax=oldVisc;
    Need(NpbOk==initialNpbOk&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&!PeriActive&&!Acec&&!BoundDerivativeVelc&&ids.Equal()&&cells.Equal()&&codes.Equal()&&pos.Equal()&&normal.Equal()&&selectors.Equal(),"Original controls/geometry/codes/cells not restored");
    vel.Restore();sigma.Restore();modes.Restore();tan.Restore();load.Restore();corr.Restore();j.Restore();theta.Restore();p.Restore();p0.Restore();rate.Restore();
    Need(vel.Equal()&&sigma.Equal()&&modes.Equal()&&tan.Equal()&&load.Equal()&&corr.Equal()&&j.Equal()&&theta.Equal()&&p.Equal()&&p0.Equal()&&rate.Equal()&&plastic.Equal()&&fstype.Equal()&&fsnormal.Equal()&&posdiv.Equal(),"Original persistent arrays not restored");Map();NoStep();
    Need(successfulRows==10000&&negativeRejected,"CPU predicate coverage incomplete");std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_inactive_cutoff_cpu_r1\",\"passed\":true,\"native_ids\":7060,\"soil\":5000,\"finite_and_poison_zero_rows\":"<<successfulRows<<",\"far791_actual_search_pairs\":"<<farVisits.pairs<<",\"far791_in_range_pairs\":"<<farVisits.inrange<<",\"far791_min_rr2\":"<<farVisits.minrr<<",\"near254_in_range_pairs\":"<<nearVisits.inrange<<",\"in_range_negative_rejected\":true,\"original_controls_IDs_cells_arrays_restored\":true,\"CODE_or_periodic_state_edits\":false,\"invalid_rate_unchanged_claimed\":false,\"physical_steps\":0,\"force_state_or_gravity_trajectory\":false,\"public_wall_or_physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=6&&std::string(argv[1])=="--predicate","Use --predicate -cpu -ompthreads:1 -stable -mdbc_freeslip OBSERVER_SEED FRESH_RESULT");AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=2;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!fs::exists(cfg.DirOut),"Fresh CPU predicate output required");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr());return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"CPU cutoff predicate failed; preserve output\n";return 2;}}

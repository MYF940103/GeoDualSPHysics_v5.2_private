// Saved-state, new zero-step CPU evaluation. Never an original-rate replay or solver.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "JException.h"
#include "FunSphKernel.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <climits>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("LianC08DarcyZeroCpu","r1","07-11-2026");
namespace fs=std::filesystem;
static_assert(sizeof(unsigned)==4&&sizeof(tfloat3)==12&&sizeof(tdouble3)==24,"Retained typed22 scalar/vector layout required");
static constexpr unsigned Total=7060,Fixed=2060,Soil=5000,Part=1000,Samples=1001;
static void Need(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static tdouble3 Product(tmatrix3d c,tdouble3 a){return TDouble3(c.a11*a.x+c.a12*a.y+c.a13*a.z,c.a21*a.x+c.a22*a.y+c.a23*a.z,c.a31*a.x+c.a32*a.y+c.a33*a.z);}
static bool Finite(float v){return std::isfinite(v);}static bool Finite(double v){return std::isfinite(v);}static bool Finite(unsigned){return true;}
static bool Finite(tfloat3 v){return Finite(v.x)&&Finite(v.y)&&Finite(v.z);}static bool Finite(tdouble3 v){return Finite(v.x)&&Finite(v.y)&&Finite(v.z);}
template<class T>static std::vector<T> ReadArray(std::ifstream& f){std::vector<T> v(Total);f.read(reinterpret_cast<char*>(v.data()),std::streamsize(sizeof(T)*Total));Need(bool(f),"Truncated typed22 array");for(const auto& x:v)Need(Finite(x),"Nonfinite typed22 value");return v;}
template<class T>struct Held{T* p;std::vector<T> v;Held(T* a,unsigned n):p(a),v(a,a+n){}bool Equal()const{return !memcmp(p,v.data(),v.size()*sizeof(T));}};
struct BorrowDerivative{tfloat3*& p;tfloat3* old;BorrowDerivative(tfloat3*& a,tfloat3* b):p(a),old(a){Need(!a,"Derivative scratch already owned");p=b;}~BorrowDerivative(){p=old;}};
struct Flags{bool &f,&d,&w,&s,&free,&damp;bool old[6];~Flags(){f=old[0];d=old[1];w=old[2];s=old[3];free=old[4];damp=old[5];}};
struct EtaScope{float& value;float old;EtaScope(float& v,float next):value(v),old(v){value=next;}~EtaScope(){value=old;}};
struct Snapshot{
  double time;std::vector<unsigned> id,fstype;std::vector<tdouble3> pos,sk,si,x0;
  std::vector<tfloat3> vel,legacykk,legacyij,normal,load;std::vector<float> rhop,kappa,p,p0,excess,posdiv;
  std::vector<double> j,n,theta,volume,rho,k;
  explicit Snapshot(const fs::path& dir){
    Need(dir.filename()=="upl_prestress10_CPU_r1_native_r1","Only the closed10s constant-k snapshot is admitted");
    std::ifstream f(dir/"typed22.bin",std::ios::binary);unsigned h[3]={};f.read(reinterpret_cast<char*>(h),12);
    const std::uintmax_t stride=8+std::uintmax_t(Total)*212;
    Need(bool(f)&&h[0]==Total&&h[1]==22&&h[2]==Samples&&fs::file_size(dir/"typed22.bin")==12+Samples*stride,"Typed22 header/extent differs");
    f.seekg(std::streamoff(12+Part*stride));f.read(reinterpret_cast<char*>(&time),8);
    id=ReadArray<unsigned>(f);pos=ReadArray<tdouble3>(f);vel=ReadArray<tfloat3>(f);legacykk=ReadArray<tfloat3>(f);legacyij=ReadArray<tfloat3>(f);normal=ReadArray<tfloat3>(f);load=ReadArray<tfloat3>(f);
    rhop=ReadArray<float>(f);kappa=ReadArray<float>(f);p=ReadArray<float>(f);p0=ReadArray<float>(f);excess=ReadArray<float>(f);sk=ReadArray<tdouble3>(f);si=ReadArray<tdouble3>(f);fstype=ReadArray<unsigned>(f);
    j=ReadArray<double>(f);n=ReadArray<double>(f);theta=ReadArray<double>(f);volume=ReadArray<double>(f);rho=ReadArray<double>(f);k=ReadArray<double>(f);posdiv=ReadArray<float>(f);
    double scalar=0;for(unsigned step=0;step<4000000;step++)scalar+=.0000025;Need(!memcmp(&time,&scalar,8),"Selected snapshot scalar clock differs");
    std::ifstream ids(dir/"native_ids.csv");std::string line;Need(bool(std::getline(ids,line)),"Native initial-ID ledger missing");if(!line.empty()&&line.back()=='\r')line.pop_back();Need(line=="id,is_fixed,x0,y0,z0,initial_hydrostatic_p0_float_Pa","Initial ledger schema differs");x0.resize(Total);
    for(unsigned q=0;q<Total;q++){Need(bool(std::getline(ids,line)),"Incomplete initial ledger");std::replace(line.begin(),line.end(),',',' ');std::istringstream row(line);unsigned native=~0u,fixed=~0u;double pzero=0;row>>native>>fixed>>x0[q].x>>x0[q].y>>x0[q].z>>pzero;Need(bool(row)&&native==q&&fixed==unsigned(q<Fixed)&&Finite(x0[q])&&id[q]==q&&kappa[q]==0,"Initial/native ID or elastic state differs");Need(p0[q]==float(pzero),"Fixed material P0 baseline differs");if(q<Fixed)Need(!memcmp(&pos[q],&x0[q],sizeof(tdouble3)),"Saved fixed position differs");}
    Need(!std::getline(ids,line),"Unexpected extra initial ledger row");
  }
};
class Probe:public JSphCpuSingle{
  std::vector<unsigned> Map()const{
    Need(Np==Total&&Npb==Fixed,"Native counts changed");std::vector<unsigned> byid(Total,UINT_MAX);
    for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(id<Total&&byid[id]==UINT_MAX&&CODE_IsNormal(Codec[q])&&(id<Fixed?(q<Npb&&CODE_IsFixed(Codec[q])):(q>=Npb&&CODE_IsFluid(Codec[q]))),"Native ID/type changed");byid[id]=q;}
    Need(!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Native exclusion changed");return byid;
  }
  void CopySaved(const Snapshot& a){for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Posc[q]=a.pos[id];Velrhopc[q]=TFloat4(a.vel[id].x,a.vel[id].y,a.vel[id].z,a.rhop[id]);const auto kk=a.sk[id],ij=a.si[id];Sigmac[q]=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);Kplasticc[q]=a.kappa[id];PorePressc[q]=a.p[id];PorePress0c[q]=a.p0[id];PoroJc[q]=a.j[id];PoroThetac[q]=a.theta[id];FSTypec[q]=a.fstype[id];FSNormalc[q]=a.normal[id];PosDivc[q]=a.posdiv[id];HydroMechLoadAcec[q]=a.load[id];}}
  void Ledger()const{const double solid=1.-double(SoilCte.Porosity),v0=double(MassFluid)/RhopZero;for(unsigned q=Npb;q<Np;q++){double n,v,rho;GetPorosityFeedbackStateCpu(q,n,v,rho);Need(Finite(n)&&Finite(v)&&Finite(rho)&&PoroJc[q]>solid&&n>0&&n<1&&v==v0*PoroJc[q]&&float(rho)==Velrhopc[q].w&&GetDynamicConductivityCpu(q)==double(SoilCte.HydraulicConductivity),"Current-J ledger/cache/constant-k failed");}}
  std::vector<unsigned> Select(const Snapshot& a)const{
    const unsigned xs[]={0,1,2,25,50,75,97,98,99},zs[]={0,1,2,12,25,37,47,48,49};const auto byid=Map();std::vector<unsigned> chosen;
    for(unsigned z:zs)for(unsigned x:xs){unsigned found=UINT_MAX;for(unsigned id=Fixed;id<Total;id++)if(fabs(a.x0[id].x-(.02+.04*x))<=64*DBL_EPSILON*4&&fabs(a.x0[id].z-(.02+.04*z))<=64*DBL_EPSILON*4){Need(found==UINT_MAX,"Duplicate initial grid match");found=byid[id];}Need(found!=UINT_MAX,"Missing selected initial material ID");chosen.push_back(found);}Need(chosen.size()==81,"Expected81 selected receivers");return chosen;
  }
  struct Reference{double rate,budget,trace,scalar,tracebudget,lap,compression;unsigned neighbors;};
  Reference Sum(unsigned i,float eta)const{
    const double water=SoilCte.PoreWaterRho,kw=SoilCte.PoreWaterBulkModulus,k=SoilCte.HydraulicConductivity,v0=double(MassFluid)/RhopZero,n=1.-(1.-double(SoilCte.Porosity))/PoroJc[i];
    double lp=0,diva=0,absolute=0;tdouble3 gp=TDouble3(0),moment=TDouble3(0);unsigned count=0;
    // Independent all-real-particle enumeration; the production function uses cell lists.
    for(unsigned j=0;j<Np;j++)if(CODE_IsFluid(Codec[j])||(j<Npb&&CODE_IsFixed(Codec[j])&&BoundModec[j]==BMODE_MDBC2)){
      const auto d=Posc[i]-Posc[j];const double rr=d.x*d.x+d.z*d.z;if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Cubic>(CSP,float(rr))),gi=Product(CorrMatc[i],g),gj=Product(CorrMatc[j],g);const double v=v0*PoroJc[j],dp=double(PorePressc[i])-PorePressc[j],w=v*Dot(d,gi+gj)/(rr+double(eta));const auto da=ToTDouble3(Acec[j])-ToTDouble3(Acec[i]);
      lp+=w*dp;moment=moment+d*w;gp=gp-gi*(v*dp);diva+=v*Dot(da,gi);absolute+=fabs(w*dp)+water*v*(fabs(da.x*gi.x)+fabs(da.z*gi.z));count++;
    }
    double tensortrace=0,tensorabs=0;
    for(unsigned j=0;j<Np;j++)if(CODE_IsFluid(Codec[j])||(j<Npb&&CODE_IsFixed(Codec[j])&&BoundModec[j]==BMODE_MDBC2)){
      const auto r=Posc[j]-Posc[i];const double rr=r.x*r.x+r.z*r.z;if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;const auto g=r*(-double(fsph::GetKernel_Fac<KERNEL_Cubic>(CSP,float(rr)))),gi=Product(CorrMatc[i],g),gj=Product(CorrMatc[j],g);const double v=v0*PoroJc[j],df=double(PorePressc[j])-PorePressc[i],rem=df-Dot(gp,r),factor=v*Dot(r,(gi+gj)*.5)/(rr+double(eta)),xx=rem*(4*r.x*r.x/rr-1)*factor,zz=rem*(4*r.z*r.z/rr-1)*factor;tensortrace+=xx+zz;tensorabs+=fabs(xx)+fabs(zz);
    }
    const bool surface=IsFreeSurfaceParticle(i,Codec,FSTypec);const auto ai=ToTDouble3(Acec[i]);const double scalar=lp-Dot(gp,moment),lap=surface?lp+water*(Dot(ai,moment)+diva):tensortrace+water*diva;
    absolute+=(surface?water*(fabs(ai.x*moment.x)+fabs(ai.z*moment.z)):fabs(gp.x*moment.x)+fabs(gp.z*moment.z));const double compression=-kw/n*PoroThetac[i],scale=kw/n*k/(water*9.80665);
    const double budget=(32*FLT_EPSILON+4096*DBL_EPSILON)*(std::max)(1.,fabs(compression)+scale*absolute),neps=(64*count+256)*DBL_EPSILON,tb=neps/(1.-neps)*(std::max)(1.,tensorabs+fabs(lp)+fabs(gp.x*moment.x)+fabs(gp.z*moment.z));
    return{compression+scale*lap,budget,tensortrace,scalar,tb,lap,compression,count};
  }
public:
  Probe(){PorosityObserver=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log,const Snapshot& a){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Need(PorosityObserver&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&HydroMech&&!HydroMechDynamicSeepage&&Simulate2D&&!PeriActive&&TKernel==KERNEL_Cubic&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundModec&&BoundSlipModec&&TangenVelc,"Legitimate observer C08 initialization differs");
    Need(TimeMax==0&&!PartBegin&&!Acec&&!BoundDerivativeVelc&&!SoilDamping&&!SoilStressRateGradCorr&&!SoilHourglassXi&&!HourglassCpu&&!SoilBoundaryDerivativeSPR&&!PoreShepardRegularization&&!HydroMechDrainage&&!HydroMechFreeSeepage&&!DynamicPoreConductivity&&!Shifting&&!Damping&&!ArtificialStress&&!NoPenetration&&!WithFloating&&!UseDEM&&!AccInput&&!StrainSoftening,"Zero-step lifecycle/control differs");
    Need(Dp==.04&&KernelH==float(.048)&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==float(.0002)&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&Gravity==TFloat3(0,0,-9.81f)&&TVisco==VISCO_Artificial&&Visco==.1f&&SoilDampingCoef==.02f&&PoreCompressionGradCorr&&PoreCompressionSourceMode==0&&TDensity==DDT_None&&HydroMechTopLoadMode==HMLOAD_None,"Saved-state material/force options differ");
    auto byid=Map();for(unsigned id=0;id<Fixed;id++)Need(!memcmp(Posc+byid[id],&a.pos[id],sizeof(tdouble3)),"Fresh fixed seed differs from saved source");
    CopySaved(a);LoadDcellParticles(Np,Codec,Posc,Dcellc);BoundChanged=true;RunCellDivide(false);Map();CopySaved(a);Ledger();
    const auto selected=Select(a);const float eta=Eta2;Need(eta>0&&Eta2==float((double(KernelH)*.1)*(double(KernelH)*.1)),"OriginalEta2 differs");
    const auto oldInter=InterStep;const double oldSpeed=DynamicConductivitySpeedMax,oldVel=VelMax;const float oldVisc=ViscDtMax;InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();
    double maxRatio=0,maxTraceRatio=0,deltaSquare=0,deltaMax=0,rateMax[2]={};unsigned fsChanged=0,fsCount=0,active=0;std::vector<float> baseline,candidate;std::ofstream rows(fs::path(cfg->DirOut)/"receivers.csv");rows<<std::setprecision(17)<<"variant,native_id,x,z,saved_fstype,recomputed_fstype,J,p,theta,Ace_x,Ace_z,Cxx,Cxz,Czx,Czz,neighbors,actual_rate_Pa_s,reference_rate_Pa_s,roundoff_budget_Pa_s,tensor_trace,scalar_defect,trace_identity_budget,lap,compression_Pa_s\n";
    try{
      Need(Acec&&Rsigmac&&Pressc&&Arc&&!BoundDerivativeVelc,"Observer temporary allocation differs");std::vector<tfloat3> derivative(Np,TFloat3(0));
      {BorrowDerivative borrow(BoundDerivativeVelc,derivative.data());Flags flags{PorosityFeedback,DynamicPorePressure,DynamicPoreWall,SoilStressRateGradCorr,HydroMechFreeSeepage,SoilDamping,{PorosityFeedback,DynamicPorePressure,DynamicPoreWall,SoilStressRateGradCorr,HydroMechFreeSeepage,SoilDamping}};PorosityFeedback=DynamicPorePressure=DynamicPoreWall=SoilStressRateGradCorr=HydroMechFreeSeepage=SoilDamping=true;
        ComputeFreeSurfaceTracking();ApplyHydroMechTopLoadAcceleration();ApplyFreeSurfacePorePressure(); // DefaultEta only; legacyDrain=false is a no-op.
        for(unsigned q=Npb;q<Np;q++){fsChanged+=FSTypec[q]!=a.fstype[Idpc[q]];if(IsFreeSurfaceParticle(q,Codec,FSTypec)){fsCount++;Need(PorePressc[q]<=0,"Saved positive pressure at refreshed true FS");}}
        for(unsigned q=0;q<NpbOk;q++)active+=BoundModec[q]==BMODE_MDBC2;
        const stinterparmsc parms=StInterparmsc(Np,Npb,NpbOk,DivData,Dcellc,Posc,Velrhopc,Idpc,Codec,Pressc,PorePressc,PorePressRatec,FSTypec,FSNormalc,NULL,CorrMatc,Arc,Acec,Deltac,ShiftingMode,ShiftPosfsc,SpsTauc,SpsGradvelc,Sigmac,Rsigmac,ArtificialStressc);StInterResultc result;result.viscdt=0;JSphCpu::Interaction_Forces_ct(parms,result);AddSoilDampingCpu(Np,Npb,Codec,Velrhopc,Acec);for(unsigned q=Npb;q<Np;q++)Acec[q].y=0;Need(std::isfinite(result.viscdt)&&result.viscdt>=0&&Eta2==eta,"Actualct viscosity/Eta invalid");
        for(unsigned q=Npb;q<Np;q++){const auto s=Rsigmac[q];Need(Finite(Acec[q])&&Finite(PoroThetac[q])&&Finite(Arc[q])&&Finite(s.xx)&&Finite(s.xy)&&Finite(s.xz)&&Finite(s.yy)&&Finite(s.yz)&&Finite(s.zz),"Actualct returned nonfinite force/theta/stress rate");}
        ComputeDynamicPoreWallAccelerationCpu();Ledger();
        const Held<tdouble3> pos(Posc,Np);const Held<tfloat4> vel(Velrhopc,Np);const Held<tsymatrix3d> sigma(Sigmac,Np);const Held<double> j(PoroJc,Np),theta(PoroThetac,Np);const Held<float> p(PorePressc,Np),p0(PorePress0c,Np),kap(Kplasticc,Np),pd(PosDivc,Np),ar(Arc,Np),press(Pressc,Np);const Held<tmatrix3d> c(CorrMatc,Np);const Held<unsigned> ids(Idpc,Np),cell(Dcellc,Np),fstype(FSTypec,Np);const Held<typecode> codes(Codec,Np);const Held<tfloat3> ace(Acec,Np),normal(FSNormalc,Np),load(HydroMechLoadAcec,Np),dv(BoundDerivativeVelc,Np),tangent(TangenVelc,Np),bn(BoundNormalc,Np);const Held<byte> modes(BoundModec,Np),slip(BoundSlipModec,Np);const Held<tsymatrix3f> sr(Rsigmac,Np);
        for(unsigned pass=0;pass<3;pass++){
          const float localEta=(pass==1?0.f:eta);{EtaScope onlyDarcy(Eta2,localEta);ComputeDynamicPorePressureRateCpu();}Need(Eta2==eta,"Eta was not restored before non-Darcy work");
          Need(pos.Equal()&&vel.Equal()&&sigma.Equal()&&j.Equal()&&theta.Equal()&&p.Equal()&&p0.Equal()&&kap.Equal()&&pd.Equal()&&ar.Equal()&&press.Equal()&&c.Equal()&&ids.Equal()&&cell.Equal()&&fstype.Equal()&&codes.Equal()&&ace.Equal()&&normal.Equal()&&load.Equal()&&dv.Equal()&&tangent.Equal()&&bn.Equal()&&modes.Equal()&&slip.Equal()&&sr.Equal(),"Darcy branch contaminated held upstream fields");Ledger();
          for(unsigned q=Npb;q<Np;q++)Need(std::isfinite(PorePressRatec[q]),"Nonfinite actual native Darcy rate");
          if(pass==0)baseline.assign(PorePressRatec+Npb,PorePressRatec+Np);else if(pass==1)candidate.assign(PorePressRatec+Npb,PorePressRatec+Np);else Need(!memcmp(PorePressRatec+Npb,baseline.data(),Soil*sizeof(float)),"Restored baseline rate is not bit-exact");
          if(pass<2)for(unsigned q:selected){const auto ref=Sum(q,localEta);const double error=fabs(double(PorePressRatec[q])-ref.rate),traceerror=fabs(ref.trace-ref.scalar);Need(error<=ref.budget&&traceerror<=ref.tracebudget,"Actual rate/reference or Eq23trace identity budget failed");maxRatio=(std::max)(maxRatio,error/ref.budget);maxTraceRatio=(std::max)(maxTraceRatio,traceerror/ref.tracebudget);const auto m=CorrMatc[q];rows<<(pass?"Cavg_Eta0":"Cavg_Eta2")<<','<<Idpc[q]<<','<<Posc[q].x<<','<<Posc[q].z<<','<<a.fstype[Idpc[q]]<<','<<FSTypec[q]<<','<<PoroJc[q]<<','<<PorePressc[q]<<','<<PoroThetac[q]<<','<<Acec[q].x<<','<<Acec[q].z<<','<<m.a11<<','<<m.a13<<','<<m.a31<<','<<m.a33<<','<<ref.neighbors<<','<<PorePressRatec[q]<<','<<ref.rate<<','<<ref.budget<<','<<ref.trace<<','<<ref.scalar<<','<<ref.tracebudget<<','<<ref.lap<<','<<ref.compression<<'\n';}
        }
        for(unsigned q=0;q<Soil;q++){const double difference=double(candidate[q])-baseline[q];deltaSquare+=difference*difference;deltaMax=(std::max)(deltaMax,fabs(difference));rateMax[0]=(std::max)(rateMax[0],fabs(double(baseline[q])));rateMax[1]=(std::max)(rateMax[1],fabs(double(candidate[q])));}Need(fsCount>0&&active>0,"Actual FS/wall coverage empty");
      }
    }catch(...){PosInteraction_Forces();InterStep=oldInter;DynamicConductivitySpeedMax=oldSpeed;VelMax=oldVel;ViscDtMax=oldVisc;throw;}
    PosInteraction_Forces();InterStep=oldInter;DynamicConductivitySpeedMax=oldSpeed;VelMax=oldVel;ViscDtMax=oldVisc;Need(!Acec&&!BoundDerivativeVelc&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&!HydroMechFreeSeepage&&!SoilDamping&&!SoilStressRateGradCorr&&TimeStep==0&&Nstep==0&&!PosPrec&&!PoroJPrec&&Eta2==eta,"Scratch/flags/time/Eta restoration failed");Map();rows.flush();Need(bool(rows),"ReceiverCSV write failed");
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_lian_c08_darcy_zero_cpu_r1\",\"passed\":true,\"source_part\":1000,\"source_completed_step\":4000000,\"source_time_s\":"<<a.time<<",\"native_IDs\":7060,\"soil\":5000,\"fixed\":2060,\"physical_steps\":0,\"actual_ct_calls\":1,\"Darcy_calls\":3,\"selected_receivers\":81,\"receiver_rows\":162,\"active_walls\":"<<active<<",\"recomputed_FS23\":"<<fsCount<<",\"saved_vs_recomputed_FSType_changes\":"<<fsChanged<<",\"baseline_Eta2\":"<<eta<<",\"candidate_Darcy_Eta2\":0,\"restored_baseline_soil_rate_bits_exact\":true,\"upstream_fields_unchanged_between_rates\":true,\"max_rate_over_retained_roundoff_budget\":"<<maxRatio<<",\"max_trace_identity_over_budget\":"<<maxTraceRatio<<",\"rate_difference_RMS_Pa_s\":"<<sqrt(deltaSquare/Soil)<<",\"rate_difference_max_Pa_s\":"<<deltaMax<<",\"baseline_rate_absmax_Pa_s\":"<<rateMax[0]<<",\"candidate_rate_absmax_Pa_s\":"<<rateMax[1]<<",\"constant_k\":true,\"pair_symmetric_C_retained\":true,\"actual_finished_Ace_not_prescribed\":true,\"saved_original_C_or_Ace_available\":false,\"original_rate_replay\":false,\"physical_accuracy_or_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=8&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--snapshot","Use --check --snapshot CLOSED_NATIVE_DIR -cpu -ompthreads:1 -stable -mdbc_freeslip OBSERVER_SEED FRESH_OUT");const fs::path source=fs::absolute(argv[3]);const auto tests=fs::path(__FILE__).parent_path().parent_path();Need(tests.is_absolute()&&fs::equivalent(source,tests/"outputs/upl_prestress10_CPU_r1_native_r1"),"Only declared closed source directory is admitted");Snapshot snapshot(source);AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!fs::exists(cfg.DirOut),"Fresh CPU zero-step output required");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr(),snapshot);return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Darcy zero-step diagnostic failed; preserve partial output\n";return 2;}}

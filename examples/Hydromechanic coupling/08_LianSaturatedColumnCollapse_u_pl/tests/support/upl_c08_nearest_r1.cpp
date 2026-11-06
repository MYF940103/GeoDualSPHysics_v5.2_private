// Real retained case08 nearest-fit state-only regression against the closed primary baseline.
// Private one-nearest-fit state queries only; no public wall admission, force, rate or time step.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "JException.h"
#include "FunSphKernel.h"
#include "FunctionsMath.h"
#include "JCellSearch_inline.h"
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
#include <stdexcept>
#include <sstream>
#include <vector>
JAppInfo AppInfo("UplC08Nearest","r1","06-11-2026");
namespace fs=std::filesystem;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static constexpr unsigned Fixed=2060,Soil=5000,Total=Fixed+Soil;
static constexpr double Head=2.,PressureBudgetScale=256.;
template<class T>struct Copy{
  T* p;std::vector<T> v;
  Copy(T* a,unsigned n):p(a){if(p)v.assign(a,a+n);}
  void Restore()const{if(p&&!v.empty())memcpy(p,v.data(),sizeof(T)*v.size());}
  bool Equal()const{return !p||v.empty()||!memcmp(p,v.data(),sizeof(T)*v.size());}
  bool ExceptQuery()const{return !p||v.size()<=1||!memcmp(p+1,v.data()+1,sizeof(T)*(v.size()-1));}
  ~Copy(){Restore();}
};
struct RestoreControls{
  unsigned& count;TpSlipMode& slip;byte*& selector;bool& feedback;bool& dynamic;bool& wall;
  unsigned n;TpSlipMode s;byte* modes;bool f,d,w;
  ~RestoreControls(){count=n;slip=s;selector=modes;feedback=f;dynamic=d;wall=w;}
};
struct Support{double nearest=DBL_MAX,sum=0,submerged=0,det=0,condition=0;unsigned nodes=0;bool active=false,first=false;};
struct Baseline{bool seen=false,physicalNear=false,accepted=false;unsigned mk=0,mode=0;std::array<double,10> physical{};};
class Probe:public JSphCpuSingle{
  std::vector<unsigned> NativeSoil;
  std::vector<Baseline> LoadBaseline(const fs::path& path)const{
    std::ifstream input(path);Need(bool(input),"Closed primary CSV is missing");std::string line;Need(bool(std::getline(input,line)),"Missing primary CSV header");if(!line.empty()&&line.back()=='\r')line.pop_back();
    Need(line=="native_id,mk,slipmode,B_x,B_z,normal_x,normal_z,mirror_x,mirror_z,true_nearest_m,physical_near,legacy_in_NpbOk,legacy_mode,mirror_nodes,sum_WV,submerged,raw_mls_det,original_first_order_gate,condition,actual_state_called,actual_reconstruction,expected_geometry_rejection,p_B_reference,p_B_actual,p_error,J_error,p_budget,J_budget,B_above_initial_H,negative_p_B","Unexpected original baseline CSV schema");
    std::vector<Baseline> rows(Fixed);unsigned count=0,nearRows=0,accepted=0;
    while(std::getline(input,line)){if(!line.empty()&&line.back()=='\r')line.pop_back();std::stringstream record(line);std::vector<std::string> v;std::string value;while(std::getline(record,value,','))v.push_back(value);Need(v.size()==30,"Truncated primary CSV row");const unsigned id=unsigned(std::stoul(v[0]));Need(id<Fixed&&!rows[id].seen,"Unknown/duplicate primary CSV ID");auto& r=rows[id];r.seen=true;r.physicalNear=(v[10]=="1");r.accepted=(v[20]=="1");r.mk=unsigned(std::stoul(v[1]));r.mode=unsigned(std::stoul(v[2]));
      const unsigned columns[10]={3,4,5,6,7,8,22,23,24,25};for(unsigned c=0;c<10;c++)if(c<7||r.accepted)r.physical[c]=std::stod(v[columns[c]]);Need(!r.accepted||r.physicalNear,"Far primary unexpectedly reconstructed");count++;nearRows+=unsigned(r.physicalNear);accepted+=unsigned(r.accepted);}
    Need(input.eof()&&count==Fixed&&nearRows==410&&accepted==400,"Closed primary CSV coverage mismatch");return rows;
  }
  tdouble3 NearestDisplacement(tdouble3 at,unsigned& source)const{
    double best=DBL_MAX;tdouble3 displacement=TDouble3(0);source=UINT_MAX;
    const StNgSearch search=nsearch::Init(at,false,DivData);
    for(int z=search.zini;z<search.zfin;z++)for(int y=search.yini;y<search.yfin;y++){
      const tuint2 range=nsearch::ParticleRange(y,z,search,DivData);
      for(unsigned p=range.x;p<range.y;p++)if(CODE_IsFluid(Codec[p])&&Velrhopc[p].w>0){const auto d=at-Posc[p];const double rr=d.x*d.x+d.z*d.z;if(float(rr)<=KernelSize2&&rr<best){best=rr;displacement=d;source=Idpc[p];}}
    }
    Need(source>=Fixed&&source<Total&&std::isfinite(best)&&best<DBL_MAX&&displacement!=TDouble3(0),"Failed original fit has no distinct finite real nearest source");return displacement;
  }
  std::vector<unsigned> Map()const{
    Need(Np==Total&&Npb==Fixed,"Initial retained particle count changed");
    std::vector<unsigned> m(Total,UINT_MAX);unsigned ns=0,nb=0;
    for(unsigned p=0;p<Np;p++){
      Need(Idpc[p]<Total&&m[Idpc[p]]==UINT_MAX,"Unknown/duplicate original native ID");m[Idpc[p]]=p;
      if(CODE_IsFluid(Codec[p])){Need(CODE_IsNormal(Codec[p])&&Idpc[p]>=Fixed,"Non-normal/unexpected soil ID");ns++;}
      else{Need(CODE_IsFixed(Codec[p])&&Idpc[p]<Fixed,"Unexpected fixed/native type");nb++;}
    }
    Need(ns==Soil&&nb==Fixed&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Native identity/exclusion mismatch");return m;
  }
  static unsigned Mk(unsigned id){return id<255?10:(id<1800?11:12);}
  void NoStep()const{Need(TimeStep==0&&Nstep==0&&!PoroJPrec&&!PosPrec,"Zero-step baseline advanced time or created predictor state");}
  Support Inspect(tdouble3 b,tdouble3 mirror)const{
    Support o;tmatrix3d raw=TMatrix3d(0),gram=TMatrix3d(0);
    for(unsigned p:NativeSoil){
      const auto db=b-Posc[p];o.nearest=(std::min)(o.nearest,db.x*db.x+db.z*db.z);
      const auto dr=mirror-Posc[p];const float rr=float(dr.x*dr.x+dr.z*dr.z);if(rr>KernelSize2)continue;
      float fac;const double wab=(rr==0?(fac=0.f,double(fsph::GetKernel_Wab<KERNEL_Cubic>(CSP,rr))):double(fsph::GetKernel_WabFac<KERNEL_Cubic>(CSP,rr,fac)));
      const double volume=double(MassFluid)/double(RhopZero)*PoroJc[p],w=wab*volume,fx=double(fac)*dr.x*volume,fz=double(fac)*dr.z*volume;
      o.nodes++;o.sum+=w;o.submerged-=volume*(dr.x*double(fac)*dr.x+dr.z*double(fac)*dr.z);
      raw.a11+=w;raw.a12+=dr.x*w;raw.a13+=dr.z*w;raw.a21+=fx;raw.a22+=dr.x*fx;raw.a23+=dr.z*fx;raw.a31+=fz;raw.a32+=dr.x*fz;raw.a33+=dr.z*fz;
      const double x=dr.x/KernelH,z=dr.z/KernelH;
      gram.a11+=w;gram.a12+=w*x;gram.a13+=w*z;gram.a21+=w*x;gram.a22+=w*x*x;gram.a23+=w*x*z;gram.a31+=w*z;gram.a32+=w*x*z;gram.a33+=w*z*z;
    }
    o.nearest=sqrt(o.nearest);o.det=fmath::Determinant3x3(raw);
    o.active=(o.submerged>0||o.sum>=double(MdbcThreshold)||(MdbcThreshold>=2&&o.sum+2>=double(MdbcThreshold)))&&o.sum>0;
    o.first=o.active&&std::isfinite(o.det)&&fabs(o.det)>=1e-3; // Existing production gate, never inverted below it.
    if(o.first){const double det=fmath::Determinant3x3(gram);Need(std::isfinite(det)&&det>0,"Admitted support lacks finite scaled condition matrix");
      const auto inv=fmath::InverseMatrix3x3(gram,det);const auto inf=[](tmatrix3d a){return (std::max)({fabs(a.a11)+fabs(a.a12)+fabs(a.a13),fabs(a.a21)+fabs(a.a22)+fabs(a.a23),fabs(a.a31)+fabs(a.a32)+fabs(a.a33)});};
      o.condition=(std::max)(1.,inf(gram)*inf(inv));Need(std::isfinite(o.condition),"Nonfinite admitted support condition");}
    return o;
  }
public:
  Probe(){PorosityObserver=true;} // The other three flags remain false through genuine InitRun.
  void Execute(const JSphCfgRun* cfg,JLog2* log,const fs::path& baselinePath){
    Need(!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall,"Observer ctor must not pre-enable feedback");
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Need(PorosityObserver&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&!HydroMechDynamicSeepage,"Actual initialization was not observer-only");
    Need(HydroMech&&Simulate2D&&TKernel==KERNEL_Cubic&&TStep==STEP_Symplectic&&CaseNp==Total&&CaseNpb==Fixed&&CaseNfluid==Soil&&TBoundary==BC_MDBC&&UseNormals&&BoundSlipModec&&BoundModec&&TangenVelc,"Wrong retained actual case08 observer seed");
    Need(!PeriActive&&!PartBegin&&!CaseNmoving&&!CaseNfloat&&!StrainSoftening&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilBoundaryDerivativeSPR&&!SoilHourglassXi&&!HourglassCpu&&!Shifting&&!Damping&&!SoilDamping&&!NoPenetration,"Zero-step baseline scope changed");
    Need(Dp==.04&&KernelH==float(.048)&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==2e-4f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&Gravity==TFloat3(0,0,-9.81f),"Paper material/geometry constants changed");
    Need(TimeMax==0&&BoundDerivativeVelc==nullptr&&!Acec&&PoroJc&&PoroThetac,"Unexpected integration/scratch state");
    const auto baseline=LoadBaseline(baselinePath);const auto map=Map();for(unsigned id=Fixed;id<Total;id++)NativeSoil.push_back(map[id]);NoStep();
    const Copy<tdouble3> originalpos(Posc,Np);const Copy<tfloat3> originalnormal(BoundNormalc,Np);const Copy<unsigned> originalids(Idpc,Np),originalcells(Dcellc,Np);const Copy<typecode> originalcodes(Codec,Np);
    const Copy<tfloat4> originalvel(Velrhopc,Np);const Copy<tsymatrix3d> originalsigma(Sigmac,Np);const Copy<float> originalp(PorePressc,Np),originalp0(PorePress0c,Np),originalrate(PorePressRatec,Np),originalk(Kplasticc,Np);
    const Copy<double> originalj(PoroJc,Np),originaltheta(PoroThetac,Np);const Copy<tfloat3> originaltan(TangenVelc,Np),originalfsnormal(FSNormalc,Np),originalload(HydroMechLoadAcec,Np);const Copy<byte> originalmode(BoundModec,Np),originalselector(BoundSlipModec,Np);const Copy<tmatrix3d> originalcorr(CorrMatc,Np);const Copy<unsigned> originalfstype(FSTypec,Np);const Copy<float> originalposdiv(PosDivc,Np);
    // Global affine pressure is prescribed, not solved. Negative side ghosts above H are retained.
    for(unsigned p=0;p<Np;p++){Velrhopc[p]=TFloat4(0,0,0,RhopZero);Sigmac[p]=TSymMatrix3d(-32,8,16,-48,4,-64);Kplasticc[p]=0;
      PoroJc[p]=1;PoroThetac[p]=0;PorePress0c[p]=PorePressRatec[p]=0;PorePressc[p]=float(double(SoilCte.PoreWaterRho)*double(Gravity.z)*(Posc[p].z-Head));}
    const Copy<tfloat4> fieldvel(Velrhopc,Np);const Copy<tsymatrix3d> fieldsigma(Sigmac,Np);const Copy<float> fieldp(PorePressc,Np);const Copy<double> fieldj(PoroJc,Np),fieldtheta(PoroThetac,Np);const Copy<tfloat3> fieldtan(TangenVelc,Np);
    const unsigned initialNpbOk=NpbOk;MdbcBoundCorrection(); // Actual legacy mDBC dispatch; no interaction force.
    std::vector<byte> legacy(BoundModec,BoundModec+Np);Need(originalpos.Equal()&&originalnormal.Equal()&&originalids.Equal()&&originalcells.Equal()&&originalcodes.Equal(),"Legacy correction changed geometry/IDs/cell list");
    for(unsigned p:NativeSoil)Need(!memcmp(Velrhopc+p,fieldvel.v.data()+p,sizeof(tfloat4))&&!memcmp(Sigmac+p,fieldsigma.v.data()+p,sizeof(tsymatrix3d))&&!memcmp(PorePressc+p,fieldp.v.data()+p,sizeof(float)),"Legacy correction modified native soil input");
    fieldvel.Restore();fieldsigma.Restore();fieldp.Restore();fieldj.Restore();fieldtheta.Restore();fieldtan.Restore();originalmode.Restore();
    std::ofstream csv(fs::path(cfg->DirOut)/"walls.csv");csv<<std::setprecision(17)<<"native_id,mk,slipmode,B_x,B_z,normal_x,normal_z,mirror_x,mirror_z,true_nearest_m,physical_near,legacy_in_NpbOk,legacy_mode,primary_raw_det,primary_first_order,retry,nearest_source_id,fit_center_x,fit_center_z,fitshift_x,fitshift_z,fit_shift_norm,fit_raw_det,fit_condition,actual_state_called,p_B_reference,p_B_actual,J_actual,p_error,J_error,p_budget,J_budget,primary_control_compared,primary_p_float_bytes_equal,primary_geometry_reference_derived_errors_equal,B_above_initial_H,negative_p_B\n";
    unsigned nearCount=0,farCount=0,pass=0,retries=0,primaryPairs=0;double maxp=0,maxj=0,maxratio=0,maxshift=0;
    {
      RestoreControls restore{NpbOk,SlipMode,BoundSlipModec,PorosityFeedback,DynamicPorePressure,DynamicPoreWall,NpbOk,SlipMode,BoundSlipModec,PorosityFeedback,DynamicPorePressure,DynamicPoreWall};
      PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;NpbOk=1;BoundSlipModec=nullptr;
      Need(CODE_IsFixed(Codec[0]),"Single query slot is not fixed");
      for(unsigned id=0;id<Fixed;id++){
        const unsigned p=map[id];const auto b=originalpos.v[p];const auto bn=originalnormal.v[p];const auto mirror=b+ToTDouble3(bn);Need(bn!=TFloat3(0),"Retained plane normal missing");
        const TpSlipMode mode=TpSlipMode(originalselector.v[p]);Need(mode==(Mk(id)==11?SLIP_NoSlip:SLIP_FreeSlip),"Original per-MK side/bed slip changed");
        const Support primary=Inspect(b,mirror);const bool isnear=primary.nearest*primary.nearest<=double(KernelSize2);const auto& control=baseline[id];Need(control.physicalNear==isnear&&control.mk==Mk(id)&&control.mode==unsigned(mode),"Primary geometry/identity eligibility changed");
        const double expected=float(double(SoilCte.PoreWaterRho)*double(Gravity.z)*(b.z-Head));tdouble3 centre=mirror,shift=TDouble3(0);unsigned source=UINT_MAX;bool retry=false,compared=false;double actual=0,actualj=0,ep=0,ej=0,pbudget=0,jbudget=0;Support fit=primary;
        if(isnear){nearCount++;Need(control.accepted==primary.first,"Original precheck no longer matches closed baseline");
          if(!primary.first){const auto nearDr=NearestDisplacement(mirror,source);centre=mirror-nearDr;shift=TDouble3(0)-nearDr;retry=true;fit=Inspect(b,centre);Need(fit.first,"Independent one-nearest retry fails original raw determinant/activation gate");retries++;maxshift=(std::max)(maxshift,sqrt(shift.x*shift.x+shift.z*shift.z));}
          Posc[0]=b;BoundNormalc[0]=bn;SlipMode=mode;
          const Copy<tfloat4> v(Velrhopc,Np);const Copy<tsymatrix3d> sigma(Sigmac,Np);const Copy<float> pnow(PorePressc,Np);const Copy<double> jnow(PoroJc,Np),tnow(PoroThetac,Np);const Copy<tfloat3> tan(TangenVelc,Np);const Copy<byte> modes(BoundModec,Np);
          ComputeDynamicPoreWallStateCpu(); // Actual bounded-retry state implementation; every near query must reconstruct.
          Need(v.ExceptQuery()&&sigma.ExceptQuery()&&pnow.ExceptQuery()&&jnow.ExceptQuery()&&tnow.ExceptQuery()&&tan.ExceptQuery()&&modes.ExceptQuery(),"Actual state modified another original slot");
          actual=PorePressc[0];actualj=PoroJc[0];ep=fabs(actual-expected);ej=fabs(actualj-1.);const double td=32768*DBL_EPSILON*fit.condition,tf=64*FLT_EPSILON*fit.condition;pbudget=PressureBudgetScale*tf;jbudget=2*td;
          Need(ep<=pbudget&&ej<=jbudget&&Velrhopc[0]==TFloat4(0,0,0,RhopZero)&&BoundModec[0]==BMODE_MDBC2,"Actual nearest-fit p/J/physical-fixed-state budget failed");pass++;maxp=(std::max)(maxp,ep);maxj=(std::max)(maxj,ej);maxratio=(std::max)({maxratio,ep/pbudget,ej/jbudget});
          if(!retry){const std::array<double,10> values={b.x,b.z,double(bn.x),double(bn.z),mirror.x,mirror.z,expected,actual,ep,ej};Need(values==control.physical,"Primary400 genuine physical/reference/derived-error CSV columns changed");const float oldp=float(control.physical[7]);Need(!memcmp(PorePressc,&oldp,sizeof(float)),"Primary400 pressure float bytes changed");compared=true;primaryPairs++;}
        }else{farCount++;Need(!control.accepted,"Far baseline unexpectedly reconstructed");} // No actual state call for far samples.
        csv<<id<<','<<Mk(id)<<','<<unsigned(mode)<<','<<b.x<<','<<b.z<<','<<bn.x<<','<<bn.z<<','<<mirror.x<<','<<mirror.z<<','<<primary.nearest<<','<<isnear<<','<<(p<initialNpbOk)<<','<<unsigned(legacy[p])<<','<<primary.det<<','<<primary.first<<','<<retry<<',';if(retry)csv<<source;csv<<','<<centre.x<<','<<centre.z<<','<<shift.x<<','<<shift.z<<','<<sqrt(shift.x*shift.x+shift.z*shift.z)<<','<<fit.det<<',';if(isnear)csv<<fit.condition;csv<<','<<isnear<<','<<expected<<',';if(isnear)csv<<actual;csv<<',';if(isnear)csv<<actualj;csv<<',';if(isnear)csv<<ep;csv<<',';if(isnear)csv<<ej;csv<<',';if(isnear)csv<<pbudget;csv<<',';if(isnear)csv<<jbudget;csv<<','<<compared<<',';if(compared)csv<<1;csv<<',';if(compared)csv<<1;csv<<','<<(b.z>Head)<<','<<(expected<0)<<'\n';
        Posc[0]=originalpos.v[0];BoundNormalc[0]=originalnormal.v[0];
      }
    }
    Need(nearCount==410&&farCount==1650&&pass==410&&retries==10&&primaryPairs==400,"Nearest geometry baseline coverage differs from declared410/10/400; preserve evidence");
    Need(NpbOk==initialNpbOk&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&originalselector.Equal()&&originalpos.Equal()&&originalnormal.Equal()&&originalids.Equal()&&originalcells.Equal()&&originalcodes.Equal(),"Original geometry/IDs/flags/selector not restored");
    originalvel.Restore();originalsigma.Restore();originalp.Restore();originalp0.Restore();originalrate.Restore();originalk.Restore();originalj.Restore();originaltheta.Restore();originaltan.Restore();originalmode.Restore();
    Need(originalvel.Equal()&&originalsigma.Equal()&&originalp.Equal()&&originalp0.Equal()&&originalrate.Equal()&&originalk.Equal()&&originalj.Equal()&&originaltheta.Equal()&&originaltan.Equal()&&originalmode.Equal()&&originalcorr.Equal()&&originalfstype.Equal()&&originalfsnormal.Equal()&&originalposdiv.Equal()&&originalload.Equal(),"Original persistent arrays not restored");NoStep();csv.flush();Need(bool(csv),"Wall diagnostic CSV write failed");
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_c08_nearest_r1\",\"passed\":true,\"native_ids\":7060,\"native_soil\":5000,\"original_walls\":2060,\"physical_near_queries\":"<<nearCount<<",\"physical_far_no_state_call\":"<<farCount<<",\"actual_state_reconstructions\":"<<pass<<",\"independent_required_nearest_retries\":"<<retries<<",\"original_primary_physical_CSV_pairs\":"<<primaryPairs<<",\"primary_actual_p_float_bytes_equal\":true,\"old_raw_J_binary_equality_claimed\":false,\"max_retry_shift_m\":"<<maxshift<<",\"max_p_error_Pa\":"<<maxp<<",\"max_J_error\":"<<maxj<<",\"max_error_over_original_budget\":"<<maxratio<<",\"geometry_IDs_cells_arrays_controls_restored\":true,\"observer_only_actual_initialization\":true,\"physical_steps\":0,\"force_rate_or_gravity_trajectory\":false,\"wet_contact_or_public_dynamic_wall_admission\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=8&&std::string(argv[1])=="--state"&&std::string(argv[2])=="--baseline","Use --state --baseline ABS_CLOSED_PRIMARY_CSV -cpu -ompthreads:1 -stable -mdbc_freeslip OBSERVER_SEED FRESH_RESULT");const fs::path baseline=argv[3];AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());
  Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!fs::exists(cfg.DirOut),"Fresh CPU nearest-fit observer output required");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr(),baseline);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Case08 nearest-fit observer failed; preserve output\n";return 2;}}

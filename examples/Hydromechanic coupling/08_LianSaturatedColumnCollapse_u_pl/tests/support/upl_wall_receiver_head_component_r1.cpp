// Private two-query state-only diagnostic on the genuine retained CPU fluid cloud.
// Query points are not physical container walls; no force, rate or trajectory is run.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "FunSphKernel.h"
#include "FunctionsMath.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
JAppInfo AppInfo("UplWallReceiverHeadCpu","r1","06-11-2026");
namespace fs=std::filesystem;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static constexpr unsigned Native=1024,Fixed=256;
static constexpr double Dp0=1./512.,Width=1./16.,Head=128.,Raw=1.5*Dp0;
using Row=std::array<double,26>;
template<class T>struct Copy{
  T* p;std::vector<T> v;Copy(T* a,unsigned n):p(a){Need(a||!n,"Missing component array");if(n)v.assign(a,a+n);}
  void Restore()const{if(!v.empty())memcpy(p,v.data(),sizeof(T)*v.size());}
  bool Equal()const{return v.empty()||!memcmp(p,v.data(),sizeof(T)*v.size());}
};
struct RestoreControls{
  unsigned& count;TpSlipMode& mode;byte*& selector;tfloat3& gravity;tfloat3& cspgravity;
  unsigned oldcount;TpSlipMode oldmode;byte* oldselector;tfloat3 oldgravity,oldcspgravity;
  ~RestoreControls(){count=oldcount;mode=oldmode;selector=oldselector;gravity=oldgravity;cspgravity=oldcspgravity;}
};
class Probe:public JSphCpuSingle{
  std::vector<unsigned> Soil;unsigned Cases=0,Rows=0,NegativeRows=0;double MaxRatio=0,MinBugSeparation=DBL_MAX;
  static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
  std::vector<unsigned> Map()const{
    std::vector<unsigned> m(CaseNp,UINT_MAX);unsigned nf=0,nb=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){Need(Idpc[p]<CaseNp&&m[Idpc[p]]==UINT_MAX,"Unknown/duplicate native ID");m[Idpc[p]]=p;if(CODE_IsFluid(Codec[p]))nf++;else{Need(CODE_IsFixed(Codec[p]),"Nonfixed ID");nb++;}}
    Need(nf==Native&&nb==Fixed&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Native/exclusion mismatch");return m;
  }
  void NoStep()const{Need(TimeStep==0&&Nstep==0&&!PoroJPrec,"State-only component advanced time");}
  void Reset(){for(unsigned p=0;p<Np;p++){Velrhopc[p]=TFloat4(0,0,0,RhopZero);Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;PorePressc[p]=PorePress0c[p]=PorePressRatec[p]=0;PoroJc[p]=1;PoroThetac[p]=0;CorrMatc[p]=TMatrix3d(0);if(TangenVelc)TangenVelc[p]=TFloat3(0);}}
  std::vector<Row> Snapshot()const{
    const auto m=Map();std::vector<Row> out;for(unsigned id:Soil){const unsigned p=m[id];const auto x=Posc[p];const auto v=Velrhopc[p];const auto s=Sigmac[p];const auto n=FSNormalc[p];const auto l=HydroMechLoadAcec[p];
      out.push_back({x.x,x.y,x.z,v.x,v.y,v.z,PorePressc[p],PorePress0c[p],PoroJc[p],PoroThetac[p],s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,Kplasticc[p],double(FSTypec[p]),n.x,n.y,n.z,PosDivc[p],l.x,l.y,l.z,v.w});for(double a:out.back())Need(std::isfinite(a),"Nonfinite native physical field");}return out;
  }
  double Condition(tdouble3 at)const{
    tmatrix3d m=TMatrix3d(0);double nearest=DBL_MAX;
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsFluid(Codec[p])){const auto d=Posc[p]-at;const double rr=d.x*d.x+d.z*d.z;nearest=(std::min)(nearest,rr);if(rr>double(KernelSize2))continue;
      const double wab=(TKernel==KERNEL_Cubic?fsph::GetKernel_Wab<KERNEL_Cubic>(CSP,float(rr)):fsph::GetKernel_Wab<KERNEL_Wendland>(CSP,float(rr)));if(wab<=0)continue;
      const double w=double(MassFluid)/RhopZero*PoroJc[p]*wab,x=d.x/KernelH,z=d.z/KernelH;m.a11+=w;m.a12+=w*x;m.a13+=w*z;m.a21+=w*x;m.a22+=w*x*x;m.a23+=w*x*z;m.a31+=w*z;m.a32+=w*x*z;m.a33+=w*z*z;}
    const double det=fmath::Determinant3x3(m);Need(nearest==0&&det>0,"Query is not a supported genuine fluid-node target");const auto inverse=fmath::InverseMatrix3x3(m,det);
    const auto inf=[](tmatrix3d a){return (std::max)({fabs(a.a11)+fabs(a.a12)+fabs(a.a13),fabs(a.a21)+fabs(a.a22)+fabs(a.a23),fabs(a.a31)+fabs(a.a32)+fabs(a.a33)});};return (std::max)(1.,inf(m)*inf(inverse));
  }
  void Check(bool firstx,std::ostream& out){
    const Copy<tdouble3> pos(Posc,Np);const Copy<tfloat3> bn(BoundNormalc,Np);const Copy<unsigned> ids(Idpc,Np);const Copy<typecode> code(Codec,Np);
    const Copy<tfloat4> oldvel(Velrhopc,Np);const Copy<tsymatrix3d> olds(Sigmac,Np);const Copy<float> oldp(PorePressc,Np),oldp0(PorePress0c,Np);const Copy<double> oldj(PoroJc,Np),oldt(PoroThetac,Np);const Copy<tfloat3> oldtan(TangenVelc,Np);const Copy<byte> oldmode(BoundModec,Np);
    for(unsigned p=0;p<Np;p++){PoroJc[p]=1.;PoroThetac[p]=0.;Velrhopc[p]=TFloat4(0,0,0,RhopZero);Sigmac[p]=tsymatrix3d{};PorePress0c[p]=0;
      const double pressure=Head+double(SoilCte.PoreWaterRho)*Dot(ToTDouble3(Gravity),Posc[p]);Need(fabs(pressure)<256,"Manufacture left retained pressure scale");PorePressc[p]=CODE_IsFluid(Codec[p])?float(pressure):12345.f;}
    for(unsigned query=0;query<2;query++){
      const bool xnormal=(query==0?firstx:!firstx);const auto target=TDouble3((xnormal?12.5:20.5)*Dp0,0,16.5*Dp0);
      BoundNormalc[query]=(xnormal?TFloat3(float(Raw),0,0):TFloat3(0,0,float(Raw)));Posc[query]=target-ToTDouble3(BoundNormalc[query]);
    }
    const auto previous=InterStep;InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();
    const auto before=Snapshot();const Copy<float> inputp(PorePressc,Np),rate(PorePressRatec,Np);const Copy<double> inputj(PoroJc,Np);const Copy<tmatrix3d> corr(CorrMatc,Np);const Copy<tfloat3> ace(Acec,Np);
    ComputeDynamicPoreWallStateCpu(); // Sole actual state consumer, NpbOk temporarily two; no C/Ace/rate/force call.
    const auto after=Snapshot();Need(!memcmp(before.data(),after.data(),Native*sizeof(Row))&&rate.Equal()&&corr.Equal()&&ace.Equal(),"State query modified native fields or untouched arrays");
    for(unsigned p=2;p<Np;p++)Need(!memcmp(PorePressc+p,inputp.v.data()+p,sizeof(float))&&!memcmp(PoroJc+p,inputj.v.data()+p,sizeof(double)),"Unselected p/J slot changed");
    const auto g=ToTDouble3(Gravity);const auto firstgn=(firstx?TDouble3(g.x,0,0):TDouble3(0,0,g.z));
    for(unsigned query=0;query<2;query++){
      const bool xnormal=(query==0?firstx:!firstx);const auto b=Posc[query];const auto raw=ToTDouble3(BoundNormalc[query]);const auto target=b+raw;
      const double condition=Condition(target),td=32768*DBL_EPSILON*condition,tf=64*FLT_EPSILON*condition,expected=float(Head+double(SoilCte.PoreWaterRho)*Dot(g,b));
      const double ep=fabs(PorePressc[query]-expected),ej=fabs(PoroJc[query]-1.);Need(ep<=256*tf&&ej<=2*td,"Per-receiver normal-head p/J budget failed");
      const double wrong=float(Head+double(SoilCte.PoreWaterRho)*(Dot(g,b)+Dot(g-firstgn,raw))),margin=fabs(wrong-expected);
      if(query==1){Need(margin>2*256*tf&&fabs(PorePressc[query]-wrong)>256*tf,"First-normal counterfactual not distinguishable under original p budget");MinBugSeparation=(std::min)(MinBugSeparation,margin/(256*tf));NegativeRows++;}else Need(margin==0,"First receiver should not separate its own normal");
      out<<(TKernel==KERNEL_Cubic?"Cubic":"Wendland")<<','<<unsigned(SlipMode)<<','<<firstx<<','<<query<<','<<Idpc[query]<<','<<xnormal<<','<<b.x<<','<<b.z<<','<<target.x<<','<<target.z<<','<<g.x<<','<<g.z<<','<<expected<<','<<PorePressc[query]<<','<<ep<<','<<ej<<','<<condition<<','<<td<<','<<tf<<','<<wrong<<','<<margin<<','<<(query==1?margin/(256*tf):0.)<<'\n';Rows++;MaxRatio=(std::max)({MaxRatio,ep/(256*tf),ej/(2*td)});
    }
    NoStep();PosInteraction_Forces();InterStep=previous;
    pos.Restore();bn.Restore();oldvel.Restore();olds.Restore();oldp.Restore();oldp0.Restore();oldj.Restore();oldt.Restore();oldtan.Restore();oldmode.Restore();
    Need(pos.Equal()&&bn.Equal()&&ids.Equal()&&code.Equal()&&oldvel.Equal()&&olds.Equal()&&oldp.Equal()&&oldp0.Equal()&&oldj.Equal()&&oldt.Equal()&&oldtan.Equal()&&oldmode.Equal(),"Query geometry/IDs/physical inputs not restored");Cases++;
  }
public:
  Probe(){PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Need(HydroMech&&!HydroMechDynamicSeepage&&Simulate2D&&(TKernel==KERNEL_Wendland||TKernel==KERNEL_Cubic)&&TStep==STEP_Symplectic&&CaseNpb==Fixed&&CaseNfluid==Native&&CaseNp==Native+Fixed&&TBoundary==BC_MDBC&&SlipMode==SLIP_FreeSlip&&MdbcCorrector&&!PeriX&&!PeriY&&PeriZ,"Wrong retained real seed");
    Need(!Gravity.x&&!Gravity.y&&!Gravity.z&&NpbOk>=2&&CODE_IsFixed(Codec[0])&&CODE_IsFixed(Codec[1])&&TangenVelc&&BoundModec,"Initial zero-g/fixed samples not retained");
    Need(SoilCte.PoreWaterRho==1000.f&&Dp==Dp0&&KernelH==float(1.8*Dp0)&&double(MassFluid)/RhopZero==Dp0*Dp0,"Changed retained pressure/J geometry scale");
    Need(!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!DynamicPoreConductivity&&!HourglassCpu&&!Shifting&&!Damping&&!InOut&&!AccInput&&!NoPenetration&&!SoilBoundaryDerivativeSPR,"Path outside state-only component scope");
    const auto m=Map();for(unsigned id=0;id<CaseNp;id++)if(CODE_IsFluid(Codec[m[id]]))Soil.push_back(id);Reset();const auto initial=Snapshot();NoStep();
    const unsigned ownedcount=NpbOk;const TpSlipMode ownedmode=SlipMode;byte* const ownedselector=BoundSlipModec;const auto ownedgravity=Gravity;const auto ownedcspgravity=CSP.gravity;
    std::ofstream csv(fs::path(cfg->DirOut)/"queries.csv");csv<<std::setprecision(17)<<"kernel,slipmode,first_x,query,retained_id,x_normal,B_x,B_z,mirror_x,mirror_z,g_x,g_z,expected_p,actual_p,p_error,J_error,condition,td,tf,analytic_old_first_normal_p,analytic_bug_margin,margin_over_original_p_budget\n";
    {
      RestoreControls restore{NpbOk,SlipMode,BoundSlipModec,Gravity,CSP.gravity,ownedcount,ownedmode,ownedselector,ownedgravity,ownedcspgravity};
      BoundSlipModec=nullptr;SlipMode=SLIP_FreeSlip;InitDynamicPoreWallCpu(); // Admit only the genuine original global-FS parallel zero-g fixture.
      NpbOk=2;Gravity=TFloat3(.5f,0,1.f);CSP.gravity=Gravity;
      for(TpSlipMode mode:{SLIP_FreeSlip,SLIP_NoSlip}){SlipMode=mode;Check(true,csv);Check(false,csv);}
    }
    const auto final=Snapshot();Need(NpbOk==ownedcount&&SlipMode==ownedmode&&BoundSlipModec==ownedselector&&!memcmp(&Gravity,&ownedgravity,sizeof(tfloat3))&&!memcmp(&CSP.gravity,&ownedcspgravity,sizeof(tfloat3))&&!memcmp(initial.data(),final.data(),Native*sizeof(Row)),"Original controls/native state not restored");
    Need(Cases==4&&Rows==8&&NegativeRows==4,"Declared two-query coverage incomplete");NoStep();csv.flush();Need(bool(csv),"Query CSV write failed");
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_wall_receiver_head_component_r1\",\"passed\":true,\"kernel\":\""<<(TKernel==KERNEL_Cubic?"Cubic":"Wendland")<<"\",\"cases\":"<<Cases<<",\"query_rows\":"<<Rows<<",\"eligible_first_normal_counterfactuals\":"<<NegativeRows<<",\"max_p_J_error_over_original_budget\":"<<MaxRatio<<",\"min_analytic_bug_separation_over_original_p_budget\":"<<MinBugSeparation<<",\"actual_state_calls\":4,\"native_soil\":1024,\"retained_fixed\":256,\"temporary_NpbOk\":2,\"controls_geometry_IDs_native_fields_restored\":true,\"actual_C_Ace_rate_force_called\":false,\"physical_steps\":0,\"physical_walls_or_periodic_gravity_admitted\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=6&&std::string(argv[1])=="--state","Use --state -cpu -ompthreads:1 -stable -mdbc_freeslip ZERO_G_SEED FRESH");AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=2;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());
  Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!fs::exists(cfg.DirOut),"Fresh CPU state-only component required");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr());return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Receiver head state-only fixture failed; preserve output\n";return 2;}}

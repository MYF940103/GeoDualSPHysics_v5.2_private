// Private instantaneous shear-force component; real CPU init and force, no step.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "FunSphKernel.h"
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
JAppInfo AppInfo("NoSlipCpuForceComponent","r2","06-11-2026");
namespace fs=std::filesystem;
static constexpr unsigned SoilCount=1024,WallCount=256;
static constexpr double Dp0=1./512.,Width=1./16.,Lz=1./16.,Tau=8.;
static void Need(bool ok,const char* s){if(!ok)throw std::runtime_error(s);}
static double Norm(tdouble3 a){return sqrt(a.x*a.x+a.y*a.y+a.z*a.z);}
static tdouble3 Abs(tdouble3 a){return TDouble3(fabs(a.x),fabs(a.y),fabs(a.z));}
static double RoundoffGamma(unsigned long long n,double u){const double nu=double(n)*u;Need(nu<1,"Roundoff operation count outside gamma domain");return nu/(1.-nu);}
static void Vec(std::ostream& f,tdouble3 a){f<<','<<a.x<<','<<a.y<<','<<a.z;}
template<class T>struct Copy{
  T* p;std::vector<T> v;Copy(T* a,unsigned n):p(a){Need(a||!n,"Missing invariant array");if(n)v.assign(a,a+n);}
  bool Equal()const{return v.empty()||!memcmp(p,v.data(),v.size()*sizeof(T));}
};
struct RestoreModes{byte*& p;TpSlipMode& mode;byte* old;TpSlipMode oldmode;~RestoreModes(){p=old;mode=oldmode;}};
using Physical=std::array<double,18>;
struct Node{
  unsigned id=0,slot=0,ff=0,fb=0;double mass=0,gamma=0;
  tdouble3 a=TDouble3(0),s=TDouble3(0),b=TDouble3(0),d=TDouble3(0);
};
struct WallPair{unsigned i,j;bool left;double vv;tdouble3 g;};
struct Oracle{
  std::vector<Node> nodes;std::vector<WallPair> walls;
  tdouble3 fluid=TDouble3(0),left=TDouble3(0),right=TDouble3(0);
  unsigned long long pairs=0,doubleops=0;unsigned maxpairs=0;
  double pairabs=0,weightedlocal=0,doublebound=0,covered=0,global=0,maxlocal=0,maxreference=0;
};
class Force:public JSphCpuSingle{
  std::vector<unsigned> Soil,Bound;unsigned Calls=0,ReceiverRows=0,GhostRows=0;
  double MaxLocalRatio=0,MaxGlobalRatio=0,MaxCoverage=0;
  std::vector<unsigned> Map()const{
    std::vector<unsigned> m(CaseNp,UINT_MAX);unsigned nf=0,nb=0;
    for(unsigned p=0;p<Np;p++){
      Need(Idpc[p]<CaseNp&&(CODE_IsNormal(Codec[p])||CODE_IsPeriodic(Codec[p]))&&(CODE_IsFluid(Codec[p])||CODE_IsFixed(Codec[p])),"Unexpected slot/code/ID");
      if(CODE_IsNormal(Codec[p])){Need(m[Idpc[p]]==UINT_MAX,"Duplicate native ID");m[Idpc[p]]=p;CODE_IsFluid(Codec[p])?nf++:nb++;}
    }
    Need(nf==SoilCount&&nb==WallCount&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Native/exclusion mismatch");return m;
  }
  bool NS(unsigned p)const{const auto mode=(BoundSlipModec?TpSlipMode(BoundSlipModec[p]):SlipMode);Need(mode==SLIP_NoSlip||mode==SLIP_FreeSlip,"Unexpected private slip selector");return mode==SLIP_NoSlip;}
  void NoStep()const{Need(TimeStep==0&&Nstep==0&&!PoroJPrec,"Force component advanced time or retained predictor J");}
  void Fields(double shear){
    for(unsigned p=0;p<Np;p++){
      Velrhopc[p]=TFloat4(0,0,0,RhopZero);PoroJc[p]=1.;PoroThetac[p]=0.;PorePressc[p]=PorePress0c[p]=PorePressRatec[p]=0;
      Sigmac[p]={0,0,(CODE_IsFluid(Codec[p])?shear:0.),0,0,0};Kplasticc[p]=0;CorrMatc[p]=TMatrix3d(0);TangenVelc[p]=TFloat3(0);
    }
  }
  std::vector<Physical> Snapshot()const{
    const auto m=Map();std::vector<Physical> v;v.reserve(SoilCount);
    for(unsigned id:Soil){const unsigned p=m[id];const auto x=Posc[p];const auto u=Velrhopc[p];const auto s=Sigmac[p];
      v.push_back({x.x,x.y,x.z,u.x,u.y,u.z,u.w,PorePressc[p],PorePress0c[p],PoroJc[p],PoroThetac[p],s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,Kplasticc[p]});for(double a:v.back())Need(std::isfinite(a),"Nonfinite physical field");}
    return v;
  }
  void State(unsigned p,double& volume,double& rho)const{
    double n;GetPorosityFeedbackStateCpu(p,n,volume,rho);
    Need(PoroJc[p]==1.&&n==double(SoilCte.Porosity)&&volume==double(MassFluid)/RhopZero&&rho==RhopZero&&volume*rho==double(MassFluid),"Current physical mass/J ledger differs from declared dyadic fixture");
    const double B=double(SoilCte.PoreWaterBulkModulus)/n,M=double(SoilCte.ModulusK)+4.*SoilCte.ModulusG/3.;
    Need(n>0&&n<1&&rho*B/(M+B)-SoilCte.PoreWaterRho>64*DBL_EPSILON*(std::max)(rho,double(SoilCte.PoreWaterRho)),"Outside retained saturated positive-k natural domain");
  }
  Oracle Preflight()const{
    Oracle o;const auto m=Map();
    for(unsigned id:Soil){Node r;r.id=id;r.slot=m[id];double vi,rhoi;State(r.slot,vi,rhoi);r.mass=rhoi*vi;
      for(unsigned q=0;q<Np;q++){
        const bool bound=q<Npb;Need(bound==bool(CODE_IsFixed(Codec[q])),"Actual fixed prefix mismatch");
        const float dx=float(Posc[r.slot].x-Posc[q].x),dy=float(Posc[r.slot].y-Posc[q].y),dz=float(Posc[r.slot].z-Posc[q].z),rr=dx*dx+dy*dy+dz*dz;
        if(rr<ALMOSTZERO||rr>KernelSize2)continue;
        if(bound)Need(BoundModec[q]!=BMODE_MDBC2OFF,"Preflight cannot bypass a pre-existing inactive wall; initial DBC is allowed until real closure");
        double vj,rhoj;State(q,vj,rhoj);const float fac=(TKernel==KERNEL_Cubic?fsph::GetKernel_Fac<KERNEL_Cubic>(CSP,rr):fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,rr));
        const auto g=TDouble3(float(fac*dx),float(fac*dy),float(fac*dz));const double shear=Tau+(bound?(NS(q)?Tau:-Tau):Tau),coeff=vj/rhoi;
        const auto a=TDouble3(coeff*shear*g.z,0,coeff*shear*g.x),f=a*r.mass;
        Need(std::isfinite(Norm(a))&&double(float(a.x))==a.x&&double(float(a.z))==a.z,"Preflight pair scaling is not the declared exact dyadic float conversion");
        r.a=r.a+a;r.s=r.s+Abs(a);bound?r.fb++:r.ff++;o.pairs++;o.pairabs+=Norm(f);
        if(bound){const bool left=BoundNormalc[q].x>0;Need(BoundNormalc[q].x!=0,"Wall face missing");o.walls.push_back({r.slot,q,left,vi*vj,g});if(left)o.left=o.left-f;else o.right=o.right-f;}
      }
      Need(r.ff>0,"Empty independent native support");r.gamma=RoundoffGamma(r.ff+r.fb+3,FLT_EPSILON);r.d=TDouble3(4096*DBL_EPSILON*(std::max)(1.,r.s.x),4096*DBL_EPSILON*(std::max)(1.,r.s.y),4096*DBL_EPSILON*(std::max)(1.,r.s.z));r.b=r.s*r.gamma+r.d;
      o.maxpairs=(std::max)(o.maxpairs,r.ff+r.fb);o.maxlocal=(std::max)(o.maxlocal,Norm(r.b));o.maxreference=(std::max)(o.maxreference,Norm(r.a));o.weightedlocal+=r.mass*Norm(r.b);o.fluid=o.fluid+r.a*r.mass;o.nodes.push_back(r);
    }
    o.doubleops=24*o.pairs+16*SoilCount+64; // All independent force/norm/fold operations plus native resultant fold, conservatively counted.
    o.doublebound=RoundoffGamma(o.doubleops,DBL_EPSILON)*(std::max)(1.,2*o.pairabs+Norm(o.fluid)+Norm(o.left)+Norm(o.right));
    o.covered=o.weightedlocal+o.doublebound;o.global=128*FLT_EPSILON*o.pairabs+4096*DBL_EPSILON*(std::max)(1.,o.pairabs);
    return o;
  }
  void WritePreflight(const fs::path& out,const char* name,const Oracle& o,unsigned mode)const{
    std::ofstream f(out/(std::string(name)+"_preflight.csv"));f<<std::setprecision(17)<<"native_id,slot,nFF,nFB,float_path_operations,current_mass,gamma_n,reference_ax,reference_ay,reference_az,absolute_ax_terms,absolute_ay_terms,absolute_az_terms,budget_ax,budget_ay,budget_az\n";
    for(const auto& r:o.nodes){f<<r.id<<','<<r.slot<<','<<r.ff<<','<<r.fb<<','<<r.ff+r.fb+3<<','<<r.mass<<','<<r.gamma;Vec(f,r.a);Vec(f,r.s);Vec(f,r.b);f<<'\n';}
    f.flush();Need(bool(f),"Pre-force node budget CSV write failed");std::ofstream j(out/(std::string(name)+"_preflight.json"));j<<std::setprecision(17)<<"{\"fixed_before_force\":true,\"pairs\":"<<o.pairs<<",\"max_nFF_plus_nFB\":"<<o.maxpairs<<",\"double_operation_bound\":"<<o.doubleops<<",\"pairabs_N\":"<<o.pairabs<<",\"weighted_local_error_bound_N\":"<<o.weightedlocal<<",\"double_error_bound_N\":"<<o.doublebound<<",\"covered_global_error_N\":"<<o.covered<<",\"unchanged_global_budget_N\":"<<o.global<<",\"coverage_ratio\":"<<o.covered/o.global<<",\"actual_force_called_yet\":false,\"physical_acceptance\":false}\n";j.flush();Need(bool(j),"Pre-force global budget write failed");
    Need(o.global>0&&o.covered<=o.global,"Measured operation bound does not fit unchanged global128FLT+4096DBL budget; reject before force");
    Need(Norm(o.fluid+o.left+o.right)<=o.doublebound,"Independent pair accounting/periodic ownership fails before force");
    if(mode==1)for(const auto& r:o.nodes)Need(fabs(r.a.x)<=r.d.x&&fabs(r.a.y)<=r.d.y&&fabs(r.a.z)<=r.d.z,"All-NS regular raw stencil is not constant-stress balanced before force");
    if(mode==0)Need(o.maxreference>o.maxlocal&&Norm(o.left)+Norm(o.right)<=o.doublebound&&Norm(o.fluid)<=o.doublebound,"FS release/symmetric reference witness empty");
    if(mode==1)Need(o.left.z>o.global&&o.right.z<-o.global&&Norm(o.left+o.right)<=o.doublebound,"Two NS reactions are not nonzero/opposed");
    if(mode==2)Need(o.left.z>o.global&&Norm(o.right)<=o.doublebound&&o.fluid.z<-o.global,"Mixed single-NS reaction/resultant witness empty");
  }
  void Case(const fs::path& out,const char* name,unsigned mode,std::ostream& summary){
    Fields(Tau);const auto before=Snapshot();const Copy<tdouble3> pos(Posc,Np);const Copy<unsigned> ids(Idpc,Np),cells(Dcellc,Np);const Copy<typecode> code(Codec,Np);const Copy<tfloat3> normal(BoundNormalc,Np);const Copy<byte> selectors(BoundSlipModec,BoundSlipModec?Np:0);
    const auto o=Preflight();WritePreflight(out,name,o,mode);MaxCoverage=(std::max)(MaxCoverage,o.covered/o.global);
    try{
      Calls++;Interaction_Forces(INTERSTEP_SymPredictor);NoStep();const auto after=Snapshot();Need(!memcmp(before.data(),after.data(),SoilCount*sizeof(Physical))&&pos.Equal()&&ids.Equal()&&cells.Equal()&&code.Equal()&&normal.Equal()&&selectors.Equal(),"Actual force changed persistent native fields/IDs/geometry/selectors");
      std::ofstream ghosts(out/(std::string(name)+"_ghosts.csv"));ghosts<<std::setprecision(17)<<"slot,native_id,noslip,wall_x,actual_double_sigma_xz,momentum_float_sigma_xz,expected_float_sigma_xz\n";
      for(unsigned p=0;p<Np;p++){
        double v,rho;State(p,v,rho);const auto s=ToTSymMatrix3f(Sigmac[p]);const float expected=float(p<Npb?(NS(p)?Tau:-Tau):Tau);
        Need(s.xx==0&&s.xy==0&&s.xz==expected&&s.yy==0&&s.yz==0&&s.zz==0,"Actual ghost/native momentum float sigma policy differs from independent prescribed oracle");
        Need(std::isfinite(Norm(ToTDouble3(Acec[p])))&&std::isfinite(Arc[p])&&std::isfinite(PorePressRatec[p]),"Nonfinite actual force/Darcy buffer");
        const auto rs=Rsigmac[p];Need(std::isfinite(rs.xx)&&std::isfinite(rs.xy)&&std::isfinite(rs.xz)&&std::isfinite(rs.yy)&&std::isfinite(rs.yz)&&std::isfinite(rs.zz),"Nonfinite stress-rate buffer");
        Need(Velrhopc[p].w>=RhopOutMin&&Velrhopc[p].w<=RhopOutMax,"Legacy rho left retained safety limits");
        if(p<Npb){Need(Velrhopc[p].x==0&&Velrhopc[p].y==0&&Velrhopc[p].z==0&&Velrhopc[p].w==RhopZero&&BoundModec[p]==BMODE_MDBC2,"Fixed marker physical state changed");ghosts<<p<<','<<Idpc[p]<<','<<NS(p)<<','<<Posc[p].x<<','<<Sigmac[p].xz<<','<<s.xz<<','<<expected<<'\n';GhostRows++;}
      }
      tdouble3 left=TDouble3(0),right=TDouble3(0),fluid=TDouble3(0); // Independent pair reaction from actual ghost inputs; NEVER fixed Ace.
      for(const auto& p:o.walls){const double shear=double(float(Sigmac[p.i].xz))+float(Sigmac[p.j].xz);const auto f=TDouble3(p.vv*shear*p.g.z,0,p.vv*shear*p.g.x);if(p.left)left=left-f;else right=right-f;}
      Need(Norm(left-o.left)<=o.global&&Norm(right-o.right)<=o.global,"Actual ghost-input pair reactions disagree with prescribed oracle");
      std::ofstream rows(out/(std::string(name)+"_force.csv"));rows<<std::setprecision(17)<<"native_id,slot,current_mass,actual_ax,actual_ay,actual_az,error_ax,error_ay,error_az,max_component_error_over_preflight_budget\n";double localmax=0,maxace=0;
      for(const auto& r:o.nodes){const auto a=ToTDouble3(Acec[r.slot]),e=Abs(a-r.a);Need(e.x<=r.b.x&&e.y<=r.b.y&&e.z<=r.b.z,"Actual native Ace exceeds fixed componentwise gamma_n budget");
        if(mode==1)Need(fabs(a.x)<=r.b.x+r.d.x&&fabs(a.y)<=r.b.y+r.d.y&&fabs(a.z)<=r.b.z+r.d.z,"All-NS local zero exceeds triangle bound after preflight null witness");
        const double ratio=(std::max)({e.x/r.b.x,e.y/r.b.y,e.z/r.b.z});localmax=(std::max)(localmax,ratio);maxace=(std::max)(maxace,Norm(a));fluid=fluid+a*r.mass;rows<<r.id<<','<<r.slot<<','<<r.mass;Vec(rows,a);Vec(rows,e);rows<<','<<ratio<<'\n';ReceiverRows++;
      }
      const double closure=Norm(fluid+left+right),difference=Norm(fluid-o.fluid);Need(closure<=o.global&&difference<=o.global,"Actual native resultant and independent wall reaction exceed retained global force budget");
      if(mode<2)Need(Norm(fluid)<=o.global,"Symmetric native fluid resultant is not balanced");
      if(mode==0)Need(maxace>o.maxlocal&&Norm(left)+Norm(right)<=o.global,"FS release vanished or acquired a nonzero shear reaction");
      if(mode==1)Need(left.z>o.global&&right.z<-o.global&&Norm(left+right)<=o.global,"NS reaction signs/opposition failed");
      if(mode==2)Need(left.z>o.global&&Norm(right)<=o.global&&fluid.z<-o.global,"Mixed nonzero fluid resultant/single NS reaction failed");
      Need(std::isfinite(AceMax)&&AceMax>=0&&std::isfinite(VelMax)&&VelMax==0&&std::isfinite(ViscDtMax)&&ViscDtMax>=0,"Actual force maxima not defined/finite");
      MaxLocalRatio=(std::max)(MaxLocalRatio,localmax);MaxGlobalRatio=(std::max)(MaxGlobalRatio,(std::max)(closure,difference)/o.global);
      summary<<name<<','<<o.pairs<<','<<o.maxpairs<<','<<o.pairabs<<','<<o.global<<','<<o.covered<<','<<localmax<<','<<closure<<','<<difference<<','<<maxace;Vec(summary,fluid);Vec(summary,o.fluid);Vec(summary,left);Vec(summary,right);Vec(summary,o.left);Vec(summary,o.right);summary<<','<<left.z/(Tau*Lz)<<','<<right.z/(Tau*Lz)<<'\n';
      rows.flush();ghosts.flush();summary.flush();Need(rows&&ghosts&&summary,"Force diagnostics write failed");PosInteraction_Forces();
    }catch(...){if(Acec)PosInteraction_Forces();throw;}
    NoStep();
  }
public:
  Force(){PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Need(HydroMech&&!HydroMechDynamicSeepage&&Simulate2D&&(TKernel==KERNEL_Cubic||TKernel==KERNEL_Wendland)&&TStep==STEP_Symplectic&&CaseNp==SoilCount+WallCount&&CaseNfluid==SoilCount&&CaseNpb==WallCount&&TBoundary==BC_MDBC&&SlipMode==SLIP_FreeSlip&&MdbcCorrector&&!PeriX&&!PeriY&&PeriZ,"Wrong real retained CPU1280 fixture");
    Need(!Gravity.x&&!Gravity.y&&!Gravity.z&&!Symmetry&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!DynamicPoreConductivity&&!ArtificialStress&&TDensity==DDT_None&&TVisco==VISCO_Artificial&&!SoilDamping,"Unmodelled gravity/load/diffusion/viscosity source");
    Need(!CaseNmoving&&!CaseNfloat&&!HourglassCpu&&!Shifting&&!Damping&&!RelaxZones&&!InOut&&!AccInput&&!NoPenetration&&!SoilBoundaryDerivativeSPR,"Auxiliary force source outside scope");
    Need(Dp==Dp0&&KernelH==float(1.8*Dp0)&&RhopZero==2048&&MassFluid==float(1./128.)&&MassBound==MassFluid&&SoilCte.PoreWaterRho==1000&&SoilCte.Porosity==.25f&&SoilCte.HydraulicConductivity==float(.0001)&&MapRealSize.z==Lz&&MapRealPosMin.x==-4*Dp0&&MapRealPosMax.x==Width+4*Dp0,"Retained geometry/dyadic mass/material changed");
    const auto map=Map();unsigned left=0,right=0;std::vector<bool> lattice(SoilCount,false);
    for(unsigned id=0;id<CaseNp;id++){const unsigned p=map[id];if(CODE_IsFluid(Codec[p])){Soil.push_back(id);const auto x=Posc[p];const double ix=x.x/Dp0-.5,iz=x.z/Dp0-.5;Need(x.y==0&&ix==round(ix)&&iz==round(iz)&&ix>=0&&ix<32&&iz>=0&&iz<32,"Retained lattice changed");const unsigned key=unsigned(ix)+32*unsigned(iz);Need(!lattice[key],"Duplicate native coordinate");lattice[key]=true;}else{Bound.push_back(id);const auto n=BoundNormalc[p];const double plane=Posc[p].x+.5*n.x;Need(n.y==0&&n.z==0&&((n.x>0&&plane==0)||(n.x<0&&plane==Width)),"True wall plane invalid");n.x>0?left++:right++;}}
    Need(left==128&&right==128,"Parallel native wall faces changed");NoStep();Fields(0);const auto initial=Snapshot();byte* const owned=BoundSlipModec;const auto oldmode=SlipMode;
    std::ofstream summary(fs::path(cfg->DirOut)/"summary.csv");summary<<std::setprecision(17)<<"case,pairs,max_neighbors,pairabs_N,retained_global_budget_N,covered_operation_bound_N,max_local_ratio,closure_N,resultant_error_N,max_actual_Ace,actual_Fx,actual_Fy,actual_Fz,reference_Fx,reference_Fy,reference_Fz,derived_left_Rx,derived_left_Ry,derived_left_Rz,derived_right_Rx,derived_right_Ry,derived_right_Rz,reference_left_Rx,reference_left_Ry,reference_left_Rz,reference_right_Rx,reference_right_Ry,reference_right_Rz,left_Rz_over_tauLz,right_Rz_over_tauLz\n";
    {std::vector<byte> local(Np,byte(SLIP_FreeSlip));RestoreModes restore{BoundSlipModec,SlipMode,owned,oldmode};BoundSlipModec=nullptr;SlipMode=SLIP_FreeSlip;InitDynamicPoreWallCpu();for(unsigned p=0;p<Npb;p++)local[p]=byte(BoundNormalc[p].x>0?SLIP_NoSlip:SLIP_FreeSlip);
      for(unsigned mode=0;mode<3;mode++){SlipMode=(mode==1?SLIP_NoSlip:SLIP_FreeSlip);BoundSlipModec=(mode==2?local.data():nullptr);Case(cfg->DirOut,mode==0?"FS":mode==1?"NS":"mixed",mode,summary);}}
    Need(BoundSlipModec==owned&&SlipMode==oldmode,"Borrowed mode pointer not restored");Fields(0);const auto final=Snapshot();Need(!memcmp(initial.data(),final.data(),SoilCount*sizeof(Physical))&&Calls==3&&ReceiverRows==3*SoilCount&&GhostRows==3*Npb,"Incomplete force cases or physical reset");NoStep();
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_noslip_cpu_force_r2\",\"passed\":true,\"kernel\":\""<<(TKernel==KERNEL_Cubic?"Cubic":"Wendland")<<"\",\"actual_force_calls\":"<<Calls<<",\"native_receiver_rows\":"<<ReceiverRows<<",\"fixed_slot_sigma_checks\":"<<GhostRows<<",\"max_component_error_over_predeclared_budget\":"<<MaxLocalRatio<<",\"max_global_error_over_retained_budget\":"<<MaxGlobalRatio<<",\"max_preflight_coverage_ratio\":"<<MaxCoverage<<",\"current_physical_native_mass\":true,\"preflight_fixed_before_each_force\":true,\"fixed_Ace_not_used_as_reaction\":true,\"reaction_derived_from_actual_ghost_pair_inputs\":true,\"borrowed_modes_and_native_physical_fields_restored\":true,\"actual_Run_or_ComputeStep_called\":false,\"completed_physical_steps\":0,\"actual_time_s\":0,\"NoSlip_physical_admission\":false,\"SH_reflection_or_energy_tested\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=6&&std::string(argv[1])=="--force","Use --force -cpu -ompthreads:1 -stable -mdbc_freeslip GENUINE_W_OR_C_SEED FRESH");AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=2;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());
  Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!fs::exists(cfg.DirOut),"Only fresh private CPU force component admitted");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Force force;force.Execute(&cfg,AppInfo.LogPtr());return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"NoSlip force component failed; preserve all preflight/force evidence\n";return 2;}}

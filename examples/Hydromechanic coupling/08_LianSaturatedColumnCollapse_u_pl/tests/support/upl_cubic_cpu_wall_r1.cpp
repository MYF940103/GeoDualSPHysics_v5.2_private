// Zero-step extraction of the retained upl_p3_wall_wave_harness_r2 Component/init.
// Cubic dispatch at retained h/dp=1.8; no wave reference, force audit or integrator.
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
JAppInfo AppInfo("CubicCpuWallComponent","r1","06-11-2026");
namespace fs=std::filesystem;
static void Need(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
static constexpr unsigned Native=1024,Fixed=256;
static constexpr double Dp0=1./512.,Width=1./16.,Lz=1./16.;
using Row=std::array<double,26>;
template<class T>struct Copy{
  T* p;std::vector<T> v;
  Copy(T* a,unsigned n):p(a){Need(a||!n,"Missing component array");if(n)v.assign(a,a+n);}
  void Restore()const{if(!v.empty())memcpy(p,v.data(),sizeof(T)*v.size());}
  bool Equal()const{return v.empty()||!memcmp(p,v.data(),sizeof(T)*v.size());}
};
class Wall:public JSphCpuSingle{
  std::vector<unsigned> Soil,Bound;
  unsigned Cases=0,Rows=0,Noncoincident=0;
  double MaxRatio=0;
  static double Norm(tdouble3 a){return sqrt(a.x*a.x+a.y*a.y+a.z*a.z);}
  std::vector<unsigned> Map()const{
    std::vector<unsigned> m(CaseNp,UINT_MAX);unsigned soil=0,bound=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){
      Need(Idpc[p]<CaseNp&&m[Idpc[p]]==UINT_MAX,"Duplicate/unknown native ID");m[Idpc[p]]=p;
      if(CODE_IsFluid(Codec[p]))soil++;else{Need(CODE_IsFixed(Codec[p]),"Nonfixed boundary");bound++;}
    }
    Need(soil==Native&&bound==Fixed&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Native/exclusion mismatch");return m;
  }
  void NoStep()const{Need(TimeStep==0&&Nstep==0&&!PoroJPrec,"Component advanced time or retained a predictor J");}
  void Reset(){
    for(unsigned p=0;p<Np;p++){
      const bool fluid=CODE_IsFluid(Codec[p]);
      Velrhopc[p]=TFloat4(fluid?float(Dp0*sin(2*acos(-1.)*Posc[p].x/(2*Width))):0.f,0,0,RhopZero);
      PorePressc[p]=PorePress0c[p]=PorePressRatec[p]=0;Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;PoroJc[p]=1;PoroThetac[p]=0;CorrMatc[p]=TMatrix3d(0);
      if(TangenVelc)TangenVelc[p]=TFloat3(0);
    }
  }
  std::vector<Row> Snapshot()const{
    const auto m=Map();std::vector<Row> out;out.reserve(Native);
    for(unsigned id:Soil){const unsigned p=m[id];const auto x=Posc[p];const auto v=Velrhopc[p];const auto s=Sigmac[p];const auto n=FSNormalc[p];const auto l=HydroMechLoadAcec[p];
      out.push_back({x.x,x.y,x.z,v.x,v.y,v.z,PorePressc[p],PorePress0c[p],PoroJc[p],PoroThetac[p],s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,Kplasticc[p],double(FSTypec[p]),n.x,n.y,n.z,PosDivc[p],l.x,l.y,l.z,v.w});
      for(double z:out.back())Need(std::isfinite(z),"Nonfinite native field");
    }return out;
  }
  double Condition(tdouble3 at)const{
    tmatrix3d mom=TMatrix3d(0);
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsFluid(Codec[p])){
      const auto d=Posc[p]-at;const double rr=d.x*d.x+d.z*d.z;if(rr>double(KernelSize2))continue;
      // Only W is needed for this independent condition estimate. Wab is safe at rr=0.
      const double wab=fsph::GetKernel_Wab<KERNEL_Cubic>(CSP,float(rr));if(wab<=0)continue;
      const double w=double(MassFluid)/RhopZero*PoroJc[p]*wab,x=d.x/KernelH,z=d.z/KernelH;
      mom.a11+=w;mom.a12+=w*x;mom.a13+=w*z;mom.a21+=w*x;mom.a22+=w*x*x;mom.a23+=w*x*z;mom.a31+=w*z;mom.a32+=w*x*z;mom.a33+=w*z*z;
    }
    const double det=fmath::Determinant3x3(mom);Need(det>0,"Independent component support singular");const auto inv=fmath::InverseMatrix3x3(mom,det);
    const auto inf=[](const tmatrix3d& a){return (std::max)({fabs(a.a11)+fabs(a.a12)+fabs(a.a13),fabs(a.a21)+fabs(a.a22)+fabs(a.a23),fabs(a.a31)+fabs(a.a32)+fabs(a.a33)});};
    return (std::max)(1.,inf(mom)*inf(inv));
  }
  void Component(const fs::path& out,bool offgrid){
    InitDynamicPoreWallCpu();const auto m=Map();
    const Copy<tdouble3> positions(Posc,Np);const Copy<unsigned> ids(Idpc,Np);const Copy<typecode> codes(Codec,Np);const Copy<tfloat3> normals(BoundNormalc,Np);
    const Copy<tfloat4> originalvel(Velrhopc,Np);const Copy<tsymatrix3d> originalstress(Sigmac,Np);const Copy<tmatrix3d> originalc(CorrMatc,Np);
    const Copy<double> originalj(PoroJc,Np),originaltheta(PoroThetac,Np);const Copy<float> originalp(PorePressc,Np),originalp0(PorePress0c,Np),originalplastic(Kplasticc,Np);
    const Copy<tfloat3> originaltangent(TangenVelc,Np);const Copy<byte> originalmode(BoundModec,Np);
    if(offgrid)for(unsigned p=0;p<Npb;p++)BoundNormalc[p].x+=float((BoundNormalc[p].x>0?1.:-1.)*Dp0/8.);
    for(unsigned p=0;p<Np;p++)if(CODE_IsFluid(Codec[p])){const double x=Posc[p].x;
      Velrhopc[p]=TFloat4(float(.125+.5*x),0,float(-.25+.125*x),RhopZero);PoroJc[p]=1.+x/1024.;PoroThetac[p]=0;
      PorePressc[p]=float(128.+256*x);PorePress0c[p]=0;Sigmac[p]={16.+x,0,8.+32*x,32.+2*x,0,64.+4*x};Kplasticc[p]=0;
    }
    InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();
    for(unsigned p=0;p<Np;p++){
      Acec[p]=BoundDerivativeVelc[p]=TFloat3(0);
      if(CODE_IsFluid(Codec[p])){const double x=Posc[p].x;Acec[p]=TFloat3(float(.25+.5*x),0,float(-.125+.25*x));CorrMatc[p]={1.+x,0,.125+.5*x,0,0,0,.125+.5*x,0,2.+x};}
    }
    const auto before=Snapshot();std::vector<tmatrix3d> nativec;std::vector<tfloat3> nativeace;
    for(unsigned id:Soil){nativec.push_back(CorrMatc[m[id]]);nativeace.push_back(Acec[m[id]]);}
    ComputeDynamicPoreWallStateCpu();ComputeDynamicPoreWallMatrixCpu();ComputeDynamicPoreWallAccelerationCpu();
    const auto after=Snapshot();Need(!memcmp(before.data(),after.data(),Native*sizeof(Row)),"Wall stages modified native physical26 fields");
    for(unsigned row=0;row<Native;row++){const unsigned p=m[Soil[row]];Need(!memcmp(CorrMatc+p,nativec.data()+row,sizeof(tmatrix3d))&&!memcmp(Acec+p,nativeace.data()+row,sizeof(tfloat3)),"Wall stages modified native C/Ace");}
    std::ofstream csv(out/(offgrid?"offgrid_component.csv":"component.csv"));csv<<std::setprecision(17)<<"id,target_x,J_error,p_error,v_error,sigma_error,C_error,ace_error,condition,double_base_tol,float_base_tol,nearest_distance_m\n";
    unsigned nonzero=0;
    for(unsigned id:Bound){const unsigned p=m[id];const auto target=Posc[p]+ToTDouble3(BoundNormalc[p]);const double x=target.x;double closest=DBL_MAX;
      for(unsigned q=Npb;q<Np;q++)if(CODE_IsFluid(Codec[q])){const auto d=Posc[q]-target;closest=(std::min)(closest,d.x*d.x+d.z*d.z);}
      Need(closest==(offgrid?Dp0*Dp0/64.:0.),"Declared coincident/Dp-over-8 target not exercised");
      const auto vm=TFloat3(float(-(.125+.5*x)),0,float(-.25+.125*x)),am=TFloat3(float(-(.25+.5*x)),0,float(-.125+.25*x));
      const tsymatrix3d s={16.+x,0,-(8.+32*x),32.+2*x,0,64.+4*x};const tmatrix3d c={1.+x,0,-(.125+.5*x),0,0,0,-(.125+.5*x),0,2.+x};
      const double ej=fabs(PoroJc[p]-(1.+x/1024.)),ep=fabs(PorePressc[p]-float(128.+256*x)),ev=Norm(ToTDouble3(BoundDerivativeVelc[p])-ToTDouble3(vm)),ea=Norm(ToTDouble3(Acec[p])-ToTDouble3(am));
      const auto sc=Sigmac[p];const auto cc=CorrMatc[p];
      const double es=(std::max)({fabs(sc.xx-s.xx),fabs(sc.xy-s.xy),fabs(sc.xz-s.xz),fabs(sc.yy-s.yy),fabs(sc.yz-s.yz),fabs(sc.zz-s.zz)});
      const double ec=(std::max)({fabs(cc.a11-c.a11),fabs(cc.a12-c.a12),fabs(cc.a13-c.a13),fabs(cc.a21-c.a21),fabs(cc.a22-c.a22),fabs(cc.a23-c.a23),fabs(cc.a31-c.a31),fabs(cc.a32-c.a32),fabs(cc.a33-c.a33)});
      const double condition=Condition(target),td=32768*DBL_EPSILON*condition,tf=64*FLT_EPSILON*condition;
      Need(ej<=td*2&&ep<=tf*256&&ev<=tf&&ea<=tf&&es<=td*128&&ec<=td*4,"Original affine wall-closure budget failed");
      Need(Velrhopc[p].x==0&&Velrhopc[p].y==0&&Velrhopc[p].z==0&&Velrhopc[p].w==RhopZero,"Physical fixed velocity changed");
      Need(BoundModec[p]==BMODE_MDBC2&&TangenVelc[p].x==0&&TangenVelc[p].y==0&&fabs(TangenVelc[p].z-vm.z)<=tf,"Wall tangent/mDBC mode mismatch");
      nonzero+=unsigned(BoundDerivativeVelc[p].x!=0&&Acec[p].x!=0&&CorrMatc[p].a13!=0&&PoroJc[p]!=1.);
      MaxRatio=(std::max)({MaxRatio,ej/(2*td),ep/(256*tf),ev/tf,ea/tf,es/(128*td),ec/(4*td)});
      csv<<id<<','<<x<<','<<ej<<','<<ep<<','<<ev<<','<<es<<','<<ec<<','<<ea<<','<<condition<<','<<td<<','<<tf<<','<<sqrt(closest)<<'\n';Rows++;
    }
    Need(nonzero==Fixed,"Affine wall witnesses vacuous");if(offgrid)Noncoincident+=nonzero;
    normals.Restore();Need(normals.Equal()&&positions.Equal()&&ids.Equal()&&codes.Equal(),"Geometry/IDs/normals changed");NoStep();PosInteraction_Forces();
    originalvel.Restore();originalstress.Restore();originalc.Restore();originalj.Restore();originaltheta.Restore();originalp.Restore();originalp0.Restore();originalplastic.Restore();originaltangent.Restore();originalmode.Restore();
    Need(originalvel.Equal()&&originalstress.Equal()&&originalc.Equal()&&originalj.Equal()&&originaltheta.Equal()&&originalp.Equal()&&originalp0.Equal()&&originalplastic.Equal()&&originaltangent.Equal()&&originalmode.Equal(),"Component input restoration failed");
    csv.flush();Need(bool(csv),"Component CSV write failed");Cases++;
  }
public:
  Wall(){PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Need(HydroMech&&!HydroMechDynamicSeepage&&Simulate2D&&TKernel==KERNEL_Cubic&&TStep==STEP_Symplectic&&CaseNpb==Fixed&&CaseNfluid==Native&&CaseNp==Native+Fixed&&TBoundary==BC_MDBC&&SlipMode==SLIP_FreeSlip&&MdbcCorrector&&!PeriX&&!PeriY&&PeriZ,"Wrong retained Cubic wall fixture/options");
    Need(!CaseNmoving&&!CaseNfloat&&!HourglassCpu&&!Shifting&&!Damping&&!RelaxZones&&!InOut&&!AccInput&&!NoPenetration&&!SoilBoundaryDerivativeSPR,"Auxiliary path outside component scope");
    Need(Dp==Dp0&&MapRealPosMin.x==-4*Dp0&&MapRealPosMax.x==Width+4*Dp0&&MapRealPosMin.z==0&&MapRealSize.z==Lz&&FixedDt&&TangenVelc&&BoundModec,"Wrong map/spacing/mDBC arrays");
    Need(SoilCte.ModulusK==89478488.f&&SoilCte.ModulusG==134217728.f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==67108864.f&&SoilCte.Porosity==.25f&&SoilCte.HydraulicConductivity==float(.0001)&&RhopZero==2048&&double(MassFluid)/RhopZero==Dp0*Dp0&&KernelH==float(1.8*Dp0),"Changed retained material/h-over-dp");
    NoStep();const auto m=Map();for(unsigned id=0;id<CaseNp;id++)if(CODE_IsFluid(Codec[m[id]]))Soil.push_back(id);else Bound.push_back(id);
    std::vector<bool> lattice(Native,false);unsigned left=0,right=0;
    std::ofstream soil(fs::path(cfg->DirOut)/"native_ids.csv"),bound(fs::path(cfg->DirOut)/"fixed_ids.csv");soil<<std::setprecision(17)<<"row,native_id,x0,y0,z0\n";bound<<std::setprecision(17)<<"row,native_id,x0,y0,z0,plane_x\n";
    for(unsigned row=0;row<Native;row++){const auto x=Posc[m[Soil[row]]];const double ix=x.x/Dp0-.5,iz=x.z/Dp0-.5;Need(ix==round(ix)&&iz==round(iz)&&ix>=0&&ix<32&&iz>=0&&iz<32&&x.y==0,"Wrong native lattice");const unsigned key=unsigned(ix)+32*unsigned(iz);Need(!lattice[key],"Duplicate soil coordinate");lattice[key]=true;soil<<row<<','<<Soil[row]<<','<<x.x<<','<<x.y<<','<<x.z<<'\n';}
    for(unsigned row=0;row<Fixed;row++){const unsigned p=m[Bound[row]];const auto n=BoundNormalc[p];const double xp=Posc[p].x+.5*n.x;Need(n.y==0&&n.z==0&&n.x!=0&&((n.x>0&&xp==0)||(n.x<0&&xp==Width)),"Wall plane/normal mismatch");n.x>0?left++:right++;bound<<row<<','<<Bound[row]<<','<<Posc[p].x<<','<<Posc[p].y<<','<<Posc[p].z<<','<<xp<<'\n';}
    Need(left==128&&right==128,"Missing parallel wall face");Reset();const auto initial=Snapshot();
    Component(cfg->DirOut,false);Component(cfg->DirOut,true);const auto final=Snapshot();
    Need(!memcmp(initial.data(),final.data(),Native*sizeof(Row))&&Cases==2&&Rows==512&&Noncoincident==256,"Initial physical state/counts not restored");NoStep();
    soil.flush();bound.flush();Need(soil&&bound,"ID CSV write failed");std::ofstream done(fs::path(cfg->DirOut)/"completion.json");
    done<<std::setprecision(17)<<"{\"stage\":\"upl_cubic_cpu_wall_r1\",\"passed\":true,\"kernel\":\"Cubic\",\"h_over_dp\":1.8,\"native_soil\":1024,\"native_fixed\":256,\"actual_slots\":"<<Np<<",\"actual_fixed_prefix\":"<<Npb<<",\"component_cases\":"<<Cases<<",\"native_wall_rows\":"<<Rows<<",\"noncoincident_rows\":"<<Noncoincident<<",\"explicit_each_wall_stage_calls\":2,\"max_error_over_original_budget\":"<<MaxRatio<<",\"all_native_physical26_and_C_Ace_unchanged_by_wall_stages\":true,\"all_geometry_ID_normal_bytes_restored\":true,\"initial_native_physical26_restored\":true,\"actual_CPU_initialization\":true,\"actual_Interaction_Forces_called\":false,\"actual_ComputeStep_Sym_called\":false,\"actual_Run_called\":false,\"completed_physical_steps\":0,\"actual_time_s\":0,\"physical_acceptance\":false}\n";
    done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=6&&std::string(argv[1])=="--wall","Use --wall -cpu -ompthreads:1 -stable -mdbc_freeslip SEED FRESH");
  AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=2;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());
  Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!fs::exists(cfg.DirOut),"Only fresh CPU zero-step component admitted");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Wall wall;wall.Execute(&cfg,AppInfo.LogPtr());return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Cubic wall component failed; preserve evidence\n";return 2;}}

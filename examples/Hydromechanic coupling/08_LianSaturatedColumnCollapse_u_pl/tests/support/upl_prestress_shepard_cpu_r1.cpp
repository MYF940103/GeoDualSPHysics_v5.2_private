// Zero-step CPU Shepard field component; no material, force, wall fit or integrator call.
#include "JSphCpuSingle.h"
#include "JArraysCpu.h"
#include "JDsTimersCpu.h"
#include "JDsDcellDef.h"
#include "JAppInfo.h"
#include "FunSphKernel.h"
#include <omp.h>
#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("PrestressShepardCpu","r1","06-11-2026");
namespace fs=std::filesystem;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static unsigned FloatBits(float a){unsigned b;static_assert(sizeof(a)==sizeof(b),"binary32 required");std::memcpy(&b,&a,4);return b;}

class Shepard:public JSphCpuSingle{
  static constexpr unsigned Count=81;
  struct Point{tdouble3 x;unsigned id,key;};
  struct Ref{double value,wrong,limit,wronglimit;};
  std::vector<unsigned> Cells;
  unsigned Rows=0,LegacyRows=0,ConstantBits=0,Projected=0,WeightWitnesses=0,MaskInner=0,MaskSurface=0;
  double MaxRatio=0,MaxWrongDifference=0;
  bool Surface(unsigned p)const{return IsFreeSurfaceParticle(p,Codec,FSTypec);}
  void NoStep()const{Need(TimeStep==0&&Nstep==0&&!PorePressPrec&&!PoroJPrec,"A physical stage/time was advanced");}
  std::vector<unsigned char> State(bool pressure)const{
    std::vector<unsigned char> bytes;
    const auto add=[&](const void* p,std::size_t n){const auto b=static_cast<const unsigned char*>(p);bytes.insert(bytes.end(),b,b+n);};
    add(Posc,Np*sizeof(*Posc));add(Velrhopc,Np*sizeof(*Velrhopc));add(Sigmac,Np*sizeof(*Sigmac));add(Kplasticc,Np*sizeof(*Kplasticc));
    add(PorePress0c,Np*sizeof(*PorePress0c));add(PoroJc,Np*sizeof(*PoroJc));add(PoroThetac,Np*sizeof(*PoroThetac));add(PorePressRatec,Np*sizeof(*PorePressRatec));
    add(Idpc,Np*sizeof(*Idpc));add(Codec,Np*sizeof(*Codec));add(Dcellc,Np*sizeof(*Dcellc));add(FSTypec,Np*sizeof(*FSTypec));add(FSNormalc,Np*sizeof(*FSNormalc));add(PosDivc,Np*sizeof(*PosDivc));add(CorrMatc,Np*sizeof(*CorrMatc));add(HydroMechLoadAcec,Np*sizeof(*HydroMechLoadAcec));
    if(pressure)add(PorePressc,Np*sizeof(*PorePressc));return bytes;
  }
  void CellTable(){
    const tuint3 nc=TUint3(5,1,5);const unsigned ncell=25,code=DCEL_GetCode(27,2,2);std::vector<Point> points;
    for(unsigned z=0;z<9;z++)for(unsigned x=0;x<9;x++){const tdouble3 a=TDouble3(x*Dp,0,z*Dp);const unsigned cx=unsigned(a.x/KernelSize),cz=unsigned(a.z/KernelSize);Need(cx<nc.x&&cz<nc.z,"Point outside cell table");points.push_back({a,x+9*z,cx+nc.x*cz});}
    // ID0 is a real fixed source/canary at the minimum-key corner, not a fitted physical wall.
    Need(points[0].id==0&&points[0].key==0,"Fixed corner must precede fluid cell groups");std::stable_sort(points.begin()+1,points.end(),[](const Point& a,const Point& b){return a.key<b.key;});
    Cells.assign(2*(ncell+1),0);
    for(unsigned group=0;group<2;group++){unsigned cursor=group?1:0;const unsigned end=group?Count:1;for(unsigned c=0;c<=ncell;c++){while(cursor<end&&points[cursor].key<c)cursor++;Cells[group*(ncell+1)+c]=cursor;}}
    DivData=MakeDivDataCpu(1,nc,TUint3(0),Cells.data(),KernelSize,code,TDouble3(0));
    for(unsigned p=0;p<Count;p++){const auto a=points[p];Posc[p]=a.x;Idpc[p]=a.id;Codec[p]=(p?CODE_TYPE_FLUID:CODE_TYPE_FIXED);Dcellc[p]=DCEL_Cell(code,a.key%nc.x,0,a.key/nc.x);}
  }
  void Field(unsigned field,bool dynamic){
    DynamicPorePressure=dynamic;PorosityFeedback=dynamic;HydroMechFreeSeepage=false;HydroMechDrainage=false;PoreShepardRegularization=true;
    for(unsigned p=0;p<Np;p++){
      const double j=.75+.25*(Idpc[p]%3);PoroJc[p]=j;PoroThetac[p]=(int(Idpc[p]%3)-1)/32.;
      const float rho=float(double(SoilCte.PoreWaterRho)+(double(RhopZero)-double(SoilCte.PoreWaterRho))/j);
      Velrhopc[p]=TFloat4(0,0,0,rho);Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;HydroMechLoadAcec[p]=TFloat3(0);
      PorePress0c[p]=float(62.5*(2.-Posc[p].z));const float q=(field==0?0.f:field==1?16.f:16.f*(int(Idpc[p]%3)-1));
      PorePressc[p]=PorePress0c[p]+q;PorePressRatec[p]=float(1024+Idpc[p]);
    }
    ComputeFreeSurfaceTracking();unsigned inner=0,surface=0;
    for(unsigned p=Npb;p<Np;p++){Surface(p)?surface++:inner++;}
    Need(inner>0&&surface>0,"Actual FS classification needs nonempty interior and surface");MaskInner=inner;MaskSurface=surface;
  }
  Ref Reference(unsigned i,bool dynamic)const{
    double den=0,num=0,absolute=0,oldDen=0,oldNum=0,oldAbs=0;
    // Independent all-slot support scan: self once, then fixed/fluid sources. No production walker/state helper.
    for(unsigned j=0;j<Np;j++){
      const auto d=Posc[i]-Posc[j];const float rr2=float(d.x*d.x+d.z*d.z);if(j!=i&&(rr2>KernelSize2||rr2<ALMOSTZERO))continue;
      const double w=double(fsph::GetKernel_Wab<KERNEL_Cubic>(CSP,j==i?0.f:rr2));
      const float mass=(j<Npb?MassBound:MassFluid);const double volume=(dynamic?(double(mass)/double(RhopZero))*PoroJc[j]:double(mass/Velrhopc[j].w));
      const double oldVolume=double(mass/Velrhopc[j].w),q=double(PorePressc[j])-double(PorePress0c[j]),a=w*volume,b=w*oldVolume;
      den+=a;num+=a*q;absolute+=fabs(a*q);oldDen+=b;oldNum+=b*q;oldAbs+=fabs(b*q);
    }
    Need(den>0&&oldDen>0,"Independent Shepard support is empty");
    const double p0=PorePress0c[i],value=p0+num/den,wrong=p0+oldNum/oldDen;
    const double gamma=(8.*Count+32.)*DBL_EPSILON/(1.-(8.*Count+32.)*DBL_EPSILON);
    const auto limit=[&](double x,double scale){const float f=float(x);const double ulp=(std::max)(fabs(double(std::nextafter(f,std::numeric_limits<float>::infinity()))-f),fabs(double(f)-std::nextafter(f,-std::numeric_limits<float>::infinity())));return .5*ulp+2*gamma*(fabs(p0)+scale);};
    return{value,wrong,limit(value,absolute/den),limit(wrong,oldAbs/oldDen)};
  }
  void One(const char* group,unsigned field,bool dynamic,bool free,bool enabled,std::ostream& out,std::ostream* legacy=nullptr){
    Field(field,dynamic);HydroMechFreeSeepage=free;if(free)ApplyPorePressureBoundaries();PoreShepardRegularization=enabled;
    const auto before=State(!enabled);const std::vector<float> pressure(PorePressc,PorePressc+Np);std::vector<Ref> refs;
    for(unsigned p=0;p<Np;p++)refs.push_back(Reference(p,dynamic));
    ShepardRegularizePorePressure();Need(before==State(!enabled),"Shepard changed protected native state");NoStep();
    for(unsigned p=0;p<Np;p++){
      const auto r=refs[p];const float rounded=float(r.value);const bool projected=enabled&&free&&p>=Npb&&Surface(p)&&rounded>0;
      const double expected=(!enabled||p<Npb?double(pressure[p]):projected?0.:r.value),limit=(!enabled||p<Npb||projected?0.:r.limit),error=fabs(double(PorePressc[p])-expected);
      Need(std::isfinite(PorePressc[p])&&error<=limit,"Actual Shepard differs from independent roundoff reference");
      if(limit>0)MaxRatio=(std::max)(MaxRatio,error/limit);
      if(p<Npb)Need(FloatBits(PorePressc[p])==FloatBits(pressure[p]),"Fixed source pressure changed");
      if(enabled&&dynamic&&field<2&&p>=Npb){Need(FloatBits(PorePressc[p])==FloatBits(pressure[p]),"Zero/constant excess or hydrostatic baseline changed bits");ConstantBits++;}
      if(enabled&&dynamic&&field==2&&!free&&p>=Npb){const double delta=fabs(r.value-r.wrong);MaxWrongDifference=(std::max)(MaxWrongDifference,delta);if(delta>r.limit+r.wronglimit)WeightWitnesses++;}
      if(projected){Need(FloatBits(PorePressc[p])==FloatBits(0.f),"Positive surface pressure was not projected");Projected++;}
      if(free&&p>=Npb&&Surface(p))Need(PorePressc[p]<=0,"Post-Shepard free surface became positive");
      out<<group<<','<<Idpc[p]<<','<<(p<Npb)<<','<<FSTypec[p]<<','<<MaskInner<<','<<MaskSurface<<','<<Posc[p].x<<','<<Posc[p].z<<','<<PoroJc[p]<<','<<Velrhopc[p].w<<','<<PorePress0c[p]<<','<<pressure[p]<<','<<PorePressc[p]<<','<<expected<<','<<limit<<','<<r.wrong<<','<<projected<<','<<FloatBits(PorePressc[p])<<'\n';Rows++;
      if(legacy){*legacy<<Idpc[p]<<','<<FSTypec[p]<<','<<PorePress0c[p]<<','<<pressure[p]<<','<<PorePressc[p]<<','<<FloatBits(PorePressc[p])<<'\n';LegacyRows++;}
    }
  }
public:
  Shepard(){
    Log=AppInfo.LogPtr();Timersc->Config(false);OmpThreads=1;omp_set_num_threads(1);
    Np=CaseNp=CaseNfluid=Count;Npb=NpbOk=CaseNpb=CaseNfixed=0;TKernel=KERNEL_Cubic;TVisco=VISCO_Artificial;TDensity=DDT_None;TStep=STEP_Symplectic;
    Simulate2D=true;TBoundary=BC_DBC;TMdbc2=MDBC2_None;SlipMode=SLIP_Vel0;HydroMech=true;HydroMechDrainage=false;HydroMechTopLoadMode=HMLOAD_None;
    PorosityObserver=PorosityFeedback=true;SoilStressRateGradCorr=PoreCompressionGradCorr=true;PoreCompressionSourceMode=0;SoilBoundaryDerivativeSPR=false;
    SoilHourglassXi=0;SoilDamping=false;Visco=0;ArtificialStress=false;ShiftingMode=SHIFT_None;Gravity=TFloat3(0);UseNormals=false;Symmetry=false;UseDEM=false;PoreShepardRegularization=false;PoreShepardInterval=40;
    SoilCte={};SoilCte.ModulusK=19607844.f;SoilCte.ModulusG=7518797.f;SoilCte.PoreWaterBulkModulus=1e9f;SoilCte.PoreWaterRho=1000;SoilCte.Porosity=.35f;RhopZero=2072.5f;
    Dp=.25;KernelH=float(1.2*Dp);KernelSize=2*KernelH;KernelSize2=KernelSize*KernelSize;Eta2=.01f*KernelH*KernelH;MassFluid=MassBound=float(double(RhopZero)*Dp*Dp);
    CSP=CteSphNull();CSP.simulate2d=true;CSP.tkernel=TKernel;CSP.kernelh=KernelH;CSP.kernelsize=KernelSize;CSP.kernelsize2=KernelSize2;CSP.eta2=Eta2;CSP.dp=Dp;CSP.massfluid=MassFluid;CSP.massbound=MassBound;CSP.rhopzero=RhopZero;CSP.kcubic=fsph::GetKernelCubic_Ctes(true,KernelH);
    AllocCpuMemoryParticles(Count,0);ReserveBasicArraysCpu();Need(Count<=CpuParticlesSize&&CheckCpuParticlesSize(Count),"Actual81-point allocation is insufficient");
    for(unsigned p=0;p<Np;p++){Idpc[p]=p;Codec[p]=CODE_TYPE_FLUID;Dcellc[p]=0;Posc[p]=TDouble3(0);Velrhopc[p]=TFloat4(0,0,0,RhopZero);Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;PorePressc[p]=PorePress0c[p]=PorePressRatec[p]=0;CorrMatc[p]=TMatrix3d(0);FSTypec[p]=FST_Inner;FSNormalc[p]=TFloat3(0);PosDivc[p]=0;HydroMechLoadAcec[p]=TFloat3(0);}
    InitPorosityObserverCpu(); // Same real observer initialization as retained Feedback, before private field selectors.
    Npb=NpbOk=CaseNpb=CaseNfixed=1;CaseNfluid=Count-1;CellTable();Gravity=CSP.gravity=TFloat3(0,0,-1./16.);NoStep();
  }
  void Run(bool legacyOnly,std::ostream& rows,std::ostream& legacy,std::ostream& done){
    One("legacy_u_pw",2,false,false,true,rows,&legacy);
    if(!legacyOnly){One("filter_OFF",2,true,false,false,rows);One("hydrostatic",0,true,false,true,rows);One("constant_excess16",1,true,false,true,rows);One("mixed_J",2,true,false,true,rows);One("mixed_J_free",2,true,true,true,rows);Need(ConstantBits==160&&WeightWitnesses>0&&Projected>0,"Required constant/weight/projection witnesses are empty");}
    Need(LegacyRows==Count&&Rows==(legacyOnly?Count:6*Count),"Incomplete field coverage");NoStep();
    done<<std::setprecision(17)<<"{\"stage\":\"upl_prestress_shepard_cpu_r1\",\"passed\":true,\"legacy_only\":"<<(legacyOnly?"true":"false")<<",\"Cubic_only\":true,\"actual_slots\":81,\"fixed_source_canaries\":1,\"fluid_targets\":80,\"rows\":"<<Rows<<",\"legacy_rows\":"<<LegacyRows<<",\"last_actual_inner_count\":"<<MaskInner<<",\"last_actual_surface_count\":"<<MaskSurface<<",\"constant_excess_bits_checks\":"<<ConstantBits<<",\"resolved_wrong_Mass_over_rho_witnesses\":"<<WeightWitnesses<<",\"max_wrong_weight_difference_Pa\":"<<MaxWrongDifference<<",\"positive_postfilter_projection_checks\":"<<Projected<<",\"max_independent_roundoff_ratio\":"<<MaxRatio<<",\"all_protected_native_state_bits_unchanged\":true,\"completed_physical_steps\":0,\"actual_integrator_or_interval40_tested\":false,\"wall_fit_or_gravity_equilibrium_tested\":false,\"new_physical_tolerance\":false,\"physical_acceptance\":false}\n";
  }
};
int main(int argc,char** argv){try{
  const bool legacy=argc==4&&std::string(argv[1])=="--legacy";Need((argc==3||legacy)&&std::string(argv[legacy?2:1])=="--out","Use [--legacy] --out FRESH_DIR");const fs::path out(argv[legacy?3:2]);Need(!fs::exists(out),"Existing result protected");
  AppInfo.ConfigRunPaths(argv[0]);AppInfo.ConfigOutput(true,false,out.string(),"data");AppInfo.LogInit((out/"Run.out").string());
  std::ofstream rows(out/"rows.csv"),old(out/"legacy.csv"),done(out/"completion.json");rows<<std::setprecision(17);old<<std::setprecision(17);
  rows<<"group,native_id,fixed,fstype,actual_inner_count,actual_surface_count,x,z,J,cached_Rhop,p0,p_before,p_after,independent_expected_Pa,roundoff_limit_Pa,wrong_Mass_over_rho_unprojected_reference_Pa,projected,actual_p_float_bits\n";old<<"native_id,fstype,p0,p_before,p_after,actual_p_float_bits\n";
  Shepard fixture;fixture.Run(legacy,rows,old,done);for(auto* f:{&rows,&old,&done}){f->flush();Need(bool(*f),"Output write failed");}return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Shepard component failed; preserve fresh results\n";return 2;}}

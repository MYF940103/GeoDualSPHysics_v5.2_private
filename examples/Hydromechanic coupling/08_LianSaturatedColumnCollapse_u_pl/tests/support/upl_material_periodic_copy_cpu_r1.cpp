// Actual CPU Symplectic periodic field copy only: native -> X ghost -> XZ ghost.
#include "JSphCpuSingle.h"
#include "JArraysCpu.h"
#include "JDsDcellDef.h"
#include "JPeriodicDef.h"
#include "JAppInfo.h"
#include "JException.h"
#include <array>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <omp.h>
JAppInfo AppInfo("UplMaterialPeriodicCopyCpu","r1","06-11-2026");
namespace fs=std::filesystem;
static void Need(bool v,const char* s){if(!v)throw std::runtime_error(s);}
template<class T> static bool Bits(T a,T b){return !std::memcmp(&a,&b,sizeof(T));}
static bool Same(tdouble3 a,tdouble3 b){return Bits(a.x,b.x)&&Bits(a.y,b.y)&&Bits(a.z,b.z);}
static bool Same(tfloat4 a,tfloat4 b){return Bits(a.x,b.x)&&Bits(a.y,b.y)&&Bits(a.z,b.z)&&Bits(a.w,b.w);}
template<class T> static bool Tensor(const T& a,const T& b){return Bits(a.xx,b.xx)&&Bits(a.yy,b.yy)&&Bits(a.zz,b.zz)&&Bits(a.xy,b.xy)&&Bits(a.yz,b.yz)&&Bits(a.xz,b.xz);}
class Probe:public JSphCpuSingle{
  static constexpr unsigned Slots=8;
  struct Saved{unsigned id,cell;typecode code;tdouble3 pos,prepos;tfloat4 vel,prevel;tsymatrix3d sigma,presigma;tsymatrix3f tau;float k,p,p0,rate,pre;double j,jn,theta;};
  Saved Get(unsigned q)const{return {Idpc[q],Dcellc[q],Codec[q],Posc[q],PosPrec[q],Velrhopc[q],VelrhopPrec[q],Sigmac[q],SigmaPrec[q],SpsTauc[q],Kplasticc[q],PorePressc[q],PorePress0c[q],PorePressRatec[q],PorePressPrec[q],PoroJc[q],PoroJPrec[q],PoroThetac[q]};}
  static bool Fields(const Saved& a,const Saved& b){
    return Same(a.prepos,b.prepos)&&Same(a.vel,b.vel)&&Same(a.prevel,b.prevel)&&Tensor(a.sigma,b.sigma)&&Tensor(a.presigma,b.presigma)&&Tensor(a.tau,b.tau)
      &&Bits(a.p,b.p)&&Bits(a.p0,b.p0)&&Bits(a.rate,b.rate)&&Bits(a.pre,b.pre)&&Bits(a.j,b.j)&&Bits(a.jn,b.jn)&&Bits(a.theta,b.theta);
  }
  static bool All(const Saved& a,const Saved& b){return a.id==b.id&&a.cell==b.cell&&a.code==b.code&&Same(a.pos,b.pos)&&Fields(a,b)&&Bits(a.k,b.k);}
  void Copy(unsigned mode,const char* axis,unsigned start,const std::array<unsigned,2>& list,tdouble3 inc,std::ostream& csv){
    std::array<Saved,Slots> before;for(unsigned q=0;q<Slots;q++)before[q]=Get(q);
    PeriodicDuplicateSymplectic(2,start,DomCells,inc,list.data(),Idpc,Codec,Dcellc,Posc,Velrhopc,SpsTauc,PosPrec,VelrhopPrec,Sigmac,SigmaPrec,PorePressc,PorePress0c,PorePressRatec,PorePressPrec);
    for(unsigned n=0;n<2;n++){
      const unsigned src=list[n]&0x7fffffffu,dst=start+n;const auto& b=before[src];const auto a=Get(dst);const double sign=(list[n]&0x80000000u)?-1.:1.;const tdouble3 pos=b.pos+inc*sign;
      const unsigned cx=unsigned((pos.x+4.)/.125),cy=unsigned((pos.y+4.)/.125),cz=unsigned((pos.z+4.)/.125);
      Need(a.id==b.id&&a.code==CODE_SetPeriodic(b.code)&&Same(a.pos,pos)&&a.cell==DCEL_Cell(DomCellCode,cx,cy,cz),"Actual periodic ID/CODE/translated position/cell differs");
      Need(Fields(a,b),"Existing current/pre velocity,stress,pore or J/theta field copy changed");
      Need(Bits(a.k,mode==1?b.k:before[dst].k),"Mode1 kappa copy or mode0 literal untouched kappa failed");
      csv<<mode<<','<<axis<<','<<src<<','<<dst<<','<<(sign<0)<<','<<a.id<<','<<unsigned(a.code)<<','<<a.pos.x<<','<<a.pos.y<<','<<a.pos.z<<','<<a.cell<<','<<b.k<<','<<before[dst].k<<','<<a.k<<','<<a.j<<','<<a.jn<<','<<a.theta<<",1,1\n";
    }
    for(unsigned q=0;q<Slots;q++)if(q<start||q>=start+2)Need(All(Get(q),before[q]),"Native/source/unused-canary slot changed outside destination range");
    Need(TimeStep==0&&Nstep==0&&!HydroMech&&!PorosityFeedback&&!PorosityObserver,"Component invoked an unintended physical stage");Np+=2;
  }
public:
  explicit Probe(unsigned mode){
    OmpThreads=1;omp_set_num_threads(1);Simulate2D=true;TStep=STEP_Symplectic;Np=2;Npb=NpbOk=0;TimeStep=0;Nstep=0;
    HydroMech=PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=false;SoilCte={};SoilCte.MaterialReturn=mode;
    PeriX=PeriZ=true;PeriY=false;PeriActive=DefPeriActive(true,false,true);PeriXinc=TDouble3(1.25,0,0);PeriZinc=TDouble3(0,0,1.25);
    DomPosMin=TDouble3(-4);Scell=.125;DomCells=TUint3(63);DomCellCode=DCEL_GetCode(6,6,6);CpuParticlesSize=Slots;
    ArraysCpu->SetArraySize(Slots);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_24B,3);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_16B,2);
    ArraysCpu->SetArrayCount(JArraysCpu::SIZE_48B,2);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_8B,3);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_4B,7);
#ifdef CODE_SIZE4
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,1);
#else
    ArraysCpu->SetArrayCount(JArraysCpu::SIZE_2B,1);
#endif
    Idpc=ArraysCpu->ReserveUint();Dcellc=ArraysCpu->ReserveUint();Codec=ArraysCpu->ReserveTypeCode();Kplasticc=ArraysCpu->ReserveFloat();
    Posc=ArraysCpu->ReserveDouble3();PosPrec=ArraysCpu->ReserveDouble3();SpsTauc=ArraysCpu->ReserveSymatrix3f();
    Velrhopc=ArraysCpu->ReserveFloat4();VelrhopPrec=ArraysCpu->ReserveFloat4();Sigmac=ArraysCpu->ReserveSymatrix3d();SigmaPrec=ArraysCpu->ReserveSymatrix3d();
    PorePressc=ArraysCpu->ReserveFloat();PorePress0c=ArraysCpu->ReserveFloat();PorePressRatec=ArraysCpu->ReserveFloat();PorePressPrec=ArraysCpu->ReserveFloat();
    PoroJc=ArraysCpu->ReserveDouble();PoroJPrec=ArraysCpu->ReserveDouble();PoroThetac=ArraysCpu->ReserveDouble();
    for(unsigned q=0;q<Slots;q++){
      Idpc[q]=q<2?41+q:1000+q;Codec[q]=CODE_TYPE_FLUID;Dcellc[q]=0;Posc[q]=TDouble3(.125+.5*q,0,.375+.5*q);PosPrec[q]=Posc[q]+TDouble3(1./64,0,1./32);
      Velrhopc[q]=TFloat4(float(q)/8,0,-float(q)/16,2072.5f);VelrhopPrec[q]=TFloat4(-float(q)/32,0,float(q)/64,2048.f+q);
      tsymatrix3d s{};s.xx=1.+q;s.yy=2.+q;s.zz=3.+q;s.xy=4.+q;s.yz=5.+q;s.xz=6.+q;Sigmac[q]=s;s.xx+=.5;s.yz-=.25;SigmaPrec[q]=s;
      tsymatrix3f t{};t.xx=.125f+q;t.yy=.25f+q;t.zz=.5f+q;t.xy=.75f+q;t.yz=1.f+q;t.xz=1.25f+q;SpsTauc[q]=t;
      Kplasticc[q]=q==0?.125f:q==1?.75f:2.f+float(q)/4;PorePressc[q]=16.f+q;PorePress0c[q]=32.f+q;PorePressRatec[q]=-.125f*float(q+1);PorePressPrec[q]=64.f+q;
      PoroJc[q]=1.+q/16.;PoroJPrec[q]=1.-q/32.;PoroThetac[q]=q/8.;
    }
  }
  void Run(unsigned mode,std::ostream& csv){
    Copy(mode,"X",2,{{0,0x80000001u}},PeriXinc,csv); // native0/1 -> positive/negative X images
    Copy(mode,"Z_after_X",4,{{2,0x80000003u}},PeriZinc,csv); // images themselves become XZ sources
    Need(Np==6&&Bits(Kplasticc[0],.125f)&&Bits(Kplasticc[1],.75f),"Native nonzero history or appended count changed");
  }
};
int main(int argc,char** argv){try{
  Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_DIR");const fs::path out=argv[2];Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh result directory required");Need(fs::create_directory(out),"Cannot create fresh result");
  std::ofstream csv(out/"copies.csv");csv<<std::setprecision(17)<<"mode,axis,source_slot,destination_slot,inverse,native_id,CODE,x,y,z,cell,source_kappa,old_destination_kappa,new_destination_kappa,J,Jpre,theta,existing_fields_bit_exact,other_slots_bit_unchanged\n";
  {Probe p(1);p.Run(1,csv);}{Probe p(0);p.Run(0,csv);}csv.flush();Need(bool(csv),"Copy CSV write failed");
  std::ofstream done(out/"completion.json");done<<"{\"stage\":\"upl_material_periodic_copy_cpu_r1\",\"passed\":true,\"pool_slots_per_mode\":8,\"native_slots_per_mode\":2,\"periodic_destinations_per_mode\":4,\"canary_slots_per_mode\":2,\"modes\":[1,0],\"actual_PeriodicDuplicateSymplectic_calls\":4,\"destination_rows\":8,\"mode1_kappa_copy_rows\":4,\"mode0_untouched_kappa_rows\":4,\"two_axis_ghost_source_chain\":true,\"all_existing_history_fields_bit_exact\":true,\"native_and_canary_slots_unchanged\":true,\"whole_struct_padding_compared\":false,\"RunPeriodic_or_CellDivide_called\":false,\"InitRun_or_force_or_integrator_called\":false,\"physical_steps\":0,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

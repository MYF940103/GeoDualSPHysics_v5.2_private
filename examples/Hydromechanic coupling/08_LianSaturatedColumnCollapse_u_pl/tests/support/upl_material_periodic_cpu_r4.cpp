// Actual periodic copy + one real cell permutation per integrator, no force or step.
#include "JSphCpuSingle.h"
#include "JArraysCpu.h"
#include "JDsTimersCpu.h"
#include "JCellDivCpuSingle.h"
#include "JDsDcellDef.h"
#include "JDsDcell.h"
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
JAppInfo AppInfo("UplMaterialPeriodicCpu","r4","07-11-2026");
namespace fs=std::filesystem;
static void Need(bool v,const char* s){if(!v)throw std::runtime_error(s);}
template<class T>static bool Bits(T a,T b){return !std::memcmp(&a,&b,sizeof(T));}
static bool Same(tdouble3 a,tdouble3 b){return Bits(a.x,b.x)&&Bits(a.y,b.y)&&Bits(a.z,b.z);}
static bool Same(tfloat4 a,tfloat4 b){return Bits(a.x,b.x)&&Bits(a.y,b.y)&&Bits(a.z,b.z)&&Bits(a.w,b.w);}
template<class T>static bool Tensor(const T& a,const T& b){return Bits(a.xx,b.xx)&&Bits(a.yy,b.yy)&&Bits(a.zz,b.zz)&&Bits(a.xy,b.xy)&&Bits(a.yz,b.yz)&&Bits(a.xz,b.xz);}
class Probe:public JSphCpuSingle{
  static constexpr unsigned Slots=8;const bool Sym;
  struct Saved{unsigned id,cell;typecode code;tdouble3 pos,prepos;tfloat4 vel,hvel;tsymatrix3d sigma,hsigma;tsymatrix3f tau;float k,km1,p,p0,rate,hp;double j,jn,theta;};
  tfloat4* HistoryVel()const{return Sym?VelrhopPrec:VelrhopM1c;}
  tsymatrix3d* HistorySigma()const{return Sym?SigmaPrec:SigmaM1c;}
  float* HistoryPore()const{return Sym?PorePressPrec:PorePressM1c;}
  Saved Get(unsigned q)const{return {Idpc[q],Dcellc[q],Codec[q],Posc[q],Sym?PosPrec[q]:TDouble3(0),Velrhopc[q],HistoryVel()[q],Sigmac[q],HistorySigma()[q],SpsTauc[q],Kplasticc[q],Sym?0.f:KplasticM1c[q],PorePressc[q],PorePress0c[q],PorePressRatec[q],HistoryPore()[q],Sym?PoroJc[q]:0.,Sym?PoroJPrec[q]:0.,Sym?PoroThetac[q]:0.};}
  static bool Fields(const Saved& a,const Saved& b){return Same(a.prepos,b.prepos)&&Same(a.vel,b.vel)&&Same(a.hvel,b.hvel)&&Tensor(a.sigma,b.sigma)&&Tensor(a.hsigma,b.hsigma)&&Tensor(a.tau,b.tau)&&Bits(a.k,b.k)&&Bits(a.km1,b.km1)&&Bits(a.p,b.p)&&Bits(a.p0,b.p0)&&Bits(a.rate,b.rate)&&Bits(a.hp,b.hp)&&Bits(a.j,b.j)&&Bits(a.jn,b.jn)&&Bits(a.theta,b.theta);}
  static bool All(const Saved& a,const Saved& b){return a.id==b.id&&a.cell==b.cell&&a.code==b.code&&Same(a.pos,b.pos)&&Fields(a,b);}
  unsigned Cell(tdouble3 p)const{return DCEL_Cell(DomCellCode,unsigned((p.x-DomPosMin.x)/Scell),unsigned((p.y-DomPosMin.y)/Scell),unsigned((p.z-DomPosMin.z)/Scell));}
  void Scope()const{Need(TimeStep==0&&Nstep==0&&!HydroMech&&!PorosityFeedback&&!PorosityObserver&&(Sym?KplasticM1c==NULL:KplasticM1c!=NULL),"Copy-only/integrator history scope changed");}
  void Copy(const char* axis,unsigned start,const std::array<unsigned,2>& list,tdouble3 inc,std::ostream& csv){
    std::array<Saved,Slots> before;for(unsigned q=0;q<Slots;q++)before[q]=Get(q);
    if(Sym)PeriodicDuplicateSymplectic(2,start,DomCells,inc,list.data(),Idpc,Codec,Dcellc,Posc,Velrhopc,SpsTauc,PosPrec,VelrhopPrec,Sigmac,SigmaPrec,PorePressc,PorePress0c,PorePressRatec,PorePressPrec);
    else PeriodicDuplicateVerlet(2,start,DomCells,inc,list.data(),Idpc,Codec,Dcellc,Posc,Velrhopc,SpsTauc,VelrhopM1c,Sigmac,SigmaM1c,PorePressc,PorePress0c,PorePressRatec,PorePressM1c);
    for(unsigned n=0;n<2;n++){const unsigned src=list[n]&0x7fffffffu,dst=start+n;const auto& b=before[src];const auto a=Get(dst);const double sign=(list[n]&0x80000000u)?-1.:1.;const tdouble3 pos=b.pos+inc*sign;
      Need(a.id==b.id&&a.code==CODE_SetPeriodic(b.code)&&Same(a.pos,pos)&&a.cell==Cell(pos)&&Fields(a,b),"Actual periodic ID/geometry/history copy differs");
      csv<<(Sym?"Symplectic":"Verlet")<<','<<axis<<','<<src<<','<<dst<<','<<a.id<<','<<a.pos.x<<','<<a.pos.z<<','<<a.k<<',';if(!Sym)csv<<a.km1;csv<<",1,1\n";
    }
    for(unsigned q=0;q<Slots;q++)if(q<start||q>=start+2)Need(All(Get(q),before[q]),"Native/source/unused canary changed outside destination range");Np+=2;Scope();
  }
public:
  explicit Probe(bool sym):Sym(sym){
    OmpThreads=1;omp_set_num_threads(1);Timersc->Config(false);Simulate2D=true;TStep=Sym?STEP_Symplectic:STEP_Verlet;Np=2;Npb=NpbOk=0;TimeStep=0;Nstep=0;
    HydroMech=PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=false;SoilCte={};PeriX=PeriZ=true;PeriY=false;PeriActive=DefPeriActive(true,false,true);PeriXinc=TDouble3(1.25,0,0);PeriZinc=TDouble3(0,0,1.25);
    DomPosMin=TDouble3(-4,0,-4);Scell=.125;DomCells=TUint3(64,1,64);DomCellCode=JDsDcell::CalcCellCode(DomCells+TUint3(1));CpuParticlesSize=Slots;
    ArraysCpu->SetArraySize(Slots);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_24B,Sym?3:2);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_16B,2);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_48B,2);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_8B,Sym?3:0);ArraysCpu->SetArrayCount(JArraysCpu::SIZE_4B,Sym?7:8);
#ifdef CODE_SIZE4
    ArraysCpu->AddArrayCount(JArraysCpu::SIZE_4B,1);
#else
    ArraysCpu->SetArrayCount(JArraysCpu::SIZE_2B,1);
#endif
    Idpc=ArraysCpu->ReserveUint();Dcellc=ArraysCpu->ReserveUint();Codec=ArraysCpu->ReserveTypeCode();Kplasticc=ArraysCpu->ReserveFloat();Posc=ArraysCpu->ReserveDouble3();SpsTauc=ArraysCpu->ReserveSymatrix3f();Velrhopc=ArraysCpu->ReserveFloat4();Sigmac=ArraysCpu->ReserveSymatrix3d();PorePressc=ArraysCpu->ReserveFloat();PorePress0c=ArraysCpu->ReserveFloat();PorePressRatec=ArraysCpu->ReserveFloat();
    if(Sym){PosPrec=ArraysCpu->ReserveDouble3();VelrhopPrec=ArraysCpu->ReserveFloat4();SigmaPrec=ArraysCpu->ReserveSymatrix3d();PorePressPrec=ArraysCpu->ReserveFloat();PoroJc=ArraysCpu->ReserveDouble();PoroJPrec=ArraysCpu->ReserveDouble();PoroThetac=ArraysCpu->ReserveDouble();}
    else{VelrhopM1c=ArraysCpu->ReserveFloat4();SigmaM1c=ArraysCpu->ReserveSymatrix3d();PorePressM1c=ArraysCpu->ReserveFloat();KplasticM1c=ArraysCpu->ReserveFloat();}
    for(unsigned q=0;q<Slots;q++){Idpc[q]=q<2?41+q:1000+q;Codec[q]=CODE_TYPE_FLUID;Posc[q]=TDouble3(.125+.5*q,0,.375+.5*q);Dcellc[q]=Cell(Posc[q]);Velrhopc[q]=TFloat4(float(q)/8,0,-float(q)/16,2072.5f);HistoryVel()[q]=TFloat4(-float(q)/32,0,float(q)/64,2048.f+q);
      auto s=TSymMatrix3d(1.+q,4.+q,6.+q,2.+q,5.+q,3.+q);Sigmac[q]=s;s.xx+=.5;s.yz-=.25;HistorySigma()[q]=s;SpsTauc[q]={.125f+q,.75f+q,1.25f+q,.25f+q,1.f+q,.5f+q};
      Kplasticc[q]=q==0?.125f:q==1?.75f:2.f+float(q)/4;PorePressc[q]=16.f+q;PorePress0c[q]=32.f+q;PorePressRatec[q]=-.125f*float(q+1);HistoryPore()[q]=64.f+q;
      if(Sym){PosPrec[q]=Posc[q]+TDouble3(1./64,0,1./32);PoroJc[q]=1.+q/16.;PoroJPrec[q]=1.-q/32.;PoroThetac[q]=q/8.;}else KplasticM1c[q]=.03125f+float(q)/16;
    }Scope();
  }
  void Run(std::ostream& copy,std::ostream& sorted,const fs::path& out){
    Copy("X",2,{{0,0x80000001u}},PeriXinc,copy);Kplasticc[0]=.25f;if(!Sym)KplasticM1c[0]=.015625f;
    Copy("Z_after_X",4,{{2,0x80000003u}},PeriZinc,copy);Need(Np==6,"Actual copy count differs");
    copy.flush();Need(bool(copy),"Copy CSV flush failed before divide");
    std::array<Saved,Slots> before;for(unsigned q=0;q<Slots;q++)before[q]=Get(q);
    std::ofstream cells(out/(Sym?"cells_Symplectic.csv":"cells_Verlet.csv"));cells<<"slot,key,expected_x,expected_y,expected_z,decoded_x,decoded_y,decoded_z\n";
    Need(DomCellCode!=0&&DCEL_GetSx(DomCellCode)-1+DCEL_GetSy(DomCellCode)+DCEL_GetSz(DomCellCode)==31,"Invalid 1+31-bit cell distribution");
    for(unsigned q=0;q<6;q++){unsigned key=Dcellc[q];const unsigned x=unsigned((Posc[q].x-DomPosMin.x)/Scell),y=unsigned((Posc[q].y-DomPosMin.y)/Scell),z=unsigned((Posc[q].z-DomPosMin.z)/Scell);const unsigned ax=DCEL_Cellx(DomCellCode,key),ay=DCEL_Celly(DomCellCode,key),az=DCEL_Cellz(DomCellCode,key);cells<<q<<','<<key<<','<<x<<','<<y<<','<<z<<','<<ax<<','<<ay<<','<<az<<'\n';cells.flush();Need(bool(cells)&&x<DomCells.x&&y<DomCells.y&&z<DomCells.z&&ax==x&&ay==y&&az==z,"Cell key failed geometric decode/bounds before Divide");}
    std::cerr<<(Sym?"Symplectic":"Verlet")<<": construct divider after 6 decoded cells\n"<<std::flush;
    JCellDivCpuSingle divider(true,false,PeriActive,true,CELLMODE_Full,float(Scell),DomPosMin,TDouble3(4,.125,4),DomCells,0,0,0,out.string());divider.DefineDomain(DomCellCode,TUint3(0),DomCells,DomPosMin,TDouble3(4,.125,4));
    std::cerr<<"before Divide\n"<<std::flush;divider.Divide(0,2,0,4,true,Dcellc,Codec,Idpc,Posc,Timersc);std::cerr<<"after Divide\n"<<std::flush;Need(divider.GetNpFinal()==6&&!divider.GetNpfOut()&&!divider.GetNpfOutIgnore(),"Actual divide excluded a fixture slot");
    const auto sort=[&](auto* field,const char* name){std::cerr<<"before SortArray "<<name<<'\n'<<std::flush;divider.SortArray(field);std::cerr<<"after SortArray "<<name<<'\n'<<std::flush;};
    sort(Idpc,"Idpc");sort(Codec,"Codec");sort(Dcellc,"Dcellc");sort(Posc,"Posc");sort(Velrhopc,"Velrhopc");sort(Sigmac,"Sigmac");sort(Kplasticc,"Kplasticc");sort(SpsTauc,"SpsTauc");sort(HistoryVel(),"HistoryVel");sort(HistorySigma(),"HistorySigma");sort(PorePressc,"PorePressc");sort(PorePress0c,"PorePress0c");sort(PorePressRatec,"PorePressRatec");sort(HistoryPore(),"HistoryPore");
    if(Sym){sort(PosPrec,"PosPrec");sort(PoroJc,"PoroJc");sort(PoroJPrec,"PoroJPrec");sort(PoroThetac,"PoroThetac");}else sort(KplasticM1c,"KplasticM1c");
    unsigned moved=0;std::array<bool,6> used{};for(unsigned q=0;q<6;q++){const auto a=Get(q);unsigned src=6;for(unsigned s=0;s<6;s++)if(a.id==before[s].id&&Same(a.pos,before[s].pos)){Need(src==6,"Ambiguous fixture identity");src=s;}Need(src<6&&!used[src]&&All(a,before[src]),"Real public SortArray lost paired history or another field");used[src]=true;moved+=src!=q;sorted<<(Sym?"Symplectic":"Verlet")<<','<<q<<','<<src<<','<<a.id<<','<<a.pos.x<<','<<a.pos.z<<','<<a.k<<',';if(!Sym)sorted<<a.km1;sorted<<",1\n";}
    Need(moved>0&&All(Get(6),before[6])&&All(Get(7),before[7]),"Sort witness vacuous or tail canary changed");Scope();
  }
};
int main(int argc,char** argv){try{
  Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_DIR");const fs::path out=argv[2];Need(!fs::exists(out)&&fs::is_directory(out.parent_path())&&fs::create_directory(out),"Fresh output required");AppInfo.LogInit((out/"component.log").string());std::ofstream copy(out/"copies.csv"),sorted(out/"sort.csv");copy<<std::setprecision(17)<<"integrator,axis,source_slot,destination_slot,native_id,x,z,kappa,kappaM1,all_fields_exact,other_slots_unchanged\n";sorted<<std::setprecision(17)<<"integrator,destination_slot,source_slot,native_id,x,z,kappa,kappaM1,all_fields_exact\n";
  for(bool sym:{true,false}){Probe p(sym);p.Run(copy,sorted,out);}copy.flush();sorted.flush();Need(bool(copy)&&bool(sorted),"Copy/sort CSV write failed");std::ofstream done(out/"completion.json");done<<"{\"stage\":\"upl_material_periodic_cpu_r4\",\"passed\":true,\"slots_per_integrator\":8,\"actual_periodic_copy_calls\":4,\"copy_rows\":8,\"actual_public_Divide_calls\":2,\"sort_rows\":12,\"actual_SortArray_float_history\":true,\"Verlet_current_and_M1_kappa\":true,\"Symplectic_no_M1_allocation\":true,\"two_axis_image_source_chain\":true,\"native_and_tail_checked\":true,\"no_struct_padding_compared\":true,\"force_or_integrator_or_InitRun_called\":false,\"physical_steps\":0,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

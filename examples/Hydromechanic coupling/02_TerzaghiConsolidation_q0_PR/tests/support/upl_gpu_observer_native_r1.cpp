// Private GPU observer entry and typed native-output checks only.
// The solver mode calls the actual JSphGpuSingle::Run without rewriting fields.
// No feedback, dynamic Darcy, public GPU unlock or physical acceptance is implied.
#include "JSphGpuSingle.h"
#include "JSphCfgRun.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "JPartDataBi4.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

JAppInfo AppInfo("GpuPorosityObserver","r1","02-11-2026");
namespace fs=std::filesystem;
static void Check(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
static unsigned Uint(const char* text){
  const std::string s=text;Check(!s.empty()&&s.find_first_not_of("0123456789")==std::string::npos,"Expected unsigned integer");
  const auto n=std::stoull(s);Check(n<=unsigned(-1),"Unsigned integer overflow");return unsigned(n);
}
static void Fresh(const fs::path& path){Check(!fs::exists(path),"Retained output protected");Check(fs::is_directory(path.parent_path()),"Output parent directory must already exist");}
static bool Finite(unsigned){return true;}
static bool Finite(float x){return std::isfinite(x);}
static bool Finite(tfloat3 x){return std::isfinite(x.x)&&std::isfinite(x.y)&&std::isfinite(x.z);}
static bool Finite(tdouble3 x){return std::isfinite(x.x)&&std::isfinite(x.y)&&std::isfinite(x.z);}
template<class T>static std::vector<T> NativeArray(JPartDataBi4& p,const char* name,unsigned n,JBinaryDataDef::TpData type){
  const auto* a=p.GetArray(name,type);Check((a->DataInPointer()?a->GetCount():a->GetFileDataCount())==n,"Wrong native array count");
  std::vector<T> v(n);Check(a->GetDataCopy(n,v.data())==n,"Incomplete native array read");return v;
}
static std::vector<unsigned> Order(const std::vector<unsigned>& id){
  const unsigned n=unsigned(id.size());std::vector<unsigned> order(n,unsigned(-1));
  for(unsigned i=0;i<n;i++){Check(id[i]<n&&order[id[i]]==unsigned(-1),"Native IDs must be unique and contiguous");order[id[i]]=i;}
  return order;
}
static double Error(JPartDataBi4& p){
  Check(p.GetPart()->ExistsValue("dterror",JBinaryDataDef::DatDouble),"Actual signed dterror telemetry missing/wrong type");
  const double e=p.GetPart()->GetvDouble("dterror");
  Check(std::isfinite(e)&&e<=1e-14,"Original signed dterror safety failed");return e;
}
static void NativeSet(JPartDataBi4& p,unsigned expected){
  Check(expected>0&&p.GetNpiece()==1&&p.Get_Npok()==expected&&!p.Get_Nout(),"Native count/pieces/exclusion changed");
  Check(p.Get_Data2d()&&!p.Get_Symmetry()&&!p.Get_NpDynamic()&&!p.Get_ReuseIds(),"Outside fixed native2D scope");
  Check(p.Get_CaseNp()==expected&&p.Get_CaseNfixed()==0&&p.Get_CaseNmoving()==0&&p.Get_CaseNfloat()==0&&p.Get_CaseNfluid()==expected,"Only a fresh no-wall native set is admitted");
  Check(std::isfinite(p.Get_TimeStep())&&p.Get_TimeStep()>=0.,"Invalid saved time");Error(p);
}
template<class T>static void ExactArray(JPartDataBi4& a,JPartDataBi4& b,const char* name,JBinaryDataDef::TpData type,const std::vector<unsigned>& oa,const std::vector<unsigned>& ob){
  const unsigned n=unsigned(oa.size());const auto x=NativeArray<T>(a,name,n,type),y=NativeArray<T>(b,name,n,type);
  for(unsigned id=0;id<n;id++)Check(Finite(x[oa[id]])&&Finite(y[ob[id]])&&!memcmp(&x[oa[id]],&y[ob[id]],sizeof(T)),name);
}
static bool ObserverSchema(JPartDataBi4& p){
  const bool j=p.ArrayExists("PoroVolumeRatio"),n=p.ArrayExists("PoroPorosity"),t=p.ArrayExists("PoroThetaLastStage");
  Check(j==n&&j==t,"Partial observer schema");return j;
}
static void Compare(const char* da,const char* db,unsigned part,unsigned expected,const fs::path& target){
  Fresh(target);JPartDataBi4 a,b;a.LoadFilePart(da,part,0,1);b.LoadFilePart(db,part,0,1);NativeSet(a,expected);NativeSet(b,expected);
  const double ta=a.Get_TimeStep(),tb=b.Get_TimeStep(),ea=Error(a),eb=Error(b);
  Check(!memcmp(&ta,&tb,sizeof(double))&&a.Get_Step()==b.Get_Step(),"Saved actual time/step changed");
  Check(a.GetPart()->ExistsValue("dterror")==b.GetPart()->ExistsValue("dterror")&&!memcmp(&ea,&eb,sizeof(double)),"Saved dterror presence/bits changed");
  const auto ia=NativeArray<unsigned>(a,"Idp",expected,JBinaryDataDef::DatUint),ib=NativeArray<unsigned>(b,"Idp",expected,JBinaryDataDef::DatUint);
  const auto oa=Order(ia),ob=Order(ib);
  ExactArray<unsigned>(a,b,"Idp",JBinaryDataDef::DatUint,oa,ob);
  ExactArray<tdouble3>(a,b,"Posd",JBinaryDataDef::DatDouble3,oa,ob);
  for(const char* name:{"Vel","Sigma_kk","Sigma_ij","FSNormal","HydroMechLoadAce"})ExactArray<tfloat3>(a,b,name,JBinaryDataDef::DatFloat3,oa,ob);
  for(const char* name:{"Rhop","Kplastic","PorePress","PorePress0","ExcessPorePress"})ExactArray<float>(a,b,name,JBinaryDataDef::DatFloat,oa,ob);
  for(const char* name:{"SigmaState_kk","SigmaState_ij"})ExactArray<tdouble3>(a,b,name,JBinaryDataDef::DatDouble3,oa,ob);
  ExactArray<unsigned>(a,b,"FSType",JBinaryDataDef::DatUint,oa,ob);
  const auto rho=NativeArray<float>(a,"Rhop",expected,JBinaryDataDef::DatFloat),plastic=NativeArray<float>(a,"Kplastic",expected,JBinaryDataDef::DatFloat);
  for(unsigned i=0;i<expected;i++)Check(rho[i]>0&&plastic[i]==0,"Nonpositive native density or nonelastic state");
  const bool sa=ObserverSchema(a),sb=ObserverSchema(b);
  std::ofstream out(target);out<<std::setprecision(17)
    <<"{\"passed\":true,\"part\":"<<part<<",\"native_count\":"<<expected<<",\"arrays\":15,\"actual_time_s\":"<<ta<<",\"saved_step\":"<<a.Get_Step()
    <<",\"dterror_s\":"<<ea<<",\"observer_schema_a\":"<<(sa?"true":"false")<<",\"observer_schema_b\":"<<(sb?"true":"false")
    <<",\"all_original_physical_array_bits_identical\":true,\"native_ID_aligned\":true,\"saved_time_step_dterror_exact\":true,\"no_exclusions\":true,\"physical_acceptance\":false}\n";
  out.flush();Check(bool(out),"Comparison receipt write failed");
}
static void ReadPoro(const char* dir,unsigned part,unsigned expected,unsigned fixed,double n0,const fs::path& target,const fs::path& receipt){
  Fresh(target);Fresh(receipt);Check(target!=receipt,"CSV and receipt must differ");
  Check(fixed==0,"This GPU observer stage admits no fixed boundary particles");
  Check(std::isfinite(n0)&&n0>0.&&n0<1.,"Expected actual 0<n0<1");
  JPartDataBi4 p;p.LoadFilePart(dir,part,0,1);NativeSet(p,expected);Check(ObserverSchema(p),"Observer arrays absent");
  const auto id=NativeArray<unsigned>(p,"Idp",expected,JBinaryDataDef::DatUint),order=Order(id);
  const auto j=NativeArray<double>(p,"PoroVolumeRatio",expected,JBinaryDataDef::DatDouble);
  const auto pn=NativeArray<double>(p,"PoroPorosity",expected,JBinaryDataDef::DatDouble);
  const auto theta=NativeArray<double>(p,"PoroThetaLastStage",expected,JBinaryDataDef::DatDouble);
  double minj=j[0],maxj=j[0],minn=pn[0],maxn=pn[0],maxtheta=0.,invariant=0.;
  std::ofstream out(target);out<<std::setprecision(17)<<"id,J,n,theta\n";
  for(unsigned native=0;native<expected;native++){
    const unsigned i=order[native];Check(std::isfinite(j[i])&&std::isfinite(pn[i])&&std::isfinite(theta[i])&&j[i]>1.-n0,"Nonfinite/out-of-domain observer state");
    const double derived=1.-(1.-n0)/j[i];Check(pn[i]==derived&&pn[i]>0.&&pn[i]<1.,"Native porosity is not the same J-derived expression");
    if(part==0)Check(j[i]==1.&&theta[i]==0.,"Fresh observer initial J/theta must be1/0");
    minj=(std::min)(minj,j[i]);maxj=(std::max)(maxj,j[i]);minn=(std::min)(minn,pn[i]);maxn=(std::max)(maxn,pn[i]);
    maxtheta=(std::max)(maxtheta,fabs(theta[i]));invariant=(std::max)(invariant,fabs((1.-pn[i])*j[i]-(1.-n0)));
    out<<native<<','<<j[i]<<','<<pn[i]<<','<<theta[i]<<'\n';
  }
  out.flush();Check(bool(out),"Native observer CSV write failed");
  std::ofstream done(receipt);done<<std::setprecision(17)
    <<"{\"passed\":true,\"part\":"<<part<<",\"native_count\":"<<expected<<",\"fixed_count\":0,\"double_arrays\":3,\"actual_time_s\":"<<p.Get_TimeStep()
    <<",\"saved_step\":"<<p.Get_Step()<<",\"n0\":"<<n0<<",\"min_J\":"<<minj<<",\"max_J\":"<<maxj<<",\"min_n\":"<<minn<<",\"max_n\":"<<maxn
    <<",\"max_abs_theta_s_inv\":"<<maxtheta<<",\"max_solid_volume_roundoff\":"<<invariant<<",\"derived_n_exact\":true,\"physical_acceptance\":false}\n";
  done.flush();Check(bool(done),"Native observer receipt write failed");
}
class GpuObserverFixture:public JSphGpuSingle{
public:
  void Enable(bool enabled){PorosityObserver=enabled;}
  void Final(const fs::path& out){
    const fs::path csvpath=out/"observer_final.csv",jsonpath=out/"observer_complete.json";Fresh(csvpath);Fresh(jsonpath);
    Check(!HydroMechDynamicSeepage&&HydroMech&&Simulate2D&&CaseNpb==0&&CaseNfluid>0,"Public GPU dynamic mode/walls are not admitted");
    Check(!PoroJPreg,"Full Run left a live predictor J history");
    const unsigned normal=ParticlesDataDown(Np,0,true,PeriActive!=0);
    Check(normal==CaseNfluid,"Final native count/exclusion changed");
    std::vector<unsigned> ids(Idp,Idp+normal);const auto order=Order(ids);
    const double n0=double(SoilCte.Porosity);Check(std::isfinite(n0)&&n0>0.&&n0<1.,"Invalid actual n0");
    std::ofstream csv(csvpath);csv<<std::setprecision(17)<<"id,J,n,theta\n";
    if(PorosityObserver){
      Check(PoroJg&&PoroThetag&&PoroJ&&PoroTheta,"Observer did not allocate complete device/host state");
      for(unsigned id=0;id<normal;id++){
        const unsigned i=order[id];Check(CODE_IsNormal(Code[i])&&CODE_IsFluid(Code[i]),"Final downloaded ID is not native soil");
        const double j=PoroJ[i],theta=PoroTheta[i],n=1.-(1.-n0)/j;
        Check(std::isfinite(j)&&std::isfinite(theta)&&std::isfinite(n)&&j>1.-n0&&n>0.&&n<1.,"Invalid final live observer state");
        csv<<id<<','<<j<<','<<n<<','<<theta<<'\n';
      }
    }
    else Check(!PoroJg&&!PoroThetag&&!PoroJ&&!PoroTheta,"OFF allocated observer state");
    csv.flush();Check(bool(csv),"Final live observer export failed");
    std::ofstream done(jsonpath);done<<std::setprecision(17)
      <<"{\"passed\":true,\"observer\":"<<(PorosityObserver?"true":"false")<<",\"actual_time_s\":"<<TimeStep<<",\"completed_steps\":"<<Nstep
      <<",\"native_count\":"<<normal<<",\"fixed_count\":0,\"n0\":"<<n0<<",\"actual_production_Run\":true,\"live_GPU_download\":true,\"predictor_history_released\":true"
      <<",\"public_dynamic_seepage\":false,\"physical_fields_rewritten_by_fixture\":false,\"feedback\":false,\"physical_acceptance\":false}\n";
    done.flush();Check(bool(done),"Observer completion write failed");
  }
};
int main(int argc,char** argv){
  try{
    Check(argc>=2,"Use --solver 0|1 GPUargs; --compare DATA_A DATA_B PART COUNT JSON; --read-poro DATA PART COUNT FIXED N0 CSV JSON");
    const std::string mode=argv[1];
    if(mode=="--compare"){Check(argc==7,"Expected DATA_A DATA_B PART COUNT NEW_JSON");Compare(argv[2],argv[3],Uint(argv[4]),Uint(argv[5]),argv[6]);return 0;}
    if(mode=="--read-poro"){Check(argc==9,"Expected DATA PART COUNT FIXED N0 NEW_CSV NEW_JSON");ReadPoro(argv[2],Uint(argv[3]),Uint(argv[4]),Uint(argv[5]),std::stod(argv[6]),argv[7],argv[8]);return 0;}
    Check(mode=="--solver"&&argc>=7,"Expected --solver 0|1 followed by normal GPU arguments");
    const std::string flag=argv[2];Check(flag=="0"||flag=="1","Observer must be0or1");
    AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=3;i<argc;i++)args.push_back(argv[i]);
    JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Check(!cfg.Cpu&&!cfg.PrintInfo,"Only an actual GPU solver invocation is admitted");
    Check(!fs::exists(cfg.DirOut),"Retained solver output protected");
    AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");
    GpuObserverFixture fixture;fixture.Enable(flag=="1");fixture.Run(AppInfo.GetFullName(),&cfg,AppInfo.LogPtr());fixture.Final(cfg.DirOut);return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
  catch(const std::string& e){std::cerr<<e<<'\n';return 1;}
  catch(const char* e){std::cerr<<e<<'\n';return 1;}
  catch(...){std::cerr<<"GPU observer fixture failed; retain all partial evidence\n";return 2;}
}

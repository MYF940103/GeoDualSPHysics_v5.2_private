// Offline decoded-typed native22/clock28 prefix comparison. No full export or solver.
#define main RetainedNeutralDecoderMain
#include "upl_cpu_public_native_r1.cpp"
#undef main
#include <cstdint>
#include <sstream>

namespace tpiraw22 {
constexpr unsigned Total=1040,Soil=1000,Fixed=40;
static_assert(sizeof(unsigned)==4&&sizeof(float)==4&&sizeof(double)==8,"Clock/array scalar ABI differs");
static_assert(sizeof(tfloat3)==12&&sizeof(tdouble3)==24,"Native vectors contain padding");
struct Tick{unsigned part,completed,saved;double time,dt;bool forced;};
struct Counts{std::uint64_t bytes=0,different=0;};
using Bytes=std::vector<unsigned char>;
static std::string Json(const std::string& value){std::ostringstream s;s<<'"';for(unsigned char c:value){if(c=='"'||c=='\\')s<<'\\'<<char(c);else if(c<32)s<<"\\u00"<<std::hex<<std::setw(2)<<std::setfill('0')<<unsigned(c)<<std::dec;else s<<char(c);}s<<'"';return s.str();}
static std::vector<std::string> Tokens(const std::string& line){std::stringstream s(line);std::vector<std::string> out;std::string v;while(std::getline(s,v,','))out.push_back(v);return out;}
static unsigned UInt(const std::string& text){Need(!text.empty()&&text.find_first_not_of("0123456789")==std::string::npos,"Unsigned plan/count field required");const auto n=std::stoull(text);Need(n<=~0u,"Plan/count overflows uint");return unsigned(n);}
static double Number(const std::string& text){size_t n=0;const double x=std::stod(text,&n);Need(n==text.size()&&std::isfinite(x),"Finite complete plan number required");return x;}
static bool Bits(double a,double b){return !std::memcmp(&a,&b,8);}
static std::vector<Tick> Plan(const fs::path& path,unsigned count){
  std::ifstream in(path);Need(bool(in),"Original clock plan missing");std::string line;std::getline(in,line);if(!line.empty()&&line.back()=='\r')line.pop_back();
  Need(line=="part,completed_steps,saved_step,time_s,dt_s,post_open_by_completed_step,target_time_s,forced_final","Original eight-column plan schema differs");
  std::vector<Tick> out;while(std::getline(in,line)){if(!line.empty()&&line.back()=='\r')line.pop_back();const auto f=Tokens(line);Need(f.size()==8,"Incomplete plan row");
    Tick t{UInt(f[0]),UInt(f[1]),UInt(f[2]),Number(f[3]),Number(f[4]),UInt(f[7])!=0};Need(t.part==out.size()&&t.dt>0&&UInt(f[7])<=1&&UInt(f[5])<=1,"Plan identity/dt/flags differ");
    Need(t.saved==(t.completed?t.completed-1:0),"Original zero-based saved Step differs");Number(f[6]);
    if(out.empty())Need(t.completed==0&&Bits(t.time,0.),"Plan must begin at actual zero");
    else Need(t.completed>out.back().completed&&t.time>out.back().time&&Bits(t.dt,out.back().dt),"Plan step/time failed to advance or locked dt changed");out.push_back(t);
  }Need(in.eof()&&out.size()==count,"Declared original plan frame count differs");return out;
}
static bool Same(const Tick& a,const Tick& b){return a.completed==b.completed&&a.saved==b.saved&&Bits(a.time,b.time)&&Bits(a.dt,b.dt);}
static void Header(JPartDataBi4& f,unsigned part,const Tick& t){
  Need(f.GetNpiece()==1&&f.GetPiece()==0&&f.Get_Npok()==Total&&!f.Get_Nout()&&f.Get_CaseNp()==Total&&f.Get_CaseNfluid()==Soil&&f.Get_CaseNfixed()==Fixed&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat(),"Native1040/1000/40 owner/count/exclusion differs");
  Need(f.Get_Data2d()&&f.Get_Data2dPosY()==0&&!f.Get_Symmetry()&&!f.Get_Splitting()&&!f.Get_NpDynamic()&&!f.Get_ReuseIds()&&f.Get_PeriMode()==PERI_X,"Outside fixed X-periodic case02 scope");
  Need(f.Get_Dp()==.01&&f.Get_H()==double(float(.018))&&f.Get_Rhop0()==2100.,"Original native geometry/reference density differs");
  Need(f.GetData()->GetItemsCount()==1&&f.GetData()->GetArraysCount()==0&&f.GetPart()->GetItemsCount()==0&&f.ArraysCount()==22,"Extra/missing native hierarchy or typed arrays");
  Metadata(f,0);auto* p=f.GetPart();Need(p->ExistsValue("Cpart",DatUint)&&p->GetvUint("Cpart")==part,"Original Cpart differs");
  Need(p->ExistsValue("TimeStep",DatDouble)&&p->ExistsValue("Step",DatUint)&&p->ExistsValue("SymplecticDtPre",DatDouble)&&p->ExistsValue("dterror",DatDouble),"Original typed clock28 absent");
  Need(Bits(f.Get_TimeStep(),t.time)&&f.Get_Step()==t.saved&&Bits(p->GetvDouble("SymplecticDtPre"),t.dt),"Actual native time/Step/dt differs from its untouched plan");
  const double error=p->GetvDouble("dterror");Need(std::isfinite(error)&&(part?error!=-DBL_MAX&&error<=1e-14:(error==-DBL_MAX||error<=1e-14)),"Original signed necessary-step interval failed; no abs/mask");
}
template<class T> static void Append(Bytes& b,const T& x){const auto* p=reinterpret_cast<const unsigned char*>(&x);b.insert(b.end(),p,p+sizeof(T));}
static Bytes Clock(JPartDataBi4& f){Bytes b;Append(b,f.Get_TimeStep());Append(b,f.Get_Step());Append(b,f.GetPart()->GetvDouble("SymplecticDtPre"));Append(b,f.GetPart()->GetvDouble("dterror"));Need(b.size()==28,"Clock payload is not28bytes");return b;}
template<class T> static Counts Array(unsigned part,const char* name,TpData type,const std::vector<T>& old,const std::vector<T>& fresh,const Native& a,const Native& b,std::ofstream& csv){
  Need(old.size()==Total&&fresh.size()==Total,"Incomplete original typed array");Counts c;c.bytes=std::uint64_t(Total)*sizeof(T);std::uint64_t elements=0;long firstId=-1,firstByte=-1;
  for(unsigned id=0;id<Total;id++){const auto* x=reinterpret_cast<const unsigned char*>(&old[a.slot[id]]);const auto* y=reinterpret_cast<const unsigned char*>(&fresh[b.slot[id]]);bool different=false;
    for(size_t j=0;j<sizeof(T);j++)if(x[j]!=y[j]){c.different++;different=true;if(firstId<0){firstId=long(id);firstByte=long(j);}}elements+=different;}
  csv<<part<<','<<name<<','<<unsigned(type)<<','<<Total<<','<<sizeof(T)<<','<<c.bytes<<','<<c.different<<','<<elements<<','<<firstId<<','<<firstByte<<'\n';return c;
}
static Counts Arrays(unsigned part,const Native& a,const Native& b,std::ofstream& csv){Counts c;
#define TPI_RAW(name,type,member) {const auto x=Array(part,name,type,a.member,b.member,a,b,csv);c.bytes+=x.bytes;c.different+=x.different;}
  TPI_RAW("Idp",DatUint,ids);TPI_RAW("Posd",DatDouble3,pos);TPI_RAW("Vel",DatFloat3,vel);TPI_RAW("Rhop",DatFloat,rhop);
  TPI_RAW("Sigma_kk",DatFloat3,legacykk);TPI_RAW("Sigma_ij",DatFloat3,legacyij);TPI_RAW("SigmaState_kk",DatDouble3,sk);TPI_RAW("SigmaState_ij",DatDouble3,si);
  TPI_RAW("Kplastic",DatFloat,plastic);TPI_RAW("FSType",DatUint,fstype);TPI_RAW("FSNormal",DatFloat3,normal);TPI_RAW("HydroMechLoadAce",DatFloat3,load);
  TPI_RAW("PorePress",DatFloat,p);TPI_RAW("PorePress0",DatFloat,p0);TPI_RAW("ExcessPorePress",DatFloat,excess);
  TPI_RAW("PoroVolumeRatio",DatDouble,j);TPI_RAW("PoroPorosity",DatDouble,n);TPI_RAW("PoroThetaLastStage",DatDouble,theta);TPI_RAW("PoroCurrentVolume",DatDouble,volume);TPI_RAW("PoroMixtureDensity",DatDouble,rho);TPI_RAW("PoroHydraulicConductivity",DatDouble,k);TPI_RAW("PosDiv",DatFloat,posdiv);
#undef TPI_RAW
  Need(c.bytes==std::uint64_t(Total)*212u,"All22 native-array byte scope differs");return c;
}
static bool Compare(const fs::path& oldArg,const fs::path& newArg,const fs::path& oldPlan,const fs::path& newPlan,unsigned oldCount,unsigned newCount,unsigned shared,const fs::path& outArg){
  Need(shared>0&&shared<=(std::min)(oldCount,newCount),"Explicit nonempty common-prefix count required");
  const auto old=fs::canonical(oldArg),fresh=fs::canonical(newArg),wanted=fs::absolute(outArg).lexically_normal();
  Need(!fs::equivalent(old,fresh)&&!fs::exists(wanted),"Distinct immutable raw inputs and fresh output required");
  const auto out=fs::canonical(wanted.parent_path())/wanted.filename();for(auto p=out.parent_path();;p=p.parent_path()){Need(!fs::equivalent(p,old)&&!fs::equivalent(p,fresh),"Output must stay outside both raw directories");if(p==p.parent_path())break;}
  Sequence(old,oldCount);Sequence(fresh,newCount);const auto aplan=Plan(oldPlan,oldCount),bplan=Plan(newPlan,newCount);
  for(unsigned p=0;p<shared;p++)Need(Same(aplan[p],bplan[p]),"Declared prefix includes different actual saved steps/times");
  Need(shared==(std::min)(oldCount,newCount)||!Same(aplan[shared],bplan[shared]),"Declared prefix was shortened despite a further real shared frame");
  Need(fs::create_directory(out),"Fresh comparison directory creation failed");std::ofstream csv(out/"arrays.csv");Need(bool(csv),"Per-array difference CSV open failed");
  csv<<"part,array,native_type,count,element_bytes,compared_bytes,different_bytes,different_elements,first_different_native_id,first_different_element_byte\n";
  Counts total;std::uint64_t clockDiff=0;unsigned frames=0;bool complete=false;std::string error;
  try{for(unsigned part=0;part<shared;part++){
    JPartDataBi4 of,nf;of.LoadFilePart(old.string(),part,0,1);nf.LoadFilePart(fresh.string(),part,0,1);Header(of,part,aplan[part]);Header(nf,part,bplan[part]);
    const auto a=Load(of,Total,0),b=Load(nf,Total,0);const auto c=Arrays(part,a,b,csv);total.bytes+=c.bytes;total.different+=c.different;
    const auto x=Clock(of),y=Clock(nf);std::uint64_t different=0;long first=-1;for(size_t j=0;j<x.size();j++)if(x[j]!=y[j]){different++;if(first<0)first=long(j);}clockDiff+=different;
    csv<<part<<",__clock28__,-1,1,28,28,"<<different<<','<<(different?1:0)<<",-1,"<<first<<'\n';frames++;
  }complete=true;}catch(const std::exception& e){error=e.what();}catch(const std::string& e){error=e;}catch(const char* e){error=e?e:"Native loader exception";}catch(...){error="Unknown native comparison exception";}
  csv.flush();Need(bool(csv),"Per-array CSV flush failed");const bool passed=complete&&!total.different&&!clockDiff;
  std::ofstream summary(out/"completion.json");Need(bool(summary),"Fresh summary open failed");summary<<std::setprecision(17)
    <<"{\"stage\":\"upl_tpi_raw22_compare_r1\",\"passed\":"<<(passed?"true":"false")<<",\"complete\":"<<(complete?"true":"false")
    <<",\"old_data\":"<<Json(old.string())<<",\"new_data\":"<<Json(fresh.string())<<",\"old_declared_frames\":"<<oldCount<<",\"new_declared_frames\":"<<newCount
    <<",\"expected_shared_frames\":"<<shared<<",\"frames_compared\":"<<frames<<",\"native_IDs_per_frame\":1040,\"soil_IDs\":1000,\"fixed_IDs\":40,\"arrays_per_frame\":22"
    <<",\"native_array_bytes_per_frame\":220480,\"native_array_bytes_compared\":"<<total.bytes<<",\"native_array_different_bytes\":"<<total.different
    <<",\"clock_bytes_per_frame\":28,\"clock_bytes_compared\":"<<std::uint64_t(frames)*28<<",\"clock_different_bytes\":"<<clockDiff
    <<",\"decoded_typed_values_compared_by_native_ID\":true,\"BI4_container_or_slot_order_bit_identity_claimed\":false,\"all22_actual_arrays_including_PosDiv_V_rho_k\":true"
    <<",\"initial_and_noninitial_signed_dterror_all_bits_included\":true,\"entire_BI4_metadata_compared\":false,\"original_counts_headers_forced_final_unchanged\":true"
    <<",\"old_uncompared_frames\":"<<oldCount-shared<<",\"new_uncompared_frames\":"<<newCount-shared<<",\"new_first_unshared_forced\":"<<(shared<newCount&&bplan[shared].forced?"true":"false")
    <<",\"new_first_unshared_completed_step\":"<<(shared<newCount?bplan[shared].completed:0)<<",\"old_first_unshared_completed_step\":"<<(shared<oldCount?aplan[shared].completed:0)
    <<",\"input_files_modified\":false,\"full_native_exports_created\":false,\"solver_or_GenCase_launched\":false,\"SHA_scans\":0,\"physical_acceptance\":false,\"error\":"<<Json(error)<<"}\n";
  summary.flush();Need(bool(summary),"Comparison summary flush failed");return passed;
}
}
int main(int argc,char** argv){try{Need(argc==10&&std::string(argv[1])=="--compare","Use --compare OLD_DATA NEW_DATA OLD_PLAN NEW_PLAN OLD_COUNT NEW_COUNT SHARED_COUNT FRESH_OUT");return tpiraw22::Compare(argv[2],argv[3],argv[4],argv[5],tpiraw22::UInt(argv[6]),tpiraw22::UInt(argv[7]),tpiraw22::UInt(argv[8]),argv[9])?0:1;}
catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<(e?e:"Native comparison exception")<<'\n';return 1;}catch(...){std::cerr<<"Raw22 comparison failed; preserve partials\n";return 2;}}

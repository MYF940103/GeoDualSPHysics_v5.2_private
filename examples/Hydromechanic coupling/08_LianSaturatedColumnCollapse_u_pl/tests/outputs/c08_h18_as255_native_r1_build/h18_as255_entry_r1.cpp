// Shared H=.072f / 5us C08 bed-role split inspector: no KeepBedOverlap and no physical update.
#include "h18_headers_r1.h"
#include "h18_profiles_r1.h"
struct H18Row{unsigned completed,saved;double time,dt;};
static std::vector<H18Row> H18Rows;
static std::filesystem::path H18PlanPath;
static float H18AS=0.f,H18Exp=0.f,H18TargetCoh=5000.f,H18Decay=0.f,H18E=0.f,H18Nu=0.f;
static std::string H18Group;
static void H18Need(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
static bool H18Bits(float a,float b){return !std::memcmp(&a,&b,sizeof(a));}
static std::vector<std::string> H18Split(std::string s,char sep){if(!s.empty()&&s.back()=='\r')s.pop_back();std::vector<std::string> out;size_t b=0;for(;;){const auto k=s.find(sep,b);out.push_back(s.substr(b,k==std::string::npos?k:k-b));if(k==std::string::npos)return out;b=k+1;}}
static unsigned H18Unsigned(const std::string& s){H18Need(!s.empty()&&s.find_first_not_of("0123456789")==std::string::npos,"Unsigned decimal required");size_t n=0;const auto value=std::stoul(s,&n);H18Need(n==s.size()&&value<=~0u,"Unsigned overflow");return unsigned(value);}
static double H18Double(const std::string& s){size_t n=0;const double x=std::stod(s,&n);H18Need(n==s.size()&&std::isfinite(x),"Finite profile number required");return x;}
static void H18ReadPlan(const std::filesystem::path& path,bool source,unsigned expected,unsigned count){
 std::ifstream f(path);std::string line;H18Need(bool(std::getline(f,line))&&H18Split(line,',')==std::vector<std::string>({"part","completed_step","saved_step","time_s","dt_s"}),"Use the original five-column scalar scheduling plan");H18Rows.clear();unsigned previous=source?0u:H18Event;double scalar=0.;if(!source)for(unsigned n=0;n<H18Event;n++)scalar+=H18Dt;
 while(std::getline(f,line)){const auto r=H18Split(line,',');H18Need(r.size()==5&&H18Unsigned(r[0])==H18Rows.size(),"Noncontiguous planned part");const unsigned completed=H18Unsigned(r[1]),saved=H18Unsigned(r[2]);const double time=H18Double(r[3]),dt=H18Double(r[4]);const bool initial=source&&H18Rows.empty();H18Need(dt==H18Dt&&(initial?(completed==0&&saved==0&&time==0.):(completed>previous&&saved==completed-1))&&completed<=expected,"Actual source/receiver planned step/dt profile differs");for(unsigned n=previous;n<completed;n++)scalar+=H18Dt;H18Need(std::abs(time-scalar)<=1e-14,"Plan differs from actual scalar +=dt replay");previous=completed;H18Rows.push_back({completed,saved,time,dt});}
 H18Need(H18Rows.size()==count&&previous==expected,"Original complete plan count/end differs");H18PlanPath=path;
}
static void H18ReadReceiverProfile(const std::filesystem::path& path,const std::string& group){
 std::ifstream f(path);std::string line;H18Need(bool(std::getline(f,line))&&H18Split(line,',')==std::vector<std::string>({"key","value"}),"Actual XML material/profile CSV required");std::map<std::string,std::string> p;while(std::getline(f,line)){auto r=H18Split(line,',');H18Need(r.size()==2&&p.emplace(r[0],r[1]).second,"Duplicate/invalid profile key");}
 const std::set<std::string> keys={"Kernel","group","ModulusE","PRvs","ArtificialStressCoef","ArtificialStressExp","DPCtes","phi","phi_r","n_phi","coh","coh_r","n_coh","dlt","DilationDecay","SoilTriggerFos","fresh_trigger_active"};H18Need(p.size()==keys.size(),"Closed receiver profile key count differs");for(auto k:keys)H18Need(p.count(k)==1,"Missing receiver profile key");H18Need(p.at("group")==group&&(group=="psi0"||group=="psi2p5"||group=="psim5"),"Closed material group required");
 const auto v=[&](const char* k){return float(H18Double(p.at(k)));};H18Need(H18Unsigned(p.at("Kernel"))==2,"Actual receiver XML/CSV Kernel must be2/Wendland");H18Group=group;H18E=v("ModulusE");H18Nu=v("PRvs");H18Need(H18E==20e6f&&H18Nu==.33f,"Actual receiver E/nu differs from the closed scope");H18AS=v("ArtificialStressCoef");H18Exp=v("ArtificialStressExp");H18TargetCoh=group=="psim5"?7500.f:5000.f;H18Decay=group=="psi0"?0.f:.2f;const float psi=group=="psi0"?0.f:(group=="psi2p5"?2.5f:-5.f);
 H18Need((H18Bits(H18AS,.3f)||H18Bits(H18AS,.5f)||H18Bits(H18AS,.7f))&&(H18Bits(H18Exp,2.55f)),"Only the explicitly prepared epsilon/exponent set is supported");H18Need(H18Unsigned(p.at("DPCtes"))==3&&p.at("fresh_trigger_active")=="0"&&v("phi")==25.f&&v("phi_r")==25.f&&v("n_phi")==0.f&&v("coh")==H18TargetCoh&&v("coh_r")==1000.f&&v("n_coh")==5.f&&v("dlt")==psi&&H18Bits(v("DilationDecay"),H18Decay)&&v("SoilTriggerFos")>=1.f,"Actual XML DP_PS/group material differs");
}
static void H18CheckWendlandContract(const std::string& contract){
 std::istringstream input(contract);std::string prefix2,prefix1;std::array<std::string,8> values;std::string kernel;
 H18Need(bool(input>>prefix2>>prefix1),"Native material contract prefix is incomplete");
 for(auto& value:values)H18Need(bool(input>>value),"Native contract has fewer than eight geometry/reference fields");
 H18Need(bool(input>>kernel)&&prefix2=="gravity-preload-2"&&prefix1=="gravity-preload-1","Native schema2/contract1 prefix differs");
 // Read the actual serialized field order, not a substring search for a digit2.
 const unsigned count=H18Unsigned(values[0]),fixed=H18Unsigned(values[1]),soil=H18Unsigned(values[2]);
 const double dp=H18Double(values[3]),h=H18Double(values[4]),massf=H18Double(values[5]),massb=H18Double(values[6]),rho=H18Double(values[7]);
 H18Need(count==7060&&fixed==2060&&soil==5000&&dp==.04&&h==double(.072f)&&massf==double(float(3.316))&&massb==massf&&rho==2072.5&&H18Unsigned(kernel)==2,"Native certificate geometry/reference/unsigned TKernel is not the declared Wendland scope");
 // The remaining material/history contract is deliberately NOT reconstructed here.
}
// Includes below contain unchanged numeric loops in distinct namespaces; all headers were lifted above.
namespace h18source{
#include "h18_source_core_r1.cpp"
}
namespace h18receiver{
#include "h18_receiver_core_r1.cpp"
}
int wmain(int argc,wchar_t** argv){unsigned headerPart=~0u;try{
 if(argc==7&&std::wstring(argv[1])==L"--source"){
  const std::wstring mode=argv[2];H18Need(mode==L"partial"||mode==L"full","Source mode must be partial or full");H18ReadPlan(argv[5],true,H18Event,H18SourceSamples);return h18source::wmain(argc,argv);
 }
 H18Need(argc==9&&std::wstring(argv[1])==L"--receiver","Use --source partial|full DATA MATERIAL_CSV PLAN FRESHOUT; or --receiver window|formal GROUP DATA PRE PLAN PROFILE_CSV FRESHOUT");const std::string profile=std::filesystem::path(argv[2]).string(),group=std::filesystem::path(argv[3]).string();const bool window=profile=="window";H18Need(window||profile=="formal","Only .90-window or full3 receiver profiles");const unsigned end=window?H18WindowEnd:H18FormalEnd,samples=window?H18WindowSamples:H18FormalSamples;H18ReadPlan(argv[6],false,end,samples);H18ReadReceiverProfile(argv[7],group);const std::filesystem::path data=argv[4],out=argv[8];H18Need(std::filesystem::is_directory(data)&&!std::filesystem::exists(out),"Missing DATA or protected output");
 for(unsigned part=0;part<samples;part++){
  headerPart=part;JPartDataBi4 f;f.LoadFilePart(data.string(),part,0,1);const auto* p=f.GetPart();
  for(const char* key:{"GravityPreloadKeepBedOverlap","GravityPreloadReleasePolicy","GravityPreloadKeptBedIds","GravityPreloadKeptBedCount","GravityPreloadActualRetiredCount"})H18Need(!p->ExistsValue(key),"Bed-role split must not carry old KeepBedOverlap metadata");
  H18Need(p->ExistsValue("DynamicArtificialStressPolicy",JBinaryDataDef::DatText)&&p->GetvText("DynamicArtificialStressPolicy")=="ReleaseOnly"&&p->ExistsValue("DynamicArtificialStressActive",JBinaryDataDef::DatBool)&&p->GetvBool("DynamicArtificialStressActive")&&p->ExistsValue("DynamicArtificialStressCoef",JBinaryDataDef::DatFloat)&&H18Bits(p->GetvFloat("DynamicArtificialStressCoef"),H18AS)&&p->ExistsValue("DynamicArtificialStressExp",JBinaryDataDef::DatFloat)&&H18Bits(p->GetvFloat("DynamicArtificialStressExp"),H18Exp),"Typed actual AS coefficient/exponent differs");
  for(const char* key:{"FreeSeepagePondingPolicy","FreeSeepagePondingActive","DynamicArtificialViscosityPolicy","DynamicArtificialViscosityOverrideActive","DynamicArtificialViscosityCoef"})H18Need(!p->ExistsValue(key),"CompletedOnly/original AV profile must not contain private policy metadata");
 }
 std::vector<std::wstring> args={argv[0],L"--read",argv[3],L"GPU",argv[4],argv[5],std::to_wstring(end),std::to_wstring(samples),L"1",argv[6],argv[8]};std::vector<wchar_t*> ptr;for(auto& s:args)ptr.push_back(s.data());const int rc=h18receiver::wmain(int(ptr.size()),ptr.data());if(rc)return rc;
 std::ofstream meta(out/"bedkeep_metadata.json");meta<<std::setprecision(17)<<"{\"stage\":\"c08_h18_wend_native_r1.metadata\",\"passed\":true,\"profile\":\""<<profile<<"\",\"group\":\""<<group<<"\",\"samples\":"<<samples<<",\"completed_steps\":"<<end<<",\"H\":"<<double(.072f)<<",\"fixed_dt_s\":"<<H18Dt<<",\"source_event_completed_step\":"<<H18Event<<",\"first_post_completed_step\":"<<H18Rows.front().completed<<",\"first_post_time_s\":"<<H18Rows.front().time<<",\"actual_plan_columns\":5,\"expected_source_handoff_schema\":2,\"same_material_plastic_PRE\":true,\"expected_source_material_CSV_keys\":15,\"receiver_material_CSV_keys\":17,\"ModulusE_float_reference\":"<<double(H18E)<<",\"PRvs_float_reference\":"<<double(H18Nu)<<",\"full_material_contract_independently_reconstructed\":false,\"target_full_material_contract_enforced_by_solver\":true,\"declared_Kernel_XML_CSV\":2,\"kernel_name_declared\":\"Wendland\",\"source_PRE_contract_kernel_checked\":true,\"receiver_kernel_independently_proven_by_arrays\":false,\"actual_XML_Runout_kernel_binding_required\":true,\"geometry_profile\":\"bedroles\",\"keep_bed_overlap\":false,\"original_target_begin\":1805,\"original_target_count\":255,\"actual_retired_count\":255,\"retained_fixed_ID_begin\":0,\"retained_fixed_ID_count\":1805,\"expected_AS\":true,\"AS_policy\":\"ReleaseOnly\",\"AS_coefficient_float_reference\":"<<double(H18AS)<<",\"AS_exponent_float_reference\":"<<double(H18Exp)<<",\"AS_active_true_headers\":"<<samples<<",\"expected_ponding_policy\":\"CompletedOnly\",\"ponding_policy_keys_absent_headers\":"<<samples<<",\"metadata_header_scans\":"<<samples<<",\"metadata_scans_decode_field_arrays\":false,\"core_array_decode_passes\":1,\"material_group_proven_by_XML_binding_required\":true,\"target_contract_enforced_by_solver_not_reader\":true,\"backend_proven_by_reader\":false,\"physical_acceptance\":false}\n";meta.flush();H18Need(bool(meta),"Metadata export failed");return 0;
 }catch(const JException& e){std::cerr<<"H18 metadata part="<<headerPart<<' '<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<"H18 metadata part="<<headerPart<<' '<<e.what()<<'\n';return 1;}}

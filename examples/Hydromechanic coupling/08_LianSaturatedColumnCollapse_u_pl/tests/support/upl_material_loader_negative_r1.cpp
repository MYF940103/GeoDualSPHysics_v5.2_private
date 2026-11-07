// Host-only real PRE and generic PART loader policy checks. No solver or restart integration.
#include "JGravityPreloadState.h"
#include "JPartsLoad4.h"
#include "JException.h"
#include "JAppInfo.h"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <map>
#include <string>
#include <vector>
JAppInfo AppInfo("UplMaterialLoaderNegative","r1","07-11-2026");
namespace fs=std::filesystem;
using D=JBinaryDataDef;
static void Need(bool b,const std::string& s){if(!b)throw std::runtime_error(s);}
static std::vector<char> Bytes(const fs::path& p){std::ifstream f(p,std::ios::binary);Need(bool(f),"Cannot read immutable file");return {(std::istreambuf_iterator<char>(f)),std::istreambuf_iterator<char>()};}
struct Array {std::string name;D::TpData type;unsigned count;std::vector<unsigned char> bytes;};
static std::vector<Array> Payload(const fs::path& path){
  JPartDataBi4 f;f.LoadFilePart(path.parent_path().string(),10,0,1);std::vector<Array> out;
  for(unsigned i=0;i<f.ArraysCount();i++){const auto* a=f.GetArray(f.ArrayName(i));const unsigned n=a->DataInPointer()?a->GetCount():a->GetFileDataCount();Array x{a->GetName(),a->GetType(),n,std::vector<unsigned char>(std::size_t(n)*D::SizeOfType(a->GetType()))};Need(a->GetDataCopy(n,x.bytes.data())==n,"Incomplete fixture array");out.push_back(std::move(x));}return out;
}
static bool SamePayload(const std::vector<Array>& a,const std::vector<Array>& b,bool renamed=false){
  if(a.size()!=b.size())return false;for(unsigned i=0;i<a.size();i++){
    const std::string expected=renamed&&a[i].name=="Kplastic"?"Kplastic_removed_for_negative_test":a[i].name;
    if(expected!=b[i].name||a[i].type!=b[i].type||a[i].count!=b[i].count||a[i].bytes!=b[i].bytes)return false;
  }return true;
}
static JGravityPreloadState Import(const fs::path& path){
  JPartDataBi4 f;f.LoadFilePart(path.parent_path().string(),10,0,1);const auto* p=f.GetPart();Need(p->ExistsValue("GravityPreloadHandoffContract",D::DatText),"True source contract absent");JGravityPreloadState state;
  state.Load(path.string(),p->GetvText("GravityPreloadHandoffContract"),7060,2060,380,.00095,.0000025,5000.f,double(float(.35)),2072.5,1000.,double(float(3.316)),double(float(.0002)),2.);return state;
}
static fs::path Fixture(const fs::path& root,const std::string& name,const fs::path& source,unsigned mutation){
  const auto dir=root/name;Need(fs::create_directory(dir),"Fresh case fixture required");const auto path=dir/"Part_0010.bi4";Need(!fs::exists(path),"Fixture already exists");
  JBinaryData data;data.LoadFile(source.string(),"JPartDataBi4",true);auto* p=data.GetItem("PART_0010");Need(p,"Actual Part0010 item absent");
  if(mutation==1||mutation==2){p->RemoveValue("MaterialLawVersion");if(mutation==1)p->SetvUint("MaterialLawVersion",3);else p->SetvFloat("MaterialLawVersion",2.f);p->SetvUint("MaterialReturn",1);}
  if(mutation==3)p->SetvUint("GravityPreloadHandoffSchema",99);
  if(mutation==4){auto* k=p->GetArray("Kplastic");Need(k&&k->GetType()==D::DatFloat,"Original typed kappa absent");k->SetName("Kplastic_removed_for_negative_test");}
  if(mutation==5){auto* k=p->GetArray("Kplastic");Need(k&&k->GetType()==D::DatFloat&&k->GetCount()==7060,"Full source history required");std::vector<float> values(7060);Need(k->GetDataCopy(7060,values.data())==7060,"Missing copied kappa");JPartDataBi4 f;f.LoadFilePart(source.parent_path().string(),10,0,1);std::vector<unsigned> ids(7060);Need(f.Get_Idp(7060,ids.data())==7060,"Missing source IDs");unsigned slot=~0u;for(unsigned i=0;i<7060;i++)if(ids[i]==2060)slot=i;Need(slot!=~0u,"Required soil sentinel ID absent");values[slot]=.125f;k->SetData(7060,values.data(),false);}
  data.SaveFile(path.string(),true,true);return path;
}
static void Text(std::ostream& o,const std::string& s){o<<'"';for(char c:s){if(c=='"'||c=='\\')o<<'\\';if(c=='\n')o<<"\\n";else if(c=='\r')o<<"\\r";else if(c=='\t')o<<"\\t";else o<<c;}o<<'"';}
struct Row {std::string name,first_cause;bool rejected,payload_unchanged,source_unchanged;};
int main(int argc,char** argv){try{
  Need(argc==5&&std::string(argv[1])=="--pre"&&std::string(argv[3])=="--out","Use --pre CERTIFIED_NEW_CPU_PRE --out FRESH_DIR");const fs::path source=fs::canonical(argv[2]),out=argv[4];
  Need(source.filename()=="Part_0010.bi4"&&!fs::exists(out)&&fs::is_directory(out.parent_path()),"Genuine Part0010 and fresh output required");const auto original=Bytes(source);const auto base=Payload(source);Need(base.size()==22,"Original22 typed arrays required");const auto control=Import(source);Need(control.MaterialLawVersion==2&&control.CompletedStep==380&&control.Count==7060&&control.Kplastic.size()==7060,"Passed new-source material schema/registry required");for(float k:control.Kplastic)Need(k==0.f,"Source qualification is not elastic");Need(fs::create_directory(out),"Cannot create fresh test output");
  std::vector<Row> rows;rows.push_back({"qualified_version2_positive_control","",false,true,Bytes(source)==original});
  const char* names[]={"unknown_version_no_legacy_fallback","wrong_type_no_legacy_fallback","unknown_handoff_schema","required_kappa_name_absent","generic_version2_history_refused"};
  const char* expected[]={"Unknown/untyped material-law version","Unknown/untyped material-law version","Missing/incompatible certified elastic handoff schema/contract","Array 'Kplastic' is not available","Material-law PART restart is not supported"};
  for(unsigned mutation=1;mutation<=5;mutation++){
    const auto fixture=Fixture(out,"n"+std::to_string(mutation),source,mutation);const auto fixture_before_bytes=Bytes(fixture);const auto before=Payload(fixture);Need(mutation==5||SamePayload(base,before,mutation==4),"Metadata/name-only fixture changed array payload");
    if(mutation==5){unsigned changed=0;for(unsigned i=0;i<base.size();i++)if(base[i].bytes!=before[i].bytes){Need(base[i].name=="Kplastic"&&base[i].count==7060&&before[i].count==7060,"Generic sentinel changed another array");changed++;}Need(changed==1,"Nonzero kappa history witness is vacuous");const auto it=std::find_if(before.begin(),before.end(),[](const Array& a){return a.name=="Kplastic";});Need(it!=before.end()&&it->bytes.size()==7060*sizeof(float),"Serialized generic kappa missing");unsigned nonzero=0;for(unsigned q=0;q<7060;q++){float k=0;std::memcpy(&k,it->bytes.data()+q*sizeof(float),sizeof(float));if(k!=0.f){Need(k==.125f,"Unexpected serialized history sentinel");nonzero++;}}Need(nonzero==1,"Actual generic fixture must contain exactly one nonzero kappa");}
    bool rejected=false;std::string cause;
    try{if(mutation==5){JPartsLoad4 loader(false);loader.LoadParticles(fixture.parent_path().string(),"unused",10,fixture.parent_path().string());}else{const auto ignored=Import(fixture);(void)ignored;}}
    catch(const JException& e){rejected=true;cause=e.ToStr();}catch(const std::exception& e){rejected=true;cause=e.what();}
    Need(rejected&&cause.find(expected[mutation-1])!=std::string::npos,"Actual first rejection cause differs: "+cause);const bool same=SamePayload(before,Payload(fixture)),originalsame=Bytes(source)==original;Need(same&&Bytes(fixture)==fixture_before_bytes&&originalsame,"Loader changed fixture or immutable original bytes");rows.push_back({names[mutation-1],cause,rejected,same,originalsame});
  }
  Need(rows.size()==6,"Actual six-case coverage incomplete");std::ofstream cases(out/"cases.csv");cases<<"case,rejected,fixture_typed_payload_unchanged,original_whole_file_unchanged\n";for(const auto& r:rows)cases<<r.name<<','<<r.rejected<<','<<r.payload_unchanged<<','<<r.source_unchanged<<'\n';cases.flush();Need(bool(cases),"Case CSV failed");
  std::ofstream done(out/"completion.json");done<<"{\"stage\":\"upl_material_loader_negative_r1\",\"passed\":true,\"actual_cases\":6,\"qualified_positive_imports\":1,\"actual_PRE_rejections\":4,\"actual_generic_PART_rejections\":1,\"original_source_whole_file_unchanged\":true,\"fixture_payload_unchanged_after_calls\":true,\"fixture_whole_files_unchanged_after_calls\":true,\"generic_nonzero_kappa_fixture\":true,\"generic_rejected_before_history_copy_or_accepted_restart\":true,\"partial_loader_memory_state_not_inspected\":true,\"memory_atomic_restore_claimed\":false,\"solver_invocations\":0,\"physical_acceptance\":false,\"cases\":[";
  for(unsigned i=0;i<rows.size();i++){if(i)done<<',';done<<"{\"name\":";Text(done,rows[i].name);done<<",\"rejected\":"<<(rows[i].rejected?"true":"false")<<",\"actual_first_cause\":";Text(done,rows[i].first_cause);done<<'}';}done<<"]}\n";done.flush();Need(bool(done),"Completion failed");return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

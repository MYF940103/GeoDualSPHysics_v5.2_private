// Private fixed-owner C04 pressure-history round-trip, using the real BI4 serializer.
#include "JPartDataBi4.h"
#include "TpiPressureRow.h"
#include <algorithm>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs=std::filesystem;
using Def=JBinaryDataDef;
constexpr unsigned fixed=8, soil=37173, n=fixed+soil;
constexpr double step_dt=1.9073486328125e-6;
const std::string item_name="TpiPressureHistory";
struct Record{unsigned id;float previous,older,current;double last_prediction;};
static_assert(sizeof(Record)==24,"reference record");
static void need(bool condition,const char* message){if(!condition)throw std::runtime_error(message);}
template<class T> static bool same(T a,T b){return std::memcmp(&a,&b,sizeof(T))==0;}
static JBinaryData* part(JBinaryData& root,unsigned number=1){
  need(number<=1,"unsupported fixture part");
  JBinaryData* p=root.GetItem(number?"PART_0001":"PART_0000");need(p!=nullptr,"native PART absent");return p;
}
template<class T> static std::vector<T> array(JBinaryData& item,const char* name,Def::TpData type,unsigned count){
  const auto* a=item.GetArray(name);need(a && a->GetType()==type && a->GetCount()==count,"wrong array type/count or missing array");
  std::vector<T> v(count);need(a->GetDataCopy(count,v.data())==count,"short array");return v;
}
static std::vector<byte> bytes(JBinaryData& root){
  std::vector<byte> v(root.GetSizeData(true));need(root.SaveData(unsigned(v.size()),v.data(),true)==v.size(),"short serialization");return v;
}
static void require_owners(const std::vector<unsigned>& ids,unsigned first,unsigned last){
  need(ids.size()==last-first,"incomplete owner set");
  std::vector<bool> seen(last-first);
  for(unsigned id:ids){need(id>=first && id<last && !seen[id-first],"invalid or duplicate owner");seen[id-first]=true;}
}
static std::vector<Record> records(const fs::path& path){
  std::ifstream f(path,std::ios::binary);std::vector<Record> r(soil);
  need(bool(f.read((char*)r.data(),r.size()*sizeof(Record))) && f.peek()==EOF,"reference size");
  for(unsigned i=0;i<r.size();i++){
    const auto& x=r[i];need(x.id==fixed+i,"reference ID set");
    need(std::isfinite(x.previous) && std::isfinite(x.older) && std::isfinite(x.current),"reference pressures");
    double q=0;need(tpi_pressure::Predict(tpi_pressure::Predictor::Linear,x.previous,x.older,q)
      && same(q,x.last_prediction),"source-step predictor does not match observed round");
  }
  return r;
}
static void add_history(JBinaryData& root,const std::vector<Record>& r){
  auto& p=*part(root);
  need(!p.GetItem(item_name) && p.GetvUint("Step")==63 && same(p.GetvDouble("SymplecticDtPre"),step_dt)
    && same(p.GetvDouble("TimeStep"),64.*step_dt),"source clock or pre-existing payload");
  auto* h=p.CreateItem(item_name);
  h->SetvUint("Schema",1);h->SetvText("Scheme","P3_B_alpha_half_beta_zero");
  h->SetvText("RunCode",root.GetvText("RunCode"));h->SetvUint("CompletedUpdates",64);
  h->SetvDouble("PreviousTime",63.*step_dt);h->SetvDouble("SavedTime",p.GetvDouble("TimeStep"));
  h->SetvDouble("Dt",step_dt);h->SetvBool("Valid",true);
  // An independent order in the payload prevents even a sorted pressure file from accidentally passing a slot join.
  std::vector<unsigned> ids(soil);std::vector<float> values(soil);
  for(unsigned i=0;i<soil;i++){const auto& x=r[soil-1-i];ids[i]=x.id;values[i]=x.previous;}
  h->CreateArray("Idp",Def::DatUint,soil,ids.data(),false);
  h->CreateArray("PorePressPrev",Def::DatFloat,soil,values.data(),false);
}
enum class Policy{DefaultA,ExactHistory,ColdIfMissing};
enum class Origin{Disabled,Loaded,Cold};
struct Restore{Origin origin;std::vector<float> previous;};
static Restore read_history(JBinaryData& root,JBinaryData& p,const std::vector<unsigned>& id,const std::vector<float>& current,Policy policy){
  if(policy==Policy::DefaultA)return {Origin::Disabled,{}};
  need(root.GetvUint("Npiece")==1 && !root.GetvBool("NpDynamic") && !root.GetvBool("ReuseIds")
    && root.GetvUllong("CaseNfixed")==fixed && root.GetvUllong("CaseNfluid")==soil && !p.GetvUint("Nout")
    && p.GetvUint("Npok")==n && current.size()==n,"unsupported owner layout");
  require_owners(id,0,n);
  for(unsigned i=0;i<n;i++)if(id[i]>=fixed)need(std::isfinite(current[i]),"nonfinite current owner pressure");
  auto* h=p.GetItem(item_name);
  if(!h){
    need(policy==Policy::ColdIfMissing,"previous pressure history missing");
    return {Origin::Cold,current};
  }
  const double dt=p.GetvDouble("SymplecticDtPre"),saved=p.GetvDouble("TimeStep");
  need(h->GetvUint("Schema")==1 && h->GetvText("Scheme")=="P3_B_alpha_half_beta_zero" && h->GetvBool("Valid")
    && h->GetvText("RunCode")==root.GetvText("RunCode") && h->GetArraysCount()==2 && !h->GetItemsCount()
    && h->GetvUint("CompletedUpdates")==p.GetvUint("Step")+1 && p.GetvUint("Cpart")>0
    && std::isfinite(dt) && dt>0. && std::isfinite(saved) && same(h->GetvDouble("Dt"),dt)
    && same(h->GetvDouble("SavedTime"),saved) && same(h->GetvDouble("PreviousTime"),saved-dt),"incompatible history identity/clock");
  const auto owners=array<unsigned>(*h,"Idp",Def::DatUint,soil);
  const auto values=array<float>(*h,"PorePressPrev",Def::DatFloat,soil);
  require_owners(owners,fixed,n);
  std::vector<float> owner_values(soil);
  for(unsigned i=0;i<soil;i++){
    need(std::isfinite(values[i]),"nonfinite previous pressure");
    owner_values[owners[i]-fixed]=values[i];
  }
  std::vector<float> previous=current;
  for(unsigned i=0;i<n;i++)if(id[i]>=fixed)previous[i]=owner_values[id[i]-fixed];
  return {Origin::Loaded,std::move(previous)};
}
template<class F> static void rejected(F action){
  try{action();}catch(const std::exception&){return;}
  throw std::runtime_error("malformed history accepted");
}
static std::vector<float> initial_pressure(const fs::path& path){
  JBinaryData root;root.LoadFile(path.string(),"JPartDataBi4");auto& p=*part(root,0);
  const auto id=array<unsigned>(p,"Idp",Def::DatUint,n);const auto current=array<float>(p,"PorePress",Def::DatFloat,n);
  require_owners(id,0,n);auto cold=read_history(root,p,id,current,Policy::ColdIfMissing);
  need(cold.origin==Origin::Cold && !std::memcmp(current.data(),cold.previous.data(),n*sizeof(float)),"initial cold pressure");
  std::vector<float> by_id(n);for(unsigned i=0;i<n;i++)by_id[id[i]]=current[i];return by_id;
}
static void malformed(JBinaryData& restored,const std::vector<unsigned>& ids,const std::vector<float>& pressure,int mode){
  auto& p=*part(restored);auto& h=*p.GetItem(item_name);
  if(mode==0)h.SetvBool("Valid",false);
  if(mode==1)h.SetvUint("Schema",2);
  if(mode==2)h.SetvDouble("Dt",step_dt/2);
  if(mode==3)h.SetvDouble("PreviousTime",62.*step_dt);
  if(mode==4)h.SetvUint("CompletedUpdates",63);
  if(mode==5)h.SetvText("RunCode","wrong-run");
  if(mode==6)h.SetvText("Scheme","other");
  if(mode==7)h.RemoveArray("PorePressPrev");
  if(mode==8){h.RemoveArray("PorePressPrev");std::vector<double> z(soil);h.CreateArray("PorePressPrev",Def::DatDouble,soil,z.data(),false);}
  if(mode==9)h.GetArray("PorePressPrev")->SetData(soil-1,pressure.data(),false);
  if(mode==10 || mode==11){
    auto owners=array<unsigned>(h,"Idp",Def::DatUint,soil);owners[1]=mode==10?owners[0]:0;
    h.GetArray("Idp")->SetData(soil,owners.data(),false);
  }
  if(mode==12){
    auto vals=array<float>(h,"PorePressPrev",Def::DatFloat,soil);vals.back()=std::numeric_limits<float>::quiet_NaN();
    h.GetArray("PorePressPrev")->SetData(soil,vals.data(),false);
  }
  if(mode==13)h.RemoveValue("Schema");
  if(mode==14)h.SetvDouble("SavedTime",65.*step_dt);
  if(mode==15)h.SetvDouble("PreviousTime",std::nextafter(63.*step_dt,64.*step_dt));
  // A corrupted item remains observable after a real binary serialization and parse.
  auto packed=bytes(restored);JBinaryData reread;reread.LoadData(unsigned(packed.size()),packed.data());
  auto& q=*part(reread);
  for(auto policy:{Policy::ExactHistory,Policy::ColdIfMissing})rejected([&]{read_history(reread,q,ids,pressure,policy);});
  need(read_history(reread,q,ids,pressure,Policy::DefaultA).origin==Origin::Disabled,"A inspected corrupt B history");
}
static void run(const fs::path& b,const fs::path& a,const fs::path& refs,const fs::path& output){
  fs::create_directory(output);
  const auto r=records(refs);
  JBinaryData root;root.LoadFile((b/"Part_0001.bi4").string(),"JPartDataBi4");auto& p=*part(root);
  need(p.GetArraysCount()==22,"expected original 22 arrays");
  auto id=array<unsigned>(p,"Idp",Def::DatUint,n);auto pressure=array<float>(p,"PorePress",Def::DatFloat,n);
  const auto init=initial_pressure(b/"Part_0000.bi4");
  rejected([&]{read_history(root,p,id,pressure,Policy::ExactHistory);});
  const auto cold=read_history(root,p,id,pressure,Policy::ColdIfMissing);
  need(cold.origin==Origin::Cold && !std::memcmp(cold.previous.data(),pressure.data(),n*sizeof(float)),"explicit cold");
  const auto before=bytes(root);
  add_history(root,r);
  const auto output_file=output/"Part_0001.bi4";
  need(!fs::exists(output_file),"existing B file");root.SaveFile(output_file.string());
  JBinaryData restored;restored.LoadFile(output_file.string(),"JPartDataBi4");
  auto& q=*part(restored);
  auto verify=[&](const std::vector<unsigned>& who,const std::vector<float>& cur){
    auto result=read_history(restored,q,who,cur,Policy::ExactHistory);need(result.origin==Origin::Loaded,"history status");
    auto optional=read_history(restored,q,who,cur,Policy::ColdIfMissing);
    need(optional.origin==Origin::Loaded && !std::memcmp(optional.previous.data(),result.previous.data(),n*sizeof(float)),"valid history lost to cold restart");
    unsigned wrong_older=0,wrong_part0=0,wrong_cold=0;
    for(unsigned i=0;i<n;i++)if(who[i]>=fixed){
      const auto& x=r[who[i]-fixed];
      need(same(x.current,cur[i]) && same(x.previous,result.previous[i]),"round/native pressure mismatch by ID");
      double predicted=0;need(tpi_pressure::Predict(tpi_pressure::Predictor::Linear,cur[i],result.previous[i],predicted),"reloaded predictor rejected");
      const double reference=double(x.current)+.5*(double(x.current)-double(x.previous));
      need(same(predicted,reference) && same(tpi_pressure::WritePressure(predicted),float(reference)),"reloaded predictor bits");
      wrong_older+=!same(reference,double(x.current)+.5*(double(x.current)-double(x.older)));
      wrong_part0+=!same(reference,double(x.current)+.5*(double(x.current)-double(init[x.id])));
      wrong_cold+=!same(reference,double(x.current));
    }
    need(wrong_older && wrong_part0 && wrong_cold,"unidentifiable history oracle");
    return std::vector<unsigned>{wrong_older,wrong_part0,wrong_cold};
  };
  const auto differences=verify(id,pressure);
  std::reverse(id.begin(),id.end());std::reverse(pressure.begin(),pressure.end());
  std::rotate(id.begin(),id.begin()+137,id.end());std::rotate(pressure.begin(),pressure.begin()+137,pressure.end());
  need(verify(id,pressure)==differences,"slot permutation");
  for(int m=0;m<16;m++){JBinaryData changed(restored);malformed(changed,id,pressure,m);}
  auto bad_id=id;bad_id[1]=bad_id[0];rejected([&]{read_history(restored,q,bad_id,pressure,Policy::ExactHistory);});
  {
    JPartDataBi4 native;native.LoadFilePart(output.string(),1);
    need(native.ArraysCount()==22 && native.Get_Npok()==n && native.Get_Step()==63,"native PART reader");
    for(unsigned i=0;i<22;i++){
      const auto* ar=p.GetArray(i);const auto* other=native.GetPart()->GetArray(i);
      need(other->GetName()==ar->GetName() && other->GetType()==ar->GetType(),"native array identity");
      std::vector<byte> v(ar->GetCount()*Def::SizeOfType(ar->GetType()));
      need(other->GetDataCopy(ar->GetCount(),v.data())==ar->GetCount() && !std::memcmp(v.data(),ar->GetPointer(),v.size()),"native array payload");
    }
  }
  const unsigned root_meta=restored.GetValuesCount(),part_meta=q.GetValuesCount();
  q.RemoveItem(item_name);need(bytes(restored)==before,"original tree data or metadata changed");
  const auto stripped=output/"stripped.bi4";need(!fs::exists(stripped),"existing stripped file");
  restored.SaveFile(stripped.string());
  JBinaryData default_a;default_a.LoadFile((a/"Part_0001.bi4").string(),"JPartDataBi4");auto& ap=*part(default_a);
  const auto off=read_history(default_a,ap,{}, {},Policy::DefaultA);
  need(off.origin==Origin::Disabled && off.previous.empty() && !ap.GetItem(item_name),"unexpected history on A");
  const auto off_file=output/"default_A.bi4";need(!fs::exists(off_file),"existing A file");
  default_a.SaveFile(off_file.string());
  std::cout<<soil<<','<<root_meta<<','<<part_meta<<','<<differences[0]<<','<<differences[1]<<','<<differences[2]<<",16\n";
}
int main(int argc,char** argv){
  try{need(argc==5,"expected B-data A-data records.bin new-output-dir");run(argv[1],argv[2],argv[3],argv[4]);return 0;}
  catch(const std::exception& e){std::cerr<<e.what()<<'\n';}
  return 1;
}

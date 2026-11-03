// Offline comparison of two actual project-main PART sequences. Never runs a solver.
// Reuse only the retained neutral Native/Load definitions and real AppInfo object.
#define main RetainedHgNeutralDecoderMain
#include "upl_cpu_public_native_r1.cpp"
#undef main
#include <cstdint>
#include <sstream>

namespace hgraw {
constexpr unsigned Soil=1000,Fixed=40,Total=1040;
static_assert(sizeof(unsigned)==4&&sizeof(float)==4&&sizeof(double)==8,"Native clock28/array scalar widths differ");
static_assert(sizeof(tfloat3)==12&&sizeof(tdouble3)==24,"Native vector arrays contain unexpected padding");
using Bytes=std::vector<unsigned char>;
struct Value{TpData type;Bytes bytes;};
struct Counts{std::uint64_t bytes=0,different=0,metadata=0,metadataDifferent=0,excluded=0;unsigned frames=0;};
static std::string Json(const std::string& text){
  std::ostringstream out;out<<'"';for(unsigned char c:text){
    if(c=='"'||c=='\\')out<<'\\'<<char(c);
    else if(c<32)out<<"\\u00"<<std::hex<<std::setw(2)<<std::setfill('0')<<unsigned(c)<<std::dec;
    else out<<char(c);
  }out<<'"';return out.str();
}
static std::string Csv(const std::string& text){std::string out="\"";for(char c:text){if(c=='"')out+='"';out+=c;}return out+'"';}
static std::string Hex(const Bytes& bytes){std::ostringstream out;out<<std::hex<<std::setfill('0');for(unsigned char b:bytes)out<<std::setw(2)<<unsigned(b);return out.str();}
template<class T> static Bytes Packed(T value){const auto* p=reinterpret_cast<const unsigned char*>(&value);return Bytes(p,p+sizeof(T));}
template<class T> static void Append(Bytes& bytes,T value){const auto b=Packed(value);bytes.insert(bytes.end(),b.begin(),b.end());}
static std::uint64_t Difference(const Bytes& a,const Bytes& b){
  std::uint64_t n=a.size()>b.size()?a.size()-b.size():b.size()-a.size();for(size_t i=0;i<(std::min)(a.size(),b.size());i++)n+=a[i]!=b[i];return n;
}
static Value Scalar(JBinaryData& data,const std::string& key){
  const auto type=data.TypeOfValue(key);Bytes bytes;
  // Metadata CSV uses exact bytes of decoded typed values, not BI4 container bytes.
  switch(type){
    case JBinaryDataDef::DatText:{const auto text=data.GetvText(key);bytes.assign(text.begin(),text.end());break;}
    case JBinaryDataDef::DatBool:bytes=Packed(data.GetvBool(key));break;
    case JBinaryDataDef::DatChar:bytes=Packed(data.GetvChar(key));break;
    case JBinaryDataDef::DatUchar:bytes=Packed(data.GetvUchar(key));break;
    case JBinaryDataDef::DatShort:bytes=Packed(data.GetvShort(key));break;
    case JBinaryDataDef::DatUshort:bytes=Packed(data.GetvUshort(key));break;
    case JBinaryDataDef::DatInt:bytes=Packed(data.GetvInt(key));break;
    case JBinaryDataDef::DatUint:bytes=Packed(data.GetvUint(key));break;
    case JBinaryDataDef::DatLlong:bytes=Packed(data.GetvLlong(key));break;
    case JBinaryDataDef::DatUllong:bytes=Packed(data.GetvUllong(key));break;
    case JBinaryDataDef::DatFloat:{const auto v=data.GetvFloat(key);Need(Finite(v),"Nonfinite metadata: "+key);bytes=Packed(v);break;}
    case JBinaryDataDef::DatDouble:{const auto v=data.GetvDouble(key);Need(Finite(v),"Nonfinite metadata: "+key);bytes=Packed(v);break;}
    case JBinaryDataDef::DatInt3:bytes=Packed(data.GetvInt3(key));break;
    case JBinaryDataDef::DatUint3:bytes=Packed(data.GetvUint3(key));break;
    case JBinaryDataDef::DatFloat3:{const auto v=data.GetvFloat3(key);Need(Finite(v),"Nonfinite metadata: "+key);Append(bytes,v.x);Append(bytes,v.y);Append(bytes,v.z);break;}
    case JBinaryDataDef::DatDouble3:{const auto v=data.GetvDouble3(key);Need(Finite(v),"Nonfinite metadata: "+key);Append(bytes,v.x);Append(bytes,v.y);Append(bytes,v.z);break;}
    default:throw std::runtime_error("Unsupported native metadata type: "+key);
  }return{type,bytes};
}
static bool Excluded(bool header,const std::string& key){
  if(header)return key=="RunCode"||key=="Date"||key=="AppName"||key=="CaseName";
  return key=="RunTime"||key=="timesim"||key=="cpualloc"||key=="nctalloc"||key=="nctused"||key=="npalloc"||key=="npused";
}
static Counts Meta(unsigned part,bool header,JBinaryData& old,JBinaryData& fresh,std::ofstream& csv){
  std::map<std::string,bool> names;Counts c;
  for(unsigned i=0;i<old.GetValuesCount();i++)names[old.NameOfValue(i)]=true;
  for(unsigned i=0;i<fresh.GetValuesCount();i++)names[fresh.NameOfValue(i)]=true;
  for(const auto& item:names){
    const auto& key=item.first;const bool oa=old.ExistsValue(key),na=fresh.ExistsValue(key),skip=Excluded(header,key);
    const auto x=oa?Scalar(old,key):Value{JBinaryDataDef::DatNull,{}},y=na?Scalar(fresh,key):Value{JBinaryDataDef::DatNull,{}};
    const bool schema=oa&&na&&x.type==y.type,same=schema&&x.bytes==y.bytes;
    // Excluded values may change, but excluded key presence/type must remain equal.
    const bool passed=schema&&(skip||same);c.metadata++;c.metadataDifferent+=!passed;c.excluded+=skip;
    csv<<part<<','<<(header?"header":"PART")<<','<<Csv(key)<<','<<oa<<','<<na<<','<<unsigned(x.type)<<','<<unsigned(y.type)<<','<<Csv(Hex(x.bytes))<<','<<Csv(Hex(y.bytes))<<','<<skip<<','<<same<<','<<passed<<'\n';
  }return c;
}
static void Header(JPartDataBi4& f,unsigned part,bool dynamic){
  Need(f.GetNpiece()==1&&f.GetPiece()==0&&f.Get_Npok()==Total&&!f.Get_Nout()&&f.Get_CaseNp()==Total&&f.Get_CaseNfluid()==Soil&&f.Get_CaseNfixed()==Fixed&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat(),"Native count/identity/exclusion differs");
  Need(f.Get_Data2d()&&f.Get_Data2dPosY()==0&&!f.Get_Symmetry()&&!f.Get_Splitting()&&!f.Get_NpDynamic()&&!f.Get_ReuseIds()&&f.Get_PeriMode()==PERI_X,"Outside fixed native 2D X-periodic column scope");
  Need(f.GetData()->GetItemsCount()==1&&f.GetData()->GetArraysCount()==0&&f.GetPart()->GetItemsCount()==0,"Extra native hierarchy/arrays outside PART");
  Need(f.GetPart()->ExistsValue("Cpart",DatUint)&&f.GetPart()->GetvUint("Cpart")==part,"Native Cpart differs from sequence");
  Need(f.ArraysCount()==(dynamic?22u:15u),"Both raw inputs must contain exact original15 or native22 schema");
  Metadata(f,dynamic?0:-1); // OFF absence; ON bool/uint/uint/double constant-law metadata.
  const auto* p=f.GetPart();Need(p->ExistsValue("TimeStep",DatDouble)&&p->ExistsValue("Step",DatUint)&&p->ExistsValue("SymplecticDtPre",DatDouble)&&p->ExistsValue("dterror",DatDouble),"Native typed clock28 missing");
  Need(std::isfinite(f.Get_TimeStep())&&f.Get_TimeStep()>=0&&std::isfinite(p->GetvDouble("SymplecticDtPre"))&&p->GetvDouble("SymplecticDtPre")>0&&std::isfinite(p->GetvDouble("dterror")),"Nonfinite/invalid native saved clock");
  // dterror is signed telemetry. Preserve initial -DBL_MAX and every subsequent bit.
}
static Bytes Clock(JPartDataBi4& f){
  Bytes b;Append(b,f.Get_TimeStep());Append(b,f.Get_Step());Append(b,f.GetPart()->GetvDouble("SymplecticDtPre"));Append(b,f.GetPart()->GetvDouble("dterror"));Need(b.size()==28,"Clock is not 28 bytes");return b;
}
static std::vector<unsigned> DynamicSteps(){
  std::vector<unsigned> s;for(unsigned n=0;n<=65536;n+=64)s.push_back(n);for(unsigned n=5120;n<=5376;n++)s.push_back(n);for(unsigned n=66560;n<=262144;n+=1024)s.push_back(n);
  std::sort(s.begin(),s.end());s.erase(std::unique(s.begin(),s.end()),s.end());Need(s.size()==1469&&s.front()==0&&s.back()==262144,"Declared saved-step set differs");return s;
}
template<class T> static Counts Array(unsigned part,const char* name,TpData type,const std::vector<T>& old,const std::vector<T>& fresh,const Native& a,const Native& b,std::ofstream& csv){
  Need(old.size()==Total&&fresh.size()==Total,"Incomplete typed native comparison");Counts c;c.bytes=std::uint64_t(Total)*sizeof(T);std::uint64_t elements=0;long firstId=-1,firstByte=-1;
  for(unsigned id=0;id<Total;id++){
    const auto* x=reinterpret_cast<const unsigned char*>(&old[a.slot[id]]);const auto* y=reinterpret_cast<const unsigned char*>(&fresh[b.slot[id]]);bool diff=false;
    for(size_t j=0;j<sizeof(T);j++)if(x[j]!=y[j]){c.different++;diff=true;if(firstId<0){firstId=long(id);firstByte=long(j);}}
    elements+=diff;
  }
  csv<<part<<','<<name<<','<<unsigned(type)<<','<<Total<<','<<sizeof(T)<<','<<c.bytes<<','<<c.different<<','<<elements<<','<<firstId<<','<<firstByte<<'\n';return c;
}
static Counts Arrays(unsigned part,bool dynamic,const Native& a,const Native& b,std::ofstream& csv){
  Counts c;
#define HGRAW_ARRAY(name,type,member) {const auto z=Array(part,name,type,a.member,b.member,a,b,csv);c.bytes+=z.bytes;c.different+=z.different;}
  HGRAW_ARRAY("Idp",DatUint,ids);HGRAW_ARRAY("Posd",DatDouble3,pos);HGRAW_ARRAY("Vel",DatFloat3,vel);HGRAW_ARRAY("Rhop",DatFloat,rhop);
  HGRAW_ARRAY("Sigma_kk",DatFloat3,legacykk);HGRAW_ARRAY("Sigma_ij",DatFloat3,legacyij);HGRAW_ARRAY("SigmaState_kk",DatDouble3,sk);HGRAW_ARRAY("SigmaState_ij",DatDouble3,si);
  HGRAW_ARRAY("Kplastic",DatFloat,plastic);HGRAW_ARRAY("FSType",DatUint,fstype);HGRAW_ARRAY("FSNormal",DatFloat3,normal);HGRAW_ARRAY("HydroMechLoadAce",DatFloat3,load);
  HGRAW_ARRAY("PorePress",DatFloat,p);HGRAW_ARRAY("PorePress0",DatFloat,p0);HGRAW_ARRAY("ExcessPorePress",DatFloat,excess);
  if(dynamic){HGRAW_ARRAY("PoroVolumeRatio",DatDouble,j);HGRAW_ARRAY("PoroPorosity",DatDouble,n);HGRAW_ARRAY("PoroThetaLastStage",DatDouble,theta);HGRAW_ARRAY("PoroCurrentVolume",DatDouble,volume);HGRAW_ARRAY("PoroMixtureDensity",DatDouble,rho);HGRAW_ARRAY("PoroHydraulicConductivity",DatDouble,k);HGRAW_ARRAY("PosDiv",DatFloat,posdiv);}
#undef HGRAW_ARRAY
  Need(c.bytes==std::uint64_t(Total)*(dynamic?212u:160u),"Incomplete all-array byte scope");return c;
}
static void Completion(const fs::path& out,const std::string& mode,const fs::path& old,const fs::path& fresh,const Counts& c,std::uint64_t clockDiff,bool complete,const std::string& error){
  const bool dynamic=mode=="Dynamic",passed=complete&&!c.different&&!clockDiff&&!c.metadataDifferent;std::ofstream done(out/"completion.json");
  done<<"{\n  \"stage\":\"upl_hg_raw_compare_r1\",\n  \"mode\":"<<Json(mode)<<",\n  \"passed\":"<<(passed?"true":"false")<<",\n  \"complete\":"<<(complete?"true":"false")<<",\n  \"old_data\":"<<Json(old.string())<<",\n  \"new_data\":"<<Json(fresh.string())<<",\n  \"frames_compared\":"<<c.frames<<",\n  \"expected_frames\":"<<(dynamic?1469:21)<<",\n  \"total_native_count\":1040,\n  \"fixed_count\":40,\n  \"soil_count\":1000,\n  \"arrays_per_frame\":"<<(dynamic?22:15)<<",\n  \"all_array_bytes_per_frame\":"<<(Total*(dynamic?212u:160u))<<",\n  \"array_bytes_compared\":"<<c.bytes<<",\n  \"array_different_bytes\":"<<c.different<<",\n  \"clock_bytes_per_frame\":28,\n  \"clock_layout\":\"TimeStep:double8,Step:uint4,SymplecticDtPre:double8,dterror:signed_double8\",\n  \"clock_different_bytes\":"<<clockDiff<<",\n  \"metadata_fields_checked\":"<<c.metadata<<",\n  \"metadata_different_fields\":"<<c.metadataDifferent<<",\n  \"excluded_metadata_rows\":"<<c.excluded<<",\n  \"excluded_header_values\":[\"RunCode\",\"Date\",\"AppName\",\"CaseName\"],\n  \"excluded_PART_values\":[\"RunTime\",\"timesim\",\"cpualloc\",\"nctalloc\",\"nctused\",\"npalloc\",\"npused\"],\n  \"excluded_values_and_types_recorded_in\":\"metadata.csv; exact decoded typed value bytes in hexadecimal, one row per field/frame\",\n  \"excluded_presence_and_types_still_compared\":true,\n  \"metadata_scope\":\"all root and PART scalar fields; only listed identity/runtime/allocation values excluded\",\n  \"array_scope\":\"both raw BI4 inputs; every declared array, every native ID including fixed IDs; exact type/count/bytes\",\n  \"clock_scope\":\"all frames; exact saved TimeStep/Step/locked-dt/signed-dterror; no resampling/interpolation or initial sentinel masking\",\n  \"finite_and_no_exclusion_checks_completed\":"<<(complete?"true":"false")<<",\n  \"dynamic_metadata_required_present\":"<<(dynamic?"true":"false")<<",\n  \"dynamic_metadata_required_absent\":"<<(dynamic?"false":"true")<<",\n  \"dynamic_PosDiv_native_float_not_CSV_reconstruction\":"<<(dynamic?"true":"false")<<",\n  \"old_CSV_exports_used\":false,\n  \"inputs_modified\":false,\n  \"solver_or_GenCase_launched\":false,\n  \"solver_exit_backend_xi_HG_allocation_or_source_binding_proved\":false,\n  \"new_physical_accuracy_threshold\":false,\n  \"physical_acceptance\":false,\n  \"error\":"<<Json(error)<<"\n}\n";
  done.flush();Need(bool(done),"Comparison completion write failed");
}
static bool Compare(const std::string& mode,const fs::path& oldArg,const fs::path& newArg,const fs::path& outArg){
  const bool dynamic=mode=="Dynamic";const unsigned samples=dynamic?1469:21;
  const auto old=fs::canonical(oldArg),fresh=fs::canonical(newArg),requested=fs::absolute(outArg).lexically_normal();
  Need(!fs::equivalent(old,fresh),"Comparison requires two distinct raw data directories");Need(!fs::exists(requested),"Retained comparison output protected");
  const auto out=fs::canonical(requested.parent_path())/requested.filename();
  for(auto parent=out.parent_path();;parent=parent.parent_path()){
    Need(!fs::equivalent(parent,old)&&!fs::equivalent(parent,fresh),"Comparison output must remain outside both raw input directories");
    if(parent==parent.parent_path())break;
  }
  Sequence(old,samples);Sequence(fresh,samples);Need(fs::create_directory(out),"Fresh comparison output directory was not created");
  std::ofstream arrays(out/"arrays.csv"),frames(out/"frames.csv"),metadata(out/"metadata.csv");
  Need(arrays&&frames&&metadata,"Comparison CSV open failed");frames<<std::setprecision(17);
  arrays<<"part,array,native_type,count,element_bytes,compared_bytes,different_bytes,different_elements,first_different_native_id,first_different_element_byte\n";
  frames<<"part,old_time_s,new_time_s,old_step_uint32,new_step_uint32,old_locked_dt_s,new_locked_dt_s,old_signed_dterror_s,new_signed_dterror_s,array_count,all_array_bytes,array_different_bytes,clock_bytes,clock_different_bytes,metadata_fields,metadata_different_fields,excluded_metadata_rows,types_counts_IDs_finite_no_exclusions_checked,passed\n";
  metadata<<"part,scope,name,old_present,new_present,old_native_type,new_native_type,old_decoded_value_bytes_hex,new_decoded_value_bytes_hex,value_excluded_from_equality,values_equal,check_passed\n";
  Counts total;std::uint64_t clockDiff=0;const auto schedule=dynamic?DynamicSteps():std::vector<unsigned>();double previousOld=-1,previousNew=-1;
  try{
    for(unsigned part=0;part<samples;part++){
      JPartDataBi4 of,nf;of.LoadFilePart(old.string(),part,0,1);nf.LoadFilePart(fresh.string(),part,0,1);Header(of,part,dynamic);Header(nf,part,dynamic);
      Need(part?(of.Get_TimeStep()>previousOld&&nf.Get_TimeStep()>previousNew):(of.Get_TimeStep()==0&&nf.Get_TimeStep()==0),"Initial/monotone saved clock differs");
      if(dynamic){const double dt=std::ldexp(1.,-19),time=schedule[part]*dt;const unsigned step=schedule[part]?schedule[part]-1:0;
        for(auto* f:{&of,&nf})Need(f->Get_TimeStep()==time&&f->Get_Step()==step&&f->GetPart()->GetvDouble("SymplecticDtPre")==dt,"Dynamic .5s/1469 declared exact saved clock differs");}
      previousOld=of.Get_TimeStep();previousNew=nf.Get_TimeStep();
      const Native a=Load(of,Total,dynamic?0:-1),b=Load(nf,Total,dynamic?0:-1);const auto fields=Arrays(part,dynamic,a,b,arrays);
      const auto h=Meta(part,true,*of.GetData(),*nf.GetData(),metadata),p=Meta(part,false,*of.GetPart(),*nf.GetPart(),metadata);const auto cd=Difference(Clock(of),Clock(nf));
      const bool passed=!fields.different&&!cd&&!h.metadataDifferent&&!p.metadataDifferent;
      frames<<part<<','<<of.Get_TimeStep()<<','<<nf.Get_TimeStep()<<','<<of.Get_Step()<<','<<nf.Get_Step()<<','<<of.GetPart()->GetvDouble("SymplecticDtPre")<<','<<nf.GetPart()->GetvDouble("SymplecticDtPre")<<','<<of.GetPart()->GetvDouble("dterror")<<','<<nf.GetPart()->GetvDouble("dterror")<<','<<(dynamic?22:15)<<','<<fields.bytes<<','<<fields.different<<",28,"<<cd<<','<<h.metadata+p.metadata<<','<<h.metadataDifferent+p.metadataDifferent<<','<<h.excluded+p.excluded<<",1,"<<passed<<'\n';
      total.frames++;total.bytes+=fields.bytes;total.different+=fields.different;total.metadata+=h.metadata+p.metadata;total.metadataDifferent+=h.metadataDifferent+p.metadataDifferent;total.excluded+=h.excluded+p.excluded;clockDiff+=cd;
    }
    for(auto* s:{&arrays,&frames,&metadata}){s->flush();Need(bool(*s),"Comparison CSV write failed");}
    Completion(out,mode,old,fresh,total,clockDiff,true,"");return !total.different&&!clockDiff&&!total.metadataDifferent;
  }catch(const std::exception& e){Completion(out,mode,old,fresh,total,clockDiff,false,e.what());throw;}
  catch(const std::string& e){Completion(out,mode,old,fresh,total,clockDiff,false,e);throw;}
  catch(const char* e){Completion(out,mode,old,fresh,total,clockDiff,false,e?e:"Native reader exception");throw;}
  catch(...){Completion(out,mode,old,fresh,total,clockDiff,false,"Unknown native reader exception");throw;}
}
}
int main(int argc,char** argv){try{
  Need(argc==6&&std::string(argv[1])=="--compare","Use --compare Legacy|Dynamic OLD_DATA NEW_DATA FRESH_OUT");const std::string mode=argv[2];Need(mode=="Legacy"||mode=="Dynamic","Comparison mode must be Legacy or Dynamic");
  return hgraw::Compare(mode,argv[3],argv[4],argv[5])?0:1;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<(e?e:"Native reader exception")<<'\n';return 1;}catch(...){std::cerr<<"Raw native comparison rejected; preserve partial evidence\n";return 2;}}

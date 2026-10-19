// Read-only actual mode5 PART inspection; no CPU/GPU bit-equivalence assertion.
// Reuse only the existing BI4 array/finite/sequence helpers, not its comparator.
#include <cfloat>
#define main old_gpu_off_compare_unused_main
#include "hg_gpu_off_compare.cpp"
#undef main

static Part BandPart(const fs::path& dir,unsigned index,bool gpu,double& mass,double& support){
  JPartDataBi4 file;file.LoadFilePart(dir.string(),index,0,1);
  Part p;p.time=file.Get_TimeStep();p.count=file.Get_Npok();p.step=file.Get_Step();p.soil=unsigned(file.Get_CaseNfluid());
  Require(file.GetNpiece()==1&&!file.Get_NpDynamic()&&!file.Get_ReuseIds(),"Require one-piece fixed native IDs");
  Require(p.count==1040&&file.Get_CaseNp()==1040&&file.Get_Nout()==0&&p.soil==1000&&file.Get_CaseNfixed()==40&&!file.Get_CaseNmoving()&&!file.Get_CaseNfloat(),"Native case counts changed");
  // Both current CPU and GPU save before Nstep++, as read in their main loops.
  Require(p.step==(index?index-1:0)&&std::isfinite(p.time)&&std::abs(p.time-index*1e-5)<1e-12,"PART index/step/time mismatch");
  mass=double(float(file.Get_MassFluid()));support=double(2.f*float(file.Get_H()));
  Require(file.Get_Data2d()&&file.Get_Dp()==.01&&float(file.Get_MassFluid())==float(.21)&&float(file.Get_H())==float(.018),"Unexpected case geometry/mass");
  for(unsigned i=0;i<file.ArraysCount();i++){
    const std::string name=file.ArrayName(i);const auto* source=file.GetArray(name);Array value;value.type=source->GetType();value.stride=JBinaryDataDef::SizeOfType(value.type);
    Require(value.type!=JBinaryDataDef::DatNull&&value.type!=JBinaryDataDef::DatText&&value.stride,"Non-numeric/unknown field: "+name);
    const unsigned count=source->DataInPointer()?source->GetCount():source->GetFileDataCount();Require(count==1040,"Field count mismatch: "+name);
    value.bytes.resize(size_t(count)*value.stride);Require(source->GetDataCopy(count,value.bytes.data())==count,"Incomplete field: "+name);
    Finite(value,name);Require(p.arrays.emplace(name,std::move(value)).second,"Repeated field: "+name);
  }
  for(const char* name:{"Idp","Vel","Rhop","Sigma_kk","Sigma_ij","SigmaState_kk","SigmaState_ij","Kplastic","PorePress","PorePress0"})Require(p.arrays.count(name)!=0,std::string("Missing field: ")+name);
  if(gpu)Require(p.arrays.count("HydroMechLoadAce")!=0,"GPU mode5 load diagnostic is missing");
  Require(p.arrays.count("Pos")+p.arrays.count("Posd")==1,"Expected one position array");
  Require(p.arrays.at("Idp").type==JBinaryDataDef::DatUint&&p.arrays.at("SigmaState_kk").type==JBinaryDataDef::DatDouble3&&p.arrays.at("SigmaState_ij").type==JBinaryDataDef::DatDouble3,"Native ID/stress types differ");
  p.slot.assign(1040,~0u);const auto& ids=p.arrays.at("Idp");
  for(unsigned i=0;i<1040;i++){unsigned id;std::memcpy(&id,ids.bytes.data()+i*ids.stride,sizeof(id));Require(id<1040&&p.slot[id]==~0u,"Duplicate/invalid native ID");p.slot[id]=i;}
  for(unsigned slot:p.slot)Require(slot!=~0u,"Missing native ID");return p;
}
template<class T> static T Element(const Part& p,const char* name,unsigned id){
  const auto& a=p.arrays.at(name);Require(a.stride==sizeof(T),std::string("Field element type mismatch: ")+name);T v;std::memcpy(&v,a.bytes.data()+size_t(p.slot.at(id))*a.stride,sizeof(v));return v;
}
static tdouble3 Position(const Part& p,unsigned id){
  if(p.arrays.count("Posd"))return Element<tdouble3>(p,"Posd",id);
  const auto q=Element<tfloat3>(p,"Pos",id);return TDouble3(q.x,q.y,q.z);
}
static std::string Number(double value){std::ostringstream s;s<<std::setprecision(17)<<value;return s.str();}
int main(int argc,char** argv){
  if(argc!=4){std::cerr<<"Use hg_gpu_band_part_check DATA cpu|gpu NEW_CHECK_JSON\n";return 2;}
  const fs::path output=fs::absolute(argv[3]);if(fs::exists(output)){std::cerr<<"Refusing existing check JSON\n";return 2;}
  bool passed=false;std::string reason;unsigned checked=0;std::ostringstream detail;const bool gpu=std::string(argv[2])=="gpu";
  try{
    Require(gpu||std::string(argv[2])=="cpu","Backend must be cpu or gpu");const fs::path dir=fs::absolute(argv[1]);Sequence(dir);
    std::vector<bool> initialBand(1040,false);std::vector<tdouble3> previous;
    for(unsigned index=0;index<=20;index++){
      double mass=0,support=0;const Part p=BandPart(dir,index,gpu,mass,support);const bool hasload=p.arrays.count("HydroMechLoadAce")!=0;
      double zmax=-DBL_MAX;std::vector<tdouble3> positions(1040);
      for(unsigned id=0;id<1040;id++){positions[id]=Position(p,id);if(id>=40)zmax=(std::max)(zmax,positions[id].z);}
      double sx=0,sy=0,sz=0,outsideMax=0,margin=DBL_MAX,stepMove=0;unsigned loaded=0,nonfloat=0;
      for(unsigned id=0;id<1040;id++){
        const bool inband=id>=40&&positions[id].z>zmax-support;
        if(!index)initialBand[id]=inband;
        Require(inband==initialBand[id],"Saved band membership changed in the 20-step window");
        if(id>=40)margin=(std::min)(margin,std::abs(positions[id].z-zmax+support));
        if(index){const double dx=positions[id].x-previous[id].x,dy=positions[id].y-previous[id].y,dz=positions[id].z-previous[id].z;stepMove=(std::max)(stepMove,std::sqrt(dx*dx+dy*dy+dz*dz));}
        const auto kk=Element<tdouble3>(p,"SigmaState_kk",id),ij=Element<tdouble3>(p,"SigmaState_ij",id);
        const auto fkk=Element<tfloat3>(p,"Sigma_kk",id),fij=Element<tfloat3>(p,"Sigma_ij",id);
        const double s[]={kk.x,kk.y,kk.z,ij.x,ij.y,ij.z};const float f[]={fkk.x,fkk.y,fkk.z,fij.x,fij.y,fij.z};
        for(unsigned c=0;c<6;c++){Require(f[c]==float(s[c]),"Legacy stress is not float projection of double state");if(id>=40&&s[c]!=double(float(s[c])))nonfloat++;}
        if(hasload){
          Require(p.arrays.at("HydroMechLoadAce").type==JBinaryDataDef::DatFloat3,"Load field must be float3");const auto a=Element<tfloat3>(p,"HydroMechLoadAce",id);
          sx+=mass*a.x;sy+=mass*a.y;sz+=mass*a.z;loaded+=(a.x!=0||a.y!=0||a.z!=0);
          if(!inband)outsideMax=(std::max)(outsideMax,std::sqrt(double(a.x)*a.x+double(a.y)*a.y+double(a.z)*a.z));
        }
      }
      const double forceTime=(index?index-1:0)*1e-5,expected=-1000.*forceTime/.01;
      const double forceError=hasload?std::abs(sz-expected):0;
      if(hasload){Require(forceError<.001&&sx==0&&sy==0,"Actual saved load total differs from base-time ramp or has horizontal force");Require(outsideMax==0,"Saved support-exterior particle has nonzero applied load");}
      // Margin and displacement are reported, not generalized into a proof for
      // arbitrary motion: load used predictor geometry; PART holds corrected geometry.
      if(checked)detail<<',';detail<<std::setprecision(17)<<"{\"part\":"<<index<<",\"saved_step\":"<<p.step<<",\"actual_time_s\":"<<p.time<<",\"load_evaluation_time_s\":"<<forceTime
        <<",\"native_count\":1040,\"soil_count\":1000,\"all_numeric_fields_finite\":true,\"array_count\":"<<p.arrays.size()<<",\"double_stress_nonfloat_components\":"<<nonfloat
        <<",\"load_available\":"<<(hasload?"true":"false")<<",\"load_count\":"<<(hasload?std::to_string(loaded):"null")<<",\"expected_vertical_force_N_m\":"<<expected
        <<",\"actual_vertical_force_N_m\":"<<(hasload?Number(sz):"null")<<",\"vertical_force_abs_error_N_m\":"<<(hasload?Number(forceError):"null")
        <<",\"support_outside_load_max\":"<<(hasload?Number(outsideMax):"null")<<",\"saved_support_edge_min_margin_m\":"<<margin<<",\"maximum_saved_endpoint_displacement_m\":"<<stepMove<<'}';
      previous=positions;checked++;
    }
    passed=true;
  }catch(const std::exception& e){reason=e.what();}catch(...){reason="Production BI4 reader exception";}
  std::ofstream record(output);record<<"{\"passed\":"<<(passed?"true":"false")<<",\"reason\":"<<Json(reason)<<",\"backend\":"<<Json(argv[2])<<",\"parts_checked\":"<<checked<<",\"expected_parts\":21,\"native_id_set\":\"0..1039\",\"parts\":["<<detail.str()<<']'
    <<",\"force_limit_N_m\":0.001,\"field_cross_backend_comparison_pending\":true,\"physical_acceptance\":false,\"full_cycle_admitted\":false,\"limitations\":[\"CPU SaveData currently has no HydroMechLoadAce; CPU force fields are null, not assumed verified\",\"GPU load evaluation uses base time (PARTk: (k-1)dt), not output time\",\"Support check uses emitted corrected positions; predictor-stage geometry was not independently captured; margin and step displacement are reported\",\"Twenty steps exercise input/pool/sort/output lifecycle only; no long-term physical or CPU/GPU equivalence claim\"]}\n";
  record.flush();if(!record){std::cerr<<"Check write failed\n";return 2;}std::cout<<(passed?"PASS":"FAIL")<<" mode5 PART structure: "<<checked<<" parts; "<<reason<<'\n';return passed?0:1;
}

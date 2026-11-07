// AS metadata adapter. The included, unchanged core owns the only22-array decode.
#define wmain C08CoreMain
#include "as_plane_core_r2.cpp"
#undef wmain

int wmain(int argc,wchar_t** argv){unsigned headerPart=~0u;try{
  Need(argc==12&&std::wstring(argv[1])==L"--read"&&std::wstring(argv[2])==L"psi0"&&(std::wstring(argv[3])==L"CPU"||std::wstring(argv[3])==L"GPU"),"Use --read psi0 CPU|GPU DATA PRE END SAMPLES 1 PLAN EXPECT_AS FRESHOUT");
  Need(std::wstring(argv[8])==L"1"&&(std::wstring(argv[10])==L"0"||std::wstring(argv[10])==L"1"),"Adapter requires NoPen1 and explicit EXPECT_AS0/1");
  const bool expectAS=std::wstring(argv[10])==L"1";const unsigned samples=Number(argv[7]),expected=Number(argv[6]);const fs::path data=argv[4],out=argv[11];
  Need(expected>EventStep&&samples>0&&samples<=expected-EventStep&&fs::is_directory(data)&&!fs::exists(out),"Fresh bounded adapter input/output required");
  unsigned activeHeaders=0,policyHeaders=0;
  for(unsigned part=0;part<samples;part++){
    headerPart=part;JPartDataBi4 f;f.LoadFilePart(data.string(),part,0,1);const auto* p=f.GetPart();
    // LoadFilePart uses OpenFileStructure/ReadItem(loadarrays=false). No GetArray/
    // GetDataCopy or field-array decode occurs in this metadata-only preflight.
    if(expectAS){
      Need(p->ExistsValue("DynamicArtificialStressPolicy",JBinaryDataDef::DatText)&&p->GetvText("DynamicArtificialStressPolicy")=="ReleaseOnly"&&p->ExistsValue("DynamicArtificialStressActive",DatBool)&&p->GetvBool("DynamicArtificialStressActive")&&p->ExistsValue("DynamicArtificialStressCoef",DatFloat)&&Bits(p->GetvFloat("DynamicArtificialStressCoef"),.2f)&&p->ExistsValue("DynamicArtificialStressExp",DatFloat)&&Bits(p->GetvFloat("DynamicArtificialStressExp"),2.55f),"Expected AS1 ReleaseOnly/Active/float coefficient metadata differs");
      activeHeaders++;
    }
    else Need(!p->ExistsValue("DynamicArtificialStressActive")||(p->ExistsValue("DynamicArtificialStressActive",DatBool)&&!p->GetvBool("DynamicArtificialStressActive")),"Expected AS0 contradicts active/ill-typed native AS metadata");
    policyHeaders+=p->ExistsValue("DynamicArtificialStressPolicy");
  }
  std::vector<wchar_t*> coreargv;for(int i=0;i<argc;i++)if(i!=10)coreargv.push_back(argv[i]);
  Need(coreargv.size()==11,"Core CLI translation differs");const int rc=C08CoreMain(int(coreargv.size()),coreargv.data());if(rc)return rc;
  std::ofstream done(out/"AS_metadata.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_c08_as_plane_native_r2\",\"passed\":true,\"expected_AS\":"<<(expectAS? "true":"false")<<",\"NoPenOn_required\":true,\"samples\":"<<samples<<",\"completed_steps\":"<<expected<<",\"AS_active_true_headers\":"<<activeHeaders<<",\"AS_policy_present_headers\":"<<policyHeaders<<",\"AS_policy_when_enabled\":\"ReleaseOnly\",\"AS_coefficient_float_reference\":"<<double(.2f)<<",\"AS_exponent_float_reference\":"<<double(2.55f)<<",\"metadata_header_scans\":"<<samples<<",\"metadata_scans_decode_field_arrays\":false,\"core_stage\":\"upl_c08_plane_native_r1\",\"core_array_decode_passes\":1,\"core_numerical_guards_modified\":false,\"PRE_arrays_reloaded_by_adapter\":false,\"backend_proven_by_reader\":false,\"reaction_J_Darcy_closed\":false,\"physical_acceptance\":false}\n";
  done.flush();Need(bool(done),"AS metadata annotation write failed; preserve completed core output, no repeated decode");return 0;
}catch(const JException& e){std::cerr<<"AS header part="<<headerPart<<' '<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<"AS header part="<<headerPart<<' '<<e.what()<<'\n';return 1;}}

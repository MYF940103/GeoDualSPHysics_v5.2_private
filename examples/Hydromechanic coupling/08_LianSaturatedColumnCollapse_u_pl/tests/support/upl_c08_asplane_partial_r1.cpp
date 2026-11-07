// Metadata-only AS preflight around a mechanically derived53-state partial core.
#define wmain ASPartialCoreMain
#include "asplane_partial_core_r1.cpp"
#undef wmain
int wmain(int argc,wchar_t** argv){unsigned headerPart=~0u;try{
  Need(argc==11&&std::wstring(argv[1])==L"--read"&&std::wstring(argv[2])==L"psi0"&&std::wstring(argv[3])==L"GPU"&&std::wstring(argv[6])==L"4212000"&&std::wstring(argv[7])==L"53"&&std::wstring(argv[8])==L"1","Use --read psi0 GPU DATA PRE 4212000 53 1 ORIGINAL60PLAN FRESHOUT");
  const fs::path data=argv[4],out=argv[10];Need(fs::is_directory(data)&&!fs::exists(out),"Existing partial result protected or missing DATA");
  for(unsigned part=0;part<53;part++){
    headerPart=part;JPartDataBi4 f;f.LoadFilePart(data.string(),part,0,1);const auto* p=f.GetPart();
    // OpenFileStructure/ReadItem(loadarrays=false): only metadata, never field arrays.
    Need(p->ExistsValue("DynamicArtificialStressPolicy",JBinaryDataDef::DatText)&&p->GetvText("DynamicArtificialStressPolicy")=="ReleaseOnly"&&p->ExistsValue("DynamicArtificialStressActive",DatBool)&&p->GetvBool("DynamicArtificialStressActive")&&p->ExistsValue("DynamicArtificialStressCoef",DatFloat)&&Bits(p->GetvFloat("DynamicArtificialStressCoef"),.2f)&&p->ExistsValue("DynamicArtificialStressExp",DatFloat)&&Bits(p->GetvFloat("DynamicArtificialStressExp"),2.55f),"AS1 ReleaseOnly/Active/float coefficient metadata differs");
  }
  const int rc=ASPartialCoreMain(argc,argv);if(rc)return rc;
  std::ofstream done(out/"AS_metadata.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_c08_asplane_partial_r1.AS\",\"passed\":true,\"expected_AS\":true,\"NoPenOn_required\":true,\"samples\":53,\"completed_steps\":4212000,\"AS_active_true_headers\":53,\"AS_policy_present_headers\":53,\"AS_policy_when_enabled\":\"ReleaseOnly\",\"AS_coefficient_float_reference\":"<<double(.2f)<<",\"AS_exponent_float_reference\":"<<double(2.55f)<<",\"metadata_header_scans\":53,\"metadata_scans_decode_field_arrays\":false,\"core_stage\":\"upl_c08_asplane_partial_r1\",\"core_array_decode_passes\":1,\"core_numerical_guards_modified\":false,\"PRE_arrays_reloaded_by_adapter\":false,\"diagnostic_partial\":true,\"runtime_success_claimed\":false,\"reaction_J_Darcy_closed\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"AS annotation write failed; preserve core output, no repeated decode");return 0;
}catch(const JException& e){std::cerr<<"AS partial header part="<<headerPart<<' '<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<"AS partial header part="<<headerPart<<' '<<e.what()<<'\n';return 1;}}

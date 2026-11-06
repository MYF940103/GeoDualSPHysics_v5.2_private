// Test-only MSVC material-point consumer; no project objects or spatial solver required.
#include "upl_material_shared_cases_r1.h"
#include <iostream>
namespace fs=std::filesystem;
int main(int argc,char** argv){
  using namespace upl_material_cases_r1;unsigned current=~0u;
  try{
    Need(argc==5&&std::string(argv[1])=="--source"&&std::string(argv[3])=="--out","Use --source ORIGINAL_POINTS.csv --out FRESH_DIR");
    const fs::path tests=fs::path(__FILE__).parent_path().parent_path(),source=argv[2],out=argv[4];
    Need(tests.is_absolute()&&fs::equivalent(source,tests/"outputs/upl_material_return_CPU_result_r1/points.csv"),"Only retained actual132-row source is admitted");
    Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh result output required");
    const auto bytes=fs::file_size(source);const auto stamp=fs::last_write_time(source);const auto cases=Load(source);
    Need(cases.size()==71&&fs::create_directory(out),"Cannot create fresh71-case output");
    std::ofstream csv(out/"points.csv");csv<<std::setprecision(17);WriteHeader(csv);
    unsigned counts[5]={},closed=0,savedbitsdiff=0;
    for(const auto& c:cases){
      current=c.point.id;const Point before=c.point;const Result r=Return(c.point.state,c.point.material);
      Need(SamePoint(before,c.point),"Core changed input fields");const Metrics v=Check(c,r);WriteRow(csv,c,r,v);
      counts[unsigned(r.status)]++;closed+=unsigned(v.constant_control);savedbitsdiff+=unsigned(!v.reference_saved_kappa_bits_equal);
    }
    csv.flush();Need(bool(csv),"CSV write failed");
    Need(counts[0]==5&&counts[1]==18&&counts[2]==36&&counts[3]==12&&counts[4]==0&&closed==6,"Expected bounded material coverage differs");
    Need(fs::file_size(source)==bytes&&fs::last_write_time(source)==stamp,"Retained source SMT changed");
    std::ofstream done(out/"completion.json");
    done<<"{\"stage\":\"upl_material_shared_cpu_r1\",\"passed\":true,\"rows\":71,\"original_candidate_reference_rows\":66,\"invalid_rows\":5,\"elastic_rows\":18,\"radial_rows\":36,\"ApexNeeded_rows\":12,\"constant_strength_checks\":6,\"NonConverged_rows\":0,\"NonConverged_naturally_covered\":false,\"input_and_failure_state_scalar_bits_preserved\":true,\"POD_padding_compared\":false,\"reference_saved_kappa_bits_differences\":"<<savedbitsdiff<<",\"parameters_and_persistent_kappa_float\":true,\"retained_source_SMT_unchanged\":true,\"SHA_scans\":0,\"spatial_solver\":false,\"physical_acceptance\":false}\n";
    done.flush();Need(bool(done),"Completion write failed");return 0;
  }catch(const std::exception& e){std::cerr<<"id="<<current<<" : "<<e.what()<<'\n';return 1;}
}

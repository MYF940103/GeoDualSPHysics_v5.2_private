// Standalone test-only CUDA material consumer. No engine object, solver or constitutive selector.
#include <cuda_runtime.h>
#include "upl_material_shared_cases_r1.h"
#include <array>
#include <iostream>
#include <iterator>
namespace fs=std::filesystem;
using namespace upl_material_cases_r1;

__global__ void ReturnBatch(unsigned count,const Point* inputs,Result* outputs){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i<count)outputs[i]=upl_material_candidate_r1::Return(inputs[i].state,inputs[i].material);
}
static void Cu(cudaError_t error){Need(error==cudaSuccess,cudaGetErrorString(error));}
struct Buffers{
  Point* inputs=nullptr;Result* outputs=nullptr;
  ~Buffers(){if(outputs)cudaFree(outputs);if(inputs)cudaFree(inputs);}
};
static Point CopyPoint(const Point& p){
  // Explicit member mapping, never an alias of tsymatrix3d/native CUDA storage.
  const auto& s=p.state.stress;const auto& m=p.material;
  return {p.id,{{s.xx,s.yy,s.zz,s.xy,s.yz,s.xz},p.state.kappa},
    {m.bulk,m.shear,m.phi,m.cohesion_peak,m.cohesion_residual,m.cohesion_decay,m.psi0,m.psi_decay}};
}
static Result Tail(unsigned index){
  Result r{};const double d=index+1.;r.state={{d,2*d,3*d,4*d,5*d,6*d},.125f};r.status=Status::Invalid;
  r.kappa_continuous=7*d;r.lambda=8*d;r.trial_yield=9*d;r.root_residual=10*d;r.root_budget=11*d;r.minus_dF_dlambda=12*d;r.iterations=0x1234abcd+index;return r;
}
static bool SameResultMembers(const Result& a,const Result& b){
  const std::array<double,6> x={a.kappa_continuous,a.lambda,a.trial_yield,a.root_residual,a.root_budget,a.minus_dF_dlambda};
  const std::array<double,6> y={b.kappa_continuous,b.lambda,b.trial_yield,b.root_residual,b.root_budget,b.minus_dF_dlambda};
  for(unsigned n=0;n<x.size();n++)if(!Bits(x[n],y[n]))return false;
  return SameState(a.state,b.state)&&a.status==b.status&&a.iterations==b.iterations;
}
static double Difference(double a,double b){
  if(std::isfinite(a)&&std::isfinite(b))return std::fabs(a-b);
  Need((std::isnan(a)&&std::isnan(b))||a==b,"CPU/GPU nonfinite scalar class differs");return 0.;
}
static double StressDifference(const Stress& a,const Stress& b){
  return (std::max)({Difference(a.xx,b.xx),Difference(a.yy,b.yy),Difference(a.zz,b.zz),
    Difference(a.xy,b.xy),Difference(a.yz,b.yz),Difference(a.xz,b.xz)});
}
int main(int argc,char** argv){unsigned current=~0u;
  try{
    Need(argc==7&&std::string(argv[1])=="--source"&&std::string(argv[3])=="--cpu"&&std::string(argv[5])=="--out",
      "Use --source ORIGINAL_POINTS.csv --cpu ACTUAL_MSVC_CPU_POINTS.csv --out FRESH_DIR");
    const fs::path tests=fs::path(__FILE__).parent_path().parent_path(),source=argv[2],cpuPath=argv[4],out=argv[6];
    Need(tests.is_absolute()&&fs::equivalent(source,tests/"outputs/upl_material_return_CPU_result_r1/points.csv"),"Only retained actual132-row source is admitted");
    Need(cpuPath.filename()=="points.csv"&&!fs::equivalent(source,cpuPath),"Actual separate MSVC CPU points.csv required");
    Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh output/existing parent required");
    const auto sourceBytes=fs::file_size(source);const auto sourceStamp=fs::last_write_time(source);
    const auto cpuBytes=fs::file_size(cpuPath);const auto cpuStamp=fs::last_write_time(cpuPath);
    const auto cases=Load(source);const auto cpuRows=ReadTable(cpuPath);Need(cases.size()==71&&cpuRows.size()==71,"Both71-case data sets required");
    std::ifstream cpudone(cpuPath.parent_path()/"completion.json");const std::string closed((std::istreambuf_iterator<char>(cpudone)),std::istreambuf_iterator<char>());
    Need(closed.find("\"stage\":\"upl_material_shared_cpu_r1\"")!=std::string::npos
      &&closed.find("\"passed\":true")!=std::string::npos&&closed.find("\"rows\":71")!=std::string::npos,"Actual successful MSVC CPU completion required");
    // This checks the known CPU writer, not an invented backend proof; root owns actual compiler/process receipts.
    std::map<unsigned,Row> cpu;
    for(const auto& row:cpuRows)Need(cpu.emplace(unsigned(std::stoul(row.at("id"))),row).second,"Duplicate CPU case ID");
    const unsigned count=unsigned(cases.size()),capacity=count+2;std::vector<Point> input(capacity);
    for(unsigned n=0;n<count;n++){
      input[n]=CopyPoint(cases[n].point);Need(SamePoint(input[n],cases[n].point),"Input member mapping differs");
      const auto& row=cpu.at(input[n].id);Need(row.at("input_bits")==PointBits(input[n])&&row.at("path")==cases[n].path&&row.at("branch")==cases[n].branch,"Actual CPU input fields differ");
    }
    input[count]=CopyPoint(cases.front().point);input[count].id=0xf1234567;input[count].state={{101,102,103,104,105,106},.25f};
    input[count+1]=CopyPoint(input[count]);input[count+1].id++;input[count+1].state.stress.xz=107;
    std::vector<Result> result(capacity);for(unsigned n=0;n<capacity;n++)result[n]=Tail(n);
    Need(fs::create_directory(out),"Cannot claim fresh output");Cu(cudaSetDevice(0));cudaDeviceProp properties{};Cu(cudaGetDeviceProperties(&properties,0));
    Buffers device;Cu(cudaMalloc(reinterpret_cast<void**>(&device.inputs),capacity*sizeof(Point)));Cu(cudaMalloc(reinterpret_cast<void**>(&device.outputs),capacity*sizeof(Result)));
    Cu(cudaMemcpy(device.inputs,input.data(),capacity*sizeof(Point),cudaMemcpyHostToDevice));Cu(cudaMemcpy(device.outputs,result.data(),capacity*sizeof(Result),cudaMemcpyHostToDevice));
    ReturnBatch<<<1,128>>>(count,device.inputs,device.outputs);Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());
    std::vector<Point> inputAfter(capacity);Cu(cudaMemcpy(inputAfter.data(),device.inputs,capacity*sizeof(Point),cudaMemcpyDeviceToHost));
    Cu(cudaMemcpy(result.data(),device.outputs,capacity*sizeof(Result),cudaMemcpyDeviceToHost));
    for(unsigned n=0;n<capacity;n++)Need(SamePoint(input[n],inputAfter[n]),"Kernel changed an input scalar field");
    for(unsigned n=count;n<capacity;n++)Need(SameResultMembers(result[n],Tail(n)),"Output tail defined member changed");
    std::ofstream rows(out/"points.csv"),parity(out/"CPU_GPU.csv");rows<<std::setprecision(17);parity<<std::setprecision(17);WriteHeader(rows);
    parity<<"id,status,input_bits_equal,result_state_bits_equal,stress_max_abs_difference_Pa,combined_original_tensor_budget_Pa,kappa_continuous_difference,combined_original_history_budget,lambda_difference,combined_original_lambda_budget,kappa_saved_float_difference,scalar_residual_CPU_Pa,scalar_residual_GPU_Pa,root_budget_CPU_Pa,root_budget_GPU_Pa,iterations_CPU,iterations_GPU\n";
    unsigned counts[5]={},closedControls=0,savedBitsDifferent=0,cpuStateBitsDifferent=0;
    double maxStress=0,maxHistory=0,maxLambda=0,maxSaved=0,maxContinuousYield=0,maxSavedYield=0;
    for(unsigned n=0;n<count;n++){
      const auto& c=cases[n];const auto& r=result[n];current=c.point.id;const Metrics m=Check(c,r);WriteRow(rows,c,r,m);
      const auto& row=cpu.at(current);Need(row.at("status")==Name(r.status),"Actual CPU/GPU return status differs");
      const double ds=StressDifference(r.state.stress,StressFrom(row,"new_")),dk=Difference(r.kappa_continuous,Number(row,"kappa_continuous"));
      const double dl=Difference(r.lambda,Number(row,"lambda")),df=Difference(r.state.kappa,Number(row,"new_kappa"));
      const double tensorBudget=m.tensor_budget+Number(row,"tensor_budget_Pa");
      const double historyBudget=2.*8192.*DBL_EPSILON*(std::max)(1.,std::fabs(c.continuous_reference));
      const double lambdaBudget=2.*4096.*DBL_EPSILON*(std::max)(1.,std::fabs(c.lambda_reference));
      if(c.reference&&CommitAllowed(r.status))Need(ds<=tensorBudget&&dk<=historyBudget&&dl<=lambdaBudget,"CPU/GPU exceeds sum of original per-program reference budgets");
      const bool stateBitsEqual=row.at("result_state_bits")==StateBits(r.state);
      parity<<current<<','<<Name(r.status)<<",1,"<<stateBitsEqual<<','<<ds<<','<<tensorBudget<<','<<dk<<','<<historyBudget<<','<<dl<<','<<lambdaBudget<<','<<df<<','<<row.at("scalar_residual_Pa")<<','<<r.root_residual<<','<<row.at("root_budget_Pa")<<','<<r.root_budget<<','<<row.at("iterations")<<','<<r.iterations<<'\n';
      counts[unsigned(r.status)]++;closedControls+=unsigned(m.constant_control);savedBitsDifferent+=unsigned(!m.reference_saved_kappa_bits_equal);cpuStateBitsDifferent+=unsigned(!stateBitsEqual);
      maxStress=(std::max)(maxStress,ds);maxHistory=(std::max)(maxHistory,dk);maxLambda=(std::max)(maxLambda,dl);maxSaved=(std::max)(maxSaved,df);
      if(r.status==Status::Radial){maxContinuousYield=(std::max)(maxContinuousYield,std::fabs(m.continuous_yield));maxSavedYield=(std::max)(maxSavedYield,std::fabs(m.saved_yield));}
    }
    rows.flush();parity.flush();Need(bool(rows)&&bool(parity),"GPU material CSV write failed");
    Need(counts[0]==5&&counts[1]==18&&counts[2]==36&&counts[3]==12&&counts[4]==0&&closedControls==6,"Declared material case/status coverage differs");
    Need(fs::file_size(source)==sourceBytes&&fs::last_write_time(source)==sourceStamp&&fs::file_size(cpuPath)==cpuBytes&&fs::last_write_time(cpuPath)==cpuStamp,"Consumed original/CPU CSV SMT changed");
    std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_material_shared_gpu_r1\",\"passed\":true,\"rows\":71,\"original_candidate_reference_rows\":66,\"invalid_rows\":5,\"elastic_rows\":18,\"radial_rows\":36,\"ApexNeeded_rows\":12,\"NonConverged_rows\":0,\"NonConverged_naturally_covered\":false,\"constant_strength_checks\":6,\"kernel_launches\":1,\"input_points_field_checks\":"<<capacity<<",\"tail_results_member_checks\":2,\"POD_padding_compared\":false,\"actual_CPU_same_input_rows\":71,\"CPU_state_bits_differences_descriptive\":"<<cpuStateBitsDifferent<<",\"reference_saved_kappa_bits_differences_descriptive\":"<<savedBitsDifferent<<",\"max_CPU_GPU_stress_difference_Pa\":"<<maxStress<<",\"max_CPU_GPU_kappa_continuous_difference\":"<<maxHistory<<",\"max_CPU_GPU_lambda_difference\":"<<maxLambda<<",\"max_CPU_GPU_saved_kappa_difference_descriptive\":"<<maxSaved<<",\"max_radial_independent_yield_continuous_Pa\":"<<maxContinuousYield<<",\"max_radial_independent_yield_saved_Pa_descriptive\":"<<maxSavedYield<<",\"device_major\":"<<properties.major<<",\"device_minor\":"<<properties.minor<<",\"parameters_and_persistent_kappa_float\":true,\"failure_state_not_committed\":true,\"source_and_CPU_SMT_unchanged\":true,\"CPU_process_proven_by_probe\":false,\"SHA_scans\":0,\"engine_objects_linked\":false,\"spatial_solver\":false,\"physical_acceptance\":false}\n";
    done.flush();Need(bool(done),"GPU completion write failed");return 0;
  }catch(const std::exception& error){std::cerr<<"id="<<current<<" : "<<error.what()<<'\n';return 1;}
}

// Standalone production-layout adapter checks; the frozen U core is an implementation reference only.
#include <cuda_runtime.h>
#include "FunSoilMaterial.h"
#include "upl_material_unified_candidate_r1.h"
#include <algorithm>
#include <array>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
namespace U=fsoil_unified_candidate_r1;
namespace fs=std::filesystem;
struct Point{unsigned id;U::State input;StSoilCte cte;TpDPCtes fit;bool soft,trigger;};
struct Value{double2 xx_xy,xz_yy,yz_zz;float kappa;fsoil::Status status;};
struct Output{Value adapter;U::Result reference;};
struct Strength{float peak,residual;};
__host__ __device__ static Strength ReferenceStrength(const Point& p){
  // FOS belongs to strength evolution, not to dilation-only evolution. Without
  // cohesion evolution there is one constant effective cohesion, not a second endpoint.
  const bool strength_evolves=p.cte.n_phi>0.f||p.cte.n_coh>0.f;
  const float factor=p.trigger&&strength_evolves?p.cte.SoilTriggerFos:1.f;
  const float peak=p.cte.coh/factor;
  return {peak,p.cte.n_coh>0.f?p.cte.coh_r:peak};
}
__host__ __device__ static U::Result Reference(const Point& p){
  if(p.cte.ModulusE==0.f&&p.cte.ModulusK==0.f&&p.cte.ModulusG==0.f){U::Result r{};r.state=p.input;r.status=U::Status::Elastic;r.reason=U::Reason::WithinYield;r.kappa_continuous=p.input.kappa;return r;}
  const auto strength=ReferenceStrength(p);
  const U::Material m={p.cte.ModulusK,p.cte.ModulusG,p.cte.phi,p.cte.phi_r,p.cte.n_phi,strength.peak,strength.residual,p.cte.n_coh,p.cte.dlt,p.cte.psiDecay};
  if(p.soft||p.cte.psiDecay>0.f)return U::ConsRelationEPsft(p.input,m,p.fit);
  const auto d=U::UpdateDPvars(m,p.input.kappa,p.fit);return U::ConsRelationEP(p.input,m.ModulusK,m.ModulusG,d.DP_phi,d.DP_kc,d.DP_psi);
}
__global__ void AdapterBatch(unsigned count,const Point* input,Output* output){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i<count){const Point p=input[i];const auto s=p.input.stress;Value value=output[i].adapter;
    value.status=fsoil::ReturnMaterial(make_double2(s.xx,s.xy),make_double2(s.xz,s.yy),make_double2(s.yz,s.zz),p.input.kappa,p.cte,p.fit,p.soft,p.trigger,value.xx_xy,value.xz_yy,value.yz_zz,value.kappa);
    output[i].adapter=value;output[i].reference=Reference(p);}
}
static void Need(bool b,const std::string& s){if(!b)throw std::runtime_error(s);}
static void Cu(cudaError_t e){Need(e==cudaSuccess,cudaGetErrorString(e));}
template<class T>static bool Bits(T a,T b){return std::memcmp(&a,&b,sizeof(T))==0;}
static std::array<double,6> Six(const U::Stress& s){return {s.xx,s.yy,s.zz,s.xy,s.yz,s.xz};}
static U::State State(const Value& v){return {{v.xx_xy.x,v.xz_yy.y,v.yz_zz.y,v.xx_xy.y,v.yz_zz.x,v.xz_yy.x},v.kappa};}
static bool SameState(const U::State& a,const U::State& b){const auto x=Six(a.stress),y=Six(b.stress);for(unsigned i=0;i<6;i++)if(!Bits(x[i],y[i]))return false;return Bits(a.kappa,b.kappa);}
static std::array<float,17> Fields(const StSoilCte& c){return {c.coh,c.phi,c.dlt,c.phi_r,c.coh_r,c.n_phi,c.n_coh,c.SoilTriggerFos,c.ModulusE,c.PRvs,c.ModulusG,c.ModulusK,c.PoreWaterRho,c.PoreWaterBulkModulus,c.Porosity,c.HydraulicConductivity,c.psiDecay};}
static bool SamePoint(const Point& a,const Point& b){const auto x=Fields(a.cte),y=Fields(b.cte);for(unsigned i=0;i<x.size();i++)if(!Bits(x[i],y[i]))return false;return a.id==b.id&&a.fit==b.fit&&a.soft==b.soft&&a.trigger==b.trigger&&SameState(a.input,b.input);}
static U::Status Status(fsoil::Status s){switch(s){
  case fsoil::Status::Invalid:return U::Status::Invalid;case fsoil::Status::Elastic:return U::Status::Elastic;
  case fsoil::Status::Smooth:return U::Status::Smooth;case fsoil::Status::Apex:return U::Status::Apex;
  case fsoil::Status::TensionRepair:return U::Status::TensionRepair;case fsoil::Status::NoAdmissibleFlow:return U::Status::NoAdmissibleFlow;
  case fsoil::Status::NonConverged:return U::Status::NonConverged;default:return U::Status::UnresolvedPath;}}
static bool SameValue(const Value& a,const Value& b){return a.status==b.status&&SameState(State(a),State(b));}
static bool SameReference(const U::Result& a,const U::Result& b){
  const std::array<double,13> x={a.trial_I,a.trial_q,a.returned_I,a.returned_q,a.trial_yield,a.kappa_continuous,a.lambda_shear,a.lambda_apex,a.lambda_tension,a.root_residual,a.root_budget,a.minus_dF_dlambda,a.radial_slope_upper_bound};
  const std::array<double,13> y={b.trial_I,b.trial_q,b.returned_I,b.returned_q,b.trial_yield,b.kappa_continuous,b.lambda_shear,b.lambda_apex,b.lambda_tension,b.root_residual,b.root_budget,b.minus_dF_dlambda,b.radial_slope_upper_bound};
  for(unsigned i=0;i<x.size();i++)if(!Bits(x[i],y[i]))return false;return SameState(a.state,b.state)&&a.status==b.status&&a.reason==b.reason&&a.iterations==b.iterations&&a.repair==b.repair;
}
static Value Sentinel(unsigned n){const double d=100.+n;return {make_double2(std::numeric_limits<double>::quiet_NaN(),d+1),make_double2(d+2,d+3),make_double2(d+4,d+5),.375f,fsoil::Status::Invalid};}
static Value CpuAdapter(const Point& p,const Value& sentinel){const auto s=p.input.stress;tsymatrix3d trial{},corrected{};
  trial.xx=s.xx;trial.yy=s.yy;trial.zz=s.zz;trial.xy=s.xy;trial.yz=s.yz;trial.xz=s.xz;
  const auto t=State(sentinel).stress;corrected.xx=t.xx;corrected.yy=t.yy;corrected.zz=t.zz;corrected.xy=t.xy;corrected.yz=t.yz;corrected.xz=t.xz;
  float k=sentinel.kappa;const auto status=fsoil::ReturnMaterial(trial,p.input.kappa,p.cte,p.fit,p.soft,p.trigger,corrected,k);
  return {make_double2(corrected.xx,corrected.xy),make_double2(corrected.xz,corrected.yy),make_double2(corrected.yz,corrected.zz),k,status};
}
static float Radians(float d){return float(double(d)*3.1415926535897932384626433832795/180.);}
static StSoilCte Cte(float psi,bool soft){StSoilCte c{};c.ModulusE=20e6f;c.PRvs=.33f;c.ModulusK=float(double(c.ModulusE)/(3.*(1.-2.*double(c.PRvs))));c.ModulusG=float(double(c.ModulusE)/(2.*(1.+double(c.PRvs))));
  c.phi=Radians(25);c.phi_r=Radians(soft?20.f:25.f);c.n_phi=soft?5.f:0.f;c.coh=5000;c.coh_r=soft?1000.f:5000.f;c.n_coh=soft?5.f:0.f;c.dlt=Radians(psi);c.psiDecay=soft?.2f:0.f;c.SoilTriggerFos=1;return c;}
struct Case{std::string name;Point point;U::Status expected;};
static std::vector<Case> Cases(){std::vector<Case> cases;const U::State initial={{-10000.,-70000.,20000.,4000.,-2500.,3500.},.02f};
  auto add=[&](std::string name,StSoilCte c,TpDPCtes fit,bool soft,bool trigger,U::Status expected){cases.push_back({name,{unsigned(cases.size()),initial,c,fit,soft,trigger},expected});};
  for(auto fit:{DP_PS,DP_C,DP_MC})for(float psi:{0.f,2.5f,-5.f})for(bool soft:{false,true})add("fit"+std::to_string(int(fit))+"_psi"+std::to_string(psi)+(soft?"_soft":"_basic"),Cte(psi,soft),fit,soft,false,U::Status::Smooth);
  for(bool soft:{false,true}){auto c=Cte(-5,soft);c.coh_r=1000;c.SoilTriggerFos=2;add(soft?"FOS_soft_cp2500":"FOS_basic_no_strength_reduction",c,DP_PS,soft,true,U::Status::Smooth);}
  {auto c=Cte(-5,false);c.psiDecay=.2f;add("sf_only_soft_flag_false",c,DP_PS,false,false,U::Status::Smooth);}
  {auto c=Cte(0,true);c.phi=c.phi_r=0;add("phi_zero_soft",c,DP_PS,true,false,U::Status::Smooth);}
  for(bool preservation:{false,true}){StSoilCte c{};c.SoilTriggerFos=1;add(preservation?"fluid_adapter_preservation_sentinel":"fluid_valid_zero_initial",c,DP_PS,preservation,false,U::Status::Elastic);if(!preservation)cases.back().point.input={{0,0,0,0,0,0},0.f};}
  {auto c=Cte(0,false);c.ModulusG=0;add("invalid_positive_E_G0",c,DP_PS,false,false,U::Status::Invalid);}
  {auto c=Cte(-5,true);c.SoilTriggerFos=10;add("invalid_cp_eff_below_cr",c,DP_PS,true,true,U::Status::Invalid);}
  {auto c=Cte(-5,false);c.psiDecay=.2f;c.SoilTriggerFos=2;add("sf_only_trigger_true_cp_not_reduced",c,DP_PS,false,true,U::Status::Smooth);
    const auto s=ReferenceStrength(cases.back().point);Need(Bits(s.peak,5000.f)&&Bits(s.residual,5000.f),"Dilation-only trigger must keep cp=cr=5000");}
  {auto c=Cte(0,true);c.n_coh=0;c.coh_r=c.coh;c.SoilTriggerFos=2;add("phi_only_FOS_constant_cp2500",c,DP_PS,true,true,U::Status::Smooth);
    const auto s=ReferenceStrength(cases.back().point);Need(Bits(s.peak,2500.f)&&Bits(s.residual,2500.f),"Phi-only FOS must use constant cohesion=2500");}
  Need(cases.size()==28,"Declared adapter point count changed");return cases;
}
static double StressDifference(const U::Stress& a,const U::Stress& b){const auto x=Six(a),y=Six(b);double e=0.;for(unsigned i=0;i<6;i++)e=(std::max)(e,std::abs(x[i]-y[i]));return e;}
struct Budget{double stress,strain;};
static Budget Limits(const Point& p,const U::Result& ref){const auto t=U::GetInvariants(p.input.stress);const auto strength=ReferenceStrength(p);
  const U::Material m={p.cte.ModulusK,p.cte.ModulusG,p.cte.phi,p.cte.phi_r,p.cte.n_phi,strength.peak,strength.residual,p.cte.n_coh,p.cte.dlt,p.cte.psiDecay};const auto d=U::UpdateDPvars(m,ref.kappa_continuous,p.fit);const double scale=(std::max)({1.,std::abs(t.I),t.q,std::abs(d.DP_kc)});
  return {5e-10*scale+1e-8,2e-12+2e-10*(std::max)({std::abs(ref.lambda_shear),std::abs(ref.lambda_tension),std::abs(ref.kappa_continuous-double(p.input.kappa))})};}
static double Check(const Case& c,const Value& actual,const U::Result& ref,const Value& sentinel){Need(ref.status==c.expected&&Status(actual.status)==ref.status,c.name+": adapter/reference status mismatch");
  if(!U::CommitAllowed(ref.status)){Need(SameState(State(actual),State(sentinel))&&SameState(ref.state,c.point.input),c.name+": failed adapter wrote sentinel or reference wrote input");return 0.;}
  const auto state=State(actual);const double error=StressDifference(state.stress,ref.state.stress);Need(U::Finite(state.stress)&&error<=Limits(c.point,ref).stress&&Bits(state.kappa,ref.state.kappa),c.name+": layout/state/storage differs from same-backend frozen U");return error;
}
struct Device{Point* input=nullptr;Output* output=nullptr;~Device(){if(output)cudaFree(output);if(input)cudaFree(input);}};
int main(int argc,char** argv){unsigned current=~0u;try{
  Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_DIR");const fs::path out=argv[2];Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh result directory required");const auto cases=Cases();const unsigned count=unsigned(cases.size()),capacity=count+2;
  std::vector<Point> input(capacity);std::vector<Output> result(capacity);for(unsigned n=0;n<count;n++)input[n]=cases[n].point;input[count]=input[0];input[count].id=0xf1234567;input[count+1]=input[count];input[count+1].id++;
  for(unsigned n=0;n<capacity;n++){result[n].adapter=Sentinel(n);result[n].reference={};result[n].reference.state=State(Sentinel(n+100));result[n].reference.status=U::Status::Invalid;result[n].reference.reason=U::Reason::InvalidInput;result[n].reference.iterations=0x12345678+n;result[n].reference.repair=true;}
  const auto before=result;Need(fs::create_directory(out),"Cannot claim output directory");Cu(cudaSetDevice(0));Device device;
  Cu(cudaMalloc(reinterpret_cast<void**>(&device.input),capacity*sizeof(Point)));Cu(cudaMalloc(reinterpret_cast<void**>(&device.output),capacity*sizeof(Output)));Cu(cudaMemcpy(device.input,input.data(),capacity*sizeof(Point),cudaMemcpyHostToDevice));Cu(cudaMemcpy(device.output,result.data(),capacity*sizeof(Output),cudaMemcpyHostToDevice));
  AdapterBatch<<<1,64>>>(count,device.input,device.output);Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());std::vector<Point> after(capacity);Cu(cudaMemcpy(after.data(),device.input,capacity*sizeof(Point),cudaMemcpyDeviceToHost));Cu(cudaMemcpy(result.data(),device.output,capacity*sizeof(Output),cudaMemcpyDeviceToHost));
  for(unsigned n=0;n<capacity;n++)Need(SamePoint(input[n],after[n]),"Input defined scalar changed");for(unsigned n=count;n<capacity;n++)Need(SameValue(result[n].adapter,before[n].adapter)&&SameReference(result[n].reference,before[n].reference),"Output tail defined member changed");
  std::ofstream csv(out/"adapters.csv");csv<<std::setprecision(17)<<"id,name,status,soft,trigger,coh_input_Pa,FOS,coh_effective_float_Pa,coh_residual_effective_float_Pa,CPU_U_stress_max_Pa,GPU_U_stress_max_Pa,CPU_GPU_stress_max_Pa,combined_stress_budget_Pa,CPU_GPU_continuous_kappa,combined_strain_budget,CPU_kappa,GPU_kappa,saved_kappa_bits_equal,CPU_xx,CPU_yy,CPU_zz,CPU_xy,CPU_yz,CPU_xz,GPU_xx,GPU_yy,GPU_zz,GPU_xy,GPU_yz,GPU_xz\n";
  unsigned failed=0,savedbits=0;double maxCPU=0,maxGPU=0,maxCross=0,maxK=0;
  for(unsigned n=0;n<count;n++){current=n;const auto& c=cases[n];const auto cpu=CpuAdapter(c.point,before[n].adapter);const auto ref=Reference(c.point);const auto& gpu=result[n].adapter;const auto& dref=result[n].reference;
    const double ec=Check(c,cpu,ref,before[n].adapter),eg=Check(c,gpu,dref,before[n].adapter);Need(ref.status==dref.status,c.name+": CPU/GPU reference classification");const auto bc=Limits(c.point,ref),bg=Limits(c.point,dref);double cross=0.,dk=0.;
    if(U::CommitAllowed(ref.status)){cross=StressDifference(State(cpu).stress,State(gpu).stress);dk=std::abs(ref.kappa_continuous-dref.kappa_continuous);Need(cross<=bc.stress+bg.stress&&dk<=bc.strain+bg.strain,c.name+": backend difference exceeds sum of original budgets");}
    else failed++;
    const bool kb=Bits(cpu.kappa,gpu.kappa);savedbits+=unsigned(!kb);maxCPU=(std::max)(maxCPU,ec);maxGPU=(std::max)(maxGPU,eg);maxCross=(std::max)(maxCross,cross);maxK=(std::max)(maxK,dk);
    const auto strength=ReferenceStrength(c.point);csv<<n<<','<<c.name<<','<<unsigned(ref.status)<<','<<c.point.soft<<','<<c.point.trigger<<','<<c.point.cte.coh<<','<<c.point.cte.SoilTriggerFos<<','<<strength.peak<<','<<strength.residual<<','<<ec<<','<<eg<<','<<cross<<','<<bc.stress+bg.stress<<','<<dk<<','<<bc.strain+bg.strain<<','<<cpu.kappa<<','<<gpu.kappa<<','<<kb;for(double x:Six(State(cpu).stress))csv<<','<<x;for(double x:Six(State(gpu).stress))csv<<','<<x;csv<<'\n';
  }
  Need(failed==2,"Two invalid noncommit witnesses required");csv.flush();Need(bool(csv),"CSV write failed");std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_material_adapters_r1\",\"passed\":true,\"points\":28,\"kernel_launches\":1,\"failed_adapter_sentinel_checks_per_backend\":2,\"input_defined_scalar_checks\":30,\"output_tail_defined_member_checks\":2,\"max_CPU_adapter_U_stress_Pa\":"<<maxCPU<<",\"max_GPU_adapter_U_stress_Pa\":"<<maxGPU<<",\"max_CPU_GPU_stress_difference_Pa\":"<<maxCross<<",\"max_CPU_GPU_continuous_kappa_difference\":"<<maxK<<",\"saved_kappa_bits_different_descriptive\":"<<savedbits<<",\"CPU_adapter_is_actual_NVCC_MSVC_host_code\":true,\"frozen_U_is_implementation_reference_only\":true,\"POD_padding_compared\":false,\"engine_objects\":0,\"spatial_solver\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<"point="<<current<<" : "<<e.what()<<'\n';return 1;}}

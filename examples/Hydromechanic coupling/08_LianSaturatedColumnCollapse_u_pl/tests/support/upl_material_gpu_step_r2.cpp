// Actual GPU Symplectic wrappers only; no JSph run, neighbours or physical step.
#include <cuda_runtime.h>
#include "JSphGpuSimple_ker.h"
#include "JAppInfo.h"
#include "upl_material_shared_cases_r1.h"
#include <array>
#include <iostream>
#include <iterator>
namespace fs=std::filesystem;
using namespace upl_material_cases_r1;
JAppInfo AppInfo("UplMaterialGpuStep","r2","06-11-2026");
static constexpr unsigned Cap=3;
static void Cu(cudaError_t e){Need(e==cudaSuccess,cudaGetErrorString(e));}
template<class T>struct Device{
  T* p=nullptr;Device(){Cu(cudaMalloc(reinterpret_cast<void**>(&p),Cap*sizeof(T)));}
  ~Device(){if(p)cudaFree(p);}Device(const Device&)=delete;Device& operator=(const Device&)=delete;
  void Put(const std::array<T,Cap>& v){Cu(cudaMemcpy(p,v.data(),sizeof(T)*Cap,cudaMemcpyHostToDevice));}
  std::array<T,Cap> Get()const{std::array<T,Cap> v;Cu(cudaMemcpy(v.data(),p,sizeof(T)*Cap,cudaMemcpyDeviceToHost));return v;}
};
template<class T>static bool Scalar(T a,T b){return !std::memcmp(&a,&b,sizeof(T));}
static Stress Named(const tsymatrix3d& s){return {s.xx,s.yy,s.zz,s.xy,s.yz,s.xz};}
static tsymatrix3d Native(const Stress& s){return TSymMatrix3d(s.xx,s.xy,s.xz,s.yy,s.yz,s.zz);}
static bool Same(const tsymatrix3d& a,const tsymatrix3d& b){return SameState({Named(a),0.f},{Named(b),0.f});}
static bool Same(const tsymatrix3f& a,const tsymatrix3f& b){return Scalar(a.xx,b.xx)&&Scalar(a.xy,b.xy)&&Scalar(a.xz,b.xz)&&Scalar(a.yy,b.yy)&&Scalar(a.yz,b.yz)&&Scalar(a.zz,b.zz);}
static bool Same(float4 a,float4 b){return Scalar(a.x,b.x)&&Scalar(a.y,b.y)&&Scalar(a.z,b.z)&&Scalar(a.w,b.w);}
static bool Same(float3 a,float3 b){return Scalar(a.x,b.x)&&Scalar(a.y,b.y)&&Scalar(a.z,b.z);}
static bool Same(double2 a,double2 b){return Scalar(a.x,b.x)&&Scalar(a.y,b.y);}
template<class T>static bool Same(T a,T b){return Scalar(a,b);}
template<class T>static void AllSame(const std::array<T,Cap>& a,const std::array<T,Cap>& b){for(unsigned i=0;i<Cap;i++)Need(Same(a[i],b[i]),"Protected input member changed");}
struct Step{
  Device<float4> prevel,vel;Device<float> ar,oldk,k,dk;Device<float3> ace;
  Device<tsymatrix3d> trial,sigma;Device<tsymatrix3f> rate;Device<typecode> code;
  Device<double2> movxy;Device<double> movz;Device<unsigned> error;
  unsigned failureChecks=0,tailChecks=0,inputChecks=0,preHistory=0,corHistory=0;double maxStress=0;
  void Run(const Case& c,const Row& cpu,bool corrector,unsigned soft,std::ostream& out){
    StSoilCte soil{};const auto& m=c.point.material;soil.ModulusK=m.bulk;soil.ModulusG=m.shear;
    soil.phi=soil.phi_r=m.phi;soil.coh=m.cohesion_peak;soil.coh_r=m.cohesion_residual;soil.n_coh=m.cohesion_decay;
    soil.dlt=m.psi0;soil.psiDecay=m.psi_decay;soil.MaterialReturn=1;soil.SoilTriggerFos=1.f;
    cusphs::CteInteractionUpTStep(&soil,soft,0);
    std::array<float4,Cap> pv,ov;std::array<float,Cap> a,kold,ko,dko;std::array<float3,Cap> ac;
    std::array<tsymatrix3d,Cap> tr,so;std::array<tsymatrix3f,Cap> sr;
    std::array<typecode,Cap> co;std::array<double2,Cap> xy;std::array<double,Cap> z;std::array<unsigned,Cap> flags;
    for(unsigned q=0;q<Cap;q++){
      const double d=double(q+1);pv[q]=make_float4(0,0,0,2100);a[q]=0;ac[q]=make_float3(0,0,0);sr[q]=TSymMatrix3f();
      tr[q]=Native(c.point.state.stress);kold[q]=c.point.state.kappa;co[q]=CODE_TYPE_FLUID;
      ov[q]=make_float4(float(100+d),float(200+d),float(300+d),float(400+d));
      so[q]=TSymMatrix3d(10*d,20*d,30*d,40*d,50*d,60*d);ko[q]=float(70+d);dko[q]=.25f;
      xy[q]=make_double2(80*d,90*d);z[q]=100*d;flags[q]=(q?0x1234abcdu+q:0u);
    }
    prevel.Put(pv);vel.Put(ov);ar.Put(a);oldk.Put(kold);k.Put(ko);dk.Put(dko);ace.Put(ac);
    trial.Put(tr);sigma.Put(so);rate.Put(sr);code.Put(co);movxy.Put(xy);movz.Put(z);error.Put(flags);
    const double dt=1./1024.;const auto gravity=TFloat3(0);
    if(corrector)cusphs::ComputeStepSymplecticCor(false,false,false,DP_PS,MDBC2_None,1,0,prevel.p,ar.p,ace.p,nullptr,
      trial.p,oldk.p,rate.p,nullptr,nullptr,dt*.5,dt,2100,700,3000,gravity,code.p,movxy.p,movz.p,vel.p,sigma.p,k.p,dk.p,nullptr,{},error.p);
    else cusphs::ComputeStepSymplecticPre(false,false,false,DP_PS,1,0,prevel.p,ar.p,ace.p,nullptr,
      trial.p,oldk.p,rate.p,nullptr,dt*.5,2100,700,3000,gravity,code.p,movxy.p,movz.p,vel.p,sigma.p,k.p,dk.p,nullptr,{},error.p);
    Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());
    const auto v=vel.Get();const auto s=sigma.Get();const auto nk=k.Get();const auto ndk=dk.Get();
    const auto mx=movxy.Get();const auto mz=movz.Get();const auto errors=error.Get();const auto codes=code.Get();
    AllSame(pv,prevel.Get());AllSame(a,ar.Get());AllSame(kold,oldk.Get());AllSame(ac,ace.Get());AllSame(tr,trial.Get());AllSame(sr,rate.Get());AllSame(co,codes);inputChecks+=7*Cap;
    for(unsigned q=1;q<Cap;q++){
      Need(Same(v[q],ov[q])&&Same(s[q],so[q])&&Same(nk[q],ko[q])&&Same(ndk[q],dko[q])&&Same(mx[q],xy[q])&&Same(mz[q],z[q])&&errors[q]==flags[q],"One of two output tail protections changed");tailChecks++;
    }
    const bool valid=CommitAllowed(c.expected);const unsigned expected=valid?0u:(1u<<unsigned(c.expected));
    Need(errors[0]==expected,"Actual integration-wrapper failure status bits differ");double gap=0,budget=0;
    if(valid){
      const Stress actual=Named(s[0]),target=StressFrom(cpu,"new_");gap=StressGap(actual,target);
      const auto ti=InvariantIndependent(c.point.state.stress),ni=InvariantIndependent(actual);
      const double own=8192.*DBL_EPSILON*(std::max)({1.,std::fabs(ti.I),ti.q,std::fabs(ni.I),ni.q});
      budget=own+Number(cpu,"tensor_budget_Pa");Need(gap<=budget,"Actual wrapper stress exceeds original combined tensor budgets");
      Need(Same(v[0],pv[0])&&Scalar(mx[0].x,0.)&&Scalar(mx[0].y,0.)&&Scalar(mz[0],0.),"Zero-kinematic wrapper field changed");
      const float expectedK=corrector?float(Number(cpu,"new_kappa")):kold[0];
      Need(Scalar(nk[0],expectedK),"Pre history restore or Cor saved-history commit differs from actual CPU expectation");
      const float expectedDk=corrector?dko[0]+fmaxf(expectedK-kold[0],0.f):dko[0];Need(Scalar(ndk[0],expectedDk),"Existing kplasticdk stage policy differs");
      if(corrector)corHistory++;else preHistory++;maxStress=(std::max)(maxStress,gap);
    }else{
      Need(Same(v[0],ov[0])&&Same(s[0],so[0])&&Scalar(nk[0],ko[0])&&Scalar(ndk[0],dko[0])&&Same(mx[0],xy[0])&&Scalar(mz[0],z[0]),"Rejected native point wrote output before returning");failureChecks++;
    }
    out<<c.point.id<<','<<(corrector?"Cor":"Pre")<<','<<Name(c.expected)<<','<<soft<<','<<errors[0]<<','<<gap<<','<<budget<<','<<nk[0]<<','<<ndk[0]<<','<<StateBits({Named(s[0]),nk[0]})<<'\n';
  }
};
int main(int argc,char** argv){unsigned current=~0u;
  try{
    Need(argc==7&&std::string(argv[1])=="--source"&&std::string(argv[3])=="--cpu"&&std::string(argv[5])=="--out","Use --source ORIGINAL132.csv --cpu ACTUAL_CPU_POINTS.csv --out FRESH_DIR");
    const fs::path tests=fs::path(__FILE__).parent_path().parent_path(),source=argv[2],cp=argv[4],out=argv[6];
    Need(tests.is_absolute()&&fs::equivalent(source,tests/"outputs/upl_material_return_CPU_result_r1/points.csv"),"Retained original132 source required");
    Need(fs::equivalent(cp,tests/"outputs/upl_material_shared_CPU_r1/result/points.csv"),"Actual separate MSVC CPU points required");
    Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh output/existing parent required");
    const auto cases=Load(source);const auto rows=ReadTable(cp);std::map<unsigned,Row> cpu;
    std::ifstream doneCPU(cp.parent_path()/"completion.json");const std::string closed((std::istreambuf_iterator<char>(doneCPU)),std::istreambuf_iterator<char>());
    Need(closed.find("\"stage\":\"upl_material_shared_cpu_r1\"")!=std::string::npos&&closed.find("\"passed\":true")!=std::string::npos&&closed.find("\"rows\":71")!=std::string::npos,"Closed actual CPU fixture required");
    for(const auto& r:rows)Need(cpu.emplace(unsigned(std::stoul(r.at("id"))),r).second,"Duplicate CPU rowID");Need(cases.size()==71&&cpu.size()==71,"Exactly71 cases required");
    for(const auto& c:cases){const auto& r=cpu.at(c.point.id);Need(r.at("input_bits")==PointBits(c.point)&&r.at("status")==Name(c.expected)&&r.at("path")==c.path&&r.at("branch")==c.branch,"Actual CPU input/status binding differs");}
    Need(fs::create_directory(out),"Cannot claim fresh output");Cu(cudaSetDevice(0));Step step;
    std::ofstream csv(out/"steps.csv");csv<<std::setprecision(17)<<"id,stage,expected_CPU_status,strainsoftening_constant,status_bits,stress_CPU_difference_Pa,combined_original_tensor_budget_Pa,kappa_output,kplasticdk_output,native_output_state_bits\n";
    for(unsigned q=0;q<cases.size();q++){const auto& c=cases[q];current=c.point.id;step.Run(c,cpu.at(current),false,q&1u,csv);step.Run(c,cpu.at(current),true,(q+1u)&1u,csv);}
    csv.flush();Need(bool(csv)&&step.failureChecks==34&&step.preHistory==54&&step.corHistory==54&&step.tailChecks==284&&step.inputChecks==2982,"Declared wrapper coverage or CSV differs");
    std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_material_gpu_step_r2\",\"passed\":true,\"case_rows\":71,\"actual_wrapper_calls\":142,\"Pre_history_checks\":54,\"Cor_history_checks\":54,\"failure_native_unchanged_checks\":34,\"tail_point_checks\":284,\"protected_input_record_checks\":2982,\"max_actual_CPU_stress_difference_Pa\":"<<step.maxStress<<",\"NonConverged_witness\":false,\"legacy_default_equivalence_claim\":false,\"spatial_solver\":false,\"physical_acceptance\":false}\n";
    done.flush();Need(bool(done),"Completion write failed");return 0;
  }catch(const std::exception& e){std::cerr<<"id="<<current<<" : "<<e.what()<<'\n';return 1;}
}

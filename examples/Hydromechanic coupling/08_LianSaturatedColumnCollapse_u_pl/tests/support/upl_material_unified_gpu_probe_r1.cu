// Standalone mathematical CUDA probe. No engine objects, particle integration or production adapter.
#include <cuda_runtime.h>
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
using Matrix=std::array<std::array<double,3>,3>;
struct Point{unsigned id;U::State input;U::Material material;TpDPCtes fit;bool constant_entry;};
struct Output{U::Result primary,basic;};
__global__ void ReturnBatch(unsigned count,const Point* input,Output* output){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i<count){const Point p=input[i];const auto r=U::ConsRelationEPsft(p.input,p.material,p.fit);output[i].primary=r;output[i].basic=r;
    if(p.constant_entry){const auto d=U::UpdateDPvars(p.material,p.input.kappa,p.fit);
      output[i].basic=U::ConsRelationEP(p.input,p.material.ModulusK,p.material.ModulusG,d.DP_phi,d.DP_kc,d.DP_psi);}}
}
static void Need(bool b,const std::string& s){if(!b)throw std::runtime_error(s);}
static void Cu(cudaError_t e){Need(e==cudaSuccess,cudaGetErrorString(e));}
template<class T>static bool Bits(T a,T b){return std::memcmp(&a,&b,sizeof(T))==0;}
static std::array<double,6> Six(const U::Stress& s){return {s.xx,s.yy,s.zz,s.xy,s.yz,s.xz};}
static std::array<float,10> Fields(const U::Material& m){return {m.ModulusK,m.ModulusG,m.phi_p,m.phi_r,m.n_p,m.coh_p,m.coh_r,m.n_c,m.psi0,m.sf};}
static bool SameState(const U::State& a,const U::State& b){const auto x=Six(a.stress),y=Six(b.stress);for(unsigned i=0;i<6;i++)if(!Bits(x[i],y[i]))return false;return Bits(a.kappa,b.kappa);}
static bool SamePoint(const Point& a,const Point& b){const auto x=Fields(a.material),y=Fields(b.material);for(unsigned i=0;i<10;i++)if(!Bits(x[i],y[i]))return false;return a.id==b.id&&a.fit==b.fit&&a.constant_entry==b.constant_entry&&SameState(a.input,b.input);}
static bool SameResult(const U::Result& a,const U::Result& b){
  const std::array<double,13> x={a.trial_I,a.trial_q,a.returned_I,a.returned_q,a.trial_yield,a.kappa_continuous,a.lambda_shear,a.lambda_apex,a.lambda_tension,a.root_residual,a.root_budget,a.minus_dF_dlambda,a.radial_slope_upper_bound};
  const std::array<double,13> y={b.trial_I,b.trial_q,b.returned_I,b.returned_q,b.trial_yield,b.kappa_continuous,b.lambda_shear,b.lambda_apex,b.lambda_tension,b.root_residual,b.root_budget,b.minus_dF_dlambda,b.radial_slope_upper_bound};
  for(unsigned i=0;i<x.size();i++)if(!Bits(x[i],y[i]))return false;
  return SameState(a.state,b.state)&&a.status==b.status&&a.reason==b.reason&&a.iterations==b.iterations&&a.repair==b.repair;
}
static Matrix Tensor(const U::Stress& s){return {{{s.xx,s.xy,s.xz},{s.xy,s.yy,s.yz},{s.xz,s.yz,s.zz}}};}
static double Trace(const Matrix& a){return a[0][0]+a[1][1]+a[2][2];}
static Matrix Deviator(Matrix a){const double mean=Trace(a)/3.;for(int i=0;i<3;i++)a[i][i]-=mean;return a;}
static double Dot(const Matrix& a,const Matrix& b){double d=0.;for(int i=0;i<3;i++)for(int j=0;j<3;j++)d+=a[i][j]*b[i][j];return d;}
static U::Stress Rotate(const U::Stress& s){
  const Matrix R={{{1./9.,8./9.,4./9.},{8./9.,1./9.,-4./9.},{-4./9.,4./9.,-7./9.}}};const auto a=Tensor(s);Matrix b{};
  for(int i=0;i<3;i++)for(int j=0;j<3;j++)for(int k=0;k<3;k++)for(int l=0;l<3;l++)b[i][j]+=R[i][k]*a[k][l]*R[j][l];
  return {b[0][0],b[1][1],b[2][2],b[0][1],b[1][2],b[0][2]};
}
static U::Stress Make(double I,double q){return {I/3.+q,I/3.-q,I/3.,0.,0.,0.};}
static double StressDifference(const U::Stress& a,const U::Stress& b){const auto x=Six(a),y=Six(b);double e=0.;for(int i=0;i<6;i++)e=(std::max)(e,std::abs(x[i]-y[i]));return e;}
struct ReferenceDP{double DP_phi,DP_kc,DP_psi;};
// Independent published coefficient formulas and exponential laws, not the tested UpdateDPvars.
static ReferenceDP ReferenceCoefficients(const U::Material& m,double k,TpDPCtes fit){
  const double phi=m.phi_r+(double(m.phi_p)-m.phi_r)*std::exp(-double(m.n_p)*k),coh=m.coh_r+(double(m.coh_p)-m.coh_r)*std::exp(-double(m.n_c)*k),psi=double(m.psi0)*std::exp(-double(m.sf)*k);
  if(fit==DP_PS){const double a=std::tan(phi),b=std::tan(psi);return {a/std::sqrt(9.+12.*a*a),3.*coh/std::sqrt(9.+12.*a*a),b/std::sqrt(9.+12.*b*b)};}
  const double side=fit==DP_MC?1.:-1.,r3=std::sqrt(3.);return {2.*std::sin(phi)/(r3*(3.+side*std::sin(phi))),6.*coh*std::cos(phi)/(r3*(3.+side*std::sin(phi))),2.*std::sin(psi)/(r3*(3.+side*std::sin(psi)))};
}
static float Radians(float degrees){return float(double(degrees)*3.1415926535897932384626433832795/180.);}
static U::Material Law(float psi,bool soft){const float E=20e6f,nu=.33f;
  return {float(double(E)/(3.*(1.-2.*double(nu)))),float(double(E)/(2.*(1.+double(nu)))),Radians(25),Radians(soft?20.f:25.f),soft?5.f:0.f,5000.f,soft?1000.f:5000.f,soft?5.f:0.f,Radians(psi),soft?.2f:0.f};}
struct Case{std::string name;Point point;U::Stress expected;double kappa,lambda;U::Status status;int rotated_from=-1;};
static Case Manufactured(const std::string& name,const U::Material& m,TpDPCtes fit,double Itr,double qtr,double Inew,double qnew,double kappa,double lambda,U::Status status,bool constant){
  return {name,{0,{Make(Itr,qtr),.02f},m,fit,constant},Make(Inew,qnew),kappa,lambda,status,-1};
}
static std::vector<Case> Cases(){std::vector<Case> cases;
  auto add=[&](Case c,bool rotated){c.point.id=unsigned(cases.size());cases.push_back(c);if(rotated){c.name+="_rot";c.rotated_from=int(c.point.id);c.point.id=unsigned(cases.size());c.point.input.stress=Rotate(c.point.input.stress);c.expected=Rotate(c.expected);cases.push_back(c);}};
  for(auto fit:{DP_PS,DP_C,DP_MC})for(float psi:{0.f,2.5f,-5.f})for(bool soft:{false,true}){
    const auto m=Law(psi,soft);const double lambda=.001,k=double(.02f)+lambda/std::sqrt(3.);const auto d=ReferenceCoefficients(m,k,fit);const double I=-60000.,q=d.DP_kc-d.DP_phi*I;
    add(Manufactured(std::string(soft?"soft_smooth_":"constant_smooth_")+std::to_string(int(fit))+"_"+std::to_string(psi),m,fit,I+9.*double(m.ModulusK)*d.DP_psi*lambda,q+double(m.ModulusG)*lambda,I,q,k,lambda,U::Status::Smooth,!soft),true);
  }
  for(auto fit:{DP_PS,DP_C,DP_MC})for(float psi:{0.f,2.5f,-5.f})for(bool shear:{false,true}){
    const auto m=Law(psi,true);const double q=shear?.003*double(m.ModulusG):0.,k=double(.02f)+q/(std::sqrt(3.)*double(m.ModulusG));const auto d=ReferenceCoefficients(m,k,fit);const double It=d.DP_kc/d.DP_phi,lambda=psi>0?.01:q/double(m.ModulusG),Itr=psi>0?It+9.*double(m.ModulusK)*d.DP_psi*lambda:It+2000.;
    add(Manufactured("soft_tip_"+std::to_string(int(fit))+"_"+std::to_string(psi)+(shear?"_shear":"_hydro"),m,fit,Itr,q,It,0.,k,lambda,psi>0?U::Status::Apex:U::Status::TensionRepair,false),false);
  }
  for(bool soft:{false,true}){auto m=Law(0,soft);m.phi_p=m.phi_r=0.f;const double lambda=.001,k=double(.02f)+lambda/std::sqrt(3.);const auto d=ReferenceCoefficients(m,k,DP_PS);
    add(Manufactured(soft?"soft_phi0":"constant_phi0",m,DP_PS,-10000.,d.DP_kc+double(m.ModulusG)*lambda,-10000.,d.DP_kc,k,lambda,U::Status::Smooth,!soft),true);}
  for(auto fit:{DP_PS,DP_MC}){const auto m=Law(0,false);auto c=Manufactured("elastic_"+std::to_string(int(fit)),m,fit,-60000.,1000.,-60000.,1000.,double(.02f),0.,U::Status::Elastic,true);add(c,false);}
  for(double f:{5e-6,2e-5}){const U::Material m{1,1,0,0,0,1,1,0,0,0};const double lambda=f<1e-5?0.:f;
    add(Manufactured(f<1e-5?"threshold_below":"threshold_above",m,DP_PS,0.,1.+f,0.,f<1e-5?1.+f:1.,double(.02f)+lambda/std::sqrt(3.),lambda,f<1e-5?U::Status::Elastic:U::Status::Smooth,true),false);}
  for(unsigned which=0;which<6;which++){auto c=Manufactured("invalid_"+std::to_string(which),Law(0,true),DP_PS,-60000.,1000.,-60000.,1000.,double(.02f),0.,U::Status::Invalid,false);
    if(which==0)c.point.input.stress.xy=std::numeric_limits<double>::quiet_NaN();if(which==1)c.point.input.stress.zz=std::numeric_limits<double>::infinity();if(which==2)c.point.input.kappa=std::numeric_limits<float>::quiet_NaN();
    if(which==3)c.point.material.ModulusG=0.f;if(which==4)c.point.material.phi_r=-.1f;if(which==5)c.point.material.sf=-1.f;add(c,false);}
  auto unresolved=Manufactured("uncertified_soft_path",Law(0,true),DP_PS,-60000.,100000.,-60000.,100000.,double(.02f),0.,U::Status::UnresolvedPath,false);
  unresolved.point.input.kappa=0.f;unresolved.point.material.n_p=1e6f;unresolved.point.material.n_c=1e6f;add(unresolved,false);
  Need(cases.size()==69,"Declared 69-point coverage changed");return cases;
}
struct Metrics{double stress_budget,strain_budget,stress_error,kappa_error,volume_error,yield_continuous,yield_saved;};
static Metrics Check(const Case& c,const U::Result& r){
  Need(r.status==c.status,c.name+": wrong return status");const auto& p=c.point;
  if(!U::CommitAllowed(r.status)){Need(SameState(r.state,p.input),c.name+": failed state changed");return {};}
  const auto trial=Tensor(p.input.stress),returned=Tensor(r.state.stress);const double It=Trace(trial),In=Trace(returned);const auto td=Deviator(trial),nd=Deviator(returned);const double qt=std::sqrt(.5*Dot(td,td)),qn=std::sqrt(.5*Dot(nd,nd));const auto d=ReferenceCoefficients(p.material,r.kappa_continuous,p.fit);
  const double scale=(std::max)({1.,std::abs(It),qt,std::abs(d.DP_kc)}),sb=5e-10*scale+1e-8,eb=2e-12+2e-10*(std::max)({std::abs(r.lambda_shear),std::abs(r.lambda_tension),std::abs(c.kappa-double(p.input.kappa))});
  Need(U::Finite(r.state.stress)&&std::isfinite(r.kappa_continuous)&&r.state.kappa>=p.input.kappa&&Bits(r.state.kappa,float(r.kappa_continuous)),c.name+": nonfinite/history storage");
  Matrix ep{};for(int i=0;i<3;i++)for(int j=0;j<3;j++)ep[i][j]=(td[i][j]-nd[i][j])/(2.*double(p.material.ModulusG));
  const double dk=std::sqrt(2.*Dot(ep,ep)/3.),ke=(std::max)(std::abs(dk-(r.kappa_continuous-double(p.input.kappa))),std::abs(r.kappa_continuous-c.kappa));
  const double ve=std::abs((It-In)/(3.*double(p.material.ModulusK))-3.*(d.DP_psi*r.lambda_shear+r.lambda_tension));
  const double se=StressDifference(r.state.stress,c.expected),yc=qn+d.DP_phi*In-d.DP_kc;const auto saved=ReferenceCoefficients(p.material,r.state.kappa,p.fit);
  Need(se<=sb&&ke<=eb&&ve<=eb&&std::abs(r.lambda_shear-c.lambda)<=eb,c.name+": manufactured stress/lambda/compliance");
  if(r.status==U::Status::Elastic)Need(SameState(r.state,p.input)&&r.lambda_shear==0.&&r.lambda_tension==0.,c.name+": elastic state changed");
  else{Need(std::abs(yc)<=sb,c.name+": continuous-history yield residual");
    if(qn>sb){double flow2=0.;for(int i=0;i<3;i++)for(int j=0;j<3;j++){const double e=ep[i][j]-r.lambda_shear*nd[i][j]/(2.*qn);flow2+=e*e;}Need(std::sqrt(flow2)<=eb,c.name+": smooth deviatoric flow");}
    else{const double S=(std::max)({1.,std::abs(It)/3.+std::sqrt(2.)*qt,std::abs(In)/3.+std::sqrt(2.)*qn});Need(std::sqrt(Dot(ep,ep))<=r.lambda_shear/std::sqrt(2.)+64.*DBL_EPSILON*S/double(p.material.ModulusG),c.name+": apex subgradient");}}
  return {sb,eb,se,ke,ve,yc,qn+saved.DP_phi*In-saved.DP_kc};
}
static U::Result Tail(unsigned n){U::Result r{};const double d=n+1.;r.state={{d,2*d,3*d,4*d,5*d,6*d},.125f};r.status=U::Status::Invalid;r.reason=U::Reason::InvalidInput;
  r.trial_I=7*d;r.trial_q=8*d;r.returned_I=9*d;r.returned_q=10*d;r.trial_yield=11*d;r.kappa_continuous=12*d;r.lambda_shear=13*d;r.lambda_apex=14*d;r.lambda_tension=15*d;r.root_residual=16*d;r.root_budget=17*d;r.minus_dF_dlambda=18*d;r.radial_slope_upper_bound=19*d;r.iterations=0x12345678+n;r.repair=true;return r;}
struct Device{Point* inputs=nullptr;Output* outputs=nullptr;~Device(){if(outputs)cudaFree(outputs);if(inputs)cudaFree(inputs);}};
int main(int argc,char** argv){unsigned current=~0u;try{
  Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_DIR");const fs::path out=argv[2];Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh result directory required");const auto cases=Cases();const unsigned count=unsigned(cases.size()),capacity=count+2;
  std::vector<Point> input(capacity);std::vector<Output> result(capacity);for(unsigned n=0;n<count;n++)input[n]=cases[n].point;
  input[count]=input[0];input[count].id=0xf1234567;input[count+1]=input[count];input[count+1].id++;
  for(unsigned n=0;n<capacity;n++)result[n]={Tail(n),Tail(n+100)};const auto original=result;
  Need(fs::create_directory(out),"Cannot claim output");Cu(cudaSetDevice(0));cudaDeviceProp prop{};Cu(cudaGetDeviceProperties(&prop,0));Device device;
  Cu(cudaMalloc(reinterpret_cast<void**>(&device.inputs),capacity*sizeof(Point)));Cu(cudaMalloc(reinterpret_cast<void**>(&device.outputs),capacity*sizeof(Output)));
  Cu(cudaMemcpy(device.inputs,input.data(),capacity*sizeof(Point),cudaMemcpyHostToDevice));Cu(cudaMemcpy(device.outputs,result.data(),capacity*sizeof(Output),cudaMemcpyHostToDevice));
  ReturnBatch<<<1,128>>>(count,device.inputs,device.outputs);Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());std::vector<Point> after(capacity);
  Cu(cudaMemcpy(after.data(),device.inputs,capacity*sizeof(Point),cudaMemcpyDeviceToHost));Cu(cudaMemcpy(result.data(),device.outputs,capacity*sizeof(Output),cudaMemcpyDeviceToHost));
  for(unsigned n=0;n<capacity;n++)Need(SamePoint(input[n],after[n]),"Input scalar changed");for(unsigned n=count;n<capacity;n++)Need(SameResult(result[n].primary,original[n].primary)&&SameResult(result[n].basic,original[n].basic),"Output tail scalar changed");
  std::ofstream rows(out/"points.csv");rows<<std::setprecision(17)<<"id,name,status,reason,device_two_entries_checked,stress_error_Pa,continuous_kappa_error,volume_error,yield_continuous_Pa,yield_saved_Pa,host_GPU_stress_Pa,host_GPU_continuous_kappa,host_GPU_lambda_shear,host_GPU_lambda_tension,stress_budget_Pa,strain_budget,host_saved_kappa,device_saved_kappa,device_continuous_kappa,lambda_shear,lambda_apex,lambda_tension,root_residual_Pa,root_budget_Pa,iterations\n";
  unsigned exact=0,rotated=0,failed=0;double dsmax=0.,dkmax=0.,dlmax=0.,semax=0.,kemax=0.,vemax=0.,ycmax=0.,ysmax=0.,rotmax=0.;
  for(unsigned n=0;n<count;n++){current=n;const auto& c=cases[n];const auto& r=result[n].primary;const auto host=U::ConsRelationEPsft(c.point.input,c.point.material,c.point.fit);const auto a=Check(c,r),b=Check(c,host);
    Need(r.status==host.status&&r.reason==host.reason&&r.repair==host.repair,c.name+": host/device classification");double ds=0.,dk=0.,dl=0.,dt=0.;
    if(U::CommitAllowed(r.status)){ds=StressDifference(r.state.stress,host.state.stress);dk=std::abs(r.kappa_continuous-host.kappa_continuous);dl=std::abs(r.lambda_shear-host.lambda_shear);dt=std::abs(r.lambda_tension-host.lambda_tension);Need(ds<=a.stress_budget+b.stress_budget&&dk<=a.strain_budget+b.strain_budget&&dl<=a.strain_budget+b.strain_budget&&dt<=a.strain_budget+b.strain_budget,c.name+": host/device original-budget sum");}
    else{failed++;Need(SameState(r.state,c.point.input)&&SameState(host.state,c.point.input),c.name+": failure input bits");}
    if(c.point.constant_entry){exact++;Need(SameResult(result[n].primary,result[n].basic),c.name+": same-device constant entries differ");}
    if(c.rotated_from>=0){rotated++;const auto& base=result[unsigned(c.rotated_from)].primary;const double re=StressDifference(r.state.stress,Rotate(base.state.stress));Need(re<=a.stress_budget,c.name+": rotation covariance");rotmax=(std::max)(rotmax,re);}
    dsmax=(std::max)(dsmax,ds);dkmax=(std::max)(dkmax,dk);dlmax=(std::max)({dlmax,dl,dt});semax=(std::max)(semax,a.stress_error);kemax=(std::max)(kemax,a.kappa_error);vemax=(std::max)(vemax,a.volume_error);if(U::CommitAllowed(r.status)&&r.status!=U::Status::Elastic){ycmax=(std::max)(ycmax,std::abs(a.yield_continuous));ysmax=(std::max)(ysmax,std::abs(a.yield_saved));}
    rows<<n<<','<<c.name<<','<<unsigned(r.status)<<','<<unsigned(r.reason)<<','<<c.point.constant_entry<<','<<a.stress_error<<','<<a.kappa_error<<','<<a.volume_error<<','<<a.yield_continuous<<','<<a.yield_saved<<','<<ds<<','<<dk<<','<<dl<<','<<dt<<','<<a.stress_budget<<','<<a.strain_budget<<','<<host.state.kappa<<','<<r.state.kappa<<','<<r.kappa_continuous<<','<<r.lambda_shear<<','<<r.lambda_apex<<','<<r.lambda_tension<<','<<r.root_residual<<','<<r.root_budget<<','<<r.iterations<<'\n';
  }
  Need(exact==24&&rotated==20&&failed==7,"Declared control coverage changed");rows.flush();Need(bool(rows),"CSV write failed");
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_material_unified_gpu_probe_r1\",\"passed\":true,\"points\":69,\"kernel_launches\":1,\"rotated_points\":"<<rotated<<",\"same_device_constant_entry_checks\":"<<exact<<",\"failed_state_bit_checks\":"<<failed<<",\"input_points_scalar_checks\":"<<capacity<<",\"output_tail_defined_member_checks\":2,\"max_manufactured_stress_error_Pa\":"<<semax<<",\"max_compliance_kappa_error\":"<<kemax<<",\"max_compliance_volume_error\":"<<vemax<<",\"max_rotation_error_Pa\":"<<rotmax<<",\"max_host_GPU_stress_difference_Pa\":"<<dsmax<<",\"max_host_GPU_continuous_kappa_difference\":"<<dkmax<<",\"max_host_GPU_multiplier_difference\":"<<dlmax<<",\"max_plastic_yield_continuous_Pa\":"<<ycmax<<",\"max_plastic_yield_saved_Pa_descriptive\":"<<ysmax<<",\"device_major\":"<<prop.major<<",\"device_minor\":"<<prop.minor<<",\"host_U_is_implementation_control_only\":true,\"POD_padding_compared\":false,\"engine_objects\":0,\"spatial_solver\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<"point="<<current<<" : "<<e.what()<<'\n';return 1;}}

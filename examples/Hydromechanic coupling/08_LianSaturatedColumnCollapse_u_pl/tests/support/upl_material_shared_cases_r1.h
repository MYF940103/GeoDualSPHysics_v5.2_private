// Host-only case loading/checks shared by the separate MSVC/CUDA material fixtures.
#pragma once
#include "upl_material_shared_candidate_r1.h"
#include <algorithm>
#include <cfloat>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace upl_material_cases_r1 {
using namespace upl_material_candidate_r1;
using Row=std::map<std::string,std::string>;
struct Point { unsigned id; State state; Material material; };
struct Case {
  Point point; bool reference; Status expected; State saved_reference;
  double continuous_reference,lambda_reference; std::string path,branch;
};
inline void Need(bool b,const char* message){if(!b)throw std::runtime_error(message);}
inline bool Bits(double a,double b){return !std::memcmp(&a,&b,sizeof(a));}
inline bool Bits(float a,float b){return !std::memcmp(&a,&b,sizeof(a));}
inline bool SameState(const State& a,const State& b){
  return Bits(a.stress.xx,b.stress.xx)&&Bits(a.stress.yy,b.stress.yy)&&Bits(a.stress.zz,b.stress.zz)
    &&Bits(a.stress.xy,b.stress.xy)&&Bits(a.stress.yz,b.stress.yz)&&Bits(a.stress.xz,b.stress.xz)&&Bits(a.kappa,b.kappa);
}
inline bool SamePoint(const Point& a,const Point& b){
  const auto& m=a.material;const auto& n=b.material;
  return a.id==b.id&&SameState(a.state,b.state)&&Bits(m.bulk,n.bulk)&&Bits(m.shear,n.shear)&&Bits(m.phi,n.phi)
    &&Bits(m.cohesion_peak,n.cohesion_peak)&&Bits(m.cohesion_residual,n.cohesion_residual)
    &&Bits(m.cohesion_decay,n.cohesion_decay)&&Bits(m.psi0,n.psi0)&&Bits(m.psi_decay,n.psi_decay);
}
inline std::vector<std::string> Split(std::string s){
  if(!s.empty()&&s.back()=='\r')s.pop_back();std::vector<std::string> v;std::istringstream in(s);std::string x;
  while(std::getline(in,x,','))v.push_back(x);return v;
}
inline std::vector<Row> ReadTable(const std::filesystem::path& path){
  std::ifstream in(path);std::string line;Need(bool(std::getline(in,line)),"Missing source CSV");
  const auto header=Split(line);std::vector<Row> rows;
  while(std::getline(in,line)){const auto v=Split(line);Need(v.size()==header.size(),"CSV width differs");Row r;
    for(unsigned i=0;i<v.size();i++)Need(r.emplace(header[i],v[i]).second,"Duplicate CSV column");rows.push_back(r);}
  Need(in.eof(),"CSV read failed");return rows;
}
inline double Number(const Row& r,const std::string& key){return std::stod(r.at(key));}
inline float Float(const Row& r,const std::string& key){
  const double v=Number(r,key);const float f=float(v);Need(double(f)==v,"Original float source field not exactly represented");return f;
}
inline Stress StressFrom(const Row& r,const std::string& p){
  return {Number(r,p+"xx"),Number(r,p+"yy"),Number(r,p+"zz"),Number(r,p+"xy"),Number(r,p+"yz"),Number(r,p+"xz")};
}
inline std::vector<Case> Load(const std::filesystem::path& source){
  const auto rows=ReadTable(source);Need(rows.size()==132,"Retained source must have132 rows");std::vector<Case> cases;
  const double pi=3.1415926535897932384626433832795;const float E=20000000.f,nu=.33f;
  const float K=E/(3.f*(1.f-2.f*nu)),G=E/(2.f*(1.f+nu)),phi=float(25.*pi/180.);
  for(unsigned id=0;id<rows.size();id++){
    const auto& r=rows[id];const auto branch=r.at("branch");
    if(branch!="consistent_dev_constant_psi"&&branch!="consistent_dev_decay_psi")continue;
    const double reported=Number(r,"psi0_deg"),degrees=(reported==0.?0.:(reported>0.?2.5:-5.));
    const float psi=float(degrees*pi/180.);Need(Bits(reported,double(psi)*180./pi),"Original float-radian psi identity differs");
    Case c{};c.point={id,{StressFrom(r,"trial_"),Float(r,"kappa_old_float")},
      {K,G,phi,Float(r,"cp_Pa"),Float(r,"cr_Pa"),Float(r,"eta"),psi,Float(r,"sf")}};
    c.reference=true;c.path=r.at("path");c.branch=branch;
    c.expected=(r.at("return_available")=="0"?Status::ApexNeeded:(r.at("status")=="elastic_exact"?Status::Elastic:Status::Radial));
    c.saved_reference={StressFrom(r,"new_"),Float(r,"kappa_saved_float")};
    c.continuous_reference=Number(r,"kappa_continuous");c.lambda_reference=Number(r,"lambda_solved");cases.push_back(c);
  }
  Need(cases.size()==66,"Exactly66 original branch2/3 rows required");
  const char* names[]={"invalid_stress_nan","invalid_stress_inf","invalid_kappa_nan","invalid_shear_zero","invalid_sf_negative"};
  for(unsigned n=0;n<5;n++){
    Case c{};c.point=cases.front().point;c.point.id=132+n;c.path=names[n];c.branch="invalid";c.expected=Status::Invalid;
    if(n==0)c.point.state.stress.xx=std::numeric_limits<double>::quiet_NaN();
    if(n==1)c.point.state.stress.zz=std::numeric_limits<double>::infinity();
    if(n==2)c.point.state.kappa=std::numeric_limits<float>::quiet_NaN();
    if(n==3)c.point.material.shear=0.f;if(n==4)c.point.material.psi_decay=-.2f;cases.push_back(c);
  }return cases;
}
struct Independent { double I,q; };
inline Independent InvariantIndependent(const Stress& s){
  return {s.xx+s.yy+s.zz,std::sqrt(((s.xx-s.zz)*(s.xx-s.zz)+(s.yy-s.zz)*(s.yy-s.zz)+(s.yy-s.xx)*(s.yy-s.xx))/6.+s.xy*s.xy+s.yz*s.yz+s.xz*s.xz)};
}
inline double YieldIndependent(const Stress& s,const Material& m,double k){
  const auto v=InvariantIndependent(s);const double t=std::tan(double(m.phi)),den=std::sqrt(9.+12.*t*t);
  const double coh=double(m.cohesion_residual)+(double(m.cohesion_peak)-m.cohesion_residual)*std::exp(-double(m.cohesion_decay)*k);
  return v.q+t/den*v.I-3.*coh/den;
}
inline double StressGap(const Stress& a,const Stress& b){
  return (std::max)({std::fabs(a.xx-b.xx),std::fabs(a.yy-b.yy),std::fabs(a.zz-b.zz),std::fabs(a.xy-b.xy),std::fabs(a.yz-b.yz),std::fabs(a.xz-b.xz)});
}
struct Metrics {
  double continuous_yield=0,saved_yield=0,storage_yield_shift=0,dev_increment=0,plastic_trace=0,dev_error=0,dev_budget=0;
  double q_error=0,I_error=0,tensor_budget=0,closed_error=0,closed_budget=0,reference_stress_maxabs=0,reference_kappa_abs=0,reference_lambda_abs=0;
  bool constant_control=false,reference_saved_kappa_bits_equal=true;
};
inline Metrics Check(const Case& c,const Result& r){
  Metrics m{};const auto& p=c.point;Need(r.status==c.expected,"Unexpected shared return status");
  if(!CommitAllowed(r.status)){Need(SameState(r.state,p.state),"Failure Result.state changed input fields");return m;}
  Need(Finite(r.state.stress)&&Finite(r.state.kappa)&&Bits(r.state.kappa,float(r.kappa_continuous))&&r.state.kappa>=p.state.kappa,"Saved float kappa/stress contract failed");
  const auto tr=InvariantIndependent(p.state.stress),v=InvariantIndependent(r.state.stress);
  const double eps=DBL_EPSILON,old=p.state.kappa;
  m.continuous_yield=YieldIndependent(r.state.stress,p.material,r.kappa_continuous);
  m.saved_yield=YieldIndependent(r.state.stress,p.material,r.state.kappa);m.storage_yield_shift=m.saved_yield-m.continuous_yield;
  m.tensor_budget=8192.*eps*(std::max)({1.,std::fabs(tr.I),tr.q,std::fabs(v.I),v.q});
  if(r.status==Status::Elastic){Need(SameState(r.state,p.state)&&r.kappa_continuous==old&&m.continuous_yield<=1e-5,"Elastic state changed or is outside yield");}
  else{
    const double G=p.material.shear,K=p.material.bulk,h=1./std::sqrt(3.);
    const auto& a=p.state.stress;const auto& b=r.state.stress;
    const double x=a.xx-b.xx,y=a.yy-b.yy,z=a.zz-b.zz,xy=a.xy-b.xy,yz=a.yz-b.yz,xz=a.xz-b.xz,mean=(x+y+z)/3.;
    m.dev_increment=std::sqrt((2./3.)*((x-mean)*(x-mean)+(y-mean)*(y-mean)+(z-mean)*(z-mean)+2.*(xy*xy+yz*yz+xz*xz))/(4.*G*G));
    m.plastic_trace=mean/K;m.dev_error=std::fabs(m.dev_increment-h*r.lambda);m.dev_budget=8192.*eps*(std::max)(1.,std::fabs(h*r.lambda));
    const double psi=double(p.material.psi0)*std::exp(-double(p.material.psi_decay)*r.kappa_continuous),t=std::tan(psi),beta=t/std::sqrt(9.+12.*t*t);
    m.q_error=std::fabs(v.q-(tr.q-G*r.lambda));m.I_error=std::fabs(v.I-(tr.I-9.*K*beta*r.lambda));
    Need(r.root_budget>0&&std::fabs(m.continuous_yield)<=4.*r.root_budget&&m.dev_error<=m.dev_budget&&m.q_error<=m.tensor_budget&&m.I_error<=m.tensor_budget,"Original radial yield/compliance/tensor budget failed");
    Need(r.lambda>=0&&r.lambda<=tr.q/G&&r.minus_dF_dlambda>0&&std::fabs(r.kappa_continuous-(old+h*r.lambda))<=8192.*eps*(std::max)(1.,std::fabs(r.kappa_continuous)),"Original radial multiplier/history contract failed");
    if(c.path=="constant_strength_closed_control"){
      Need(p.material.cohesion_peak==p.material.cohesion_residual&&p.material.psi_decay==0.f,"Closed-control input differs");
      const double tp=std::tan(double(p.material.phi)),den=std::sqrt(9.+12.*tp*tp),alpha=tp/den;
      const double closed=(tr.q+alpha*tr.I-3.*p.material.cohesion_peak/den)/(G+9.*K*alpha*beta);
      m.constant_control=true;m.closed_error=std::fabs(r.lambda-closed);m.closed_budget=4096.*eps*(std::max)(1.,std::fabs(closed));
      Need(m.closed_error<=m.closed_budget,"Original constant-strength closed-lambda budget failed");
    }
  }
  if(c.reference){
    m.reference_stress_maxabs=StressGap(r.state.stress,c.saved_reference.stress);
    m.reference_kappa_abs=std::fabs(r.kappa_continuous-c.continuous_reference);m.reference_lambda_abs=std::fabs(r.lambda-c.lambda_reference);
    m.reference_saved_kappa_bits_equal=Bits(r.state.kappa,c.saved_reference.kappa);
    Need(m.reference_stress_maxabs<=m.tensor_budget&&m.reference_kappa_abs<=8192.*eps*(std::max)(1.,std::fabs(c.continuous_reference))
      &&m.reference_lambda_abs<=4096.*eps*(std::max)(1.,std::fabs(c.lambda_reference)),"Retained candidate comparison exceeds original arithmetic budgets");
  }return m;
}
inline const char* Name(Status s){
  switch(s){case Status::Invalid:return "Invalid";case Status::Elastic:return "Elastic";case Status::Radial:return "Radial";case Status::ApexNeeded:return "ApexNeeded";default:return "NonConverged";}
}
inline std::string StateBits(const State& s){
  std::ostringstream o;o<<std::hex;const double v[]={s.stress.xx,s.stress.yy,s.stress.zz,s.stress.xy,s.stress.yz,s.stress.xz};
  for(double x:v){std::uint64_t b;std::memcpy(&b,&x,8);o<<b<<':';}std::uint32_t b;std::memcpy(&b,&s.kappa,4);o<<b;return o.str();
}
inline std::string PointBits(const Point& p){
  std::ostringstream o;o<<StateBits(p.state)<<std::hex;const auto& m=p.material;
  const float v[]={m.bulk,m.shear,m.phi,m.cohesion_peak,m.cohesion_residual,m.cohesion_decay,m.psi0,m.psi_decay};
  for(float x:v){std::uint32_t b;std::memcpy(&b,&x,4);o<<':'<<b;}return o.str();
}
inline void PutStress(std::ostream& o,const Stress& s){o<<','<<s.xx<<','<<s.yy<<','<<s.zz<<','<<s.xy<<','<<s.yz<<','<<s.xz;}
inline void WriteHeader(std::ostream& o){
  o<<"id,path,branch,reference,input_xx,input_yy,input_zz,input_xy,input_yz,input_xz,input_kappa,bulk_float,shear_float,phi_rad_float,cp_float,cr_float,eta_float,psi0_rad_float,sf_float,input_bits,status,new_xx,new_yy,new_zz,new_xy,new_yz,new_xz,new_kappa,result_state_bits,kappa_continuous,lambda,trial_yield_Pa,scalar_residual_Pa,root_budget_Pa,minus_dF_dlambda_Pa,iterations,independent_yield_continuous_Pa,independent_yield_saved_Pa,saved_float_yield_shift_Pa,independent_dev_increment,plastic_trace,dev_error,dev_budget,q_error_Pa,I_error_Pa,tensor_budget_Pa,constant_control,closed_lambda_error,closed_lambda_budget,reference_stress_maxabs_Pa,reference_kappa_continuous_abs,reference_lambda_abs,reference_saved_kappa_bits_equal\n";
}
inline void WriteRow(std::ostream& o,const Case& c,const Result& r,const Metrics& v){
  const auto& p=c.point;const auto& m=p.material;o<<p.id<<','<<c.path<<','<<c.branch<<','<<c.reference;PutStress(o,p.state.stress);
  o<<','<<p.state.kappa<<','<<m.bulk<<','<<m.shear<<','<<m.phi<<','<<m.cohesion_peak<<','<<m.cohesion_residual<<','<<m.cohesion_decay<<','<<m.psi0<<','<<m.psi_decay<<','<<PointBits(p)<<','<<Name(r.status);PutStress(o,r.state.stress);
  o<<','<<r.state.kappa<<','<<StateBits(r.state)<<','<<r.kappa_continuous<<','<<r.lambda<<','<<r.trial_yield<<','<<r.root_residual<<','<<r.root_budget<<','<<r.minus_dF_dlambda<<','<<r.iterations
    <<','<<v.continuous_yield<<','<<v.saved_yield<<','<<v.storage_yield_shift<<','<<v.dev_increment<<','<<v.plastic_trace<<','<<v.dev_error<<','<<v.dev_budget<<','<<v.q_error<<','<<v.I_error<<','<<v.tensor_budget
    <<','<<v.constant_control<<','<<v.closed_error<<','<<v.closed_budget<<','<<v.reference_stress_maxabs<<','<<v.reference_kappa_abs<<','<<v.reference_lambda_abs<<','<<v.reference_saved_kappa_bits_equal<<'\n';
}
} // namespace upl_material_cases_r1

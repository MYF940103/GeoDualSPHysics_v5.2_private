// Actual CUDA stage wrappers only; no new kernel, force, scene or physical integration loop.
#include <cuda_runtime.h>
#include "JSphGpuSimple_ker.h"
#include "JAppInfo.h"
#include "FunSoilMaterial.h"
#include "upl_material_unified_candidate_r1.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <map>
#include <sstream>
#include <stdexcept>
#include <vector>
JAppInfo AppInfo("UplMaterialStageGpu","r1","07-11-2026");
namespace fs=std::filesystem;namespace U=fsoil_unified_candidate_r1;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
template<class T>static bool Bits(T a,T b){return !std::memcmp(&a,&b,sizeof(T));}
static U::Stress Named(const tsymatrix3d& s){return {s.xx,s.yy,s.zz,s.xy,s.yz,s.xz};}
static tsymatrix3d Native(const U::Stress& s){return TSymMatrix3d(s.xx,s.xy,s.xz,s.yy,s.yz,s.zz);}
static std::array<double,6> Six(const U::Stress& s){return {s.xx,s.yy,s.zz,s.xy,s.yz,s.xz};}
static bool Same(const U::Stress& a,const U::Stress& b){const auto x=Six(a),y=Six(b);for(unsigned i=0;i<6;i++)if(!Bits(x[i],y[i]))return false;return true;}
static double Gap(const U::Stress& a,const U::Stress& b){const auto x=Six(a),y=Six(b);double e=0;for(unsigned i=0;i<6;i++)e=(std::max)(e,std::abs(x[i]-y[i]));return e;}
struct Inv{double I,q;};
static Inv Invariant(const U::Stress& s){const double I=s.xx+s.yy+s.zz,m=I/3.;return {I,std::sqrt(.5*((s.xx-m)*(s.xx-m)+(s.yy-m)*(s.yy-m)+(s.zz-m)*(s.zz-m)+2.*(s.xy*s.xy+s.yz*s.yz+s.xz*s.xz)))};}
struct DP{double alpha,kc,beta;};
static DP Coeff(const U::Material& m,double k,TpDPCtes fit){
  const double p=m.phi_r+(double(m.phi_p)-m.phi_r)*std::exp(-double(m.n_p)*k),c=m.coh_r+(double(m.coh_p)-m.coh_r)*std::exp(-double(m.n_c)*k),b=double(m.psi0)*std::exp(-double(m.sf)*k);
  if(fit==DP_PS){const double t=std::tan(p),u=std::tan(b);return {t/std::sqrt(9.+12.*t*t),3.*c/std::sqrt(9.+12.*t*t),u/std::sqrt(9.+12.*u*u)};}
  const double sign=fit==DP_MC?1.:-1.,r=std::sqrt(3.);return {2.*std::sin(p)/(r*(3.+sign*std::sin(p))),6.*c*std::cos(p)/(r*(3.+sign*std::sin(p))),2.*std::sin(b)/(r*(3.+sign*std::sin(b)))};
}
static U::Stress Make(double I,double q){return {I/3.+q,I/3.-q,I/3.,0,0,0};}
static U::Stress Rotate(const U::Stress& s){
  const double r[3][3]={{1./9,8./9,4./9},{8./9,1./9,-4./9},{-4./9,4./9,-7./9}},a[3][3]={{s.xx,s.xy,s.xz},{s.xy,s.yy,s.yz},{s.xz,s.yz,s.zz}};double b[3][3]{};
  for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++)for(unsigned k=0;k<3;k++)for(unsigned l=0;l<3;l++)b[i][j]+=r[i][k]*a[k][l]*r[j][l];return {b[0][0],b[1][1],b[2][2],b[0][1],b[1][2],b[0][2]};
}
static float Rad(double d){return float(d*3.1415926535897932384626433832795/180.);}
static U::Material Law(float psi,bool soft){const float E=20e6f,n=.33f;return {float(double(E)/(3.*(1.-2.*double(n)))),float(double(E)/(2.*(1.+double(n)))),Rad(25),Rad(soft?20:25),soft?5.f:0.f,5000,soft?1000.f:5000.f,soft?5.f:0.f,Rad(psi),soft?.2f:0.f};}
struct Case{std::string name;U::Material reference;StSoilCte soil;TpDPCtes fit;U::Stress fulltrial;float old=.02f;bool soft=false,trigger=false,fluid=false;};
static StSoilCte Soil(const U::Material& m){StSoilCte s{};s.ModulusE=20e6f;s.ModulusK=m.ModulusK;s.ModulusG=m.ModulusG;s.phi=m.phi_p;s.phi_r=m.phi_r;s.n_phi=m.n_p;s.coh=m.coh_p;s.coh_r=m.coh_r;s.n_coh=m.n_c;s.dlt=m.psi0;s.psiDecay=m.sf;s.SoilTriggerFos=1;return s;}
static Case Smooth(std::string name,U::Material m,TpDPCtes fit){
  Case c{};c.name=name;c.reference=m;c.soil=Soil(m);c.fit=fit;c.soft=m.n_p>0||m.n_c>0;
  const double lambda=.001,k=double(c.old)+lambda/std::sqrt(3.);const auto d=Coeff(m,k,fit);const double I=-60000.,q=d.kc-d.alpha*I;c.fulltrial=Rotate(Make(I+9.*double(m.ModulusK)*d.beta*lambda,q+double(m.ModulusG)*lambda));return c;
}
static std::vector<Case> Cases(){std::vector<Case> v;
  for(auto fit:{DP_PS,DP_C,DP_MC})for(bool soft:{false,true})v.push_back(Smooth(std::string(soft?"soft_":"basic_")+std::to_string(unsigned(fit)),Law(fit==DP_PS?0.f:fit==DP_C?2.5f:-5.f,soft),fit));
  {auto m=Law(2.5f,true);m.phi_p=m.phi_r=0;m.n_p=0;v.push_back(Smooth("phi0_soft",m,DP_PS));}
  {auto m=Law(2.5f,false);m.sf=.2f;auto c=Smooth("sf_only_no_FOS",m,DP_PS);c.trigger=true;c.soil.SoilTriggerFos=2;c.soil.coh_r=4500;v.push_back(c);}
  {auto m=Law(2.5f,true);m.coh_p=m.coh_r=2500;m.n_c=0;m.sf=0;auto c=Smooth("phi_only_FOS_unused_cr",m,DP_C);c.trigger=true;c.soil.coh=5000;c.soil.coh_r=4500;c.soil.SoilTriggerFos=2;v.push_back(c);}
  {auto m=Law(2.5f,true);Case c{};c.name="positive_apex_dev_saturated";c.reference=m;c.soil=Soil(m);c.fit=DP_PS;c.soft=true;const auto d=Coeff(m,c.old,c.fit);c.fulltrial=Make(d.kc/d.alpha+9.*double(m.ModulusK)*d.beta*.01,0);v.push_back(c);}
  {Case c{};c.name="no_soil_zero_moduli";c.fit=DP_PS;c.fluid=true;c.old=0;v.push_back(c);}Need(v.size()==11,"Success point count changed");return v;
}

static void Cu(cudaError_t e){Need(e==cudaSuccess,cudaGetErrorString(e));}
static bool Equal(const tsymatrix3d& a,const tsymatrix3d& b){return Same(Named(a),Named(b));}
static bool Equal(const tsymatrix3f& a,const tsymatrix3f& b){return Bits(a.xx,b.xx)&&Bits(a.yy,b.yy)&&Bits(a.zz,b.zz)&&Bits(a.xy,b.xy)&&Bits(a.yz,b.yz)&&Bits(a.xz,b.xz);}
static bool Equal(float4 a,float4 b){return Bits(a.x,b.x)&&Bits(a.y,b.y)&&Bits(a.z,b.z)&&Bits(a.w,b.w);}
static bool Equal(float3 a,float3 b){return Bits(a.x,b.x)&&Bits(a.y,b.y)&&Bits(a.z,b.z);}
static bool Equal(double2 a,double2 b){return Bits(a.x,b.x)&&Bits(a.y,b.y);}
template<class T>static bool Equal(T a,T b){return Bits(a,b);}
template<class T>static void All(const std::array<T,3>& a,const std::array<T,3>& b){for(unsigned q=0;q<3;q++)Need(Equal(a[q],b[q]),"Defined input/output member changed");}
template<class T>struct Device{T* p=nullptr;Device(){Cu(cudaMalloc(reinterpret_cast<void**>(&p),3*sizeof(T)));}~Device(){if(p)cudaFree(p);}Device(const Device&)=delete;Device& operator=(const Device&)=delete;
  void Put(const std::array<T,3>& a){Cu(cudaMemcpy(p,a.data(),3*sizeof(T),cudaMemcpyHostToDevice));}
  std::array<T,3> Get()const{std::array<T,3> a;Cu(cudaMemcpy(a.data(),p,3*sizeof(T),cudaMemcpyDeviceToHost));return a;}
};
using CpuRow=std::map<std::string,std::string>;
static std::map<std::string,CpuRow> ReadCpu(const fs::path& file){
  std::ifstream f(file);Need(bool(f),"Closed CPU CSV absent");std::string line;std::getline(f,line);if(!line.empty()&&line.back()=='\r')line.pop_back();std::vector<std::string> header;{std::stringstream s(line);std::string v;while(std::getline(s,v,','))header.push_back(v);}
  std::map<std::string,CpuRow> rows;while(std::getline(f,line)){if(!line.empty()&&line.back()=='\r')line.pop_back();std::stringstream s(line);std::string v;CpuRow row;unsigned n=0;while(std::getline(s,v,',')){Need(n<header.size(),"CPU CSV has excess cells");row[header[n++]]=v;}Need(n==header.size(),"CPU CSV missing cells");Need(rows.emplace(row.at("case")+"\n"+row.at("stage"),row).second,"Duplicate CPU case/stage");}
  std::ifstream done(file.parent_path()/"completion.json");const std::string text((std::istreambuf_iterator<char>(done)),std::istreambuf_iterator<char>());Need(rows.size()==26&&text.find("\"stage\":\"upl_material_stage_cpu_r1\"")!=std::string::npos&&text.find("\"passed\":true")!=std::string::npos,"CPU stage is not the closed 26-row result");return rows;
}
static U::Stress CsvStress(const CpuRow& r){return {std::stod(r.at("sigma_xx")),std::stod(r.at("sigma_yy")),std::stod(r.at("sigma_zz")),std::stod(r.at("sigma_xy")),std::stod(r.at("sigma_yz")),std::stod(r.at("sigma_xz"))};}
struct Step{
  Device<float4> prev,vel;Device<float> ar,basek,currentk,k,dk;Device<float3> ace;Device<tsymatrix3d> base,sigma;Device<tsymatrix3f> rate;Device<typecode> code;Device<double2> movxy;Device<double> movz;Device<unsigned> error;
  unsigned calls=0,tails=0,failures=0,prebits=0,corbits=0,verletbits=0;double maxCpu=0.;
  void Run(Case c,const char* phase,const CpuRow& cpu,std::ostream& csv,bool reject=false){
    constexpr double dt=.125;const bool pre=std::string(phase)=="Pre"||std::string(phase)=="Reject_setup_Pre",ver=std::string(phase).find("Verlet_")==0,full=std::string(phase)=="Verlet_2dt";
    StSoilCte soil=c.soil;if(reject){soil.n_phi=soil.n_coh=1e6f;soil.phi_r=Rad(20);soil.coh_r=1000;c.soft=true;}
    cusphs::CteInteractionUpTStep(&soil,c.soft?1u:0u,c.trigger?1u:0u);
    std::array<float4,3> pv,vo;std::array<float,3> a,bk,ck,ko,dko;std::array<float3,3> ac;std::array<tsymatrix3d,3> bs,so;std::array<tsymatrix3f,3> sr;std::array<typecode,3> co;std::array<double2,3> xy;std::array<double,3> z;std::array<unsigned,3> er;
    for(unsigned q=0;q<3;q++){const double d=q+1.;pv[q]=make_float4(q==1?1.f/1024:0,0,q==1?-1.f/2048:0,2072.5f);vo[q]=q<2?make_float4(0,0,0,2072.5f):make_float4(11,12,13,14);a[q]=0;ac[q]=make_float3(0,0,0);bk[q]=ck[q]=q==1?c.old:0;ko[q]=q==0?0.f:float(7+d);dko[q]=.25f;bs[q]=q==1?Native(c.fulltrial):TSymMatrix3d();so[q]=q==0?TSymMatrix3d():TSymMatrix3d(d,2*d,3*d,4*d,5*d,6*d);sr[q]=TSymMatrix3f();co[q]=q==0?CODE_TYPE_FIXED:CODE_TYPE_FLUID;xy[q]=make_double2(q==0?0:8*d,q==0?0:9*d);z[q]=q==0?0:10*d;er[q]=q?0x1234abcdu+q:0;}
    if(!c.fluid){sr[1].xx=8192;sr[1].yy=-8192;bs[1].xx-=sr[1].xx*dt;bs[1].yy-=sr[1].yy*dt;}
    if(reject)bs[1]=Native(Make(-60000,100000));
    if(full)ck[1]=.75f; // Different current versus M1 history is intentional, not a physical trajectory.
    prev.Put(pv);vel.Put(vo);ar.Put(a);basek.Put(bk);currentk.Put(ck);k.Put(ko);dk.Put(dko);ace.Put(ac);base.Put(bs);sigma.Put(so);rate.Put(sr);code.Put(co);movxy.Put(xy);movz.Put(z);error.Put(er);
    tsymatrix3d* outputSigma=full?base.p:sigma.p;float* outputK=full?basek.p:k.p;
    if(ver)cusphs::ComputeStepVerlet(false,false,false,c.fit,MDBC2_Std,2,1,prev.p,prev.p,base.p,full?basek.p:currentk.p,currentk.p,rate.p,ar.p,ace.p,nullptr,nullptr,nullptr,dt,full?dt+dt:dt,2072.5f,700,3000,TFloat3(0),code.p,movxy.p,movz.p,vel.p,outputSigma,outputK,dk.p,nullptr,error.p);
    else if(pre)cusphs::ComputeStepSymplecticPre(false,false,false,c.fit,2,1,prev.p,ar.p,ace.p,nullptr,base.p,basek.p,rate.p,nullptr,dt*.5,2072.5f,700,3000,TFloat3(0),code.p,movxy.p,movz.p,vel.p,sigma.p,k.p,dk.p,nullptr,{},error.p);
    else cusphs::ComputeStepSymplecticCor(false,false,false,c.fit,MDBC2_Std,2,1,prev.p,ar.p,ace.p,nullptr,base.p,basek.p,rate.p,nullptr,nullptr,dt*.5,dt,2072.5f,700,3000,TFloat3(0),code.p,movxy.p,movz.p,vel.p,sigma.p,k.p,dk.p,nullptr,{},error.p);
    Cu(cudaGetLastError());Cu(cudaDeviceSynchronize());calls++;const auto b=base.Get(),s=sigma.Get();const auto old=basek.Get(),nk=k.Get(),d=dk.Get();const auto v=vel.Get();const auto mx=movxy.Get();const auto mz=movz.Get();const auto e=error.Get();
    const auto& resultSigma=full?b:s;const auto& resultK=full?old:nk;const auto expectedStatus=unsigned(std::stoul(cpu.at("reference_status")));const unsigned expectedError=reject?1u<<unsigned(fsoil::Status::UnresolvedPath):0u;Need(e[0]==expectedError&&e[1]==er[1]&&e[2]==er[2],"Actual wrapper status/tail flag differs");
    All(pv,prev.Get());All(a,ar.Get());All(ac,ace.Get());All(ck,currentk.Get());All(sr,rate.Get());All(co,code.Get());
    for(unsigned q:{0u,2u}){Need(Equal(b[q],bs[q])&&Bits(old[q],bk[q])&&Equal(s[q],so[q])&&Bits(nk[q],ko[q])&&Bits(d[q],dko[q])&&Equal(v[q],vo[q])&&Equal(mx[q],xy[q])&&Bits(mz[q],z[q]),"Fixed or tail canary changed");tails++;}
    double gap=0,budget=0;
    if(reject){Need(expectedStatus==unsigned(fsoil::Status::UnresolvedPath)&&Equal(s[1],so[1])&&Bits(nk[1],ko[1])&&Bits(d[1],dko[1])&&Equal(v[1],vo[1])&&Equal(mx[1],xy[1])&&Bits(mz[1],z[1]),"Rejected point wrote native output");failures++;}
    else{
      Need(e[0]==0,"Successful wrapper failed");const auto actual=Named(resultSigma[1]),target=CsvStress(cpu);const auto ti=Invariant(Named(bs[1])),ni=Invariant(actual);budget=std::stod(cpu.at("tensor_budget_Pa"))+8192.*DBL_EPSILON*(std::max)({1.,std::fabs(ti.I),ti.q,std::fabs(ni.I),ni.q});gap=Gap(actual,target);Need(gap<=budget,"Actual GPU/CPU stress exceeds original combined roundoff budgets");
      const float wanted=std::stof(cpu.at("kappa_written"));Need(Bits(resultK[1],wanted),"Actual GPU stage history differs from CPU float writeback");
      const float wantedDk=pre?dko[1]:dko[1]+fmaxf(wanted-(ver?ck[1]:bk[1]),0.f);Need(Bits(d[1],wantedDk),"Raw DK did not use actual current history");Need(Equal(v[1],pv[1])&&Bits(mx[1].x,double(pv[1].x)*dt*(pre?.5:1.))&&Bits(mx[1].y,0.)&&Bits(mz[1],double(pv[1].z)*dt*(pre?.5:1.)),"Zero-acceleration kinematics changed");
      if(pre)prebits++;else if(ver)verletbits++;else corbits++;maxCpu=(std::max)(maxCpu,gap);
    }
    if(full){Need(Equal(s[1],so[1])&&Bits(nk[1],ko[1]),"Unused separate output changed in in-place M1 call");bs[1]=resultSigma[1];bk[1]=resultK[1];}
    All(bs,b);All(bk,old);csv<<c.name<<','<<phase<<','<<unsigned(c.fit)<<','<<expectedStatus<<','<<expectedError<<','<<gap<<','<<budget<<','<<resultK[1]<<','<<d[1]<<','<<full<<'\n';csv.flush();Need(bool(csv),"GPU stage CSV write failed");
  }
};
int main(int argc,char** argv){std::string current;try{
  Need(argc==5&&std::string(argv[1])=="--cpu"&&std::string(argv[3])=="--out","Use --cpu CLOSED_CPU_stages.csv --out FRESH_DIR");const fs::path cpu=argv[2],out=argv[4];const auto rows=ReadCpu(cpu);Need(!fs::exists(out)&&fs::is_directory(out.parent_path())&&fs::create_directory(out),"Fresh output required");Cu(cudaSetDevice(0));Step step;std::ofstream csv(out/"stages.csv");csv<<std::setprecision(17)<<"case,stage,fit,CPU_status,status_bits,stress_CPU_gap_Pa,combined_tensor_budget_Pa,kappa_output,raw_DK_output,inplace_M1_alias\n";
  auto run=[&](Case c,const char* phase,bool reject=false){current=c.name+"/"+phase;step.Run(c,phase,rows.at(c.name+"\n"+phase),csv,reject);};const auto cases=Cases();for(const auto& c:cases){run(c,"Pre");run(c,"Cor");}
  Case rejected=Smooth("uncertified",Law(0,true),DP_PS);rejected.old=0;rejected.fulltrial=Make(-20000,0);run(rejected,"Reject_setup_Pre");run(rejected,"Cor_rejected",true);run(cases[0],"Verlet_2dt");run(cases[0],"Verlet_reset_dt");
  Need(step.calls==26&&step.failures==1&&step.prebits==12&&step.corbits==11&&step.verletbits==2&&step.tails==52,"Actual GPU stage coverage differs");std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_material_stage_gpu_r1\",\"passed\":true,\"actual_wrapper_calls\":26,\"manufactured_points\":14,\"Pre_old_kappa_checks\":12,\"Cor_commit_checks\":11,\"Verlet_pairing_raw_DK_checks\":2,\"expected_Cor_rejections\":1,\"fixed_and_tail_checks\":52,\"max_actual_CPU_stress_gap_Pa\":"<<step.maxCpu<<",\"new_CUDA_kernel\":false,\"host_ComputeVerlet_not_called\":true,\"general_Verlet_irreversibility_claim\":false,\"spatial_force_or_solver\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<current<<": "<<e.what()<<'\n';return 1;}}

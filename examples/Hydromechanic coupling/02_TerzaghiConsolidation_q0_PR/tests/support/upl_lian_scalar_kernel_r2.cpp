// Fixed-receiver 2D scalar spatial diagnostic only. No JSph, BI4 or integration.
// Root builds against frozen archived FunSphKernel.h and its actual include closure.
#define NOMINMAX
#include <windows.h>
#include "FunSphKernel.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace scalar_r2 {
using Clock=std::chrono::steady_clock;
static void Need(bool value,const char* message){if(!value)throw std::runtime_error(message);}
struct V {double x=0,z=0;};
struct M {double xx=0,xz=0,zx=0,zz=0;};
static V Add(V a,V b){return{a.x+b.x,a.z+b.z};}
static V Sub(V a,V b){return{a.x-b.x,a.z-b.z};}
static V Mul(V a,double s){return{a.x*s,a.z*s};}
static double Dot(V a,V b){return a.x*b.x+a.z*b.z;}
static double One(V a){return std::fabs(a.x)+std::fabs(a.z);}
static V Apply(M c,V g){return{c.xx*g.x+c.xz*g.z,c.zx*g.x+c.zz*g.z};}
static double Norm(M a){return(std::max)(std::fabs(a.xx)+std::fabs(a.xz),std::fabs(a.zx)+std::fabs(a.zz));}
static double Gamma(unsigned n){const double v=n*DBL_EPSILON;Need(v<.01,"Roundoff operation count invalid");return v/(1-v);}
static M Inverse(M m){const double d=m.xx*m.zz-m.xz*m.zx;Need(std::isfinite(d)&&d>0,"Moment singular or negatively oriented");return{m.zz/d,-m.xz/d,-m.zx/d,m.xx/d};}
static double Ratio(double residual,double bound){if(bound==0){Need(residual==0,"Nonzero residual with zero bound");return 0;}return residual/bound;}
struct Pair {unsigned j;V d,g;double rr;};
struct Node {V x;M moment,c;std::vector<Pair> pairs;double condition=0;};
struct Cloud {unsigned denominator;bool jitter,cubic;double dp,h,volume,eta,condition,affineResidual,momentAbs,scaleRatio;std::vector<Node> nodes;std::uint64_t kernelParity=0;};
constexpr int Guard=9,Width=19;
constexpr unsigned Receiver=Guard+Width*Guard;
static const char* Fields[]={"1","x","z","half_x2","xz","half_z2","cos2pi_x","cos2pi_x_plus_z"};
static const char* Variants[]={"receiver_C_r2","receiver_C_Eta2","production_pair_C_Eta2"};
static std::uint32_t Hash(unsigned x,unsigned z,unsigned salt){
  std::uint32_t a=std::uint32_t(x)*0x9e3779b9u^std::uint32_t(z)*0x85ebca6bu^salt;
  a^=a>>16;a*=0x7feb352du;a^=a>>15;a*=0x846ca68bu;return a^(a>>16);
}
static double Jitter(unsigned x,unsigned z,unsigned salt){return(double(Hash(x,z,salt)&65535u)/65535.-.5)*.16;}

// Independent spelling of the archived float Fac operations. This parity test
// compares fixed native operands/operation order, not a double ideal-kernel error.
static float ManualFac(bool cubic,const StKWendlandCte& w,const StKCubicCte& c,float h,float rr){
  const float rad=sqrt(rr),q=rad/h;
  if(!cubic){const float t=1.f-.5f*q;return w.bwen*q*t*t*t/rad;}
  if(rad>h){const float t=2.f-q;const float t2=t*t;return c.c2*t2/rad;}
  const float q2=q*q;return(c.c1*q+c.d1*q2)/rad;
}

static Cloud Make(unsigned denominator,bool jitter,bool cubic){
  Cloud a{};a.denominator=denominator;a.jitter=jitter;a.cubic=cubic;a.dp=1./denominator;
  a.h=double(float((cubic?1.2:1.8)*a.dp));a.volume=a.dp*a.dp;
  a.eta=double(float((.1*a.h)*(.1*a.h)));a.nodes.resize(Width*Width);
  const float hf=float(a.h),support=float(2*a.h),support2=support*support;
  const auto wk=fsph::GetKernelWendland_Ctes(true,a.h);const auto ck=fsph::GetKernelCubic_Ctes(true,a.h);
  for(int z=-Guard;z<=Guard;z++)for(int x=-Guard;x<=Guard;x++){
    const unsigned i=unsigned(x+Guard)+Width*unsigned(z+Guard);
    const bool disturb=jitter&&i!=Receiver;
    a.nodes[i].x={(x+(disturb?Jitter(unsigned(x+Guard),unsigned(z+Guard),17):0))*a.dp,
                  (z+(disturb?Jitter(unsigned(x+Guard),unsigned(z+Guard),71):0))*a.dp};
  }
  Need(a.nodes.size()<=361&&a.nodes[Receiver].x.x==0&&a.nodes[Receiver].x.z==0,"Fixed receiver/node cap differs");
  for(unsigned i=0;i<a.nodes.size();i++){
    auto& n=a.nodes[i];
    for(unsigned j=0;j<a.nodes.size();j++){
      const V d=Sub(n.x,a.nodes[j].x);const double rr=Dot(d,d);
      if(rr>double(support2)||rr<ALMOSTZERO)continue;
      const float fac=cubic?fsph::GetKernelCubic_Fac(ck,hf,float(rr)):fsph::GetKernelWendland_Fac(wk,hf,float(rr));
      const float independent=ManualFac(cubic,wk,ck,hf,float(rr));
      Need(std::memcmp(&fac,&independent,sizeof(float))==0,"Archived kernel Fac parity failed");a.kernelParity++;
      const V g=Mul(d,double(fac));n.pairs.push_back({j,d,g,rr});
      n.moment.xx-=a.volume*d.x*g.x;n.moment.xz-=a.volume*d.x*g.z;
      n.moment.zx-=a.volume*d.z*g.x;n.moment.zz-=a.volume*d.z*g.z;
    }
    n.c=Inverse(n.moment);n.condition=Norm(n.moment)*Norm(n.c);
    Need(!n.pairs.empty()&&std::isfinite(n.condition)&&Gamma(unsigned(64*n.pairs.size()+256))*n.condition<.01,"Conditioning invalidates original forward bound");
  }
  const auto& n=a.nodes[Receiver];M first,scaled;
  a.condition=n.condition;
  for(const auto& q:n.pairs){
    const V r=Mul(q.d,-1),g=Apply(n.c,q.g);const auto& x=a.nodes[q.j].x;
    Need(std::fabs(x.x)+support<=(Guard-.08)*a.dp&&std::fabs(x.z)+support<=(Guard-.08)*a.dp,"A used neighbor C lacks full support guard");
    first.xx+=a.volume*g.x*r.x;first.xz+=a.volume*g.x*r.z;first.zx+=a.volume*g.z*r.x;first.zz+=a.volume*g.z*r.z;
    a.momentAbs+=a.volume*One(g)*One(r);a.condition=(std::max)(a.condition,a.nodes[q.j].condition);
    const V sg=Mul(q.g,1.5);scaled.xx+=a.volume*r.x*sg.x;scaled.xz+=a.volume*r.x*sg.z;
    scaled.zx+=a.volume*r.z*sg.x;scaled.zz+=a.volume*r.z*sg.z;
  }
  first.xx-=1;first.zz-=1;a.affineResidual=Norm(first);
  const M sc=Inverse(scaled);const double u=Gamma(unsigned(64*n.pairs.size()+256));
  for(const auto& q:n.pairs){
    const V g=Apply(n.c,q.g),sg=Apply(sc,Mul(q.g,1.5));
    const double bound=u*(n.condition+Norm(scaled)*Norm(sc))*(One(g)+One(sg));
    const double ratio=Ratio(One(Sub(g,sg)),bound);a.scaleRatio=(std::max)(a.scaleRatio,ratio);
    Need(ratio<=1,"Common kernel-amplitude normalization invariance failed");
  }
  Need(a.affineResidual<=u*a.momentAbs,"Corrected affine moment exceeded original roundoff budget");
  return a;
}

struct Truth {double value;V gradient;std::array<double,3> h;};
static Truth Field(unsigned f,V x){
  const double k=2*std::acos(-1.);
  switch(f){
    case 0:return{1,{0,0},{0,0,0}};case 1:return{x.x,{1,0},{0,0,0}};case 2:return{x.z,{0,1},{0,0,0}};
    case 3:return{.5*x.x*x.x,{x.x,0},{1,0,0}};case 4:return{x.x*x.z,{x.z,x.x},{0,1,0}};
    case 5:return{.5*x.z*x.z,{0,x.z},{0,0,1}};
    case 6:{const double c=std::cos(k*x.x),s=std::sin(k*x.x);return{c,{-k*s,0},{-k*k*c,0,0}};}
    default:{const double c=std::cos(k*(x.x+x.z)),s=std::sin(k*(x.x+x.z));return{c,{-k*s,-k*s},{-k*k*c,-k*k*c,-k*k*c}};}
  }
}
static V CorrectedGradient(const Cloud& a,const std::vector<double>& p){
  const auto& n=a.nodes[Receiver];V gp;
  for(const auto& q:n.pairs)gp=Add(gp,Mul(Apply(n.c,q.g),a.volume*(p[q.j]-p[Receiver])));
  return gp;
}
struct Direct {std::array<double,4> h{};V gp;double scale=0;};
// Printed Eq23: accumulate its two sums separately, with the approximate Eq22
// gradient. Do not insert the exact manufactured gradient into this operator.
static Direct DirectEq23(const Cloud& a,const std::vector<double>& p){
  Direct out;out.gp=CorrectedGradient(a,p);const auto& n=a.nodes[Receiver];
  std::array<double,4> raw{};std::array<V,4> defect{};
  for(const auto& q:n.pairs){
    const V r=Mul(q.d,-1),ghat=Apply(n.c,q.g);const double delta=p[q.j]-p[Receiver],F=Dot(r,ghat)/q.rr;
    const std::array<double,4> D={4*r.x*r.x/q.rr-1,4*r.x*r.z/q.rr,4*r.z*r.x/q.rr,4*r.z*r.z/q.rr-1};
    for(unsigned c=0;c<4;c++){const double coefficient=a.volume*D[c]*F;
      raw[c]+=coefficient*delta;defect[c]=Add(defect[c],Mul(r,coefficient));
      out.scale+=std::fabs(coefficient*delta)+std::fabs(coefficient)*(std::fabs(out.gp.x*r.x)+std::fabs(out.gp.z*r.z));
    }
  }
  for(unsigned c=0;c<4;c++)out.h[c]=raw[c]-Dot(out.gp,defect[c]);
  return out;
}
struct Eval {std::array<double,3> h{},budget{};V gp;double scalar=0,scale=0,gradientBudget=0;};
// Current CPU XZ expression arithmetic/signs, specialized to J=1, V=dp^2,
// zero acceleration and no boundary substitution. This is not an actual JSph call.
static double ProductionScalar(const Cloud& a,const std::vector<double>& p,unsigned variant,double& scale){
  const auto& n=a.nodes[Receiver];double lp=0;V lx,gp;
  for(const auto& q:n.pairs){
    const V gi=Apply(n.c,q.g),gj=Apply(variant<2?n.c:a.nodes[q.j].c,q.g);
    const double dp=p[Receiver]-p[q.j],w=a.volume*Dot(q.d,Add(gi,gj))/(q.rr+(variant?a.eta:0));
    lp+=w*dp;lx=Add(lx,Mul(q.d,w));gp=Sub(gp,Mul(gi,a.volume*dp));scale+=std::fabs(w*dp);
  }
  scale+=std::fabs(gp.x*lx.x)+std::fabs(gp.z*lx.z);
  return lp-gp.x*lx.x-gp.z*lx.z;
}
static Eval Evaluate(const Cloud& a,const std::vector<double>& p,unsigned variant,unsigned field){
  const auto& n=a.nodes[Receiver];Eval out;out.gp=CorrectedGradient(a,p);
  const double u=Gamma(unsigned(64*n.pairs.size()+256));double gpScale=0;
  for(const auto& q:n.pairs)gpScale+=a.volume*One(Apply(n.c,q.g))*(std::fabs(p[q.j])+std::fabs(p[Receiver]));
  out.gradientBudget=(a.affineResidual+u*a.momentAbs)*One(Field(field,n.x).gradient)+u*gpScale;
  for(const auto& q:n.pairs){
    const V r=Mul(q.d,-1),gi=Apply(n.c,q.g),gj=Apply(variant<2?n.c:a.nodes[q.j].c,q.g);
    const double F=Dot(r,variant<2?gi:Mul(Add(gi,gj),.5))/(q.rr+(variant?a.eta:0));
    const double delta=p[q.j]-p[Receiver],defect=delta-Dot(out.gp,r);
    // Eta2 regularizes F only. D retains its literal unregularized r2 denominator.
    const std::array<double,3> D={4*r.x*r.x/q.rr-1,4*r.x*r.z/q.rr,4*r.z*r.z/q.rr-1};
    const double defectBound=u*(std::fabs(p[Receiver])+std::fabs(p[q.j]))+One(r)*out.gradientBudget
      +u*(std::fabs(out.gp.x*r.x)+std::fabs(out.gp.z*r.z));
    for(unsigned c=0;c<3;c++){const double coefficient=a.volume*D[c]*F,term=coefficient*defect;
      out.h[c]+=term;out.budget[c]+=std::fabs(coefficient)*defectBound+u*std::fabs(term);
      if(c!=1)out.scale+=std::fabs(term);
    }
    const double w=a.volume*Dot(q.d,Add(gi,gj))/(q.rr+(variant?a.eta:0));
    out.scale+=std::fabs(w)*(std::fabs(out.gp.x*q.d.x)+std::fabs(out.gp.z*q.d.z));
  }
  out.scalar=ProductionScalar(a,p,variant,out.scale);return out;
}

static int Run(const std::filesystem::path& dir){
  Need(!std::filesystem::exists(dir),"Retained output protected");
  Need(SetPriorityClass(GetCurrentProcess(),BELOW_NORMAL_PRIORITY_CLASS)!=0,"Cannot set this diagnostic BelowNormal");
  DWORD_PTR allowed=0,system=0;Need(GetProcessAffinityMask(GetCurrentProcess(),&allowed,&system)!=0&&allowed,"Cannot read own allowed affinity");
  const DWORD_PTR selected=allowed&(~allowed+1);Need(SetProcessAffinityMask(GetCurrentProcess(),selected)!=0,"Cannot restrict this diagnostic to one allowed CPU");
  std::filesystem::create_directory(dir);std::ofstream csv(dir/"responses.csv");csv<<std::setprecision(17);
  csv<<"kernel_condition,cloud,dp_denominator,dp,h,Eta2,V,receiver_x,receiver_z,nodes,receiver_neighbors,condition_inf_max_used_C,corrected_affine_residual_inf,kernel_scale_invariance_roundoff_ratio,pressure_storage,field,variant,analytic_Laplacian,scalar_Lstar,scalar_abs_error,scalar_relative_error_if_nonzero,scalar_error_ratio_previous_over_current,direct_Eq23_trace,direct_Hxx,direct_Hxz,direct_Hzx,direct_Hzz,Hxx,Hxz,Hzz,approx_gradient_x,approx_gradient_z,gradient_L1_error,input_float_quantization_max,matched_trace_roundoff_ratio,literal_direct_trace_roundoff_ratio,double_affine_forward_bound_applicable,double_affine_roundoff_ratio,float_affine_is_diagnostic\n";
  std::array<double,192> previous;previous.fill(std::numeric_limits<double>::quiet_NaN());
  std::uint64_t clouds=0,responses=0,kernelParity=0,constantChecks=0,affineChecks=0,formulaChecks=0,directChecks=0;
  double maxTraceRatio=0,maxDirectRatio=0,maxAffineRatio=0,maxScaleRatio=0,maxFloatAffine=0;
  const auto started=Clock::now();
  for(unsigned kernel=0;kernel<2;kernel++)for(unsigned jitter=0;jitter<2;jitter++)for(unsigned denominator:{16u,32u,64u}){
    const Cloud a=Make(denominator,jitter!=0,kernel!=0);const auto& n=a.nodes[Receiver];clouds++;kernelParity+=a.kernelParity;
    maxScaleRatio=(std::max)(maxScaleRatio,a.scaleRatio);const double u=Gamma(unsigned(64*n.pairs.size()+256));
    for(unsigned mode=0;mode<2;mode++)for(unsigned f=0;f<8;f++){
      std::vector<double> p;double quantization=0;
      for(const auto& node:a.nodes){const double exact=Field(f,node.x).value,value=mode?double(float(exact)):exact;p.push_back(value);quantization=(std::max)(quantization,std::fabs(value-exact));}
      const Direct literal=DirectEq23(a,p);Need(literal.h[1]==literal.h[2],"Eq23 mixed-index symmetry failed");
      const Truth truth=Field(f,n.x);const double exact=truth.h[0]+truth.h[2];
      for(unsigned variant=0;variant<3;variant++){
        const Eval e=Evaluate(a,p,variant,f);const double trace=e.h[0]+e.h[2],error=std::fabs(e.scalar-exact);
        Need(std::isfinite(e.scalar)&&std::isfinite(error)&&std::isfinite(trace),"Nonfinite scalar response");
        const double traceRatio=Ratio(std::fabs(trace-e.scalar),u*e.scale);Need(traceRatio<=1,"Matched tensor/scalar formula forward bound failed");formulaChecks++;
        maxTraceRatio=(std::max)(maxTraceRatio,traceRatio);double directRatio=0,affineRatio=0;
        if(!variant){directRatio=Ratio(std::fabs(literal.h[0]+literal.h[3]-e.scalar),u*(literal.scale+e.scale));
          Need(directRatio<=1,"Printed direct Eq23 trace differs from matched receiver-C/r2 scalar");directChecks++;maxDirectRatio=(std::max)(maxDirectRatio,directRatio);}
        if(!f){Need(e.gp.x==0&&e.gp.z==0&&e.scalar==0&&trace==0&&e.h[0]==0&&e.h[1]==0&&e.h[2]==0
          &&literal.h[0]==0&&literal.h[1]==0&&literal.h[2]==0&&literal.h[3]==0,"Constant input null is not exact");constantChecks++;}
        const bool affine=f==1||f==2;
        if(!mode&&affine){
          Need(One(Sub(e.gp,truth.gradient))<=e.gradientBudget,"Double affine gradient exceeded original forward bound");
          for(unsigned c=0;c<3;c++){const double ratio=Ratio(std::fabs(e.h[c]),e.budget[c]);Need(ratio<=1,"Double affine Hessian exceeded original forward bound");affineRatio=(std::max)(affineRatio,ratio);}
          maxAffineRatio=(std::max)(maxAffineRatio,affineRatio);affineChecks++;
        }
        if(mode&&affine)maxFloatAffine=(std::max)(maxFloatAffine,std::fabs(e.scalar)); // Diagnostic only, never a zero/convergence gate.
        const unsigned key=(((kernel*2+jitter)*2+mode)*8+f)*3+variant;
        // Project Cubic is the actual archived continuous profile, not a repair
        // silently attributed to the inconsistent inner cubic printed in Eq21.
        csv<<(kernel?"projectCubic_h1p2":"production_Wendland_h1p8")<<','<<(jitter?"fixed_jitter_008dp":"ordered")<<','<<denominator<<','<<a.dp<<','<<a.h<<','<<a.eta<<','<<a.volume
          <<",0,0,"<<a.nodes.size()<<','<<n.pairs.size()<<','<<a.condition<<','<<a.affineResidual<<','<<a.scaleRatio<<','<<(mode?"float_quantized_pressure":"double_pressure")<<','<<Fields[f]<<','<<Variants[variant]
          <<','<<exact<<','<<e.scalar<<','<<error<<',';
        if(exact!=0)csv<<error/std::fabs(exact);csv<<',';
        if(std::isfinite(previous[key])&&error>0)csv<<previous[key]/error;previous[key]=error;
        csv<<','<<literal.h[0]+literal.h[3];for(double value:literal.h)csv<<','<<value;for(double value:e.h)csv<<','<<value;
        csv<<','<<e.gp.x<<','<<e.gp.z<<','<<One(Sub(e.gp,truth.gradient))<<','<<quantization<<','<<traceRatio<<',';
        if(!variant)csv<<directRatio;csv<<','<<int(!mode&&affine)<<',';if(!mode&&affine)csv<<affineRatio;
        csv<<','<<int(mode&&affine)<<'\n';responses++;
      }
    }
  }
  Need(clouds==12&&responses==576&&constantChecks==72&&affineChecks==72&&formulaChecks==576&&directChecks==192,"Declared fixed coverage differs");
  csv.flush();Need(bool(csv),"Response CSV write failed");
  std::ofstream done(dir/"completion.json");done<<std::setprecision(17)
    <<"{\"stage\":\"upl_lian_scalar_kernel_r2\",\"passed\":true,\"arithmetic_checks_passed\":true,\"clouds\":"<<clouds<<",\"responses\":"<<responses
    <<",\"max_nodes_per_cloud\":361,\"fixed_receiver\":true,\"neighbor_C_full_support_guard_verified\":true,\"kernel_Fac_bitwise_parity_checks\":"<<kernelParity
    <<",\"constant_exact_null_checks\":"<<constantChecks<<",\"double_affine_component_group_checks\":"<<affineChecks
    <<",\"matched_trace_formula_checks\":"<<formulaChecks<<",\"printed_direct_Eq23_trace_checks\":"<<directChecks
    <<",\"max_matched_trace_roundoff_ratio\":"<<maxTraceRatio<<",\"max_direct_trace_roundoff_ratio\":"<<maxDirectRatio
    <<",\"max_double_affine_roundoff_ratio\":"<<maxAffineRatio<<",\"max_kernel_amplitude_invariance_roundoff_ratio\":"<<maxScaleRatio
    <<",\"max_float_affine_scalar_abs_DIAGNOSTIC\":"<<maxFloatAffine
    <<",\"operator_gradient_is_approximate_Eq22\":true,\"analytic_gradient_inserted_into_operator\":false,\"float_affine_zero_or_convergence_gate\":false"
    <<",\"projectCubic_h1p2_is_controlled_condition\":true,\"literal_printed_Eq21_kernel_reproduction\":false,\"Eta2_regularizes_F_only_not_D4\":true"
    <<",\"single_thread_no_OpenMP\":true,\"own_priority_class\":"<<GetPriorityClass(GetCurrentProcess())<<",\"own_affinity_mask\":"<<selected
    <<",\"wall_fixture_or_variable_k_tested\":false,\"global_matrix_or_spectrum\":false,\"production_JSph_or_solver_called\":false"
    <<",\"kernel_production_setting_changed\":false,\"P2_or_accuracy_gate_added\":false,\"Eq23_accuracy_accepted\":false,\"physical_acceptance\":false"
    <<",\"wall_seconds\":"<<std::chrono::duration<double>(Clock::now()-started).count()<<"}\n";
  done.flush();Need(bool(done),"Completion JSON write failed");return 0;
}
}

int main(int argc,char** argv){try{
  scalar_r2::Need(argc==2,"Use STANDALONE_PROGRAM FRESH_SHALLOW_OUTPUT_DIRECTORY");
  return scalar_r2::Run(argv[1]);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Standalone scalar diagnostic failed; preserve partial output\n";return 2;}}

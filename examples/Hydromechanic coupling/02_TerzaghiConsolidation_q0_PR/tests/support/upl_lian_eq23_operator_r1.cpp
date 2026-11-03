// Standalone 2D constant-k/J=1 manufactured operator diagnostic. No JSph or BI4.
// Root must compile against the frozen archived header closure, never live headers.
#include "FunSphKernel.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace eq23 {
using Clock=std::chrono::steady_clock;
static void Need(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
struct V2 {double x=0,z=0;};
static V2 Add(V2 a,V2 b){return{a.x+b.x,a.z+b.z};}
static V2 Sub(V2 a,V2 b){return{a.x-b.x,a.z-b.z};}
static V2 Mul(V2 a,double b){return{a.x*b,a.z*b};}
static double Dot(V2 a,V2 b){return a.x*b.x+a.z*b.z;}
static double One(V2 a){return std::fabs(a.x)+std::fabs(a.z);}
struct M2 {double xx=0,xz=0,zx=0,zz=0;};
static V2 Apply(M2 a,V2 b){return{a.xx*b.x+a.xz*b.z,a.zx*b.x+a.zz*b.z};}
static double Norm(M2 a){return(std::max)(std::fabs(a.xx)+std::fabs(a.xz),std::fabs(a.zx)+std::fabs(a.zz));}
static double Gamma(unsigned n){const double v=n*DBL_EPSILON;Need(v<.01,"Roundoff operation count invalid");return v/(1-v);}
struct Pair {unsigned j;V2 d,g;double rr;};
struct Node {V2 x;M2 m,c;std::vector<Pair> pairs;double cond=0,inverseResidual=0,affineResidual=0,momentAbs=0;bool interior=false;};
struct Cloud {unsigned nx;bool jitter,periodic;double dp,h,V,eta;std::vector<Node> a;};
static std::uint32_t Hash(unsigned x,unsigned z,unsigned salt){
  std::uint32_t v=std::uint32_t(x)*0x9e3779b9u^std::uint32_t(z)*0x85ebca6bu^salt;
  v^=v>>16;v*=0x7feb352du;v^=v>>15;v*=0x846ca68bu;return v^(v>>16);
}
static double Jitter(unsigned x,unsigned z,unsigned salt){return(double(Hash(x,z,salt)&65535u)/65535.-.5)*.16;}
static Cloud Make(unsigned nx,bool jitter,bool periodic){
  Cloud a; a.nx=nx;a.jitter=jitter;a.periodic=periodic;a.dp=1./nx;a.V=a.dp*a.dp;
  a.h=double(float(1.8*a.dp));a.eta=double(float((.1*a.h)*(.1*a.h)));
  const float hf=float(a.h),support=float(2*a.h),support2=support*support;
  Need(!periodic||support<.5f,"Periodic support must have a unique minimum image");
  const auto kernel=fsph::GetKernelWendland_Ctes(true,a.h);a.a.resize(nx*nx);
  for(unsigned z=0;z<nx;z++)for(unsigned x=0;x<nx;x++){
    auto& n=a.a[x+nx*z];n.x={(x+.5+(jitter?Jitter(x,z,17):0))*a.dp,(z+.5+(jitter?Jitter(x,z,71):0))*a.dp};
    n.interior=periodic||(std::min)({n.x.x,n.x.z,1-n.x.x,1-n.x.z})>=double(support);
  }
  for(unsigned i=0;i<a.a.size();i++){
    auto& n=a.a[i];
    for(unsigned j=0;j<a.a.size();j++){
      V2 d=Sub(n.x,a.a[j].x);if(periodic){d.x-=std::round(d.x);d.z-=std::round(d.z);}
      const double rr=Dot(d,d);if(rr>double(support2)||rr<ALMOSTZERO)continue;
      // Rate expression's double displacement, float rr/kernel factor, double product.
      const double fac=fsph::GetKernelWendland_Fac(kernel,hf,float(rr));const V2 g=Mul(d,fac);
      n.pairs.push_back({j,d,g,rr});
      // Same 2D moment/inverse arithmetic pattern as FsCorrMatInverse; J=1,V constant.
      n.m.xx+=-d.x*g.x*a.V;n.m.xz+=-d.x*g.z*a.V;
      n.m.zx+=-d.z*g.x*a.V;n.m.zz+=-d.z*g.z*a.V;
    }
    Need(!n.pairs.empty(),"Empty manufactured support");
    const double det=n.m.xx*n.m.zz-n.m.xz*n.m.zx;
    Need(std::isfinite(det)&&det>0,"Singular/nonpositive manufactured moment");
    n.c={n.m.zz/det,-n.m.xz/det,-n.m.zx/det,n.m.xx/det};n.cond=Norm(n.m)*Norm(n.c);
    M2 e{n.c.xx*n.m.xx+n.c.xz*n.m.zx-1,n.c.xx*n.m.xz+n.c.xz*n.m.zz,
         n.c.zx*n.m.xx+n.c.zz*n.m.zx,n.c.zx*n.m.xz+n.c.zz*n.m.zz-1};
    n.inverseResidual=Norm(e);M2 b;
    for(const auto& p:n.pairs){const V2 r=Mul(p.d,-1),gi=Apply(n.c,p.g);
      b.xx+=a.V*gi.x*r.x;b.xz+=a.V*gi.x*r.z;b.zx+=a.V*gi.z*r.x;b.zz+=a.V*gi.z*r.z;
      n.momentAbs+=a.V*One(gi)*One(r);
    }
    b.xx-=1;b.zz-=1;n.affineResidual=Norm(b);
    Need(std::isfinite(n.cond)&&Gamma(unsigned(64*n.pairs.size()+256))*n.cond<.01,"Conditioning makes the declared roundoff bound uninformative");
  }
  return a;
}

static const char* Fields[]={"1","x","z","x2","xz","z2","cos2pi_x"};
static const char* Variants[]={"literal_receiver_C_r2","receiver_C_Eta2","pair_C_Eta2","pair_C_Eta2_tangent_Neumann"};
struct Truth {double p;V2 grad;std::array<double,3> h;};
static Truth Field(unsigned f,V2 x){
  const double k=2*std::acos(-1.);
  switch(f){
    case 0:return{1,{0,0},{0,0,0}};case 1:return{x.x,{1,0},{0,0,0}};case 2:return{x.z,{0,1},{0,0,0}};
    case 3:return{x.x*x.x,{2*x.x,0},{2,0,0}};case 4:return{x.x*x.z,{x.z,x.x},{0,1,0}};
    case 5:return{x.z*x.z,{0,2*x.z},{0,0,2}};
    default:return{std::cos(k*x.x),{-k*std::sin(k*x.x),0},{-k*k*std::cos(k*x.x),0,0}};
  }
}
static bool Tangent(unsigned f){return f==0||f==1||f==3||f==6;}
struct Eval {std::array<double,3> h{},budget{};V2 gp;double scalar=0,traceBudget=0,scale=0,gradientBudget=0,inputQuantization=0;};
// Direct XZ specialization of ComputeDynamicPorePressureRateCpu's lp/lx/gp path.
// Actual float-pressure mode is used separately; this function is no JSph execution.
static double ProductionExpression(const Cloud& a,unsigned i,const std::vector<double>& p,unsigned variant,V2* gradient=nullptr){
  const auto& n=a.a[i];double lp=0;V2 lx,gp;
  for(const auto& q:n.pairs){const V2 gi=Apply(n.c,q.g),gj=Apply(variant<2?n.c:a.a[q.j].c,q.g);
    const double dp=p[i]-p[q.j],w=a.V*(q.d.x*(gi.x+gj.x)+q.d.z*(gi.z+gj.z))/(q.rr+(variant? a.eta:0));
    lp+=w*dp;lx=Add(lx,Mul(q.d,w));gp=Sub(gp,Mul(gi,a.V*dp));
  }
  if(variant==3)gp.z-=gp.z; // n=(0,1), Ace=0: only analytically tangent fields are admitted.
  if(gradient)*gradient=gp;
  return lp-gp.x*lx.x-gp.z*lx.z;
}
static Eval Literal(const Cloud& a,unsigned i,const std::vector<double>& p,unsigned variant,unsigned f,bool storedFloat){
  const auto& n=a.a[i];Eval out;const double u=Gamma(unsigned(64*n.pairs.size()+256));
  double gpScale=0;const Truth ti=Field(f,n.x);
  for(const auto& q:n.pairs){const V2 gi=Apply(n.c,q.g);const double delta=p[q.j]-p[i];
    out.gp=Add(out.gp,Mul(gi,a.V*delta));gpScale+=a.V*One(gi)*(std::fabs(p[q.j])+std::fabs(p[i]));
    out.inputQuantization=(std::max)(out.inputQuantization,std::fabs(p[q.j]-Field(f,a.a[q.j].x).p));
  }
  out.inputQuantization=(std::max)(out.inputQuantization,std::fabs(p[i]-ti.p));
  // The float kernel samples are fixed operands shared by M,C,gp: no spurious
  // FLT_EPS multiplier on the inverse identity. Pressure storage is a distinct term.
  double inputGradient=0;
  for(const auto& q:n.pairs){const V2 gi=Apply(n.c,q.g);const auto tj=Field(f,a.a[q.j].x);
    const double pressureBound=(storedFloat?double(FLT_EPSILON):0)*(std::fabs(ti.p)+std::fabs(tj.p));
    inputGradient+=a.V*One(gi)*pressureBound;
  }
  out.gradientBudget=(n.affineResidual+u*n.momentAbs)*One(ti.grad)+u*gpScale+inputGradient;
  if(variant==3)out.gp.z-=out.gp.z;
  double absoluteTrace=0,productionScale=0;
  for(const auto& q:n.pairs){
    const V2 r=Mul(q.d,-1),gi=Apply(n.c,q.g),gj=Apply(variant<2?n.c:a.a[q.j].c,q.g);
    const double delta=p[q.j]-p[i],defect=delta-Dot(out.gp,r);
    const double F=Dot(r,variant<2?gi:Mul(Add(gi,gj),.5))/(q.rr+(variant?a.eta:0));
    const std::array<double,3> D={4*r.x*r.x/q.rr-1,4*r.x*r.z/q.rr,4*r.z*r.z/q.rr-1};
    const auto tj=Field(f,a.a[q.j].x);
    const double pressureBound=((storedFloat?double(FLT_EPSILON):0)+u)*(std::fabs(ti.p)+std::fabs(tj.p));
    const double defectBound=pressureBound+One(r)*out.gradientBudget+u*(std::fabs(out.gp.x*r.x)+std::fabs(out.gp.z*r.z));
    for(unsigned c=0;c<3;c++){const double v=a.V*defect*D[c]*F;out.h[c]+=v;out.budget[c]+=std::fabs(a.V*D[c]*F)*defectBound+u*std::fabs(v);}
    absoluteTrace+=std::fabs(a.V*defect*D[0]*F)+std::fabs(a.V*defect*D[2]*F);
    const double w=a.V*Dot(q.d,Add(gi,gj))/(q.rr+(variant?a.eta:0));
    productionScale+=std::fabs(w*(p[i]-p[q.j]))+std::fabs(w)*(std::fabs(out.gp.x*q.d.x)+std::fabs(out.gp.z*q.d.z));
  }
  out.scalar=ProductionExpression(a,i,p,variant);out.scale=absoluteTrace+productionScale;
  out.traceBudget=u*out.scale;return out;
}
struct Stats {
  unsigned count=0;std::array<double,3> sq{},max{},sum{},bound{};double traceSq=0,traceMax=0,scalarSq=0,scalarMax=0,gradMax=0,condition=0,traceRatio=0,affineRatio=0,quantization=0;
};
static double Ratio(double error,double bound){if(bound==0){Need(error==0,"Nonzero residual with zero forward bound");return 0;}return error/bound;}
static void Measurements(const Cloud& a,std::ofstream& moments,std::ofstream& csv,std::uint64_t& receivers,std::uint64_t& constantChecks,std::uint64_t& affineChecks,std::uint64_t& traceChecks){
  const char* cloud=a.jitter?"fixed_jitter_008dp":"ordered";
  for(unsigned i=0;i<a.a.size();i++){const auto& n=a.a[i];
    moments<<cloud<<','<<a.nx<<','<<i<<','<<(n.interior?"interior":"truncated")<<','<<n.x.x<<','<<n.x.z<<','<<n.pairs.size()<<','<<a.dp<<','<<a.h<<','<<a.eta<<','<<a.V<<','<<n.m.xx<<','<<n.m.xz<<','<<n.m.zx<<','<<n.m.zz<<','<<n.c.xx<<','<<n.c.xz<<','<<n.c.zx<<','<<n.c.zz<<','<<n.cond<<','<<n.inverseResidual<<','<<n.affineResidual<<'\n';receivers++;
  }
  for(unsigned f=0;f<7;f++)for(unsigned mode=0;mode<2;mode++){
    std::vector<double> p;for(const auto& n:a.a){const double v=Field(f,n.x).p;p.push_back(mode?double(float(v)):v);}
    for(unsigned variant=0;variant<4;variant++){
      if(variant==3&&!Tangent(f))continue;std::array<Stats,2> groups;
      for(unsigned i=0;i<a.a.size();i++){
        const auto& n=a.a[i];const auto v=Literal(a,i,p,variant,f,mode!=0);const auto truth=Field(f,n.x);auto& s=groups[n.interior?0:1];s.count++;
        for(unsigned c=0;c<3;c++){const double error=std::fabs(v.h[c]-truth.h[c]);s.sq[c]+=error*error;s.max[c]=(std::max)(s.max[c],error);s.sum[c]+=v.h[c];s.bound[c]=(std::max)(s.bound[c],v.budget[c]);Need(std::isfinite(v.h[c])&&std::isfinite(v.budget[c]),"Nonfinite manufactured Hessian or bound");}
        const double exactTrace=truth.h[0]+truth.h[2],te=std::fabs(v.h[0]+v.h[2]-exactTrace),se=std::fabs(v.scalar-exactTrace);
        s.traceSq+=te*te;s.traceMax=(std::max)(s.traceMax,te);s.scalarSq+=se*se;s.scalarMax=(std::max)(s.scalarMax,se);
        s.gradMax=(std::max)(s.gradMax,One(Sub(v.gp,truth.grad)));s.condition=(std::max)(s.condition,n.cond);s.quantization=(std::max)(s.quantization,v.inputQuantization);
        const double traceError=std::fabs(v.h[0]+v.h[2]-v.scalar),ratio=Ratio(traceError,v.traceBudget);s.traceRatio=(std::max)(s.traceRatio,ratio);
        Need(std::isfinite(v.scalar)&&traceError<=v.traceBudget,"Matched tensor/scalar expression exceeded declared forward bound");traceChecks++;
        if(f==0){Need(v.gp.x==0&&v.gp.z==0&&v.h[0]==0&&v.h[1]==0&&v.h[2]==0&&v.scalar==0,"Constant null is not exact");constantChecks++;}
        if(f==1||f==2){for(unsigned c=0;c<3;c++){const double r=Ratio(std::fabs(v.h[c]),v.budget[c]);s.affineRatio=(std::max)(s.affineRatio,r);Need(std::fabs(v.h[c])<=v.budget[c],"Affine Hessian exceeded declared forward bound");}affineChecks++;}
      }
      for(unsigned region=0;region<2;region++){const auto& s=groups[region];Need(s.count>0,"Manufactured region empty");
        csv<<cloud<<','<<a.nx<<','<<a.dp<<','<<(mode?"production_float_pressure":"double_manufactured_pressure")<<','<<Fields[f]<<','<<Variants[variant]<<','<<(region?"truncated":"interior")<<','<<s.count<<','<<int(f==1||f==2);
        for(unsigned c=0;c<3;c++)csv<<','<<s.sum[c]/s.count<<','<<std::sqrt(s.sq[c]/s.count)<<','<<s.max[c]<<','<<s.bound[c];
        csv<<','<<std::sqrt(s.traceSq/s.count)<<','<<s.traceMax<<','<<std::sqrt(s.scalarSq/s.count)<<','<<s.scalarMax<<','<<s.gradMax<<','<<s.condition<<','<<s.traceRatio<<','<<s.affineRatio<<','<<s.quantization<<'\n';
      }
    }
  }
}

static void Matrix(const Cloud& a,std::ofstream& matrix,std::ofstream& diagnostic){
  const unsigned n=unsigned(a.a.size());const auto started=Clock::now();const char* cloud=a.jitter?"fixed_jitter_008dp":"ordered";
  Need(n==64&&a.periodic,"Only64-node periodic matrix diagnostic admitted");
  for(unsigned variant=0;variant<3;variant++){
    std::vector<double> A(n*n),p(n);
    for(unsigned j=0;j<n;j++){p[j]=1;for(unsigned i=0;i<n;i++)A[i*n+j]=ProductionExpression(a,i,p,variant);p[j]=0;}
    double rowMax=0,columnMax=0,symmetry=0,frobenius=0;
    for(unsigned i=0;i<n;i++){double row=0,column=0;matrix<<cloud<<','<<Variants[variant]<<','<<i;
      for(unsigned j=0;j<n;j++){const double value=A[i*n+j];Need(std::isfinite(value),"Nonfinite periodic coefficient");matrix<<','<<value;row+=value;column+=a.V*A[j*n+i];symmetry=(std::max)(symmetry,std::fabs(value-A[j*n+i]));frobenius+=value*value;}
      matrix<<'\n';rowMax=(std::max)(rowMax,std::fabs(row));columnMax=(std::max)(columnMax,std::fabs(column));
    }
    std::fill(p.begin(),p.end(),1.);for(unsigned i=0;i<n;i++)Need(ProductionExpression(a,i,p,variant)==0,"Periodic constant null is not exact");
    diagnostic<<cloud<<','<<Variants[variant]<<','<<n<<','<<a.V<<','<<rowMax<<','<<columnMax<<','<<symmetry<<','<<std::sqrt(frobenius)<<','<<A.size()*sizeof(double)<<','<<std::chrono::duration<double>(Clock::now()-started).count()<<'\n';
  }
}
} // namespace eq23

int main(int argc,char** argv){try{
  using namespace eq23;Need(argc==2,"Use NEW_OUTPUT_DIRECTORY (root captures program, argv, exit and hashes)");
  const std::filesystem::path dir=argv[1];Need(!std::filesystem::exists(dir),"Retained output protected; preserve partial failure without retry");
  Need(std::filesystem::create_directory(dir),"Fresh output directory creation failed");const auto started=Clock::now();
  std::ofstream moments(dir/"moments.csv"),fields(dir/"fields.csv"),matrix(dir/"periodic_matrix.csv"),diagnostic(dir/"periodic_diagnostics.csv");
  for(auto* s:{&moments,&fields,&matrix,&diagnostic}){Need(bool(*s),"New CSV open failed");*s<<std::setprecision(17);}
  moments<<"cloud,nx,receiver,region,x,z,neighbors,dp,h,Eta2,V,Mxx,Mxz,Mzx,Mzz,Cxx,Cxz,Czx,Czz,condition_inf,inverse_residual_inf,corrected_affine_residual_inf\n";
  fields<<"cloud,nx,dp,pressure_storage,field,variant,region,receivers,affine_forward_bound_applicable,Hxx_mean,Hxx_error_RMS,Hxx_error_max,Hxx_affine_forward_bound_max,Hxz_mean,Hxz_error_RMS,Hxz_error_max,Hxz_affine_forward_bound_max,Hzz_mean,Hzz_error_RMS,Hzz_error_max,Hzz_affine_forward_bound_max,trace_error_RMS,trace_error_max,scalar_expression_error_RMS,scalar_expression_error_max,gradient_L1_error_max,condition_inf_max,matched_trace_roundoff_ratio_max,affine_roundoff_ratio_max,input_float_quantization_max\n";
  matrix<<"cloud,variant,row";for(unsigned j=0;j<64;j++)matrix<<",a"<<j;matrix<<'\n';
  diagnostic<<"cloud,variant,n,V,row_sum_abs_max,volume_weighted_column_sum_abs_max,antisymmetry_abs_max,Frobenius_norm,matrix_storage_bytes,cumulative_matrix_wall_seconds\n";
  std::uint64_t receivers=0,constantChecks=0,affineChecks=0,traceChecks=0;
  for(bool jitter:{false,true})for(unsigned nx:{16u,24u,32u})Measurements(Make(nx,jitter,false),moments,fields,receivers,constantChecks,affineChecks,traceChecks);
  for(bool jitter:{false,true})Matrix(Make(8,jitter,true),matrix,diagnostic);
  Need(receivers==3712&&constantChecks==29696&&affineChecks==51968&&traceChecks==185600,"Incomplete fixed manufactured case coverage");
  for(auto* s:{&moments,&fields,&matrix,&diagnostic}){s->flush();Need(bool(*s),"CSV flush failed");}
  std::ofstream done(dir/"completion.json");Need(bool(done),"Completion open failed");done<<std::setprecision(17)
    <<"{\"stage\":\"upl_lian_eq23_operator_r1\",\"basic_arithmetic_checks_passed\":true,\"dimension\":2,\"constant_k\":true,\"J\":1,\"manufactured_receivers\":"<<receivers
    <<",\"exact_constant_checks\":"<<constantChecks<<",\"affine_forward_bound_checks\":"<<affineChecks<<",\"matched_trace_forward_bound_checks\":"<<traceChecks
    <<",\"periodic_matrix_nodes\":64,\"periodic_matrices\":6,\"eigenvalues_computed_by_this_program\":false,\"quadratic_or_smooth_accuracy_threshold_applied\":false,\"quadratic_exactness_claimed\":false,\"convergence_order_accepted\":false,\"production_JSph_or_trajectory_executed\":false,\"general_Neumann_boundary_acceptance\":false,\"Eq23_discrete_accuracy_accepted\":false,\"physical_acceptance\":false,\"wall_seconds\":"<<std::chrono::duration<double>(Clock::now()-started).count()<<"}\n";
  done.flush();Need(bool(done),"Completion flush failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

// Frozen-quadrature 2D pressure-only comparison; no JSph call, wall or trajectory.
// Eq25 pressure weighting is normalized with gamma=1/common mobility omitted.
// The PDF's defect term lacks a visible repeated 1/gamma: this is NOT a literal
// reproduction of that dimensionally ambiguous complete printed pressure rate.
#define main RetainedScalarKernelR4Main
#include "upl_lian_scalar_kernel_r4.cpp"
#undef main

namespace variable_scalar_r1 {
using namespace scalar_r4;
static const double N0=double(float(.3)),Rho0=2100.,Water=1000.,K0=double(float(.0001)),Ck=1./8.;
static const double Alpha=1./((1.-N0)*Ck);
static const char* States[]={"J1_law_ON","uniform_J_law_ON","affine_J_law_ON","affine_J_constant_law_OFF"};
static const char* Branches[]={"receiver_C_r2","production_pair_C_Eta2"};
static const char* Methods[]={"production_product_rule_pattern","Eq25_pressure_weight_pattern_gamma1"};
struct State {Cloud a;unsigned kind=0;bool variable=false;V gradJ;std::vector<double> j,n,v,rho,k;};
static double Law(double j,bool variable){return !variable||j==1.?K0:K0*std::exp((j-1.)/((1.-N0)*Ck));}
static void Deadline(Clock::time_point start){
  Need(std::chrono::duration<double>(Clock::now()-start).count()<1.,"One-second private diagnostic budget reached; preserve partial output");
}
static State Manufacture(const Cloud& geometry,unsigned kind){
  State s;s.a=geometry;s.kind=kind;s.variable=kind!=3;s.gradJ=kind>=2?V{1./32.,1./64.}:V{};
  const auto count=s.a.nodes.size();s.j.resize(count);s.n.resize(count);s.v.resize(count);s.rho.resize(count);s.k.resize(count);
  // Dyadic dp makes this exact float reference mass divided by rho0 equal dp^2.
  const double v0=double(float(Rho0*s.a.dp*s.a.dp))/Rho0;
  Need(v0==s.a.volume,"Reference mass/rho0 quadrature differs from the retained cloud");
  for(unsigned i=0;i<count;i++){
    s.j[i]=kind==1?1.+1./64.:1.+Dot(s.gradJ,s.a.nodes[i].x);
    s.n[i]=1.-(1.-N0)/s.j[i];s.v[i]=v0*s.j[i];s.rho[i]=Water+(Rho0-Water)/s.j[i];s.k[i]=Law(s.j[i],s.variable);
    Need(s.j[i]>1.-N0&&s.n[i]>0&&s.n[i]<1&&std::isfinite(s.v[i])&&s.v[i]>0&&std::isfinite(s.rho[i])&&s.rho[i]>0
      &&std::isfinite(s.k[i])&&s.k[i]>0,"Frozen J/n/V/rho/k state invalid");
  }
  for(unsigned i=0;i<count;i++){
    auto& node=s.a.nodes[i];node.moment=M{};
    for(const auto& q:node.pairs){
      node.moment.xx-=s.v[q.j]*q.d.x*q.g.x;node.moment.xz-=s.v[q.j]*q.d.x*q.g.z;
      node.moment.zx-=s.v[q.j]*q.d.z*q.g.x;node.moment.zz-=s.v[q.j]*q.d.z*q.g.z;
    }
    node.c=Inverse(node.moment);node.condition=Norm(node.moment)*Norm(node.c);
    Need(std::isfinite(node.condition)&&Gamma(unsigned(128*node.pairs.size()+512))*node.condition<.01,"Current-J C conditioning exceeds forward-bound domain");
  }
  const auto& receiver=s.a.nodes[Receiver];M first;s.a.condition=receiver.condition;s.a.momentAbs=0;
  for(const auto& q:receiver.pairs){
    const auto& x=s.a.nodes[q.j].x;const double support=2*s.a.h;
    Need(std::fabs(x.x)+support<=(Guard-.08)*s.a.dp&&std::fabs(x.z)+support<=(Guard-.08)*s.a.dp,"Used neighbor C lacks complete support margin");
    const V r=Mul(q.d,-1),g=Apply(receiver.c,q.g);const double v=s.v[q.j];
    first.xx+=v*g.x*r.x;first.xz+=v*g.x*r.z;first.zx+=v*g.z*r.x;first.zz+=v*g.z*r.z;
    s.a.momentAbs+=v*One(g)*One(r);s.a.condition=(std::max)(s.a.condition,s.a.nodes[q.j].condition);
  }
  first.xx-=1;first.zz-=1;s.a.affineResidual=Norm(first);
  Need(s.a.affineResidual<=Gamma(unsigned(128*receiver.pairs.size()+512))*s.a.momentAbs,"Current-J corrected first moment exceeds declared arithmetic bound");
  return s;
}
struct Weight {V gi,gj;double denominator,w,F,Dxx,Dxz,Dzz;};
static Weight Coefficient(const State& s,const Pair& q,unsigned branch){
  Weight a;a.gi=Apply(s.a.nodes[Receiver].c,q.g);a.gj=branch?Apply(s.a.nodes[q.j].c,q.g):a.gi;
  a.denominator=q.rr+(branch?s.a.eta:0.);a.w=s.v[q.j]*Dot(q.d,Add(a.gi,a.gj))/a.denominator;
  const V r=Mul(q.d,-1);a.F=Dot(r,branch?Mul(Add(a.gi,a.gj),.5):a.gi)/a.denominator;
  a.Dxx=4*r.x*r.x/q.rr-1;a.Dxz=4*r.x*r.z/q.rr;a.Dzz=4*r.z*r.z/q.rr-1;return a;
}
struct Evaluation {double lp=0,rawK=0,lstar=0,defect=0,chain=0,product=0,eq25=0,direct=0,budget=0;V gp,gj,gk;};
static Evaluation Evaluate(const State& s,const std::vector<double>& pressure,unsigned branch){
  Evaluation e;V lx,directDefect,absGp,absLx,absDirect;double directRaw=0,absLp=0,absRaw=0,absPaper=0;
  const double ki=s.k[Receiver];
  for(const auto& q:s.a.nodes[Receiver].pairs){
    const auto a=Coefficient(s,q,branch);const double dp=pressure[Receiver]-pressure[q.j],kbar=.5*(ki+s.k[q.j]);
    const double term=a.w*dp;e.lp+=term;e.rawK+=kbar*term;lx=Add(lx,Mul(q.d,a.w));
    const V gpTerm=Mul(a.gi,-s.v[q.j]*dp);e.gp=Add(e.gp,gpTerm);
    e.gj=Add(e.gj,Mul(a.gi,s.v[q.j]*(s.j[q.j]-s.j[Receiver])));
    absLp+=std::fabs(term);absRaw+=std::fabs(kbar*term);
    absGp=Add(absGp,{std::fabs(gpTerm.x),std::fabs(gpTerm.z)});
    absLx=Add(absLx,{std::fabs(q.d.x*a.w),std::fabs(q.d.z*a.w)});
    // Independently accumulate the two pressure sums using r_ji, F and literal
    // D4/r^2. Only F is regularized in the deliberately adapted pair-C branch.
    const V r=Mul(q.d,-1);const double c=s.v[q.j]*(a.Dxx+a.Dzz)*a.F;
    const double raw=c*kbar*(pressure[q.j]-pressure[Receiver]);directRaw+=raw;absPaper+=std::fabs(raw);
    directDefect=Add(directDefect,Mul(r,c));absDirect=Add(absDirect,{std::fabs(r.x*c),std::fabs(r.z*c)});
  }
  e.gk=s.variable?Mul(e.gj,Alpha*ki):V{};e.defect=Dot(e.gp,lx);e.lstar=e.lp-e.defect;
  e.chain=Dot(e.gk,e.gp);e.product=ki*e.lstar+e.chain;
  e.eq25=e.rawK-ki*e.defect; // Receiver ki on the unweighted gradient defect, NEVER pair-k on that whole defect.
  e.direct=directRaw-ki*Dot(e.gp,directDefect);
  // Declared before results: gamma_(128*m+512), operand-scaled, no absolute
  // floor. This bounds formula/reduction roundoff, NOT continuum accuracy.
  const double scale=absRaw+absPaper+std::fabs(ki)*(absLp+Dot(absGp,absLx)+Dot(absGp,absDirect))
    +std::fabs(e.chain)+std::fabs(e.product)+std::fabs(e.eq25)+std::fabs(e.direct);
  e.budget=Gamma(unsigned(128*s.a.nodes[Receiver].pairs.size()+512))*scale;
  Need(std::isfinite(e.product)&&std::isfinite(e.eq25)&&std::isfinite(e.direct)&&std::isfinite(e.budget),"Nonfinite normalized pressure operator");
  return e;
}
static void FrozenRows(const State& s,unsigned geometry,std::ostream& nodes,std::ostream& weights){
  for(unsigned i=0;i<s.a.nodes.size();i++){
    const auto& n=s.a.nodes[i];nodes<<geometry<<','<<s.a.denominator<<','<<int(s.a.jitter)<<','<<States[s.kind]<<','<<i
      <<','<<n.x.x<<','<<n.x.z<<','<<s.j[i]<<','<<s.n[i]<<','<<s.v[i]<<','<<s.rho[i]<<','<<s.k[i]
      <<','<<n.c.xx<<','<<n.c.xz<<','<<n.c.zx<<','<<n.c.zz<<','<<n.pairs.size()<<','<<n.condition<<'\n';
  }
  for(unsigned branch=0;branch<2;branch++)for(const auto& q:s.a.nodes[Receiver].pairs){
    const auto a=Coefficient(s,q,branch);weights<<geometry<<','<<States[s.kind]<<','<<Branches[branch]<<','<<q.j
      <<','<<q.d.x<<','<<q.d.z<<','<<q.rr<<','<<s.v[q.j]<<','<<s.k[Receiver]<<','<<s.k[q.j]<<','<<.5*(s.k[Receiver]+s.k[q.j])
      <<','<<a.gi.x<<','<<a.gi.z<<','<<a.gj.x<<','<<a.gj.z<<','<<a.denominator<<','<<a.w<<','<<a.F<<','<<a.Dxx<<','<<a.Dxz<<','<<a.Dzz<<'\n';
  }
}
static int Run(const std::filesystem::path& dir){
  const auto started=Clock::now();Need(!std::filesystem::exists(dir),"Retained output protected; use one fresh shallow directory");
  Need(SetPriorityClass(GetCurrentProcess(),BELOW_NORMAL_PRIORITY_CLASS)!=0,"Cannot lower this diagnostic priority");
  DWORD_PTR allowed=0,system=0;Need(GetProcessAffinityMask(GetCurrentProcess(),&allowed,&system)!=0&&allowed,"Cannot read own affinity");
  const DWORD_PTR selected=allowed&(~allowed+1);Need(SetProcessAffinityMask(GetCurrentProcess(),selected)!=0,"Cannot restrict own process to one allowed CPU");
  std::filesystem::create_directory(dir);std::ofstream rows(dir/"responses.csv"),nodes(dir/"states.csv"),weights(dir/"weights.csv");
  for(auto* stream:{&rows,&nodes,&weights})*stream<<std::setprecision(17);
  nodes<<"geometry,dp_denominator,jitter,J_law_state,node,x,z,J,n,V,rho,k,Cxx,Cxz,Czx,Czz,neighbors,C_condition_inf\n";
  weights<<"geometry,J_law_state,C_denominator,neighbor,dx,dz,r2,Vj,ki,kj,kbar,gi_x,gi_z,gj_x,gj_z,F_denominator,w,F,Dxx,Dxz,Dzz\n";
  rows<<"geometry,cloud,dp_denominator,dp,h,Eta2,J_law_state,pressure_storage,field,C_denominator,k_treatment,receiver_neighbors,max_used_C_condition,receiver_J,receiver_n,receiver_V,receiver_rho,receiver_k,analytic_gradk_x,analytic_gradk_z,approx_GJ_x,approx_GJ_z,approx_Gp_x,approx_Gp_z,analytic_div_k_gradp,actual_normalized_source,absolute_continuum_error,relative_continuum_error_if_nonzero,error_ratio_previous_over_current,input_float_quantization_max,unweighted_Lstar,raw_pair_k_sum,receiver_ki_gradient_defect,product_rule_chain,independent_D4_trace,trace_formula_roundoff_ratio,constant_k_reduction_applicable,constant_k_reduction_roundoff_ratio,exact_constant_null_checked\n";
  std::array<double,512> previous;previous.fill(std::numeric_limits<double>::quiet_NaN());
  unsigned geometries=0,states=0,responses=0,traceChecks=0,reductionChecks=0,nullChecks=0;std::uint64_t kernelParity=0;
  double maxTrace=0,maxReduction=0,maxError=0,maxFloatQuantization=0;
  for(unsigned jitter=0;jitter<2;jitter++)for(unsigned denominator:{16u,32u,64u}){
    Deadline(started);const Cloud geometry=Make(denominator,jitter!=0,false);const unsigned number=geometries++;kernelParity+=geometry.kernelParity;
    for(unsigned kind=0;kind<4;kind++){
      Deadline(started);const State s=Manufacture(geometry,kind);states++;FrozenRows(s,number,nodes,weights);
      const double ki=s.k[Receiver];const V analyticGk=s.variable?Mul(s.gradJ,Alpha*ki):V{};
      const bool constantK=kind!=2;
      for(unsigned mode=0;mode<2;mode++)for(unsigned field=0;field<8;field++){
        Deadline(started);std::vector<double> p;double quantization=0;
        for(const auto& node:s.a.nodes){const double exact=Field(field,node.x).value,value=mode?double(float(exact)):exact;
          p.push_back(value);quantization=(std::max)(quantization,std::fabs(value-exact));}
        maxFloatQuantization=(std::max)(maxFloatQuantization,quantization);
        const auto truth=Field(field,s.a.nodes[Receiver].x);const double analytic=ki*(truth.h[0]+truth.h[2])+Dot(analyticGk,truth.gradient);
        for(unsigned branch=0;branch<2;branch++){
          const Evaluation e=Evaluate(s,p,branch);const double tr=Ratio(std::fabs(e.eq25-e.direct),e.budget);
          Need(tr<=1,"Normalized Eq25 scalar/direct D4 trace identity failed");traceChecks++;maxTrace=(std::max)(maxTrace,tr);
          double reduction=0;
          if(constantK){
            Need(e.gk.x==0&&e.gk.z==0&&e.chain==0,"Uniform/constant conductivity has a spurious chain term");
            reduction=Ratio((std::max)(std::fabs(e.product-ki*e.lstar),std::fabs(e.eq25-ki*e.lstar)),e.budget);
            Need(reduction<=1,"Constant-k reduction differs from matching C/denominator scalar route");reductionChecks++;maxReduction=(std::max)(maxReduction,reduction);
          }
          for(unsigned method=0;method<2;method++){
            const double value=method?e.eq25:e.product,error=std::fabs(value-analytic);
            if(field==0){Need(value==0&&e.gp.x==0&&e.gp.z==0&&e.rawK==0&&e.defect==0&&e.chain==0&&e.direct==0,"Constant pressure exact null failed");nullChecks++;}
            // Affine p with variable k has nonzero grad(k).grad(p): no affine-null
            // or continuum-error acceptance threshold is imposed in either precision.
            maxError=(std::max)(maxError,error);const unsigned key=(((((jitter*4+kind)*2+mode)*8+field)*2+branch)*2+method);
            rows<<number<<','<<(jitter?"fixed_jitter_008dp":"ordered")<<','<<denominator<<','<<s.a.dp<<','<<s.a.h<<','<<s.a.eta<<','<<States[kind]
              <<','<<(mode?"float_quantized_pressure":"double_pressure")<<','<<Fields[field]<<','<<Branches[branch]<<','<<Methods[method]
              <<','<<s.a.nodes[Receiver].pairs.size()<<','<<s.a.condition<<','<<s.j[Receiver]<<','<<s.n[Receiver]<<','<<s.v[Receiver]<<','<<s.rho[Receiver]<<','<<ki
              <<','<<analyticGk.x<<','<<analyticGk.z<<','<<e.gj.x<<','<<e.gj.z<<','<<e.gp.x<<','<<e.gp.z<<','<<analytic<<','<<value<<','<<error<<',';
            if(analytic!=0)rows<<error/std::fabs(analytic);rows<<',';if(std::isfinite(previous[key])&&error>0)rows<<previous[key]/error;previous[key]=error;
            rows<<','<<quantization<<','<<e.lstar<<','<<e.rawK<<','<<ki*e.defect<<','<<e.chain<<','<<e.direct<<','<<tr<<','<<int(constantK)<<',';
            if(constantK)rows<<reduction;rows<<','<<int(field==0)<<'\n';responses++;
          }
        }
      }
    }
  }
  Need(geometries==6&&states==24&&responses==1536&&traceChecks==768&&reductionChecks==576&&nullChecks==192,"Declared bounded coverage differs");
  for(auto* stream:{&rows,&nodes,&weights}){stream->flush();Need(bool(*stream),"Bounded diagnostic CSV write failed");}
  Deadline(started);const double elapsed=std::chrono::duration<double>(Clock::now()-started).count();
  std::ofstream done(dir/"completion.json");done<<std::setprecision(17)
    <<"{\"stage\":\"upl_lian_variable_scalar_r1\",\"passed\":true,\"arithmetic_checks_passed\":true,\"geometries\":"<<geometries<<",\"frozen_J_law_states\":"<<states<<",\"responses\":"<<responses
    <<",\"max_nodes_per_state\":361,\"fixed_receiver\":true,\"receiver_and_used_neighbor_C_full_support\":true,\"C_rebuilt_with_current_J_volumes\":true,\"kernel_Fac_bitwise_parity_checks\":"<<kernelParity
    <<",\"normalized_D4_trace_identity_checks\":"<<traceChecks<<",\"constant_k_reduction_checks\":"<<reductionChecks<<",\"constant_pressure_exact_null_checks\":"<<nullChecks
    <<",\"max_trace_roundoff_ratio\":"<<maxTrace<<",\"max_constant_k_reduction_roundoff_ratio\":"<<maxReduction<<",\"max_continuum_error_DIAGNOSTIC\":"<<maxError<<",\"max_float_pressure_quantization\":"<<maxFloatQuantization
    <<",\"k0_m_s\":"<<K0<<",\"n0_float\":"<<N0<<",\"Ck\":"<<Ck<<",\"alpha\":"<<Alpha
    <<",\"pressure_only_common_mobility_factor_omitted_gamma1\":true,\"literal_complete_printed_Eq25_rate_reproduced\":false,\"printed_defect_gamma_scope_unresolved\":true"
    <<",\"receiver_C_r2_is_normalized_Eq25_2D_pressure_weight_trace\":true,\"pair_C_Eta2_Eq25_is_deliberately_adapted\":true,\"D4_denominator_always_bare_r2\":true"
    <<",\"analytic_gradient_inserted_into_operator\":false,\"affine_variable_k_null_gate\":false,\"continuum_error_or_refinement_gate\":false,\"pressure_float_affine_null_gate\":false"
    <<",\"frozen_quadrature_not_compatible_deformed_trajectory\":true,\"production_JSph_or_solver_called\":false,\"acceleration_Darcy_term_tested\":false,\"wall_tested\":false,\"global_matrix_or_spectral_acceptance\":false"
    <<",\"single_native_thread_no_OpenMP\":true,\"own_priority_class\":"<<GetPriorityClass(GetCurrentProcess())<<",\"own_affinity_mask\":"<<selected<<",\"cooperative_wall_budget_s\":1,\"work_wall_seconds_before_completion_write\":"<<elapsed
    <<",\"new_accuracy_gate\":false,\"production_change_admitted\":false,\"physical_acceptance\":false}\n";
  done.flush();Need(bool(done),"Completion write failed");return 0;
}
}

int main(int argc,char** argv){try{
  variable_scalar_r1::Need(argc==2,"Use STANDALONE_PROGRAM FRESH_SHALLOW_OUTPUT_DIRECTORY");
  return variable_scalar_r1::Run(argv[1]);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Variable-k pressure diagnostic rejected; preserve partial output\n";return 2;}}

// r2: same material candidate/points; only the near-zero apex observer uses an absolute roundoff bound.
// No AppInfo, solver, native reader, production objects or external material implementation.
#include "upl_material_apex_candidate_r1.h"
#include "upl_material_general_candidate_r1.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
namespace A=fsoil_apex_candidate_r1;
namespace B=fsoil_general_candidate_r1;
namespace fs=std::filesystem;
using M=std::array<std::array<double,3>,3>;
static constexpr double Pi=3.1415926535897932384626433832795;
static void Need(bool b,const std::string& s){if(!b)throw std::runtime_error(s);}
template<class T>static bool Bits(T a,T b){return !std::memcmp(&a,&b,sizeof(T));}
static std::array<double,6> Six(const A::Stress& s){return {s.xx,s.yy,s.zz,s.xy,s.yz,s.xz};}
static M Matrix(const A::Stress& s){return {{{s.xx,s.xy,s.xz},{s.xy,s.yy,s.yz},{s.xz,s.yz,s.zz}}};}
static A::Stress Stress(const M& a){return {a[0][0],a[1][1],a[2][2],a[0][1],a[1][2],a[0][2]};}
static M Zero(){return M{};}
static M Identity(){return {{{1,0,0},{0,1,0},{0,0,1}}};}
static M Multiply(const M& a,const M& b){M c{};for(int i=0;i<3;i++)for(int j=0;j<3;j++)for(int k=0;k<3;k++)c[i][j]+=a[i][k]*b[k][j];return c;}
static M Transpose(const M& a){M b{};for(int i=0;i<3;i++)for(int j=0;j<3;j++)b[i][j]=a[j][i];return b;}
static M Minus(const M& a,const M& b){M c{};for(int i=0;i<3;i++)for(int j=0;j<3;j++)c[i][j]=a[i][j]-b[i][j];return c;}
static double Dot(const M& a,const M& b){double x=0;for(int i=0;i<3;i++)for(int j=0;j<3;j++)x+=a[i][j]*b[i][j];return x;}
static double Trace(const M& a){return a[0][0]+a[1][1]+a[2][2];}
static M Dev(const M& a){M b=a;const double mean=Trace(a)/3.;for(int i=0;i<3;i++)b[i][i]-=mean;return b;}
struct Inv{double I,q;};
static Inv Independent(const A::Stress& s){const M a=Matrix(s),d=Dev(a);return {Trace(a),std::sqrt(.5*Dot(d,d))};}
static double Diff(const A::Stress& a,const A::Stress& b){const auto x=Six(a),y=Six(b);double e=0;for(int i=0;i<6;i++)e=std::max(e,std::abs(x[i]-y[i]));return e;}
static bool StateBits(const A::State& a,const A::State& b){const auto x=Six(a.stress),y=Six(b.stress);for(int i=0;i<6;i++)if(!Bits(x[i],y[i]))return false;return Bits(a.kappa,b.kappa);}
static bool MaterialBits(const A::Material& a,const A::Material& b){return Bits(a.ModulusK,b.ModulusK)&&Bits(a.ModulusG,b.ModulusG)&&Bits(a.DP_phi,b.DP_phi)&&Bits(a.DP_kc,b.DP_kc)&&Bits(a.DP_psi,b.DP_psi);}
static A::Stress Make(double I,double q){const double m=I/3.;return {m+q,m-q,m,0,0,0};}
static A::Stress Rotate(const A::Stress& s,const M& r){return Stress(Multiply(Multiply(r,Matrix(s)),Transpose(r)));}
static M Rotation(){
  const double a=.37,b=-.51,c=.83;
  const M rx={{{1,0,0},{0,std::cos(c),-std::sin(c)},{0,std::sin(c),std::cos(c)}}};
  const M ry={{{std::cos(b),0,std::sin(b)},{0,1,0},{-std::sin(b),0,std::cos(b)}}};
  const M rz={{{std::cos(a),-std::sin(a),0},{std::sin(a),std::cos(a),0},{0,0,1}}};return Multiply(Multiply(rz,ry),rx);
}
// Independent published PS/C/MC formulas, evaluated from the actual float angle/cohesion inputs.
static A::Material Parameters(int fit,float psi_deg){
  const float E=20e6f,nu=.33f,phi=float(25.*Pi/180.),c=5000.f,psi=float(double(psi_deg)*Pi/180.);
  const float K=float(double(E)/(3.*(1.-2.*double(nu)))),G=float(double(E)/(2.*(1.+double(nu))));
  const double ph=phi,ps=psi,root3=std::sqrt(3.);double alpha,kc,beta;
  if(fit==0){const double d=std::sqrt(9.+12.*std::tan(ph)*std::tan(ph));alpha=std::tan(ph)/d;kc=3.*double(c)/d;beta=std::tan(ps)/std::sqrt(9.+12.*std::tan(ps)*std::tan(ps));}
  else {const double sign=fit==1?-1.:1.;alpha=2.*std::sin(ph)/(root3*(3.+sign*std::sin(ph)));kc=6.*double(c)*std::cos(ph)/(root3*(3.+sign*std::sin(ph)));beta=2.*std::sin(ps)/(root3*(3.+sign*std::sin(ps)));}
  return {K,G,alpha,kc,beta};
}
struct Case{
  std::string name,category;int fit=-1;float psi_deg=0;A::Material material{};A::State input{};A::Stress expected{};
  double expected_kappa=0,expected_lambda=-1;bool valid=true,regular=false,expect_apex=false,expect_repair=false,boundary=false,expect_negative_work=false;
};
struct Counts{unsigned points=0,rotated=0,invalid=0,general=0,negative_work=0,failures=0;double stress=0,yield=0,kappa=0,volume=0,flow=0,rotation=0,general_stress=0,work=0;std::map<std::string,unsigned> categories,statuses;std::vector<std::string> failed;};
static const char* Status(A::Status s){switch(s){case A::Status::Invalid:return "Invalid";case A::Status::Elastic:return "Elastic";case A::Status::Smooth:return "Smooth";case A::Status::Apex:return "Apex";case A::Status::TensionRepair:return "TensionRepair";default:return "NoAdmissibleFlow";}}
static void Check(bool b,const char* text,std::string& failure){if(!b){if(!failure.empty())failure+=';';failure+=text;}}
struct Record{A::Result result;};
static Record Point(const Case& c,bool rotated,const M& R,const A::Result* base,std::ofstream& out,Counts& stats){
  A::State in=c.input;if(rotated)in.stress=Rotate(in.stress,R);const A::State original=in;const A::Material savedmat=c.material;
  const A::Stress expected=rotated?Rotate(c.expected,R):c.expected;const A::Result r=A::Return(in,c.material);std::string failure;
  const std::string name=c.name+(rotated?"_rot":"");stats.points++;stats.rotated+=unsigned(rotated);stats.categories[c.category]++;stats.statuses[Status(r.status)]++;
  Check(StateBits(in,original)&&MaterialBits(c.material,savedmat),"input_changed",failure);
  double scale=1,stress_error=0,yield_error=0,kappa_error=0,volume_error=0,flow_error=0,rotation_error=0,work_error=0,work=0,subgradient2=0,general_error=0,general_kappa=0,lambda_error=0;bool general_checked=false,general_input_unchanged=true;int general_status=-1;
  if(!c.valid){stats.invalid++;Check(!A::CommitAllowed(r.status)&&StateBits(r.state,original),"failed_state_written",failure);}
  else {
    Check(A::CommitAllowed(r.status),"expected_committable_branch",failure);
    const Inv tr=Independent(in.stress),v=Independent(r.state.stress);scale=std::max({1.,std::abs(tr.I),tr.q,std::abs(c.material.DP_kc)});
    const double stress_budget=5e-10*scale+1e-8,strain_budget=2e-12+2e-10*std::max({std::abs(r.lambda_shear),std::abs(r.lambda_tension),std::abs(c.expected_kappa-double(in.kappa))});
    stress_error=Diff(r.state.stress,expected);yield_error=std::max(0.,v.q+c.material.DP_phi*v.I-c.material.DP_kc);
    Check(stress_error<=stress_budget,"analytic_stress",failure);Check(yield_error<=stress_budget,"yield_admissibility",failure);
    Check(std::isfinite(v.I)&&std::isfinite(v.q)&&std::isfinite(r.kappa_continuous),"nonfinite_committed_state",failure);
    Check(r.state.kappa>=in.kappa&&Bits(r.state.kappa,float(r.kappa_continuous)),"float_history_rounding",failure);
    const double K=c.material.ModulusK,G=c.material.ModulusG;const M trial_dev=Dev(Matrix(in.stress)),new_dev=Dev(Matrix(r.state.stress));M epdev=Minus(trial_dev,new_dev);
    for(int i=0;i<3;i++)for(int j=0;j<3;j++)epdev[i][j]/=2.*G;
    const double dk=std::sqrt(2.*Dot(epdev,epdev)/3.),actual_volume=(tr.I-v.I)/(3.*K);
    kappa_error=std::max(std::abs((r.kappa_continuous-double(in.kappa))-dk),std::abs(r.kappa_continuous-c.expected_kappa));
    Check(kappa_error<=strain_budget,"deviatoric_kappa",failure);
    const double wanted_volume=3.*(c.material.DP_psi*r.lambda_shear+r.lambda_tension);volume_error=std::abs(actual_volume-wanted_volume);
    Check(volume_error<=strain_budget,"volumetric_compliance",failure);Check(r.lambda_shear>=0.&&r.lambda_tension>=0.,"negative_multiplier",failure);
    if(r.status==A::Status::Elastic){Check(StateBits(r.state,in)&&r.lambda_shear==0.&&r.lambda_tension==0.,"elastic_state_or_flow",failure);}
    else {
      M wanted{};
      if(v.q>stress_budget){for(int i=0;i<3;i++)for(int j=0;j<3;j++)wanted[i][j]=r.lambda_shear*new_dev[i][j]/(2.*v.q);flow_error=std::sqrt(Dot(Minus(epdev,wanted),Minus(epdev,wanted)));Check(flow_error<=strain_budget,"smooth_deviatoric_flow",failure);}
      else if(r.lambda_shear>0.){
        subgradient2=Dot(epdev,epdev)/(r.lambda_shear*r.lambda_shear); // Raw ill-conditioned quotient retained as an observation.
        const double S=std::max({1.,std::abs(tr.I)/3.+std::sqrt(2.)*tr.q,std::abs(v.I)/3.+std::sqrt(2.)*v.q});
        const double absolute_roundoff=64.*std::numeric_limits<double>::epsilon()*S/G;
        Check(std::sqrt(Dot(epdev,epdev))<=r.lambda_shear/std::sqrt(2.)+absolute_roundoff,"apex_subgradient_bound",failure);
      }
      else Check(dk<=strain_budget,"zero_shear_multiplier_nonzero_dev",failure);
      Check(std::abs(v.q+c.material.DP_phi*v.I-c.material.DP_kc)<=stress_budget,"plastic_yield_equality",failure);
    }
    if(c.expect_apex)Check(r.status==A::Status::Apex&&!r.repair&&v.q<=stress_budget,"pure_apex_label",failure);
    if(c.expect_repair)Check(r.status==A::Status::TensionRepair&&r.repair&&r.lambda_apex==0.,"explicit_tension_label",failure);
    if(c.boundary)Check((r.status==A::Status::Apex||r.status==A::Status::TensionRepair||r.status==A::Status::Smooth)&&v.q<=stress_budget,"boundary_tip_flow",failure);
    if(r.status==A::Status::TensionRepair){Check(c.material.DP_phi>0.,"repair_without_cone_tip",failure);const double It=c.material.DP_kc/c.material.DP_phi;Check(std::abs(v.I-It)<=stress_budget&&v.q<=stress_budget,"joint_surface_equalities",failure);Check(std::abs(r.lambda_shear-tr.q/G)<=strain_budget,"joint_shear_endpoint",failure);}
    if(c.expected_lambda>=0.){lambda_error=std::abs(r.lambda_shear-c.expected_lambda);Check(lambda_error<=strain_budget,"analytic_lambda",failure);}
    M ep=epdev;for(int i=0;i<3;i++)ep[i][i]+=actual_volume/3.;work=Dot(Matrix(r.state.stress),ep);
    const double invariant_work=v.q*(tr.q-v.q)/G+v.I*(tr.I-v.I)/(9.*K);work_error=std::abs(work-invariant_work);
    Check(work_error<=stress_budget*std::max(1.,std::abs(r.lambda_shear))+strain_budget*scale,"plastic_work_compliance",failure);
    if(work<0.)stats.negative_work++;if(c.expect_negative_work)Check(work<0.&&r.status==A::Status::TensionRepair,"negative_work_witness_hidden",failure);
    if(rotated&&base){rotation_error=Diff(r.state.stress,Rotate(base->state.stress,R));Check(rotation_error<=stress_budget&&std::abs(r.kappa_continuous-base->kappa_continuous)<=strain_budget,"rotation_covariance",failure);}
    // General candidate currently supports the regular smooth branch only.
    if(c.regular){
      general_checked=true;stats.general++;const auto s=Six(in.stress);const B::State gin{{s[0],s[1],s[2],s[3],s[4],s[5]},in.kappa};const B::State old=gin;
      const auto g=B::ConsRelationEP(gin,c.material.ModulusK,c.material.ModulusG,c.material.DP_phi,c.material.DP_kc,c.material.DP_psi);general_status=int(g.status);
      const A::State gs{{g.state.stress.xx,g.state.stress.yy,g.state.stress.zz,g.state.stress.xy,g.state.stress.yz,g.state.stress.xz},g.state.kappa};
      const A::State gi{{gin.stress.xx,gin.stress.yy,gin.stress.zz,gin.stress.xy,gin.stress.yz,gin.stress.xz},gin.kappa},go{{old.stress.xx,old.stress.yy,old.stress.zz,old.stress.xy,old.stress.yz,old.stress.xz},old.kappa};
      general_input_unchanged=StateBits(gi,go);general_error=Diff(gs.stress,r.state.stress);general_kappa=std::abs(g.kappa_continuous-r.kappa_continuous);
      Check(g.status==B::Status::Radial&&general_input_unchanged&&general_error<=stress_budget&&general_kappa<=strain_budget&&Bits(gs.kappa,r.state.kappa),"general_regular_radial_comparison",failure);
    }
    stats.stress=std::max(stats.stress,stress_error);stats.yield=std::max(stats.yield,yield_error);stats.kappa=std::max(stats.kappa,kappa_error);stats.volume=std::max(stats.volume,volume_error);stats.flow=std::max(stats.flow,flow_error);stats.rotation=std::max(stats.rotation,rotation_error);stats.general_stress=std::max(stats.general_stress,general_error);stats.work=std::max(stats.work,work_error);
  }
  if(!failure.empty()){stats.failures++;stats.failed.push_back(name+":"+failure);}
  out<<name<<','<<c.category<<','<<c.fit<<','<<c.psi_deg<<','<<rotated<<','<<c.valid<<','<<Status(r.status)<<','<<unsigned(r.reason)<<','<<r.repair<<','<<r.trial_I<<','<<r.trial_q<<','<<r.returned_I<<','<<r.returned_q<<','<<r.lambda_shear<<','<<r.lambda_apex<<','<<r.lambda_tension<<','<<in.kappa<<','<<r.kappa_continuous<<','<<r.state.kappa<<','<<stress_error<<','<<yield_error<<','<<kappa_error<<','<<volume_error<<','<<flow_error<<','<<subgradient2<<','<<rotation_error<<','<<lambda_error<<','<<work<<','<<work_error<<','<<general_checked<<','<<general_status<<','<<general_error<<','<<general_kappa<<','<<general_input_unchanged<<','<<failure<<'\n';
  return {r};
}
static Case Basic(std::string name,std::string category,const A::Material& m,double Itr,double qtr,double Inew,double qnew,float old=.02f){
  Case c;c.name=name;c.category=category;c.material=m;c.input={Make(Itr,qtr),old};c.expected=Make(Inew,qnew);c.expected_kappa=double(old)+(qtr-qnew)/(std::sqrt(3.)*double(m.ModulusG));return c;
}
static void JsonString(std::ofstream& o,const std::string& s){o<<'"';for(char c:s){if(c=='"'||c=='\\')o<<'\\';o<<c;}o<<'"';}
int main(int argc,char** argv){try{
  Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_DIR");const fs::path out=argv[2];Need(!fs::exists(out)&&fs::create_directory(out),"Fresh output directory required");
  std::ofstream points(out/"points.csv");Need(bool(points),"Cannot write points.csv");points<<std::setprecision(17)<<"name,category,fit,psi_degrees,rotated,input_valid,status,reason,repair,trial_I_Pa,trial_q_Pa,returned_I_Pa,returned_q_Pa,lambda_shear,lambda_apex,lambda_tension,old_kappa,kappa_continuous,saved_float_kappa,stress_max_abs_error_Pa,positive_yield_residual_Pa,kappa_error,volume_flow_error,deviatoric_flow_error,apex_subgradient_norm2,rotation_stress_error_Pa,analytic_lambda_error,endpoint_mechanical_work_Pa,work_compliance_error_Pa,general_compared,general_status,general_stress_error_Pa,general_kappa_error,general_input_unchanged,failure\n";
  const M R=Rotation(),check=Minus(Multiply(R,Transpose(R)),Identity());const double rotation_orthogonality=std::sqrt(Dot(check,check));const double det=R[0][0]*(R[1][1]*R[2][2]-R[1][2]*R[2][1])-R[0][1]*(R[1][0]*R[2][2]-R[1][2]*R[2][0])+R[0][2]*(R[1][0]*R[2][1]-R[1][1]*R[2][0]);Need(rotation_orthogonality<=1e-14&&std::abs(det-1.)<=1e-14,"Rotation must be proper orthogonal");
  std::vector<Case> cases;
  for(int fit=0;fit<3;fit++)for(float psi:{0.f,2.5f,-5.f}){
    const auto m=Parameters(fit,psi);const std::string stem="fit"+std::to_string(fit)+"_psi"+(psi<0?"minus5":psi>0?"plus2p5":"zero");
    const double Inew=-60000.,qnew=m.DP_kc-m.DP_phi*Inew,lambda=.001;auto c=Basic(stem+"_smooth","manufactured_smooth",m,Inew+9.*double(m.ModulusK)*m.DP_psi*lambda,qnew+double(m.ModulusG)*lambda,Inew,qnew);c.fit=fit;c.psi_deg=psi;c.regular=true;c.expected_lambda=lambda;cases.push_back(c);
    const double It=m.DP_kc/m.DP_phi;
    if(psi>0){const double la=.01,qt=.4*double(m.ModulusG)*la;auto a=Basic(stem+"_apex","positive_beta_pure_apex",m,It+9.*double(m.ModulusK)*m.DP_psi*la,qt,It,0.);a.fit=fit;a.psi_deg=psi;a.expect_apex=true;a.expected_lambda=la;cases.push_back(a);}
    else for(int shear=0;shear<2;shear++){const double qt=shear?.003*double(m.ModulusG):0.;auto t=Basic(stem+(shear?"_shear_repair":"_hydro_repair"),"zero_negative_beta_tension",m,It+2000.,qt,It,0.);t.fit=fit;t.psi_deg=psi;t.expect_repair=true;cases.push_back(t);}
  }
  for(double beta:{.125,0.,-.125}){const A::Material m{1.f,1.f,.25,1.,beta};const double It=4.,Itr=beta>0?It+9.*beta:It;auto c=Basic(beta>0?"boundary_positive":beta<0?"boundary_negative":"boundary_zero","tip_boundary",m,Itr,1.,It,0.);c.boundary=true;cases.push_back(c);}
  {const A::Material m{1.f,1.f,0.,1.,0.};auto c=Basic("phi0_shear","phi0_cylinder",m,2.,3.,2.,1.);c.regular=true;c.expected_lambda=2.;cases.push_back(c);auto e=Basic("phi0_hydro_elastic","phi0_cylinder",m,100.,0.,100.,0.);cases.push_back(e);}
  {const A::Material m{1.f,1.f,0.,0.,0.};cases.push_back(Basic("phi0_kc0_shear","phi0_cylinder",m,2.,1.,2.,0.));}
  {const A::Material m{1.f,1.f,.25,0.,.125};auto c=Basic("kc0_positive_apex","zero_strength_tip",m,.01125,.004,0.,0.);c.expect_apex=true;c.expected_lambda=.01;cases.push_back(c);}
  {const A::Material m{1.f,1.f,.25,0.,0.};auto c=Basic("kc0_hydro_repair","zero_strength_tip",m,1.,0.,0.,0.);c.expect_repair=true;cases.push_back(c);}
  {const auto m=Parameters(0,0.f);auto c=Basic("ordinary_elastic","ordinary_elastic",m,-60000.,.25*m.DP_kc,-60000.,.25*m.DP_kc);cases.push_back(c);}
  {const A::Material m{float(25./9.),1.f,.2,1.,-.1};const double f=.25,la=f/(double(m.ModulusG)+9.*double(m.ModulusK)*m.DP_phi*m.DP_psi),qn=1.-la,In=1.25-9.*double(m.ModulusK)*m.DP_psi*la;auto c=Basic("negative_beta_multiple_roots","multiple_root_witness",m,1.25,1.,In,qn);c.regular=true;c.expected_lambda=la;Need(std::abs(la-.5)<2e-6,"Actual float-modulus witness must retain minimal smooth root near0.5");cases.push_back(c);}
  {const A::Material m{10.f,1.f,.2,.1,-.1};auto c=Basic("nonpositive_D_joint","nonpositive_D_negative_work",m,0.,1.,.5,0.);Need(double(m.ModulusG)+9.*double(m.ModulusK)*m.DP_phi*m.DP_psi<=0.,"D<=0 witness malformed");c.expect_repair=true;c.expect_negative_work=true;cases.push_back(c);}
  Counts counts;for(const auto& c:cases){const auto b=Point(c,false,R,nullptr,points,counts);Point(c,true,R,&b.result,points,counts);}
  const auto good=Parameters(0,0.f);for(int which=0;which<5;which++){auto c=Basic("invalid_"+std::to_string(which),"invalid_atomic",good,-60000.,1000.,-60000.,1000.);c.valid=false;
    if(which==0)c.material.ModulusG=0.f;if(which==1)c.material.DP_phi=-1.;if(which==2)c.input.kappa=-.1f;if(which==3)c.input.stress.xy=std::numeric_limits<double>::quiet_NaN();if(which==4)c.material.DP_psi=std::numeric_limits<double>::quiet_NaN();Point(c,false,R,nullptr,points,counts);}
  points.flush();Need(bool(points),"points.csv write failed");const bool coverage=cases.size()==35&&counts.points==75&&counts.rotated==35&&counts.invalid==5&&counts.general==22&&counts.negative_work>=2;const bool passed=coverage&&!counts.failures;
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_material_apex_probe_r2\",\"passed\":"<<(passed?"true":"false")<<",\"point_count\":"<<counts.points<<",\"rotated_points\":"<<counts.rotated<<",\"invalid_atomic_points\":"<<counts.invalid<<",\"general_regular_comparisons\":"<<counts.general<<",\"negative_mechanical_work_observed_points\":"<<counts.negative_work<<",\"failure_count\":"<<counts.failures<<",\"expected_coverage_passed\":"<<(coverage?"true":"false")<<",\"max_stress_error_Pa\":"<<counts.stress<<",\"max_positive_yield_residual_Pa\":"<<counts.yield<<",\"max_continuous_kappa_error\":"<<counts.kappa<<",\"max_volume_flow_error\":"<<counts.volume<<",\"max_deviatoric_flow_error\":"<<counts.flow<<",\"max_rotation_stress_error_Pa\":"<<counts.rotation<<",\"max_general_stress_difference_Pa\":"<<counts.general_stress<<",\"max_work_compliance_error_Pa\":"<<counts.work<<",\"rotation_orthogonality_error\":"<<rotation_orthogonality<<",\"rotation_determinant\":"<<det<<",\"boundary_roundoff_smooth_near_tip_allowed\":true,\"by_category\":{";bool comma=false;for(const auto& e:counts.categories){if(comma)done<<',';JsonString(done,e.first);done<<':'<<e.second;comma=true;}done<<"},\"by_status\":{";comma=false;for(const auto& e:counts.statuses){if(comma)done<<',';JsonString(done,e.first);done<<':'<<e.second;comma=true;}done<<"},\"failed_points\":[";for(unsigned i=0;i<counts.failed.size();i++){if(i)done<<',';JsonString(done,counts.failed[i]);}done<<"],\"general_apex_or_tension_support_claimed\":false,\"softening_or_particle_or_full_collapse_acceptance\":false,\"physical_acceptance\":false,\"solver_invocations\":0}\n";done.flush();Need(bool(done),"Completion write failed");return passed?0:1;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}

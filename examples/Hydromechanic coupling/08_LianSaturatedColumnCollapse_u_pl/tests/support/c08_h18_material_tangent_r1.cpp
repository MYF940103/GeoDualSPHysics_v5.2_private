// Standalone frozen-material diagnostic. No JSph, native reader or time step.
#include "FunSoilMaterial.h"
#include <array>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace fs=std::filesystem;
using V6=std::array<double,6>;
using M6=std::array<V6,6>;
constexpr unsigned First=2060,Count=5000;
const double Width=.000005;
void Need(bool ok,const std::string& text){if(!ok)throw std::runtime_error(text);}
template<class T> bool Bits(T a,T b){return std::memcmp(&a,&b,sizeof(T))==0;}
std::vector<std::string> Split(const std::string& line){std::vector<std::string> v;size_t a=0;for(;;){auto b=line.find(',',a);v.push_back(line.substr(a,b==std::string::npos?b:b-a));if(b==std::string::npos)return v;a=b+1;}}
struct Csv{
  std::ifstream file;std::map<std::string,size_t> keys;std::vector<std::string> row;unsigned rows=0;
  explicit Csv(const fs::path& path):file(path){Need(bool(file),"Missing CSV: "+path.string());std::string s;Need(bool(std::getline(file,s)),"Missing CSV header");if(!s.empty()&&s.back()=='\r')s.pop_back();auto h=Split(s);for(size_t i=0;i<h.size();i++)Need(keys.emplace(h[i],i).second,"Duplicate CSV column");}
  bool Next(){std::string s;if(!std::getline(file,s)){Need(file.eof(),"CSV read error");return false;}if(!s.empty()&&s.back()=='\r')s.pop_back();row=Split(s);Need(row.size()==keys.size(),"CSV row width differs");rows++;return true;}
  const std::string& Text(const char* key)const{auto q=keys.find(key);Need(q!=keys.end(),std::string("Missing column ")+key);return row[q->second];}
  double D(const char* key)const{const auto& s=Text(key);size_t end=0;double v=std::stod(s,&end);Need(end==s.size()&&std::isfinite(v),std::string("Invalid finite value ")+key);return v;}
  unsigned U(const char* key)const{double v=D(key);Need(v>=0&&v<=4294967295.&&v==std::floor(v),"Invalid unsigned value");return unsigned(v);}
  float F(const char* key)const{double v=D(key);float f=float(v);Need(Bits(double(f),v),std::string("CSV value not exact original float: ")+key);return f;}
};
const char* Sig[6]={"sigma_xx","sigma_yy","sigma_zz","sigma_xy","sigma_yz","sigma_xz"};
const char* Rate[6]={"Rsigma_xx","Rsigma_yy","Rsigma_zz","Rsigma_xy","Rsigma_yz","Rsigma_xz"};
const char* Names[6]={"xx","yy","zz","xy","yz","xz"};
const char* Eps[6]={"exx","eyy","ezz","gamma_xy","gamma_yz","gamma_xz"};
V6 Vector(const fsoil::Stress& s){return {{s.xx,s.yy,s.zz,s.xy,s.yz,s.xz}};}
fsoil::Stress Stress(const V6& a){return {a[0],a[1],a[2],a[3],a[4],a[5]};}
tsymatrix3d Sym(const V6& a){tsymatrix3d s{};s.xx=a[0];s.yy=a[1];s.zz=a[2];s.xy=a[3];s.yz=a[4];s.xz=a[5];return s;}
V6 Vector(const tsymatrix3d& s){return {{s.xx,s.yy,s.zz,s.xy,s.yz,s.xz}};}
bool Same(const V6& a,const V6& b){for(unsigned j=0;j<6;j++)if(!Bits(a[j],b[j]))return false;return true;}
struct Snapshot{V6 sigma{},rate{};float kappa=0;double time=0;unsigned step=0;bool seen=false;};
struct Shadow{unsigned status=0,reason=0;float old=0,saved=0;double continuous=0,I=0,q=0;bool trigger=false,seen=false;};
struct Point{unsigned part,id;double time;V6 trial;float old;bool trigger;fsoil::Result actual;};
StSoilCte Parameters(){StSoilCte c{};c.ModulusE=20e6f;c.PRvs=.33f;c.ModulusK=float(c.ModulusE/(3.f*(1.f-2.f*c.PRvs)));c.ModulusG=float(c.ModulusE/(2.f*(1.f+c.PRvs)));c.phi=float(TORAD*25.f);c.phi_r=c.phi;c.n_phi=0.f;c.coh=5000.f;c.coh_r=1000.f;c.n_coh=5.f;c.dlt=0.f;c.psiDecay=0.f;c.SoilTriggerFos=1.65f;Need(c.ModulusK==19607844.f&&c.ModulusG==7518796.5f,"Frozen original float moduli differ");return c;}
fsoil::Result Evaluate(const V6& trial,float old,bool trigger,const StSoilCte& c,bool frozen){
  const fsoil::State input={Stress(trial),old};
  if(!frozen)return fsoil::EvaluateMaterial(input,c,DP_PS,true,trigger);
  const float coh=(trigger&&(c.n_phi>0.f||c.n_coh>0.f)?c.coh/c.SoilTriggerFos:c.coh);
  const fsoil::Material m={c.ModulusK,c.ModulusG,c.phi,c.phi_r,c.n_phi,coh,c.coh_r,c.n_coh,c.dlt,c.psiDecay};
  const auto d=fsoil::UpdateDPvars(m,old,DP_PS);
  // Freeze complete double coefficients at kappa_n; do not round an equivalent c.
  return fsoil::ConsRelationEP(input,c.ModulusK,c.ModulusG,d.DP_phi,d.DP_kc,d.DP_psi);
}
std::vector<Point> Baseline(unsigned part,const fs::path& dir,const StSoilCte& c){
  std::array<std::vector<Snapshot>,3> s;for(auto& v:s)v.resize(Count);
  Csv stages(dir/"stages.csv");while(stages.Next()){
    const auto& name=stages.Text("stage");int which=name=="restored_n"?0:name=="force_h"?1:name=="raw_full"?2:-1;
    unsigned id=stages.U("native_id");Need(id>=First&&id<First+Count,"Stage soil ID domain differs");if(which<0)continue;
    auto& a=s[which][id-First];Need(!a.seen,"Duplicate selected stage/ID");a.seen=true;a.time=stages.D("solver_time_s");a.step=stages.U("solver_completed_step");a.kappa=stages.F("kappa");
    for(unsigned j=0;j<6;j++){a.sigma[j]=stages.D(Sig[j]);if(which==1)a.rate[j]=stages.F(Rate[j]);}
  }Need(stages.rows==35000,"Exactly seven5000-ID original stages required");for(const auto& v:s)for(const auto& q:v)Need(q.seen,"Incomplete selected stage");
  std::vector<Shadow> sh(Count);Csv shadow(dir/"material_shadow.csv");while(shadow.Next()){
    if(shadow.Text("stage")!="full")continue;unsigned id=shadow.U("native_id");Need(id>=First&&id<First+Count,"Shadow ID differs");auto& q=sh[id-First];Need(!q.seen,"Duplicate full shadow");q.seen=true;q.status=shadow.U("shadow_status");q.reason=shadow.U("shadow_reason");q.old=shadow.F("kappa_n");q.saved=shadow.F("shadow_kappa");Need(Bits(q.saved,shadow.F("actual_saved_kappa")),"Original full saved kappa differs");q.continuous=shadow.D("kappa_continuous");q.I=shadow.D("I_trial");q.q=shadow.D("q_trial");q.trigger=shadow.U("trigger")!=0;
    Need(Bits(shadow.D("stage_width_s"),Width)&&shadow.D("K_Pa")==c.ModulusK&&shadow.D("G_Pa")==c.ModulusG,"Original full width/moduli differ");
    Need(shadow.U("source_completed_step")==unsigned(part==38?2076001:2152001),"Wrong source completed step");
  }Need(shadow.rows==10000,"Exactly10000 original half/full shadow rows required");
  std::map<std::pair<unsigned,unsigned>,unsigned> first;std::set<unsigned> ids={4953,4954,6767,6865};std::vector<Point> all;all.reserve(Count);
  for(unsigned k=0;k<Count;k++){
    const auto& n=s[0][k];const auto& f=s[1][k];const auto& raw=s[2][k];const auto& q=sh[k];Need(q.seen&&!q.trigger,"Original untriggered full shadow required");
    Need(n.step==unsigned(part==38?2076001:2152001)&&f.step==n.step&&raw.step==n.step&&Bits(f.time,n.time)&&Bits(raw.time,n.time),"Original inner-step clocks/steps differ");
    Need(Bits(n.kappa,q.old)&&Bits(raw.kappa,q.saved),"Original kappa base differs");V6 trial{};for(unsigned j=0;j<6;j++)trial[j]=n.sigma[j]+float(f.rate[j])*Width;
    auto r=Evaluate(trial,n.kappa,q.trigger,c,false);Need(fsoil::CommitAllowed(r.status)&&unsigned(r.status)==q.status&&unsigned(r.reason)==q.reason,"Original baseline material classification differs");
    Need(Same(Vector(r.state.stress),raw.sigma)&&Bits(r.state.kappa,raw.kappa)&&Bits(r.kappa_continuous,q.continuous)&&Bits(r.trial_I,q.I)&&Bits(r.trial_q,q.q),"Original baseline six-stress/kappa/invariants bits differ");
    tsymatrix3d returned{};float saved=-1;auto status=fsoil::ReturnMaterial(Sym(trial),n.kappa,c,DP_PS,true,q.trigger,returned,saved);
    Need(status==r.status&&Same(Vector(returned),raw.sigma)&&Bits(saved,raw.kappa),"Original named ReturnMaterial adapter bits differ");
    first.emplace(std::make_pair(q.status,q.reason),k+First);all.push_back({part,k+First,n.time,trial,n.kappa,q.trigger,r});
  }
  Need(first.size()==3&&first.at({1,1})==2060&&first.at({2,3})==unsigned(part==38?2455:2089)&&first.at({4,6})==unsigned(part==38?4656:2103),"Predeclared original class representatives differ");
  for(const auto& q:first)ids.insert(q.second);Need(ids.size()==7,"Seven predeclared material points required");std::vector<Point> result;for(unsigned id:ids)result.push_back(all[id-First]);return result;
}
V6 Elastic(const V6& e,const StSoilCte& c){const double K=c.ModulusK,G=c.ModulusG,tr=e[0]+e[1]+e[2],lam=K-2.*G/3.;return {{lam*tr+2.*G*e[0],lam*tr+2.*G*e[1],lam*tr+2.*G*e[2],G*e[3],G*e[4],G*e[5]}};}
struct Acoustic{double xx,xz,zx,zz,min,max,asym;};
Acoustic Q(const M6& C,double angle){double nx=std::cos(angle),nz=std::sin(angle);V6 ex={{nx,0,0,0,0,nz}},ez={{0,0,nz,0,0,nx}},sx{},sz{};for(unsigned i=0;i<6;i++)for(unsigned j=0;j<6;j++){sx[i]+=C[i][j]*ex[j];sz[i]+=C[i][j]*ez[j];}Acoustic q{};q.xx=sx[0]*nx+sx[5]*nz;q.zx=sx[5]*nx+sx[2]*nz;q.xz=sz[0]*nx+sz[5]*nz;q.zz=sz[5]*nx+sz[2]*nz;double b=.5*(q.xz+q.zx),d=std::hypot(q.xx-q.zz,2.*b);q.min=.5*(q.xx+q.zz-d);q.max=.5*(q.xx+q.zz+d);q.asym=std::fabs(q.xz-q.zx);return q;}
int main(int argc,char** argv){try{
  Need(argc==6&&std::string(argv[1])=="--review"&&std::string(argv[5])=="--execution-authorized","Use --review STEP38DIR STEP76DIR FRESHOUT --execution-authorized; no solver action");
  fs::path output=argv[4];Need(!fs::exists(output),"Existing complete/partial output protected");auto c=Parameters();auto points=Baseline(38,argv[2],c);auto p76=Baseline(76,argv[3],c);points.insert(points.end(),p76.begin(),p76.end());Need(points.size()==14,"Fourteen points required");fs::create_directories(output);
  std::ofstream point(output/"points.csv"),tangent(output/"tangents.csv"),branches(output/"branches.csv"),acoustic(output/"acoustic.csv"),summary(output/"summary.csv");for(auto f:{&point,&tangent,&branches,&acoustic,&summary}){Need(bool(*f),"Fresh output unavailable");*f<<std::setprecision(17);}
  point<<"part,native_id,source_time_s,kappa_n,actual_status,actual_reason,kappa_continuous,kappa_saved,trial_xx,trial_yy,trial_zz,trial_xy,trial_yz,trial_xz,returned_xx,returned_yy,returned_zz,returned_xy,returned_yz,returned_xz,lambda_shear,lambda_apex,lambda_tension\n";
  tangent<<"part,native_id,law,strain_scale,stress_component,engineering_strain_component,C_Pa,available,all_12_perturbations_same_branch\n";
  branches<<"part,native_id,law,strain_scale,engineering_strain_component,base_status,base_reason,plus_status,plus_reason,minus_status,minus_reason,both_commit,same_branch,kappa_plus,kappa_minus,kappa_continuous_plus,kappa_continuous_minus,central_nonlinearity_stress_norm_Pa,stress_perturbation_max_Pa\n";
  acoustic<<"part,native_id,law,strain_scale,angle_deg,Qxx_Pa,Qxz_Pa,Qzx_Pa,Qzz_Pa,symmetric_min_Pa,symmetric_max_Pa,abs_Qxz_minus_Qzx_Pa,elastic_min_Pa,elastic_max_Pa,available,all_12_perturbations_same_branch\n";
  summary<<"part,native_id,law,strain_scale,base_status,base_reason,available,all_12_perturbations_same_branch,minimum_symmetric_acoustic_Pa,minimum_angle_deg,maximum_abs_Qxz_minus_Qzx_Pa,C_Frobenius_Pa,engineering_C_asymmetry_Frobenius_Pa,elastic_shear_modulus_Pa,elastic_longitudinal_modulus_Pa\n";
  M6 Ce{};for(unsigned j=0;j<6;j++){V6 e{};e[j]=1;auto s=Elastic(e,c);for(unsigned i=0;i<6;i++)Ce[i][j]=s[i];}
  unsigned branchRows=0,tangentRows=0,acousticRows=0,summaryRows=0;const double nan=std::numeric_limits<double>::quiet_NaN();
  for(const auto& p:points){point<<p.part<<','<<p.id<<','<<p.time<<','<<p.old<<','<<unsigned(p.actual.status)<<','<<unsigned(p.actual.reason)<<','<<p.actual.kappa_continuous<<','<<p.actual.state.kappa;for(double x:p.trial)point<<','<<x;for(double x:Vector(p.actual.state.stress))point<<','<<x;point<<','<<p.actual.lambda_shear<<','<<p.actual.lambda_apex<<','<<p.actual.lambda_tension<<'\n';
    for(unsigned mode=0;mode<2;mode++){const char* law=mode?"frozen_strength_at_kappa_n":"original_softening";auto base=Evaluate(p.trial,p.old,p.trigger,c,mode!=0);const auto bv=Vector(base.state.stress);
      for(int power=5;power<=11;power++){const double h=std::pow(10.,-power);M6 C{};bool available=fsoil::CommitAllowed(base.status),same=available;
        for(unsigned j=0;j<6;j++){V6 eps{};eps[j]=h;auto ds=Elastic(eps,c);V6 plus=p.trial,minus=p.trial;double mx=0;for(unsigned i=0;i<6;i++){plus[i]+=ds[i];minus[i]-=ds[i];mx=(std::max)(mx,std::fabs(ds[i]));}auto a=Evaluate(plus,p.old,p.trigger,c,mode!=0),b=Evaluate(minus,p.old,p.trigger,c,mode!=0);bool ok=fsoil::CommitAllowed(a.status)&&fsoil::CommitAllowed(b.status),one=ok&&a.status==base.status&&b.status==base.status&&a.reason==base.reason&&b.reason==base.reason;available=available&&ok;same=same&&one;auto av=Vector(a.state.stress),zv=Vector(b.state.stress);double nonlinear=0;for(unsigned i=0;i<6;i++){C[i][j]=ok?(av[i]-zv[i])/(2.*h):nan;double d=(av[i]-bv[i])+(zv[i]-bv[i]);nonlinear+=d*d;}branches<<p.part<<','<<p.id<<','<<law<<','<<h<<','<<Eps[j]<<','<<unsigned(base.status)<<','<<unsigned(base.reason)<<','<<unsigned(a.status)<<','<<unsigned(a.reason)<<','<<unsigned(b.status)<<','<<unsigned(b.reason)<<','<<ok<<','<<one<<','<<a.state.kappa<<','<<b.state.kappa<<','<<a.kappa_continuous<<','<<b.kappa_continuous<<','<<(ok?std::sqrt(nonlinear):nan)<<','<<mx<<'\n';branchRows++;}
        for(unsigned i=0;i<6;i++)for(unsigned j=0;j<6;j++){tangent<<p.part<<','<<p.id<<','<<law<<','<<h<<','<<Names[i]<<','<<Eps[j]<<','<<C[i][j]<<','<<available<<','<<same<<'\n';tangentRows++;}
        double minimum=std::numeric_limits<double>::infinity(),minimumAngle=nan,maxAsym=0,norm=0,asym=0;for(unsigned i=0;i<6;i++)for(unsigned j=0;j<6;j++){norm+=C[i][j]*C[i][j];double d=C[i][j]-C[j][i];asym+=d*d;}
        for(unsigned deg=0;deg<=180;deg++){auto q=Q(C,PI*double(deg)/180.),elastic=Q(Ce,PI*double(deg)/180.);if(available&&q.min<minimum){minimum=q.min;minimumAngle=deg;}if(available)maxAsym=(std::max)(maxAsym,q.asym);acoustic<<p.part<<','<<p.id<<','<<law<<','<<h<<','<<deg<<','<<q.xx<<','<<q.xz<<','<<q.zx<<','<<q.zz<<','<<q.min<<','<<q.max<<','<<q.asym<<','<<elastic.min<<','<<elastic.max<<','<<available<<','<<same<<'\n';acousticRows++;}
        summary<<p.part<<','<<p.id<<','<<law<<','<<h<<','<<unsigned(base.status)<<','<<unsigned(base.reason)<<','<<available<<','<<same<<','<<(available?minimum:nan)<<','<<minimumAngle<<','<<(available?maxAsym:nan)<<','<<std::sqrt(norm)<<','<<std::sqrt(asym)<<','<<c.ModulusG<<','<<double(c.ModulusK)+4.*double(c.ModulusG)/3.<<'\n';summaryRows++;
      }
    }
  }
  Need(branchRows==1176&&tangentRows==7056&&acousticRows==35476&&summaryRows==196,"Exact diagnostic coverage differs");for(auto f:{&point,&tangent,&branches,&acoustic,&summary}){f->flush();Need(bool(*f),"Output write failed");}
  std::ofstream done(output/"completion.json");done<<"{\"stage\":\"c08_h18_material_tangent_r1\",\"passed\":true,\"parts\":[38,76],\"baseline_full_rows\":10000,\"baseline_all6_sigma_kappa_bits_matched\":true,\"trial_reconstructed_from_original_stages\":true,\"selected_points\":14,\"branch_rows\":"<<branchRows<<",\"tangent_rows\":"<<tangentRows<<",\"acoustic_rows\":"<<acousticRows<<",\"summary_rows\":"<<summaryRows<<",\"physical_steps\":0,\"force_calls\":0,\"native_reads\":0,\"original_law_unchanged\":true,\"local_frozen_strength_is_not_a_physical_case\":true,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");std::cout<<"Standalone material baseline/tangent diagnostic complete; no physical steps.\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

// Three exact C08 material groups: production entry versus independent manufactured endpoints.
// Oracle formulas/budgets derive from upl_material_unified_probe_r1.cpp lines60-80,104-138,176-198.
// No archived candidate material solver, spatial engine object, GPU or HG producer is invoked.
#include "FunSoilMaterial.h"
#include <array>
#include <cmath>
#include <cstdint>
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
namespace fs=std::filesystem;
using Stress=fsoil::Stress;using State=fsoil::State;using Status=fsoil::Status;
using M=std::array<std::array<double,3>,3>;
static void Need(bool b,const std::string& s){if(!b)throw std::runtime_error(s);}
template<class T>static bool Bits(T a,T b){return !std::memcmp(&a,&b,sizeof(T));}
static std::array<double,6> Six(const Stress& s){return {s.xx,s.yy,s.zz,s.xy,s.yz,s.xz};}
static bool Same(const State& a,const State& b){const auto x=Six(a.stress),y=Six(b.stress);for(unsigned i=0;i<6;i++)if(!Bits(x[i],y[i]))return false;return Bits(a.kappa,b.kappa);}
static M Matrix(const Stress& s){return {{{s.xx,s.xy,s.xz},{s.xy,s.yy,s.yz},{s.xz,s.yz,s.zz}}};}
static M Minus(const M& a,const M& b){M c{};for(int i=0;i<3;i++)for(int j=0;j<3;j++)c[i][j]=a[i][j]-b[i][j];return c;}
static double Dot(const M& a,const M& b){double x=0;for(int i=0;i<3;i++)for(int j=0;j<3;j++)x+=a[i][j]*b[i][j];return x;}
static double Trace(const M& a){return a[0][0]+a[1][1]+a[2][2];}
static M Dev(const M& a){M b=a;const double mean=Trace(a)/3.;for(int i=0;i<3;i++)b[i][i]-=mean;return b;}
struct Inv{double I,q;};
static Inv Independent(const Stress& s){const M a=Matrix(s),d=Dev(a);return {Trace(a),std::sqrt(.5*Dot(d,d))};}
static Stress Make(double I,double q){const double m=I/3.;return {m+q,m-q,m,0,0,0};}
static double Diff(const Stress& a,const Stress& b){const auto x=Six(a),y=Six(b);double e=0;for(unsigned i=0;i<6;i++)e=(std::max)(e,std::abs(x[i]-y[i]));return e;}
static std::array<float,12> Fields(const StSoilCte& c){return {c.ModulusE,c.PRvs,c.ModulusK,c.ModulusG,c.phi,c.phi_r,c.n_phi,c.coh,c.coh_r,c.n_coh,c.dlt,c.psiDecay};}
struct Group{const char* name;float cp,psi,sf;};
static constexpr Group Groups[]={{"psi0",5000,0,0},{"psi2p5",5000,2.5f,.2f},{"psim5",7500,-5,.2f}};
static float Radians(float d){return float(TORAD*d);}
static uint32_t FloatBits(float x){uint32_t u;static_assert(sizeof(u)==sizeof(x),"Expected binary32 float");std::memcpy(&u,&x,sizeof(u));return u;}
static StSoilCte Parameters(const Group& g){
  StSoilCte c{};c.ModulusE=20e6f;c.PRvs=.33f;
  // Preserve the actual C08 original float modulus evaluation, not double-rounded material constants.
  c.ModulusK=float(c.ModulusE/(3.f*(1.f-2.f*c.PRvs)));c.ModulusG=float(c.ModulusE/(2.f*(1.f+c.PRvs)));
  c.phi=c.phi_r=Radians(25);c.n_phi=0;c.coh=g.cp;c.coh_r=1000;c.n_coh=5;
  c.dlt=Radians(g.psi);c.psiDecay=g.sf;c.SoilTriggerFos=1.65f;
  const uint32_t expectedPsi=g.psi<0?0xbdb2b8c2u:g.psi>0?0x3d32b8c2u:0u;
  Need(FloatBits(c.phi)==0x3edf66f3u&&FloatBits(c.phi_r)==0x3edf66f3u&&FloatBits(c.dlt)==expectedPsi,"Actual production TORAD float angle bits differ");
  Need(c.ModulusK==19607844.f&&c.ModulusG==7518796.5f,"Original float C08 moduli differ");return c;
}
struct DP{double DP_phi,DP_kc,DP_psi;};
static DP IndependentCoefficients(const StSoilCte& c,double kappa,bool trigger){
  // Independent published exponential laws and plane-strain coefficients; never call UpdateDPvars.
  const float cp=trigger?c.coh/c.SoilTriggerFos:c.coh;
  const double phi=double(c.phi_r)+(double(c.phi)-c.phi_r)*std::exp(-double(c.n_phi)*kappa);
  const double coh=double(c.coh_r)+(double(cp)-c.coh_r)*std::exp(-double(c.n_coh)*kappa);
  const double psi=double(c.dlt)*std::exp(-double(c.psiDecay)*kappa),a=std::tan(phi),b=std::tan(psi);
  return {a/std::sqrt(9.+12.*a*a),3.*coh/std::sqrt(9.+12.*a*a),b/std::sqrt(9.+12.*b*b)};
}
static const char* Name(Status s){switch(s){case Status::Elastic:return "Elastic";case Status::Smooth:return "Smooth";case Status::Apex:return "Apex";case Status::TensionRepair:return "TensionRepair";case Status::Invalid:return "Invalid";case Status::NonConverged:return "NonConverged";case Status::UnresolvedPath:return "UnresolvedPath";default:return "NoAdmissibleFlow";}}
struct Case{Group group;StSoilCte c;bool trigger;std::string kind;State input;Stress expected;double kappa,lambda;Status status;};
static std::vector<Case> Cases(){std::vector<Case> v;
  for(const auto& g:Groups)for(bool trigger:{false,true}){
    const auto c=Parameters(g);const float old=.02f;const auto d0=IndependentCoefficients(c,old,trigger);
    v.push_back({g,c,trigger,"elastic",{Make(-60000.,.25*d0.DP_kc),old},Make(-60000.,.25*d0.DP_kc),double(old),0,Status::Elastic});
    const double lambda=.001,k=double(old)+lambda/std::sqrt(3.);const auto d=IndependentCoefficients(c,k,trigger);
    const double I=-60000.,q=d.DP_kc-d.DP_phi*I;
    v.push_back({g,c,trigger,"smooth",{Make(I+9.*double(c.ModulusK)*d.DP_psi*lambda,q+double(c.ModulusG)*lambda),old},Make(I,q),k,lambda,Status::Smooth});
    const double qt=.003*double(c.ModulusG),kt=double(old)+.003/std::sqrt(3.);const auto tip=IndependentCoefficients(c,kt,trigger);
    const double It=tip.DP_kc/tip.DP_phi,lt=g.psi>0?.01:.003,Itr=g.psi>0?It+9.*double(c.ModulusK)*tip.DP_psi*lt:It+2000.;
    v.push_back({g,c,trigger,g.psi>0?"positive_apex":"joint_tension_repair",{Make(Itr,qt),old},Make(It,0),kt,lt,g.psi>0?Status::Apex:Status::TensionRepair});
  }
  for(const auto& g:Groups){auto c=Parameters(g);c.ModulusG=0;const State in={Make(-60000.,1000.),.02f};v.push_back({g,c,false,"invalid_positive_E_G0",in,in.stress,double(in.kappa),0,Status::Invalid});}
  Need(v.size()==21,"Closed21-point coverage changed");return v;
}
static void Put(std::ostream& o,const Stress& s){for(double x:Six(s))o<<','<<x;}
int main(int argc,char** argv){try{
  Need(argc==3&&std::string(argv[1])=="--out","Use --out FRESH_DIR");const fs::path out=argv[2];Need(!fs::exists(out)&&fs::create_directory(out),"Fresh output directory required");
  std::ofstream csv(out/"points.csv");Need(bool(csv),"Cannot write points");csv<<std::setprecision(17);
  csv<<"group,kind,trigger,cp_input_Pa,cp_effective_float_Pa,cr_Pa,nc,psi_input_deg,sf,FOS,K_Pa,G_Pa,expected_status,actual_status,old_kappa,continuous_kappa,saved_float_kappa,expected_kappa,lambda_shear,lambda_tension,stress_error_Pa,positive_yield_error_Pa,kappa_error,volume_error,deviatoric_flow_error,stress_budget_Pa,strain_budget,input_unchanged,invalid_adapter_sentinel_unchanged";
  for(const char* prefix:{"trial","expected","actual"})for(const char* key:{"xx","yy","zz","xy","yz","xz"})csv<<','<<prefix<<'_'<<key<<"_Pa";csv<<'\n';
  std::map<std::string,unsigned> counts;unsigned points=0,invalidAdapter=0,triggerSmooth=0;double maxStress=0,maxYield=0,maxKappa=0,maxVolume=0,maxFlow=0;
  for(const auto& c:Cases()){
    const State original=c.input;const auto before=Fields(c.c);const float originalFos=c.c.SoilTriggerFos;
    const auto r=fsoil::EvaluateMaterial(c.input,c.c,DP_PS,true,c.trigger);
    bool unchanged=Same(c.input,original)&&Bits(c.c.SoilTriggerFos,originalFos);const auto after=Fields(c.c);for(unsigned j=0;j<before.size();j++)unchanged=unchanged&&Bits(before[j],after[j]);
    Need(unchanged&&r.status==c.status,std::string(c.group.name)+"/"+c.kind+": input or actual branch changed");
    double stressError=0,yieldError=0,kappaError=0,volumeError=0,flowError=0,stressBudget=0,strainBudget=0;bool sentinel=true;
    if(c.status==Status::Invalid){
      Need(!fsoil::CommitAllowed(r.status)&&Same(r.state,original),"Invalid state committed");
      tsymatrix3d trial=TSymMatrix3d(original.stress.xx,original.stress.xy,original.stress.xz,original.stress.yy,original.stress.yz,original.stress.zz);
      tsymatrix3d corrected=TSymMatrix3d(101.,102.,103.,104.,105.,106.);const auto saved=corrected;float k=.375f;
      const auto status=fsoil::ReturnMaterial(trial,original.kappa,c.c,DP_PS,true,c.trigger,corrected,k);
      sentinel=status==Status::Invalid&&Bits(k,.375f)&&Bits(corrected.xx,saved.xx)&&Bits(corrected.yy,saved.yy)&&Bits(corrected.zz,saved.zz)&&Bits(corrected.xy,saved.xy)&&Bits(corrected.yz,saved.yz)&&Bits(corrected.xz,saved.xz);
      Need(sentinel,"Invalid named adapter wrote sentinel");invalidAdapter++;
    }else{
      Need(fsoil::CommitAllowed(r.status),"Expected committable state rejected");const Inv tr=Independent(c.input.stress),v=Independent(r.state.stress);const auto d=IndependentCoefficients(c.c,r.kappa_continuous,c.trigger);
      const double scale=(std::max)({1.,std::abs(tr.I),tr.q,std::abs(d.DP_kc)});
      // Original unified-probe tolerances, without expansion for these material groups.
      stressBudget=5e-10*scale+1e-8;strainBudget=2e-12+2e-10*(std::max)({std::abs(r.lambda_shear),std::abs(r.lambda_tension),std::abs(c.kappa-double(c.input.kappa))});
      stressError=Diff(r.state.stress,c.expected);yieldError=(std::max)(0.,v.q+d.DP_phi*v.I-d.DP_kc);
      Need(stressError<=stressBudget&&yieldError<=stressBudget,"Independent manufactured endpoint/yield error");
      Need(r.state.kappa>=c.input.kappa&&Bits(r.state.kappa,float(r.kappa_continuous)),"Original float history rounding/monotonicity failed");
      const double K=c.c.ModulusK,G=c.c.ModulusG;const M trialDev=Dev(Matrix(c.input.stress)),newDev=Dev(Matrix(r.state.stress));M epdev=Minus(trialDev,newDev);
      for(unsigned a=0;a<3;a++)for(unsigned b=0;b<3;b++)epdev[a][b]/=2.*G;
      const double dk=std::sqrt(2.*Dot(epdev,epdev)/3.),actualVolume=(tr.I-v.I)/(3.*K);
      kappaError=(std::max)(std::abs(r.kappa_continuous-double(c.input.kappa)-dk),std::abs(r.kappa_continuous-c.kappa));
      volumeError=std::abs(actualVolume-3.*(d.DP_psi*r.lambda_shear+r.lambda_tension));
      Need(kappaError<=strainBudget&&volumeError<=strainBudget&&r.lambda_shear>=0&&r.lambda_tension>=0,"Independent history/volume-flow contract failed");
      if(c.status==Status::Elastic)Need(Same(r.state,c.input)&&r.lambda_shear==0&&r.lambda_tension==0,"Elastic flow changed");
      else{
        Need(std::abs(v.q+d.DP_phi*v.I-d.DP_kc)<=stressBudget&&std::abs(r.lambda_shear-c.lambda)<=strainBudget,"Plastic yield/known multiplier failed");
        if(v.q>stressBudget){M wanted{};for(unsigned a=0;a<3;a++)for(unsigned b=0;b<3;b++)wanted[a][b]=r.lambda_shear*newDev[a][b]/(2.*v.q);const auto gap=Minus(epdev,wanted);flowError=std::sqrt(Dot(gap,gap));Need(flowError<=strainBudget,"Independent smooth deviatoric flow failed");}
        else{
          const double S=(std::max)({1.,std::abs(tr.I)/3.+std::sqrt(2.)*tr.q,std::abs(v.I)/3.+std::sqrt(2.)*v.q});
          const double roundoff=64.*std::numeric_limits<double>::epsilon()*S/G;
          Need(std::sqrt(Dot(epdev,epdev))<=r.lambda_shear/std::sqrt(2.)+roundoff,"Original apex subgradient bound failed");
        }
        if(c.status==Status::Apex)Need(!r.repair&&v.q<=stressBudget,"Positive-psi apex mislabelled");
        if(c.status==Status::TensionRepair)Need(r.repair&&r.lambda_apex==0&&std::abs(r.lambda_shear-tr.q/G)<=strainBudget,"Joint tension-repair history failed");
        if(c.trigger&&c.status==Status::Smooth)triggerSmooth++;
      }
      maxStress=(std::max)(maxStress,stressError);maxYield=(std::max)(maxYield,yieldError);maxKappa=(std::max)(maxKappa,kappaError);maxVolume=(std::max)(maxVolume,volumeError);maxFlow=(std::max)(maxFlow,flowError);
    }
    points++;counts[Name(r.status)]++;csv<<c.group.name<<','<<c.kind<<','<<c.trigger<<','<<c.c.coh<<','<<(c.trigger?c.c.coh/c.c.SoilTriggerFos:c.c.coh)<<','<<c.c.coh_r<<','<<c.c.n_coh<<','<<c.group.psi<<','<<c.c.psiDecay<<','<<c.c.SoilTriggerFos<<','<<c.c.ModulusK<<','<<c.c.ModulusG<<','<<Name(c.status)<<','<<Name(r.status)<<','<<c.input.kappa<<','<<r.kappa_continuous<<','<<r.state.kappa<<','<<c.kappa<<','<<r.lambda_shear<<','<<r.lambda_tension<<','<<stressError<<','<<yieldError<<','<<kappaError<<','<<volumeError<<','<<flowError<<','<<stressBudget<<','<<strainBudget<<','<<unchanged<<','<<sentinel;Put(csv,c.input.stress);Put(csv,c.expected);Put(csv,r.state.stress);csv<<'\n';
  }
  Need(points==21&&counts["Elastic"]==6&&counts["Smooth"]==6&&counts["Apex"]==2&&counts["TensionRepair"]==4&&counts["Invalid"]==3&&invalidAdapter==3&&triggerSmooth==3,"Closed nonvacuous coverage failed");
  csv.flush();Need(bool(csv),"Points CSV write failed");std::ofstream done(out/"completion.json");done<<std::setprecision(17)
    <<"{\"stage\":\"c08_h18_hg_material_groups_probe_r1\",\"passed\":true,\"points\":21,\"groups\":3,\"trigger_values_per_group\":2,\"Elastic\":6,\"Smooth\":6,\"Apex\":2,\"TensionRepair\":4,\"Invalid\":3,\"EvaluateMaterial_calls\":21,\"invalid_ReturnMaterial_calls\":3,\"invalid_noncommit_sentinels\":3,\"trigger_ON_smooth_points\":3,\"max_stress_error_Pa\":"<<maxStress<<",\"max_positive_yield_error_Pa\":"<<maxYield<<",\"max_kappa_error\":"<<maxKappa<<",\"max_volume_flow_error\":"<<maxVolume<<",\"max_deviatoric_flow_error\":"<<maxFlow
    <<",\"independent_manufactured_oracle\":true,\"original_tolerances_unchanged\":true,\"parameters_and_persistent_history_float\":true,\"frozen_candidate_material_calls\":0,\"engine_objects\":0,\"GPU_calls\":0,\"HGproducer_calls\":0,\"spatial_solver_calls\":0,\"physical_acceptance\":false}\n";
  done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

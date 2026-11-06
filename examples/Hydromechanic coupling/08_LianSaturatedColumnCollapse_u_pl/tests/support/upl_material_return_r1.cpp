// Test-only material-point candidates. Linked production legacy remains untouched.
#include "DualSphDef.h"
#include "JAppInfo.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
JAppInfo AppInfo("UplMaterialReturn","r1","06-11-2026");
void UpdateDPvars(float&,float&,float&,float,float,float,float,float,float,float,float,TpDPCtes);
void Updatedfdk(double&,float,float,float,float,float,float,float,float,double,TpDPCtes);
void ConsRelationEPsft_fast(tsymatrix3d,float,float,float,float,float,float,float,float,float,TpDPCtes,float,tsymatrix3d&,float&);
namespace fs=std::filesystem;
constexpr double Pi=3.1415926535897932384626433832795;
const float E=20000000.f,Nu=.33f,Phi=float(25.*Pi/180.);
const float Bulk=E/(3.f*(1.f-2.f*Nu)),Shear=E/(2.f*(1.f+Nu));
static void Need(bool ok,const char* m){if(!ok)throw std::runtime_error(m);}
struct Material{float cp,cr,eta,psi0,sf;}; // Original parameter storage remains float.
struct Inv{double I,q;};
static Inv Invariants(const tsymatrix3d& s){const double I=s.xx+s.yy+s.zz,m=I/3.;return {I,std::sqrt(.5*((s.xx-m)*(s.xx-m)+(s.yy-m)*(s.yy-m)+(s.zz-m)*(s.zz-m)+2.*(s.xy*s.xy+s.yz*s.yz+s.xz*s.xz)))};}
struct Coeff{double a,kc,b,fk,bk,psi;};
static Coeff At(const Material& m,double k,double I,bool decay){
  const double t=std::tan(double(Phi)),den=std::sqrt(9.+12.*t*t),coh=double(m.cr)+(double(m.cp)-m.cr)*std::exp(-double(m.eta)*k);
  const double psi=double(m.psi0)*(decay?std::exp(-double(m.sf)*k):1.),tp=std::tan(psi),dp=9.+12.*tp*tp;
  return {t/den,3.*coh/den,tp/std::sqrt(dp),3.*double(m.eta)*(coh-m.cr)/den,
    (decay?-double(m.sf)*psi:0.)*9.*(1.+tp*tp)/std::pow(dp,1.5),psi};
}
// Independent Eq14/16/18 check from returned tensor invariants and SAVED kappa.
static double Yield(const tsymatrix3d& s,const Material& m,double k){const auto v=Invariants(s);const double t=std::tan(double(Phi)),den=std::sqrt(9.+12.*t*t),c=double(m.cr)+(double(m.cp)-m.cr)*std::exp(-double(m.eta)*k);return v.q+t/den*v.I-3.*c/den;}
static tsymatrix3d Stress(double I,double q){tsymatrix3d s={};const double scale=q/std::sqrt(1.+.25*.25+.125*.125+.5*.5);s.xx=I/3.+scale;s.yy=I/3.;s.zz=I/3.-scale;s.xy=.25*scale;s.yz=-.125*scale;s.xz=.5*scale;return s;}
static double Gap(const tsymatrix3d& a,const tsymatrix3d& b){return (std::max)({fabs(a.xx-b.xx),fabs(a.yy-b.yy),fabs(a.zz-b.zz),fabs(a.xy-b.xy),fabs(a.yz-b.yz),fabs(a.xz-b.xz)});}
static std::array<double,3> Norms(const tsymatrix3d& trial,const tsymatrix3d& s){
  const double x=trial.xx-s.xx,y=trial.yy-s.yy,z=trial.zz-s.zz,xy=trial.xy-s.xy,yz=trial.yz-s.yz,xz=trial.xz-s.xz,mean=(x+y+z)/3.;
  const double ds2=(x-mean)*(x-mean)+(y-mean)*(y-mean)+(z-mean)*(z-mean)+2.*(xy*xy+yz*yz+xz*xz),dev2=ds2/(4.*double(Shear)*Shear);
  return {std::sqrt((2./3.)*dev2),std::sqrt((2./3.)*(dev2+mean*mean/(3.*double(Bulk)*Bulk))),mean/double(Bulk)};
}
struct Result{tsymatrix3d s={};float k=0;double kcontinuous=0,lambda=0,linearPlus=0,linearMinus=0,stableDen=0,rootResidual=0,rootBudget=0,h=0;unsigned iterations=0;const char* status="unset";bool available=false;};
static const char* Branch[4]={"linked_legacy","consistent_full_constant_psi","consistent_dev_constant_psi","consistent_dev_decay_psi"};
static Result Legacy(const tsymatrix3d& trial,const Material& m,float old){
  Result r;r.k=old;r.s=trial;r.kcontinuous=old;float a=0,kc=0,b=0;double fk=0;UpdateDPvars(a,kc,b,Phi,Phi,0.f,m.cp,m.cr,m.eta,m.psi0,old,DP_PS);const auto v=Invariants(trial);Updatedfdk(fk,Phi,Phi,0.f,m.cp,m.cr,m.eta,m.psi0,old,v.I,DP_PS);
  const float hf=std::sqrt((2.f/3.f)*(3.f*b*b+.5f));r.h=hf;const double f=v.q+double(a)*v.I-kc,A=9.*double(Bulk)*a*b+double(Shear);r.linearPlus=(f>1e-5?f/(A+fk*hf):0.);r.linearMinus=(f>1e-5?f/(A-fk*hf):0.);r.stableDen=A-fk*hf;
  ConsRelationEPsft_fast(trial,Bulk,Shear,Phi,Phi,0.f,m.cp,m.cr,m.eta,m.psi0,DP_PS,old,r.s,r.k);
  r.kcontinuous=r.k;r.available=std::isfinite(r.s.xx)&&std::isfinite(r.s.yy)&&std::isfinite(r.s.zz)&&std::isfinite(r.s.xy)&&std::isfinite(r.s.yz)&&std::isfinite(r.s.xz)&&std::isfinite(r.k);r.status=(r.available?"observed_legacy":"observed_nonfinite_legacy");return r;
}
static Result Candidate(const tsymatrix3d& trial,const Material& m,float old,unsigned branch){
  Result r;r.s=trial;r.k=old;r.kcontinuous=old;const auto tr=Invariants(trial);const bool dev=(branch>=2),decay=(branch==3);const auto co=At(m,old,tr.I,decay);const double ft=tr.q+co.a*tr.I-co.kc;
  r.h=(dev?1./std::sqrt(3.):std::sqrt((2./3.)*(3.*co.b*co.b+.5)));const double A=double(Shear)+9.*double(Bulk)*co.a*co.b;r.stableDen=A-co.fk*r.h;r.linearPlus=(ft>1e-5?ft/(A+co.fk*r.h):0.);r.linearMinus=(ft>1e-5?ft/r.stableDen:0.);
  if(ft<1e-5){r.available=true;r.status="elastic_exact";return r;}
  if(!(tr.q>0.)){r.status="apex_unsupported";return r;}
  if(!(r.stableDen>0.)){r.status="nonpositive_initial_consistency_denominator";return r;}
  const double limit=tr.q/double(Shear); // Never cross q=0 or invent an apex flow direction.
  const auto evaluate=[&](double l,double& df,double& I,double& k,Coeff& c){k=double(old)+r.h*l;c=At(m,k,tr.I,decay);I=tr.I-9.*double(Bulk)*c.b*l;const double f=tr.q-double(Shear)*l+c.a*I-c.kc;df=-double(Shear)-9.*double(Bulk)*c.a*(c.b+l*c.bk*r.h)+c.fk*r.h;return f;};
  double d=0,I=0,k=old;Coeff c{};const double flimit=evaluate(limit,d,I,k,c);
  if(!std::isfinite(flimit)||flimit>0){r.status="radial_root_requires_apex_or_nonlocal_branch";return r;}
  double lo=0,hi=limit,l=(std::min)(hi,(std::max)(lo,r.linearMinus)),f=ft;
  r.rootBudget=1e-10*(std::max)({1.,fabs(tr.q),fabs(co.a*tr.I),fabs(co.kc)});
  for(unsigned n=0;n<80;n++){
    f=evaluate(l,d,I,k,c);r.iterations=n+1;
    if(!(std::isfinite(f)&&std::isfinite(d)&&std::isfinite(k)&&k>=old&&d<0.)){r.status="nonfinite_or_nonpositive_local_consistency";return r;}
    if(fabs(f)<=r.rootBudget)break;
    if(f>0)lo=l;else hi=l;const double next=l-f/d;l=(std::isfinite(next)&&next>lo&&next<hi?next:.5*(lo+hi));
  }
  r.rootResidual=f;r.lambda=l;r.stableDen=-d;r.kcontinuous=k;
  if(fabs(f)>r.rootBudget){r.status="bounded_scalar_root_not_converged";return r;}
  const double scale=(tr.q-double(Shear)*l)/tr.q;Need(scale>=0&&scale<=1,"Internal radial bracket defect");const double mean=I/3.,oldmean=tr.I/3.;
  r.s.xx=mean+scale*(trial.xx-oldmean);r.s.yy=mean+scale*(trial.yy-oldmean);r.s.zz=mean+scale*(trial.zz-oldmean);r.s.xy=scale*trial.xy;r.s.yz=scale*trial.yz;r.s.xz=scale*trial.xz;
  r.k=float(k);r.available=true;r.status="radial_return_available";return r;
}
static void Put(std::ostream& out,const tsymatrix3d& s){out<<','<<s.xx<<','<<s.yy<<','<<s.zz<<','<<s.xy<<','<<s.yz<<','<<s.xz;}
struct Counts{unsigned rows=0,legacyNonfinite=0,radial=0,unsupported=0,elastic=0;};
static Result Row(std::ostream& out,Counts& count,const char* path,unsigned step,unsigned branch,const Material& m,const tsymatrix3d& trial,float old){
  const Result r=(branch?Candidate(trial,m,old,branch):Legacy(trial,m,old));const auto tr=Invariants(trial);const bool decay=(branch==3);const auto start=At(m,old,tr.I,decay);const double ft=Yield(trial,m,old);const auto norm=(r.available?Norms(trial,r.s):std::array<double,3>{0,0,0});
  const double savedYield=(r.available?Yield(r.s,m,r.k):std::numeric_limits<double>::quiet_NaN()),continuousYield=(r.available?Yield(r.s,m,r.kcontinuous):std::numeric_limits<double>::quiet_NaN());const auto end=At(m,r.kcontinuous,tr.I,decay);
  double analyticLambda=std::numeric_limits<double>::quiet_NaN();if(m.cp==m.cr&&(!decay||m.sf==0.f||m.psi0==0.f)&&ft>1e-5)analyticLambda=ft/(double(Shear)+9.*double(Bulk)*start.a*start.b);
  // No legacy residual, norm, loss or candidate difference is forced to pass.
  out<<path<<','<<step<<','<<Branch[branch]<<','<<double(m.psi0)*180./Pi<<','<<m.cp<<','<<m.cr<<','<<m.eta<<','<<(decay?m.sf:0.f)<<','<<old<<','<<r.kcontinuous<<','<<r.k<<','<<double(r.k)-old<<','<<r.kcontinuous-old<<','<<r.available<<','<<r.status;
  Put(out,trial);Put(out,r.s);out<<','<<ft<<','<<(r.available?Yield(r.s,m,old):std::numeric_limits<double>::quiet_NaN())<<','<<continuousYield<<','<<savedYield<<','<<start.psi*180./Pi<<','<<end.psi*180./Pi<<','<<r.h<<','<<r.linearPlus<<','<<r.linearMinus<<','<<r.lambda<<','<<r.stableDen<<','<<r.rootResidual<<','<<r.rootBudget<<','<<r.iterations<<','<<norm[0]<<','<<norm[1]<<','<<norm[2]<<','<<r.h*r.lambda<<','<<analyticLambda<<','<<(std::isfinite(analyticLambda)&&branch?fabs(r.lambda-analyticLambda):std::numeric_limits<double>::quiet_NaN())<<','<<double(std::nextafter(old,std::numeric_limits<float>::infinity()))-old<<','<<(r.available&&r.k==old&&Gap(trial,r.s)>0)<<','<<(branch&&r.available?norm[branch>=2?0:1]:std::numeric_limits<double>::quiet_NaN())<<','<<(branch&&r.available?fabs(norm[branch>=2?0:1]-r.h*r.lambda):std::numeric_limits<double>::quiet_NaN())<<','<<(branch&&r.available&&fabs(continuousYield)<=(std::max)(4.*r.rootBudget,1e-5))<<'\n';
  count.rows++;if(!r.available){if(branch)count.unsupported++;else count.legacyNonfinite++;}else if(!branch){}else if(r.lambda>0)count.radial++;else count.elastic++;return r;
}
int main(int argc,char** argv){try{
  Need(argc==2,"Use FRESH_OUTPUT_DIRECTORY");const fs::path dir=argv[1];Need(!fs::exists(dir)&&fs::is_directory(dir.parent_path()),"Fresh output and existing parent required");Need(fs::create_directory(dir),"Cannot claim fresh output");std::ofstream out(dir/"points.csv");Need(bool(out),"Cannot create points.csv");out<<std::setprecision(17);
  out<<"path,step,branch,psi0_deg,cp_Pa,cr_Pa,eta,sf,kappa_old_float,kappa_continuous,kappa_saved_float,kappa_written_increment,kappa_continuous_increment,return_available,status,trial_xx,trial_yy,trial_zz,trial_xy,trial_yz,trial_xz,new_xx,new_yy,new_zz,new_xy,new_yz,new_xz,f_trial_old_Pa,f_return_old_Pa,f_return_continuous_Pa,f_return_saved_Pa,psi_at_old_deg,psi_at_continuous_deg,h_history,lambda_linear_plus,lambda_linear_minus,lambda_solved,minus_dF_dlambda_Pa,scalar_residual_Pa,scalar_budget_Pa,root_iterations,dev_norm_total_return,full_norm_total_return,plastic_volume_total_return,h_lambda,constant_strength_closed_lambda,constant_strength_lambda_error,kappa_next_float_ULP,zero_saved_kappa_despite_return,independent_history_norm,independent_norm_minus_h_lambda,independent_tensor_yield_within_root_budget\n";Counts count;
  for(double degrees:{0.,2.5,-5.}){
    const Material m{degrees<0?7500.f:5000.f,1000.f,5.f,float(degrees*Pi/180.),.2f};
    for(unsigned branch=0;branch<4;branch++){
      float k=0;tsymatrix3d previous={};bool prior=true;
      for(unsigned step=0;step<7&&prior;step++){
        const double yieldq=At(m,k,-60000.,false).kc-At(m,k,-60000.,false).a*(-60000.);tsymatrix3d trial={};const char* label="";
        if(step==0){trial=Stress(-60000.,.5*yieldq);label="elastic";}
        else if(step==1){trial=Stress(-60000.,yieldq+200.);label="first_yield_nonzero_shear";}
        else if(step<=4){const auto v=Invariants(previous);trial=Stress(v.I,v.q+1000.);label="further_loading_nonzero_shear";}
        else if(step==5){const auto v=Invariants(previous);trial=Stress(v.I,.5*v.q);label="unloading";}
        else{const auto v=Invariants(previous);trial=Stress(v.I,v.q+100.);label="elastic_reload";}
        const auto r=Row(out,count,label,step,branch,m,trial,k);prior=r.available;if(prior){previous=r.s;k=r.k;}
      }
      const float preset=.5f;const auto strength=At(m,preset,-60000.,false);Row(out,count,"preset_kappa_nonzero_shear",0,branch,m,Stress(-60000.,strength.kc-strength.a*(-60000.)+1000.),preset);
      const double apexI=strength.kc/strength.a+1000.;Row(out,count,"hydrostatic_apex_diagnostic",0,branch,m,Stress(apexI,0),preset);Row(out,count,"near_apex_diagnostic",0,branch,m,Stress(apexI,1.),preset);
      const Material constant{m.cp,m.cp,0.f,m.psi0,0.f};const auto co=At(constant,0,-60000.,false);Row(out,count,"constant_strength_closed_control",0,branch,constant,Stress(-60000.,co.kc-co.a*(-60000.)+1000.),0.f);
    }
  }
  out.flush();Need(bool(out),"Material points CSV write failed");std::ofstream done(dir/"completion.json");done<<"{\"stage\":\"upl_material_return_r1\",\"rows\":"<<count.rows<<",\"candidate_radial_returns\":"<<count.radial<<",\"candidate_elastic_returns\":"<<count.elastic<<",\"candidate_unsupported_rows\":"<<count.unsupported<<",\"observed_legacy_nonfinite_rows\":"<<count.legacyNonfinite<<",\"production_legacy_linked\":true,\"four_algorithms_separate\":true,\"parameters_float\":true,\"persistent_kappa_float\":true,\"candidate_local_root_double\":true,\"unsupported_apex_explicit\":true,\"legacy_or_difference_forced_to_pass\":false,\"constitutive_release_or_physical_acceptance\":false,\"spatial_solver\":false}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

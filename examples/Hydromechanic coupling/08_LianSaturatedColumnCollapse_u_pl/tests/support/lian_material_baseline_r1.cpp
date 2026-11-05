// Material-point observations of the linked CPU implementation; no spatial solver.
// Link the frozen non-main CPU objects. Do not include or clone JSphCpu.cpp.
#include "DualSphDef.h"
#include "JAppInfo.h"
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

JAppInfo AppInfo("LianMaterialBaseline","r1","06-11-2026");

void UpdateDPvars(float&,float&,float&,float,float,float,float,float,float,float,float,TpDPCtes);
void Updatedfdk(double&,float,float,float,float,float,float,float,float,double,TpDPCtes);
void ConsRelationEPsft_fast(tsymatrix3d,float,float,float,float,float,float,float,float,float,TpDPCtes,float,tsymatrix3d&,float&);
void ConsRelationEP_fast(tsymatrix3d,float,float,float,float,float,float,tsymatrix3d&,float&);

namespace fs=std::filesystem;
constexpr double Pi=3.1415926535897932384626433832795;
const float Phi=float(25.*Pi/180.),E=20000000.f,Nu=.33f;
const float Bulk=E/(3.f*(1.f-2.f*Nu)),Shear=E/(2.f*(1.f+Nu));
const float Coh=5000.f,Residual=1000.f,Eta=5.f;
struct Invariants{double mean,q;};
static Invariants Inv(const tsymatrix3d& s){
  const double m=(s.xx+s.yy+s.zz)/3.;
  const double x=s.xx-m,y=s.yy-m,z=s.zz-m;
  return {m,std::sqrt(.5*(x*x+y*y+z*z+2.*(s.xy*s.xy+s.yz*s.yz+s.xz*s.xz)))};
}
// Independent plane-strain yield reference: direct Eq16/18, not UpdateDPvars.
static double Strength(double k,bool soft){
  const double c=soft?double(Residual)+(double(Coh)-Residual)*std::exp(-double(Eta)*k):double(Coh);
  const double t=std::tan(double(Phi));return 3.*c/std::sqrt(9.+12.*t*t);
}
static double Yield(const tsymatrix3d& s,double k,bool soft){
  const auto v=Inv(s);const double t=std::tan(double(Phi));
  return v.q+3.*v.mean*t/std::sqrt(9.+12.*t*t)-Strength(k,soft);
}
static tsymatrix3d Trial(double q){tsymatrix3d s={};s.xx=-20000.+q;s.yy=-20000.;s.zz=-20000.-q;return s;}
static void Put(std::ostream& out,const tsymatrix3d& s){out<<','<<s.xx<<','<<s.yy<<','<<s.zz<<','<<s.xy<<','<<s.yz<<','<<s.xz;}
static void Need(bool good,const char* text){if(!good)throw std::runtime_error(text);}

static void Point(std::ostream& out,bool soft,float psi,unsigned step,const char* label
  ,const tsymatrix3d& trial,float old,tsymatrix3d& next,float& knew){
  const float cr=soft?Residual:Coh,nc=soft?Eta:0.f;
  float aphi=0,kc=0,apsi=0;double df=0;
  UpdateDPvars(aphi,kc,apsi,Phi,Phi,0.f,Coh,cr,nc,psi,old,DP_PS);
  Updatedfdk(df,Phi,Phi,0.f,Coh,cr,nc,psi,old,3.*Inv(trial).mean,DP_PS);
  if(soft)ConsRelationEPsft_fast(trial,Bulk,Shear,Phi,Phi,0.f,Coh,cr,nc,psi,DP_PS,old,next,knew);
  else ConsRelationEP_fast(trial,Bulk,Shear,aphi,kc,apsi,old,next,knew);
  const auto ti=Inv(trial);
  const double ft=ti.q+double(aphi)*(3.*ti.mean)-double(kc);
  // Predictions only: these expose the two consistency signs and norm choices.
  const float hfull=std::sqrt((2.f/3.f)*(3.f*apsi*apsi+.5f));
  const double hdev=1./std::sqrt(3.),flow=9.*double(Bulk)*aphi*apsi+double(Shear);
  const double plus=flow+df*hfull,minusfull=flow-df*hfull,minusdev=flow-df*hdev;
  const double lp=(ft>1e-5?ft/plus:0.),lm=(ft>1e-5?ft/minusfull:0.),ld=(ft>1e-5?ft/minusdev:0.);
  const double predicted=lp*hfull,written=double(knew)-double(old);
  const double eps=1e-5;
  const double dfref=(Yield(trial,double(old)+eps,soft)-Yield(trial,double(old)-eps,soft))/(2.*eps);
  // Independent compliance applied to the ACTUAL full returned stress correction.
  // It includes any final apex/radial projection, not just the first plastic flow.
  const double dx=trial.xx-next.xx,dy=trial.yy-next.yy,dz=trial.zz-next.zz;
  const double xy=trial.xy-next.xy,yz=trial.yz-next.yz,xz=trial.xz-next.xz;
  const double mean=(dx+dy+dz)/3.;
  const double ds2=(dx-mean)*(dx-mean)+(dy-mean)*(dy-mean)+(dz-mean)*(dz-mean)+2.*(xy*xy+yz*yz+xz*xz);
  const double dev2=ds2/(4.*double(Shear)*Shear);
  const double devnorm=std::sqrt((2./3.)*dev2);
  const double fullnorm=std::sqrt((2./3.)*(dev2+mean*mean/(3.*double(Bulk)*Bulk)));
  const double ulp=double(std::nextafter(old,std::numeric_limits<float>::infinity()))-old;
  const bool rounded=(predicted>0 && float(double(old)+predicted)==old && knew==old);
  for(double v:{next.xx,next.yy,next.zz,next.xy,next.yz,next.xz,double(knew),df,dfref,lp,lm,ld,devnorm,fullnorm})
    Need(std::isfinite(v),"Nonfinite actual material result or descriptive reference");
  out<<(soft?"cohesion_softening":"constant_strength")<<','<<double(psi)*180./Pi<<','<<step<<','<<label;
  Put(out,trial);Put(out,next);
  out<<','<<old<<','<<knew<<','<<written<<','<<Yield(trial,old,soft)<<','<<Yield(next,old,soft)<<','<<Yield(next,knew,soft)
    <<','<<aphi<<','<<kc<<','<<apsi<<','<<ft<<','<<df<<','<<dfref<<','<<hfull<<','<<hdev<<','<<flow
    <<','<<plus<<','<<minusfull<<','<<minusdev<<','<<lp<<','<<lm<<','<<ld<<','<<predicted
    <<','<<devnorm<<','<<fullnorm<<','<<std::sqrt(3.)*devnorm<<','<<mean/double(Bulk)
    <<','<<ulp<<','<<rounded<<','<<(written==0 && devnorm>0)<<'\n';
}

int main(int argc,char** argv){try{
  Need(argc==2,"Use FRESH_OUTPUT_DIRECTORY");const fs::path dir=argv[1];
  Need(!fs::exists(dir)&&fs::is_directory(dir.parent_path()),"Fresh output and existing parent required; retain prior data");
  fs::create_directory(dir);std::ofstream out(dir/"points.csv");Need(bool(out),"Cannot create points CSV");out<<std::setprecision(17);
  out<<"material,psi0_deg,step,path,trial_xx,trial_yy,trial_zz,trial_xy,trial_yz,trial_xz,new_xx,new_yy,new_zz,new_xy,new_yz,new_xz,kappa_old,kappa_new,kappa_written_increment"
    <<",f_trial_old_strength_Pa,f_new_old_strength_Pa,f_new_new_strength_Pa,actual_DP_phi,actual_DP_kc_Pa,actual_DP_psi,actual_frozen_trial_f_Pa,actual_dfdk_Pa,independent_fd_dfdk_Pa"
    <<",old_full_flow_norm,deviatoric_flow_norm,frozen_flow_denominator_Pa,plus_full_denominator_Pa,minus_full_denominator_Pa,minus_dev_denominator_Pa"
    <<",pred_lambda_plus_full,pred_lambda_minus_full,pred_lambda_minus_dev,pred_first_return_dk_plus_full,dev_norm_total_return,full_norm_total_return,lambda_equiv_total_dev_return,plastic_volume_total_return"
    <<",kappa_next_float_ulp,predicted_float_loss,zero_written_kappa_despite_return_strain\n";
  unsigned rows=0;
  for(bool soft:{false,true})for(double degrees:{0.,2.5,-5.}){
    const float psi=float(degrees*Pi/180.);float k=0;tsymatrix3d previous={};
    const double t=std::tan(double(Phi)),yieldq=Strength(0,soft)+60000.*t/std::sqrt(9.+12.*t*t);
    for(unsigned step=0;step<6;step++){
      tsymatrix3d trial={};const char* label="";
      if(step==0){trial=Trial(.5*yieldq);label="elastic";}
      else if(step==1){trial=Trial(yieldq+100.);label="first_yield";}
      else if(step==2){trial=previous;trial.xx+=1000.;trial.zz-=1000.;label="further_loading";}
      else if(step==3){trial=previous;const double m=Inv(trial).mean;
        trial.xx=m+.5*(trial.xx-m);trial.yy=m+.5*(trial.yy-m);trial.zz=m+.5*(trial.zz-m);
        trial.xy*=.5;trial.yz*=.5;trial.xz*=.5;label="unloading";}
      else if(step==4){trial=previous;trial.xx+=1000.;trial.zz-=1000.;label="elastic_reload";}
      else{k=.5f;trial=Trial(Strength(k,soft)+60000.*t/std::sqrt(9.+12.*t*t)+.001);label="synthetic_history_rounding_probe";}
      tsymatrix3d next={};float knew=k;
      Point(out,soft,psi,step,label,trial,k,next,knew);previous=next;k=knew;rows++;
    }
  }
  out.flush();Need(bool(out),"Material CSV write failed");
  std::ofstream done(dir/"completion.json");done<<"{\"stage\":\"lian_material_baseline_r1\",\"rows\":"<<rows
    <<",\"linked_existing_CPU_material_functions\":true,\"psi_softening_implemented\":false,\"spatial_solver\":false,\"observations_only\":true,\"numerical_differences_forced_to_pass\":false,\"physical_acceptance\":false}\n";
  done.flush();Need(bool(done),"Material completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

// Test-only persistent-history companion. No spatial solver or production edits.
// Link the same frozen CPU non-main objects used by lian_material_baseline_r1.
#include "DualSphDef.h"
#include "JAppInfo.h"
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>

JAppInfo AppInfo("LianMaterialHistory","r1","06-11-2026");
void GetStressInvariant(double,double,double,double,double,double,double&,double&);
void GetDPYieldFunction(double&,double,double,float,float);
void UpdateDPvars(float&,float&,float&,float,float,float,float,float,float,float,float,TpDPCtes);
void Updatedfdk(double&,float,float,float,float,float,float,float,float,double,TpDPCtes);
void ConsRelationEPsft_fast(tsymatrix3d,float,float,float,float,float,float,float,float,float,TpDPCtes,float,tsymatrix3d&,float&);

// Companion of production ConsRelationEPsft_fast, with exactly these changes:
// name; double input/output/local tk; explicit float(tk) at BOTH linked material
// helper entries; and double(tk)+dk without the persistent float writeback.
// Full norm, plus denominator, old-strength projection and constant psi remain.
static void ConsRelationEPsft_history_double(tsymatrix3d sigma
        , const float E_ModulusK, const float E_ModulusG, const float MC_phi, const float MC_phir, const float n_phi
        , const float MC_c, const float MC_cr, const float n_coh, const float MC_psi
        , const TpDPCtes dpctes, double kplastic
        , tsymatrix3d &nsigma, double& nkplastic)
{
    double tsigma_xx, tsigma_yy, tsigma_zz, tsigma_xy, tsigma_yz, tsigma_xz;
    double tk;
    double ModulusK = E_ModulusK;
    double ModulusG = E_ModulusG;
    const float phi_p = MC_phi;
    const float phi_r = MC_phir;
    const float n_p   = n_phi;
    const float coh_p = MC_c;
    const float coh_r = MC_cr;
    const float n_c   = n_coh;
    const float psi = MC_psi;
    tsigma_xx = sigma.xx;
    tsigma_yy = sigma.yy;
    tsigma_zz = sigma.zz;
    tsigma_xy = sigma.xy;
    tsigma_yz = sigma.yz;
    tsigma_xz = sigma.xz;
    tk = kplastic;
    float DP_phi=0, DP_kc=0, DP_psi=0;
    UpdateDPvars(DP_phi,DP_kc,DP_psi,phi_p,phi_r,n_p,coh_p,coh_r,n_c,psi,float(tk),dpctes);
    double f=0, I1=0, J2=0;
    float err = 1e-5f;
    GetStressInvariant(tsigma_xx,tsigma_yy,tsigma_zz,tsigma_xy,tsigma_yz,tsigma_xz,I1,J2);
    GetDPYieldFunction(f,I1,J2,DP_phi,DP_kc);
    if (f<err) {
        nkplastic = tk;
        nsigma.xx = tsigma_xx;
        nsigma.yy = tsigma_yy;
        nsigma.zz = tsigma_zz;
        nsigma.xy = tsigma_xy;
        nsigma.yz = tsigma_yz;
        nsigma.xz = tsigma_xz;
    }
    else {
        double dsigmap_xx = 0, dsigmap_yy = 0, dsigmap_zz = 0, dsigmap_xy = 0, dsigmap_yz = 0, dsigmap_xz = 0
             , dk = 0;;
        double dfdk = 0;
        Updatedfdk(dfdk,phi_p,phi_r,n_p,coh_p,coh_r,n_c,psi,float(tk),I1,dpctes);
        const float dkflowcoef = sqrt((2.f/3.f)*(3.f*DP_psi*DP_psi+0.5f));
        double extra = dfdk*dkflowcoef;
        double dlambda = f /(9.f*ModulusK*DP_phi*DP_psi+ModulusG+extra);
        double GJ2 = ModulusG / sqrt(J2);
        double Deppxx = 3.f*ModulusK*DP_psi+GJ2*(tsigma_xx-I1/3.f);
        double Deppyy = 3.f*ModulusK*DP_psi+GJ2*(tsigma_yy-I1/3.f);
        double Deppzz = 3.f*ModulusK*DP_psi+GJ2*(tsigma_zz-I1/3.f);
        double Deppxy = GJ2*tsigma_xy;
        double Deppyz = GJ2*tsigma_yz;
        double Deppxz = GJ2*tsigma_xz;
        dsigmap_xx = dlambda*Deppxx;
        dsigmap_yy = dlambda*Deppyy;
        dsigmap_zz = dlambda*Deppzz;
        dsigmap_xy = dlambda*Deppxy;
        dsigmap_yz = dlambda*Deppyz;
        dsigmap_xz = dlambda*Deppxz;
        tsigma_xx = tsigma_xx - dsigmap_xx;
        tsigma_yy = tsigma_yy - dsigmap_yy;
        tsigma_zz = tsigma_zz - dsigmap_zz;
        tsigma_xy = tsigma_xy - dsigmap_xy;
        tsigma_yz = tsigma_yz - dsigmap_yz;
        tsigma_xz = tsigma_xz - dsigmap_xz;
        dk = dlambda*dkflowcoef;
        tk = double(tk) + dk;
        GetStressInvariant(tsigma_xx,tsigma_yy,tsigma_zz,tsigma_xy,tsigma_yz,tsigma_xz,I1,J2);
        double kalpha = DP_kc / DP_phi;
        if (I1 > kalpha) {
            tsigma_xx = tsigma_xx - (I1 - kalpha) / 3.f;
            tsigma_yy = tsigma_yy - (I1 - kalpha) / 3.f;
            tsigma_zz = tsigma_zz - (I1 - kalpha) / 3.f;
            GetStressInvariant(tsigma_xx, tsigma_yy, tsigma_zz, tsigma_xy, tsigma_yz, tsigma_xz, I1, J2);
        }
        double fscale = (J2>0.f? (-DP_phi * I1 + DP_kc) / sqrt(J2): 1.f);
        if (J2 != 0 && fscale < 1.f) {
            tsigma_xx = fscale * (tsigma_xx - I1 / 3.f) + I1 / 3.f;
            tsigma_yy = fscale * (tsigma_yy - I1 / 3.f) + I1 / 3.f;
            tsigma_zz = fscale * (tsigma_zz - I1 / 3.f) + I1 / 3.f;
            tsigma_xy = fscale * tsigma_xy;
            tsigma_yz = fscale * tsigma_yz;
            tsigma_xz = fscale * tsigma_xz;
        }
        nkplastic = tk;
        nsigma.xx = tsigma_xx;
        nsigma.yy = tsigma_yy;
        nsigma.zz = tsigma_zz;
        nsigma.xy = tsigma_xy;
        nsigma.yz = tsigma_yz;
        nsigma.xz = tsigma_xz;
    }
}

namespace fs=std::filesystem;
using Clock=std::chrono::steady_clock;
constexpr double Pi=3.1415926535897932384626433832795;
const float Phi=float(25.*Pi/180.),Psi=float(2.5*Pi/180.),E=20000000.f,Nu=.33f;
const float Bulk=E/(3.f*(1.f-2.f*Nu)),Shear=E/(2.f*(1.f+Nu));
const float Coh=5000.f,Residual=1000.f,Eta=5.f;
static void Need(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
static double Abs(double x){return std::fabs(x);}
static double Gap(const tsymatrix3d& a,const tsymatrix3d& b){
    double m=0;for(double x:{Abs(a.xx-b.xx),Abs(a.yy-b.yy),Abs(a.zz-b.zz),Abs(a.xy-b.xy),Abs(a.yz-b.yz),Abs(a.xz-b.xz)})if(m<x)m=x;return m;
}
static double MeanEffectiveCompression(const tsymatrix3d& s){return -(s.xx+s.yy+s.zz)/3.;}
struct Material{float a=0,kc=0,psi=0;double yield=0;};
static Material At(const tsymatrix3d& s,double persistent_k){
    Material m;UpdateDPvars(m.a,m.kc,m.psi,Phi,Phi,0.f,Coh,Residual,Eta,Psi,float(persistent_k),DP_PS);
    double I1=0,J2=0;GetStressInvariant(s.xx,s.yy,s.zz,s.xy,s.yz,s.xz,I1,J2);
    GetDPYieldFunction(m.yield,I1,J2,m.a,m.kc);return m;
}
static tsymatrix3d Initial(double k){
    tsymatrix3d s={};const auto m=At(s,k);const double q=double(m.kc)+60000.*double(m.a);
    s.xx=-20000.+q;s.yy=-20000.;s.zz=-20000.-q;return s;
}
static tsymatrix3d Increment(tsymatrix3d s,double dq){s.xx+=dq;s.zz-=dq;return s;}
static void Put(std::ostream& out,const tsymatrix3d& s){out<<','<<s.xx<<','<<s.yy<<','<<s.zz<<','<<s.xy<<','<<s.yz<<','<<s.xz;}
struct Summary{
    const char* name;unsigned steps,rows=0,zero_float=0,zero_double=0;
    double initial_k,dq,final_float=0,final_double=0,max_k_gap=0,max_stress_gap=0,max_mean_gap=0,max_kc_gap=0;
    double max_yield_float=0,max_yield_double=0;
};
static void Row(std::ostream& out,const Summary& p,const char* branch,unsigned step,const tsymatrix3d& trial
    ,const tsymatrix3d& s,double old,double next,bool control,double kgap,double mgap,double sgap,double cg){
    const auto mt=At(trial,old),mo=At(s,old),mn=At(s,next);
    const double mf=float(old),mulp=double(std::nextafter(float(old),std::numeric_limits<float>::infinity()))-mf;
    const double pulp=control?mulp:std::nextafter(old,std::numeric_limits<double>::infinity())-old;
    const double returned=Gap(trial,s);const bool zero=next==old&&returned>0;
    for(double x:{s.xx,s.yy,s.zz,s.xy,s.yz,s.xz,old,next,mt.yield,mo.yield,mn.yield,double(mn.kc),kgap,mgap,sgap,cg})
        Need(std::isfinite(x),"Nonfinite observation");
    out<<p.name<<','<<branch<<','<<step<<','<<(step?p.dq:0)<<','<<old<<','<<next<<','<<double(float(old))<<','<<double(float(next))
       <<','<<next-old<<','<<mn.kc<<','<<mt.yield<<','<<mo.yield<<','<<mn.yield<<','<<MeanEffectiveCompression(s);
    Put(out,s);out<<','<<returned<<','<<mulp<<','<<pulp<<','<<zero<<','<<kgap<<','<<mgap<<','<<sgap<<','<<cg<<'\n';
}
static Summary Path(std::ostream& out,const char* name,double initial_k,double dq,unsigned steps){
    Summary p{name,steps};p.initial_k=initial_k;p.dq=dq;
    float kf=float(initial_k);double kd=initial_k;tsymatrix3d sf=Initial(initial_k),sd=sf;
    Row(out,p,"production_float",0,sf,sf,kf,kf,true,0,0,0,0);
    Row(out,p,"companion_double_history",0,sd,sd,kd,kd,false,0,0,0,0);p.rows=2;
    for(unsigned step=1;step<=steps;step++){
        const auto tf=Increment(sf,dq),td=Increment(sd,dq);const float of=kf;const double od=kd;tsymatrix3d nf={},nd={};
        ConsRelationEPsft_fast(tf,Bulk,Shear,Phi,Phi,0.f,Coh,Residual,Eta,Psi,DP_PS,of,nf,kf);
        ConsRelationEPsft_history_double(td,Bulk,Shear,Phi,Phi,0.f,Coh,Residual,Eta,Psi,DP_PS,od,nd,kd);
        const double kgap=kd-double(kf),mgap=MeanEffectiveCompression(nd)-MeanEffectiveCompression(nf),sgap=Gap(nf,nd),cg=double(At(nd,kd).kc)-At(nf,kf).kc;
        Row(out,p,"production_float",step,tf,nf,of,kf,true,kgap,mgap,sgap,cg);
        Row(out,p,"companion_double_history",step,td,nd,od,kd,false,kgap,mgap,sgap,cg);
        p.rows+=2;
        p.zero_float+=kf==of&&Gap(tf,nf)>0;p.zero_double+=kd==od&&Gap(td,nd)>0;
        if(p.max_k_gap<Abs(kgap))p.max_k_gap=Abs(kgap);if(p.max_stress_gap<sgap)p.max_stress_gap=sgap;
        if(p.max_mean_gap<Abs(mgap))p.max_mean_gap=Abs(mgap);if(p.max_kc_gap<Abs(cg))p.max_kc_gap=Abs(cg);
        const double yf=Abs(At(nf,kf).yield),yd=Abs(At(nd,kd).yield);
        if(p.max_yield_float<yf)p.max_yield_float=yf;if(p.max_yield_double<yd)p.max_yield_double=yd;
        sf=nf;sd=nd;
    }
    p.final_float=kf;p.final_double=kd;return p;
}
static void Json(std::ostream& out,const Summary& p){
    out<<"{\"path\":\""<<p.name<<"\",\"updates_per_branch\":"<<p.steps<<",\"CSV_rows_including_initial\":"<<p.rows
       <<",\"initial_kappa\":"<<p.initial_k<<",\"deviatoric_stress_increment_Pa\":"<<p.dq
       <<",\"final_float_kappa\":"<<p.final_float<<",\"final_double_kappa\":"<<p.final_double
       <<",\"zero_float_write_with_return_rows\":"<<p.zero_float<<",\"zero_double_write_with_return_rows\":"<<p.zero_double
       <<",\"max_abs_kappa_gap\":"<<p.max_k_gap<<",\"max_stress_component_gap_Pa\":"<<p.max_stress_gap
       <<",\"max_mean_effective_compression_gap_Pa\":"<<p.max_mean_gap<<",\"max_DP_kc_gap_Pa\":"<<p.max_kc_gap
       <<",\"max_abs_new_material_yield_float_Pa\":"<<p.max_yield_float<<",\"max_abs_new_material_yield_double_Pa\":"<<p.max_yield_double<<'}';
}
int main(int argc,char** argv){try{
    Need(argc==2,"Use FRESH_OUTPUT_DIRECTORY");const fs::path dir=argv[1];
    Need(!fs::exists(dir)&&fs::is_directory(dir.parent_path()),"Fresh output and existing parent required");
    Need(fs::create_directory(dir),"Cannot claim fresh output directory");std::ofstream out(dir/"points.csv");Need(bool(out),"Cannot create CSV");out<<std::setprecision(17);
    out<<"path,branch,step,dq_Pa,kappa_old,kappa_new,material_kappa_old,material_kappa_new,kappa_increment,actual_DP_kc_Pa,trial_yield_old_Pa,returned_yield_old_Pa,returned_yield_new_Pa,mean_effective_compression_Pa"
       <<",xx,yy,zz,xy,yz,xz,stress_return_max_Pa,material_float_ulp,persistent_kappa_ulp,zero_kappa_write_with_stress_return,paired_kappa_gap_D_minus_F,paired_mean_effective_compression_gap_D_minus_F,paired_stress_gap_max_Pa,paired_DP_kc_gap_D_minus_F\n";
    const auto start=Clock::now();const auto ordinary=Path(out,"ordinary_continuous",0.,1000.,16);
    const auto subulp=Path(out,"subulp_continuous",.5,.1,256);
    const auto loopns=std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-start).count();
    out.flush();Need(bool(out),"CSV write failed");std::ofstream done(dir/"completion.json");Need(bool(done),"Cannot create completion");done<<std::setprecision(17);
    done<<"{\"stage\":\"lian_material_history_r1\",\"rows\":"<<ordinary.rows+subulp.rows
        <<",\"linked_production_float_calls\":"<<ordinary.steps+subulp.steps<<",\"test_double_history_calls\":"<<ordinary.steps+subulp.steps
        <<",\"material_and_DP_coefficients_remain_float\":true,\"history_cast_to_float_at_material_entries\":true,\"same_plus_full_norm_old_strength_algorithm\":true"
        <<",\"psi_target_deg\":2.5,\"psi_softening_implemented\":false,\"pore_pressure_state_or_equation\":false,\"spatial_solver\":false,\"observations_only\":true,\"physical_acceptance\":false"
        <<",\"timing_is_single_probe_overhead_not_case_speed\":true,\"paired_paths_with_CSV_diagnostics_nanoseconds\":"<<loopns<<",\"paths\":[";
    Json(done,ordinary);done<<',';Json(done,subulp);done<<"]}\n";done.flush();Need(bool(done),"Completion write failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

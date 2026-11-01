// Frozen-field P3 operator screening only. No JSph, solver, state evolution or boundary implementation.
// Uses the real project Wendland kernel and matrix inverse; finite reciprocal graphs have no periodic clones.
#include "FunSphKernel.h"
#include "FunctionsMath.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
namespace fs=std::filesystem;
static void Need(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static double Norm(tdouble3 a){return sqrt(Dot(a,a));}
static tdouble3 Mul(const tmatrix3d& c,tdouble3 a){return TDouble3(c.a11*a.x+c.a12*a.y+c.a13*a.z,c.a21*a.x+c.a22*a.y+c.a23*a.z,c.a31*a.x+c.a32*a.y+c.a33*a.z);}
static tmatrix3d Mean(const tmatrix3d& a,const tmatrix3d& b){
  return TMatrix3d((a.a11+b.a11)*.5,(a.a12+b.a12)*.5,(a.a13+b.a13)*.5,
    (a.a21+b.a21)*.5,(a.a22+b.a22)*.5,(a.a23+b.a23)*.5,(a.a31+b.a31)*.5,(a.a32+b.a32)*.5,(a.a33+b.a33)*.5);
}
static void Outer(tmatrix3d& m,tdouble3 a,tdouble3 b,double w){
  m.a11+=w*a.x*b.x;m.a12+=w*a.x*b.y;m.a13+=w*a.x*b.z;
  m.a21+=w*a.y*b.x;m.a22+=w*a.y*b.y;m.a23+=w*a.y*b.z;
  m.a31+=w*a.z*b.x;m.a32+=w*a.z*b.y;m.a33+=w*a.z*b.z;
}
static constexpr double RhoWater=1000,Kw=2e8,K=1./1024.,Gamma=8000.,Dp=1./8.,H=Dp,Eta2=H*H/100.;
static const char* Operator(unsigned op){return op==0?"raw_pair_R":op==1?"symC_pair_R":"legacy_symC_head_plus_receiverC_Das";}
struct Node{tdouble3 x;double j,n,V;bool core;tmatrix3d c;};
struct Edge{unsigned i,j;tdouble3 d,g;double rr,betaRaw,betaSym;};
struct Patch{
  unsigned dim;bool jitter;std::vector<Node> nodes;std::vector<Edge> edges;
  double minBeta=0,maxBetaAsym=0;unsigned coreCount=0;
  Patch(unsigned dimension,bool disorder):dim(dimension),jitter(disorder){
    const double n0=double(float(.3)),v0=pow(Dp,int(dim));
    for(int iy=(dim==3?-4:0);iy<=(dim==3?4:0);iy++)for(int iz=-4;iz<=4;iz++)for(int ix=-4;ix<=4;ix++){
      const unsigned hash=unsigned(ix+4)*73u+unsigned(iy+4)*151u+unsigned(iz+4)*263u+17u;
      tdouble3 x=TDouble3(ix*Dp,iy*Dp,iz*Dp);
      if(jitter){const unsigned axis=hash%dim;const double dx=((hash/7)%2?1.:-1.)*Dp/8.;if(axis==0)x.x+=dx;else if(dim==2||axis==2)x.z+=dx;else x.y+=dx;}
      const double j=double(28+hash%9)/32.;const bool core=abs(ix)<=1&&abs(iz)<=1&&(dim==2||abs(iy)<=1);
      nodes.push_back({x,j,1.-(1.-n0)/j,v0*j,core,TMatrix3d(0)});if(core)coreCount++;
    }
    const auto kernel=fsph::GetKernelWendland_Ctes(dim==2,H);
    for(unsigned i=0;i<nodes.size();i++)for(unsigned j=i+1;j<nodes.size();j++){
      const auto d=nodes[i].x-nodes[j].x;const double rr=Dot(d,d);
      if(rr<=4.*H*H&&rr>0){const double fac=fsph::GetKernelWendland_Fac(kernel,float(H),float(rr));const auto g=d*fac;
        edges.push_back({i,j,d,g,rr,0,0});Outer(nodes[i].c,d,g,-nodes[j].V);Outer(nodes[j].c,d,g,-nodes[i].V);}
    }
    for(auto& p:nodes){
      const auto m=p.c;
      if(dim==2){const double det=m.a11*m.a33-m.a13*m.a31;Need(det>0,"Singular/nonpositive2D patch moment");p.c=TMatrix3d(0);p.c.a11=m.a33/det;p.c.a13=-m.a13/det;p.c.a31=-m.a31/det;p.c.a33=m.a11/det;}
      else{const double det=fmath::Determinant3x3(m);Need(det>0,"Singular/nonpositive3D patch moment");p.c=fmath::InverseMatrix3x3(m,det);}
    }
    for(auto& e:edges){
      const auto c=Mean(nodes[e.i].c,nodes[e.j].c);e.betaRaw=Dot(e.d,e.g)/(e.rr+Eta2);e.betaSym=Dot(e.d,Mul(c,e.g))/(e.rr+Eta2);
      const double reverse=Dot(e.d*(-1.),Mul(Mean(nodes[e.j].c,nodes[e.i].c),e.g*(-1.)))/(e.rr+Eta2);
      Need(std::isfinite(e.betaSym)&&e.betaRaw<=0&&e.betaSym<=0,"Positive/nonfinite reciprocal beta");
      Need(e.betaSym==reverse,"Symmetric pair coefficient is not exactly reciprocal");minBeta=(std::min)(minBeta,e.betaSym);maxBetaAsym=(std::max)(maxBetaAsym,fabs(e.betaSym-reverse));
    }
    Need(coreCount==(dim==2?9u:27u),"Full-support core coverage changed");
  }
};
struct Field{
  const char* name;std::vector<double> p;std::vector<tdouble3> ace,as,gradReference;
  tdouble3 gravity;double theta=0,k=K,continuum=0;bool equilibrium=false,affinePressure=false,purePressure=false,constantFlux=false;
};
static Field MakeField(const Patch& patch,unsigned which){
  static const char* names[]={"equilibrium_g0_Aplus","equilibrium_gminus_Aplus","equilibrium_gminus_Aminus","equilibrium_gplus_Aplus",
    "constant_pressure_constant_acceleration","pure_quadratic_pressure","quadratic_pressure_affine_acceleration","k0_compression","k0_dilation","k0_zero_trace",
    "freefall_gminus","freefall_gplus","static_hydrostatic_gminus"};
  Field f;f.name=names[which];f.gravity=TDouble3(0,0,which==0||which==5?0:which==3||which==11?8:-8);
  f.equilibrium=which<4||which>=10;f.affinePressure=which<5||which>=7;f.purePressure=which==5;f.constantFlux=which==4;
  f.theta=which==7?-1./32.:which==8?1./32.:0;if(which>=7&&which<=9)f.k=0;
  const tdouble3 A=TDouble3(.25,patch.dim==3?-.125:0.,-.5)*(which==2?-1.:1.);
  for(const auto& node:patch.nodes){
    const auto x=node.x;double p=2048;tdouble3 a=TDouble3(0),gp=TDouble3(0);
    if(which<5){a=A;if(which<4){gp=A*(-RhoWater);p+=Dot(gp,x);}}
    else if(which>=10){
      if(which==12){a=f.gravity*(-1.);gp=f.gravity*RhoWater;p+=Dot(gp,x);} //-Stationary hydrostatic: a_s=0.
      //-Free fall otherwise: Ace=0, a_s=g, constant pressure.
    }
    else if(which==5||which==6){
      const tdouble3 hdiag=TDouble3(1024,patch.dim==3?2048:0,3072),b=TDouble3(64,patch.dim==3?-32:0,128);
      gp=TDouble3(b.x+hdiag.x*x.x,b.y+hdiag.y*x.y,b.z+hdiag.z*x.z);p+=Dot(b,x)+.5*(hdiag.x*x.x*x.x+hdiag.y*x.y*x.y+hdiag.z*x.z*x.z);
      f.continuum=hdiag.x+hdiag.y+hdiag.z;
      if(which==6){a=A+TDouble3(x.x/16.+x.z/32.+(patch.dim==3?x.y/64.:0.),patch.dim==3?(x.x/128.-x.y/32.-x.z/64.):0.,-x.x/64.+x.z/8.+(patch.dim==3?x.y/32.:0.));f.continuum+=RhoWater*(1./16.+1./8.-(patch.dim==3?1./32.:0.));}
    }
    f.p.push_back(p);f.ace.push_back(a);f.as.push_back(a+f.gravity);f.gradReference.push_back(gp);
  }
  return f;
}
struct Result{std::array<std::vector<double>,3> rate,darcy;std::vector<tdouble3> gp,q,qReference;double maxR=0,maxQerror=0,maxQGravityError=0;};
static Result Evaluate(const Patch& patch,const Field& f){
  const unsigned n=unsigned(patch.nodes.size());Result r;
  for(unsigned op=0;op<3;op++){r.rate[op].assign(n,0);r.darcy[op].assign(n,0);}r.gp.assign(n,TDouble3(0));
  for(const auto& e:patch.edges){
    const auto i=e.i,j=e.j;const auto& pi=patch.nodes[i];const auto& pj=patch.nodes[j];
    const auto ci=Mul(pi.c,e.g),cj=Mul(pj.c,e.g*(-1.));const auto abar=(f.ace[i]+f.ace[j])*.5;
    const double Rij=f.p[i]-f.p[j]+RhoWater*Dot(abar,e.d),Rji=f.p[j]-f.p[i]+RhoWater*Dot(abar,e.d*(-1.));
    const double scale=fabs(f.p[i]-f.p[j])+RhoWater*fabs(Dot(abar,e.d));
    Need(fabs(Rij+Rji)<=32*DBL_EPSILON*scale+1e-12,"Pair residual lost antisymmetry");
    r.maxR=(std::max)(r.maxR,fabs(Rij));
    const auto abarFromPhysical=((f.as[i]-f.gravity)+(f.as[j]-f.gravity))*.5;
    Need(fabs(Rij-(f.p[i]-f.p[j]+RhoWater*Dot(abarFromPhysical,e.d)))<=32*DBL_EPSILON*scale+1e-12,"Gravity cancellation is not once-only");
    for(unsigned op=0;op<2;op++){const double beta=op==0?e.betaRaw:e.betaSym;r.darcy[op][i]+=2*pj.V*Rij*beta;r.darcy[op][j]+=2*pi.V*Rji*beta;}
    const double Hij=f.p[i]-f.p[j]-RhoWater*Dot(f.gravity,e.d),Hji=f.p[j]-f.p[i]-RhoWater*Dot(f.gravity,e.d*(-1.));
    r.darcy[2][i]+=2*pj.V*Hij*e.betaSym+RhoWater*pj.V*Dot(f.as[j]-f.as[i],ci);
    r.darcy[2][j]+=2*pi.V*Hji*e.betaSym+RhoWater*pi.V*Dot(f.as[i]-f.as[j],cj);
    r.gp[i]=r.gp[i]+ci*(pj.V*(f.p[j]-f.p[i]));r.gp[j]=r.gp[j]+cj*(pi.V*(f.p[i]-f.p[j]));
  }
  for(unsigned i=0;i<n;i++){
    const auto& p=patch.nodes[i];
    for(unsigned op=0;op<3;op++){r.darcy[op][i]*=Kw/p.n*f.k/Gamma;r.rate[op][i]=r.darcy[op][i]-Kw/p.n*f.theta;Need(std::isfinite(r.rate[op][i]),"Nonfinite frozen rate");}
    const auto q=(r.gp[i]-(f.gravity-f.as[i])*RhoWater)*(-f.k/Gamma),qReduced=(r.gp[i]+f.ace[i]*RhoWater)*(-f.k/Gamma);
    const auto qr=(f.gradReference[i]+f.ace[i]*RhoWater)*(-f.k/Gamma);
    r.q.push_back(q);r.qReference.push_back(qr);r.maxQerror=(std::max)(r.maxQerror,Norm(q-qr));r.maxQGravityError=(std::max)(r.maxQGravityError,Norm(q-qReduced));
    Need(Norm(q-qReduced)<=5e-13*(std::max)(1.,Norm(qReduced))+1e-15,"Pointwise Darcy flux contains extra/missing body gravity");
    if(f.affinePressure){Need(Norm(r.gp[i]-f.gradReference[i])<=5e-12*(std::max)(1.,Norm(f.gradReference[i])),"Corrected affine pressure gradient fails pointwise reference");Need(Norm(q-qr)<=1e-12,"Affine Darcy flux fails pointwise reference");}
    if(f.equilibrium)for(unsigned op=0;op<2;op++)Need(fabs(r.rate[op][i])<=1e-7,"Pair equilibrium rate is not zero within declared roundoff");
    if(f.k==0)for(unsigned op=0;op<3;op++)Need(fabs(r.rate[op][i]+Kw/p.n*f.theta)<=5e-13*(std::max)(1.,fabs(Kw/p.n*f.theta)),"k0 compression equation changed");
  }
  return r;
}
struct Totals{unsigned rows=0;double maxBudgetRelative=0,maxEnergyRelative=0,maxEquilibriumRate=0,maxFluxError=0,maxConstantFluxDefect=0;};
static void Record(const Patch& patch,const Field& f,const Result& r,std::ostream& rows,std::ostream& summary,Totals& totals){
  for(unsigned op=0;op<3;op++){
    long double budget=0,budgetScale=0,energy=0,energyScale=0,pairEnergy=0,compBudget=0,totalBudget=0;
    double coreSquares=0,outerSquares=0,coreMax=0,outerMax=0,rateMax=0;unsigned nc=0,no=0;
    for(unsigned i=0;i<patch.nodes.size();i++){
      const auto& p=patch.nodes[i];const double weight=p.V*p.n/Kw,actual=r.rate[op][i],reference=Kw/p.n*(f.k/Gamma*f.continuum-f.theta),error=actual-reference;
      budget+=(long double)weight*r.darcy[op][i];budgetScale+=fabs(weight*r.darcy[op][i]);
      energy+=(long double)weight*f.p[i]*r.darcy[op][i];energyScale+=fabs(weight*f.p[i]*r.darcy[op][i]);
      totalBudget+=(long double)weight*actual;compBudget-=p.V*f.theta;rateMax=(std::max)(rateMax,fabs(actual));
      if(p.core){nc++;coreSquares+=error*error;coreMax=(std::max)(coreMax,fabs(error));}else{no++;outerSquares+=error*error;outerMax=(std::max)(outerMax,fabs(error));}
      const auto q=r.q[i],qr=r.qReference[i];
      rows<<patch.dim<<','<<patch.jitter<<','<<f.name<<','<<Operator(op)<<','<<i<<','<<p.core<<','<<f.p[i]<<','<<f.ace[i].x<<','<<f.ace[i].y<<','<<f.ace[i].z<<','<<p.n<<','<<p.V<<','<<f.theta<<','<<actual<<','<<r.darcy[op][i]<<','<<reference<<','<<q.x<<','<<q.y<<','<<q.z<<','<<qr.x<<','<<qr.y<<','<<qr.z<<'\n';totals.rows++;
    }
    if(op<2){
      const double tolerance=1024*DBL_EPSILON*double(budgetScale)+1e-14;
      Need(fabs(double(budget))<=tolerance,"Frozen reciprocal weighted Darcy budget failed");
      Need(fabs(double(totalBudget-compBudget))<=tolerance+1e-14,"Frozen compression-inclusive weighted budget failed");
      totals.maxBudgetRelative=(std::max)(totals.maxBudgetRelative,fabs(double(budget))/((std::max)(1e-14,double(budgetScale))));
    }
    if(f.purePressure){
      for(const auto& e:patch.edges){const double dp=f.p[e.i]-f.p[e.j],beta=op==0?e.betaRaw:e.betaSym;pairEnergy+=2.*f.k/Gamma*patch.nodes[e.i].V*patch.nodes[e.j].V*dp*dp*beta;}
      if(op<2){const double scale=(std::max)(double(energyScale),fabs(double(pairEnergy)));Need(double(energy)<=1e-10&&fabs(double(energy-pairEnergy))<=1024*DBL_EPSILON*scale+1e-10,"Frozen pure-pressure energy identity/sign failed");totals.maxEnergyRelative=(std::max)(totals.maxEnergyRelative,fabs(double(energy-pairEnergy))/((std::max)(1e-10,scale)));}
    }
    if(f.equilibrium&&op<2)totals.maxEquilibriumRate=(std::max)(totals.maxEquilibriumRate,rateMax);
    if(f.constantFlux&&op==1)totals.maxConstantFluxDefect=(std::max)(totals.maxConstantFluxDefect,coreMax);
    totals.maxFluxError=(std::max)(totals.maxFluxError,f.affinePressure?r.maxQerror:0.);
    summary<<patch.dim<<','<<patch.jitter<<','<<f.name<<','<<Operator(op)<<','<<patch.nodes.size()<<','<<patch.edges.size()<<','<<nc<<','<<no<<','<<double(budget)<<','<<double(totalBudget)<<','<<double(compBudget)<<','<<double(energy)<<','<<double(pairEnergy)<<','<<sqrt(coreSquares/nc)<<','<<coreMax<<','<<sqrt(outerSquares/no)<<','<<outerMax<<','<<rateMax<<','<<r.maxR<<','<<r.maxQerror<<','<<r.maxQGravityError<<'\n';
  }
}
int main(int argc,char** argv){
  try{
    Need(argc==3&&std::string(argv[1])=="--out","Use --out NEW_DIRECTORY");const fs::path out(argv[2]);Need(!fs::exists(out),"Retained output protected");fs::create_directories(out);
    std::ofstream nodes(out/"nodes.csv"),pairs(out/"pair_summary.csv"),rows(out/"rates.csv"),summary(out/"summary.csv");
    for(auto* s:{&nodes,&pairs,&rows,&summary})*s<<std::setprecision(17);
    nodes<<"dimension,jitter,id,x_m,y_m,z_m,J,n,V_mpowdim,full_support_core,Cxx,Cxy,Cxz,Cyy,Cyz,Czz\n";
    pairs<<"dimension,jitter,nodes,undirected_pairs,core_nodes,min_sym_beta,max_reciprocity_error,positive_beta_count\n";
    rows<<"dimension,jitter,field,operator,id,core,p_pa,Acex_m_s2,Acey_m_s2,Acez_m_s2,n,V_mpowdim,theta_per_s,total_rate_pa_s,darcy_rate_pa_s,continuum_rate_pa_s,qx_m_s,qy_m_s,qz_m_s,qrefx_m_s,qrefy_m_s,qrefz_m_s\n";
    summary<<"dimension,jitter,field,operator,nodes,undirected_pairs,core_nodes,outer_nodes,frozen_darcy_budget_mpowdim_s,frozen_total_budget_mpowdim_s,compression_budget_mpowdim_s,purep_energy_rate_pa_mpowdim_s,purep_pair_identity_pa_mpowdim_s,core_continuum_rms_pa_s,core_continuum_absmax_pa_s,outer_continuum_rms_pa_s,outer_continuum_absmax_pa_s,rate_absmax_pa_s,pair_R_absmax_pa,pointwise_flux_error_absmax_m_s,gravity_flux_identity_error_m_s\n";
    Totals totals;unsigned patches=0;
    for(unsigned dim:{2u,3u})for(bool jitter:{false,true}){
      Patch p(dim,jitter);patches++;
      for(unsigned i=0;i<p.nodes.size();i++){const auto& n=p.nodes[i];nodes<<dim<<','<<jitter<<','<<i<<','<<n.x.x<<','<<n.x.y<<','<<n.x.z<<','<<n.j<<','<<n.n<<','<<n.V<<','<<n.core<<','<<n.c.a11<<','<<n.c.a12<<','<<n.c.a13<<','<<n.c.a22<<','<<n.c.a23<<','<<n.c.a33<<'\n';}
      pairs<<dim<<','<<jitter<<','<<p.nodes.size()<<','<<p.edges.size()<<','<<p.coreCount<<','<<p.minBeta<<','<<p.maxBetaAsym<<",0\n";
      for(unsigned field=0;field<13;field++){const auto f=MakeField(p,field);const auto r=Evaluate(p,f);Record(p,f,r,rows,summary,totals);}
    }
    for(auto* s:{&nodes,&pairs,&rows,&summary}){s->flush();Need(bool(*s),"CSV write failed");}
    std::ofstream done(out/"complete.json");done<<std::setprecision(17)<<"{\"frozen_algebraic_gates_passed\":true,\"patches\":"<<patches<<",\"operators\":3,\"fields_per_patch\":13,\"node_operator_rows\":"<<totals.rows
      <<",\"max_frozen_budget_scaled_residual\":"<<totals.maxBudgetRelative<<",\"max_purep_energy_scaled_residual\":"<<totals.maxEnergyRelative<<",\"max_pair_equilibrium_rate_pa_s\":"<<totals.maxEquilibriumRate<<",\"max_affine_flux_error_m_s\":"<<totals.maxFluxError
      <<",\"symC_constant_flux_core_defect_pa_s\":"<<totals.maxConstantFluxDefect<<",\"constant_flux_defect_is_diagnostic\":true,\"continuum_accuracy_admitted\":false,\"actual_production_rate_pass_called\":false,\"production_overwrite_sentinel_verified\":false,\"physical_trajectory\":false,\"water_mass_conservation_proved\":false,\"periodic_clone_tested\":false,\"physical_acceptance\":false}\n";
    done.flush();Need(bool(done),"Completion write failed");std::cout<<"Frozen P3 algebraic screening finished; inspect defects before candidate admission. No production/physical acceptance.\n";return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}

// Four independent actual CPU OFF/alpha.1 numerical-viscosity force/Darcy evaluations; no time update.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsFixedDt.h"
#include <memory>
#include "JCellDivCpuSingle.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "JException.h"
#include "FunSphKernel.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <climits>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include <utility>
JAppInfo AppInfo("C08ResidualViscCpu","r2","09-11-2026");
namespace pathfs=std::filesystem;
static_assert(sizeof(unsigned)==4&&sizeof(tfloat3)==12&&sizeof(tdouble3)==24&&sizeof(tsymatrix3d)==48,"Frozen typed22 and named stress layout required");
static constexpr unsigned Original=7060,Total=6805,Fixed=1805,Soil=5000,Samples=90;
static constexpr unsigned Parts[2]={13,14},Pair[2]={7011,7012},Focus[4]={7011,7012,6230,6231},Bed[5]={1800,1852,1904,1956,2008};
static void Need(bool x,const char* s){if(!x)throw std::runtime_error(s);}
template<class T>static bool Bits(const T& a,const T& b){return !memcmp(&a,&b,sizeof(T));}
static bool Finite(float x){return std::isfinite(x);}static bool Finite(double x){return std::isfinite(x);}static bool Finite(unsigned){return true;}
static bool Finite(tfloat3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}static bool Finite(tdouble3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static tdouble3 Product(const tmatrix3d& c,tdouble3 g){return TDouble3(c.a11*g.x+c.a12*g.y+c.a13*g.z,c.a21*g.x+c.a22*g.y+c.a23*g.z,c.a31*g.x+c.a32*g.y+c.a33*g.z);}
template<class T>static std::vector<T> ReadArray(std::ifstream& f){std::vector<T> v(Total);f.read(reinterpret_cast<char*>(v.data()),sizeof(T)*Total);Need(bool(f),"Truncated native array");for(const auto& x:v)Need(Finite(x),"Nonfinite native array");return v;}

// Frozen-geometry, full soil-only matched eta0 least squares. Numerical viscosity, not GNOG.
static constexpr double Alpha=.1;
struct Mat2{double xx=0,xz=0,zx=0,zz=0;};
static tdouble3 Mul(const Mat2& a,tdouble3 d){return TDouble3(a.xx*d.x+a.xz*d.z,0,a.zx*d.x+a.zz*d.z);}
static void Outer(Mat2& a,tdouble3 v,tdouble3 d,double w){a.xx+=w*v.x*d.x;a.xz+=w*v.x*d.z;a.zx+=w*v.z*d.x;a.zz+=w*v.z*d.z;}
static double MN(const Mat2& a){return sqrt(a.xx*a.xx+a.xz*a.xz+a.zx*a.zx+a.zz*a.zz);}
static double MDot(const Mat2& a,const Mat2& b){return a.xx*b.xx+a.xz*b.xz+a.zx*b.zx+a.zz*b.zz;}
static double Len(tdouble3 a){return sqrt(Dot(a,a));}
struct Stats{
  double edges=0;
  double max_degree=0;
  double max_condition=0;
  double gamma64=0;
  double dmax_unit=0;
  double alpha_dt_dmax=0;
  double work=0;
  double form=0;
  double work_plus_2form=0;
  double work_budget=0;
  double work_defect_prediction=0;
  double work_certificate_error=0;
  double max_normal_defect=0;
  double max_normal_budget_fraction=0;
  double net_force_norm=0;
  double net_force_budget=0;
  double torque_y=0;
  double torque_budget=0;
  double torque_defect_prediction=0;
  double torque_certificate_error=0;
  double max_force=0;
  double max_added_accel=0;
  double committed_work=0;
  double committed_work_budget=0;
  double committed_net_force_norm=0;
  double committed_net_force_budget=0;
  double committed_torque_y=0;
  double committed_torque_budget=0;
  double max_commit_force_error=0;
  double manufacture_max_residual=0;
  double manufacture_residual_budget=0;
  double manufacture_force_budget=0;
};
static void StatsHeader(std::ostream& f){const char* names[]={"edges","max_degree","max_condition","gamma64","dmax_unit","alpha_dt_dmax","work","form","work_plus_2form","work_budget","work_defect_prediction","work_certificate_error","max_normal_defect","max_normal_budget_fraction","net_force_norm","net_force_budget","torque_y","torque_budget","torque_defect_prediction","torque_certificate_error","max_force","max_added_accel","committed_work","committed_work_budget","committed_net_force_norm","committed_net_force_budget","committed_torque_y","committed_torque_budget","max_commit_force_error","manufacture_max_residual","manufacture_residual_budget","manufacture_force_budget"};for(const char* n:names)f<<','<<n;}
static void StatsWrite(std::ostream& f,const Stats& s){const double values[]={s.edges,s.max_degree,s.max_condition,s.gamma64,s.dmax_unit,s.alpha_dt_dmax,s.work,s.form,s.work_plus_2form,s.work_budget,s.work_defect_prediction,s.work_certificate_error,s.max_normal_defect,s.max_normal_budget_fraction,s.net_force_norm,s.net_force_budget,s.torque_y,s.torque_budget,s.torque_defect_prediction,s.torque_certificate_error,s.max_force,s.max_added_accel,s.committed_work,s.committed_work_budget,s.committed_net_force_norm,s.committed_net_force_budget,s.committed_torque_y,s.committed_torque_budget,s.max_commit_force_error,s.manufacture_max_residual,s.manufacture_residual_budget,s.manufacture_force_budget};for(double v:values){Need(Finite(v),"Nonfinite candidate metric");f<<','<<v;}}
struct Edge{unsigned i,j;tdouble3 d;double weight,eta0,beta0;};
struct Graph{
  std::vector<tdouble3> x,v;std::vector<double> V,rho,mass,degree,condition;std::vector<Mat2> M;std::vector<Edge> edges;double G=0,h=0,gamma=0,dmax=0,maxdegree=0,maxcond=0;
  explicit Graph(unsigned n):x(n),v(n),V(n),rho(n),mass(n),degree(n),condition(n),M(n){}
  void Prepare(){
    std::vector<unsigned> count(x.size());for(const auto& e:edges){Outer(M[e.i],e.d,e.d,e.eta0*V[e.j]*e.weight);Outer(M[e.j],e.d,e.d,e.eta0*V[e.i]*e.weight);degree[e.i]+=e.beta0;degree[e.j]+=e.beta0;count[e.i]++;count[e.j]++;}
    for(unsigned i=0;i<x.size();i++){M[i].zx=M[i].xz;const auto a=M[i];const double scale=(std::max)({fabs(a.xx),fabs(a.xz),fabs(a.zz)});Need(scale>0&&Finite(scale),"Empty matched LS moment; no skipped node");const double aa=a.xx/scale,b=a.xz/scale,c=a.zz/scale,det=aa*c-b*b;Need(aa>0&&c>0&&det>128.*DBL_EPSILON*(aa*c+b*b),"Rank-deficient matched2D LS moment; no regularization");const double large=.5*(aa+c+hypot(aa-c,2*b)),eigenlo=det/large;condition[i]=large/eigenlo;maxcond=(std::max)(maxcond,condition[i]);maxdegree=(std::max)(maxdegree,double(count[i]));dmax=(std::max)(dmax,degree[i]/mass[i]);}
    const double ne=64.*double(x.size()+edges.size()+unsigned(maxdegree)+1)*DBL_EPSILON;Need(ne<1.,"Invalid declared double gamma");gamma=ne/(1.-ne);
  }
  std::vector<Mat2> Fit(const std::vector<tdouble3>& velocity)const{
    std::vector<Mat2> N(x.size()),L(x.size());for(const auto& e:edges){const auto dv=velocity[e.i]-velocity[e.j];Outer(N[e.i],dv,e.d,e.eta0*V[e.j]*e.weight);Outer(N[e.j],dv,e.d,e.eta0*V[e.i]*e.weight);}
    for(unsigned i=0;i<x.size();i++){const auto a=M[i],b=N[i];const double scale=(std::max)({fabs(a.xx),fabs(a.xz),fabs(a.zz)}),aa=a.xx/scale,bb=a.xz/scale,c=a.zz/scale,den=scale*(aa*c-bb*bb);L[i]={ (b.xx*c-b.xz*bb)/den,(-b.xx*bb+b.xz*aa)/den,(b.zx*c-b.zz*bb)/den,(-b.zx*bb+b.zz*aa)/den};Need(Finite(MN(L[i])),"Nonfinite unregularized LS solution");}return L;
  }
};
struct Evaluation{Stats s;std::vector<tdouble3> force;std::vector<Mat2> L;};
static Evaluation Evaluate(const Graph& g,const std::vector<tdouble3>& v,double alpha){
  Evaluation r;r.force.assign(v.size(),TDouble3(0));r.L=g.Fit(v);r.s.edges=double(g.edges.size());r.s.max_degree=g.maxdegree;r.s.max_condition=g.maxcond;r.s.gamma64=g.gamma;r.s.dmax_unit=g.dmax;
  std::vector<Mat2> defect(v.size());std::vector<double> defectScale(v.size()),forceScale(v.size());double rawScale=0,forcePairs=0,edgeVelocity=0;
  for(const auto& e:g.edges){const auto dv=v[e.i]-v[e.j],pi=Mul(r.L[e.i],e.d),pj=Mul(r.L[e.j],e.d),ri=dv-pi,rj=dv-pj;const double vv=Len(dv),li=Len(pi),lj=Len(pj),distance=Len(e.d);const auto f=(ri+rj)*(-.5*alpha*e.beta0);r.force[e.i]=r.force[e.i]+f;r.force[e.j]=r.force[e.j]-f;Outer(defect[e.i],ri,e.d,e.beta0);Outer(defect[e.j],rj,e.d,e.beta0);defectScale[e.i]+=e.beta0*(vv+li)*distance;defectScale[e.j]+=e.beta0*(vv+lj)*distance;forceScale[e.i]+=alpha*e.beta0*(vv+li+lj);forceScale[e.j]+=alpha*e.beta0*(vv+li+lj);r.s.form+=.25*alpha*e.beta0*(Dot(ri,ri)+Dot(rj,rj));rawScale+=alpha*e.beta0*(Dot(dv,dv)+Dot(pi,pi)+Dot(pj,pj));forcePairs+=2*Len(f);edgeVelocity=(std::max)(edgeVelocity,vv+li+lj);r.s.manufacture_max_residual=(std::max)({r.s.manufacture_max_residual,Len(ri),Len(rj)});}
  tdouble3 net=TDouble3(0);double contraction=0,normalWorkBudget=0,normalTorqueBudget=0,torqueScale=0,nodePowerScale=0;
  for(unsigned i=0;i<v.size();i++){const double dn=MN(defect[i]),budget=4*g.gamma*(1+g.condition[i])*defectScale[i];Need(dn<=budget,"Matched LS normal equation exceeds declared forward budget");r.s.max_normal_defect=(std::max)(r.s.max_normal_defect,dn);r.s.max_normal_budget_fraction=(std::max)(r.s.max_normal_budget_fraction,budget?dn/budget:0.);contraction+=MDot(r.L[i],defect[i]);normalWorkBudget+=.5*alpha*MN(r.L[i])*budget;normalTorqueBudget+=alpha*budget;net=net+r.force[i];r.s.work+=Dot(v[i],r.force[i]);r.s.torque_y+=g.x[i].z*r.force[i].x-g.x[i].x*r.force[i].z;r.s.torque_defect_prediction-=.5*alpha*(defect[i].xz-defect[i].zx);torqueScale+=fabs(g.x[i].z*r.force[i].x)+fabs(g.x[i].x*r.force[i].z);nodePowerScale+=fabs(v[i].x*r.force[i].x)+fabs(v[i].z*r.force[i].z);r.s.max_force=(std::max)(r.s.max_force,Len(r.force[i]));r.s.manufacture_force_budget=(std::max)(r.s.manufacture_force_budget,4*g.gamma*(1+g.condition[i])*forceScale[i]);}
  r.s.work_plus_2form=r.s.work+2*r.s.form;r.s.work_defect_prediction=-.5*alpha*contraction;r.s.work_certificate_error=r.s.work_plus_2form-r.s.work_defect_prediction;r.s.work_budget=g.gamma*(rawScale+nodePowerScale+2*r.s.form)+normalWorkBudget;r.s.net_force_norm=Len(net);r.s.net_force_budget=g.gamma*forcePairs;r.s.torque_budget=g.gamma*torqueScale+normalTorqueBudget;r.s.torque_certificate_error=r.s.torque_y-r.s.torque_defect_prediction;r.s.manufacture_residual_budget=4*g.gamma*(1+g.maxcond)*edgeVelocity;
  Need(fabs(r.s.work_certificate_error)<=g.gamma*(rawScale+nodePowerScale+2*r.s.form)&&fabs(r.s.torque_certificate_error)<=g.gamma*(torqueScale+fabs(r.s.torque_defect_prediction))&&fabs(r.s.work_plus_2form)<=r.s.work_budget&&r.s.work<=r.s.work_budget&&r.s.net_force_norm<=r.s.net_force_budget&&fabs(r.s.torque_y)<=r.s.torque_budget,"Damping quadratic/global force/torque certificate failed");return r;
}

struct Snapshot{
  unsigned part,completed;double time;std::vector<unsigned> id,fstype,byid;
  std::vector<tdouble3> pos,sk,si;std::vector<tfloat3> vel,legacykk,legacyij,fsnormal,load;
  std::vector<float> rhop,kap,p,p0,excess,posdiv;std::vector<double> j,n,theta,volume,rho,k;
  Snapshot(const pathfs::path& folder,unsigned selected):part(selected),completed(4000000+4000*(selected+1)),byid(Original,UINT_MAX){
    std::ifstream f(folder/"typed22.bin",std::ios::binary);unsigned h[3]={};f.read(reinterpret_cast<char*>(h),12);const std::uintmax_t stride=8+std::uintmax_t(Total)*212;
    Need(bool(f)&&h[0]==Total&&h[1]==22&&h[2]==Samples&&pathfs::file_size(folder/"typed22.bin")==12+Samples*stride,"Actual90/6805/22 native extent differs");
    Need((selected==Parts[0]||selected==Parts[1]),"Only actual total-AS/n3 causal90 saved parts13/14 is admitted");f.seekg(std::streamoff(12+selected*stride));f.read(reinterpret_cast<char*>(&time),8);Need(bool(f)&&Finite(time),"Invalid native clock");
    id=ReadArray<unsigned>(f);pos=ReadArray<tdouble3>(f);vel=ReadArray<tfloat3>(f);legacykk=ReadArray<tfloat3>(f);legacyij=ReadArray<tfloat3>(f);fsnormal=ReadArray<tfloat3>(f);load=ReadArray<tfloat3>(f);
    rhop=ReadArray<float>(f);kap=ReadArray<float>(f);p=ReadArray<float>(f);p0=ReadArray<float>(f);excess=ReadArray<float>(f);sk=ReadArray<tdouble3>(f);si=ReadArray<tdouble3>(f);fstype=ReadArray<unsigned>(f);
    j=ReadArray<double>(f);n=ReadArray<double>(f);theta=ReadArray<double>(f);volume=ReadArray<double>(f);rho=ReadArray<double>(f);k=ReadArray<double>(f);posdiv=ReadArray<float>(f);
    unsigned fixed=0,soil=0;for(unsigned q=0;q<Total;q++){const unsigned a=id[q];const bool bed=std::find(std::begin(Bed),std::end(Bed),a)!=std::end(Bed);Need(a<Original&&byid[a]==UINT_MAX&&(a<1800||bed||a>=2060),"Unexpected/duplicate/retired native ID");byid[a]=q;if(a<2060)fixed++;else{soil++;Need(kap[q]>=0&&j[q]>1.-double(.35f)&&n[q]>0&&n[q]<1&&rho[q]>0&&k[q]>0,"Invalid soil native ledger domain");if(fstype[q]==2||fstype[q]==3)Need(p[q]<=0,"Closed saved FS2/3 has positive pressure");}}
    Need(fixed==Fixed&&soil==Soil,"Actual fixed/soil ownership differs");
  }
};
class Probe:public JSphCpuSingle{
  std::vector<typecode> releasedCode;std::vector<tfloat3> releasedNormal;std::vector<byte> releasedSlip;
  std::vector<unsigned> Map()const{
    Need(Np==Total&&Npb==Fixed&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Full released-state allocation differs");std::vector<unsigned> b(Original,UINT_MAX);unsigned soil=0,fixed=0;
    for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(id<Original&&b[id]==UINT_MAX&&CODE_IsNormal(Codec[q]),"Changed/duplicate native identity");b[id]=q;if(id>=2060){Need(q>=Npb&&CODE_IsFluid(Codec[q]),"Soil ownership differs");soil++;}else{Need(q<Npb&&CODE_IsFixed(Codec[q])&&(id<1800||IsGravityPreloadBedId(id)),"Fixed ownership differs");fixed++;}}
    Need(soil==Soil&&fixed==Fixed,"Released counts differ");return b;
  }
  void StaticRoles()const{for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(Bits(Codec[q],releasedCode[id]),"ID-owned code changed");if(q<Npb){Need(Bits(BoundNormalc[q],releasedNormal[id])&&Bits(BoundSlipModec[q],releasedSlip[id]),"ID-owned wall normal/slip changed");if(IsGravityPreloadBedId(id))Need(BoundNormalc[q]==TFloat3(0,0,float(Dp))&&BoundSlipModec[q]==byte(SLIP_NoSlip),"Kept bed override differs");}}}
  void CopySaved(const Snapshot& a){for(unsigned q=0;q<Np;q++){const unsigned s=a.byid[Idpc[q]];Need(s!=UINT_MAX,"Snapshot/current ID mismatch");Posc[q]=a.pos[s];Velrhopc[q]=TFloat4(a.vel[s].x,a.vel[s].y,a.vel[s].z,a.rhop[s]);const auto kk=a.sk[s],ij=a.si[s];Sigmac[q]=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);Kplasticc[q]=a.kap[s];PorePressc[q]=a.p[s];PorePress0c[q]=a.p0[s];PoroJc[q]=a.j[s];PoroThetac[q]=a.theta[s];FSTypec[q]=a.fstype[s];FSNormalc[q]=a.fsnormal[s];PosDivc[q]=a.posdiv[s];HydroMechLoadAcec[q]=a.load[s];}}
  void Ledger(const Snapshot& a)const{for(unsigned q=Npb;q<Np;q++){const unsigned s=a.byid[Idpc[q]];double n,v,rho;GetPorosityFeedbackStateCpu(q,n,v,rho);const double k=GetDynamicConductivityCpu(q);Need(Bits(n,a.n[s])&&Bits(v,a.volume[s])&&Bits(rho,a.rho[s])&&Bits(k,a.k[s])&&Bits(float(rho),a.rhop[s]),"Original soil J/n/V/rho/k/cache ledger differs");}}
  void Restore(const Snapshot& a){
    Need(!Acec&&!Rsigmac&&!BoundDerivativeVelc&&!ArtificialStressc,"Previous force scratch still owned");Map();CopySaved(a);LoadDcellParticles(Np,Codec,Posc,Dcellc);
    const bool free=HydroMechFreeSeepage,shep=PoreShepardRegularization;HydroMechFreeSeepage=PoreShepardRegularization=false;
    try{BoundChanged=true;RunCellDivide(false);}catch(...){HydroMechFreeSeepage=free;PoreShepardRegularization=shep;throw;}HydroMechFreeSeepage=free;PoreShepardRegularization=shep;
    Need(!CellDivSingle->GetNpbOut()&&!CellDivSingle->GetNpfOut()&&!CellDivSingle->GetNpbOutIgnore()&&!CellDivSingle->GetNpfOutIgnore(),"Snapshot cell rebuild excluded a particle");Map();CopySaved(a);StaticRoles();Ledger(a);TimeStep=a.time;Nstep=a.completed;
  }
  void SoilUnchanged(const Snapshot& a)const{for(unsigned q=Npb;q<Np;q++){const unsigned s=a.byid[Idpc[q]];const tfloat4 v=TFloat4(a.vel[s].x,a.vel[s].y,a.vel[s].z,a.rhop[s]);const auto kk=a.sk[s],ij=a.si[s];const auto stress=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);Need(Bits(Posc[q],a.pos[s])&&Bits(Velrhopc[q],v)&&Bits(Sigmac[q],stress)&&Bits(Kplasticc[q],a.kap[s])&&Bits(PorePressc[q],a.p[s])&&Bits(PorePress0c[q],a.p0[s])&&Bits(PoroJc[q],a.j[s]),"Force evaluation changed a soil primary state");}StaticRoles();Ledger(a);Need(TimeStep==a.time&&unsigned(Nstep)==a.completed&&!PosPrec&&!PoroJPrec,"Zero-step evaluation advanced the state");}
  struct Response{std::vector<tdouble3> ace;std::vector<float> rate;std::vector<unsigned> fs;std::vector<tsymatrix3f> rsigma;std::vector<double> theta;std::vector<tmatrix3d> C;std::array<double,2> pairNormal{},pairRddot{};double normal=0,rddot=0;Response():ace(Original),rate(Original),fs(Original),rsigma(Original),theta(Original),C(Original){}};
  bool armed=false,candidate=false;unsigned hookOff=0,hookOn=0;Stats last;std::vector<tdouble3> idealDa,committedDa;
  Graph MakeGraph()const{
    Graph g(Soil);g.G=double(SoilCte.ModulusG);g.h=double(KernelH);const auto byid=Map();Need(g.G>0&&g.h>0,"Positive shear modulus/h required");for(unsigned i=0;i<Soil;i++){const unsigned q=byid[2060+i];double n;GetPorosityFeedbackStateCpu(q,n,g.V[i],g.rho[i]);g.mass[i]=g.V[i]*g.rho[i];g.x[i]=Posc[q];g.v[i]=TDouble3(Velrhopc[q].x,Velrhopc[q].y,Velrhopc[q].z);Need(g.x[i].y==0&&g.v[i].y==0&&g.mass[i]>0,"Planar positive current mass required");}
    const double support=4*g.h*g.h;for(unsigned i=0;i<Soil;i++)for(unsigned j=i+1;j<Soil;j++){const auto d=g.x[i]-g.x[j];const double rr=Dot(d,d);Need(rr>0,"Coincident soil nodes are not silently skipped");if(rr>=support)continue;const double w=-double(fsph::GetKernel_Fac<KERNEL_Cubic>(CSP,float(rr)));if(w==0)continue;Need(w>0&&Finite(w),"Cubic positive-weight graph required");const double eta=g.G*.5*(g.h/sqrt(g.G/g.rho[i])+g.h/sqrt(g.G/g.rho[j]));g.edges.push_back({i,j,d,w,eta,eta*g.V[i]*g.V[j]*w});}g.Prepare();return g;
  }
public:
  void Apply(){
    if(!armed)return;if(!candidate){hookOff++;return;}hookOn++;Need(Acec&&Rsigmac&&CorrMatc&&PoroThetac,"Candidate hook must run after mechanical force and before actual Darcy");const auto byid=Map();std::vector<double> theta(Soil);std::vector<tsymatrix3f> sigmaRate(Soil);std::vector<tmatrix3d> C(Soil);for(unsigned i=0;i<Soil;i++){const unsigned q=byid[2060+i];theta[i]=PoroThetac[q];sigmaRate[i]=Rsigmac[q];C[i]=CorrMatc[q];}Graph g=MakeGraph();auto r=Evaluate(g,g.v,Alpha);r.s.alpha_dt_dmax=Alpha*SymplecticDtPre*g.dmax;Need(r.s.alpha_dt_dmax<=1.,"Frozen isolated damping midpoint bound failed; original coupled bound still separate");std::vector<tfloat3> updated(Soil);tdouble3 net=TDouble3(0);double forceBudget=0,torqueBudget=0,workBudget=0;
    for(unsigned i=0;i<Soil;i++){const unsigned q=byid[2060+i];const auto old=ToTDouble3(Acec[q]),da=r.force[i]/g.mass[i];idealDa[2060+i]=da;updated[i]=TFloat3(float(old.x+da.x),0,float(old.z+da.z));Need(Finite(updated[i]),"Candidate float acceleration overflow");const auto committed=ToTDouble3(updated[i])-old,fc=committed*g.mass[i];committedDa[2060+i]=committed;const double budget=2.*FLT_EPSILON*g.mass[i]*(Len(old)+Len(da));Need(Len(fc-r.force[i])<=budget,"Once-final float acceleration commit exceeded declared bound");r.s.max_commit_force_error=(std::max)(r.s.max_commit_force_error,Len(fc-r.force[i]));r.s.max_added_accel=(std::max)(r.s.max_added_accel,Len(da));r.s.committed_work+=Dot(g.v[i],fc);net=net+fc;r.s.committed_torque_y+=g.x[i].z*fc.x-g.x[i].x*fc.z;forceBudget+=budget;torqueBudget+=Len(g.x[i])*budget;workBudget+=Len(g.v[i])*budget;}
    r.s.committed_net_force_norm=Len(net);r.s.committed_net_force_budget=r.s.net_force_budget+forceBudget;r.s.committed_torque_budget=r.s.torque_budget+torqueBudget;r.s.committed_work_budget=r.s.work_budget+workBudget;Need(r.s.committed_net_force_norm<=r.s.committed_net_force_budget&&fabs(r.s.committed_torque_y)<=r.s.committed_torque_budget&&r.s.committed_work<=r.s.committed_work_budget,"Committed float force/power/torque differs beyond rounding allowance");for(unsigned i=0;i<Soil;i++){const unsigned q=byid[2060+i];Acec[q]=updated[i];Need(Bits(PoroThetac[q],theta[i])&&Bits(Rsigmac[q],sigmaRate[i])&&Bits(CorrMatc[q],C[i]),"Candidate changed theta/Rsigma/C");}last=r.s;
  }
  void Manufactured(std::ostream& f,unsigned part){
    const Graph g=MakeGraph();tdouble3 center=TDouble3(0);for(auto x:g.x)center=center+x;center=center/double(Soil);for(unsigned test=0;test<3;test++){std::vector<tdouble3> v(Soil);for(unsigned i=0;i<Soil;i++){const auto x=g.x[i]-center;v[i]=test==0?TDouble3(.25,0,-.125):test==1?TDouble3(.07*x.x-.04*x.z+.2,0,.03*x.x+.02*x.z-.1):TDouble3(.08*x.z,0,-.08*x.x);}const auto r=Evaluate(g,v,Alpha);Need(r.s.manufacture_max_residual<=r.s.manufacture_residual_budget&&r.s.max_force<=r.s.manufacture_force_budget,"Manufactured constant/affine/rigid-rotation residual failed declared forward bound");f<<part<<','<<(test==0?"constant":test==1?"affine":"rigid_rotation");StatsWrite(f,r.s);f<<'\n';}
  }
  void Execute(const JSphCfgRun* cfg,JLog2* log,const Snapshot& first,const Snapshot& second){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();RunGravityPreloadHandoffCpu();FreePartsInit();
    Need(IsGravityPreloadHandoff()&&GravityPreload&&!GravityPreloadElasticSource&&!GravityPreloadReleased&&unsigned(Nstep)==4000000&&GravityPreloadKeepBedOverlap&&GravityPreloadBedIds==std::vector<unsigned>(std::begin(Bed),std::end(Bed)),"Actual certified PRE/keep5 receiver initialization differs");RunGravityPreloadRelease();Map();
    Need(GravityPreloadReleased&&GravityPreloadActualStep==4000000&&DynamicPorePressure&&PorosityFeedback&&DynamicPoreWall&&DynamicPoreConductivity&&DynamicPoreConductivityCk==2.&&HydroMechFreeSeepage&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilDamping&&!PoreShepardRegularization,"Released force-only controls differ");
    Need(Simulate2D&&!PeriActive&&TKernel==KERNEL_Cubic&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundSlipModec&&SoilStressRateGradCorr&&!SoilBoundaryDerivativeSPR&&!HourglassCpu&&!SoilHourglassXi&&!WithFloating&&!UseDEM&&!AccInput&&!Shifting&&!Damping&&TDensity==DDT_None&&NoPenetration&&TMdbc2==MDBC2_NoPen&&UseDynamicPorePlaneContact(),"Frozen released force scope differs");
    Need(ArtificialStress&&ArtificialStressCoef==.2f&&ArtificialStressExp==3.f&&TVisco==VISCO_Artificial&&Visco==.1f&&!ViscoTime&&Dp==.04&&KernelH==.048f&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==.0002f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&Gravity==TFloat3(0,0,-9.81f),"Original total-AS3/AV/material/kernel differs");
    Need(FixedDt&&FixedDt->GetFixedValue()==.0000025&&SymplecticDtPre==.0000025,"Original fixed/current necessary-step context differs");
    releasedCode.resize(Original);releasedNormal.resize(Original);releasedSlip.resize(Original);for(unsigned q=0;q<Np;q++){releasedCode[Idpc[q]]=Codec[q];if(q<Npb){releasedNormal[Idpc[q]]=BoundNormalc[q];releasedSlip[Idpc[q]]=BoundSlipModec[q];}}StaticRoles();const double releaseTime=GravityPreloadActualTime;const auto gravity=ToTDouble3(Gravity);
    std::ofstream soil(pathfs::path(cfg->DirOut)/"soil_force.csv"),focus(pathfs::path(cfg->DirOut)/"focus.csv"),pairs(pathfs::path(cfg->DirOut)/"pairs.csv"),damping(pathfs::path(cfg->DirOut)/"damping.csv"),manufactures(pathfs::path(cfg->DirOut)/"manufactured.csv"),callsCsv(pathfs::path(cfg->DirOut)/"calls.csv");for(auto* f:{&soil,&focus,&pairs,&damping,&manufactures,&callsCsv})*f<<std::setprecision(17);
    soil<<"call,part,time_s,tau_s,mode,native_id,x_m,z_m,Ace_x_m_s2,Ace_y_m_s2,Ace_z_m_s2,total_a_x_m_s2,total_a_y_m_s2,total_a_z_m_s2,switch_minus_baseline_Ace_x_m_s2,switch_minus_baseline_Ace_y_m_s2,switch_minus_baseline_Ace_z_m_s2,rate_Pa_s,switch_minus_baseline_rate_Pa_s,saved_FS,actual_FS,baseline_FS,theta_s_1,Rsigma_xx_Pa_s,Rsigma_yy_Pa_s,Rsigma_zz_Pa_s,Rsigma_xy_Pa_s,Rsigma_yz_Pa_s,Rsigma_xz_Pa_s,ideal_added_a_x_m_s2,ideal_added_a_z_m_s2,committed_added_a_x_m_s2,committed_added_a_z_m_s2\n";
    focus<<"call,part,time_s,tau_s,completed_step,mode,native_id,x_m,y_m,z_m,vx_m_s,vy_m_s,vz_m_s,p_Pa,P0_Pa,kappa,J,n,volume_m3,rho_kg_m3,k_m_s,sigma_xx_Pa,sigma_yy_Pa,sigma_zz_Pa,sigma_xy_Pa,sigma_yz_Pa,sigma_xz_Pa,total_trace_Pa,saved_FS,actual_FS,FSNormal_x,FSNormal_y,FSNormal_z,PosDiv,Cxx,Cxy,Cxz,Cyx,Cyy,Cyz,Czx,Czy,Czz,theta_s_1,Rsigma_xx_Pa_s,Rsigma_yy_Pa_s,Rsigma_zz_Pa_s,Rsigma_xy_Pa_s,Rsigma_yz_Pa_s,Rsigma_xz_Pa_s,Rsigma_trace_Pa_s,Ace_x_m_s2,Ace_y_m_s2,Ace_z_m_s2,total_a_x_m_s2,total_a_y_m_s2,total_a_z_m_s2,rate_Pa_s\n";
    pairs<<"call,part,time_s,tau_s,completed_step,mode,id_i,id_j,r_m,nx,ny,nz,dvx_m_s,dvy_m_s,dvz_m_s,rdot_m_s,tangential_speed2_m2_s2,tangential_curvature_m_s2,relative_total_a_normal_m_s2,rddot_m_s2,switch_minus_baseline_relative_a_normal_m_s2,switch_minus_baseline_rddot_m_s2,ideal_added_relative_a_normal_m_s2,committed_added_relative_a_normal_m_s2\n";
    callsCsv<<"call,part,time_s,tau_s,completed_step,mode,AS_enabled,AS_coefficient,AS_exponent,AV_coefficient,soil,saved_FS_changes,baseline_FS_changes,max_actual_rate_abs_Pa_s,actual_DtVariable_s,necessary_bound_s,force_scale_s,wave_visc_scale_s,pore_scale_s,k_gradient_scale_s,SymplecticDtPre_s,DtMin_s,AceMax_m_s2,VelMax_m_s,ViscDtMax,primary_bits_unchanged,operator_flags_restored\n";
    damping<<"call,part,time_s,tau_s,mode,alpha";StatsHeader(damping);damping<<'\n';manufactures<<"part,manufacture";StatsHeader(manufactures);manufactures<<'\n';unsigned calls=0,soilRows=0,focusRows=0,pairRows=0,restoreRateChecks=0,unchangedDerivativeChecks=0;const char* modes[2]={"OFF","ON"};
    for(const Snapshot* base:{&first,&second}){
      std::vector<Response> responses;responses.reserve(2);
      for(unsigned mode=0;mode<2;mode++){
        Restore(*base);SoilUnchanged(*base);const auto byid=Map();last=Stats{};idealDa.assign(Original,TDouble3(0));committedDa.assign(Original,TDouble3(0));Response out;unsigned savedFS=0,changedFS=0;double maxRate=0,dt=0,bound=0,forceDt=0,wave=0,pore=0,gradientDt=DBL_MAX;bool cleanup=true;
        {candidate=(mode==1);armed=true;
          try{Interaction_Forces(INTERSTEP_SymCorrector);armed=false;candidate=false;calls++;Need(Acec&&Rsigmac&&PorePressRatec&&BoundDerivativeVelc&&(ArtificialStress?ArtificialStressc!=NULL:ArtificialStressc==NULL),"Actual complete force-stage scratch/switch differs");SoilUnchanged(*base);
            dt=DtVariable(false);forceDt=CFLnumber*(AceMax?sqrt(double(KernelH)/AceMax):DBL_MAX);wave=double(KernelH)/((std::max)(double(Cs0),VelMax*10.)+double(KernelH)*ViscDtMax);GetDynamicStepScalesCpu(wave,pore);wave*=CFLnumber;if(DynamicPoreConductivity&&DynamicConductivitySpeedMax>0)gradientDt=double(PoreDtSafety)*double(KernelH)/DynamicConductivitySpeedMax;pore=(std::min)(pore,gradientDt);bound=(std::min)(forceDt,(std::min)(wave,pore));
            for(unsigned q=Npb;q<Np;q++){const unsigned id=Idpc[q],s=base->byid[id];Need(Finite(Acec[q])&&Finite(PorePressRatec[q])&&Finite(PoroThetac[q])&&Finite(Rsigmac[q].xx)&&Finite(Rsigmac[q].yy)&&Finite(Rsigmac[q].zz)&&Finite(Rsigmac[q].xy)&&Finite(Rsigmac[q].yz)&&Finite(Rsigmac[q].xz),"Actual full5000 force/rate/stressrate nonfinite");out.ace[id]=ToTDouble3(Acec[q]);out.rate[id]=PorePressRatec[q];out.fs[id]=FSTypec[q];out.rsigma[id]=Rsigmac[q];out.theta[id]=PoroThetac[q];out.C[id]=CorrMatc[q];if(mode){Need(Bits(out.rsigma[id],responses[0].rsigma[id])&&Bits(out.theta[id],responses[0].theta[id])&&Bits(out.C[id],responses[0].C[id])&&out.fs[id]==responses[0].fs[id],"ON changed original Rsigma/theta/C/FS before Darcy");unchangedDerivativeChecks++;}savedFS+=out.fs[id]!=base->fstype[s];const auto a=out.ace[id]+gravity,da=mode?out.ace[id]-responses[0].ace[id]:TDouble3(0);const double dr=mode?double(out.rate[id])-responses[0].rate[id]:0.;changedFS+=mode&&out.fs[id]!=responses[0].fs[id];maxRate=(std::max)(maxRate,fabs(double(out.rate[id])));soil<<calls<<','<<base->part<<','<<TimeStep<<','<<TimeStep-releaseTime<<','<<modes[mode]<<','<<id<<','<<Posc[q].x<<','<<Posc[q].z<<','<<out.ace[id].x<<','<<out.ace[id].y<<','<<out.ace[id].z<<','<<a.x<<','<<a.y<<','<<a.z<<','<<da.x<<','<<da.y<<','<<da.z<<','<<out.rate[id]<<','<<dr<<','<<base->fstype[s]<<','<<out.fs[id]<<','<<(mode?responses[0].fs[id]:out.fs[id])<<','<<PoroThetac[q]<<','<<Rsigmac[q].xx<<','<<Rsigmac[q].yy<<','<<Rsigmac[q].zz<<','<<Rsigmac[q].xy<<','<<Rsigmac[q].yz<<','<<Rsigmac[q].xz<<','<<idealDa[id].x<<','<<idealDa[id].z<<','<<committedDa[id].x<<','<<committedDa[id].z<<'\n';soilRows++;}
            for(unsigned id:Focus){const unsigned q=byid[id],s=base->byid[id];const auto x=Posc[q];const auto v=Velrhopc[q];const auto stress=Sigmac[q];const auto sr=Rsigmac[q];const auto normal=FSNormalc[q];const auto C=CorrMatc[q];const auto a=out.ace[id]+gravity;double n,V,rho;GetPorosityFeedbackStateCpu(q,n,V,rho);Need(Finite(sr.xx)&&Finite(sr.yy)&&Finite(sr.zz)&&Finite(sr.xy)&&Finite(sr.yz)&&Finite(sr.xz),"Actual focus stress rate nonfinite");focus<<calls<<','<<base->part<<','<<TimeStep<<','<<TimeStep-releaseTime<<','<<unsigned(Nstep)<<','<<modes[mode]<<','<<id<<','<<x.x<<','<<x.y<<','<<x.z<<','<<v.x<<','<<v.y<<','<<v.z<<','<<PorePressc[q]<<','<<PorePress0c[q]<<','<<Kplasticc[q]<<','<<PoroJc[q]<<','<<n<<','<<V<<','<<rho<<','<<GetDynamicConductivityCpu(q)<<','<<stress.xx<<','<<stress.yy<<','<<stress.zz<<','<<stress.xy<<','<<stress.yz<<','<<stress.xz<<','<<stress.xx+stress.yy+stress.zz-3.*PorePressc[q]<<','<<base->fstype[s]<<','<<FSTypec[q]<<','<<normal.x<<','<<normal.y<<','<<normal.z<<','<<PosDivc[q]<<','<<C.a11<<','<<C.a12<<','<<C.a13<<','<<C.a21<<','<<C.a22<<','<<C.a23<<','<<C.a31<<','<<C.a32<<','<<C.a33<<','<<PoroThetac[q]<<','<<sr.xx<<','<<sr.yy<<','<<sr.zz<<','<<sr.xy<<','<<sr.yz<<','<<sr.xz<<','<<double(sr.xx)+sr.yy+sr.zz<<','<<out.ace[id].x<<','<<out.ace[id].y<<','<<out.ace[id].z<<','<<a.x<<','<<a.y<<','<<a.z<<','<<out.rate[id]<<'\n';focusRows++;}
            for(unsigned which=0;which<2;which++){const unsigned idi=Focus[2*which],idj=Focus[2*which+1],i=byid[idi],j=byid[idj];const auto dx=Posc[i]-Posc[j];const double r=sqrt(Dot(dx,dx));Need(r>0&&Finite(r),"Coincident pair geometry");const auto n=dx/r,dv=TDouble3(double(Velrhopc[i].x)-Velrhopc[j].x,double(Velrhopc[i].y)-Velrhopc[j].y,double(Velrhopc[i].z)-Velrhopc[j].z);const double rdot=Dot(dv,n);const auto vt=dv-n*rdot;const double tangent=Dot(vt,vt),curve=tangent/r,normal=Dot(n,(out.ace[idi]+gravity)-(out.ace[idj]+gravity));out.pairNormal[which]=normal;out.pairRddot[which]=normal+curve;pairs<<calls<<','<<base->part<<','<<TimeStep<<','<<TimeStep-releaseTime<<','<<unsigned(Nstep)<<','<<modes[mode]<<','<<idi<<','<<idj<<','<<r<<','<<n.x<<','<<n.y<<','<<n.z<<','<<dv.x<<','<<dv.y<<','<<dv.z<<','<<rdot<<','<<tangent<<','<<curve<<','<<normal<<','<<normal+curve<<','<<(mode?normal-responses[0].pairNormal[which]:0.)<<','<<(mode?normal+curve-responses[0].pairRddot[which]:0.)<<','<<Dot(n,idealDa[idi]-idealDa[idj])<<','<<Dot(n,committedDa[idi]-committedDa[idj])<<'\n';pairRows++;}
            Need(TimeStep==base->time&&unsigned(Nstep)==base->completed,"Zero-step force advanced actual clock");PosInteraction_Forces();cleanup=false;
          }catch(...){armed=false;candidate=false;if(cleanup)PosInteraction_Forces();throw;}
        }
        Need(!armed&&!candidate&&ArtificialStress&&Visco==.1f&&!Acec&&!Rsigmac&&!ArtificialStressc&&!BoundDerivativeVelc,"Operator flags/scratch were not restored");SoilUnchanged(*base);if(!mode){Manufactured(manufactures,base->part);SoilUnchanged(*base);}responses.push_back(std::move(out));CopySaved(*base);for(unsigned q=Npb;q<Np;q++){const unsigned id=Idpc[q];PorePressRatec[q]=responses[0].rate[id];Need(Bits(PorePressRatec[q],responses[0].rate[id]),"Baseline actual Rate bits not restored");restoreRateChecks++;}SoilUnchanged(*base);
        callsCsv<<calls<<','<<base->part<<','<<TimeStep<<','<<TimeStep-releaseTime<<','<<unsigned(Nstep)<<','<<modes[mode]<<','<<1<<','<<double(ArtificialStressCoef)<<','<<double(ArtificialStressExp)<<','<<double(Visco)<<','<<Soil<<','<<savedFS<<','<<changedFS<<','<<maxRate<<','<<dt<<','<<bound<<','<<forceDt<<','<<wave<<','<<pore<<','<<gradientDt<<','<<SymplecticDtPre<<','<<double(DtMin)<<','<<AceMax<<','<<VelMax<<','<<ViscDtMax<<",1,1\n";damping<<calls<<','<<base->part<<','<<TimeStep<<','<<TimeStep-releaseTime<<','<<modes[mode]<<','<<(mode?Alpha:0.);StatsWrite(damping,last);damping<<'\n';for(auto* f:{&soil,&focus,&pairs,&damping,&manufactures,&callsCsv}){f->flush();Need(bool(*f),"Complete force CSV write failed");}
      }
    }
    Need(calls==4&&soilRows==20000&&focusRows==16&&pairRows==8&&restoreRateChecks==20000&&unchangedDerivativeChecks==10000&&hookOff==2&&hookOn==2,"Exact OFF/ON independent-restore coverage differs");std::ofstream done(pathfs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_c08_residual_visc_cpu_r2\",\"passed\":true,\"source_parts\":[13,14],\"focus_IDs\":[7011,7012,6230,6231],\"source_release_time_s\":"<<releaseTime<<",\"native_IDs\":6805,\"soil\":5000,\"fixed\":1805,\"actual_ct_calls\":4,\"actual_Darcy_calls\":4,\"call_rows\":4,\"pair_rows\":8,\"focus_rows\":16,\"soil_force_rows\":20000,\"baseline_rate_restore_bits_checks\":20000,\"actual_DtVariable_false_calls\":4,\"ON_Rsigma_theta_C_FS_bits_checks\":10000,\"hook_OFF_calls\":2,\"hook_ON_calls\":2,\"manufactured_rows\":6,\"alpha\":0.1,\"physical_steps\":0,\"material_return_calls\":0,\"filter_calls\":0,\"actual_force_includes_all_neighbors_and_wall_response\":true,\"all5000_soil_primary_bits_preserved_each_call\":true,\"hook_before_original_Darcy_wrapper\":true,\"extra_Darcy_calls\":0,\"ViscDtMax_altered_by_candidate\":false,\"candidate_frozen_damping_bound_checked_separately\":true,\"soil_only_matched_eta0_LS\":true,\"unregularized_rank_checked\":true,\"node_skip_or_regularization\":false,\"final_once_pernode_float_commit\":true,\"double_force_and_float_commit_budgets_separate\":true,\"actual_C_theta_stressrate_exported\":true,\"numerical_damping_not_GNOG\":true,\"original_GPU_bit_replay\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");

  }
};
void C08ResidualViscosityApply(JSphCpuSingle* p){static_cast<Probe*>(p)->Apply();}
int main(int argc,char** argv){try{
  Need(argc>=9&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--snapshot","Use --check --snapshot CLOSED_CAUSAL90_NATIVE -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 EXISTING_CAUSAL_SEED FRESH_OUT");const pathfs::path folder=pathfs::absolute(argv[3]),tests=pathfs::path(__FILE__).parent_path().parent_path();Need(pathfs::equivalent(folder,tests/"outputs/upl_c08_causal_window_GPU_r1/native"),"Only actual passed total-AS/n3 causal90 is admitted");Snapshot first(folder,Parts[0]),second(folder,Parts[1]);AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!pathfs::exists(cfg.DirOut),"Fresh CPU component output required; certified PRE contract stays legal");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr(),first,second);return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Frozen residual-viscosity candidate failed; preserve first result\n";return 2;}}

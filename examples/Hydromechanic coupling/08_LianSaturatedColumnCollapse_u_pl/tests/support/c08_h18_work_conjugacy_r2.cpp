// Author-only actual-CPU zero-step work-conjugacy audit; no time or material update.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsFixedDt.h"
#include "JCellDivCpuSingle.h"
#include "JCellSearch_inline.h"
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
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("C08H18WorkConjugacy","r1","14-11-2026");
namespace pf=std::filesystem;
static constexpr unsigned Original=7060,Total=6805,Fixed=1805,Soil=5000,Samples=301;
static constexpr unsigned Parts[4]={38,76,92,300},Steps[4]={2076001,2152001,2184001,2600000};
static const char* Terms[7]={"compression","LP","Taylor_pressure","Da","FS_Ace_Lx","chain_pressure","chain_Ace"};
static const char* Groups[3]={"all","fluid_donors","fixed_donors"};
static_assert(sizeof(unsigned)==4&&sizeof(tfloat3)==12&&sizeof(tdouble3)==24&&sizeof(tsymatrix3d)==48,"Original typed22 ABI required");
static void Need(bool x,const std::string& s){if(!x)throw std::runtime_error(s);}
static std::string Detail(const char* label,unsigned part,unsigned id,double actual,double reference,double budget){std::ostringstream s;s<<std::setprecision(17)<<label<<" part="<<part<<" ID="<<id<<" actual="<<actual<<" reference="<<reference<<" budget="<<budget;return s.str();}
template<class T>static bool Bits(const T& a,const T& b){return !memcmp(&a,&b,sizeof(T));}
static bool Finite(float x){return std::isfinite(x);}static bool Finite(double x){return std::isfinite(x);}static bool Finite(unsigned){return true;}
static bool Finite(tfloat3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}static bool Finite(tdouble3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static tdouble3 Abs(tdouble3 a){return TDouble3(fabs(a.x),fabs(a.y),fabs(a.z));}
static tdouble3 Product(tmatrix3d c,tdouble3 g){return TDouble3(c.a11*g.x+c.a12*g.y+c.a13*g.z,c.a21*g.x+c.a22*g.y+c.a23*g.z,c.a31*g.x+c.a32*g.y+c.a33*g.z);}
static double RoundoffGamma(unsigned n){const double u=.5*DBL_EPSILON,t=n*u;Need(t<1,"Invalid arithmetic operation count");return t/(1-t);}
struct Stamp{pf::path p;std::uintmax_t bytes;pf::file_time_type time;explicit Stamp(pf::path q):p(q),bytes(pf::file_size(q)),time(pf::last_write_time(q)){}void Check()const{Need(pf::file_size(p)==bytes&&pf::last_write_time(p)==time,"Protected file changed: "+p.string());}};
template<class T>static std::vector<T> ReadArray(std::ifstream& f){std::vector<T> v(Total);f.read(reinterpret_cast<char*>(v.data()),sizeof(T)*Total);Need(bool(f),"Truncated native array");for(const auto& x:v)Need(Finite(x),"Nonfinite native array");return v;}
struct Snapshot{
  unsigned part,completed;double time;std::vector<unsigned> id,fs,byid;
  std::vector<tdouble3> pos,sk,si;std::vector<tfloat3> vel,legacykk,legacyij,normal,load;
  std::vector<float> rhop,kap,p,p0,excess,posdiv;std::vector<double> j,n,theta,volume,rho,k;
  Snapshot(const pf::path& folder,unsigned which):part(Parts[which]),completed(Steps[which]),byid(Original,UINT_MAX){
    std::ifstream clocks(folder/"clocks.csv");std::string line;Need(bool(std::getline(clocks,line)),"Missing native clocks");unsigned rows=0;bool found=false;
    while(std::getline(clocks,line)){std::stringstream ss(line);std::vector<std::string> c;std::string x;while(std::getline(ss,x,','))c.push_back(x);Need(c.size()==11,"Native clock layout differs");if(std::stoul(c[0])==part){Need(!found&&std::stoul(c[4])==completed,"Completed-step clock differs");time=std::stod(c[2]);found=true;}rows++;}Need(found&&rows==Samples,"Native full301 clock coverage differs");
    std::ifstream f(folder/"typed22.bin",std::ios::binary);unsigned h[3]={};f.read(reinterpret_cast<char*>(h),12);const std::uintmax_t stride=8+std::uintmax_t(Total)*212;
    Need(bool(f)&&h[0]==Total&&h[1]==22&&h[2]==Samples&&pf::file_size(folder/"typed22.bin")==12+Samples*stride,"Original full301/6805/22 extent differs");f.seekg(std::streamoff(12+part*stride));double nativeTime;f.read(reinterpret_cast<char*>(&nativeTime),8);Need(bool(f)&&Bits(time,nativeTime),"Actual native/CSV clock differs");
    id=ReadArray<unsigned>(f);pos=ReadArray<tdouble3>(f);vel=ReadArray<tfloat3>(f);legacykk=ReadArray<tfloat3>(f);legacyij=ReadArray<tfloat3>(f);normal=ReadArray<tfloat3>(f);load=ReadArray<tfloat3>(f);
    rhop=ReadArray<float>(f);kap=ReadArray<float>(f);p=ReadArray<float>(f);p0=ReadArray<float>(f);excess=ReadArray<float>(f);sk=ReadArray<tdouble3>(f);si=ReadArray<tdouble3>(f);fs=ReadArray<unsigned>(f);
    j=ReadArray<double>(f);n=ReadArray<double>(f);theta=ReadArray<double>(f);volume=ReadArray<double>(f);rho=ReadArray<double>(f);k=ReadArray<double>(f);posdiv=ReadArray<float>(f);
    unsigned fixed=0,soil=0;for(unsigned q=0;q<Total;q++){const unsigned a=id[q];Need(a<Original&&byid[a]==UINT_MAX&&(a<Fixed||a>=2060),"Unexpected/duplicate/retired bedroles native ID");byid[a]=q;if(a<Fixed)fixed++;else{soil++;Need(kap[q]>=0&&j[q]>1.-double(.35f)&&n[q]>0&&n[q]<1&&rho[q]>0&&k[q]>0,"Invalid native soil ledger");if(fs[q]==2||fs[q]==3)Need(p[q]<=0,"Saved FS2/3 pressure is positive");}}Need(fixed==Fixed&&soil==Soil,"Native bedroles ownership differs");
  }
};
void GetStrainSpinRateTensor_sym(tfloat3,tfloat3,tfloat3,tsymatrix3f&,tfloat3&);
void GetStressRateTensor_Elastic(tsymatrix3f,tfloat3,tsymatrix3f,const float,const float,tsymatrix3f&);
class Probe:public JSphCpuSingle{
  std::vector<typecode> code;std::vector<tfloat3> wallnormal;std::vector<byte> slip;
  std::vector<unsigned> Map()const{Need(Np==Total&&Npb==Fixed&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Completed released allocation differs");std::vector<unsigned> b(Original,UINT_MAX);unsigned soil=0,fixed=0;for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(id<Original&&b[id]==UINT_MAX&&CODE_IsNormal(Codec[q]),"Changed/duplicate ID");b[id]=q;if(id>=2060){Need(q>=Npb&&CODE_IsFluid(Codec[q]),"Soil role differs");soil++;}else{Need(id<Fixed&&q<Npb&&CODE_IsFixed(Codec[q]),"Fixed bedroles role differs");fixed++;}}Need(soil==Soil&&fixed==Fixed,"Released ID counts differ");return b;}
  void Roles()const{for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(Bits(Codec[q],code[id]),"ID-owned code changed");if(q<Npb)Need(Bits(BoundNormalc[q],wallnormal[id])&&Bits(BoundSlipModec[q],slip[id]),"ID-owned wall normal/slip changed");}}
  void Copy(const Snapshot& a){for(unsigned q=0;q<Np;q++){const unsigned s=a.byid[Idpc[q]];Need(s!=UINT_MAX,"Restore ID differs");Posc[q]=a.pos[s];Velrhopc[q]=TFloat4(a.vel[s].x,a.vel[s].y,a.vel[s].z,a.rhop[s]);const auto kk=a.sk[s],ij=a.si[s];Sigmac[q]=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);Kplasticc[q]=a.kap[s];PorePressc[q]=a.p[s];PorePress0c[q]=a.p0[s];PoroJc[q]=a.j[s];PoroThetac[q]=a.theta[s];FSTypec[q]=a.fs[s];FSNormalc[q]=a.normal[s];PosDivc[q]=a.posdiv[s];HydroMechLoadAcec[q]=a.load[s];}}
  void Ledger(const Snapshot& a)const{for(unsigned q=Npb;q<Np;q++){const unsigned s=a.byid[Idpc[q]];double n,v,rho;GetPorosityFeedbackStateCpu(q,n,v,rho);const double k=GetDynamicConductivityCpu(q);Need(Bits(n,a.n[s])&&Bits(v,a.volume[s])&&Bits(rho,a.rho[s])&&Bits(k,a.k[s])&&Bits(float(rho),a.rhop[s]),"Native J/n/V/rho/k/cache ledger differs");}}
  void Unchanged(const Snapshot& a)const{for(unsigned q=Npb;q<Np;q++){const unsigned s=a.byid[Idpc[q]];const tfloat4 v=TFloat4(a.vel[s].x,a.vel[s].y,a.vel[s].z,a.rhop[s]);const auto kk=a.sk[s],ij=a.si[s];const auto sigma=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);Need(Bits(Posc[q],a.pos[s])&&Bits(Velrhopc[q],v)&&Bits(Sigmac[q],sigma)&&Bits(Kplasticc[q],a.kap[s])&&Bits(PorePressc[q],a.p[s])&&Bits(PorePress0c[q],a.p0[s])&&Bits(PoroJc[q],a.j[s]),"Force changed soil primary state");}Roles();Ledger(a);Need(Bits(TimeStep,a.time)&&unsigned(Nstep)==a.completed&&!PosPrec&&!PoroJPrec,"Zero-step clock/state advanced");}
  void Restore(const Snapshot& a){Need(!Acec&&!Rsigmac&&!BoundDerivativeVelc&&!ArtificialStressc,"Previous force scratch owned");Map();Copy(a);LoadDcellParticles(Np,Codec,Posc,Dcellc);const bool free=HydroMechFreeSeepage,shep=PoreShepardRegularization;HydroMechFreeSeepage=PoreShepardRegularization=false;try{BoundChanged=true;RunCellDivide(false);}catch(...){HydroMechFreeSeepage=free;PoreShepardRegularization=shep;throw;}HydroMechFreeSeepage=free;PoreShepardRegularization=shep;Need(!CellDivSingle->GetNpbOut()&&!CellDivSingle->GetNpfOut()&&!CellDivSingle->GetNpbOutIgnore()&&!CellDivSingle->GetNpfOutIgnore(),"Cell rebuild excluded a particle");Map();Copy(a);Roles();Ledger(a);TimeStep=a.time;Nstep=a.completed;Unchanged(a);}
// New diagnostics below the unchanged, sealed pair-tool loader/restore prefix.
  struct Mat{double a[3][3]={{0,0,0},{0,0,0},{0,0,0}};};
  struct Sum{double value=0,absolute=0;unsigned n=0;void Add(double x){Need(Finite(x),"Nonfinite work term");value+=x;absolute+=fabs(x);n++;}double Budget()const{return RoundoffGamma(8*n+64)*absolute;}};
  struct Row{
    Mat raw,physical,corrected;std::array<tfloat3,3> literal{{TFloat3(0),TFloat3(0),TFloat3(0)}};
    tfloat3 force=TFloat3(0);tsymatrix3f rate={0,0,0,0,0,0};
    tdouble3 total=TDouble3(0),art=TDouble3(0),av=TDouble3(0),absolute=TDouble3(0);
    double theta=0,thetaAbs=0,gradientAbs=0,port=0;unsigned donors=0;
  };
  struct Edge{unsigned i,j;tdouble3 g;double vi,vj;};
  static double Trace(const Mat& a){return a.a[0][0]+a.a[1][1]+a.a[2][2];}
  static Mat Correct(const Mat& a,const tmatrix3d& c){Mat b;for(unsigned r=0;r<3;r++){const auto q=Product(c,TDouble3(a.a[r][0],a.a[r][1],a.a[r][2]));b.a[r][0]=q.x;b.a[r][1]=q.y;b.a[r][2]=q.z;}return b;}
  static tfloat3 CorrectFloat(const tfloat3& g,const tmatrix3d& c){return TFloat3(float(double(g.x)*c.a11+double(g.y)*c.a12+double(g.z)*c.a13),float(double(g.x)*c.a21+double(g.y)*c.a22+double(g.z)*c.a23),float(double(g.x)*c.a31+double(g.y)*c.a32+double(g.z)*c.a33));}
  static tsymatrix3d TotalStress(tsymatrix3d s,float p){const auto f=ToTSymMatrix3f(s);return TSymMatrix3d(double(f.xx)-p,double(f.xy),double(f.xz),double(f.yy)-p,double(f.yz),double(f.zz)-p);}
  static tdouble3 Mul(tsymatrix3d s,tdouble3 g){return TDouble3(s.xx*g.x+s.xy*g.y+s.xz*g.z,s.xy*g.x+s.yy*g.y+s.yz*g.z,s.xz*g.x+s.yz*g.y+s.zz*g.z);}
  static double Contract(tsymatrix3d s,const Mat& l){return s.xx*l.a[0][0]+s.yy*l.a[1][1]+s.zz*l.a[2][2]+s.xy*(l.a[0][1]+l.a[1][0])+s.xz*(l.a[0][2]+l.a[2][0])+s.yz*(l.a[1][2]+l.a[2][1]);}
  static void WriteMat(std::ostream& f,const Mat& a){for(const auto& row:a.a)for(double x:row)f<<','<<x;}
  static void AddFloat(tfloat3& a,tdouble3 b){a.x+=float(b.x);a.y+=float(b.y);a.z+=float(b.z);}
  static void Rate(const std::array<tfloat3,3>& l,tsymatrix3f sigma,float k,float g,tsymatrix3f& r){
    // These are original external CPU symbols from the retained JSphCpu object, not new constitutive code.
    tsymatrix3f e={0,0,0,0,0,0};tfloat3 w=TFloat3(0);
    GetStrainSpinRateTensor_sym(l[0],l[1],l[2],e,w);GetStressRateTensor_Elastic(e,w,sigma,k,g,r);
  }
  Row Assemble(unsigned i,bool boundary,std::vector<Edge>& edges)const{
    Row r;const auto vi=TDouble3(Velrhopc[i].x,Velrhopc[i].y,Velrhopc[i].z);const auto ti=TotalStress(Sigmac[i],PorePressc[i]);
    double ni,volumei,rhoi;GetPorosityFeedbackStateCpu(i,ni,volumei,rhoi);const double v0=double(MassFluid)/double(RhopZero);const auto ci=CorrMatc[i];
    const float wdp=fsph::GetKernel_Wab<KERNEL_Wendland>(CSP,float(Dp*Dp)),inv=1.f/wdp;Need(wdp>0,"Original AS reference kernel invalid");
    const StNgSearch ngs=nsearch::Init(Dcellc[i],boundary,DivData);
    for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){
      const tuint2 range=nsearch::ParticleRange(y,z,ngs,DivData);
      for(unsigned j=range.x;j<range.y;j++){
        Need((boundary&&j<Npb&&CODE_IsFixed(Codec[j]))||(!boundary&&j>=Npb&&CODE_IsFluid(Codec[j])),"Unexpected actual cell donor role");
        const float dx=float(Posc[i].x-Posc[j].x),dy=float(Posc[i].y-Posc[j].y),dz=float(Posc[i].z-Posc[j].z),rr2=dx*dx+dy*dy+dz*dz;
        if(rr2>KernelSize2||rr2<ALMOSTZERO)continue;
        const TpSlipMode slipmode=(boundary&&BoundSlipModec? TpSlipMode(BoundSlipModec[j]):SlipMode);const bool mdbc=(boundary&&TBoundary==BC_MDBC&&slipmode>=SLIP_NoSlip);
        if(mdbc&&BoundModec&&BoundModec[j]==BMODE_MDBC2OFF)continue;
        Need(PoroJc[j]>1.-double(SoilCte.Porosity),"Actual force donor J invalid");r.donors++;
        const double vj=v0*PoroJc[j],rhoj=double(SoilCte.PoreWaterRho)+(double(RhopZero)-double(SoilCte.PoreWaterRho))/PoroJc[j];
        float fac=0;const float wab=fsph::GetKernel_WabFac<KERNEL_Wendland>(CSP,rr2,fac),gx=fac*dx,gy=fac*dy,gz=fac*dz;const auto g=TDouble3(gx,gy,gz);
        if(!boundary)edges.push_back({Idpc[i],Idpc[j],g,volumei,vj});
        const auto vbase=TDouble3(Velrhopc[j].x,Velrhopc[j].y,Velrhopc[j].z);
        const auto vder=(boundary&&BoundDerivativeVelc? ToTDouble3(BoundDerivativeVelc[j]):vbase);
        const auto vvis=(mdbc&&TangenVelc?ToTDouble3(TangenVelc[j]):vbase);
        const auto vreal=(boundary?TDouble3(0):vbase);const double cg[3]={g.x,g.y,g.z},dd[3]={vder.x-vi.x,vder.y-vi.y,vder.z-vi.z},dr[3]={vreal.x-vi.x,vreal.y-vi.y,vreal.z-vi.z};
        // Independent double adjoint shadows use exact differences of stored float velocities.
        for(unsigned a=0;a<3;a++)for(unsigned b=0;b<3;b++){r.raw.a[a][b]+=vj*dd[a]*cg[b];r.physical.a[a][b]+=vj*dr[a]*cg[b];}
        const float dvx=float(vi.x)-float(vder.x),dvy=float(vi.y)-float(vder.y),dvz=float(vi.z)-float(vder.z),volume=-float(vj);const float dv[3]={dvx,dvy,dvz};
        for(unsigned a=0;a<3;a++){const float d=dv[a]*volume;r.literal[a].x+=d*gx;r.literal[a].y+=d*gy;r.literal[a].z+=d*gz;r.gradientAbs+=fabs(double(d)*gx)+fabs(double(d)*gy)+fabs(double(d)*gz);}
        const double px=dx,py=(Simulate2D?0:double(dy)),pz=dz,prr2=px*px+py*py+pz*pz;
        if(prr2<=double(KernelSize2)&&prr2>=ALMOSTZERO){const double pfac=double(fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(prr2)));const auto pg=TDouble3(pfac*px,Simulate2D?0:pfac*py,pfac*pz);const auto pcg=(PoreCompressionGradCorr?Product(ci,pg):pg);const double theta=vj*(-double(dvx)*pcg.x+(Simulate2D?0:-double(dvy)*pcg.y)-double(dvz)*pcg.z);r.theta+=theta;r.thetaAbs+=fabs(theta);}
        const auto sf=ToTSymMatrix3f(Sigmac[i]),sj=ToTSymMatrix3f(Sigmac[j]);const double pw=double(PorePressc[i])+double(PorePressc[j]),c=vj/rhoi;
        const double xx=double(sf.xx)+sj.xx-pw,yy=double(sf.yy)+sj.yy-pw,zz=double(sf.zz)+sj.zz-pw,xy=double(sf.xy)+sj.xy,xz=double(sf.xz)+sj.xz,yz=double(sf.yz)+sj.yz;
        const auto at=TDouble3(c*(xx*gx+xy*gy+xz*gz),c*(yy*gy+xy*gx+yz*gz),c*(zz*gz+yz*gy+xz*gx));AddFloat(r.force,at);r.total=r.total+at;r.absolute=r.absolute+Abs(at);
        const auto ar=ArtificialStressc[i],br=ArtificialStressc[j];const double axx=double(ar.xx)+br.xx,ayy=double(ar.yy)+br.yy,azz=double(ar.zz)+br.zz,axy=double(ar.xy)+br.xy,axz=double(ar.xz)+br.xz,ayz=double(ar.yz)+br.yz;const float ratio=wab*inv;
        if(ratio>0.f&&(axx||ayy||azz||axy||axz||ayz)){const double m=vj/rhoi*double(powf(ratio,ArtificialStressExp));const double a=m*axx,b=m*ayy,c=m*azz,d=m*axy,e=m*axz,f=m*ayz;const auto aa=TDouble3(a*gx+d*gy+e*gz,b*gy+d*gx+f*gz,c*gz+f*gy+e*gx);AddFloat(r.force,aa);r.art=r.art+aa;r.absolute=r.absolute+Abs(aa);}
        const float vx=float(vi.x)-float(vvis.x),vy=float(vi.y)-float(vvis.y),vz=float(vi.z)-float(vvis.z),dot=dx*vx+dy*vy+dz*vz;
        if(dot<0){const float dotrr=dot/(rr2+Eta2),mu=KernelH*dotrr,cbar=float(Cs0),avcoef=(boundary?Visco*ViscoBoundFactor:Visco);const double rhobar=(rhoi+rhoj)*.5,mass=vj*rhoj,pi=(-double(avcoef)*double(cbar)*double(mu)/rhobar)*mass;const auto va=TDouble3(pi*double(gx),pi*double(gy),pi*double(gz));r.force.x-=float(va.x);r.force.y-=float(va.y);r.force.z-=float(va.z);r.av=r.av-va;r.absolute=r.absolute+Abs(va);}
        if(boundary)r.port+=volumei*vj*(Dot(vi,Mul(TotalStress(Sigmac[j],PorePressc[j]),g))+Dot(vder,Mul(ti,g)));
      }
    }
    r.corrected=Correct(r.raw,ci);for(auto& a:r.literal)a=CorrectFloat(a,ci);Rate(r.literal,ToTSymMatrix3f(Sigmac[i]),SoilCte.ModulusK,SoilCte.ModulusG,r.rate);return r;
  }
  void Virtual(unsigned part,const std::vector<Edge>& edges,std::ostream& out)const{
    const auto byid=Map();std::vector<double> nearest(Original,std::numeric_limits<double>::infinity());std::vector<byte> interior(Original,0);
    for(const auto& e:edges){const auto dr=Posc[byid[e.i]]-Posc[byid[e.j]];nearest[e.i]=(std::min)(nearest[e.i],sqrt(Dot(dr,dr)));}
    for(unsigned i=Npb;i<Np;i++){interior[Idpc[i]]=1;for(unsigned j=0;j<Npb;j++){const auto d=Posc[i]-Posc[j];if(Dot(d,d)<4*double(KernelH)*KernelH){interior[Idpc[i]]=0;break;}}}
    // Predeclared healthy comparator: lexicographically first interior edge in[.9,1.1]dp,
    // with neither endpoint's nearest-soil distance below .85dp. Selection never uses power/error.
    std::array<unsigned,2> healthy{{UINT_MAX,UINT_MAX}};
    for(const auto& e:edges)if(e.i<e.j&&interior[e.i]&&interior[e.j]&&nearest[e.i]>=.85*Dp&&nearest[e.j]>=.85*Dp){
      const auto xi=Posc[byid[e.i]],xj=Posc[byid[e.j]],d=xi-xj;const double distance=sqrt(Dot(d,d));
      if(distance<.9*Dp||distance>1.1*Dp)continue;
      if(std::array<unsigned,2>{{e.i,e.j}}<healthy)healthy={{e.i,e.j}};
    }
    Need(healthy[0]!=UINT_MAX,"Predeclared healthy virtual comparator unavailable; preserve diagnostic instead of substituting a fitted pair");
    const std::array<std::array<unsigned,2>,3> pairs{{{{6767,6865}},{{4953,4954}},healthy}};
    for(unsigned probe=0;probe<4;probe++){
      std::vector<tdouble3> u(Original,TDouble3(0));double distance=0;unsigned first=UINT_MAX,second=UINT_MAX;
      if(probe==3){for(unsigned q=Npb;q<Np;q++)u[Idpc[q]]=TDouble3(1,0,0);}else{first=pairs[probe][0];second=pairs[probe][1];const auto dr=Posc[byid[first]]-Posc[byid[second]];distance=sqrt(Dot(dr,dr));Need(distance>0,"Coincident virtual pair");u[first]=dr*(.5/distance);u[second]=dr*(-.5/distance);}
      std::vector<Mat> raw(Original);Sum power,rawWork,correctedWork,unorm,braw,bcorrect,thetaRaw,thetaCorrect;
      for(const auto& e:edges){const auto du=u[e.j]-u[e.i];const double d[3]={du.x,du.y,du.z},g[3]={e.g.x,e.g.y,e.g.z};for(unsigned a=0;a<3;a++)for(unsigned b=0;b<3;b++)raw[e.i].a[a][b]+=e.vj*d[a]*g[b];const auto ti=TotalStress(Sigmac[byid[e.i]],PorePressc[byid[e.i]]),tj=TotalStress(Sigmac[byid[e.j]],PorePressc[byid[e.j]]);power.Add(e.vi*e.vj*Dot(u[e.i],Mul(ti,e.g)+Mul(tj,e.g)));}
      for(unsigned q=Npb;q<Np;q++){const unsigned id=Idpc[q];double n,V,rho;GetPorosityFeedbackStateCpu(q,n,V,rho);const auto c=Correct(raw[id],CorrMatc[q]);const auto ti=TotalStress(Sigmac[q],PorePressc[q]);rawWork.Add(V*Contract(ti,raw[id]));correctedWork.Add(V*Contract(ti,c));unorm.Add(V*Dot(u[id],u[id]));double nr=0,nc=0;for(unsigned a=0;a<3;a++)for(unsigned b=0;b<3;b++){const double r=.5*(raw[id].a[a][b]+raw[id].a[b][a]),t=.5*(c.a[a][b]+c.a[b][a]);nr+=r*r;nc+=t*t;}braw.Add(V*nr);bcorrect.Add(V*nc);thetaRaw.Add(V*Trace(raw[id])*Trace(raw[id]));thetaCorrect.Add(V*Trace(c)*Trace(c));}
      const double residual=power.value+rawWork.value,budget=power.Budget()+rawWork.Budget()+RoundoffGamma(128*unsigned(edges.size())+128)*(power.absolute+rawWork.absolute);Need(fabs(residual)<=budget,"Virtual raw soil adjoint exceeds arithmetic budget");
      out<<part<<','<<(probe==0?"pair6767_6865":probe==1?"pair4953_4954":probe==2?"healthy_pair":"translation_x")<<','<<first<<','<<second<<','<<distance<<','<<edges.size()<<','<<power.value<<','<<rawWork.value<<','<<correctedWork.value<<','<<correctedWork.value-rawWork.value<<','<<residual<<','<<budget<<','<<sqrt(unorm.value)<<','<<sqrt(braw.value)<<','<<sqrt(bcorrect.value)<<','<<sqrt(thetaRaw.value)<<','<<sqrt(thetaCorrect.value)<<','<<(unorm.value>0?sqrt(braw.value/unorm.value):0)<<','<<(unorm.value>0?sqrt(bcorrect.value/unorm.value):0)<<",1,0\n";
    }
  }
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,const std::array<Snapshot,4>& states){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();RunGravityPreloadHandoffCpu();FreePartsInit();
    Need(IsGravityPreloadHandoff()&&GravityPreload&&!GravityPreloadElasticSource&&!GravityPreloadReleased&&unsigned(Nstep)==2000000&&!GravityPreloadKeepBedOverlap&&GravityPreloadBedIds.empty(),"Original schema2/bed-last handoff required");RunGravityPreloadRelease();Map();
    Need(GravityPreloadReleased&&GravityPreloadActualStep==2000000&&GravityPreloadIdBegin==1805&&GravityPreloadIdCount==255&&DynamicPorePressure&&PorosityFeedback&&DynamicPoreWall&&DynamicPoreConductivity&&DynamicPoreConductivityCk==2.&&HydroMechFreeSeepage&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilDamping&&!PoreShepardRegularization,"Original released controls differ");
    Need(Simulate2D&&!Symmetry&&!PeriActive&&OmpThreads==1&&TKernel==KERNEL_Wendland&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundSlipModec&&SoilStressRateGradCorr&&!SoilBoundaryDerivativeSPR&&!HourglassCpu&&!SoilHourglassXi&&!WithFloating&&!UseDEM&&!AccInput&&!Shifting&&!Damping&&TDensity==DDT_None&&NoPenetration&&TMdbc2==MDBC2_NoPen&&UseDynamicPorePlaneContact(),"Original current scope differs");
    Need(ArtificialStress&&ArtificialStressCoef==.3f&&ArtificialStressExp==2.55f&&TVisco==VISCO_Artificial&&Visco==.1f&&!ViscoTime&&Dp==.04&&KernelH==.072f&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==.0002f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&Gravity==TFloat3(0,0,-9.81f)&&FixedDt&&FixedDt->GetFixedValue()==.000005&&SymplecticDtPre==.000005,"Exact original AS03/Wendland/5us context required");
    code.resize(Original);wallnormal.resize(Original);slip.resize(Original);for(unsigned q=0;q<Np;q++){code[Idpc[q]]=Codec[q];if(q<Npb){wallnormal[Idpc[q]]=BoundNormalc[q];slip[Idpc[q]]=BoundSlipModec[q];}}Roles();const double release=GravityPreloadActualTime;
    std::ofstream soil(pf::path(cfg->DirOut)/"soil.csv"),groups(pf::path(cfg->DirOut)/"groups.csv"),walls(pf::path(cfg->DirOut)/"walls.csv"),summary(pf::path(cfg->DirOut)/"summary.csv"),virtuals(pf::path(cfg->DirOut)/"virtual.csv");for(auto f:{&soil,&groups,&walls,&summary,&virtuals})*f<<std::setprecision(17);
    soil<<"part,time_s,tau_s,completed_step,id,x,y,z,vx,vy,vz,p,P0,J,kappa,rho,V,m,FSsaved,FSfresh,C11,C12,C13,C21,C22,C23,C31,C32,C33,sigma_xx,sigma_yy,sigma_zz,sigma_xy,sigma_yz,sigma_xz,Rsigma_xx,Rsigma_yy,Rsigma_zz,Rsigma_xy,Rsigma_yz,Rsigma_xz,trace_Rsigma,theta,theta_literal,theta_error,theta_budget,rate_error_max,rate_budget,Ace_x,Ace_y,Ace_z,literal_Ace_x,literal_Ace_y,literal_Ace_z,force_error_max,force_budget,raw_L11,raw_L12,raw_L13,raw_L21,raw_L22,raw_L23,raw_L31,raw_L32,raw_L33,C_L11,C_L12,C_L13,C_L21,C_L22,C_L23,C_L31,C_L32,C_L33,force_bits_equal,rate_bits_equal\n";
    groups<<"part,time_s,id,donor_group,donors,P_total_stress_double,Iraw_derivative,Iraw_physical,IC_derivative,G1_minus_raw,P_AS_double,P_AV_double,ghost_port_expected,stress_Ace_x,stress_Ace_y,stress_Ace_z,AS_Ace_x,AS_Ace_y,AS_Ace_z,AV_Ace_x,AV_Ace_y,AV_Ace_z,raw_L11,raw_L12,raw_L13,raw_L21,raw_L22,raw_L23,raw_L31,raw_L32,raw_L33,C_L11,C_L12,C_L13,C_L21,C_L22,C_L23,C_L31,C_L32,C_L33\n";
    walls<<"part,time_s,id,slip,mode,x,z,vghost_x,vghost_y,vghost_z,vderiv_x,vderiv_y,vderiv_z,vvisc_x,vvisc_y,vvisc_z,motion_x,motion_y,motion_z,p,P0,J,sigma_xx,sigma_yy,sigma_zz,sigma_xy,sigma_yz,sigma_xz\n";
    summary<<"part,time_s,tau_s,group,receivers,directed_donors,P_stress,Iraw,IC,G1_gap,raw_closure_or_wall_port_residual,arithmetic_budget,P_AS,P_AV,P_gravity,m_sum,mdot_proxy,half_mdot_v2_proxy,primary_unchanged\n";
    virtuals<<"part,probe,id_i,id_j,r_m,soil_directed_edges,P_frozen_stress,Iraw,IC,G1_gap,raw_closure_residual,arithmetic_budget,Vnorm_u,Vnorm_symLraw,Vnorm_symLC,Vnorm_traceLraw,Vnorm_traceLC,symLraw_over_u_s_1,symLC_over_u_s_1,soil_only,walls_closed\n";
    unsigned calls=0,soilRows=0,groupRows=0,wallRows=0;double maxForceError=0,maxRateError=0,maxThetaError=0;
    for(const auto& state:states){Restore(state);Unchanged(state);bool cleanup=true;try{
      Interaction_Forces(INTERSTEP_SymCorrector);calls++;Need(Acec&&Rsigmac&&PorePressRatec&&BoundDerivativeVelc&&CorrMatc&&ArtificialStressc&&TangenVelc,"Original actual force scratch incomplete");Unchanged(state);
      std::array<Sum,2> ps,ir,ic,as,av,port;std::array<unsigned,2> donors{{0,0}};Sum gravity,mass,mdot,massPower;std::vector<Edge> edges;
      for(unsigned q=Npb;q<Np;q++){
        const unsigned id=Idpc[q],s=state.byid[id];const auto velocity=TDouble3(Velrhopc[q].x,Velrhopc[q].y,Velrhopc[q].z);const auto stress=Sigmac[q],ti=TotalStress(stress,PorePressc[q]);double n,V,rho;GetPorosityFeedbackStateCpu(q,n,V,rho);const double m=V*rho;const auto c=CorrMatc[q];const Row row[2]={Assemble(q,false,edges),Assemble(q,true,edges)};
        Mat totalRaw,totalC;for(unsigned a=0;a<3;a++)for(unsigned b=0;b<3;b++){totalRaw.a[a][b]=row[0].raw.a[a][b]+row[1].raw.a[a][b];totalC.a[a][b]=row[0].corrected.a[a][b]+row[1].corrected.a[a][b];}
        tfloat3 literal=row[0].force+row[1].force;literal.y=0;const auto err=ToTDouble3(Acec[q])-ToTDouble3(literal);const double error=(std::max)({fabs(err.x),fabs(err.y),fabs(err.z)}),absforce=(std::max)({row[0].absolute.x+row[1].absolute.x,row[0].absolute.y+row[1].absolute.y,row[0].absolute.z+row[1].absolute.z});
        const unsigned count=row[0].donors+row[1].donors;const double u=.5*FLT_EPSILON,gamma=(12.*count+64.)*u/(1.-(12.*count+64.)*u),forceBudget=gamma*absforce+64.*FLT_MIN;Need(Finite(forceBudget)&&error<=forceBudget,Detail("Literal whole-neighbor force",state.part,id,error,0,forceBudget));
        tsymatrix3f r=row[0].rate;const auto t=row[1].rate;r.xx+=t.xx;r.yy+=t.yy;r.zz+=t.zz;r.xy+=t.xy;r.yz+=t.yz;r.xz+=t.xz;const auto actual=Rsigmac[q];Need(Finite(Acec[q])&&Finite(PoroThetac[q]),"Nonfinite actual force or theta");for(float value:{actual.xx,actual.yy,actual.zz,actual.xy,actual.yz,actual.xz,r.xx,r.yy,r.zz,r.xy,r.yz,r.xz})Need(Finite(value),"Nonfinite actual/literal stress rate");const double rateError=(std::max)({fabs(double(r.xx)-actual.xx),fabs(double(r.yy)-actual.yy),fabs(double(r.zz)-actual.zz),fabs(double(r.xy)-actual.xy),fabs(double(r.yz)-actual.yz),fabs(double(r.xz)-actual.xz)});
        const double cNorm=fabs(c.a11)+fabs(c.a12)+fabs(c.a13)+fabs(c.a21)+fabs(c.a22)+fabs(c.a23)+fabs(c.a31)+fabs(c.a32)+fabs(c.a33),sNorm=fabs(stress.xx)+fabs(stress.yy)+fabs(stress.zz)+2*(fabs(stress.xy)+fabs(stress.yz)+fabs(stress.xz)),rateBudget=gamma*(double(SoilCte.ModulusK)+4*double(SoilCte.ModulusG)+4*sNorm)*(row[0].gradientAbs+row[1].gradientAbs)*(1+cNorm)+256.*FLT_MIN;
        Need(Finite(rateBudget)&&rateError<=rateBudget,Detail("Literal corrected stress rate",state.part,id,rateError,0,rateBudget));const double theta=row[0].theta+row[1].theta,thetaError=fabs(theta-PoroThetac[q]),thetaBudget=RoundoffGamma(32*count+128)*(row[0].thetaAbs+row[1].thetaAbs)+64.*DBL_MIN;Need(Finite(thetaBudget)&&thetaError<=thetaBudget,Detail("Original theta row",state.part,id,theta,PoroThetac[q],thetaBudget));
        maxForceError=(std::max)(maxForceError,error);maxRateError=(std::max)(maxRateError,rateError);maxThetaError=(std::max)(maxThetaError,thetaError);
        soil<<state.part<<','<<TimeStep<<','<<TimeStep-release<<','<<unsigned(Nstep)<<','<<id<<','<<Posc[q].x<<','<<Posc[q].y<<','<<Posc[q].z<<','<<velocity.x<<','<<velocity.y<<','<<velocity.z<<','<<PorePressc[q]<<','<<PorePress0c[q]<<','<<PoroJc[q]<<','<<Kplasticc[q]<<','<<rho<<','<<V<<','<<m<<','<<state.fs[s]<<','<<FSTypec[q]<<','<<c.a11<<','<<c.a12<<','<<c.a13<<','<<c.a21<<','<<c.a22<<','<<c.a23<<','<<c.a31<<','<<c.a32<<','<<c.a33<<','<<stress.xx<<','<<stress.yy<<','<<stress.zz<<','<<stress.xy<<','<<stress.yz<<','<<stress.xz<<','<<actual.xx<<','<<actual.yy<<','<<actual.zz<<','<<actual.xy<<','<<actual.yz<<','<<actual.xz<<','<<double(actual.xx)+actual.yy+actual.zz<<','<<PoroThetac[q]<<','<<theta<<','<<thetaError<<','<<thetaBudget<<','<<rateError<<','<<rateBudget<<','<<Acec[q].x<<','<<Acec[q].y<<','<<Acec[q].z<<','<<literal.x<<','<<literal.y<<','<<literal.z<<','<<error<<','<<forceBudget;WriteMat(soil,totalRaw);WriteMat(soil,totalC);soil<<','<<Bits(literal,Acec[q])<<','<<Bits(r,actual)<<'\n';soilRows++;
        for(unsigned g=0;g<2;g++){const auto& a=row[g];const double p=m*Dot(velocity,a.total),raw=V*Contract(ti,a.raw),phys=V*Contract(ti,a.physical),corrected=V*Contract(ti,a.corrected),pa=m*Dot(velocity,a.art),pv=m*Dot(velocity,a.av);ps[g].Add(p);ir[g].Add(raw);ic[g].Add(corrected);as[g].Add(pa);av[g].Add(pv);port[g].Add(a.port);donors[g]+=a.donors;groups<<state.part<<','<<TimeStep<<','<<id<<','<<(g?"wall":"soil")<<','<<a.donors<<','<<p<<','<<raw<<','<<phys<<','<<corrected<<','<<corrected-raw<<','<<pa<<','<<pv<<','<<a.port<<','<<a.total.x<<','<<a.total.y<<','<<a.total.z<<','<<a.art.x<<','<<a.art.y<<','<<a.art.z<<','<<a.av.x<<','<<a.av.y<<','<<a.av.z;WriteMat(groups,a.raw);WriteMat(groups,a.corrected);groups<<'\n';groupRows++;}
        gravity.Add(m*Dot(velocity,ToTDouble3(Gravity)));mass.Add(m);const double dm=double(SoilCte.PoreWaterRho)*V*PoroThetac[q];mdot.Add(dm);massPower.Add(.5*dm*Dot(velocity,velocity));
      }
      for(unsigned q=0;q<Npb;q++){const auto v=Velrhopc[q];const auto d=BoundDerivativeVelc[q],tv=TangenVelc[q],mv=(MotionVelc?MotionVelc[q]:TFloat3(0));Need(mv==TFloat3(0),"Static physical wall moved");const auto s=Sigmac[q];walls<<state.part<<','<<TimeStep<<','<<Idpc[q]<<','<<unsigned(BoundSlipModec[q])<<','<<unsigned(BoundModec[q])<<','<<Posc[q].x<<','<<Posc[q].z<<','<<v.x<<','<<v.y<<','<<v.z<<','<<d.x<<','<<d.y<<','<<d.z<<','<<tv.x<<','<<tv.y<<','<<tv.z<<','<<mv.x<<','<<mv.y<<','<<mv.z<<','<<PorePressc[q]<<','<<PorePress0c[q]<<','<<PoroJc[q]<<','<<s.xx<<','<<s.yy<<','<<s.zz<<','<<s.xy<<','<<s.yz<<','<<s.xz<<'\n';wallRows++;}
      for(unsigned g=0;g<2;g++){const double residual=ps[g].value+ir[g].value-port[g].value,budget=ps[g].Budget()+ir[g].Budget()+port[g].Budget()+RoundoffGamma(128*donors[g]+128)*(ps[g].absolute+ir[g].absolute+port[g].absolute);Need(fabs(residual)<=budget,"Double raw adjoint identity exceeds arithmetic budget");summary<<state.part<<','<<TimeStep<<','<<TimeStep-release<<','<<(g?"wall":"soil")<<','<<Soil<<','<<donors[g]<<','<<ps[g].value<<','<<ir[g].value<<','<<ic[g].value<<','<<ic[g].value-ir[g].value<<','<<residual<<','<<budget<<','<<as[g].value<<','<<av[g].value<<','<<gravity.value<<','<<mass.value<<','<<mdot.value<<','<<massPower.value<<",1\n";}
      Virtual(state.part,edges,virtuals);Unchanged(state);PosInteraction_Forces();cleanup=false;Copy(state);Unchanged(state);for(auto f:{&soil,&groups,&walls,&summary,&virtuals}){f->flush();Need(bool(*f),"Audit CSV failed");}
    }catch(...){if(cleanup)PosInteraction_Forces();throw;}}
    Need(calls==4&&soilRows==20000&&groupRows==40000&&wallRows==7220,"Four-state baseline-only coverage differs");std::ofstream done(pf::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"c08_h18_work_conjugacy_r2\",\"passed\":true,\"source_parts\":[38,76,92,300],\"force_calls\":4,\"soil_rows\":20000,\"group_rows\":40000,\"wall_rows\":7220,\"summary_rows\":8,\"virtual_rows\":16,\"virtual_soil_only\":true,\"virtual_wall_closure\":false,\"max_literal_force_error\":"<<maxForceError<<",\"max_literal_stress_rate_error\":"<<maxRateError<<",\"max_literal_theta_error\":"<<maxThetaError<<",\"all5000_soil_primary_bits_unchanged\":true,\"physical_steps\":0,\"material_steps\":0,\"new_OFF_windows\":0,\"fixed_wall_physical_power\":0,\"mass_and_storage_are_not_fluid_mass\":true,\"raw_adjoint_and_corrected_gap_are_conditional_operator_diagnostics\":true,\"total_energy_closure_asserted\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Audit completion write failed");
  }
};

int main(int argc,char** argv){try{
  Need(argc>=9&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--native","Use --check --native CLOSED_AS03_FULL301 -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 ORIGINAL_AS03_SEED FRESH_OUT");const pf::path tests=pf::path(__FILE__).parent_path().parent_path(),native=pf::absolute(argv[3]),seed=tests/"outputs/c08_h18_as03n255_full3_r1/c08_h18_as03n255_full3_r1",pre=tests/"outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4";Need(pf::equivalent(native,tests/"outputs/c08_h18_as03n255_full3_r1/native_r1"),"Only the existing complete AS03 full301 native is admitted");
  std::vector<Stamp> protectedFiles;for(const char* leaf:{"typed22.bin","typed22_layout.csv","clocks.csv","completion.json","bedkeep_metadata.json"})protectedFiles.emplace_back(native/leaf);for(const char* suffix:{".xml",".bi4","_Normals.nbi4"})protectedFiles.emplace_back(pf::path(seed.string()+suffix));protectedFiles.emplace_back(pre);for(const char* leaf:{"c08_h18_as03n255_full3_r1.run.json","c08_h18_as03n255_full3_r1.call.json","c08_h18_as03n255_full3_native_r1.check.json","c08_h18_as03n255_full3_review_r1.check.json","c08_h18_work_conjugacy_r2.build.json"})protectedFiles.emplace_back(tests/"logs"/leaf);protectedFiles.emplace_back(pf::absolute(argv[0]));
  for(const char* leaf:{"DsphConfig.xml","ChronoEngine.dll","dsphchrono.dll","vcomp140.dll","msvcp140.dll","vcruntime140.dll","vcruntime140_1.dll"})protectedFiles.emplace_back(pf::absolute(argv[0]).parent_path()/leaf);
  const std::array<Snapshot,4> states={Snapshot(native,0),Snapshot(native,1),Snapshot(native,2),Snapshot(native,3)};AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&pf::absolute(cfg.CaseName)==pf::absolute(seed)&&pf::absolute(cfg.DirOut)==pf::absolute(tests/"outputs/c08_h18_work_conjugacy_r2")&&!pf::exists(cfg.DirOut),"Exact AS03 seed and new zero-step output required");AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr(),states);for(const auto& q:protectedFiles)q.Check();return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Fresh zero-step work audit failed; preserve outputs\n";return 2;}}

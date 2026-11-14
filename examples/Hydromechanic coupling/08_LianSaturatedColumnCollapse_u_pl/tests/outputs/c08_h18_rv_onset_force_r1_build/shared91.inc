// Two actual-CPU RHS partitions on sealed AS03 completed states; no time update.
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
JAppInfo AppInfo("C08H18RvOnsetForce","r1","15-11-2026");
namespace pf=std::filesystem;
static constexpr unsigned Original=7060,Total=6805,Fixed=1805,Soil=5000,Samples=91;
static constexpr unsigned Parts[5]={40,42,43,76,90},Steps[5]={2080001,2084001,2086001,2152001,2180000};
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
  unsigned part,completed;double time;std::string raw_clock;std::vector<unsigned> id,fs,byid;
  std::vector<tdouble3> pos,sk,si;std::vector<tfloat3> vel,legacykk,legacyij,normal,load;
  std::vector<float> rhop,kap,p,p0,excess,posdiv;std::vector<double> j,n,theta,volume,rho,k;
  Snapshot(const pf::path& folder,unsigned which):part(Parts[which]),completed(Steps[which]),byid(Original,UINT_MAX){
    std::ifstream clocks(folder/"clocks.csv");std::string line;Need(bool(std::getline(clocks,line))&&line=="part,file,time_s,tau_from_actual_release_s,completed_step,saved_step,dt_s,signed_dterror_s,dterror_interval_empty,native_IDs,phase","Original complete11-column native clock schema required");unsigned rows=0;bool found=false;
    while(std::getline(clocks,line)){std::stringstream ss(line);std::vector<std::string> c;std::string x;while(std::getline(ss,x,','))c.push_back(x);Need(c.size()==11,"Native clock layout differs");if(std::stoul(c[0])==part){Need(!found&&std::stoul(c[4])==completed,"Completed-step clock differs");time=std::stod(c[2]);raw_clock=line;Need(std::stoul(c[5])==completed-1&&std::stod(c[6])==.000005&&Finite(std::stod(c[7]))&&std::stod(c[7])<=1e-14&&std::stoul(c[8])==0&&std::stoul(c[9])==Total&&std::stoul(c[10])==1,"Actual selected saved/signed/native clock policy differs");found=true;}rows++;}Need(found&&rows==Samples,"Native closed91 clock coverage differs");
    std::ifstream f(folder/"typed22.bin",std::ios::binary);unsigned h[3]={};f.read(reinterpret_cast<char*>(h),12);const std::uintmax_t stride=8+std::uintmax_t(Total)*212;
    Need(bool(f)&&h[0]==Total&&h[1]==22&&h[2]==Samples&&pf::file_size(folder/"typed22.bin")==12+Samples*stride,"Original closed91/6805/22 extent differs");f.seekg(std::streamoff(12+part*stride));double nativeTime;f.read(reinterpret_cast<char*>(&nativeTime),8);Need(bool(f)&&Bits(time,nativeTime),"Actual native/CSV clock differs");
    id=ReadArray<unsigned>(f);pos=ReadArray<tdouble3>(f);vel=ReadArray<tfloat3>(f);legacykk=ReadArray<tfloat3>(f);legacyij=ReadArray<tfloat3>(f);normal=ReadArray<tfloat3>(f);load=ReadArray<tfloat3>(f);
    rhop=ReadArray<float>(f);kap=ReadArray<float>(f);p=ReadArray<float>(f);p0=ReadArray<float>(f);excess=ReadArray<float>(f);sk=ReadArray<tdouble3>(f);si=ReadArray<tdouble3>(f);fs=ReadArray<unsigned>(f);
    j=ReadArray<double>(f);n=ReadArray<double>(f);theta=ReadArray<double>(f);volume=ReadArray<double>(f);rho=ReadArray<double>(f);k=ReadArray<double>(f);posdiv=ReadArray<float>(f);
    unsigned fixed=0,soil=0;for(unsigned q=0;q<Total;q++){const unsigned a=id[q];Need(a<Original&&byid[a]==UINT_MAX&&(a<Fixed||a>=2060),"Unexpected/duplicate/retired bedroles native ID");byid[a]=q;if(a<Fixed)fixed++;else{soil++;Need(kap[q]>=0&&j[q]>1.-double(.35f)&&n[q]>0&&n[q]<1&&rho[q]>0&&k[q]>0,"Invalid native soil ledger");if(fs[q]==2||fs[q]==3)Need(p[q]<=0,"Saved FS2/3 pressure is positive");}}Need(fixed==Fixed&&soil==Soil,"Native bedroles ownership differs");
  }
};
struct Sums{double lp=0,da=0,lpabs=0,daabs=0;tdouble3 lx=TDouble3(0),gp=TDouble3(0),gradj=TDouble3(0),lxabs=TDouble3(0),gpabs=TDouble3(0),jabs=TDouble3(0);unsigned count=0;
  void Add(tdouble3 d,tdouble3 gi,double v,double w,double dp,tdouble3 daij,double dj){lp+=w*dp;lx=lx+d*w;gp=gp-gi*(v*dp);gradj=gradj+gi*(v*dj);da+=v*Dot(daij,gi);lpabs+=fabs(w*dp);daabs+=v*Dot(Abs(daij),Abs(gi));lxabs=lxabs+Abs(d*w);gpabs=gpabs+Abs(gi*(v*dp));jabs=jabs+Abs(gi*(v*dj));count++;}
};
struct Global{unsigned count=0,changed=0;double volume=0,weight=0,storage=0,actualQ=0,actualAbs=0,coefficientQ=0,error=0,budget=0;std::array<double,7> q{},absq{};};
struct Reference{double time=0,theta=0;unsigned step=0,fs=0;float rate=0;tfloat3 ace=TFloat3(0);bool present=false;};
static std::array<std::vector<Reference>,2> Baseline(const pf::path& path){
  std::array<std::vector<Reference>,2> result;for(auto& q:result)q.resize(Original);std::ifstream f(path);std::string line;Need(bool(std::getline(f,line)),"Missing retained pair baseline CSV");
  auto Split=[](const std::string& s){std::vector<std::string> c;std::stringstream stream(s);std::string x;while(std::getline(stream,x,','))c.push_back(x);return c;};const auto header=Split(line);
  auto Column=[&](const char* name){const auto p=std::find(header.begin(),header.end(),name);Need(p!=header.end(),"Retained pair CSV column missing");return unsigned(p-header.begin());};
  const unsigned cp=Column("part"),cm=Column("mode"),ci=Column("native_id"),ct=Column("time_s"),cs=Column("completed_step"),cx=Column("Acex"),cy=Column("Acey"),cz=Column("Acez"),cr=Column("pressure_rate_Pa_s"),ch=Column("theta_s_1"),cf=Column("fresh_FS");unsigned rows=0,selected=0;
  while(std::getline(f,line)){const auto c=Split(line);Need(c.size()==header.size(),"Retained pair CSV layout differs");rows++;const unsigned part=std::stoul(c[cp]);if(c[cm]!="baseline"||(part!=Parts[0]&&part!=Parts[1]))continue;const unsigned which=(part==Parts[0]?0:1),id=std::stoul(c[ci]);Need(id>=2060&&id<Original&&!result[which][id].present,"Retained baseline duplicate or role differs");auto& r=result[which][id];r.time=std::stod(c[ct]);r.step=std::stoul(c[cs]);r.ace=TFloat3(float(std::stod(c[cx])),float(std::stod(c[cy])),float(std::stod(c[cz])));r.rate=float(std::stod(c[cr]));r.theta=std::stod(c[ch]);r.fs=std::stoul(c[cf]);r.present=true;Need(Finite(r.time)&&Finite(r.ace)&&Finite(r.rate)&&Finite(r.theta),"Nonfinite retained baseline value");selected++;}
  Need(rows==60000&&selected==10000,"Retained actual12-call baseline coverage differs");return result;
}
class Probe:public JSphCpuSingle{
protected:
  std::vector<typecode> code;std::vector<tfloat3> wallnormal;std::vector<byte> slip;
  std::vector<unsigned> Map()const{Need(Np==Total&&Npb==Fixed&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Completed released allocation differs");std::vector<unsigned> b(Original,UINT_MAX);unsigned soil=0,fixed=0;for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(id<Original&&b[id]==UINT_MAX&&CODE_IsNormal(Codec[q]),"Changed/duplicate ID");b[id]=q;if(id>=2060){Need(q>=Npb&&CODE_IsFluid(Codec[q]),"Soil role differs");soil++;}else{Need(id<Fixed&&q<Npb&&CODE_IsFixed(Codec[q]),"Fixed bedroles role differs");fixed++;}}Need(soil==Soil&&fixed==Fixed,"Released ID counts differ");return b;}
  void Roles()const{for(unsigned q=0;q<Np;q++){const unsigned id=Idpc[q];Need(Bits(Codec[q],code[id]),"ID-owned code changed");if(q<Npb)Need(Bits(BoundNormalc[q],wallnormal[id])&&Bits(BoundSlipModec[q],slip[id]),"ID-owned wall normal/slip changed");}}
  void Copy(const Snapshot& a){for(unsigned q=0;q<Np;q++){const unsigned s=a.byid[Idpc[q]];Need(s!=UINT_MAX,"Restore ID differs");Posc[q]=a.pos[s];Velrhopc[q]=TFloat4(a.vel[s].x,a.vel[s].y,a.vel[s].z,a.rhop[s]);const auto kk=a.sk[s],ij=a.si[s];Sigmac[q]=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);Kplasticc[q]=a.kap[s];PorePressc[q]=a.p[s];PorePress0c[q]=a.p0[s];PoroJc[q]=a.j[s];PoroThetac[q]=a.theta[s];FSTypec[q]=a.fs[s];FSNormalc[q]=a.normal[s];PosDivc[q]=a.posdiv[s];HydroMechLoadAcec[q]=a.load[s];}}
  void Ledger(const Snapshot& a)const{for(unsigned q=Npb;q<Np;q++){const unsigned s=a.byid[Idpc[q]];double n,v,rho;GetPorosityFeedbackStateCpu(q,n,v,rho);const double k=GetDynamicConductivityCpu(q);Need(Bits(n,a.n[s])&&Bits(v,a.volume[s])&&Bits(rho,a.rho[s])&&Bits(k,a.k[s])&&Bits(float(rho),a.rhop[s]),"Native J/n/V/rho/k/cache ledger differs");}}
  void Unchanged(const Snapshot& a)const{for(unsigned q=Npb;q<Np;q++){const unsigned s=a.byid[Idpc[q]];const tfloat4 v=TFloat4(a.vel[s].x,a.vel[s].y,a.vel[s].z,a.rhop[s]);const auto kk=a.sk[s],ij=a.si[s];const auto sigma=TSymMatrix3d(kk.x,ij.x,ij.z,kk.y,ij.y,kk.z);Need(Bits(Posc[q],a.pos[s])&&Bits(Velrhopc[q],v)&&Bits(Sigmac[q],sigma)&&Bits(Kplasticc[q],a.kap[s])&&Bits(PorePressc[q],a.p[s])&&Bits(PorePress0c[q],a.p0[s])&&Bits(PoroJc[q],a.j[s]),"Force changed soil primary state");}Roles();Ledger(a);Need(Bits(TimeStep,a.time)&&unsigned(Nstep)==a.completed&&!PosPrec&&!PoroJPrec,"Zero-step clock/state advanced");}
  void Restore(const Snapshot& a){Need(!Acec&&!Rsigmac&&!BoundDerivativeVelc&&!ArtificialStressc,"Previous force scratch owned");Map();Copy(a);LoadDcellParticles(Np,Codec,Posc,Dcellc);const bool free=HydroMechFreeSeepage,shep=PoreShepardRegularization;HydroMechFreeSeepage=PoreShepardRegularization=false;try{BoundChanged=true;RunCellDivide(false);}catch(...){HydroMechFreeSeepage=free;PoreShepardRegularization=shep;throw;}HydroMechFreeSeepage=free;PoreShepardRegularization=shep;Need(!CellDivSingle->GetNpbOut()&&!CellDivSingle->GetNpfOut()&&!CellDivSingle->GetNpbOutIgnore()&&!CellDivSingle->GetNpfOutIgnore(),"Cell rebuild excluded a particle");Map();Copy(a);Roles();Ledger(a);TimeStep=a.time;Nstep=a.completed;Unchanged(a);}
  std::array<Sums,3> Assemble(unsigned i)const{
    std::array<Sums,3> r;const double v0=double(MassFluid)/double(RhopZero);const tmatrix3d ci=CorrMatc[i];
    for(unsigned group=0;group<2;group++){const bool boundary=group==1;const StNgSearch ngs=nsearch::Init(Dcellc[i],boundary,DivData);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){const tuint2 range=nsearch::ParticleRange(y,z,ngs,DivData);
        for(unsigned j=range.x;j<range.y;j++)if(CODE_IsFluid(Codec[j])||(boundary&&CODE_IsFixed(Codec[j]))){
          const tdouble3 d=TDouble3(Posc[i].x-Posc[j].x,0,Posc[i].z-Posc[j].z);const double rr=d.x*d.x+d.y*d.y+d.z*d.z;if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;Need(!boundary||BoundModec[j]!=BMODE_MDBC2OFF,"Actual Darcy contains disabled wall donor");
          const double fac=fsph::GetKernel_Fac<KERNEL_Wendland>(CSP,float(rr));const tdouble3 g=d*fac,gi=Product(ci,g),gj=Product(CorrMatc[j],g);const double v=v0*PoroJc[j],dp=double(PorePressc[i])-double(PorePressc[j]);
          const double w=v*(d.x*(gi.x+gj.x)+d.y*(gi.y+gj.y)+d.z*(gi.z+gj.z))/(rr+double(Eta2));const tdouble3 da=TDouble3(double(Acec[j].x)-Acec[i].x,double(Acec[j].y)-Acec[i].y,double(Acec[j].z)-Acec[i].z);
          r[0].Add(d,gi,v,w,dp,da,PoroJc[j]-PoroJc[i]);r[group+1].Add(d,gi,v,w,dp,da,PoroJc[j]-PoroJc[i]);
        }
      }
    }return r;
  }
};

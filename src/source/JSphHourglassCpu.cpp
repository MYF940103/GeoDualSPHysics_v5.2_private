//HEAD_DSPH
/*
 <DUALSPHYSICS> Copyright (c) 2020 by Dr Jose M. Dominguez et al.
 This file is part of DualSPHysics, distributed under the GNU Lesser General
 Public License, version 2.1 or (at your option) any later version.
*/

/// \file JSphHourglassCpu.cpp \brief Implements the small-rotation elastic HG term.

#include "JSphHourglassCpu.h"
#include <algorithm>
#include <cfloat>
#include <climits>
#include <cmath>
#include <cstring>

using namespace std;

JSphHourglassCpu::JSphHourglassCpu(){
  ClassName="JSphHourglassCpu";
}

void JSphHourglassCpu::Check(bool okay,const char* message)const{
  if(!okay)Run_Exceptioon(message);
}

unsigned JSphHourglassCpu::Index(unsigned id)const{
  Check(id>=FirstId && id-FirstId<Count,"HG unexpected native soil ID.");
  return(id-FirstId);
}

double JSphHourglassCpu::MinImage(double dx)const{
  return(Period>0? dx-Period*floor(dx/Period+.5): dx);
}

void JSphHourglassCpu::Config(unsigned firstid,unsigned count,double xi,double mass,
  double period,double kernelh,double support,double bwen,double shear)
{
  Check(count>0 && count<unsigned(INT_MAX) && isfinite(xi) && xi>0 && mass>0
    && isfinite(period) && period>=0 && kernelh>0 && support>0
    && (!period || support<period*.5) && bwen<0 && shear>0,
    "HG invalid particle, elastic, kernel or neighbor configuration.");
  FirstId=firstid;Count=count;Xi=xi;Mass=mass;Period=period;KernelH=kernelh;
  Support=support;Bwen=bwen;Shear=shear;StepDt=0;PredictorSkew=0;
  Nodes.assign(Count,Node{});History.assign(Count,Vec{});HistoryRate.assign(Count,Vec{});
  RateSeen.assign(Count,0);EndpointRateReady=false;
  Next.assign(Count,-1);Heads.clear();Pairs.clear();Pairs.reserve(size_t(Count)*24);
  RateInfo=StRateInfo{};Stats=StStats{};Stats.minpairs=UINT_MAX;Stats.mintau=DBL_MAX;
  Phase=PH_PredictorForce;
}

//==============================================================================
/// Gather native particles in ascending ID order. Keep the tested cell/pair
/// traversal order; changing it also changes floating-point accumulation order.
//==============================================================================
void JSphHourglassCpu::BuildPairs(unsigned np,unsigned npb,const unsigned* idp,
  const typecode* code,const tdouble3* pos,const tfloat4* velrhop,const float* kplastic)
{
  double xmin=DBL_MAX,xmax=-DBL_MAX,zmin=DBL_MAX,zmax=-DBL_MAX;
  for(auto& n:Nodes)n=Node{};
  unsigned count=0;
  for(unsigned p=npb;p<np;p++)if(CODE_IsNormal(code[p]) && CODE_IsFluid(code[p])){
    auto& n=Nodes[Index(idp[p])];Check(n.vol==0,"HG duplicate native soil ID.");
    const auto v=velrhop[p];
    Check(v.w>0 && isfinite(v.w),"HG invalid density.");
    Check(kplastic[p]==0,"HG currently supports elastic states only.");
    n.x=pos[p].x;n.z=pos[p].z;n.vx=v.x;n.vz=v.z;n.vol=Mass/v.w;
    Check(isfinite(n.x) && isfinite(n.z) && isfinite(n.vx) && isfinite(n.vz),"HG nonfinite particle state.");
    xmin=(std::min)(xmin,n.x);xmax=(std::max)(xmax,n.x);
    zmin=(std::min)(zmin,n.z);zmax=(std::max)(zmax,n.z);count++;
  }
  Check(count==Count,"HG native soil particle set changed.");
  const double nxvalue=(Period>0? floor(Period/Support): floor((xmax-xmin)/Support)+1);
  const double nzvalue=floor((zmax-zmin)/Support)+1;
  Check(nxvalue<INT_MAX && nzvalue<INT_MAX && nxvalue*nzvalue<INT_MAX,"HG cell grid is too large.");
  const int nx=(std::max)(1,int(nxvalue)),nz=int(nzvalue);
  const double cellx=(Period>0? Period/nx: Support);
  Heads.assign(size_t(nx)*nz,-1);
  for(unsigned i=0;i<Count;i++){
    const auto& n=Nodes[i];const double x=(Period>0? n.x-Period*floor(n.x/Period): n.x-xmin);
    const int cx=(std::min)(nx-1,int(x/cellx)),cz=int((n.z-zmin)/Support);
    const int cell=cz*nx+cx;Next[i]=Heads[cell];Heads[cell]=int(i);
  }
  Pairs.clear();
  const double h=KernelH,rrmax=Support*Support,bwen=Bwen;
  for(unsigned i=0;i<Count;i++){
    const auto& a=Nodes[i];const double x=(Period>0? a.x-Period*floor(a.x/Period): a.x-xmin);
    const int cx=(std::min)(nx-1,int(x/cellx)),cz=int((a.z-zmin)/Support);
    int cols[3],ncols=0;
    for(int dx=-1;dx<=1;dx++){
      const int c=(Period>0? (cx+dx+nx)%nx: cx+dx);bool seen=false;
      if(c<0 || c>=nx)continue;
      for(int k=0;k<ncols;k++)seen|=(cols[k]==c);
      if(!seen)cols[ncols++]=c;
    }
    for(int z=(std::max)(0,cz-1);z<=(std::min)(nz-1,cz+1);z++)for(int c=0;c<ncols;c++)
      for(int jj=Heads[z*nx+cols[c]];jj>=0;jj=Next[jj]){
        const unsigned j=unsigned(jj);if(j<=i)continue;
        const double dx=MinImage(a.x-Nodes[j].x),dz=a.z-Nodes[j].z,rr=dx*dx+dz*dz;
        if(rr>=rrmax)continue;Check(rr>0,"HG coincident native particles.");
        const double s=(std::max)(0.,1.-sqrt(rr)/(2*h));
        Pairs.push_back({i,j,dx,dz,-bwen/h*s*s*s});
      }
  }
  const unsigned pairs=unsigned(Pairs.size());
  if(!Stats.ratecalls)Stats.firstpairs=pairs;
  Stats.minpairs=(std::min)(Stats.minpairs,pairs);Stats.maxpairs=(std::max)(Stats.maxpairs,pairs);
}

//==============================================================================
/// Matched soil-only LS gradient and non-nested residual. With frozen geometry,
/// the one-sided LS residual energy gives ratepower = -2*form. This identity is
/// not a coupled, time-dependent energy-conservation assertion.
//==============================================================================
void JSphHourglassCpu::Rate(){
  for(const auto& pair:Pairs){
    auto& a=Nodes[pair.i];auto& b=Nodes[pair.j];
    const double dx=pair.x,dz=pair.z,vx=a.vx-b.vx,vz=a.vz-b.vz;
    const auto add=[&](Node& n,double w){
      n.mxx+=w*dx*dx;n.mxz+=w*dx*dz;n.mzz+=w*dz*dz;
      n.nxx+=w*vx*dx;n.nxz+=w*vx*dz;n.nzx+=w*vz*dx;n.nzz+=w*vz*dz;
    };
    add(a,b.vol*pair.w);add(b,a.vol*pair.w);
  }
  for(auto& n:Nodes){
    const double det=n.mxx*n.mzz-n.mxz*n.mxz,tr=n.mxx+n.mzz;
    const double hi=.5*(tr+hypot(n.mxx-n.mzz,2*n.mxz)),lo=det/hi;
    Check(isfinite(det) && lo>0 && hi/lo<1e8,"HG rank-deficient soil-only LS moment.");
    RateInfo.condition=(std::max)(RateInfo.condition,hi/lo);
    n.lxx=(n.nxx*n.mzz-n.nxz*n.mxz)/det;n.lxz=(n.nxz*n.mxx-n.nxx*n.mxz)/det;
    n.lzx=(n.nzx*n.mzz-n.nzz*n.mxz)/det;n.lzz=(n.nzz*n.mxx-n.nzx*n.mxz)/det;
    RateInfo.skew=(std::max)(RateInfo.skew,.5*fabs(n.lxz-n.lzx));
  }
  std::fill(HistoryRate.begin(),HistoryRate.end(),Vec{});
  for(const auto& pair:Pairs){
    auto& a=Nodes[pair.i];auto& b=Nodes[pair.j];
    const double vx=a.vx-b.vx,vz=a.vz-b.vz;
    const double aix=vx-a.lxx*pair.x-a.lxz*pair.z,aiz=vz-a.lzx*pair.x-a.lzz*pair.z;
    const double bjx=vx-b.lxx*pair.x-b.lxz*pair.z,bjz=vz-b.lzx*pair.x-b.lzz*pair.z;
    const double beta=Xi*Shear*a.vol*b.vol*pair.w;
    a.betasum+=beta;b.betasum+=beta;
    const double rx=-beta*.5*(aix+bjx)/Mass,rz=-beta*.5*(aiz+bjz)/Mass;
    HistoryRate[pair.i].x+=rx;HistoryRate[pair.i].z+=rz;
    HistoryRate[pair.j].x-=rx;HistoryRate[pair.j].z-=rz;
    RateInfo.form+=.25*beta*(aix*aix+aiz*aiz+bjx*bjx+bjz*bjz);
  }
  for(const auto& n:Nodes)RateInfo.lambda=(std::max)(RateInfo.lambda,2*n.betasum/Mass);
}

//==============================================================================
/// A corrected endpoint can supply the next predictor rate only when every
/// rate input is bit-identical by native ID. Reordering and periodic copies do
/// not invalidate it. A changed/invalid state falls back to the original full
/// gather and its checks; no approximate or pointer-based state test is used.
//==============================================================================
bool JSphHourglassCpu::SameRateState(unsigned np,unsigned npb,const unsigned* idp,
  const typecode* code,const tdouble3* pos,const tfloat4* velrhop,const float* kplastic)
{
  std::fill(RateSeen.begin(),RateSeen.end(),::byte(0));unsigned count=0;
  for(unsigned p=npb;p<np;p++)if(CODE_IsNormal(code[p]) && CODE_IsFluid(code[p])){
    const unsigned i=Index(idp[p]);if(RateSeen[i])return(false);RateSeen[i]=1;
    const auto v=velrhop[p];
    if(!(v.w>0 && isfinite(v.w)) || kplastic[p]!=0)return(false);
    const auto& n=Nodes[i];const double vx=v.x,vz=v.z,vol=Mass/v.w;
    if(memcmp(&n.x,&pos[p].x,sizeof(double)) || memcmp(&n.z,&pos[p].z,sizeof(double))
      || memcmp(&n.vx,&vx,sizeof(double)) || memcmp(&n.vz,&vz,sizeof(double))
      || memcmp(&n.vol,&vol,sizeof(double)))return(false);
    count++;
  }
  return(count==Count);
}

void JSphHourglassCpu::EvaluateRate(bool endpoint,unsigned np,unsigned npb,const unsigned* idp,
  const typecode* code,const tdouble3* pos,const tfloat4* velrhop,const float* kplastic)
{
  const bool reuse=!endpoint && EndpointRateReady && SameRateState(np,npb,idp,code,pos,velrhop,kplastic);
  if(!reuse){
    BuildPairs(np,npb,idp,code,pos,velrhop,kplastic);
    RateInfo=StRateInfo{};Rate();RateInfo.tau=1/sqrt(RateInfo.lambda);
  }
  auto& ri=RateInfo;
  Check(isfinite(ri.tau) && StepDt<=.2*ri.tau,"HG dt exceeds 0.2 frozen stiffness time scale.");
  Stats.mintau=(std::min)(Stats.mintau,ri.tau);Stats.maxtauratio=(std::max)(Stats.maxtauratio,StepDt/ri.tau);
  Stats.maxlambda=(std::max)(Stats.maxlambda,ri.lambda);
  if(!reuse)for(unsigned i=0;i<Count;i++){
    const auto& n=Nodes[i];const auto r=HistoryRate[i];
    Check(isfinite(r.x) && isfinite(r.z),"HG nonfinite rate.");
    ri.netx+=Mass*r.x;ri.netz+=Mass*r.z;ri.sumrate+=Mass*hypot(r.x,r.z);
    ri.ratepower+=Mass*(n.vx*r.x+n.vz*r.z);ri.rmax=(std::max)(ri.rmax,hypot(r.x,r.z));
    const double div=n.lxx+n.lzz;
    ri.meandxx+=n.lxx;ri.rmsdxx+=n.lxx*n.lxx;ri.meandiv+=div;ri.rmsdiv+=div*div;
  }
  Stats.maxnetrate=(std::max)(Stats.maxnetrate,hypot(ri.netx,ri.netz));
  if(ri.sumrate>0)Stats.maxrelativerate=(std::max)(Stats.maxrelativerate,hypot(ri.netx,ri.netz)/ri.sumrate);
  Stats.maxcondition=(std::max)(Stats.maxcondition,ri.condition);Stats.maxskew=(std::max)(Stats.maxskew,ri.skew);
  if(endpoint)Stats.spinbound+=StepDt*(std::max)(PredictorSkew,ri.skew);else PredictorSkew=ri.skew;
  Check(Stats.spinbound<.01,"HG accumulated spin exceeds the small-rotation limit (0.01 rad).");
  ri.workerror=fabs(ri.ratepower+2*ri.form);
  Stats.maxpoweridentityerror=(std::max)(Stats.maxpoweridentityerror,ri.workerror);
  Check(ri.workerror<=1e-9*(1+fabs(ri.ratepower)+2*ri.form),"HG weighted LS virtual-work identity failed.");
  Stats.ratecalls++;if(endpoint)Stats.endpointrates++;else Stats.predictorrates++;
  if(reuse)Stats.ratecachehits++;else Stats.ratecalculations++;
  EndpointRateReady=endpoint;
}

//==============================================================================
/// Add a double history to the physical float acceleration once, keeping the
/// tested conversion order. Resolve IDs again after the predictor cell sort.
//==============================================================================
void JSphHourglassCpu::AddHistory(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,tfloat3* ace){
  Vec net{},actualnet{};double sumforce=0,hmax=0;
  unsigned count=0;
  for(unsigned p=npb;p<np;p++)if(CODE_IsNormal(code[p]) && CODE_IsFluid(code[p])){
    const auto a=History[Index(idp[p])];
    Check(isfinite(a.x) && isfinite(a.z),"HG nonfinite history.");
    const double ax=ace[p].x,az=ace[p].z;
    ace[p].x=float(ax+a.x);ace[p].z=float(az+a.z);
    actualnet.x+=Mass*(double(ace[p].x)-ax);actualnet.z+=Mass*(double(ace[p].z)-az);
    net.x+=Mass*a.x;net.z+=Mass*a.z;sumforce+=Mass*hypot(a.x,a.z);
    hmax=(std::max)(hmax,hypot(a.x,a.z));count++;
  }
  Check(count==Count,"HG native soil particle set changed before force addition.");
  Stats.maxnetforce=(std::max)(Stats.maxnetforce,hypot(net.x,net.z));
  Stats.maxactualnetforce=(std::max)(Stats.maxactualnetforce,hypot(actualnet.x,actualnet.z));
  if(sumforce>0)Stats.maxrelativeforce=(std::max)(Stats.maxrelativeforce,hypot(net.x,net.z)/sumforce);
  Stats.maxhistory=(std::max)(Stats.maxhistory,hmax);Stats.forcecalls++;
}

void JSphHourglassCpu::UpdateHistory(double dt){
  for(unsigned i=0;i<Count;i++){
    History[i].x+=.5*dt*HistoryRate[i].x;History[i].z+=.5*dt*HistoryRate[i].z;
    Stats.maxhistory=(std::max)(Stats.maxhistory,hypot(History[i].x,History[i].z));
  }
}

void JSphHourglassCpu::PredictorForce(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,
  const tdouble3* pos,const tfloat4* velrhop,const float* kplastic,tfloat3* ace,double dt)
{
  Check(Phase==PH_PredictorForce && isfinite(dt) && dt>0,"HG invalid predictor force stage.");
  StepDt=dt;EvaluateRate(false,np,npb,idp,code,pos,velrhop,kplastic);
  AddHistory(np,npb,idp,code,ace);Phase=PH_PredictorUpdate;
}

void JSphHourglassCpu::PredictorUpdate(double dt){
  Check(Phase==PH_PredictorUpdate && dt==StepDt,"HG invalid predictor history update.");
  UpdateHistory(dt);Stats.predictorupdates++;Phase=PH_CorrectorForce;
}

void JSphHourglassCpu::CorrectorForce(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,tfloat3* ace){
  Check(Phase==PH_CorrectorForce,"HG invalid corrector force stage.");
  AddHistory(np,npb,idp,code,ace);Phase=PH_CorrectorUpdate;
}

void JSphHourglassCpu::CorrectorUpdate(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,
  const tdouble3* pos,const tfloat4* velrhop,const float* kplastic,double dt)
{
  Check(Phase==PH_CorrectorUpdate && dt==StepDt,"HG invalid endpoint history update.");
  EvaluateRate(true,np,npb,idp,code,pos,velrhop,kplastic);
  UpdateHistory(dt);Stats.correctorupdates++;Phase=PH_PredictorForce;
}

llong JSphHourglassCpu::GetAllocMemory()const{
  return(llong(Nodes.capacity())*sizeof(Node)+llong(History.capacity()+HistoryRate.capacity())*sizeof(Vec)
    +llong(Pairs.capacity())*sizeof(Pair)+llong(Heads.capacity()+Next.capacity())*sizeof(int)
    +llong(RateSeen.capacity())*sizeof(::byte));
}

double JSphHourglassCpu::GetDtLimit()const{
  return(Stats.ratecalls? .2*RateInfo.tau: DBL_MAX);
}

tdouble3 JSphHourglassCpu::GetHistory(unsigned id)const{
  const auto a=History[Index(id)];return(TDouble3(a.x,0,a.z));
}

tdouble3 JSphHourglassCpu::GetRate(unsigned id)const{
  const auto r=HistoryRate[Index(id)];return(TDouble3(r.x,0,r.z));
}

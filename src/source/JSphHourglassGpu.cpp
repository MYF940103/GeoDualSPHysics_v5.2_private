//HEAD_DSPH
/*
 <DUALSPHYSICS> Copyright (c) 2020 by Dr Jose M. Dominguez et al.
 This file is part of DualSPHysics, distributed under the GNU Lesser General
 Public License, version 2.1 or (at your option) any later version.
*/
/// \file JSphHourglassGpu.cpp \brief GPU elastic HG phases and checked reductions.
#include "JSphHourglassGpu.h"
#include "JCellDivGpu_ker.h"
#include <algorithm>
#include <cfloat>
#include <climits>
#include <cmath>

using namespace std;

JSphHourglassGpu::JSphHourglassGpu(){ ClassName="JSphHourglassGpu"; }
JSphHourglassGpu::~JSphHourglassGpu(){ DestructorActive=true;FreeMemory(); }
void JSphHourglassGpu::Check(bool okay,const char* message)const{
  if(!okay)Run_Exceptioon(message);
}
void JSphHourglassGpu::CheckCuda(cudaError_t error)const{
  if(error!=cudaSuccess)Run_ExceptioonCuda(error,"GPU hourglass device operation failed.");
}
void JSphHourglassGpu::FreeMemory(){
  cudaFree(Nodesg);Nodesg=NULL;cudaFree(Historyg);Historyg=NULL;
  cudaFree(HistoryRateg);HistoryRateg=NULL;cudaFree(Slotsg);Slotsg=NULL;
  cudaFree(Keysg);Keysg=NULL;cudaFree(Orderg);Orderg=NULL;
  cudaFree(Errorg);Errorg=NULL;cudaFree(Rangesg);Rangesg=NULL;
  cudaFree(Partialg);Partialg=NULL;cudaFree(Resultg);Resultg=NULL;
  Count=CellCapacity=PartialCount=PairCount=0;Phase=PH_Unconfigured;EndpointRateReady=false;
}
unsigned JSphHourglassGpu::Index(unsigned id)const{
  Check(id>=FirstId && id-FirstId<Count,"HG unexpected native soil ID.");return(id-FirstId);
}
void JSphHourglassGpu::Config(unsigned firstid,unsigned count,double xi,double mass,
  double period,double kernelh,double support,double bwen,double shear)
{
  Check(count>0 && count<unsigned(INT_MAX) && isfinite(xi) && xi>0 && mass>0
    && period>0 && kernelh>0 && support>0 && support<period*.5 && bwen<0 && shear>0,
    "HG invalid particle, elastic, kernel or periodic configuration.");
  FreeMemory();FirstId=firstid;Count=count;Xi=xi;Mass=mass;Period=period;
  KernelH=kernelh;Support=support;Bwen=bwen;Shear=shear;StepDt=0;PredictorSkew=0;
  PartialCount=cuhg::PartialCount(Count);
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&Nodesg),sizeof(cuhg::StNode)*Count));
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&Historyg),sizeof(double2)*Count));
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&HistoryRateg),sizeof(double2)*Count));
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&Slotsg),sizeof(unsigned)*Count));
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&Keysg),sizeof(unsigned)*Count));
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&Orderg),sizeof(unsigned)*Count));
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&Errorg),sizeof(unsigned)));
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&Partialg),sizeof(cuhg::StReduce)*PartialCount));
  CheckCuda(cudaMalloc(reinterpret_cast<void**>(&Resultg),sizeof(cuhg::StReduce)));
  CheckCuda(cudaMemset(Nodesg,0,sizeof(cuhg::StNode)*Count));
  CheckCuda(cudaMemset(Historyg,0,sizeof(double2)*Count));
  CheckCuda(cudaMemset(HistoryRateg,0,sizeof(double2)*Count));
  RateInfo=StRateInfo{};Stats=StStats{};Stats.minpairs=UINT_MAX;Stats.mintau=DBL_MAX;
  Phase=PH_PredictorForce;
}
cuhg::StReduce JSphHourglassGpu::ReadResult()const{
  cuhg::Reduce(PartialCount,Partialg,Resultg);CheckCuda(cudaGetLastError());
  cuhg::StReduce r;CheckCuda(cudaMemcpy(&r,Resultg,sizeof(r),cudaMemcpyDeviceToHost));return(r);
}
void JSphHourglassGpu::CheckState(unsigned errors)const{
  Check(!(errors&cuhg::ERR_Id),"HG unexpected native soil ID.");
  Check(!(errors&cuhg::ERR_Duplicate),"HG duplicate native soil ID.");
  Check(!(errors&cuhg::ERR_Missing),"HG native soil particle set changed.");
  Check(!(errors&cuhg::ERR_Density),"HG invalid density.");
  Check(!(errors&cuhg::ERR_Plastic),"HG currently supports elastic states only.");
  Check(!(errors&cuhg::ERR_State),"HG nonfinite particle state.");
  Check(!(errors&cuhg::ERR_Coincident),"HG coincident native particles.");
  Check(!(errors&cuhg::ERR_Rank),"HG rank-deficient soil-only LS moment.");
  Check(!(errors&cuhg::ERR_Rate),"HG nonfinite rate.");
  Check(!(errors&cuhg::ERR_History),"HG nonfinite history.");
}
void JSphHourglassGpu::MapNative(unsigned np,unsigned npb,const unsigned* idp,const typecode* code){
  cuhg::MapNative(np,npb,FirstId,Count,idp,code,Slotsg,Errorg);
  CheckCuda(cudaGetLastError());
}

//==============================================================================
/// Gather/compare by native ID. The endpoint always rebuilds its own HG grid:
/// main SPH cell ranges refer to the pre-corrector state at this point.
//==============================================================================
void JSphHourglassGpu::EvaluateRate(bool endpoint,unsigned np,unsigned npb,const unsigned* idp,
  const typecode* code,const double2* posxy,const double* posz,const float4* velrhop,const float* kplastic)
{
  MapNative(np,npb,idp,code);
  cuhg::Gather(Count,Mass,Slotsg,Errorg,posxy,posz,velrhop,kplastic,Nodesg,Partialg);
  const cuhg::StReduce state=ReadResult();CheckState(state.errors);
  const bool reuse=RateCacheEnabled && !endpoint && EndpointRateReady && !state.changed;
  if(!reuse){
    const double nxvalue=floor(Period/Support),nzvalue=floor((state.zmax-state.zmin)/Support)+1;
    Check(nxvalue<INT_MAX && nzvalue<INT_MAX && nxvalue*nzvalue<INT_MAX,"HG cell grid is too large.");
    const unsigned nx=unsigned((std::max)(1,int(nxvalue))),nz=unsigned(nzvalue),ncells=nx*nz;
    if(ncells>CellCapacity){
      CheckCuda(cudaFree(Rangesg));Rangesg=NULL;
      CheckCuda(cudaMalloc(reinterpret_cast<void**>(&Rangesg),sizeof(int2)*ncells));CellCapacity=ncells;
    }
    const cuhg::StGrid grid={nx,nz,Period/nx,state.zmin,Period,Support,KernelH,Bwen,Xi,Mass,Shear};
    cuhg::CellKeys(Count,grid,Nodesg,Keysg,Orderg);CheckCuda(cudaGetLastError());
    cudiv::Sort(Keysg,Orderg,Count,true);
    cudiv::CalcBeginEndCell(true,Count,0,ncells,0,Keysg,Rangesg);
    cuhg::Moments(Count,grid,Orderg,Rangesg,Nodesg,Errorg);
    cuhg::Rates(Count,grid,Orderg,Rangesg,Nodesg,Errorg,HistoryRateg,Partialg);
    const cuhg::StReduce r=ReadResult();CheckState(r.errors);
    PairCount=r.pairs;if(!Stats.ratecalls)Stats.firstpairs=PairCount;
    Stats.minpairs=(std::min)(Stats.minpairs,PairCount);Stats.maxpairs=(std::max)(Stats.maxpairs,PairCount);
    RateInfo=StRateInfo{};
    RateInfo.netx=r.netx;RateInfo.netz=r.netz;RateInfo.condition=r.condition;RateInfo.skew=r.skew;
    RateInfo.form=r.form;RateInfo.lambda=r.lambda;RateInfo.tau=1/sqrt(r.lambda);
    RateInfo.ratepower=r.ratepower;RateInfo.rmax=r.rmax;RateInfo.sumrate=r.sumrate;
    RateInfo.meandxx=r.meandxx;RateInfo.rmsdxx=r.rmsdxx;RateInfo.meandiv=r.meandiv;RateInfo.rmsdiv=r.rmsdiv;
  }
  auto& ri=RateInfo;
  Check(isfinite(ri.tau) && StepDt<=.2*ri.tau,"HG dt exceeds 0.2 frozen stiffness time scale.");
  Stats.mintau=(std::min)(Stats.mintau,ri.tau);Stats.maxtauratio=(std::max)(Stats.maxtauratio,StepDt/ri.tau);
  Stats.maxlambda=(std::max)(Stats.maxlambda,ri.lambda);
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

void JSphHourglassGpu::AddHistory(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,float3* ace){
  // Resolve the physical slots again after the predictor's main cell sorting.
  MapNative(np,npb,idp,code);
  cuhg::AddHistory(Count,Mass,Slotsg,Errorg,Historyg,ace,Partialg);
  const cuhg::StReduce r=ReadResult();CheckState(r.errors);
  Stats.maxnetforce=(std::max)(Stats.maxnetforce,hypot(r.netx,r.netz));
  Stats.maxactualnetforce=(std::max)(Stats.maxactualnetforce,hypot(r.actualx,r.actualz));
  if(r.sumforce>0)Stats.maxrelativeforce=(std::max)(Stats.maxrelativeforce,hypot(r.netx,r.netz)/r.sumforce);
  Stats.maxhistory=(std::max)(Stats.maxhistory,r.hmax);Stats.forcecalls++;
}
void JSphHourglassGpu::UpdateHistory(double dt){
  cuhg::UpdateHistory(Count,dt,HistoryRateg,Historyg,Partialg);
  const cuhg::StReduce r=ReadResult();CheckState(r.errors);
  Stats.maxhistory=(std::max)(Stats.maxhistory,r.hmax);
}
void JSphHourglassGpu::PredictorForce(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,
  const double2* posxy,const double* posz,const float4* velrhop,const float* kplastic,float3* ace,double dt)
{
  Check(Phase==PH_PredictorForce && isfinite(dt) && dt>0,"HG invalid predictor force stage.");
  StepDt=dt;EvaluateRate(false,np,npb,idp,code,posxy,posz,velrhop,kplastic);
  AddHistory(np,npb,idp,code,ace);Phase=PH_PredictorUpdate;
}
void JSphHourglassGpu::PredictorUpdate(double dt){
  Check(Phase==PH_PredictorUpdate && dt==StepDt,"HG invalid predictor history update.");
  UpdateHistory(dt);Stats.predictorupdates++;Phase=PH_CorrectorForce;
}
void JSphHourglassGpu::CorrectorForce(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,float3* ace){
  Check(Phase==PH_CorrectorForce,"HG invalid corrector force stage.");
  AddHistory(np,npb,idp,code,ace);Phase=PH_CorrectorUpdate;
}
void JSphHourglassGpu::CorrectorUpdate(unsigned np,unsigned npb,const unsigned* idp,const typecode* code,
  const double2* posxy,const double* posz,const float4* velrhop,const float* kplastic,double dt)
{
  Check(Phase==PH_CorrectorUpdate && dt==StepDt,"HG invalid endpoint history update.");
  EvaluateRate(true,np,npb,idp,code,posxy,posz,velrhop,kplastic);
  UpdateHistory(dt);Stats.correctorupdates++;Phase=PH_PredictorForce;
}
llong JSphHourglassGpu::GetAllocMemory()const{
  return(llong(Count)*(sizeof(cuhg::StNode)+2*sizeof(double2)+3*sizeof(unsigned))
    +llong(CellCapacity)*sizeof(int2)+llong(PartialCount+(Resultg? 1: 0))*sizeof(cuhg::StReduce)
    +(Errorg? sizeof(unsigned): 0));
}
double JSphHourglassGpu::GetDtLimit()const{ return(Stats.ratecalls? .2*RateInfo.tau: DBL_MAX); }
tdouble3 JSphHourglassGpu::GetHistory(unsigned id)const{
  double2 h;CheckCuda(cudaMemcpy(&h,Historyg+Index(id),sizeof(h),cudaMemcpyDeviceToHost));return(TDouble3(h.x,0,h.y));
}
tdouble3 JSphHourglassGpu::GetRate(unsigned id)const{
  double2 r;CheckCuda(cudaMemcpy(&r,HistoryRateg+Index(id),sizeof(r),cudaMemcpyDeviceToHost));return(TDouble3(r.x,0,r.y));
}

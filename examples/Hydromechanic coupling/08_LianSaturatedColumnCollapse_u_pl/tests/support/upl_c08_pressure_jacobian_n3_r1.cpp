// Actual CPU frozen41-pressure conditional Jacobian responses; no time integration.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
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
JAppInfo AppInfo("C08PressureJacobianN3","r1","09-11-2026");
namespace pathfs=std::filesystem;
static_assert(sizeof(unsigned)==4&&sizeof(tfloat3)==12&&sizeof(tdouble3)==24&&sizeof(tsymatrix3d)==48,"Frozen typed22 and named stress layout required");
static constexpr unsigned Original=7060,Total=6805,Fixed=1805,Soil=5000,Samples=90;
static constexpr unsigned Focus[4]={7013,7015,6963,7014},Bed[5]={1800,1852,1904,1956,2008};
static constexpr unsigned Selected[41]={6963,7013,7014,7015,7016,7012,6965,6964,7017,6966,7011,6967,6915,6962,6914,7018,6968,6917,6866,6916,6913,6918,6867,6865,7019,6969,6816,7010,6868,6817,6864,6919,6920,6869,7020,6818,6767,6970,6912,6815,6870};
static void Need(bool x,const char* s){if(!x)throw std::runtime_error(s);}
template<class T>static bool Bits(const T& a,const T& b){return !memcmp(&a,&b,sizeof(T));}
static bool Finite(float x){return std::isfinite(x);}static bool Finite(double x){return std::isfinite(x);}static bool Finite(unsigned){return true;}
static bool Finite(tfloat3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}static bool Finite(tdouble3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static tdouble3 Product(const tmatrix3d& c,tdouble3 g){return TDouble3(c.a11*g.x+c.a12*g.y+c.a13*g.z,c.a21*g.x+c.a22*g.y+c.a23*g.z,c.a31*g.x+c.a32*g.y+c.a33*g.z);}
template<class T>static std::vector<T> ReadArray(std::ifstream& f){std::vector<T> v(Total);f.read(reinterpret_cast<char*>(v.data()),sizeof(T)*Total);Need(bool(f),"Truncated native array");for(const auto& x:v)Need(Finite(x),"Nonfinite native array");return v;}
struct Snapshot{
  unsigned part,completed;double time;std::vector<unsigned> id,fstype,byid;
  std::vector<tdouble3> pos,sk,si;std::vector<tfloat3> vel,legacykk,legacyij,fsnormal,load;
  std::vector<float> rhop,kap,p,p0,excess,posdiv;std::vector<double> j,n,theta,volume,rho,k;
  Snapshot(const pathfs::path& folder,unsigned selected):part(selected),completed(4000000+4000*(selected+1)),byid(Original,UINT_MAX){
    std::ifstream f(folder/"typed22.bin",std::ios::binary);unsigned h[3]={};f.read(reinterpret_cast<char*>(h),12);const std::uintmax_t stride=8+std::uintmax_t(Total)*212;
    Need(bool(f)&&h[0]==Total&&h[1]==22&&h[2]==Samples&&pathfs::file_size(folder/"typed22.bin")==12+Samples*stride,"Actual90/6805/22 native extent differs");
    Need(selected==71,"Only actual causal90 part71 is admitted");f.seekg(std::streamoff(12+selected*stride));f.read(reinterpret_cast<char*>(&time),8);Need(bool(f)&&Finite(time),"Invalid native clock");
    id=ReadArray<unsigned>(f);pos=ReadArray<tdouble3>(f);vel=ReadArray<tfloat3>(f);legacykk=ReadArray<tfloat3>(f);legacyij=ReadArray<tfloat3>(f);fsnormal=ReadArray<tfloat3>(f);load=ReadArray<tfloat3>(f);
    rhop=ReadArray<float>(f);kap=ReadArray<float>(f);p=ReadArray<float>(f);p0=ReadArray<float>(f);excess=ReadArray<float>(f);sk=ReadArray<tdouble3>(f);si=ReadArray<tdouble3>(f);fstype=ReadArray<unsigned>(f);
    j=ReadArray<double>(f);n=ReadArray<double>(f);theta=ReadArray<double>(f);volume=ReadArray<double>(f);rho=ReadArray<double>(f);k=ReadArray<double>(f);posdiv=ReadArray<float>(f);
    unsigned fixed=0,soil=0;for(unsigned q=0;q<Total;q++){const unsigned a=id[q];const bool bed=std::find(std::begin(Bed),std::end(Bed),a)!=std::end(Bed);Need(a<Original&&byid[a]==UINT_MAX&&(a<1800||bed||a>=2060),"Unexpected/duplicate/retired native ID");byid[a]=q;if(a<2060)fixed++;else{soil++;Need(kap[q]>=0&&j[q]>1.-double(.35f)&&n[q]>0&&n[q]<1&&rho[q]>0&&k[q]>0,"Invalid soil native ledger domain");if(fstype[q]==2||fstype[q]==3)Need(p[q]<=0,"Closed saved FS2/3 has positive pressure");}}
    Need(fixed==Fixed&&soil==Soil,"Actual fixed/soil ownership differs");for(unsigned a:Focus)Need(byid[a]!=UINT_MAX,"Explicit focus missing");
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
  struct Terms{unsigned neighbors;double compression,lp,defect,divace,chain,rate,budget;};
  Terms Sum(unsigned i)const{
    const double water=SoilCte.PoreWaterRho,kw=SoilCte.PoreWaterBulkModulus,gamma=water*9.80665,v0=double(MassFluid)/RhopZero,ki=GetDynamicConductivityCpu(i),kp=ki/((1.-double(SoilCte.Porosity))*DynamicPoreConductivityCk);double n,v,rho;GetPorosityFeedbackStateCpu(i,n,v,rho);
    double lp=0,da=0,absLp=0,absDa=0;tdouble3 lx=TDouble3(0),gp=TDouble3(0),gJ=TDouble3(0);unsigned count=0;
    // All actual particles, independent of production cell order; never omit fixed support.
    for(unsigned j=0;j<Np;j++)if(CODE_IsFluid(Codec[j])||(j<Npb&&CODE_IsFixed(Codec[j]))){const auto d=Posc[i]-Posc[j];const double rr=d.x*d.x+d.z*d.z;if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;if(j<Npb)Need(BoundModec[j]!=BMODE_MDBC2OFF,"Inactive fixed sample in actual Darcy support");const auto g=d*double(fsph::GetKernel_Fac<KERNEL_Cubic>(CSP,float(rr))),gi=Product(CorrMatc[i],g),gj=Product(CorrMatc[j],g);const double vol=v0*PoroJc[j],dp=double(PorePressc[i])-PorePressc[j],w=vol*Dot(d,gi+gj)/(rr+double(Eta2));const auto delta=ToTDouble3(Acec[j])-ToTDouble3(Acec[i]);lp+=w*dp;lx=lx+d*w;gp=gp-gi*(vol*dp);gJ=gJ+gi*(vol*(PoroJc[j]-PoroJc[i]));da+=vol*Dot(delta,gi);absLp+=fabs(w*dp);absDa+=vol*(fabs(delta.x*gi.x)+fabs(delta.z*gi.z));count++;}
    const bool fs=HydroMechFreeSeepage&&IsFreeSurfaceParticle(i,Codec,FSTypec);const auto a=ToTDouble3(Acec[i]);const double defect=fs?water*Dot(a,lx):-Dot(gp,lx),chain=kp*Dot(gJ,gp+a*water),B=kw/n;
    Terms q{count,-B*PoroThetac[i],B*ki/gamma*lp,B*ki/gamma*defect,B*ki/gamma*water*da,B/gamma*chain,0,0};q.rate=q.compression+q.lp+q.defect+q.divace+q.chain;
    const double absolute=fabs(q.compression)+B/gamma*(ki*(absLp+(fs?water*(fabs(a.x*lx.x)+fabs(a.z*lx.z)):fabs(gp.x*lx.x)+fabs(gp.z*lx.z))+water*absDa)+kp*(fabs(gJ.x)*(fabs(gp.x)+water*fabs(a.x))+fabs(gJ.z)*(fabs(gp.z)+water*fabs(a.z))));const double neps=(64.*count+256.)*DBL_EPSILON;
    q.budget=(32.*FLT_EPSILON+neps/(1.-neps))*(std::max)(1.,absolute);Need(Finite(q.rate)&&Finite(q.budget)&&fabs(double(PorePressRatec[i])-q.rate)<=q.budget,"Actual Darcy rate/test-side five-term sum budget failed");return q;
  }
public:
  void Execute(const JSphCfgRun* cfg,JLog2* log,const Snapshot& base){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();RunGravityPreloadHandoffCpu();FreePartsInit();
    Need(IsGravityPreloadHandoff()&&GravityPreload&&!GravityPreloadElasticSource&&!GravityPreloadReleased&&unsigned(Nstep)==4000000&&GravityPreloadKeepBedOverlap&&GravityPreloadBedIds==std::vector<unsigned>(std::begin(Bed),std::end(Bed)),"Actual certified PRE/keep5 receiver initialization differs");RunGravityPreloadRelease();Map();
    Need(GravityPreloadReleased&&GravityPreloadActualStep==4000000&&DynamicPorePressure&&PorosityFeedback&&DynamicPoreWall&&DynamicPoreConductivity&&DynamicPoreConductivityCk==2.&&HydroMechFreeSeepage&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilDamping&&!PoreShepardRegularization,"Released dynamic controls differ");
    Need(Simulate2D&&!PeriActive&&TKernel==KERNEL_Cubic&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundSlipModec&&SoilStressRateGradCorr&&!SoilBoundaryDerivativeSPR&&!HourglassCpu&&!SoilHourglassXi&&!WithFloating&&!UseDEM&&!AccInput&&!Shifting&&!Damping&&TDensity==DDT_None&&NoPenetration&&TMdbc2==MDBC2_NoPen&&UseDynamicPorePlaneContact(),"Frozen released force scope differs");
    Need(ArtificialStress&&ArtificialStressCoef==.2f&&ArtificialStressExp==3.f&&Dp==.04&&KernelH==.048f&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==.0002f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&TVisco==VISCO_Artificial&&Visco==.1f&&Gravity==TFloat3(0,0,-9.81f),"Frozen material/kernel/AS/AV differs");
    releasedCode.resize(Original);releasedNormal.resize(Original);releasedSlip.resize(Original);for(unsigned q=0;q<Np;q++){releasedCode[Idpc[q]]=Codec[q];if(q<Npb){releasedNormal[Idpc[q]]=BoundNormalc[q];releasedSlip[Idpc[q]]=BoundSlipModec[q];}}StaticRoles();const double sourceTime=GravityPreloadActualTime;
    Restore(base);const std::vector<unsigned> selected(std::begin(Selected),std::end(Selected));for(unsigned id:selected){Need(base.byid[id]!=UINT_MAX&&base.p[base.byid[id]]<-16.f,"Fixed original41 pressure columns must exist and remain negative under both perturbations");}
    std::ofstream rates(pathfs::path(cfg->DirOut)/"rates.csv"),callRows(pathfs::path(cfg->DirOut)/"calls.csv");for(auto* f:{&rates,&callRows})*f<<std::setprecision(17);
    rates<<"evaluation,AS_exp,kind,column_native_id,requested_h_Pa,sign,actual_column_delta_Pa,row_native_id,x,z,p_Pa,J,n,volume_m3,theta,actual_FS,Ace_x,Ace_z,actual_rate_Pa_s,compression_Pa_s,LP_Pa_s,defect_Pa_s,divAce_Pa_s,chain_Pa_s,shadow_sum_Pa_s,shadow_budget_Pa_s\n";
    callRows<<"evaluation,part,time_s,tau_s,completed_step,AS_exp,kind,column_native_id,requested_h_Pa,sign,base_column_p_Pa,actual_column_p_Pa,actual_column_delta_Pa,base_column_float_bits,actual_column_float_bits,soil,selected,FS_baseline_changed,saved_FS_changed,max_actual_rate_abs_Pa_s,max_shadow_budget_fraction,primary_bits_unchanged\n";
    unsigned calls=0,rateRows=0,baselineCalls=0,centralCalls=0,fsChecks=0;double maxRatio=0;std::vector<unsigned> baselineFS,baselineWallMode;std::vector<float> baselineRates;unsigned rateRestoreChecks=0,wallModeChecks=0;
    const auto floatBits=[](float value){std::uint32_t bits;memcpy(&bits,&value,4);return bits;};
    const auto evaluate=[&](const Snapshot& incoming,unsigned column,unsigned h,int sign){
      Restore(incoming);const float exponent=ArtificialStressExp;Need(exponent==3.f,"Only original AS3 is admitted");const auto byid=Map();const bool baseline=(column==UINT_MAX);const char* kind=(baseline?"baseline":"central");const double clock=TimeStep;const int step=Nstep;const float original=(baseline?0.f:base.p[base.byid[column]]),changed=(baseline?0.f:incoming.p[incoming.byid[column]]);const double delta=baseline?0.:double(changed)-double(original);bool cleanup=true;
      Need(baseline||(column>=2060&&std::find(selected.begin(),selected.end(),column)!=selected.end()&&h==16&&(sign==1||sign==-1)&&changed<0.f&&Finite(changed)&&sign*delta>0),"Invalid explicit one-column perturbation");Log->Printf("PressureZero: evaluation=%u ASexp=%.0f column=%d h=%u sign=%d actual_delta=%.17g; zero physical steps.",calls+1,double(exponent),baseline?-1:int(column),h,sign,delta);
      try{Interaction_Forces(INTERSTEP_SymCorrector);calls++;Need(Acec&&Rsigmac&&PorePressRatec&&BoundDerivativeVelc&&ArtificialStressc,"Actual force-stage scratch missing");SoilUnchanged(incoming);unsigned changedFS=0,savedFS=0;double rateMax=0,ratio=0;
        if(baseline){Need(baselineFS.empty(),"Duplicate exponent baseline");baselineFS.assign(Original,UINT_MAX);baselineWallMode.assign(Original,UINT_MAX);baselineRates.resize(Original);baselineCalls++;}else{Need(baselineFS.size()==Original,"Perturbation preceded its exponent baseline");centralCalls++;}
        for(unsigned q=Npb;q<Np;q++){const unsigned id=Idpc[q];Need(Finite(Acec[q])&&Finite(PoroThetac[q])&&Finite(PorePressRatec[q]),"Actual full5000 force/rate nonfinite");const auto sr=Rsigmac[q];Need(Finite(sr.xx)&&Finite(sr.yy)&&Finite(sr.zz)&&Finite(sr.xy)&&Finite(sr.yz)&&Finite(sr.xz),"Actual stress rate nonfinite");if(baseline){baselineFS[id]=FSTypec[q];baselineRates[id]=PorePressRatec[q];}else{changedFS+=FSTypec[q]!=baselineFS[id];fsChecks++;}savedFS+=FSTypec[q]!=base.fstype[base.byid[id]];rateMax=(std::max)(rateMax,fabs(double(PorePressRatec[q])));}
        Need(changedFS==0,"Pressure-only perturbation changed FSType relative to its baseline");for(unsigned q=0;q<Npb;q++){const unsigned id=Idpc[q];if(baseline)baselineWallMode[id]=BoundModec[q];else{Need(unsigned(BoundModec[q])==baselineWallMode[id],"Pressure-only perturbation changed a wall activity mask");wallModeChecks++;}}
        for(unsigned id:selected){const unsigned q=byid[id];const auto t=Sum(q);ratio=(std::max)(ratio,fabs(double(PorePressRatec[q])-t.rate)/t.budget);double n,volume,rho;GetPorosityFeedbackStateCpu(q,n,volume,rho);rates<<calls<<','<<exponent<<','<<kind<<','<<(baseline?-1:int(column))<<','<<h<<','<<sign<<','<<delta<<','<<id<<','<<Posc[q].x<<','<<Posc[q].z<<','<<PorePressc[q]<<','<<PoroJc[q]<<','<<n<<','<<volume<<','<<PoroThetac[q]<<','<<FSTypec[q]<<','<<Acec[q].x<<','<<Acec[q].z<<','<<PorePressRatec[q]<<','<<t.compression<<','<<t.lp<<','<<t.defect<<','<<t.divace<<','<<t.chain<<','<<t.rate<<','<<t.budget<<'\n';rateRows++;}
        callRows<<calls<<','<<base.part<<','<<clock<<','<<clock-sourceTime<<','<<step<<','<<exponent<<','<<kind<<','<<(baseline?-1:int(column))<<','<<h<<','<<sign<<',';if(baseline)callRows<<",,0,,";else callRows<<original<<','<<changed<<','<<delta<<','<<floatBits(original)<<','<<floatBits(changed);callRows<<','<<Soil<<','<<selected.size()<<','<<changedFS<<','<<savedFS<<','<<rateMax<<','<<ratio<<",1\n";maxRatio=(std::max)(maxRatio,ratio);Need(TimeStep==clock&&Nstep==step,"Force evaluation advanced clock");PosInteraction_Forces();cleanup=false;
      }catch(...){if(cleanup)PosInteraction_Forces();throw;}Need(!Acec&&!Rsigmac&&!ArtificialStressc&&!BoundDerivativeVelc,"Force scratch not released");SoilUnchanged(incoming);CopySaved(base);for(unsigned q=Npb;q<Np;q++){const unsigned id=Idpc[q];PorePressRatec[q]=baselineRates[id];Need(Bits(PorePressRatec[q],baselineRates[id]),"Original baseline pressure-rate bits were not restored");rateRestoreChecks++;}SoilUnchanged(base);
    };
    evaluate(base,UINT_MAX,0,0);for(unsigned column:selected)for(int sign:{1,-1}){Snapshot incoming=base;const unsigned s=incoming.byid[column];incoming.p[s]=float(double(base.p[s])+double(sign)*16.);incoming.excess[s]=float(incoming.p[s]-incoming.p0[s]);evaluate(incoming,column,16,sign);}
    Need(calls==83&&baselineCalls==1&&centralCalls==82&&rateRows==3403&&fsChecks==410000&&wallModeChecks==148010&&rateRestoreChecks==415000&&ArtificialStressExp==3.f,"Exact83-call/41-pressure response coverage or restoration missing");for(auto* f:{&rates,&callRows}){f->flush();Need(bool(*f),"Response CSV write failed");}
    std::ofstream done(pathfs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_c08_pressure_jacobian_n3_r1\",\"passed\":true,\"source_part\":71,\"source_time_s\":"<<base.time<<",\"source_completed_step\":"<<base.completed<<",\"AS_exponents\":[3],\"requested_h_Pa\":[16],\"selected_native_IDs\":[";for(unsigned q=0;q<selected.size();q++){if(q)done<<',';done<<selected[q];}done<<"],\"native_IDs\":6805,\"soil\":5000,\"fixed\":1805,\"actual_ct_calls\":83,\"actual_Darcy_calls\":83,\"baseline_calls\":1,\"central_calls\":82,\"central_column_h_groups\":41,\"rate_rows\":3403,\"call_rows\":83,\"FSType_baseline_checks\":410000,\"wall_mode_baseline_checks\":148010,\"baseline_rate_restore_bits_checks\":415000,\"original_pressure_restored_after_each_call\":true,\"original_baseline_rates_restored_after_each_call\":true,\"source_profile\":\"total_AS_n3_Shepard_OFF_causal90\",\"pore_water_bulk_modulus_Pa\":"<<double(SoilCte.PoreWaterBulkModulus)<<",\"metric_reference\":\"saved_native_n_and_volume_verified_bit_equal_by_Ledger\",\"physical_steps\":0,\"material_return_calls\":0,\"all5000_soil_primary_bits_match_explicit_incoming_state\":true,\"only_selected_float_pressure_perturbed\":true,\"actual_float_pressure_deltas_exported\":true,\"wall_state_C_Ace_rebuilt_each_call\":true,\"actual_seed_PRE_handoff_and_keep5_release\":true,\"max_rate_shadow_budget_fraction\":"<<maxRatio<<",\"five_term_sum_is_test_side_shadow\":true,\"outside_soil_pressure_perturbations_held_zero\":true,\"finite_difference_responses_not_analytic_AD\":true,\"finite_difference_convergence_not_yet_analyzed\":true,\"full_coupled_spectrum_claimed\":false,\"original_GPU_rate_or_unsaved_stage_replay\":false,\"reaction_J_Darcy_closed\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=9&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--snapshot","Use --check --snapshot CLOSED_CAUSAL90_NATIVE -cpu -ompthreads:1 -stable -mdbc_freeslip:1 EXISTING_CAUSAL_SEED FRESH_OUT");const pathfs::path folder=pathfs::absolute(argv[3]),tests=pathfs::path(__FILE__).parent_path().parent_path();Need(pathfs::equivalent(folder,tests/"outputs/upl_c08_causal_window_GPU_r1/native"),"Only actual passed causal90 input is admitted");Snapshot base(folder,71);
  AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!pathfs::exists(cfg.DirOut),"Fresh CPU component output required");// Keep the real PRE loader output contract; no SaveData or time integration is called.
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr(),base);return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"CPU zero-step failed; preserve first result\n";return 2;}}

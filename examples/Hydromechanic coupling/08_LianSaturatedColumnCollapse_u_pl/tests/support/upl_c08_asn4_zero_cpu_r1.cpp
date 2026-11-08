// New CPU force-stage evaluations of two sealed n4 saved states; no time integration.
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
JAppInfo AppInfo("C08ASN4ZeroCpu","r1","09-11-2026");
namespace pathfs=std::filesystem;
static_assert(sizeof(unsigned)==4&&sizeof(tfloat3)==12&&sizeof(tdouble3)==24&&sizeof(tsymatrix3d)==48,"Frozen typed22 and named stress layout required");
static constexpr unsigned Original=7060,Total=6805,Fixed=1805,Soil=5000,Samples=66;
static constexpr unsigned Parts[2]={29,64},Focus[4]={7013,7015,6963,7014},Bed[5]={1800,1852,1904,1956,2008};
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
    Need(bool(f)&&h[0]==Total&&h[1]==22&&h[2]==Samples&&pathfs::file_size(folder/"typed22.bin")==12+Samples*stride,"Actual66/6805/22 native extent differs");
    Need(selected==Parts[0]||selected==Parts[1],"Only pre-pulse parts29/64 are admitted");f.seekg(std::streamoff(12+selected*stride));f.read(reinterpret_cast<char*>(&time),8);Need(bool(f)&&Finite(time),"Invalid native clock");
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
  std::vector<unsigned> Select(const Snapshot& a)const{
    const auto b=Map();std::vector<std::pair<double,unsigned>> score;const double radius2=4.*double(KernelSize2);
    for(unsigned id=2060;id<Original;id++){const auto x=a.pos[a.byid[id]];double d2=DBL_MAX;for(unsigned f:Focus){const auto d=x-a.pos[a.byid[f]];d2=(std::min)(d2,d.x*d.x+d.z*d.z);}if(d2<=radius2)score.emplace_back(d2,id);}
    std::sort(score.begin(),score.end());std::vector<unsigned> out;for(const auto& x:score){if(out.size()==81)break;out.push_back(b[x.second]);}Need(!out.empty()&&out.size()<=81,"Receiver output selection differs");for(unsigned f:Focus)Need(std::find(out.begin(),out.end(),b[f])!=out.end(),"An explicit focus was truncated");return out;
  }
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
  void Execute(const JSphCfgRun* cfg,JLog2* log,const Snapshot& first,const Snapshot& second){
    AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();RunGravityPreloadHandoffCpu();FreePartsInit();
    Need(IsGravityPreloadHandoff()&&GravityPreload&&!GravityPreloadElasticSource&&!GravityPreloadReleased&&unsigned(Nstep)==4000000&&GravityPreloadKeepBedOverlap&&GravityPreloadBedIds==std::vector<unsigned>(std::begin(Bed),std::end(Bed)),"Actual certified PRE/keep5 receiver initialization differs");RunGravityPreloadRelease();Map();
    Need(GravityPreloadReleased&&GravityPreloadActualStep==4000000&&DynamicPorePressure&&PorosityFeedback&&DynamicPoreWall&&DynamicPoreConductivity&&DynamicPoreConductivityCk==2.&&HydroMechFreeSeepage&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!SoilDamping&&!PoreShepardRegularization,"Released dynamic controls differ");
    Need(Simulate2D&&!PeriActive&&TKernel==KERNEL_Cubic&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundSlipModec&&SoilStressRateGradCorr&&!SoilBoundaryDerivativeSPR&&!HourglassCpu&&!SoilHourglassXi&&!WithFloating&&!UseDEM&&!AccInput&&!Shifting&&!Damping&&TDensity==DDT_None&&NoPenetration&&TMdbc2==MDBC2_NoPen&&UseDynamicPorePlaneContact(),"Frozen released force scope differs");
    Need(ArtificialStress&&ArtificialStressCoef==.2f&&ArtificialStressExp==4.f&&Dp==.04&&KernelH==.048f&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.PoreWaterBulkModulus==1e9f&&SoilCte.HydraulicConductivity==.0002f&&SoilCte.ModulusE==20e6f&&SoilCte.PRvs==.33f&&TVisco==VISCO_Artificial&&Visco==.1f&&Gravity==TFloat3(0,0,-9.81f),"Frozen material/kernel/AS/AV differs");
    releasedCode.resize(Original);releasedNormal.resize(Original);releasedSlip.resize(Original);for(unsigned q=0;q<Np;q++){releasedCode[Idpc[q]]=Codec[q];if(q<Npb){releasedNormal[Idpc[q]]=BoundNormalc[q];releasedSlip[Idpc[q]]=BoundSlipModec[q];}}StaticRoles();const double sourceTime=GravityPreloadActualTime;
    std::ofstream rows(pathfs::path(cfg->DirOut)/"receivers.csv"),walls(pathfs::path(cfg->DirOut)/"walls.csv"),evals(pathfs::path(cfg->DirOut)/"evaluations.csv");for(auto* f:{&rows,&walls,&evals})*f<<std::setprecision(17);
    rows<<"part,time_s,tau_s,completed_step,AS_exp,native_id,x,z,vx,vz,p_Pa,P0_Pa,kappa,J,n,rho,k,saved_FS,actual_FS,theta,Rxx,Ryy,Rzz,Rxy,Ryz,Rxz,Ace_x,Ace_y,Ace_z,Cxx,Cxz,Czx,Czz,neighbors,actual_rate_Pa_s,compression_Pa_s,LP_Pa_s,defect_Pa_s,divAce_Pa_s,chain_Pa_s,shadow_sum_Pa_s,shadow_budget_Pa_s\n";
    walls<<"part,time_s,tau_s,AS_exp,native_id,Bx,Bz,normal_x,normal_z,slip,code,boundmode,is_kept_bed,J,p_Pa,P0_Pa,sxx,syy,szz,sxy,syz,sxz,Cxx,Cxz,Czx,Czz,Ace_x,Ace_y,Ace_z,derivative_vx,derivative_vz,tangent_vx,tangent_vz\n";
    evals<<"part,time_s,tau_s,completed_step,AS_exp,soil,selected,related_walls,active_walls,FS23,saved_FS_changed,max_actual_rate_abs_Pa_s,max_shadow_budget_fraction,primary_bits_unchanged\n";
    unsigned calls=0,receiverRows=0,wallRows=0;double maxRatio=0;
    for(const Snapshot* a:{&first,&second})for(float exponent:{4.f,3.f}){
      Restore(*a);ArtificialStressExp=exponent;const auto selected=Select(*a);const double clock=TimeStep;const int step=Nstep;bool cleanup=true;
      try{Interaction_Forces(INTERSTEP_SymCorrector);calls++;Need(Acec&&Rsigmac&&PorePressRatec&&BoundDerivativeVelc&&ArtificialStressc,"Actual force-stage scratch missing");SoilUnchanged(*a);unsigned changed=0,fs23=0,active=0;double rateMax=0,ratio=0;
        for(unsigned q=Npb;q<Np;q++){Need(Finite(Acec[q])&&Finite(PoroThetac[q])&&Finite(PorePressRatec[q]),"Actual full5000 force/rate nonfinite");const auto s=Rsigmac[q];Need(Finite(s.xx)&&Finite(s.yy)&&Finite(s.zz)&&Finite(s.xy)&&Finite(s.yz)&&Finite(s.xz),"Actual stress rate nonfinite");changed+=FSTypec[q]!=a->fstype[a->byid[Idpc[q]]];fs23+=IsFreeSurfaceParticle(q,Codec,FSTypec);rateMax=(std::max)(rateMax,fabs(double(PorePressRatec[q])));}
        for(unsigned q=0;q<NpbOk;q++)active+=BoundModec[q]==BMODE_MDBC2;std::set<unsigned> related;
        for(unsigned q:selected){const auto t=Sum(q);ratio=(std::max)(ratio,fabs(double(PorePressRatec[q])-t.rate)/t.budget);const unsigned id=Idpc[q],saved=a->byid[id];const auto x=Posc[q];const auto c=CorrMatc[q];const auto v=Velrhopc[q];const auto s=Rsigmac[q];const auto acc=Acec[q];double n,volume,rho;GetPorosityFeedbackStateCpu(q,n,volume,rho);
          rows<<a->part<<','<<clock<<','<<clock-sourceTime<<','<<step<<','<<exponent<<','<<id<<','<<x.x<<','<<x.z<<','<<v.x<<','<<v.z<<','<<PorePressc[q]<<','<<PorePress0c[q]<<','<<Kplasticc[q]<<','<<PoroJc[q]<<','<<n<<','<<rho<<','<<GetDynamicConductivityCpu(q)<<','<<a->fstype[saved]<<','<<FSTypec[q]<<','<<PoroThetac[q]<<','<<s.xx<<','<<s.yy<<','<<s.zz<<','<<s.xy<<','<<s.yz<<','<<s.xz<<','<<acc.x<<','<<acc.y<<','<<acc.z<<','<<c.a11<<','<<c.a13<<','<<c.a31<<','<<c.a33<<','<<t.neighbors<<','<<PorePressRatec[q]<<','<<t.compression<<','<<t.lp<<','<<t.defect<<','<<t.divace<<','<<t.chain<<','<<t.rate<<','<<t.budget<<'\n';receiverRows++;
          for(unsigned b=0;b<Npb;b++){const auto d=x-Posc[b];if(d.x*d.x+d.z*d.z<=double(KernelSize2))related.insert(b);}}
        for(unsigned q:related){const auto x=Posc[q];const auto c=CorrMatc[q];const auto bn=BoundNormalc[q];const auto s=Sigmac[q];const auto acc=Acec[q];const auto dv=BoundDerivativeVelc[q];const auto tv=TangenVelc[q];Need(BoundModec[q]==BMODE_MDBC2&&Finite(PoroJc[q])&&Finite(PorePressc[q])&&Finite(acc),"Related wall is not a valid active sample");walls<<a->part<<','<<clock<<','<<clock-sourceTime<<','<<exponent<<','<<Idpc[q]<<','<<x.x<<','<<x.z<<','<<bn.x<<','<<bn.z<<','<<unsigned(BoundSlipModec[q])<<','<<unsigned(Codec[q])<<','<<unsigned(BoundModec[q])<<','<<IsGravityPreloadBedId(Idpc[q])<<','<<PoroJc[q]<<','<<PorePressc[q]<<','<<PorePress0c[q]<<','<<s.xx<<','<<s.yy<<','<<s.zz<<','<<s.xy<<','<<s.yz<<','<<s.xz<<','<<c.a11<<','<<c.a13<<','<<c.a31<<','<<c.a33<<','<<acc.x<<','<<acc.y<<','<<acc.z<<','<<dv.x<<','<<dv.z<<','<<tv.x<<','<<tv.z<<'\n';wallRows++;}
        evals<<a->part<<','<<clock<<','<<clock-sourceTime<<','<<step<<','<<exponent<<','<<Soil<<','<<selected.size()<<','<<related.size()<<','<<active<<','<<fs23<<','<<changed<<','<<rateMax<<','<<ratio<<",1\n";maxRatio=(std::max)(maxRatio,ratio);Need(TimeStep==clock&&Nstep==step,"Force stage advanced clock");PosInteraction_Forces();cleanup=false;
      }catch(...){if(cleanup)PosInteraction_Forces();throw;}Need(!Acec&&!Rsigmac&&!ArtificialStressc&&!BoundDerivativeVelc,"Force scratch not released");SoilUnchanged(*a);
    }
    ArtificialStressExp=4.f;Need(calls==4,"Exactly four explicit force evaluations required");for(auto* f:{&rows,&walls,&evals}){f->flush();Need(bool(*f),"CSV write failed");}
    std::ofstream done(pathfs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_c08_asn4_zero_cpu_r1\",\"passed\":true,\"source_parts\":[29,64],\"AS_exponents\":[4,3],\"native_IDs\":6805,\"soil\":5000,\"fixed\":1805,\"actual_ct_calls\":4,\"actual_Darcy_calls\":4,\"receiver_rows\":"<<receiverRows<<",\"wall_rows\":"<<wallRows<<",\"physical_steps\":0,\"material_return_calls\":0,\"all5000_soil_primary_bits_unchanged_each_call\":true,\"actual_seed_PRE_handoff_and_keep5_release\":true,\"snapshot_recomputed_FS_reported\":true,\"max_rate_shadow_budget_fraction\":"<<maxRatio<<",\"actual_CPU_finished_Ace_used\":true,\"five_term_sum_is_test_side_shadow\":true,\"original_GPU_rate_or_unsaved_stage_replay\":false,\"pressure_Jacobian_or_spectrum\":false,\"reaction_J_Darcy_closed\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=9&&std::string(argv[1])=="--check"&&std::string(argv[2])=="--snapshot","Use --check --snapshot CLOSED_N4_NATIVE -cpu -ompthreads:1 -stable -mdbc_freeslip:1 EXISTING_N4_SEED FRESH_OUT");const pathfs::path folder=pathfs::absolute(argv[3]),tests=pathfs::path(__FILE__).parent_path().parent_path();Need(pathfs::equivalent(folder,tests/"outputs/upl_c08_asn4_window_GPU_r1/native_partial_r1"),"Only closed n4 partial input is admitted");Snapshot first(folder,Parts[0]),second(folder,Parts[1]);
  AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!pathfs::exists(cfg.DirOut),"Fresh CPU component output required");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr(),first,second);return 0;
}catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"CPU zero-step failed; preserve first result\n";return 2;}}

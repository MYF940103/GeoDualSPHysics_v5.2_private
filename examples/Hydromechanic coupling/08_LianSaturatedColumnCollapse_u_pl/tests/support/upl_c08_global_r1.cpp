// Actual case08 global state/FS/C/prescribed-Ace/Darcy composition, no momentum or step.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "JException.h"
#include "JCellSearch_inline.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <climits>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <vector>
JAppInfo AppInfo("UplC08Global","r1","06-11-2026");
namespace fs=std::filesystem;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static constexpr unsigned Fixed=2060,Soil=5000,Total=Fixed+Soil;
static constexpr double Height=2.;
template<class T>struct Copy{T* p;std::vector<T> v;Copy(T* a,unsigned n):p(a){if(p)v.assign(a,a+n);}void Restore()const{if(p&&!v.empty())memcpy(p,v.data(),sizeof(T)*v.size());}bool Equal()const{return !p||v.empty()||!memcmp(p,v.data(),sizeof(T)*v.size());}~Copy(){Restore();}};
template<class T>static bool EqualAt(const T* p,const std::vector<T>& b,unsigned q){return q<b.size()&&!memcmp(p+q,b.data()+q,sizeof(T));}
struct RestoreFlags{bool& feedback;bool& dynamic;bool& wall;bool f,d,w;~RestoreFlags(){feedback=f;dynamic=d;wall=w;}};
struct Reference{bool seen=false,selected=false;double p=0,j=0,expected=0,pbudget=0,jbudget=0;};
struct Coverage{std::array<unsigned long long,4> in{},off{},outside{},missing{};unsigned active=0,inactive=0;unsigned long long scalar_pairs=0,search_candidates=0;};
class Probe:public JSphCpuSingle{
  std::vector<unsigned> Map()const{
    Need(Np==Total&&Npb==Fixed,"Wrong retained7060 geometry");std::vector<unsigned> m(Total,UINT_MAX);unsigned ns=0,nb=0;
    for(unsigned q=0;q<Np;q++){Need(Idpc[q]<Total&&m[Idpc[q]]==UINT_MAX,"Unknown/duplicate native ID");m[Idpc[q]]=q;if(CODE_IsFluid(Codec[q])){Need(CODE_IsNormal(Codec[q])&&Idpc[q]>=Fixed,"Native soil code changed");ns++;}else{Need(CODE_IsFixed(Codec[q])&&Idpc[q]<Fixed,"Unexpected wall type");nb++;}}
    Need(ns==Soil&&nb==Fixed&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Retained ID/exclusion mismatch");return m;
  }
  static std::vector<std::string> Split(const std::string& line){std::stringstream s(line);std::vector<std::string> row;std::string v;while(std::getline(s,v,','))row.push_back(v);return row;}
  std::vector<Reference> LoadReference(const fs::path& path)const{
    std::ifstream input(path);Need(bool(input),"Closed nearest-state reference CSV missing");std::string line;Need(bool(std::getline(input,line)),"Reference header missing");const auto header=Split(line);
    const auto column=[&](const char* name){const auto at=std::find(header.begin(),header.end(),name);Need(at!=header.end(),"Reference schema missing required column");return size_t(at-header.begin());};
    const size_t idc=column("native_id"),selected=column("physical_near"),pc=column("p_B_actual"),jc=column("J_actual"),ec=column("p_B_reference"),pb=column("p_budget"),jb=column("J_budget");
    std::vector<Reference> out(Fixed);unsigned count=0,used=0;
    while(std::getline(input,line)){const auto row=Split(line);Need(row.size()==header.size(),"Truncated closed nearest reference row");const unsigned id=unsigned(std::stoul(row[idc]));Need(id<Fixed&&!out[id].seen,"Unknown/duplicate reference ID");auto& r=out[id];r.seen=true;r.selected=(row[selected]=="1");if(r.selected){r.p=std::stod(row[pc]);r.j=std::stod(row[jc]);r.expected=std::stod(row[ec]);r.pbudget=std::stod(row[pb]);r.jbudget=std::stod(row[jb]);Need(r.pbudget>0&&r.jbudget>0,"Invalid retained reference budget");used++;}count++;}
    Need(input.eof()&&count==Fixed&&used==410,"Closed nearest reference coverage mismatch");return out;
  }
  std::array<bool,4> Support(unsigned fluid,unsigned fixed,std::array<double,4>& rr)const{
    const double dx=Posc[fluid].x-Posc[fixed].x,dy=Posc[fluid].y-Posc[fixed].y,dz=Posc[fluid].z-Posc[fixed].z;
    rr[0]=dx*dx+0.+dz*dz;rr[1]=float(rr[0]);const float fx=float(dx),fy=float(dy),fz=float(dz);rr[2]=fx*fx+fy*fy+fz*fz;rr[3]=fx*fx+0.f+fz*fz;
    return {rr[0]<=double(KernelSize2)&&rr[0]>=ALMOSTZERO,float(rr[1])<=KernelSize2&&float(rr[1])>=ALMOSTZERO,float(rr[2])<=KernelSize2&&float(rr[2])>=ALMOSTZERO,float(rr[3])<=KernelSize2&&float(rr[3])>=ALMOSTZERO};
  }
  Coverage Audit(const std::vector<unsigned>& map,unsigned trial,std::ostream& pairs,std::ostream& walls)const{
    Coverage c;std::vector<unsigned> wallPairs(Fixed,0);
    // Test-only independent finite-geometry inspector: all5000x2060 pairs, not production work.
    for(unsigned id=Fixed;id<Total;id++){
      const unsigned fluid=map[id];std::vector<unsigned> searched;const auto ngs=nsearch::Init(Dcellc[fluid],true,DivData);
      for(int z=ngs.zini;z<ngs.zfin;z++)for(int y=ngs.yini;y<ngs.yfin;y++){const auto range=nsearch::ParticleRange(y,z,ngs,DivData);for(unsigned q=range.x;q<range.y;q++)if(CODE_IsFixed(Codec[q]))searched.push_back(q);}
      c.search_candidates+=searched.size();std::sort(searched.begin(),searched.end());Need(std::adjacent_find(searched.begin(),searched.end())==searched.end(),"Actual boundary nsearch duplicated a source");
      for(unsigned bid=0;bid<Fixed;bid++){
        const unsigned fixed=map[bid];std::array<double,4> rr;const auto in=Support(fluid,fixed,rr);c.scalar_pairs++;const bool any=in[0]||in[1]||in[2]||in[3];if(!any)continue;
        const bool covered=std::binary_search(searched.begin(),searched.end(),fixed);wallPairs[bid]++;
        for(unsigned k=0;k<4;k++)if(in[k]){c.in[k]++;c.off[k]+=unsigned(BoundModec[fixed]==BMODE_MDBC2OFF);c.outside[k]+=unsigned(fixed>=NpbOk);c.missing[k]+=unsigned(!covered);}
        Need(covered&&fixed<NpbOk&&BoundModec[fixed]==BMODE_MDBC2,"A real supported wall is OFF, outside NpbOk or absent from actual nsearch");
        pairs<<trial<<','<<id<<','<<bid<<','<<fixed<<','<<NpbOk<<','<<unsigned(BoundModec[fixed])<<','<<rr[0]<<','<<rr[1]<<','<<rr[2]<<','<<rr[3]<<','<<in[0]<<','<<in[1]<<','<<in[2]<<','<<in[3]<<','<<covered<<'\n';
      }
    }
    for(unsigned bid=0;bid<Fixed;bid++){const unsigned fixed=map[bid];if(fixed<NpbOk){Need(BoundModec[fixed]==(wallPairs[bid]?BMODE_MDBC2:BMODE_MDBC2OFF),"Current state eligibility disagrees with independent complete geometry");c.active+=unsigned(wallPairs[bid]>0);c.inactive+=unsigned(wallPairs[bid]==0);}else Need(wallPairs[bid]==0,"Ignored/outside-prefix wall has a real consumer pair");
      walls<<trial<<','<<bid<<','<<fixed<<','<<Posc[fixed].x<<','<<Posc[fixed].z<<','<<(fixed<NpbOk)<<','<<unsigned(BoundModec[fixed])<<','<<wallPairs[bid]<<'\n';}
    Need(c.scalar_pairs==static_cast<unsigned long long>(Soil)*Fixed&&c.active==410&&c.inactive==55,"Global geometry support counts changed");
    for(unsigned k=0;k<4;k++)Need(c.in[k]>0&&c.off[k]==0&&c.outside[k]==0&&c.missing[k]==0,"OFF/outside-prefix/search coverage invariant failed");return c;
  }
  void NoStep()const{Need(TimeStep==0&&Nstep==0&&!PoroJPrec&&!PosPrec,"Global fixture advanced a step or predictor");}
  void Manufacture(const std::vector<byte>& originalModes){
    for(unsigned q=0;q<Np;q++){Velrhopc[q]=TFloat4(0,0,0,RhopZero);Sigmac[q]=TSymMatrix3d(-32,8,16,-48,4,-64);Kplasticc[q]=0;PoroJc[q]=1;PoroThetac[q]=0;PorePress0c[q]=0;PorePressRatec[q]=1234567.f;
      PorePressc[q]=float(double(SoilCte.PoreWaterRho)*double(Gravity.z)*(Posc[q].z-Height));CorrMatc[q]=TMatrix3d(0);Acec[q]=TFloat3(0);TangenVelc[q]=TFloat3(0);FSTypec[q]=(q<Npb?FST_Boundary:FST_Inner);FSNormalc[q]=TFloat3(0);PosDivc[q]=0;BoundModec[q]=originalModes[q];}
  }
public:
  Probe(){PorosityObserver=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log,const fs::path& referencePath){
    Need(!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall,"Observer-only constructor required");AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Need(PorosityObserver&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&HydroMech&&!HydroMechDynamicSeepage&&Simulate2D&&TKernel==KERNEL_Cubic&&TStep==STEP_Symplectic&&TBoundary==BC_MDBC&&!PeriActive&&BoundModec&&BoundSlipModec&&TangenVelc,"Wrong legitimate observer initialization");
    Need(Dp==.04&&KernelH==float(.048)&&RhopZero==2072.5f&&Gravity==TFloat3(0,0,-9.81f)&&TimeMax==0&&NpbOk==465&&!HydroMechDrainage&&HydroMechTopLoadMode==HMLOAD_None&&!DynamicPoreConductivity&&!StrainSoftening&&!SoilBoundaryDerivativeSPR&&!SoilHourglassXi&&!Damping&&!SoilDamping&&!NoPenetration&&!Acec&&!BoundDerivativeVelc,"Global zero-step scope changed");
    const auto map=Map();const auto reference=LoadReference(referencePath);NoStep();
    const Copy<unsigned> ids(Idpc,Np),cells(Dcellc,Np),fstype(FSTypec,Np);const Copy<typecode> codes(Codec,Np);const Copy<tdouble3> pos(Posc,Np);const Copy<tfloat3> normal(BoundNormalc,Np),tan(TangenVelc,Np),load(HydroMechLoadAcec,Np),fsnormal(FSNormalc,Np);
    const Copy<tfloat4> vel(Velrhopc,Np);const Copy<tsymatrix3d> sigma(Sigmac,Np);const Copy<byte> modes(BoundModec,Np),selectors(BoundSlipModec,Np);const Copy<tmatrix3d> corr(CorrMatc,Np);const Copy<double> j(PoroJc,Np),theta(PoroThetac,Np);const Copy<float> p(PorePressc,Np),p0(PorePress0c,Np),rate(PorePressRatec,Np),plastic(Kplasticc,Np),posdiv(PosDivc,Np);
    const unsigned initialNpbOk=NpbOk;const auto oldInter=InterStep;const double oldSpeed=DynamicConductivitySpeedMax,oldVelMax=VelMax;const float oldVisc=ViscDtMax;
    std::ofstream ledger(fs::path(cfg->DirOut)/"ids.csv"),pairs(fs::path(cfg->DirOut)/"pairs.csv"),walls(fs::path(cfg->DirOut)/"walls.csv"),fields(fs::path(cfg->DirOut)/"fields.csv");for(auto* out:{&ledger,&pairs,&walls,&fields})*out<<std::setprecision(17);
    ledger<<"native_id,sorted_slot,is_fluid,x,y,z,original_mode,in_original_NpbOk\n";for(unsigned id=0;id<Total;id++){const auto q=map[id];ledger<<id<<','<<q<<','<<CODE_IsFluid(Codec[q])<<','<<Posc[q].x<<','<<Posc[q].y<<','<<Posc[q].z<<','<<unsigned(BoundModec[q])<<','<<(q<NpbOk)<<'\n';}
    pairs<<"trial,fluid_id,fixed_id,fixed_slot,current_NpbOk,mode,Darcy_rr2,FS_rr2,force_rr2,umbrella_rr2,in_Darcy,in_FS,in_force,in_umbrella,actual_nsearch_covered\n";
    walls<<"trial,fixed_id,sorted_slot,B_x,B_z,in_NpbOk,mode,all_geometry_support_union_pairs\n";
    fields<<"trial,native_id,is_fluid,x,z,J,theta,p_Pa,p0_Pa,vx,vy,vz,rho,sxx,sxy,sxz,syy,syz,szz,C11,C12,C13,C21,C22,C23,C31,C32,C33,FSType,FSnx,FSny,FSnz,PosDiv,Ace_x,Ace_y,Ace_z,rate_Pa_s,reference_p_error,reference_J_error\n";
    // Allocate ordinary scratch BEFORE private flags. No derivative scratch was budgeted at observer Init.
    InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();Need(Acec&&BoundDerivativeVelc==nullptr,"Observer allocation budget changed");
    Coverage coverage[2];std::vector<byte> baselineModes;std::vector<unsigned> offSlots;std::vector<float> bp,br,bp0,bpd;std::vector<double> bj,bt;std::vector<tfloat4> bv;std::vector<tfloat3> ba,btan,bfn;std::vector<tsymatrix3d> bs;std::vector<tmatrix3d> bc;std::vector<unsigned> bfs;
    double maxReferenceP=0,maxReferenceJ=0,maxAceError=0,maxRateAbs[2]={0,0},rateRms[2]={0,0};unsigned compared=0,referencePairs=0;bool negativeRejected=false;
    try{
      RestoreFlags restore{PorosityFeedback,DynamicPorePressure,DynamicPoreWall,PorosityFeedback,DynamicPorePressure,DynamicPoreWall};PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;
      for(unsigned trial=0;trial<2;trial++){
        Manufacture(modes.v);
        if(trial){Need(offSlots.size()==55,"OFF poison witness is empty or changed");const double nan=std::numeric_limits<double>::quiet_NaN();const float fnan=std::numeric_limits<float>::quiet_NaN();for(unsigned q:offSlots){PoroJc[q]=nan;PorePressc[q]=fnan;Sigmac[q]=TSymMatrix3d(nan,nan,nan,nan,nan,nan);CorrMatc[q]=TMatrix3d(nan);Acec[q]=TFloat3(fnan);}}
        ComputeFreeSurfaceTracking(); // Exactly one state refresh, then native FS/C and current wall C per trial.
        Need(ids.Equal()&&cells.Equal()&&codes.Equal()&&pos.Equal()&&normal.Equal()&&selectors.Equal()&&NpbOk==initialNpbOk,"Stage composition moved particles/cells/controls");
        coverage[trial]=Audit(map,trial,pairs,walls);
        for(unsigned q=0;q<Np;q++)if(CODE_IsFluid(Codec[q]))Acec[q]=TFloat3(-Gravity.x,-Gravity.y,-Gravity.z); // Prescribed same-stage a_true=0; no momentum solve.
        const Copy<float> inputp(PorePressc,Np);const Copy<double> inputj(PoroJc,Np),inputtheta(PoroThetac,Np);const Copy<tmatrix3d> inputc(CorrMatc,Np);
        ComputeDynamicPorePressureRateCpu(); // Owns actual wall-Ace extension before complete rate.
        Need(inputp.Equal()&&inputj.Equal()&&inputtheta.Equal()&&inputc.Equal(),"Darcy changed frozen p/J/theta/C inputs");
        for(unsigned id=0;id<Total;id++){
          const unsigned q=map[id];const bool fluid=CODE_IsFluid(Codec[q]);const bool active=(q<NpbOk&&BoundModec[q]==BMODE_MDBC2);if(!fluid&&!active)continue;
          Need(std::isfinite(PoroJc[q])&&PoroJc[q]>1.-double(SoilCte.Porosity)&&std::isfinite(PorePressc[q])&&std::isfinite(Acec[q].x)&&std::isfinite(Acec[q].y)&&std::isfinite(Acec[q].z),"Live global state is nonfinite/outside saturated domain");
          const auto cm=CorrMatc[q];const double cdet=cm.a11*cm.a33-cm.a13*cm.a31;Need(std::isfinite(cdet)&&cdet>0,"Live native/wall C not finite positive oriented");const auto vv=Velrhopc[q];Need(vv==TFloat4(0,0,0,RhopZero),"Manufactured physical wall/native velocity changed");const auto ssfinite=Sigmac[q];const auto nf=FSNormalc[q];for(double value:{ssfinite.xx,ssfinite.xy,ssfinite.xz,ssfinite.yy,ssfinite.yz,ssfinite.zz,cm.a11,cm.a12,cm.a13,cm.a21,cm.a22,cm.a23,cm.a31,cm.a32,cm.a33,double(nf.x),double(nf.y),double(nf.z),double(PosDivc[q]),PoroThetac[q],double(PorePress0c[q])})Need(std::isfinite(value),"Live stress/C/classification data nonfinite");
          const double aceError=(std::max)({fabs(double(Acec[q].x)+Gravity.x),fabs(double(Acec[q].y)+Gravity.y),fabs(double(Acec[q].z)+Gravity.z)});maxAceError=(std::max)(maxAceError,aceError);Need(aceError==0.,"Zero Ace+g source did not return the exact prescribed finite acceleration");
          double ep=0,ej=0;if(active){const auto& r=reference[id];Need(r.selected,"New active recipient absent from closed410 reference");ep=fabs(double(PorePressc[q])-r.expected);ej=fabs(PoroJc[q]-1.);Need(ep<=r.pbudget&&ej<=r.jbudget,"Closed nearest-reference p/J budgets failed");const float oldp=float(r.p);Need(!memcmp(PorePressc+q,&oldp,sizeof(float))&&!memcmp(PoroJc+q,&r.j,sizeof(double)),"Global active p/J differs from genuine closed state control");maxReferenceP=(std::max)(maxReferenceP,ep);maxReferenceJ=(std::max)(maxReferenceJ,ej);referencePairs++;}
          if(fluid){Need(std::isfinite(PorePressRatec[q]),"Native affine-quantized Darcy rate is nonfinite");maxRateAbs[trial]=(std::max)(maxRateAbs[trial],fabs(double(PorePressRatec[q])));rateRms[trial]+=double(PorePressRatec[q])*PorePressRatec[q];}
          if(trial){Need(EqualAt(PorePressc,bp,q)&&EqualAt(PoroJc,bj,q)&&EqualAt(PoroThetac,bt,q)&&EqualAt(Velrhopc,bv,q)&&EqualAt(Sigmac,bs,q)&&EqualAt(CorrMatc,bc,q)&&EqualAt(Acec,ba,q)&&EqualAt(PorePressRatec,br,q)&&EqualAt(PorePress0c,bp0,q)&&EqualAt(TangenVelc,btan,q)&&EqualAt(FSTypec,bfs,q)&&EqualAt(FSNormalc,bfn,q)&&EqualAt(PosDivc,bpd,q),"OFF poison changed a genuinely live field/output byte");compared++;}
          const auto ss=Sigmac[q];const auto nn=FSNormalc[q];fields<<trial<<','<<id<<','<<fluid<<','<<Posc[q].x<<','<<Posc[q].z<<','<<PoroJc[q]<<','<<PoroThetac[q]<<','<<PorePressc[q]<<','<<PorePress0c[q]<<','<<vv.x<<','<<vv.y<<','<<vv.z<<','<<vv.w<<','<<ss.xx<<','<<ss.xy<<','<<ss.xz<<','<<ss.yy<<','<<ss.yz<<','<<ss.zz<<','<<cm.a11<<','<<cm.a12<<','<<cm.a13<<','<<cm.a21<<','<<cm.a22<<','<<cm.a23<<','<<cm.a31<<','<<cm.a32<<','<<cm.a33<<','<<FSTypec[q]<<','<<nn.x<<','<<nn.y<<','<<nn.z<<','<<PosDivc[q]<<','<<Acec[q].x<<','<<Acec[q].y<<','<<Acec[q].z<<','<<PorePressRatec[q]<<',';if(active)fields<<ep;fields<<',';if(active)fields<<ej;fields<<'\n';
        }
        rateRms[trial]=sqrt(rateRms[trial]/Soil);
        if(!trial){baselineModes.assign(BoundModec,BoundModec+Np);for(unsigned q=0;q<NpbOk;q++)if(BoundModec[q]==BMODE_MDBC2OFF)offSlots.push_back(q);bp.assign(PorePressc,PorePressc+Np);bj.assign(PoroJc,PoroJc+Np);bt.assign(PoroThetac,PoroThetac+Np);bv.assign(Velrhopc,Velrhopc+Np);bs.assign(Sigmac,Sigmac+Np);bc.assign(CorrMatc,CorrMatc+Np);ba.assign(Acec,Acec+Np);br.assign(PorePressRatec,PorePressRatec+Np);bp0.assign(PorePress0c,PorePress0c+Np);btan.assign(TangenVelc,TangenVelc+Np);bfs.assign(FSTypec,FSTypec+Np);bfn.assign(FSNormalc,FSNormalc+Np);bpd.assign(PosDivc,PosDivc+Np);}
        else Need(!memcmp(BoundModec,baselineModes.data(),Np*sizeof(byte)),"Poison altered support classification or outside-prefix modes");
      }
      // Restore finite fields and a proved active state, then exercise the ORIGINAL in-range-OFF guard.
      memcpy(PorePressc,bp.data(),Np*sizeof(float));memcpy(PoroJc,bj.data(),Np*sizeof(double));memcpy(PoroThetac,bt.data(),Np*sizeof(double));memcpy(CorrMatc,bc.data(),Np*sizeof(tmatrix3d));memcpy(Acec,ba.data(),Np*sizeof(tfloat3));memcpy(Sigmac,bs.data(),Np*sizeof(tsymatrix3d));memcpy(BoundModec,baselineModes.data(),Np*sizeof(byte));
      const unsigned bad=map[254];Need(bad<NpbOk&&BoundModec[bad]==BMODE_MDBC2,"Selected original in-range negative receiver is not active");BoundModec[bad]=BMODE_MDBC2OFF;
      try{ComputeDynamicPorePressureRateCpu();}catch(const JException& e){negativeRejected=e.ToStr().find("Dynamic Darcy fixture produced a nonfinite pressure rate or conductivity-gradient speed.")!=std::string::npos;Need(negativeRejected,"Unexpected global negative exception");}
      Need(negativeRejected,"In-rangeOFF was silently accepted after global stage composition"); // No unchanged invalid-rate promise.
      NoStep();
    }catch(...){PosInteraction_Forces();InterStep=oldInter;throw;}
    PosInteraction_Forces();InterStep=oldInter;DynamicConductivitySpeedMax=oldSpeed;VelMax=oldVelMax;ViscDtMax=oldVisc;
    Need(NpbOk==initialNpbOk&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&!PeriActive&&!Acec&&!BoundDerivativeVelc&&ids.Equal()&&cells.Equal()&&codes.Equal()&&pos.Equal()&&normal.Equal()&&selectors.Equal(),"Original geometry/control/scratch not restored");
    vel.Restore();sigma.Restore();modes.Restore();tan.Restore();load.Restore();corr.Restore();j.Restore();theta.Restore();p.Restore();p0.Restore();rate.Restore();plastic.Restore();fstype.Restore();fsnormal.Restore();posdiv.Restore();
    Need(vel.Equal()&&sigma.Equal()&&modes.Equal()&&tan.Equal()&&load.Equal()&&corr.Equal()&&j.Equal()&&theta.Equal()&&p.Equal()&&p0.Equal()&&rate.Equal()&&plastic.Equal()&&fstype.Equal()&&fsnormal.Equal()&&posdiv.Equal(),"Original persistent arrays not restored");Map();NoStep();Need(compared==5410&&referencePairs==820&&offSlots.size()==55&&negativeRejected,"Global finite/poison/reference coverage incomplete");for(auto* out:{&ledger,&pairs,&walls,&fields}){out->flush();Need(bool(*out),"Global CSV write failed");}
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_c08_global_r1\",\"passed\":true,\"native_ids\":7060,\"soil\":5000,\"NpbOk\":"<<initialNpbOk<<",\"active\":410,\"OFF_in_prefix\":55,\"outside_prefix_checked\":1595,\"scalar_geometry_pairs_per_trial\":"<<coverage[0].scalar_pairs<<",\"consumer_support_pairs\":["<<coverage[0].in[0]<<','<<coverage[0].in[1]<<','<<coverage[0].in[2]<<','<<coverage[0].in[3]<<"],\"all_OFF_in_support_pairs\":0,\"all_supported_outside_prefix_pairs\":0,\"all_supported_missing_actual_nsearch_pairs\":0,\"genuine_nearest_p_J_reference_pairs\":"<<referencePairs<<",\"finite_poison_live_typed_field_equal_rows\":"<<compared<<",\"max_reference_p_error_Pa\":"<<maxReferenceP<<",\"max_reference_J_error\":"<<maxReferenceJ<<",\"max_prescribed_Ace_error\":"<<maxAceError<<",\"finite_affine_rate_absmax_Pa_s\":"<<maxRateAbs[0]<<",\"finite_affine_rate_RMS_Pa_s\":"<<rateRms[0]<<",\"poison_affine_rate_absmax_Pa_s\":"<<maxRateAbs[1]<<",\"poison_affine_rate_RMS_Pa_s\":"<<rateRms[1]<<",\"in_range_OFF_negative_rejected\":true,\"geometry_IDs_cells_arrays_controls_restored\":true,\"prescribed_Ace_not_actual_momentum\":true,\"actual_legacy_MdbcBoundCorrection_called\":false,\"physical_steps\":0,\"wet_contact_public_wall_or_physical_acceptance\":false}\n";done.flush();Need(bool(done),"Global completion write failed");
  }
};
int main(int argc,char** argv){try{
  Need(argc>=8&&std::string(argv[1])=="--global"&&std::string(argv[2])=="--reference","Use --global --reference ABS_CLOSED_NEAREST_WALLS_CSV -cpu -ompthreads:1 -stable -mdbc_freeslip SAME_OBSERVER_SEED FRESH_RESULT");const fs::path reference=argv[3];AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!fs::exists(cfg.DirOut),"Fresh CPU global zero-step output required");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe probe;probe.Execute(&cfg,AppInfo.LogPtr(),reference);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Global case08 diagnostic failed; preserve output\n";return 2;}}

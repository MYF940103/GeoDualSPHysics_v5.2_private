// Private Ck2 wall/free-surface composition on the actual C08 geometry; zero steps.
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JDsTimersCpu.h"
#include "JAppInfo.h"
#include "JLog2.h"
#include "FunSphKernel.h"
#include "FunctionsMath.h"
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
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("Ck2FreeWallCpu","r1","07-11-2026");
namespace fs=std::filesystem;
static void Need(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static double Dot(tdouble3 a,tdouble3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static tdouble3 Product(tmatrix3d a,tdouble3 b){return TDouble3(a.a11*b.x+a.a12*b.y+a.a13*b.z,a.a21*b.x+a.a22*b.y+a.a23*b.z,a.a31*b.x+a.a32*b.y+a.a33*b.z);}
static double MatrixNorm(tmatrix3d a){return (std::max)({fabs(a.a11)+fabs(a.a12)+fabs(a.a13),fabs(a.a21)+fabs(a.a22)+fabs(a.a23),fabs(a.a31)+fabs(a.a32)+fabs(a.a33)});}
template<class T>struct Copy{T* p;std::vector<T> v;Copy(T* a,unsigned n):p(a),v(a,a+n){}void Restore()const{std::memcpy(p,v.data(),v.size()*sizeof(T));}bool Equal()const{return !std::memcmp(p,v.data(),v.size()*sizeof(T));}~Copy(){Restore();}};
struct BorrowDerivative{tfloat3*& p;tfloat3* old;BorrowDerivative(tfloat3*& a,tfloat3* b):p(a),old(a){Need(!a,"Derivative scratch already owned");p=b;}~BorrowDerivative(){p=old;}};
struct Flags{bool &f,&d,&w,&c,&free;bool old[5];double &ck,&speed,oldck,oldspeed;tfloat3 &g,&cg,oldg,oldcg;~Flags(){f=old[0];d=old[1];w=old[2];c=old[3];free=old[4];ck=oldck;speed=oldspeed;g=oldg;cg=oldcg;}};
class Probe:public JSphCpuSingle{
  static constexpr unsigned Total=7060,Fixed=2060,Soil=5000,PerGroup=27;
  static constexpr double Slope=1./128.,Ck=2.,ManufacturedG=-1./16.,Drive=4.;
  using Row=std::array<double,18>;
  struct Fit{double condition;bool first;};
  struct Reference{double value,limit,chain,analytic,condition,k,lap;};
  double Top=0,Left=0,Right=0,Bed=0,MaxRatio=0,MaxHydroRatio=0,MaxWallRatio=0,MinSignal=DBL_MAX;
  unsigned RateRows=0,WallRows=0,Projected=0,AnalyticRows=0,ChainWitnesses=0,MaskInner[2]={},MaskSurface[2]={};
  void NoStep()const{Need(TimeStep==0&&Nstep==0&&!PosPrec&&!VelrhopPrec&&!PoroJPrec&&!PorePressPrec,"A physical stage/time was advanced");}
  bool Surface(unsigned p)const{return IsFreeSurfaceParticle(p,Codec,FSTypec);}
  bool Core(unsigned p)const{const auto x=Posc[p];return FSTypec[p]==FST_Inner&&x.x>Left+KernelSize&&x.x<Right-KernelSize&&x.z>Bed+KernelSize&&x.z<Top-KernelSize;}
  std::vector<unsigned> Map()const{std::vector<unsigned> map(Total,UINT_MAX);unsigned soil=0,wall=0;Need(Np==Total&&Npb==Fixed,"Native counts changed");for(unsigned p=0;p<Np;p++){const unsigned id=Idpc[p];Need(id<Total&&map[id]==UINT_MAX&&CODE_IsNormal(Codec[p]),"Unknown/duplicate/non-normal ID");map[id]=p;if(id<Fixed){Need(p<Npb&&CODE_IsFixed(Codec[p]),"Fixed native prefix/type changed");wall++;}else{Need(p>=Npb&&CODE_IsFluid(Codec[p]),"Soil prefix/type changed");soil++;}}Need(soil==Soil&&wall==Fixed&&!GetOutPosCount()&&!GetOutRhopCount()&&!GetOutMoveCount(),"Native/exclusion coverage differs");return map;}
  std::vector<Row> State()const{std::vector<Row> rows;const auto map=Map();for(unsigned id=Fixed;id<Total;id++){const unsigned p=map[id];const auto x=Posc[p];const auto v=Velrhopc[p];const auto s=Sigmac[p];rows.push_back({x.x,x.y,x.z,v.x,v.y,v.z,v.w,PorePressc[p],PorePress0c[p],PoroJc[p],PoroThetac[p],s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,Kplasticc[p]});for(double a:rows.back())Need(std::isfinite(a),"Nonfinite held soil field");}return rows;}
  double MirrorZ(unsigned p)const{return Posc[p].z+(p<Npb?double(BoundNormalc[p].z):0.);}
  double JOracle(unsigned p)const{return 1.+Slope*(MirrorZ(p)-1.);}
  double KOracle(unsigned p)const{const double solid=1.-double(SoilCte.Porosity),n=1.-solid/PoroJc[p],e=n/(1.-n),e0=double(SoilCte.Porosity)/solid;return double(SoilCte.HydraulicConductivity)*exp((e-e0)/Ck);}
  double Potential(unsigned p,double drive)const{return -ManufacturedG*Posc[p].z+drive*MirrorZ(p);}
  tdouble3 AceOracle(unsigned p,double drive)const{const double qz=(p<Npb&&BoundNormalc[p].z>0?-1.:1.);return TDouble3(0,0,-ManufacturedG+qz*drive);}
  bool Source(unsigned p)const{return CODE_IsFluid(Codec[p])||(p<Npb&&CODE_IsFixed(Codec[p])&&BoundModec[p]==BMODE_MDBC2);}
  Fit FitAt(tdouble3 at,tdouble3 original)const{
    tmatrix3d m=TMatrix3d(0);const double v0=double(MassFluid)/RhopZero;
    // Independent all-real-soil enumeration; normalized derivative MLS matrix, not a field fit.
    for(unsigned p=Npb;p<Np;p++)if(CODE_IsFluid(Codec[p])){const auto d=at-Posc[p];const float rr=float(d.x*d.x+d.z*d.z);if(rr>KernelSize2)continue;float fac=0;const double wab=rr==0?double(fsph::GetKernel_Wab<KERNEL_Cubic>(CSP,rr)):double(fsph::GetKernel_WabFac<KERNEL_Cubic>(CSP,rr,fac));const double v=v0*PoroJc[p],w=v*wab,gx=v*double(fac)*d.x*KernelH,gz=v*double(fac)*d.z*KernelH,x=d.x/KernelH,z=d.z/KernelH;
      m.a11+=w;m.a12+=x*w;m.a13+=z*w;m.a21+=gx;m.a22+=x*gx;m.a23+=z*gx;m.a31+=gz;m.a32+=x*gz;m.a33+=z*gz;}
    const double det=fmath::Determinant3x3(m);if(!std::isfinite(det)||fabs(det)<1e-3)return{0,false};const auto inv=fmath::InverseMatrix3x3(m,det);const auto shift=original-at;const double c=MatrixNorm(m)*MatrixNorm(inv)*(1.+(fabs(shift.x)+fabs(shift.z))/KernelH);Need(std::isfinite(c)&&c>0,"Nonfinite independent fit condition");return{(std::max)(1.,c),true};
  }
  double WallCondition(unsigned p)const{
    const auto target=Posc[p]+ToTDouble3(BoundNormalc[p]);const auto first=FitAt(target,target);if(first.first)return first.condition;
    double nearest=DBL_MAX;for(unsigned j=Npb;j<Np;j++)if(CODE_IsFluid(Codec[j])){const auto d=target-Posc[j];const double rr=d.x*d.x+d.z*d.z;if(float(rr)<=KernelSize2)nearest=(std::min)(nearest,rr);}
    Need(nearest<DBL_MAX,"Independent mirror has no real-source retry");double condition=0;unsigned ties=0;
    // Only the one nearest-source retry; max over exact nearest ties bounds traversal tie order.
    for(unsigned j=Npb;j<Np;j++)if(CODE_IsFluid(Codec[j])){const auto d=target-Posc[j];if(d.x*d.x+d.z*d.z==nearest){const auto fit=FitAt(Posc[j],target);Need(fit.first,"Nearest-source matrix is not first order");condition=(std::max)(condition,fit.condition);ties++;}}
    Need(ties&&condition>0,"Independent retry condition missing");return condition;
  }
  std::vector<unsigned> Receivers()const{
    std::vector<unsigned> groups[3],selected;const auto map=Map();for(unsigned id=Fixed;id<Total;id++){const unsigned p=map[id];const auto x=Posc[p];if(Surface(p))groups[0].push_back(p);else if(Core(p))groups[1].push_back(p);else if(FSTypec[p]==FST_Inner&&(x.x<=Left+KernelSize||x.x>=Right-KernelSize||x.z<=Bed+KernelSize))groups[2].push_back(p);}
    for(const auto& group:groups){Need(group.size()>=PerGroup,"Nonempty FS/core/near-wall receiver coverage is insufficient");for(unsigned i=0;i<PerGroup;i++)selected.push_back(group[(group.size()-1)*i/(PerGroup-1)]);}Need(selected.size()==81,"Expected81 disjoint receivers");return selected;
  }
  Reference Assemble(unsigned i,double drive,const std::vector<double>& wallCondition)const{
    const double water=SoilCte.PoreWaterRho,kw=SoilCte.PoreWaterBulkModulus,v0=double(MassFluid)/RhopZero,solid=1.-double(SoilCte.Porosity),n=1.-solid/PoroJc[i],ki=KOracle(i),dk=ki/(solid*Ck),scale=kw/n/(water*9.80665);
    double head=0,remainder=0,diva=0,lpabs=0,divabs=0,condition=1.;tdouble3 gradp=TDouble3(0),gradj=TDouble3(0),moment=TDouble3(0);tmatrix3d m=TMatrix3d(0);const auto ai=ToTDouble3(Acec[i]);
    // Potential differences plus exact Taylor remainder; no production cell walker/rate call.
    for(unsigned j=0;j<Np;j++)if(Source(j)){const auto d=Posc[i]-Posc[j];const double rr=d.x*d.x+d.z*d.z;if(rr>double(KernelSize2)||rr<ALMOSTZERO)continue;const double fac=fsph::GetKernel_Fac<KERNEL_Cubic>(CSP,float(rr));const auto g=d*fac,gi=Product(CorrMatc[i],g),gj=Product(CorrMatc[j],g);const double v=v0*PoroJc[j],w=v*Dot(d,gi+gj)/(rr+double(Eta2)),dp=double(PorePressc[i])-PorePressc[j],dphi=Potential(i,drive)-Potential(j,drive);const auto da=ToTDouble3(Acec[j])-ai;
      head+=w*(dp+water*dphi);remainder+=w*(Dot(ai,d)-dphi);diva+=v*Dot(da,gi);moment=moment+d*w;gradp=gradp-gi*(v*dp);gradj=gradj+gi*(v*(PoroJc[j]-PoroJc[i]));lpabs+=fabs(w*dp);divabs+=v*(fabs(da.x*gi.x)+fabs(da.z*gi.z));
      m.a11-=v*d.x*g.x;m.a13-=v*d.x*g.z;m.a31-=v*d.z*g.x;m.a33-=v*d.z*g.z;if(j<Npb)condition=(std::max)(condition,wallCondition[j]);}
    const auto c=CorrMatc[i];const double cm=(std::max)(fabs(c.a11)+fabs(c.a13),fabs(c.a31)+fabs(c.a33)),mm=(std::max)(fabs(m.a11)+fabs(m.a13),fabs(m.a31)+fabs(m.a33));condition=(std::max)(condition,(std::max)(1.,cm*mm));const auto b=gradp+ai*water;
    const double lap=head+water*(remainder+diva)-(Surface(i)?0.:Dot(b,moment)),chain=dk*Dot(gradj,b),absolute=ki*(lpabs+(Surface(i)?water*(fabs(ai.x*moment.x)+fabs(ai.z*moment.z)):fabs(gradp.x*moment.x)+fabs(gradp.z*moment.z))+water*divabs)+fabs(dk)*(fabs(gradj.x*b.x)+fabs(gradj.z*b.z));
    const double limit=(32*FLT_EPSILON+4096*DBL_EPSILON)*condition*(std::max)(1.,scale*absolute);Need(std::isfinite(limit)&&limit>0,"Invalid retained roundoff propagation");return{scale*(ki*lap+chain),limit,scale*chain,scale*dk*Slope*water*drive,condition,ki,scale*ki*lap};
  }
  void Field(){
    for(unsigned p=0;p<Np;p++){const bool soil=p>=Npb;const double j=soil?1.+Slope*(Posc[p].z-1.):1.;PoroJc[p]=j;PoroThetac[p]=0;const double rho=double(SoilCte.PoreWaterRho)+(double(RhopZero)-SoilCte.PoreWaterRho)/j;Velrhopc[p]=TFloat4(0,0,0,soil?float(rho):RhopZero);Sigmac[p]=tsymatrix3d{};Kplasticc[p]=0;HydroMechLoadAcec[p]=TFloat3(0);PorePressc[p]=float(-double(SoilCte.PoreWaterRho)*ManufacturedG*(Top-Posc[p].z));PorePress0c[p]=float(-double(SoilCte.PoreWaterRho)*ManufacturedG*(2.-Posc[p].z));PorePressRatec[p]=1234567.f;Need(std::isfinite(PorePressc[p])&&fabs(PorePressc[p])<256,"Manufacture left retained256 pressure scale");}
  }
  void Projection(std::ostream& out){
    std::vector<unsigned> surface;for(unsigned p=Npb;p<Np;p++)if(Surface(p)&&Posc[p].x>Left+2*KernelSize&&Posc[p].x<Right-2*KernelSize)surface.push_back(p);Need(surface.size()>=3,"Three central actual FS sign canaries missing");const Copy<float> pressure(PorePressc,Np),rates(PorePressRatec,Np);const Copy<unsigned> types(FSTypec,Np);const auto before=State();const float values[]={16,0,-16};for(unsigned j=0;j<3;j++)PorePressc[surface[j]]=values[j];std::vector<Row> supplied;for(unsigned p=0;p<Np;p++)supplied.push_back(StateRow(p));ApplyPorePressureBoundaries();unsigned clips=0;
    for(unsigned p=0;p<Np;p++){Row expected=supplied[p];if(p>=Npb&&Surface(p)&&expected[7]>0){expected[7]=0;clips++;}const auto actual=StateRow(p);Need(!std::memcmp(expected.data(),actual.data(),sizeof(Row)),"Projection changed an unselected or held native field");}
    Need(clips==1&&rates.Equal()&&types.Equal(),"Positive-only projection/rate/mask witness changed");for(unsigned j=0;j<3;j++)out<<Idpc[surface[j]]<<','<<FSTypec[surface[j]]<<','<<values[j]<<','<<PorePressc[surface[j]]<<','<<PorePress0c[surface[j]]<<'\n';Projected+=clips;pressure.Restore();const auto restored=State();Need(!std::memcmp(before.data(),restored.data(),before.size()*sizeof(Row)),"Projection pressure inputs were not restored");
  }
  Row StateRow(unsigned p)const{const auto x=Posc[p];const auto v=Velrhopc[p];const auto s=Sigmac[p];return{x.x,x.y,x.z,v.x,v.y,v.z,v.w,PorePressc[p],PorePress0c[p],PoroJc[p],PoroThetac[p],s.xx,s.xy,s.xz,s.yy,s.yz,s.zz,Kplasticc[p]};}
  void Check(unsigned field,std::ostream& rates,std::ostream& walls,std::ostream& mask,std::ostream& projection){
    const double drive=field?Drive:0.;Field();const auto before=State();ComputeFreeSurfaceTracking(); // Actual wall state -> fluid FS/C -> wall C.
    std::vector<double> conditions(Np,1.);unsigned active=0,inner=0,surface=0;
    for(unsigned p=0;p<NpbOk;p++)if(BoundModec[p]==BMODE_MDBC2){conditions[p]=WallCondition(p);active++;}
    for(unsigned p=Npb;p<Np;p++){if(Surface(p)){surface++;Need(Posc[p].z==Top&&PorePressc[p]==0,"Non-top true FS is incompatible with manufactured hydrostatic head");}else if(FSTypec[p]==FST_Inner)inner++;mask<<field<<','<<Idpc[p]<<','<<Posc[p].x<<','<<Posc[p].z<<','<<FSTypec[p]<<','<<PosDivc[p]<<','<<PorePressc[p]<<','<<PorePress0c[p]<<'\n';Acec[p]=ToTFloat3(AceOracle(p,drive));}
    Need(active&&inner&&surface,"Actual wall/true-inner/FS coverage is empty");MaskInner[field]=inner;MaskSurface[field]=surface;if(!field)Projection(projection);ComputeDynamicPoreWallAccelerationCpu();
    for(unsigned p=0;p<NpbOk;p++)if(BoundModec[p]==BMODE_MDBC2){const double condition=conditions[p],td=32768*DBL_EPSILON*condition,tf=64*FLT_EPSILON*condition,ej=fabs(PoroJc[p]-JOracle(p)),ep=fabs(double(PorePressc[p])-double(float(-double(SoilCte.PoreWaterRho)*ManufacturedG*(Top-Posc[p].z)))),ea=sqrt(Dot(ToTDouble3(Acec[p])-AceOracle(p,drive),ToTDouble3(Acec[p])-AceOracle(p,drive)));Need(ej<=2*td&&ep<=256*tf&&ea<=tf*(1.+fabs(ManufacturedG)+drive),"Wall J/head/Ace exceeds original condition-scaled affine budget");MaxWallRatio=(std::max)({MaxWallRatio,ej/(2*td),ep/(256*tf),ea/(tf*(1.+fabs(ManufacturedG)+drive))});walls<<field<<','<<Idpc[p]<<','<<Posc[p].x<<','<<Posc[p].z<<','<<MirrorZ(p)<<','<<JOracle(p)<<','<<PoroJc[p]<<','<<ej<<','<<2*td<<','<<ep<<','<<256*tf<<','<<ea<<','<<tf*(1.+fabs(ManufacturedG)+drive)<<','<<condition<<'\n';WallRows++;}
    const auto selected=Receivers();std::vector<Reference> refs;for(unsigned p:selected)refs.push_back(Assemble(p,drive,conditions));const Copy<tmatrix3d> matrices(CorrMatc,Np);const Copy<unsigned> types(FSTypec,Np);ComputeDynamicPorePressureRateCpu();
    for(unsigned p=Npb;p<Np;p++)Need(std::isfinite(PorePressRatec[p])&&PorePressRatec[p]!=1234567.f,"A soil rate is nonfinite or unwritten");
    for(unsigned j=0;j<selected.size();j++){const unsigned p=selected[j];const auto r=refs[j];const double got=PorePressRatec[p],error=fabs(got-r.value),actualk=GetDynamicConductivityCpu(p);Need(std::isfinite(actualk)&&actualk>0&&fabs(actualk-r.k)<=32768*DBL_EPSILON*r.condition*r.k,"Actual same-stage conductivity differs from independent void-ratio law");Need(error<=r.limit,"Actual Darcy differs from independent head/remainder reference");MaxRatio=(std::max)(MaxRatio,error/r.limit);if(!field){Need(fabs(got)<=r.limit,"Static total head generated rate outside original roundoff budget");MaxHydroRatio=(std::max)(MaxHydroRatio,fabs(got)/r.limit);}if(Core(p)){Need(fabs(got-r.analytic)<=r.limit,"True-core affine-J analytic product rule failed");AnalyticRows++;if(field){const double signal=fabs(r.analytic)/r.limit;Need(signal>1&&fabs(r.lap-r.analytic)>r.limit,"Omitted-chain negative control is vacuous");MinSignal=(std::min)(MinSignal,signal);ChainWitnesses++;}}rates<<field<<','<<Idpc[p]<<','<<Posc[p].x<<','<<Posc[p].z<<','<<FSTypec[p]<<','<<Core(p)<<','<<PoroJc[p]<<','<<actualk<<','<<r.k<<','<<got<<','<<r.value<<','<<r.limit<<','<<r.chain<<','<<r.analytic<<','<<r.lap<<','<<r.condition<<'\n';RateRows++;}
    const auto after=State();Need(!std::memcmp(before.data(),after.data(),before.size()*sizeof(Row))&&matrices.Equal()&&types.Equal(),"Zero-step closures/rate changed held soil state or FS/C");NoStep();
  }
public:
  Probe(){PorosityObserver=true;}
  void Execute(const JSphCfgRun* cfg,JLog2* log){
    Need(!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall,"Legitimate constant observer-only InitRun required");AppName=AppInfo.GetFullName();Log=log;CfgRun=cfg;Timersc->Config(false);LoadConfig(cfg);LoadCaseParticles();VisuConfig();ConfigDomain();ConfigRunMode();InitRunCpu();FreePartsInit();
    Need(PorosityObserver&&HydroMech&&!HydroMechDynamicSeepage&&Simulate2D&&TStep==STEP_Symplectic&&TKernel==KERNEL_Cubic&&TBoundary==BC_MDBC&&UseNormals&&BoundModec&&BoundSlipModec&&TangenVelc&&!PeriActive,"Retained C08 observer scope differs");Need(CaseNp==Total&&CaseNpb==Fixed&&CaseNfluid==Soil&&CaseNfixed==Fixed&&Dp==.04&&KernelH==float(.048)&&RhopZero==2072.5f&&SoilCte.Porosity==.35f&&SoilCte.PoreWaterRho==1000.f&&SoilCte.HydraulicConductivity==float(.0002),"Native material/geometry differs");Need(TimeMax==0&&!PartBegin&&!CaseNmoving&&!CaseNfloat&&!HydroMechDrainage&&!PoreShepardRegularization&&!SoilDamping&&!SoilHourglassXi&&!HourglassCpu&&!Shifting&&!Damping&&!NoPenetration&&!Acec&&!BoundDerivativeVelc&&!DynamicPoreConductivity&&HydroMechConductivityModel==0&&HydroMechConductivityCk==0,"Wrong zero-step constant input scope");NoStep();Map();Top=-DBL_MAX;bool seen[3]={};
    for(unsigned p=Npb;p<Np;p++)Top=(std::max)(Top,Posc[p].z);for(unsigned p=0;p<Npb;p++){const auto n=BoundNormalc[p];const auto face=Posc[p]+ToTDouble3(n)*.5;const unsigned k=n.z>0?2:(n.x>0?0:1);Need(n.y==0&&(k==2?n.x==0:n.z==0)&&Dot(ToTDouble3(n),ToTDouble3(n))>0&&TpSlipMode(BoundSlipModec[p])==(k==2?SLIP_NoSlip:SLIP_FreeSlip),"Actual axis-plane/mixed-slip walls differ");double& plane=k==2?Bed:(k==0?Left:Right);if(seen[k])Need(fabs(plane-(k==2?face.z:face.x))<=1e-6*Dp,"Actual face is not coplanar");else plane=k==2?face.z:face.x;seen[k]=true;}Need(seen[0]&&seen[1]&&seen[2]&&Top<2.&&fabs(Top+.5*Dp-2.)<1e-6*Dp,"Actual top/H2 or three physical planes differ");
    const Copy<tdouble3> pos(Posc,Np);const Copy<unsigned> ids(Idpc,Np),cells(Dcellc,Np),types(FSTypec,Np);const Copy<typecode> codes(Codec,Np);const Copy<tfloat4> vel(Velrhopc,Np);const Copy<tsymatrix3d> sigma(Sigmac,Np);const Copy<double> j(PoroJc,Np),theta(PoroThetac,Np);const Copy<float> p(PorePressc,Np),p0(PorePress0c,Np),rate(PorePressRatec,Np),kap(Kplasticc,Np),pd(PosDivc,Np);const Copy<tmatrix3d> c(CorrMatc,Np);const Copy<byte> modes(BoundModec,Np);const Copy<tfloat3> tan(TangenVelc,Np),fsnormal(FSNormalc,Np),normals(BoundNormalc,Npb),load(HydroMechLoadAcec,Np);
    std::ofstream rates(fs::path(cfg->DirOut)/"rates.csv"),walls(fs::path(cfg->DirOut)/"walls.csv"),mask(fs::path(cfg->DirOut)/"mask.csv"),projection(fs::path(cfg->DirOut)/"projection.csv");for(auto* f:{&rates,&walls,&mask,&projection})*f<<std::setprecision(17);rates<<"field,native_id,x,z,fstype,true_core,J,actual_k_m_s,void_ratio_k_reference,actual_rate,independent_rate,roundoff_limit,chain_rate,core_analytic_rate,omitted_chain_rate,condition\n";walls<<"field,native_id,x,z,actual_mirror_z,J_reference,J_actual,J_error,J_budget,p_error,p_budget,Ace_error,Ace_budget,condition\n";mask<<"field,native_id,x,z,fstype,posdiv,p,p0_fixed_H2\n";projection<<"native_id,fstype,input_p,actual_p,p0_unchanged\n";
    const auto inter=InterStep;InterStep=INTERSTEP_SymPredictor;PreInteraction_Forces();
    try{Need(Acec&&!BoundDerivativeVelc,"Observer scratch allocation differs");std::vector<tfloat3> derivative(Np,TFloat3(0));{BorrowDerivative borrow(BoundDerivativeVelc,derivative.data());Flags flags{PorosityFeedback,DynamicPorePressure,DynamicPoreWall,DynamicPoreConductivity,HydroMechFreeSeepage,{PorosityFeedback,DynamicPorePressure,DynamicPoreWall,DynamicPoreConductivity,HydroMechFreeSeepage},DynamicPoreConductivityCk,DynamicConductivitySpeedMax,DynamicPoreConductivityCk,DynamicConductivitySpeedMax,Gravity,CSP.gravity,Gravity,CSP.gravity};PorosityFeedback=DynamicPorePressure=DynamicPoreWall=DynamicPoreConductivity=HydroMechFreeSeepage=true;DynamicPoreConductivityCk=Ck;Gravity=CSP.gravity=TFloat3(0,0,float(ManufacturedG));for(unsigned field=0;field<2;field++)Check(field,rates,walls,mask,projection);}}catch(...){PosInteraction_Forces();InterStep=inter;throw;}PosInteraction_Forces();InterStep=inter;
    vel.Restore();sigma.Restore();j.Restore();theta.Restore();p.Restore();p0.Restore();rate.Restore();kap.Restore();pd.Restore();c.Restore();modes.Restore();tan.Restore();fsnormal.Restore();types.Restore();load.Restore();Need(pos.Equal()&&ids.Equal()&&cells.Equal()&&codes.Equal()&&normals.Equal()&&State().size()==Soil&&!Acec&&!BoundDerivativeVelc&&!PorosityFeedback&&!DynamicPorePressure&&!DynamicPoreWall&&!DynamicPoreConductivity&&!HydroMechFreeSeepage,"Original geometry/flags/scratch were not restored");NoStep();Need(RateRows==162&&WallRows>0&&Projected==1&&AnalyticRows==54&&ChainWitnesses==27,"Declared component coverage incomplete");for(auto* f:{&rates,&walls,&mask,&projection}){f->flush();Need(bool(*f),"CSV write failed");}
    std::ofstream done(fs::path(cfg->DirOut)/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"upl_ck2_free_wall_cpu_r1\",\"passed\":true,\"native_IDs\":7060,\"soil\":5000,\"fixed\":2060,\"fields\":2,\"receivers_per_field\":81,\"rate_rows\":"<<RateRows<<",\"wall_rows\":"<<WallRows<<",\"true_inner_counts\":["<<MaskInner[0]<<','<<MaskInner[1]<<"],\"FS_counts\":["<<MaskSurface[0]<<','<<MaskSurface[1]<<"],\"analytic_core_rows\":"<<AnalyticRows<<",\"nonzero_chain_witnesses\":"<<ChainWitnesses<<",\"positive_FS_canaries_projected\":"<<Projected<<",\"max_rate_over_original_budget\":"<<MaxRatio<<",\"max_static_rate_over_original_budget\":"<<MaxHydroRatio<<",\"max_wall_over_original_budget\":"<<MaxWallRatio<<",\"minimum_chain_signal_over_budget\":"<<MinSignal<<",\"J_slope\":"<<Slope<<",\"Ck\":2,\"manufactured_gravity_z\":"<<ManufacturedG<<",\"drive\":"<<Drive<<",\"mobility_gamma\":"<<double(SoilCte.PoreWaterRho)*9.80665<<",\"actual_top_particle_z\":"<<Top<<",\"p0_fixed_reference_H\":2,\"physical_steps\":0,\"actual_momentum_called\":false,\"public_scope_admitted\":false,\"Eq25_conservative_flux_proven\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
  }
};
int main(int argc,char** argv){try{Need(argc>=6&&std::string(argv[1])=="--check","Use --check -cpu -ompthreads:1 -stable -mdbc_freeslip SAME_OBSERVER_SEED FRESH_RESULT");AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=2;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());Need(cfg.Cpu&&!cfg.PrintInfo&&!cfg.PartBegin&&!fs::exists(cfg.DirOut),"Fresh CPU zero-step component required");cfg.Sv_Binx=cfg.Sv_Info=cfg.Sv_Csv=cfg.Sv_Vtk=false;AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");Probe test;test.Execute(&cfg,AppInfo.LogPtr());return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Ck2 composition failed; preserve partial output\n";return 2;}}

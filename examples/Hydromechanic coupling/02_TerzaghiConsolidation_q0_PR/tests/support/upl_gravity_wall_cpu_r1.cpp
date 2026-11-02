// Private true Run and a separate typed native reader. No integrator or field override.
#define main RetainedGravityWallNativeMain
#include "upl_cpu_public_native_r1.cpp"
#undef main
#include "JSphCpuSingle.h"
#include "JSphCfgRun.h"
#include "JXml.h"
#include "JLog2.h"

namespace gravitywall {
constexpr unsigned Soil=1024,Fixed=256,Total=1280,Columns=33;
constexpr double Dp=1./512.,V0=Dp*Dp,GravityZ=-8.,DtC=1./33554432.,DtH=1./67108864.,End=1./32768.,Cadence=1./8388608.;
struct Window{const char* name;double dt,end,cadence;unsigned steps,samples;};
static bool Variable(const std::string& model){Need(model=="constant"||model=="variable","Model must be constant|variable");return model=="variable";}
static Window Select(const std::string& name,bool variable){
  if(name=="smoke"){Need(!variable,"Only the declared constant two-step smoke is admitted");return{"smoke",DtC,2.*DtC,DtC,2,3};}
  if(name=="coarse")return{"coarse",DtC,End,Cadence,1024,257};
  if(name=="half")return{"half",DtH,End,Cadence,2048,257};
  throw std::runtime_error("Use the declared smoke|coarse|half window");
}
static void Fresh(const fs::path& p){Need(!fs::exists(p),"Retained output protected: "+p.string());}
static double Law(double j,bool variable){return variable&&j!=1.?K0*std::exp((j-1.)/((1.-N0)*Ck)):K0;}
static void Runtime(const fs::path& path,const Window& w,bool variable,bool reference){
  Need(!reference||w.samples==257,"Reference reader admits only retained full coarse/half controls");JXml x;x.LoadFile(path.string());
  const auto* h=x.GetNodeError("case.execution.special.hydromechanics");const auto* c=x.GetNodeError("case.execution.constants");const auto* s=x.GetNodeError("case.execution.special.soils");
  auto hv=[&](const char* key,double value){Need(x.ReadElementDouble(h,key,"value")==value,"Runtime hydromechanics differs: "+std::string(key));};
  hv("HydroMech",1);hv("PoreWaterRho",Rhow);hv("PoreWaterBulkModulus",Kw);hv("Porosity",N0);hv("HydraulicConductivity",.0001);hv("PoreDtSafety",.1);
  hv("PoreShepardRegularization",0);hv("PoreCompressionGradCorr",1);hv("PoreCompressionSourceMode",0);hv("HydroMechInitMode",0);hv("HydroMechTopLoadMode",0);hv("HydroMechDrainage",0);
  hv("HydroMechDynamicSeepage",reference?1.:0.);hv("HydroMechConductivityModel",reference&&variable?1.:0.);Need(x.ReadElementDouble(h,"HydroMechConductivityCk","value",reference&&!variable,0.)==(reference&&variable?Ck:0.),"Runtime public Ck differs (only old constant reference may omit its default0 key)");
  const auto g=TDouble3(0,0,reference?0.:GravityZ);Need(x.GetAttributeDouble3(x.GetFirstElement(c,"gravity"))==g&&x.GetAttributeDouble3(x.GetFirstElement(x.GetNodeError("case.casedef.constantsdef"),"gravity"))==g,"Both real runtime gravity declarations must match the selected private/reference scope");
  Need(x.ReadElementDouble(c,"rhop0","value")==Rho0&&x.ReadElementDouble(c,"dp","value")==Dp&&double(float(x.ReadElementDouble(c,"h","value")))==double(float(1.8*Dp))&&x.ReadElementDouble(c,"massfluid","value")==Rho0*V0&&x.ReadElementDouble(c,"massbound","value")==Rho0*V0&&x.ReadElementDouble(c,"cflnumber","value")==.2,"Runtime wall geometry/material differs");
  Need(x.ReadElementDouble(s,"ModulusE","value")==268435456.&&x.ReadElementDouble(s,"PRvs","value")==0&&x.ReadElementDouble(s,"phi","value")==0&&x.ReadElementDouble(s,"coh","value")==1e12&&x.ReadElementDouble(s,"dlt","value")==0,"Runtime elastic material differs");
  unsigned columns=0;std::vector<bool> velocity(32,false);
  for(auto* e=x.GetNodeError("case.execution.special.initialize")->FirstChildElement("fluidvelocity");e;e=e->NextSiblingElement("fluidvelocity")){
    const auto* only=x.GetFirstElement(e,"onlypos");const double lo=x.GetAttributeDouble(x.GetFirstElement(only,"posmin"),"x"),hi=x.GetAttributeDouble(x.GetFirstElement(only,"posmax"),"x"),col=lo/Dp-.25;
    Need(col==std::round(col)&&col>=0&&col<32&&hi==lo+.5*Dp&&!velocity[unsigned(col)]&&x.GetAttributeDouble3(x.GetFirstElement(e,"direction"))==TDouble3(1,0,0),"Runtime sine column/direction differs");
    Need(float(x.GetAttributeDouble(x.GetFirstElement(e,"velocity"),"v"))==float(A*std::sin(2.*std::acos(-1.)*(col+.5)*Dp/Lx)),"Runtime initial sine differs");velocity[unsigned(col)]=true;columns++;
  }Need(columns==32,"All32 real fluidvelocity initializers are required; a zero-field component seed is not equivalent");
  std::map<std::string,double> p;for(auto* e=x.GetNodeError("case.execution.parameters")->FirstChildElement("parameter");e;e=e->NextSiblingElement("parameter"))Need(p.emplace(x.GetAttributeStr(e,"key"),x.GetAttributeDouble(e,"value")).second,"Duplicate runtime parameter");
  auto pv=[&](const char* key,double value){Need(p.count(key)&&p.at(key)==value,"Runtime option/clock differs: "+std::string(key));};
  pv("SavePosDouble",1);pv("Boundary",2);pv("SlipMode",3);pv("NoPenetration",0);pv("StepAlgorithm",2);pv("Kernel",2);pv("ViscoTreatment",1);pv("Visco",0);pv("ArtificialStress",0);
  pv("SoilStressRateGradCorr",1);pv("SoilHourglassXi",0);pv("SoilBoundaryDerivativeSPR",0);pv("SoilDamping",0);pv("DensityDT",0);pv("Shifting",0);pv("PartsOutMax",0);pv("RhopOutMin",700);pv("RhopOutMax",3000);pv("ZPeriodicIncX",0);
  pv("DtIni",w.dt);pv("DtFixed",w.dt);pv("TimeMax",w.end);pv("TimeOut",w.cadence);
  for(const char* key:{"XZPeriodic","XPeriodicIncY","XPeriodicIncZ","YPeriodicIncX","YPeriodicIncZ","ZPeriodicIncY"})Need(!p.count(key),"Only rectangular tangential Z periodicity is admitted");
}
// Immutable Load(...,model) is used only for public g0 references. Private output
// has exactly three J arrays; it must not be passed to that public six-array loader.
static Native LoadPrivate(JPartDataBi4& f){
  Metadata(f,-1);Native a;a.ids=NativeArray<unsigned>(f,"Idp",Total,DatUint);a.pos=NativeArray<tdouble3>(f,"Posd",Total,DatDouble3);Need(!f.ArrayExists("Pos"),"Double saved positions required");
  a.vel=NativeArray<tfloat3>(f,"Vel",Total,DatFloat3);a.rhop=NativeArray<float>(f,"Rhop",Total,DatFloat);a.legacykk=NativeArray<tfloat3>(f,"Sigma_kk",Total,DatFloat3);a.legacyij=NativeArray<tfloat3>(f,"Sigma_ij",Total,DatFloat3);
  a.sk=NativeArray<tdouble3>(f,"SigmaState_kk",Total,DatDouble3);a.si=NativeArray<tdouble3>(f,"SigmaState_ij",Total,DatDouble3);a.plastic=NativeArray<float>(f,"Kplastic",Total,DatFloat);a.fstype=NativeArray<unsigned>(f,"FSType",Total,DatUint);
  a.normal=NativeArray<tfloat3>(f,"FSNormal",Total,DatFloat3);a.load=NativeArray<tfloat3>(f,"HydroMechLoadAce",Total,DatFloat3);a.p=NativeArray<float>(f,"PorePress",Total,DatFloat);a.p0=NativeArray<float>(f,"PorePress0",Total,DatFloat);a.excess=NativeArray<float>(f,"ExcessPorePress",Total,DatFloat);
  a.j=NativeArray<double>(f,"PoroVolumeRatio",Total,DatDouble);a.n=NativeArray<double>(f,"PoroPorosity",Total,DatDouble);a.theta=NativeArray<double>(f,"PoroThetaLastStage",Total,DatDouble);
  for(const char* key:{"PoroCurrentVolume","PoroMixtureDensity","PoroHydraulicConductivity","PosDiv"})Need(!f.ArrayExists(key),"Private3J schema must not pretend public native extras");
  a.slot.assign(Total,~0u);for(unsigned p=0;p<Total;p++){Need(a.ids[p]<Total&&a.slot[a.ids[p]]==~0u,"Invalid/duplicate native ID");a.slot[a.ids[p]]=p;}for(unsigned p:a.slot)Need(p!=~0u,"Missing native ID");return a;
}
static std::vector<tdouble3> Initial(const Native& a){
  std::vector<tdouble3> out(Total);std::vector<bool> soil(Soil,false),fixed(Fixed,false);unsigned band=0;
  for(unsigned id=0;id<Total;id++){const unsigned p=a.slot[id];const auto x=a.pos[p];out[id]=x;const double ix=x.x/Dp-.5,iz=x.z/Dp-.5;
    Need(x.y==0&&ix==std::round(ix)&&iz==std::round(iz)&&iz>=0&&iz<32,"Initial tensor lattice differs");
    if(id<Fixed){Need((id<128?(ix>=-4&&ix<0):(ix>=32&&ix<36))&&Norm2(a.vel[p])==0&&a.rhop[p]==Rho0&&a.j[p]==1&&a.n[p]==0&&a.theta[p]==0&&a.p[p]==0&&Norm2(a.sk[p])==0&&Norm2(a.si[p])==0,"Initial fixed4-layer state differs");const unsigned key=unsigned(ix<0?ix+4:ix-28)+8*unsigned(iz);Need(key<Fixed&&!fixed[key],"Repeated fixed initial point");fixed[key]=true;continue;}
    Need(ix>=0&&ix<32,"Initial soil x lattice differs");const unsigned key=unsigned(ix)+32*unsigned(iz);Need(key<Soil&&!soil[key],"Repeated soil initial point");soil[key]=true;
    Need(a.vel[p].x==float(A*std::sin(2.*std::acos(-1.)*x.x/Lx))&&a.vel[p].y==0&&a.vel[p].z==0&&a.p[p]==0&&a.p0[p]==0&&Norm2(a.sk[p])==0&&Norm2(a.si[p])==0&&a.j[p]==1&&a.n[p]==N0&&a.theta[p]==0,"Initial native sine/p0/J state differs");
    band+=unsigned((std::min)(x.x,Width-x.x)<=2.*double(float(1.8*Dp)));
  }Need(band==256,"Original256-material-point wall band differs");return out;
}
static void Read(const Window& w,bool variable,bool reference,const fs::path& dir,const fs::path& xml,const fs::path& target){
  Runtime(xml,w,variable,reference);Fresh(target);Sequence(dir,w.samples);fs::create_directory(target);
  std::ofstream inertial(target/"physical.bin",std::ios::binary),accelerated(target/"frame.bin",std::ios::binary),original(target/"original15.bin",std::ios::binary),history(target/"history.csv"),ids(target/"native_ids.csv"),fixed(target/"fixed_ids.csv"),markers(target/"fixed_samples.csv"),last(target/"last_poro.csv"),posdiv;
  const unsigned head[]={Soil,Columns,w.samples},originalHead[]={Total,15,w.samples};inertial.write(reinterpret_cast<const char*>(head),12);accelerated.write(reinterpret_cast<const char*>(head),12);original.write(reinterpret_cast<const char*>(originalHead),12);
  for(auto* o:{&history,&ids,&fixed,&markers,&last})*o<<std::setprecision(17);if(reference){posdiv.open(target/"reference_PosDiv.csv");posdiv<<std::setprecision(17)<<"part,id,native_PosDiv\n";}
  ids<<"row,id,x0,y0,z0,wall_band\n";fixed<<"row,id,x0,y0,z0,plane_x\n";last<<"id,J,n,theta\n";markers<<"part,id,x,y,z,vx,vy,vz,p,J,n_zero_marker,theta_zero_marker\n";
  history<<"part,time_s,saved_step,dt_s,signed_dterror_s,frame_energy_ratio,inertial_energy_ratio,pressure_RMS_Pa,frame_material_displacement_max_mm,max_abs_J_minus_1,min_n,max_n,min_current_k_m_s,max_current_k_m_s,k_span_over_k0,k_change_over_k0,max_coupled_CFL,max_Ddt_h2,min_continuous_margin,max_ledger_relative_error,unweighted_mean_vz,unweighted_mean_frame_vz,uniform_body_velocity_shift\n";
  std::vector<tdouble3> initial;double e0=0,maxEnergy=0,maxJ=0,maxSpan=0,maxChange=0,maxCfl=0,maxDiff=0,minMargin=DBL_MAX,maxLedger=0,minError=DBL_MAX,maxError=-DBL_MAX;unsigned rows=0,markerRows=0;
  const double h=double(float(1.8*Dp)),gamma=Rhow*9.80665,gz=reference?0.:GravityZ;
  for(unsigned part=0;part<w.samples;part++){
    JPartDataBi4 file;file.LoadFilePart(dir.string(),part,0,1);
    Need(file.GetNpiece()==1&&file.Get_Npok()==Total&&!file.Get_Nout()&&file.Get_CaseNp()==Total&&file.Get_CaseNfluid()==Soil&&file.Get_CaseNfixed()==Fixed&&!file.Get_CaseNmoving()&&!file.Get_CaseNfloat(),"Native1280 wall set/exclusions differ");
    Need(file.Get_Data2d()&&!file.Get_Symmetry()&&!file.Get_NpDynamic()&&!file.Get_ReuseIds()&&file.Get_PeriMode()==PERI_Z,"Only2D fixed-x/pure-Z-periodic native scope is admitted");
    Need(file.Get_Dp()==Dp&&file.Get_H()==h&&file.Get_Rhop0()==Rho0&&file.Get_MassFluid()==Rho0*V0&&file.Get_MassBound()==Rho0*V0,"Native wall geometry/inertia differs");
    const double time=file.Get_TimeStep();const unsigned step=part?unsigned(std::llround(part*w.cadence/w.dt))-1:0;
    Need(time==part*w.cadence&&file.Get_Step()==step&&file.GetPart()->ExistsValue("SymplecticDtPre",DatDouble)&&file.GetPart()->GetvDouble("SymplecticDtPre")==w.dt,"Actual saved clock/zero-based step/locked dt differs");
    Need(file.GetPart()->ExistsValue("dterror",DatDouble),"Native signed dterror missing");const double error=file.GetPart()->GetvDouble("dterror");Need(std::isfinite(error)&&error<=1e-14,"Original signed fixed-step guard failed");minError=(std::min)(minError,error);maxError=(std::max)(maxError,error);
    Metadata(file,reference?(variable?1:0):-1);const Native a=reference?::Load(file,Total,variable?1:0):LoadPrivate(file);
    if(!part){initial=Initial(a);for(unsigned id=0;id<Total;id++){const auto x=initial[id];if(id<Fixed)fixed<<id<<','<<id<<','<<x.x<<','<<x.y<<','<<x.z<<','<<(x.x<0?0.:Width)<<'\n';else ids<<id-Fixed<<','<<id<<','<<x.x<<','<<x.y<<','<<x.z<<','<<((std::min)(x.x,Width-x.x)<=2.*h)<<'\n';}}
    inertial.write(reinterpret_cast<const char*>(&time),8);accelerated.write(reinterpret_cast<const char*>(&time),8);original.write(reinterpret_cast<const char*>(&time),8);Original15(original,a);
    double energy=0,labEnergy=0,p2=0,umax=0,jn=0,nlo=DBL_MAX,nhi=0,klo=DBL_MAX,khi=0,change=0,cflmax=0,diffmax=0,marginmin=DBL_MAX,frameLedger=0,meanVz=0,meanFrameVz=0;
    for(unsigned id=0;id<Total;id++){
      const unsigned p=a.slot[id];const auto x=a.pos[p],s=a.sk[p],q=a.si[p];const auto v=a.vel[p];
      Need(a.plastic[p]==0&&a.rhop[p]>=700&&a.rhop[p]<=3000&&a.p0[p]==0&&Norm2(a.load[p])==0&&a.excess[p]==float(a.p[p]-a.p0[p]),"Elastic/passive-rho/p0/load/native-excess guard failed");
      Need(a.legacykk[p].x==float(s.x)&&a.legacykk[p].y==float(s.y)&&a.legacykk[p].z==float(s.z)&&a.legacyij[p].x==float(q.x)&&a.legacyij[p].y==float(q.y)&&a.legacyij[p].z==float(q.z),"Float stress display does not round actual double state");
      if(id<Fixed){Need(!std::memcmp(&x,&initial[id],sizeof(tdouble3))&&Norm2(v)==0&&a.rhop[p]==Rho0&&a.n[p]==0&&a.theta[p]==0&&a.j[p]>1.-N0,"Fixed physical wall geometry/velocity or CPU zero markers differ");if(reference)Need(a.volume[p]==0&&a.rho[p]==0&&a.k[p]==0,"Reference CPU fixed derived zero markers differ");markers<<part<<','<<id<<','<<x.x<<','<<x.y<<','<<x.z<<','<<v.x<<','<<v.y<<','<<v.z<<','<<a.p[p]<<','<<a.j[p]<<','<<a.n[p]<<','<<a.theta[p]<<'\n';markerRows++;continue;}
      const double j=a.j[p],n=1.-(1.-N0)/j,V=V0*j,rho=Rhow+(Rho0-Rhow)/j,k=Law(j,variable);
      Need(x.y==0&&x.x>0&&x.x<Width&&x.z>0&&x.z<Lz&&j>1.-N0&&std::fabs(j-1.)<=1e-4&&n>0&&n<1&&std::isfinite(V)&&V>0&&std::isfinite(rho)&&rho>0&&std::isfinite(k)&&k>0,"Original weak saturated/current-k/no-wrap domain failed");
      Need(Close(a.n[p],n)&&std::fabs((1.-a.n[p])*j-(1.-N0))<=5e-13,"Native n/solid-volume ledger failed");frameLedger=(std::max)(frameLedger,std::fabs(a.n[p]-n)/n);
      if(reference){Need(Close(a.volume[p],V)&&Close(a.rho[p],rho)&&Close(a.k[p],k),"Reference CPU native volume/inertia/k ledger differs");frameLedger=(std::max)({frameLedger,std::fabs(a.volume[p]-V)/V,std::fabs(a.rho[p]-rho)/rho,std::fabs(a.k[p]-k)/k});posdiv<<part<<','<<id<<','<<a.posdiv[p]<<'\n';}
      const tdouble3 u=x-initial[id],xf=TDouble3(x.x,x.y,x.z-.5*gz*time*time),vf=TDouble3(v.x,v.y,double(v.z)-gz*time),uf=TDouble3(u.x,u.y,u.z-.5*gz*time*time);
      const double tr=s.x+s.y+s.z,mean=tr/3.,dev=(s.x-mean)*(s.x-mean)+(s.y-mean)*(s.y-mean)+(s.z-mean)*(s.z-mean)+2.*Norm2(q),stored=dev/(4.*Shear)+tr*tr/(18.*Bulk)+n*double(a.p[p])*a.p[p]/(2.*Kw);
      energy+=V*(.5*rho*Norm2(vf)+stored);labEnergy+=V*(.5*rho*Norm2(v)+stored);
      const double B=Kw/n,D=B*k/gamma,cf=std::sqrt((Bulk+4.*Shear/3.+B)/rho)*w.dt/h,df=D*w.dt/(h*h),margin=rho*B/(Bulk+4.*Shear/3.+B)-Rhow;
      Need(std::isfinite(cf)&&cf<=.01&&std::isfinite(df)&&df<=.01&&w.dt<=double(float(.1))*h*h/D&&margin>64.*DBL_EPSILON*(std::max)(rho,Rhow),"Original saved necessary acoustic/diffusion/continuous-domain screen failed");
      std::array<double,Columns> row={x.x,x.y,x.z,double(v.x),double(v.y),double(v.z),double(a.p[p]),double(a.p0[p]),j,a.theta[p],s.x,q.x,q.z,s.y,q.y,s.z,double(a.plastic[p]),double(a.fstype[p]),double(a.normal[p].x),double(a.normal[p].y),double(a.normal[p].z),double(a.load[p].x),double(a.load[p].y),double(a.load[p].z),double(a.rhop[p]),u.x,u.y,u.z,double(a.excess[p]),a.n[p],reference?a.volume[p]:V,reference?a.rho[p]:rho,reference?a.k[p]:k};
      for(double value:row)Need(std::isfinite(value),"Nonfinite common33 output");inertial.write(reinterpret_cast<const char*>(row.data()),Columns*8);row[0]=xf.x;row[1]=xf.y;row[2]=xf.z;row[3]=vf.x;row[4]=vf.y;row[5]=vf.z;row[25]=uf.x;row[26]=uf.y;row[27]=uf.z;accelerated.write(reinterpret_cast<const char*>(row.data()),Columns*8);
      p2+=double(a.p[p])*a.p[p];meanVz+=v.z;meanFrameVz+=vf.z;umax=(std::max)(umax,1000.*std::sqrt(Norm2(uf)));jn=(std::max)(jn,std::fabs(j-1.));nlo=(std::min)(nlo,n);nhi=(std::max)(nhi,n);klo=(std::min)(klo,k);khi=(std::max)(khi,k);change=(std::max)(change,std::fabs(k/K0-1.));cflmax=(std::max)(cflmax,cf);diffmax=(std::max)(diffmax,df);marginmin=(std::min)(marginmin,margin);rows++;
      if(part+1==w.samples)last<<id<<','<<j<<','<<a.n[p]<<','<<a.theta[p]<<'\n';
    }
    if(!part){e0=energy;Need(std::isfinite(e0)&&e0>0,"Initial wave energy empty");}const double ratio=energy/e0;Need(std::isfinite(ratio)&&ratio<=1.1,"Original energy budget failed in the soil accelerating frame");
    maxEnergy=(std::max)(maxEnergy,ratio);maxJ=(std::max)(maxJ,jn);maxSpan=(std::max)(maxSpan,(khi-klo)/K0);maxChange=(std::max)(maxChange,change);maxCfl=(std::max)(maxCfl,cflmax);maxDiff=(std::max)(maxDiff,diffmax);minMargin=(std::min)(minMargin,marginmin);maxLedger=(std::max)(maxLedger,frameLedger);
    history<<part<<','<<time<<','<<step<<','<<w.dt<<','<<error<<','<<ratio<<','<<labEnergy/e0<<','<<std::sqrt(p2/Soil)<<','<<umax<<','<<jn<<','<<nlo<<','<<nhi<<','<<klo<<','<<khi<<','<<(khi-klo)/K0<<','<<change<<','<<cflmax<<','<<diffmax<<','<<marginmin<<','<<frameLedger<<','<<meanVz/Soil<<','<<meanFrameVz/Soil<<','<<gz*time<<'\n';
  }
  Need(rows==Soil*w.samples&&markerRows==Fixed*w.samples&&maxJ>(w.samples==3?0.:1e-8)&&(!variable||w.samples==3||maxSpan>=.005),"Original full coverage/natural J/k activation screen failed");
  for(auto* o:{&inertial,&accelerated,&original,&history,&ids,&fixed,&markers,&last}){o->flush();Need(bool(*o),"Typed native review write failed");}if(reference){posdiv.flush();Need(bool(posdiv),"Reference native PosDiv export failed");}
  std::ofstream done(target/"completion.json");done<<std::setprecision(17)<<"{\"passed\":true,\"stage\":\"upl_gravity_wall_cpu_r1\",\"window\":\""<<w.name<<"\",\"model\":\""<<(variable?"variable":"constant")<<"\",\"backend\":\""<<(reference?"CPU_public_g0_reference":"CPU_private_tangential_gravity")<<"\",\"samples\":"<<w.samples<<",\"native_count\":1024,\"fixed_count\":256,\"total_native_count\":1280,\"common_columns\":33,\"dt_s\":"<<w.dt<<",\"cadence_s\":"<<w.cadence<<",\"actual_end_s\":"<<w.end<<",\"gravity_z_m_s2\":"<<gz<<",\"conductivity_Ck\":"<<(variable?Ck:0.)<<",\"original_arrays\":15,\"native_J_arrays\":"<<(reference?6:3)<<",\"V_rho_k_derived_not_native\":"<<(reference?"false":"true")<<",\"native_PosDiv_available\":"<<(reference?"true":"false")<<",\"public_dynamic_metadata\":"<<(reference?"true":"false")<<",\"soil_native_ledger_checks\":"<<rows<<",\"fixed_zero_marker_checks\":"<<markerRows<<",\"fixed_frame_transform_applied\":false,\"max_frame_energy_ratio\":"<<maxEnergy<<",\"max_abs_J_minus_1\":"<<maxJ<<",\"max_k_span_over_k0\":"<<maxSpan<<",\"max_k_change_over_k0\":"<<maxChange<<",\"max_saved_coupled_CFL\":"<<maxCfl<<",\"max_saved_Ddt_h2\":"<<maxDiff<<",\"min_continuous_margin\":"<<minMargin<<",\"max_ledger_relative_error\":"<<maxLedger<<",\"min_signed_dterror_s\":"<<minError<<",\"max_signed_dterror_s\":"<<maxError<<",\"half_comparison_performed\":false,\"g0_frame_or_body_comparison_performed\":false,\"face_or_force_audit_performed\":false,\"force_stage_gradient_independently_observed\":false,\"raw_SHA_or_owned_exit_verified_by_reader\":false,\"public_or_normal_gravity_accepted\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Native completion write failed");
}
class WallGravityCpu:public JSphCpuSingle{
  const bool variable_;
public:
  explicit WallGravityCpu(bool variable):variable_(variable){PorosityObserver=PorosityFeedback=DynamicPorePressure=DynamicPoreWall=true;DynamicPoreConductivity=variable;DynamicPoreConductivityCk=variable?::Ck:0.;}
  void Finish(const fs::path& out,const gravitywall::Window& w){
    Need(PorosityObserver&&PorosityFeedback&&DynamicPorePressure&&DynamicPoreWall&&DynamicPoreConductivity==variable_&&DynamicPoreConductivityCk==(variable_?::Ck:0.)&&!HydroMechDynamicSeepage&&HydroMechConductivityModel==0&&HydroMechConductivityCk==0,"Actual Run left its explicit private model");
    Need(HydroMech&&Simulate2D&&TStep==STEP_Symplectic&&!PartBegin&&CaseNpb==gravitywall::Fixed&&CaseNfluid==gravitywall::Soil&&CaseNp==gravitywall::Total&&!CaseNfloat&&!CaseNmoving&&!PeriX&&!PeriY&&PeriZ&&PeriZinc.x==0&&PeriZinc.y==0&&std::fabs(PeriZinc.z)==::Lz&&OmpThreads==1&&Gravity==TFloat3(0,0,gravitywall::GravityZ)&&CSP.gravity==Gravity&&TBoundary==BC_MDBC&&UseNormals&&BoundNormalc&&BoundModec,"Actual Run wall/gravity/backend scope differs");
    Need(TimeStep==w.end&&Nstep==w.steps&&SymplecticDtPre==w.dt&&!PosPrec&&!VelrhopPrec&&!SigmaPrec&&!PorePressPrec&&!PoroJPrec,"Actual Run end/steps/locked dt/PRE release differs");
    Need(double(SoilCte.HydraulicConductivity)==::K0&&double(SoilCte.Porosity)==::N0&&double(RhopZero)==::Rho0&&double(SoilCte.PoreWaterRho)==::Rhow&&double(SoilCte.PoreWaterBulkModulus)==::Kw&&double(SoilCte.ModulusK)==::Bulk&&double(SoilCte.ModulusG)==::Shear,"Actual loaded material differs");
    Need(std::isfinite(DynamicConductivitySpeedMax)&&DynamicConductivitySpeedMax>=0&&(variable_||DynamicConductivitySpeedMax==0),"Actual last-force cache invalid");std::vector<unsigned> order(gravitywall::Total,~0u);unsigned left=0,right=0;
    for(unsigned p=0;p<Np;p++)if(CODE_IsNormal(Codec[p])){const unsigned id=Idpc[p];Need(id<gravitywall::Total&&order[id]==~0u,"Actual final native ID/code differs");order[id]=p;
      if(id<gravitywall::Fixed){Need(CODE_IsFixed(Codec[p])&&Velrhopc[p].x==0&&Velrhopc[p].y==0&&Velrhopc[p].z==0&&Velrhopc[p].w==::Rho0&&(BoundSlipModec?TpSlipMode(BoundSlipModec[p]):SlipMode)==SLIP_FreeSlip,"Actual fixed physical velocity/FreeSlip differs");const auto b=ToTDouble3(BoundNormalc[p]);const double plane=Posc[p].x+.5*b.x;Need(b.y==0&&b.z==0&&b.x!=0&&plane==(b.x>0?0.: ::Width)&&double(Gravity.x)*b.x+double(Gravity.y)*b.y+double(Gravity.z)*b.z==0.,"Actual opposing x normals or strict tangent gravity differs");if(b.x>0)left++;else right++;}
      else Need(CODE_IsFluid(Codec[p]),"Actual soil owner is not normal fluid");
    }Need(left==128&&right==128,"Both opposing fixed wall owners are required");
    gravitywall::Fresh(out/"live_final.csv");gravitywall::Fresh(out/"actual_complete.json");std::ofstream live(out/"live_final.csv");live<<std::setprecision(17)<<"id,J,n,theta\n";
    for(unsigned id=0;id<gravitywall::Total;id++){Need(order[id]!=~0u,"Final native missing");const unsigned p=order[id];if(id<gravitywall::Fixed)continue;double n,V,rho;GetPorosityFeedbackStateCpu(p,n,V,rho);Need(std::isfinite(PoroJc[p])&&PoroJc[p]>1.-::N0&&std::isfinite(PoroThetac[p])&&n>0&&n<1&&Kplasticc[p]==0,"Actual final soil ledger/elastic state invalid");live<<id<<','<<PoroJc[p]<<','<<n<<','<<PoroThetac[p]<<'\n';}live.flush();Need(bool(live),"Final live export failed");
    std::ofstream done(out/"actual_complete.json");done<<std::setprecision(17)<<"{\"passed\":true,\"stage\":\"upl_gravity_wall_cpu_r1\",\"window\":\""<<w.name<<"\",\"model\":\""<<(variable_?"variable":"constant")<<"\",\"actual_production_Run\":true,\"private_feedback_and_complete_rate_and_wall\":true,\"private_conductivity_Ck\":"<<(variable_?::Ck:0.)<<",\"public_master\":false,\"physical_fields_rewritten_by_fixture\":false,\"native_count\":1024,\"fixed_count\":256,\"completed_steps\":"<<Nstep<<",\"actual_end_s\":"<<TimeStep<<",\"dt_s\":"<<SymplecticDtPre<<",\"gravity_z_m_s2\":-8,\"predictor_histories_released\":true,\"last_force_gradient_speed_m_s\":"<<DynamicConductivitySpeedMax<<",\"face_or_force_audit_performed\":false,\"public_or_normal_gravity_accepted\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Actual completion write failed");
  }
};
}
int main(int argc,char** argv){try{
  Need(argc>=4,"Use --solver MODEL WINDOW ordinaryCPUargs, --read MODEL WINDOW DATA XML NEWREVIEW or --read-reference MODEL coarse|half DATA XML NEWREVIEW");const std::string action=argv[1];const bool variable=gravitywall::Variable(argv[2]);const auto w=gravitywall::Select(argv[3],variable);
  if(action=="--read"||action=="--read-reference"){Need(argc==7,"Reader requires MODEL WINDOW DATA XML NEWREVIEW");gravitywall::Read(w,variable,action=="--read-reference",argv[4],argv[5],argv[6]);return 0;}
  Need(action=="--solver"&&argc>=7,"Solver requires MODEL WINDOW and ordinary explicit CPU arguments");AppInfo.ConfigRunPaths(argv[0]);std::vector<char*> args{argv[0]};for(int i=4;i<argc;i++)args.push_back(argv[i]);JSphCfgRun cfg;cfg.LoadArgv(int(args.size()),args.data());
  Need(cfg.Cpu&&cfg.OmpThreads==1&&!cfg.PrintInfo&&!fs::exists(cfg.DirOut)&&cfg.PartBegin==0&&cfg.NstepsBreak==0&&cfg.TimeMax<0&&cfg.TimePart<0&&!cfg.SvAllSteps,"Fresh CPU OMP1 true Run with XML clocks and no override/restart required");gravitywall::Runtime(cfg.CaseName+".xml",w,variable,false);
  AppInfo.ConfigOutput(cfg.CreateDirs,cfg.CsvSepComa,cfg.DirOut,cfg.DirDataOut);AppInfo.LogInit(AppInfo.GetDirOut()+"/Run.out");gravitywall::WallGravityCpu fixture(variable);fixture.Run(AppInfo.GetFullName(),&cfg,AppInfo.LogPtr());fixture.Finish(cfg.DirOut,w);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Private tangential-gravity CPU wall Run/read rejected; preserve evidence\n";return 2;}}

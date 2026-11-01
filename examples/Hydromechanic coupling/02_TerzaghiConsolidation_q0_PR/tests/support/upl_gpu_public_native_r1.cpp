// Offline public-GPU output/schema comparison; no solver entry or backend relabelling.
// Reuse only backend-neutral typed BI4 helpers from the immutable CPU reader.
#define main RetainedCpuPublicNativeMain
#include "upl_cpu_public_native_r1.cpp"
#undef main
#include "JXml.h"

namespace gpupublic {
struct Recipe {
  bool wall,smoke;int model;unsigned soil,fixed,total,samples;
  double dp,h,v0,dt,cadence,end;
};
static Recipe Declare(const std::string& geometry,const std::string& model,const std::string& window,double dt){
  Need(geometry=="Periodic"||geometry=="Wall","Geometry must be Periodic or Wall");
  Need(model=="constant"||model=="smooth","Model must be constant or smooth");
  Need(window=="Smoke"||window=="Full","Window must be Smoke or Full");
  Recipe r{};r.wall=geometry=="Wall";r.smoke=window=="Smoke";r.model=model=="smooth"?1:0;
  r.soil=r.wall?1024:512;r.fixed=r.wall?256:0;r.total=r.soil+r.fixed;r.samples=r.smoke?3:257;
  r.dp=r.wall?1./512.:1./256.;r.h=double(float(1.8*r.dp));r.v0=r.dp*r.dp;r.dt=dt;
  const double coarse=r.wall?std::ldexp(1.,-25):std::ldexp(1.,-24);
  Need(dt==coarse||(!r.smoke&&dt==coarse*.5),"Undeclared actual fixed step");
  r.cadence=r.smoke?dt:std::ldexp(1.,-23);r.end=(r.samples-1)*r.cadence;return r;
}
static void Runtime(const fs::path& path,const Recipe& r){
  JXml x;x.LoadFile(path.string());const auto* h=x.GetNodeError("case.execution.special.hydromechanics");
  const auto* s=x.GetNodeError("case.execution.special.soils");const auto* c=x.GetNodeError("case.execution.constants");
  auto hv=[&](const char* key,double v){Need(x.ReadElementDouble(h,key,"value")==v,std::string("Runtime hydromechanics differs: ")+key);};
  hv("HydroMech",1);hv("PoreWaterRho",Rhow);hv("PoreWaterBulkModulus",Kw);hv("Porosity",N0);hv("HydraulicConductivity",1e-4);
  hv("PoreShepardRegularization",0);hv("PoreCompressionGradCorr",1);hv("PoreCompressionSourceMode",0);hv("HydroMechInitMode",0);hv("HydroMechTopLoadMode",0);hv("HydroMechDrainage",0);
  Need(x.ReadElementBool(h,"HydroMechDynamicSeepage","value",true,false),"GPU public runtime master must be true");
  Need(x.ReadElementUnsigned(h,"HydroMechConductivityModel","value",true,0)==unsigned(r.model)&&x.ReadElementDouble(h,"HydroMechConductivityCk","value",true,0.)==(r.model?Ck:0.),"GPU public runtime model/Ck differs");
  Need(double(float(x.ReadElementDouble(h,"PoreDtSafety","value")))==double(float(.1)),"Original pore safety changed");
  Need(x.ReadElementDouble(s,"ModulusE","value")==268435456.&&x.ReadElementDouble(s,"PRvs","value")==0&&x.ReadElementDouble(s,"phi","value")==0&&x.ReadElementDouble(s,"coh","value")==1e12&&x.ReadElementDouble(s,"dlt","value")==0,"Runtime elastic material differs");
  Need(Norm2(x.GetAttributeDouble3(x.GetFirstElement(c,"gravity")))==0&&x.ReadElementDouble(c,"cflnumber","value")==.2&&x.ReadElementDouble(c,"rhop0","value")==Rho0&&x.ReadElementDouble(c,"dp","value")==r.dp&&double(float(x.ReadElementDouble(c,"h","value")))==r.h&&x.ReadElementDouble(c,"massfluid","value")==Rho0*r.v0,"Runtime geometry/g0/material differs");
  if(r.wall)Need(x.ReadElementDouble(c,"massbound","value")==Rho0*r.v0,"Runtime wall mass differs");
  std::map<std::string,double> p;for(auto* e=x.GetNodeError("case.execution.parameters")->FirstChildElement("parameter");e;e=e->NextSiblingElement("parameter"))Need(p.emplace(x.GetAttributeStr(e,"key"),x.GetAttributeDouble(e,"value")).second,"Duplicate runtime parameter");
  auto pv=[&](const char* key,double v){Need(p.count(key)&&p.at(key)==v,std::string("Runtime option/clock differs: ")+key);};
  pv("SavePosDouble",1);pv("StepAlgorithm",2);pv("Kernel",2);pv("ViscoTreatment",1);pv("Visco",0);pv("ArtificialStress",0);pv("SoilStressRateGradCorr",1);pv("SoilHourglassXi",0);pv("SoilBoundaryDerivativeSPR",0);pv("SoilDamping",0);pv("DensityDT",0);pv("Shifting",0);pv("PartsOutMax",0);pv("RhopOutMin",700);pv("RhopOutMax",3000);
  pv("DtFixed",r.dt);pv("DtIni",r.dt);pv("TimeMax",r.end);pv("TimeOut",r.cadence);
  if(r.wall){pv("Boundary",2);pv("SlipMode",3);pv("NoPenetration",0);pv("ZPeriodicIncX",0);Need(!p.count("XZPeriodic")&&!p.count("XPeriodicIncZ"),"Only tangential wall periodicity admitted");}
  else{pv("XZPeriodic",1);Need(!p.count("XPeriodicIncZ")&&!p.count("ZPeriodicIncX"),"Only rectangular XZ periodicity admitted");}
}
template<class T>static bool Bits(const T& a,const T& b){return std::memcmp(&a,&b,sizeof(T))==0;}
static double Header(JPartDataBi4& f,const Recipe& r,unsigned part){
  Need(f.GetNpiece()==1&&f.Get_Npok()==r.total&&!f.Get_Nout()&&f.Get_CaseNp()==r.total&&f.Get_CaseNfixed()==r.fixed&&f.Get_CaseNfluid()==r.soil&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat(),"Native pieces/counts/exclusion differ");
  Need(f.Get_Data2d()&&!f.Get_Symmetry()&&!f.Get_NpDynamic()&&!f.Get_ReuseIds()&&f.Get_PeriMode()==(r.wall?PERI_Z:PERI_XZ),"Native 2D/periodic schema differs");
  Need(f.Get_Dp()==r.dp&&f.Get_H()==r.h&&f.Get_Rhop0()==Rho0&&f.Get_MassFluid()==Rho0*r.v0&&(!r.wall||f.Get_MassBound()==Rho0*r.v0),"Native material/geometry differs");
  const double time=part*r.cadence;const unsigned step=part?unsigned(std::llround(time/r.dt))-1:0;
  Need(f.Get_TimeStep()==time&&f.Get_Step()==step,"Actual native clock/zero-based saved step differs");
  Need(f.GetPart()->ExistsValue("SymplecticDtPre",DatDouble)&&f.GetPart()->GetvDouble("SymplecticDtPre")==r.dt,"Actual locked step missing/wrong");
  Need(f.GetPart()->ExistsValue("dterror",DatDouble),"Typed signed dterror missing");const double error=f.GetPart()->GetvDouble("dterror");
  Need(std::isfinite(error)&&error<=1e-14,"Original signed dterror guard failed");return error;
}
template<class T>static void Match(JPartDataBi4& control,const char* name,TpData type,const std::vector<T>& actual,const std::vector<unsigned>& aslot,const std::vector<unsigned>& cslot){
  const auto old=NativeArray<T>(control,name,unsigned(actual.size()),type);
  for(unsigned id=0;id<aslot.size();id++)Need(Bits(actual[aslot[id]],old[cslot[id]]),std::string("Private/public native bit difference: ")+name+" ID="+std::to_string(id));
}
static std::vector<unsigned> Slots(const std::vector<unsigned>& id){
  std::vector<unsigned> slot(id.size(),~0u);for(unsigned p=0;p<id.size();p++){Need(id[p]<id.size()&&slot[id[p]]==~0u,"Private native ID missing/duplicate/out-of-range");slot[id[p]]=p;}return slot;
}
static void Compare(const Recipe& r,const fs::path& controlDir,const fs::path& publicDir,const fs::path& runtime,const fs::path& out){
  Need(!fs::exists(out)&&fs::is_directory(out.parent_path()),"Fresh review output required; retained results protected");
  Need(!fs::equivalent(controlDir,publicDir),"Private control and public output must differ");Runtime(runtime,r);Sequence(controlDir,r.samples);Sequence(publicDir,r.samples);fs::create_directory(out);
  std::ofstream exact(out/"common.csv"),extra(out/"public_extra.csv"),ids(out/"native_ids.csv"),fixed(out/"fixed_ids.csv"),history(out/"history.csv"),inputs(out/"input_files.csv");
  for(auto* s:{&exact,&extra,&ids,&fixed,&history})*s<<std::setprecision(17);
  exact<<"part,time_s,saved_step,locked_dt_s,signed_dterror_s,original15_exact,J_exact,theta_exact,soil_n_exact,actual_clock_step_dterror_exact\n";
  extra<<"part,id,is_soil,J,last_stage_theta,private_n,public_n,current_volume,mixture_density,hydraulic_conductivity,actual_native_PosDiv\n";
  ids<<"row,id,x0,y0,z0,wall_band\n";fixed<<"row,id,x0,y0,z0,plane_x\n";inputs<<"part,private_filename,public_filename\n";
  history<<"part,time_s,saved_step,signed_dterror_s,energy_ratio,max_abs_J_minus_1,min_soil_n,max_soil_n,min_current_k,max_current_k,k_span_over_k0,max_ledger_relative_error,max_coupled_CFL,max_Ddt_h2,max_abs_native_PosDiv\n";
  std::vector<tdouble3> initial(r.total);double e0=0,maxEnergy=0,maxJ=0,maxSpan=0,maxLedger=0,maxCfl=0,maxDiff=0,maxPosDiv=0,minError=DBL_MAX,maxError=-DBL_MAX;
  unsigned soilChecks=0,markerChecks=0,commonChecks=0,bandCount=0;
  for(unsigned part=0;part<r.samples;part++){
    JPartDataBi4 old,now;old.LoadFilePart(controlDir.string(),part,0,1);now.LoadFilePart(publicDir.string(),part,0,1);
    const double oe=Header(old,r,part),ne=Header(now,r,part),ot=old.Get_TimeStep(),nt=now.Get_TimeStep(),od=old.GetPart()->GetvDouble("SymplecticDtPre"),nd=now.GetPart()->GetvDouble("SymplecticDtPre");
    Need(Bits(oe,ne)&&Bits(ot,nt)&&Bits(od,nd)&&old.Get_Step()==now.Get_Step(),"Private/public actual clock, locked step or signed dterror bits differ");
    Metadata(old,-1);Metadata(now,r.model);const Native a=Load(now,r.total,r.model);
    for(const char* key:{"PoroVolumeRatio","PoroPorosity","PoroThetaLastStage"})Need(old.ArrayExists(key),"Private observer schema missing");
    for(const char* key:{"PoroCurrentVolume","PoroMixtureDensity","PoroHydraulicConductivity","PosDiv"})Need(!old.ArrayExists(key),"Private control is not the frozen three-array GPU schema");
    const auto oldid=NativeArray<unsigned>(old,"Idp",r.total,DatUint),cslot=Slots(oldid);
    Match(old,"Idp",DatUint,a.ids,a.slot,cslot);Match(old,"Posd",DatDouble3,a.pos,a.slot,cslot);Need(!old.ArrayExists("Pos"),"Private control does not save double positions");
    Match(old,"Vel",DatFloat3,a.vel,a.slot,cslot);Match(old,"Sigma_kk",DatFloat3,a.legacykk,a.slot,cslot);Match(old,"Sigma_ij",DatFloat3,a.legacyij,a.slot,cslot);Match(old,"FSNormal",DatFloat3,a.normal,a.slot,cslot);Match(old,"HydroMechLoadAce",DatFloat3,a.load,a.slot,cslot);
    Match(old,"Rhop",DatFloat,a.rhop,a.slot,cslot);Match(old,"Kplastic",DatFloat,a.plastic,a.slot,cslot);Match(old,"PorePress",DatFloat,a.p,a.slot,cslot);Match(old,"PorePress0",DatFloat,a.p0,a.slot,cslot);Match(old,"ExcessPorePress",DatFloat,a.excess,a.slot,cslot);
    Match(old,"SigmaState_kk",DatDouble3,a.sk,a.slot,cslot);Match(old,"SigmaState_ij",DatDouble3,a.si,a.slot,cslot);Match(old,"FSType",DatUint,a.fstype,a.slot,cslot);Match(old,"PoroVolumeRatio",DatDouble,a.j,a.slot,cslot);Match(old,"PoroThetaLastStage",DatDouble,a.theta,a.slot,cslot);
    const auto oldn=NativeArray<double>(old,"PoroPorosity",r.total,DatDouble);double lo=DBL_MAX,hi=0,nlo=DBL_MAX,nhi=0,jn=0,ledger=0,cfl=0,diff=0,posdiv=0;
    for(unsigned id=0;id<r.total;id++){
      const unsigned p=a.slot[id],q=cslot[id];const bool soil=id>=r.fixed;const double j=a.j[p];
      Need(j>1.-N0&&a.plastic[p]==0&&a.rhop[p]>=700&&a.rhop[p]<=3000&&a.p0[p]==0&&Norm2(a.load[p])==0&&a.excess[p]==float(a.p[p]-a.p0[p]),"Original J/elastic/passive/p0/load/excess guard failed");
      Need(a.legacykk[p].x==float(a.sk[p].x)&&a.legacykk[p].y==float(a.sk[p].y)&&a.legacykk[p].z==float(a.sk[p].z)&&a.legacyij[p].x==float(a.si[p].x)&&a.legacyij[p].y==float(a.si[p].y)&&a.legacyij[p].z==float(a.si[p].z),"Legacy stress not rounded from actual double state");
      if(!part){
        initial[id]=a.pos[p];Need(a.pos[p].y==0&&j==1.&&a.theta[p]==0&&a.p[p]==0&&Norm2(a.sk[p])==0&&Norm2(a.si[p])==0,"Fresh native initial state differs");
        if(soil){const double ix=a.pos[p].x/r.dp-.5,iz=a.pos[p].z/r.dp-.5;Need(ix==std::round(ix)&&iz==std::round(iz)&&ix>=0&&ix<32&&iz>=0&&iz<(r.wall?32:16),"Initial soil lattice differs");const float vx=float(A*std::sin(2.*std::acos(-1.)*a.pos[p].x/Lx));Need(a.vel[p].x==vx&&a.vel[p].y==0&&a.vel[p].z==0,"Initial sine velocity differs");const bool band=r.wall&&(std::min)(a.pos[p].x,Width-a.pos[p].x)<=2.*r.h;bandCount+=unsigned(band);ids<<id-r.fixed<<','<<id<<','<<a.pos[p].x<<','<<a.pos[p].y<<','<<a.pos[p].z<<','<<band<<'\n';}
        else{Need(a.pos[p].x<0||a.pos[p].x>Width,"Fixed point inside soil");fixed<<id<<','<<id<<','<<a.pos[p].x<<','<<a.pos[p].y<<','<<a.pos[p].z<<','<<(a.pos[p].x<0?0.:Width)<<'\n';}
      }
      posdiv=(std::max)(posdiv,std::fabs(double(a.posdiv[p])));
      if(!soil){
        Need(Bits(a.pos[p],initial[id])&&Norm2(a.vel[p])==0&&a.rhop[p]==Rho0&&a.theta[p]==0,"Fixed physical state changed");
        Need(a.n[p]==0&&a.volume[p]==0&&a.rho[p]==0&&a.k[p]==0,"Public fixed outputs are not explicit nonphysical zero markers");
        Need(oldn[q]==1.-(1.-N0)/j,"Private fixed n is not the original reconstructed sample");markerChecks++;
      }else{
        Need(Bits(a.n[p],oldn[q]),"Private/public soil native porosity bits differ");
        const double n=1.-(1.-N0)/j,V=r.v0*j,rho=Rhow+(Rho0-Rhow)/j,ki=r.model&&j!=1.?K0*std::exp((j-1.)/((1.-N0)*Ck)):K0;
        Need(a.pos[p].y==0&&a.pos[p].x>0&&a.pos[p].x<(r.wall?Width:Lx)&&a.pos[p].z>0&&a.pos[p].z<Lz&&std::fabs(j-1.)<=1e-4&&n>0&&n<1&&std::isfinite(ki)&&ki>0,"Original weak saturated geometry/domain failed");
        const double got[]={a.n[p],a.volume[p],a.rho[p],a.k[p]},ref[]={n,V,rho,ki};for(unsigned k=0;k<4;k++){Need(Close(got[k],ref[k]),"Public native derived ledger differs from same saved J");ledger=(std::max)(ledger,std::fabs(got[k]-ref[k])/(std::max)(std::fabs(ref[k]),DBL_MIN));}
        Need(std::fabs((1.-a.n[p])*j-(1.-N0))<=5e-13,"Solid-volume ledger failed");const double b=Kw/n,M=Bulk+4.*Shear/3.,D=b*ki/(Rhow*9.80665),margin=rho*b/(M+b)-Rhow;
        const double cf=std::sqrt((M+b)/rho)*r.dt/r.h,df=D*r.dt/(r.h*r.h);Need(std::isfinite(margin)&&margin>64.*DBL_EPSILON*(std::max)(rho,Rhow)&&std::isfinite(cf)&&cf<=.01&&std::isfinite(df)&&df<=.01&&r.dt<=double(float(.1))*r.h*r.h/D,"Original saved necessary domain/wave/pore screens failed");
        lo=(std::min)(lo,ki);hi=(std::max)(hi,ki);nlo=(std::min)(nlo,n);nhi=(std::max)(nhi,n);jn=(std::max)(jn,std::fabs(j-1.));cfl=(std::max)(cfl,cf);diff=(std::max)(diff,df);soilChecks++;
      }
      extra<<part<<','<<id<<','<<soil<<','<<j<<','<<a.theta[p]<<','<<oldn[q]<<','<<a.n[p]<<','<<a.volume[p]<<','<<a.rho[p]<<','<<a.k[p]<<','<<a.posdiv[p]<<'\n';commonChecks++;
    }
    const double energy=Energy(a,r.soil,r.fixed);if(!part){e0=energy;Need(std::isfinite(e0)&&e0>0,"Initial native energy empty");}const double ratio=energy/e0,span=(hi-lo)/K0;Need(std::isfinite(ratio)&&ratio<=1.1,"Original saved native energy bound failed");
    maxEnergy=(std::max)(maxEnergy,ratio);maxJ=(std::max)(maxJ,jn);maxSpan=(std::max)(maxSpan,span);maxLedger=(std::max)(maxLedger,ledger);maxCfl=(std::max)(maxCfl,cfl);maxDiff=(std::max)(maxDiff,diff);maxPosDiv=(std::max)(maxPosDiv,posdiv);minError=(std::min)(minError,ne);maxError=(std::max)(maxError,ne);
    exact<<part<<','<<nt<<','<<now.Get_Step()<<','<<nd<<','<<ne<<",true,true,true,true,true\n";
    history<<part<<','<<nt<<','<<now.Get_Step()<<','<<ne<<','<<ratio<<','<<jn<<','<<nlo<<','<<nhi<<','<<lo<<','<<hi<<','<<span<<','<<ledger<<','<<cfl<<','<<diff<<','<<posdiv<<'\n';
    const auto filename=JPartDataBi4::GetFileNamePart(part);inputs<<part<<','<<filename<<','<<filename<<'\n';
  }
  Need(soilChecks==r.soil*r.samples&&markerChecks==r.fixed*r.samples&&commonChecks==r.total*r.samples,"Native comparison/ledger coverage incomplete");
  Need(!r.wall||bandCount==256,"Original fixed-material wall band count differs");Need(maxJ>(r.smoke?0.:1e-8),"Natural native J evolution empty");Need(!r.model||r.smoke||maxSpan>=.005,"Original smooth-k activation screen failed");Need(maxPosDiv>0,"Actual public native PosDiv output is empty");
  for(auto* s:{&exact,&extra,&ids,&fixed,&history,&inputs}){s->flush();Need(bool(*s),"Offline comparison output write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)
    <<"{\"passed\":true,\"stage\":\"upl_gpu_public_native_r1\",\"backend\":\"GPU\",\"public_schema\":true,\"control_backend\":\"GPU\",\"private_control_schema\":\"observer3_no_public_metadata\",\"geometry\":\""<<(r.wall?"Wall":"Periodic")<<"\",\"window\":\""<<(r.smoke?"Smoke":"Full")<<"\",\"conductivity_model\":"<<r.model<<",\"conductivity_Ck\":"<<(r.model?Ck:0.)
    <<",\"native_count\":"<<r.soil<<",\"fixed_count\":"<<r.fixed<<",\"total_native_count\":"<<r.total<<",\"samples\":"<<r.samples<<",\"dt_s\":"<<r.dt<<",\"cadence_s\":"<<r.cadence<<",\"actual_end_s\":"<<r.end
    <<",\"original_typed_arrays\":15,\"original15_all_native_exact\":true,\"J_theta_all_native_exact\":true,\"soil_native_n_exact\":true,\"actual_time_step_locked_dt_signed_dterror_exact\":true,\"common_node_comparisons\":"<<commonChecks<<",\"native_double_dynamic_arrays\":6,\"native_PosDiv_float_present\":true,\"metadata_typed_verified\":true,\"soil_ledger_checks\":"<<soilChecks<<",\"fixed_zero_marker_checks\":"<<markerChecks
    <<",\"max_ledger_relative_error\":"<<maxLedger<<",\"max_energy_ratio\":"<<maxEnergy<<",\"max_abs_J_minus_1\":"<<maxJ<<",\"max_k_span_over_k0\":"<<maxSpan<<",\"max_saved_coupled_CFL\":"<<maxCfl<<",\"max_saved_Ddt_h2\":"<<maxDiff<<",\"max_abs_native_PosDiv\":"<<maxPosDiv<<",\"min_signed_dterror_s\":"<<minError<<",\"max_signed_dterror_s\":"<<maxError
    <<",\"fixed_n_change_is_declared_nonphysical_marker\":true,\"old_PosDiv_comparison_available\":false,\"PosDiv_compaction_proven_by_reader\":false,\"no_exclusions\":true,\"no_interpolation_or_masks\":true,\"physical_binary_exported\":false,\"original_scientific_receipts_may_be_inherited_only_after_wrapper_binding\":true,\"half_cross_reference_recomputed\":false,\"endpoint_force_audit_recomputed\":false,\"cached_gradient_speed_independently_verified\":false,\"file_SHA_verified_by_reader\":false,\"full_program_exit_verified_by_reader\":false,\"physical_acceptance\":false}\n";
  done.flush();Need(bool(done),"Offline comparison completion write failed");
}
}
int main(int argc,char** argv){try{
  Need(argc==10&&std::string(argv[1])=="--compare","Use --compare Periodic|Wall constant|smooth Smoke|Full PRIVATE_DATA PUBLIC_DATA RUNTIME_XML DT NEWREVIEWDIR");
  const auto r=gpupublic::Declare(argv[2],argv[3],argv[4],std::stod(argv[8]));gpupublic::Compare(r,argv[5],argv[6],argv[7],argv[9]);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(...){std::cerr<<"Offline public-GPU comparison rejected; preserve all data and partial review\n";return 2;}}

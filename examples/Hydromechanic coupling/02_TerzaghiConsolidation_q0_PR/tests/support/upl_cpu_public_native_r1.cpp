// Offline-only canonical BI4 reader. Never invokes a solver or changes native data.
#include "JPartDataBi4.h"
#include "JBinaryData.h"
#include "JAppInfo.h"
#include <algorithm>
#include <array>
#include <cfloat>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
JAppInfo AppInfo("PublicDynamicCpuNative","r1","01-11-2026");
namespace fs=std::filesystem;
using TpData=JBinaryDataDef::TpData;
static constexpr TpData DatBool=JBinaryDataDef::DatBool,DatUint=JBinaryDataDef::DatUint,
  DatFloat=JBinaryDataDef::DatFloat,DatDouble=JBinaryDataDef::DatDouble,
  DatFloat3=JBinaryDataDef::DatFloat3,DatDouble3=JBinaryDataDef::DatDouble3;
static constexpr double A=1./512.,Lx=1./8.,Width=1./16.,Lz=1./16.,N0=.25,Rho0=2048.,Rhow=1000.,Kw=67108864.;
static constexpr double Bulk=89478488.,Shear=134217728.,Ck=1./8192.;
static const double K0=double(float(.0001)),Cu=std::sqrt((Bulk+4.*Shear/3.+Kw/N0)/Rho0);
static const double Pstar=(Kw/N0)*A/Cu,Ustar=A/(Cu*2*std::acos(-1.)/Lx);
static void Need(bool yes,const std::string& why){if(!yes)throw std::runtime_error(why);}
static bool Close(double got,double ref){return std::isfinite(got)&&std::isfinite(ref)&&std::fabs(got-ref)<=5e-13*(std::max)(std::fabs(ref),DBL_MIN);}
static double Norm2(tdouble3 x){return x.x*x.x+x.y*x.y+x.z*x.z;}
static double Norm2(tfloat3 x){return double(x.x)*x.x+double(x.y)*x.y+double(x.z)*x.z;}
static bool Finite(unsigned){return true;}
static bool Finite(float x){return std::isfinite(x);}
static bool Finite(double x){return std::isfinite(x);}
static bool Finite(tfloat3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}
static bool Finite(tdouble3 x){return Finite(x.x)&&Finite(x.y)&&Finite(x.z);}
template<class T> static std::vector<T> NativeArray(JPartDataBi4& part,const char* name,unsigned count,TpData type){
  const auto* array=part.GetArray(name,type);
  Need((array->DataInPointer()?array->GetCount():array->GetFileDataCount())==count,"Wrong native array count: "+std::string(name));
  std::vector<T> result(count);Need(array->GetDataCopy(count,result.data())==count,"Incomplete native array: "+std::string(name));
  for(const auto& value:result)Need(Finite(value),"Nonfinite native array: "+std::string(name));return result;
}
template<class T> static void WriteTyped(std::ofstream& out,const std::vector<T>& values,const std::vector<unsigned>& slot){
  for(unsigned index:slot)out.write(reinterpret_cast<const char*>(&values[index]),sizeof(T));
}
struct Native{
  std::vector<unsigned> ids,fstype,slot;
  std::vector<tdouble3> pos,sk,si;
  std::vector<tfloat3> vel,legacykk,legacyij,normal,load;
  std::vector<float> rhop,plastic,p,p0,excess,posdiv;
  std::vector<double> j,n,theta,volume,rho,k;
};
static Native Load(JPartDataBi4& file,unsigned total,int model){
  Native a;a.ids=NativeArray<unsigned>(file,"Idp",total,DatUint);
  a.pos=NativeArray<tdouble3>(file,"Posd",total,DatDouble3);Need(!file.ArrayExists("Pos"),"Single-precision position is outside this test");
  a.vel=NativeArray<tfloat3>(file,"Vel",total,DatFloat3);a.rhop=NativeArray<float>(file,"Rhop",total,DatFloat);
  a.legacykk=NativeArray<tfloat3>(file,"Sigma_kk",total,DatFloat3);a.legacyij=NativeArray<tfloat3>(file,"Sigma_ij",total,DatFloat3);
  a.sk=NativeArray<tdouble3>(file,"SigmaState_kk",total,DatDouble3);a.si=NativeArray<tdouble3>(file,"SigmaState_ij",total,DatDouble3);
  a.plastic=NativeArray<float>(file,"Kplastic",total,DatFloat);a.fstype=NativeArray<unsigned>(file,"FSType",total,DatUint);
  a.normal=NativeArray<tfloat3>(file,"FSNormal",total,DatFloat3);a.load=NativeArray<tfloat3>(file,"HydroMechLoadAce",total,DatFloat3);
  a.p=NativeArray<float>(file,"PorePress",total,DatFloat);a.p0=NativeArray<float>(file,"PorePress0",total,DatFloat);
  a.excess=NativeArray<float>(file,"ExcessPorePress",total,DatFloat);
  a.slot.assign(total,~0u);
  for(unsigned p=0;p<total;p++){Need(a.ids[p]<total&&a.slot[a.ids[p]]==~0u,"Invalid/duplicate native ID");a.slot[a.ids[p]]=p;}
  for(unsigned index:a.slot)Need(index!=~0u,"Missing native ID");
  const char* dynamic[]={"PoroVolumeRatio","PoroPorosity","PoroThetaLastStage","PoroCurrentVolume","PoroMixtureDensity","PoroHydraulicConductivity"};
  for(const char* name:dynamic)Need(file.ArrayExists(name)==(model>=0),"Wrong ON/OFF dynamic array presence: "+std::string(name));
  Need(file.ArrayExists("PosDiv")==(model>=0),"Wrong ON/OFF actual PosDiv presence");
  if(model>=0){
    a.j=NativeArray<double>(file,dynamic[0],total,DatDouble);a.n=NativeArray<double>(file,dynamic[1],total,DatDouble);
    a.theta=NativeArray<double>(file,dynamic[2],total,DatDouble);a.volume=NativeArray<double>(file,dynamic[3],total,DatDouble);
    a.rho=NativeArray<double>(file,dynamic[4],total,DatDouble);a.k=NativeArray<double>(file,dynamic[5],total,DatDouble);
    a.posdiv=NativeArray<float>(file,"PosDiv",total,DatFloat);
  }return a;
}
static void Original15(std::ofstream& out,const Native& a){
  WriteTyped(out,a.ids,a.slot);WriteTyped(out,a.pos,a.slot);WriteTyped(out,a.vel,a.slot);
  WriteTyped(out,a.legacykk,a.slot);WriteTyped(out,a.legacyij,a.slot);WriteTyped(out,a.normal,a.slot);WriteTyped(out,a.load,a.slot);
  WriteTyped(out,a.rhop,a.slot);WriteTyped(out,a.plastic,a.slot);WriteTyped(out,a.p,a.slot);WriteTyped(out,a.p0,a.slot);WriteTyped(out,a.excess,a.slot);
  WriteTyped(out,a.sk,a.slot);WriteTyped(out,a.si,a.slot);WriteTyped(out,a.fstype,a.slot);
}
using Row=std::array<double,26>;
struct Frame{double time;std::vector<Row> rows;};
static Frame Physical(const Native& a,unsigned soil,unsigned fixed,double time){
  Frame f{time,{}};f.rows.reserve(soil);
  for(unsigned id=fixed;id<fixed+soil;id++){
    const unsigned p=a.slot[id];const auto x=a.pos[p],s=a.sk[p],t=a.si[p];const auto v=a.vel[p],n=a.normal[p],l=a.load[p];
    // SigmaState_ij is (xy,yz,xz), not (xy,xz,yz).
    f.rows.push_back({x.x,x.y,x.z,double(v.x),double(v.y),double(v.z),double(a.p[p]),double(a.p0[p]),a.j[p],a.theta[p],
      s.x,t.x,t.z,s.y,t.y,s.z,double(a.plastic[p]),double(a.fstype[p]),double(n.x),double(n.y),double(n.z),double(a.posdiv[p]),double(l.x),double(l.y),double(l.z),double(a.rhop[p])});
  }return f;
}
static void WritePhysical(std::ofstream& out,const Frame& f){out.write(reinterpret_cast<const char*>(&f.time),8);for(const auto& row:f.rows)out.write(reinterpret_cast<const char*>(row.data()),26*8);}
static void Sequence(const fs::path& dir,unsigned samples){
  Need(fs::is_directory(dir),"Native data directory missing");unsigned found=0;
  for(const auto& item:fs::directory_iterator(dir))if(item.is_regular_file()&&item.path().filename().string().rfind("Part_",0)==0&&item.path().extension()==".bi4")found++;
  Need(found==samples,"Extra/missing native PART/piece files");
  for(unsigned i=0;i<samples;i++)Need(fs::is_regular_file(dir/JPartDataBi4::GetFileNamePart(i)),"Missing native PART");
}
static void Metadata(JPartDataBi4& file,int model){
  const auto* part=file.GetPart();
  const char* keys[]={"HydroMechDynamicSeepage","DynamicSeepageSchema","HydroMechConductivityModel","HydroMechConductivityCk"};
  for(const char* name:keys)Need(part->ExistsValue(name)==(model>=0),"Wrong ON/OFF native model metadata presence: "+std::string(name));
  if(model>=0){
    Need(part->ExistsValue(keys[0],DatBool)&&part->GetvBool(keys[0]),"Native total switch is not bool true");
    Need(part->ExistsValue(keys[1],DatUint)&&part->GetvUint(keys[1])==1,"Native schema is not uint1");
    Need(part->ExistsValue(keys[2],DatUint)&&part->GetvUint(keys[2])==unsigned(model),"Native conductivity model is not expected uint");
    Need(part->ExistsValue(keys[3],DatDouble)&&part->GetvDouble(keys[3])==(model?Ck:0.),"Native conductivity Ck is not expected double");
  }
}
static double Energy(const Native& a,unsigned soil,unsigned fixed){
  double energy=0;
  for(unsigned id=fixed;id<fixed+soil;id++){const unsigned p=a.slot[id];const auto s=a.sk[p],t=a.si[p];const double tr=s.x+s.y+s.z,mean=tr/3.;
    const double dev=std::pow(s.x-mean,2)+std::pow(s.y-mean,2)+std::pow(s.z-mean,2)+2.*Norm2(t);
    energy+=a.volume[p]*(.5*a.rho[p]*Norm2(a.vel[p])+dev/(4*Shear)+tr*tr/(18*Bulk)+a.n[p]*double(a.p[p])*a.p[p]/(2*Kw));
  }return energy;
}
static void Read(const fs::path& dir,unsigned soil,unsigned fixed,unsigned samples,double dt,double cadence,int model,const fs::path& target){
  Need(!fs::exists(target),"Retained native review protected");Need((soil==512&&fixed==0)||(soil==1024&&fixed==256),"Undeclared geometry");
  Need(model>=-1&&model<=1&&!(soil==512&&model==1),"Undeclared public model/geometry");
  Need(std::isfinite(dt)&&dt>0&&std::isfinite(cadence)&&cadence>=dt&&cadence/dt==std::round(cadence/dt),"Non-dyadic output scheduling input");
  const bool off=model<0,smoke=samples==3;Need(off?(samples==9&&soil==512&&dt==std::pow(2.,-24)&&cadence==dt):
    (smoke?(soil==1024&&model==1&&dt==std::pow(2.,-25)&&cadence==dt):(samples==257&&cadence==std::pow(2.,-23))),"Undeclared sample window");
  if(!off&&!smoke)Need(soil==512?(dt==std::pow(2.,-24)||dt==std::pow(2.,-25)):(dt==std::pow(2.,-25)||dt==std::pow(2.,-26)),"Undeclared canonical fixed step");
  Sequence(dir,samples);fs::create_directory(target);
  std::ofstream raw(target/"original15.bin",std::ios::binary),physical,nativecsv(target/"native_ids.csv"),fixedcsv(target/"fixed_ids.csv"),history(target/"history.csv");
  const unsigned total=soil+fixed,oldheader[]={total,15,samples};raw.write(reinterpret_cast<const char*>(oldheader),12);
  if(!off){physical.open(target/"physical.bin",std::ios::binary);const unsigned h[]={soil,26,samples};physical.write(reinterpret_cast<const char*>(h),12);}
  for(auto* stream:{&nativecsv,&fixedcsv,&history})*stream<<std::setprecision(17);
  nativecsv<<"row,native_id,x0,y0,z0,wall_band\n";fixedcsv<<"row,native_id,x0,y0,z0,plane_x\n";
  history<<"part,time_s,native_step,dt_s,dterror_s,energy_ratio,pressure_RMS_Pa,max_material_displacement_mm,max_abs_J_minus_1,min_n,max_n,min_k,max_k,k_span_over_initial_k0,max_k_change_over_initial_k0,max_ledger_relative_error,max_coupled_CFL,max_Ddt_h2\n";
  std::vector<tdouble3> initial(total);double e0=0,maxEnergy=0,maxJ=0,minK=DBL_MAX,maxK=0,maxSpan=0,maxChange=0,maxLedger=0,maxCfl=0,maxDiff=0,maxError=-DBL_MAX,minError=DBL_MAX;
  unsigned ledgerChecks=0,markerChecks=0,bandCount=0;
  const double dp=soil==512?1./256.:1./512.,h=double(float(1.8*dp)),v0=dp*dp,gamma=Rhow*9.80665;
  for(unsigned part=0;part<samples;part++){
    JPartDataBi4 file;file.LoadFilePart(dir.string(),part,0,1);
    Need(file.GetNpiece()==1&&file.Get_Npok()==total&&!file.Get_Nout()&&file.Get_CaseNp()==total&&file.Get_CaseNfluid()==soil&&file.Get_CaseNfixed()==fixed&&!file.Get_CaseNmoving()&&!file.Get_CaseNfloat(),"Native particle set/exclusions changed");
    Need(file.Get_Data2d()&&!file.Get_Symmetry()&&!file.Get_NpDynamic()&&!file.Get_ReuseIds(),"Outside fixed 2D native scope");
    Need(file.Get_Dp()==dp&&file.Get_H()==h&&file.Get_Rhop0()==Rho0&&file.Get_MassFluid()/Rho0==v0,"Actual native material/volume geometry mismatch");
    Need(file.Get_PeriMode()==(fixed?PERI_Z:PERI_XZ),"Wrong native periodic axes");
    const double time=file.Get_TimeStep(),wanted=part*cadence;const unsigned step=part?unsigned(std::llround(wanted/dt))-1:0;
    Need(time==wanted&&file.Get_Step()==step,"Actual native saved clock/zero-based step differs");
    Need(file.GetPart()->ExistsValue("SymplecticDtPre",DatDouble)&&file.GetPart()->GetvDouble("SymplecticDtPre")==dt,"Native locked step metadata differs");
    // Original telemetry is signed max(FixedDt-DtVariable), not an absolute clock residual.
    Need(file.GetPart()->ExistsValue("dterror",DatDouble),"Actual signed dterror telemetry missing");
    const double error=file.GetPart()->GetvDouble("dterror");Need(std::isfinite(error)&&error<=1e-14,"Original signed fixed-grid error guard failed");maxError=(std::max)(maxError,error);minError=(std::min)(minError,error);
    Metadata(file,model);const Native a=Load(file,total,model);double frameLedger=0,lo=DBL_MAX,hi=0,change=0,jn=0,nnlo=DBL_MAX,nnhi=0,pe=0,mu=0,cfl=0,diff=0;
    for(unsigned id=0;id<total;id++){
      const unsigned p=a.slot[id];Need(a.plastic[p]==0&&a.rhop[p]>=700&&a.rhop[p]<=3000&&a.p0[p]==0&&Norm2(a.load[p])==0,"Elastic/passive-density/no-load/p0 guard failed");
      Need(a.excess[p]==float(a.p[p]-a.p0[p]),"Native float excess pressure does not equal p-p0");
      Need(a.legacykk[p].x==float(a.sk[p].x)&&a.legacykk[p].y==float(a.sk[p].y)&&a.legacykk[p].z==float(a.sk[p].z)
        &&a.legacyij[p].x==float(a.si[p].x)&&a.legacyij[p].y==float(a.si[p].y)&&a.legacyij[p].z==float(a.si[p].z),"Legacy stress display does not round from double state");
      if(!part){
        initial[id]=a.pos[p];Need(a.pos[p].y==0,"Initial particle is not in the declared plane");
        if(id>=fixed){
          const unsigned row=id-fixed;const double ix=a.pos[p].x/dp-.5,iz=a.pos[p].z/dp-.5;
          Need(ix==std::round(ix)&&iz==std::round(iz)&&ix>=0&&ix<32&&iz>=0&&iz<(fixed?32:16),"Native soil initial lattice differs");
          const float expected=float(A*std::sin(2*std::acos(-1.)*a.pos[p].x/Lx));
          Need(a.vel[p].x==expected&&a.vel[p].y==0&&a.vel[p].z==0&&a.p[p]==0&&Norm2(a.sk[p])==0&&Norm2(a.si[p])==0,"Initial native velocity/pressure/stress is not declared sine");
          const bool band=fixed&&(std::min)(a.pos[p].x,Width-a.pos[p].x)<=2*h;bandCount+=unsigned(band);
          nativecsv<<row<<','<<id<<','<<a.pos[p].x<<','<<a.pos[p].y<<','<<a.pos[p].z<<','<<band<<'\n';
          if(!off)Need(a.j[p]==1&&a.n[p]==N0&&a.theta[p]==0,"Initial public J/n/theta did not fresh-start");
        }else{
          Need(a.pos[p].x<0||a.pos[p].x>Width,"Fixed point is inside soil");
          fixedcsv<<id<<','<<id<<','<<a.pos[p].x<<','<<a.pos[p].y<<','<<a.pos[p].z<<','<<(a.pos[p].x<0?0.:Width)<<'\n';
        }
      }
      if(id<fixed){
        Need(!std::memcmp(&a.pos[p],&initial[id],sizeof(tdouble3))&&Norm2(a.vel[p])==0&&a.rhop[p]==Rho0,"Real fixed position/physical velocity changed");
        if(!off){Need(a.n[p]==0&&a.volume[p]==0&&a.rho[p]==0&&a.k[p]==0&&a.theta[p]==0,"Fixed derived output is not zero marker");markerChecks++;}
      }else{
        Need(a.pos[p].x>0&&a.pos[p].x<(fixed?Width:Lx),"Soil left declared x domain");pe+=double(a.p[p])*a.p[p];
        const auto u=a.pos[p]-initial[id];mu=(std::max)(mu,1000*std::sqrt(Norm2(u)));
        if(!off){
          const double j=a.j[p],n=1.-(1.-N0)/j,V=v0*j,rho=Rhow+(Rho0-Rhow)/j,k=model&&j!=1?K0*std::exp((j-1.)/((1.-N0)*Ck)):K0;
          Need(j>1.-N0&&std::fabs(j-1)<=1e-4&&n>0&&n<1&&rho>0&&V>0&&std::isfinite(k)&&k>0,"Weak saturated state left its declared domain");
          const double got[]={a.n[p],a.volume[p],a.rho[p],a.k[p]},ref[]={n,V,rho,k};
          for(unsigned q=0;q<4;q++){Need(Close(got[q],ref[q]),"Saved derived native ledger differs from J");frameLedger=(std::max)(frameLedger,std::fabs(got[q]-ref[q])/(std::max)(std::fabs(ref[q]),DBL_MIN));}
          Need(std::fabs((1.-a.n[p])*j-(1.-N0))<=5e-13,"Solid-volume ledger identity failed");
          const double b=Kw/n,cu2=(Bulk+4.*Shear/3.+b)/rho,D=b*k/gamma,margin=rho*b/(Bulk+4.*Shear/3.+b)-Rhow;
          Need(margin>64*DBL_EPSILON*(std::max)(rho,Rhow),"Saved current state outside strict positive-k decay domain");
          const double cf=std::sqrt(cu2)*dt/h,df=D*dt/(h*h);Need(cf<=.01&&df<=.01&&dt<=double(float(.1))*h*h/D,"Saved necessary wave/pore step guard failed");
          cfl=(std::max)(cfl,cf);diff=(std::max)(diff,df);jn=(std::max)(jn,std::fabs(j-1));nnlo=(std::min)(nnlo,n);nnhi=(std::max)(nnhi,n);
          lo=(std::min)(lo,a.k[p]);hi=(std::max)(hi,a.k[p]);change=(std::max)(change,std::fabs(a.k[p]/K0-1));ledgerChecks++;
        }
      }
    }
    const double energy=off?0:Energy(a,soil,fixed);if(!off&&!part){e0=energy;Need(e0>0&&std::isfinite(e0),"Initial physical energy empty");}
    const double ratio=off?0:energy/e0;Need(off||(std::isfinite(ratio)&&ratio<=1.1),"Original native energy bound failed");
    raw.write(reinterpret_cast<const char*>(&time),8);Original15(raw,a);raw.flush();Need(bool(raw),"Original-array binary output failed");
    if(!off){WritePhysical(physical,Physical(a,soil,fixed,time));physical.flush();Need(bool(physical),"26-field binary output failed");}
    maxEnergy=(std::max)(maxEnergy,ratio);maxJ=(std::max)(maxJ,jn);maxLedger=(std::max)(maxLedger,frameLedger);maxCfl=(std::max)(maxCfl,cfl);maxDiff=(std::max)(maxDiff,diff);
    const double span=off?0:(hi-lo)/K0;maxSpan=(std::max)(maxSpan,span);maxChange=(std::max)(maxChange,change);if(!off){minK=(std::min)(minK,lo);maxK=(std::max)(maxK,hi);}
    history<<part<<','<<time<<','<<step<<','<<dt<<','<<error<<','<<ratio<<','<<std::sqrt(pe/soil)<<','<<mu<<','<<jn<<','<<(off?0:nnlo)<<','<<nnhi<<','<<(off?0:lo)<<','<<hi<<','<<span<<','<<change<<','<<frameLedger<<','<<cfl<<','<<diff<<'\n';
  }
  Need(!fixed||bandCount==256,"Declared native wall band count changed");
  if(!off&&!smoke)Need(maxJ>1e-8,"Natural public J evolution is empty");
  if(model==1&&!smoke)Need(maxSpan>=.005&&maxChange>=.005,"Natural public conductivity evolution is empty");
  Need(ledgerChecks==(off?0:soil*samples)&&markerChecks==(off?0:fixed*samples),"Native ledger/marker coverage incomplete");
  nativecsv.flush();fixedcsv.flush();history.flush();Need(nativecsv&&fixedcsv&&history,"Native text outputs failed");
  std::ofstream done(target/"complete.json");done<<std::setprecision(17)<<"{\"passed\":true,\"native_count\":"<<soil<<",\"fixed_count\":"<<fixed<<",\"total_native_count\":"<<total<<",\"samples\":"<<samples<<",\"model\":"<<model<<",\"dt_actual\":"<<dt<<",\"cadence_s\":"<<cadence<<",\"actual_start_s\":0,\"actual_end_s\":"<<(samples-1)*cadence<<",\"original_arrays\":15,\"derived_arrays\":"<<(off?0:6)<<",\"physical_columns\":"<<(off?0:26)<<",\"posdiv_native_present\":"<<(off?"false":"true")<<",\"model_metadata_verified\":"<<(off?"false":"true")<<",\"model_metadata_absent\":"<<(off?"true":"false")<<",\"no_exclusions\":true,\"native_ID_aligned\":true,\"all_arrays_finite\":true,\"saved_clock_step_exact\":true,\"double_sigma_state\":true,\"initial_sine_verified\":true,\"initial_J1_verified\":"<<(off?"false":"true")<<",\"ledger_native_checks\":"<<ledgerChecks<<",\"fixed_marker_checks\":"<<markerChecks<<",\"max_ledger_relative_error\":"<<maxLedger<<",\"new_model_energy_evaluated\":"<<(off?"false":"true")<<",\"max_energy_ratio\":"<<maxEnergy<<",\"max_abs_J_minus_1\":"<<maxJ<<",\"min_k\":"<<(off?0:minK)<<",\"max_k\":"<<maxK<<",\"max_k_span_over_initial_k0\":"<<maxSpan<<",\"max_k_change_over_initial_k0\":"<<maxChange<<",\"max_coupled_CFL\":"<<maxCfl<<",\"max_Ddt_h2\":"<<maxDiff<<",\"min_signed_dterror\":"<<minError<<",\"max_signed_dterror\":"<<maxError<<",\"finite_dterror_safety_checked\":true,\"Pstar\":"<<Pstar<<",\"Ustar\":"<<Ustar<<",\"cached_gradient_speed_independently_verified\":false,\"full_program_exit_verified_by_reader\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Native completion output failed");
}
static Frame ReadFrame(std::ifstream& in,unsigned native){
  Frame f{};f.rows.resize(native);in.read(reinterpret_cast<char*>(&f.time),8);for(auto& row:f.rows)in.read(reinterpret_cast<char*>(row.data()),26*8);Need(bool(in),"Truncated26-field frame");return f;
}
static void Half(const fs::path& left,const fs::path& right,const fs::path& target){
  Need(!fs::exists(target),"Retained half receipt protected");std::ifstream a(left,std::ios::binary),b(right,std::ios::binary);unsigned ha[3],hb[3];a.read(reinterpret_cast<char*>(ha),12);b.read(reinterpret_cast<char*>(hb),12);
  Need(a&&b&&!std::memcmp(ha,hb,12)&&(ha[0]==512||ha[0]==1024)&&ha[1]==26&&ha[2]==257,"Wrong same-model public half schema");const unsigned native=ha[0];
  for(const char* name:{"native_ids.csv","fixed_ids.csv"}){std::ifstream ia(left.parent_path()/name,std::ios::binary),ib(right.parent_path()/name,std::ios::binary);Need(ia.is_open()&&ib.is_open(),"Half identity ledger missing");const std::string sa((std::istreambuf_iterator<char>(ia)),std::istreambuf_iterator<char>()),sb((std::istreambuf_iterator<char>(ib)),std::istreambuf_iterator<char>());Need(!sa.empty()&&sa==sb,"Half native/fixed identities differ");}
  double mp=0,mu=0,np=0,nv=0,nu=0,mj=0;
  for(unsigned part=0;part<257;part++){const auto x=ReadFrame(a,native),y=ReadFrame(b,native);Need(x.time==y.time&&x.time==part*std::pow(2.,-23),"Half actual clocks differ");double pe=0,ve=0,ue=0;
    for(unsigned row=0;row<native;row++){const auto& p=x.rows[row];const auto& q=y.rows[row];if(!part)Need(!std::memcmp(p.data(),q.data(),26*8),"Half initial native physical fields differ");
      pe+=std::pow(p[6]-q[6],2);double u=0;for(unsigned j=0;j<3;j++){u+=std::pow(p[j]-q[j],2);ve+=std::pow(p[j+3]-q[j+3],2);}ue+=u;mu=(std::max)(mu,1000*std::sqrt(u));mj=(std::max)(mj,std::fabs(p[8]-q[8]));}
    const double pr=std::sqrt(pe/native),vr=std::sqrt(ve/native)/A,ur=std::sqrt(ue/native)/Ustar;mp=(std::max)(mp,pr);np=(std::max)(np,pr/Pstar);nv=(std::max)(nv,vr);nu=(std::max)(nu,ur);
    Need(pr<=5&&mu<=.005&&pr/Pstar<=1e-4&&vr<=1e-4&&ur<=1e-4,"Original independent half absolute/normalized limit failed");
  }Need(a.peek()==std::char_traits<char>::eof()&&b.peek()==std::char_traits<char>::eof(),"Unreviewed trailing half frames");
  std::ofstream out(target);out<<std::setprecision(17)<<"{\"passed\":true,\"samples\":257,\"native_ids\":"<<native<<",\"columns\":26,\"max_pressure_RMS_Pa\":"<<mp<<",\"max_material_displacement_mm\":"<<mu<<",\"max_pressure_RMS_over_Pstar\":"<<np<<",\"max_velocity_vector_RMS_over_A\":"<<nv<<",\"max_displacement_vector_RMS_over_Ustar\":"<<nu<<",\"max_J_difference\":"<<mj<<",\"physical_acceptance\":false}\n";out.flush();Need(bool(out),"Half receipt output failed");
}
int main(int argc,char** argv){try{
  if(argc==5&&std::string(argv[1])=="--half"){Half(argv[2],argv[3],argv[4]);return 0;}
  Need(argc==10&&std::string(argv[1])=="--read","Use --read DATA_DIR SOIL FIXED SAMPLES DT CADENCE MODEL NEWREVIEWDIR or --half LEFT RIGHT NEWJSON");
  Read(argv[2],unsigned(std::stoul(argv[3])),unsigned(std::stoul(argv[4])),unsigned(std::stoul(argv[5])),std::stod(argv[6]),std::stod(argv[7]),std::stoi(argv[8]),argv[9]);return 0;
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}catch(...){std::cerr<<"Offline native review rejected; retain inputs and partial analysis\n";return 2;}}

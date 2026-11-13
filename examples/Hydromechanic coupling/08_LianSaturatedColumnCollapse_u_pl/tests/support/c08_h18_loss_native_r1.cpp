// One failed source, not a PRE qualification or a replacement native reader.
// The generated shared/source bodies retain the passed plastic reader's guards.
#include "loss_shared_r1.h"
namespace h18source {
#include "loss_source_r1.cpp"
}

namespace forensic {
using namespace h18source;
using namespace h18source::prediag;
static unsigned Nonfinite=0;
template<class V> static std::vector<V> ObservedArray(JPartDataBi4& f,const char* name,unsigned count,TpData type){
  const auto* array=f.GetArray(name,type);
  Need((array->DataInPointer()?array->GetCount():array->GetFileDataCount())==count,"Wrong final array count: "+std::string(name));
  std::vector<V> values(count);Need(array->GetDataCopy(count,values.data())==count,"Incomplete final array: "+std::string(name));
  for(const auto& v:values)Nonfinite+=unsigned(!Finite(v));
  return values;
}
template<class V> static std::vector<V> OutArray(JBinaryData* f,const char* name,unsigned count,TpData type){
  const auto* array=f->GetArray(name);Need(array&&array->GetType()==type,"Missing/incorrect PartOut array: "+std::string(name));
  Need((array->DataInPointer()?array->GetCount():array->GetFileDataCount())==count,"PartOut array count differs");
  std::vector<V> result(count);Need(array->GetDataCopy(count,result.data())==count,"Incomplete PartOut array");return result;
}
template<class V> static void OriginalOrder(std::ofstream& out,const std::vector<V>& a){out.write(reinterpret_cast<const char*>(a.data()),std::streamsize(a.size()*sizeof(V)));}
static Native FinalArrays(JPartDataBi4& f,unsigned count){
  Native a;
  a.ids=ObservedArray<unsigned>(f,"Idp",count,DatUint);a.pos=ObservedArray<tdouble3>(f,"Posd",count,DatDouble3);Need(!f.ArrayExists("Pos"),"Unexpected final single position");
  a.vel=ObservedArray<tfloat3>(f,"Vel",count,DatFloat3);a.legacykk=ObservedArray<tfloat3>(f,"Sigma_kk",count,DatFloat3);a.legacyij=ObservedArray<tfloat3>(f,"Sigma_ij",count,DatFloat3);
  a.normal=ObservedArray<tfloat3>(f,"FSNormal",count,DatFloat3);a.load=ObservedArray<tfloat3>(f,"HydroMechLoadAce",count,DatFloat3);
  a.rhop=ObservedArray<float>(f,"Rhop",count,DatFloat);a.plastic=ObservedArray<float>(f,"Kplastic",count,DatFloat);a.p=ObservedArray<float>(f,"PorePress",count,DatFloat);a.p0=ObservedArray<float>(f,"PorePress0",count,DatFloat);a.excess=ObservedArray<float>(f,"ExcessPorePress",count,DatFloat);
  a.sk=ObservedArray<tdouble3>(f,"SigmaState_kk",count,DatDouble3);a.si=ObservedArray<tdouble3>(f,"SigmaState_ij",count,DatDouble3);a.fstype=ObservedArray<unsigned>(f,"FSType",count,DatUint);
  a.j=ObservedArray<double>(f,"PoroVolumeRatio",count,DatDouble);a.n=ObservedArray<double>(f,"PoroPorosity",count,DatDouble);a.theta=ObservedArray<double>(f,"PoroThetaLastStage",count,DatDouble);a.volume=ObservedArray<double>(f,"PoroCurrentVolume",count,DatDouble);a.rho=ObservedArray<double>(f,"PoroMixtureDensity",count,DatDouble);a.k=ObservedArray<double>(f,"PoroHydraulicConductivity",count,DatDouble);a.posdiv=ObservedArray<float>(f,"PosDiv",count,DatFloat);
  a.slot.assign(Total,~0u);for(unsigned q=0;q<count;q++){Need(a.ids[q]<Total&&a.slot[a.ids[q]]==~0u,"Invalid/duplicate final original-domain ID");a.slot[a.ids[q]]=q;}return a;
}
static void SaveFinal(const fs::path& out,const Native& a,double time){
  std::ofstream raw(out/"final_part533_typed22.bin",std::ios::binary);const unsigned header[]={unsigned(a.ids.size()),22,1};raw.write(reinterpret_cast<const char*>(header),12);raw.write(reinterpret_cast<const char*>(&time),8);
  OriginalOrder(raw,a.ids);OriginalOrder(raw,a.pos);OriginalOrder(raw,a.vel);OriginalOrder(raw,a.legacykk);OriginalOrder(raw,a.legacyij);OriginalOrder(raw,a.normal);OriginalOrder(raw,a.load);OriginalOrder(raw,a.rhop);OriginalOrder(raw,a.plastic);OriginalOrder(raw,a.p);OriginalOrder(raw,a.p0);OriginalOrder(raw,a.excess);OriginalOrder(raw,a.sk);OriginalOrder(raw,a.si);OriginalOrder(raw,a.fstype);OriginalOrder(raw,a.j);OriginalOrder(raw,a.n);OriginalOrder(raw,a.theta);OriginalOrder(raw,a.volume);OriginalOrder(raw,a.rho);OriginalOrder(raw,a.k);OriginalOrder(raw,a.posdiv);raw.flush();Need(bool(raw),"Final original-order export failed");
  fs::copy_file(out/"prefix/typed22_layout.csv",out/"final_part533_layout.csv");
}
static unsigned Excluded(const fs::path& data,const fs::path& out,double time,const std::vector<unsigned>& missing){
  unsigned files=0,records=0,excluded=~0u;std::ofstream csv(out/"excluded.csv");csv<<std::setprecision(17)<<"part,time_s,native_id,x_m,y_m,z_m,vx_m_s,vy_m_s,vz_m_s,rhop_kg_m3,motive\n";
  for(const auto& q:fs::directory_iterator(data))if(q.is_regular_file()&&q.path().extension()==".obi4"&&q.path().filename().string().rfind("PartOut_",0)==0){
    files++;JBinaryData f;f.LoadFileListApp(q.path().string(),"JPartOutBi4",true);
    for(unsigned item=0;item<f.GetItemsCount();item++){
      auto* p=f.GetItem(item);if(!p->ExistsValue("Cpart"))continue;
      Need(p->ExistsValue("Cpart",DatUint)&&p->GetvUint("Cpart")==533&&p->ExistsValue("TimeStep",DatDouble)&&Bits(p->GetvDouble("TimeStep"),time)&&p->ExistsValue("Nout",DatUint)&&p->GetvUint("Nout")==1,"Unexpected PartOut part/time/count");
      auto ids=OutArray<unsigned>(p,"Idp",1,DatUint);auto pos=OutArray<tdouble3>(p,"Posd",1,DatDouble3);auto vel=OutArray<tfloat3>(p,"Vel",1,DatFloat3);auto rho=OutArray<float>(p,"Rhop",1,DatFloat);auto motive=OutArray<byte>(p,"Motive",1,JBinaryDataDef::DatUchar);
      Need(missing.size()==1&&ids[0]==missing[0]&&ids[0]>=Fixed&&motive[0]==1&&Finite(pos[0])&&Finite(vel[0])&&Finite(rho[0]),"PartOut must match the actual one missing soil ID and position motive");
      records++;excluded=ids[0];csv<<533<<','<<time<<','<<ids[0]<<','<<pos[0].x<<','<<pos[0].y<<','<<pos[0].z<<','<<vel[0].x<<','<<vel[0].y<<','<<vel[0].z<<','<<rho[0]<<','<<unsigned(motive[0])<<'\n';
    }
  }
  csv.flush();Need(bool(csv)&&files==1&&records==1,"PartOut files/record closure differs");return excluded;
}
}

int wmain(int argc,wchar_t** argv){
  using namespace forensic;fs::path out;try{
    Need(argc==6&&std::wstring(argv[1])==L"--read","Use --read DATA MATERIAL_CSV ORIGINAL1001PLAN FRESHOUT");const fs::path data=argv[2],material=argv[3],plan=argv[4];out=argv[5];Need(fs::is_directory(data)&&!fs::exists(out),"Missing DATA or protected output");
    H18ReadPlan(plan,true,H18Event,H18SourceSamples);Need(fs::create_directory(out),"Cannot create fresh forensic output");
    std::vector<std::wstring> args={argv[0],L"--source",L"partial",argv[2],argv[3],argv[4],(out/"prefix").wstring()};std::vector<wchar_t*> ptr;for(auto& x:args)ptr.push_back(x.data());Need(h18source::wmain(int(ptr.size()),ptr.data())==0,"Strict original prefix guards failed; preserve partial diagnostics");
    Need(H18Group=="psi0"&&H18TargetCoh==5000.f&&H18Decay==0.f,"Only the actual failed psi0 source is admitted");
    Need(LossX0.size()==Total&&LossP0.size()==Total&&LossPreviousK.size()==Total&&LossCompleted==1064001,"Strict prefix captured state/count differs");
    JPartDataBi4 f;f.LoadFilePart(data.string(),533,0,1);const unsigned n=f.Get_Npok(),step=f.Get_Step(),completed=step+1;const double time=f.Get_TimeStep();
    Need(f.GetNpiece()==1&&f.GetPiece()==0&&n==7059&&f.Get_Nout()==1&&f.Get_CaseNp()==Total&&f.Get_CaseNfixed()==Fixed&&f.Get_CaseNfluid()==Soil&&!f.Get_CaseNmoving()&&!f.Get_CaseNfloat()&&f.Get_Data2d()&&f.Get_Data2dPosY()==0&&!f.Get_Symmetry()&&!f.Get_NpDynamic()&&!f.Get_ReuseIds()&&f.Get_PeriMode()==PERI_None,"Final abnormal registry differs from the observed one loss");
    Need(step==1064543&&completed==1064544&&f.Get_Dp()==Dp&&f.Get_H()==double(.072f)&&f.Get_Rhop0()==Rho&&f.Get_MassFluid()==Mass&&f.Get_MassBound()==Mass&&f.ArraysCount()==22,"Final actual step/reference/22 schema differs");
    double scalar=LossScalar;for(unsigned j=LossCompleted;j<completed;j++)scalar+=Dt;Need(Finite(time)&&std::abs(time-scalar)<=1e-14,"Forced-final actual scalar clock differs");Metadata(f,false);const auto* p=f.GetPart();Need(p->ExistsValue("SymplecticDtPre",DatDouble)&&Bits(p->GetvDouble("SymplecticDtPre"),Dt)&&p->ExistsValue("dterror",DatDouble),"Final actual dt/signed metadata missing");const double signedError=p->GetvDouble("dterror");Need(Finite(signedError)&&signedError!=-DBL_MAX&&signedError<=1e-14,"Original final signed necessary-step guard failed");
    const auto a=FinalArrays(f,n);SaveFinal(out,a,time);Need(Nonfinite==0,"Final payload contains nonfinite values; bytes preserved");std::vector<unsigned> missing;for(unsigned id=0;id<Total;id++)if(a.slot[id]==~0u)missing.push_back(id);const unsigned excluded=Excluded(data,out,time,missing);
    Need(missing.size()==1&&excluded==3060,"Observed missing ID differs from the independently retained exclusion");
    unsigned fixedChecks=0,ledger=0,p0Checks=0,cache=0,kappa=0,fsCount=0,fsPositive=0,zBelow=0,xBelow=0;double maxLedger=0,minZ=DBL_MAX,maxSpeed=0,maxK=0;
    for(unsigned q=0;q<n;q++){
      const unsigned id=a.ids[q];const auto x=a.pos[q],s=a.sk[q],t=a.si[q];Need(x.y==0&&a.rhop[q]>0&&Bits(a.p0[q],LossP0[id])&&a.excess[q]==float(a.p[q]-a.p0[q])&&a.fstype[q]<=4&&a.plastic[q]>=0.f&&a.plastic[q]>=LossPreviousK[id]&&Norm2(a.load[q])==0,"Original retained-final P0/history/finite-domain guard failed");p0Checks++;kappa++;
      Need(a.legacykk[q].x==float(s.x)&&a.legacykk[q].y==float(s.y)&&a.legacykk[q].z==float(s.z)&&a.legacyij[q].x==float(t.x)&&a.legacyij[q].y==float(t.y)&&a.legacyij[q].z==float(t.z),"Final float display differs from double stress");
      if(id<Fixed){Need(!std::memcmp(&x,&LossX0[id],sizeof(x))&&Norm2(a.vel[q])==0&&a.j[q]>1-Por&&a.plastic[q]==0.f&&a.theta[q]==0&&a.n[q]==0&&a.volume[q]==0&&a.rho[q]==0&&a.k[q]==0,"Original final fixed position/marker differs");fixedChecks++;continue;}
      const double j=a.j[q],por=1-(1-Por)/j,V=Mass/Rho*j,rho=Water+(Rho-Water)/j,k=K0Case*std::exp((j-1)/((1-Por)*CkCase));Need(j>1-Por&&por>0&&por<1&&V>0&&rho>0&&std::fabs((1-a.n[q])*j-(1-Por))<=5e-13,"Original final single-J domain/ledger failed");const double got[]={a.n[q],a.volume[q],a.rho[q],a.k[q]},ref[]={por,V,rho,k};for(unsigned z=0;z<4;z++){Need(Close(got[z],ref[z]),"Original final n/V/rho/k ledger differs");maxLedger=(std::max)(maxLedger,std::fabs(got[z]-ref[z])/(std::max)(std::fabs(ref[z]),DBL_MIN));}Need(Bits(a.rhop[q],float(rho)),"Original final density cache bits differ");ledger++;cache++;
      minZ=(std::min)(minZ,x.z);zBelow+=unsigned(x.z<0);xBelow+=unsigned(x.x<0);maxSpeed=(std::max)(maxSpeed,std::sqrt(Norm2(a.vel[q])));maxK=(std::max)(maxK,double(a.plastic[q]));if(a.fstype[q]==2||a.fstype[q]==3){fsCount++;fsPositive+=unsigned(a.p[q]>0);}
    }
    Need(fixedChecks==2060&&ledger==4999&&p0Checks==7059,"Final present-ID coverage differs");
    std::ofstream meta(out/"final_part533.json");meta<<std::setprecision(17)<<"{\"part\":533,\"completed_step\":"<<completed<<",\"saved_step\":"<<step<<",\"time_s\":"<<time<<",\"dt_s\":"<<Dt<<",\"signed_dterror_s\":"<<signedError<<",\"original_native_ID_domain\":7060,\"native_ID_domain\":7060,\"present_native_IDs\":7059,\"present_IDs\":7059,\"missing_ids\":["<<excluded<<"],\"array_count\":22,\"typed_arrays\":22,\"typed_bytes_per_particle\":212,\"payload_original_array_order\":true,\"missing_values_padded\":false,\"nonfinite_values\":"<<Nonfinite<<",\"scalar_clock_error_s\":"<<std::abs(time-scalar)<<",\"fixed_marker_checks\":"<<fixedChecks<<",\"ledger_checks\":"<<ledger<<",\"P0_bits_checks\":"<<p0Checks<<",\"rho_cache_bits_checks\":"<<cache<<",\"kappa_nondecreasing_checks\":"<<kappa<<",\"max_ledger_relative_error\":"<<maxLedger<<",\"saved_FS23_observed\":"<<fsCount<<",\"saved_FS23_positive_observed\":"<<fsPositive<<",\"saved_FS_sign_observational_after_Shepard\":true,\"soil_z_below0\":"<<zBelow<<",\"soil_x_below0\":"<<xBelow<<",\"soil_min_z_m\":"<<minZ<<",\"soil_max_speed_m_s\":"<<maxSpeed<<",\"soil_max_kappa\":"<<maxK<<",\"forced_final_not_on_nominal_plan\":true,\"plan_nominal_completed_step\":"<<H18Rows[533].completed<<",\"plan_nominal_time_s\":"<<H18Rows[533].time<<",\"native_whole_run_passed\":false,\"physical_acceptance\":false}\n";meta.flush();Need(bool(meta),"Final metadata export failed");
    std::ofstream done(out/"completion.json");done<<std::setprecision(17)<<"{\"stage\":\"c08_h18_loss_native_r1\",\"diagnostic_complete\":true,\"strict_prefix_native_passed\":true,\"whole_run_native_passed\":false,\"source_complete\":false,\"certified_PRE\":false,\"physical_acceptance\":false,\"equilibrium_acceptance\":false,\"actual_saved_frames\":534,\"strict_prefix_samples\":533,\"strict_prefix_final_part\":532,\"strict_prefix_completed_step\":"<<LossCompleted<<",\"strict_prefix_actual_end_s\":"<<LossScalar<<",\"forced_final_part\":533,\"forced_final_completed_step\":"<<completed<<",\"actual_end_s\":"<<time<<",\"final_present_IDs\":7059,\"original_native_ID_domain\":7060,\"missing_ids\":["<<excluded<<"],\"PartOut_matches_missing_ID\":true,\"PartOut_motive\":1,\"original_plan_rows\":1001,\"plan_truncated_or_rewritten\":false,\"native_rewritten\":false,\"final_arrays_original_order\":true,\"missing_ID_padded\":false,\"decoder_passes_per_saved_frame\":1,\"solver_invocations\":0}\n";done.flush();Need(bool(done),"Diagnostic completion export failed");return 0;
  }catch(const JException& e){std::cerr<<e.ToStr()<<'\n';return 1;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}

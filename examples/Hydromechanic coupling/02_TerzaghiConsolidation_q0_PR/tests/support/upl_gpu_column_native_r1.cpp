// Pure private GPU column .025s/3-frame BI4 reader; no GPU calls, JSph object, or solver.
// Native15/private3J types are read, not transcribed from CPU dynamics; fixed n is a GPU mirror sample.
#define main RetainedGpuColumnDecoderMain
#include "upl_cpu_public_native_r1.cpp"
#undef main

namespace gpucolumn {
constexpr unsigned Soil=1000,Fixed=40,Total=1040,Columns=26;
constexpr double Dp=.01,Rho=2100.,Water=1000.,KwCase=2e8;
static const double N0Case=double(float(.3)),KCase=double(float(.0001)),Mass=double(float(.21));
static const char* Fields[Columns]={"x","y","z","vx","vy","vz","PorePress","PorePress0","J","theta","sigma_xx","sigma_xy","sigma_xz","sigma_yy","sigma_yz","sigma_zz","Kplastic","FSType","FSNormal_x","FSNormal_y","FSNormal_z","ExcessPorePress","LoadAce_x","LoadAce_y","LoadAce_z","legacy_Rhop"};
static void Clock(std::ofstream& out,double time,unsigned step,double locked,double error){out.write(reinterpret_cast<const char*>(&time),8);out.write(reinterpret_cast<const char*>(&step),4);out.write(reinterpret_cast<const char*>(&locked),8);out.write(reinterpret_cast<const char*>(&error),8);}
static std::vector<unsigned> SaveSteps(unsigned samples,double dt){
  if(samples==3&&dt==2.5e-6)return{0,1,2};
  Need(samples==769&&(dt==2.5e-6||dt==1.25e-6),"Private reader admits only declared smoke or769-part coarse/half");
  const unsigned factor=dt==2.5e-6?1:2;std::vector<unsigned> steps;
  for(unsigned n=0;n<=3990;n+=10)steps.push_back(factor*n);
  for(unsigned n=3991;n<=4010;n++)steps.push_back(factor*n);
  for(unsigned n=4020;n<=5000;n+=10)steps.push_back(factor*n);
  for(unsigned n=5020;n<=10000;n+=20)steps.push_back(factor*n);
  Need(steps.size()==samples,"Internal saved-step declaration differs");return steps;
}
static Native LoadNative(JPartDataBi4& f){
  Need(f.ArraysCount()==18u,"GPU private schema requires exactly original15 plus native3J arrays");
  for(const char* key:{"HydroMechDynamicSeepage","DynamicSeepageSchema","HydroMechConductivityModel","HydroMechConductivityCk"})
    Need(!f.GetData()->ExistsValue(key)&&!f.GetPart()->ExistsValue(key),"Private public-master-OFF metadata must be absent at global and PART levels");
  for(const char* key:{"PoroCurrentVolume","PoroMixtureDensity","PoroHydraulicConductivity","PosDiv"})Need(!f.ArrayExists(key),"Public native extras are not this private schema");
  Native a;a.ids=NativeArray<unsigned>(f,"Idp",Total,DatUint);a.pos=NativeArray<tdouble3>(f,"Posd",Total,DatDouble3);Need(!f.ArrayExists("Pos"),"Double position native array required");
  a.vel=NativeArray<tfloat3>(f,"Vel",Total,DatFloat3);a.rhop=NativeArray<float>(f,"Rhop",Total,DatFloat);
  a.legacykk=NativeArray<tfloat3>(f,"Sigma_kk",Total,DatFloat3);a.legacyij=NativeArray<tfloat3>(f,"Sigma_ij",Total,DatFloat3);
  a.sk=NativeArray<tdouble3>(f,"SigmaState_kk",Total,DatDouble3);a.si=NativeArray<tdouble3>(f,"SigmaState_ij",Total,DatDouble3);
  a.plastic=NativeArray<float>(f,"Kplastic",Total,DatFloat);a.fstype=NativeArray<unsigned>(f,"FSType",Total,DatUint);
  a.normal=NativeArray<tfloat3>(f,"FSNormal",Total,DatFloat3);a.load=NativeArray<tfloat3>(f,"HydroMechLoadAce",Total,DatFloat3);
  a.p=NativeArray<float>(f,"PorePress",Total,DatFloat);a.p0=NativeArray<float>(f,"PorePress0",Total,DatFloat);a.excess=NativeArray<float>(f,"ExcessPorePress",Total,DatFloat);
  for(const char* key:{"PoroVolumeRatio","PoroPorosity","PoroThetaLastStage"})Need(f.ArrayExists(key),"Missing native GPU private J array");
  a.j=NativeArray<double>(f,"PoroVolumeRatio",Total,DatDouble);a.n=NativeArray<double>(f,"PoroPorosity",Total,DatDouble);a.theta=NativeArray<double>(f,"PoroThetaLastStage",Total,DatDouble);
  a.slot.assign(Total,~0u);for(unsigned p=0;p<Total;p++){Need(a.ids[p]<Total&&a.slot[a.ids[p]]==~0u,"Invalid/duplicate native ID");a.slot[a.ids[p]]=p;}for(unsigned p:a.slot)Need(p!=~0u,"Missing native ID");return a;
}
static std::vector<tdouble3> Initial(const Native& a){
  std::vector<tdouble3> x0(Total);std::vector<bool> soil(Soil,false),fixed(Fixed,false);
  for(unsigned id=0;id<Total;id++){
    const unsigned p=a.slot[id];const auto x=a.pos[p];x0[id]=x;const long ix=long(std::llround(x.x/Dp-.5)),iz=long(std::llround(x.z/Dp-.5));
    Need(x.y==0&&ix>=0&&ix<10&&std::fabs(x.x-(double(ix)+.5)*Dp)<=64.*DBL_EPSILON&&std::fabs(x.z-(double(iz)+.5)*Dp)<=64.*DBL_EPSILON,"Initial cell-centred decimal lattice differs");
    Need(Norm2(a.vel[p])==0&&a.rhop[p]==Rho&&a.p[p]==0&&a.p0[p]==0&&a.excess[p]==0&&Norm2(a.sk[p])==0&&Norm2(a.si[p])==0&&a.plastic[p]==0&&Norm2(a.load[p])==0&&a.j[p]==1&&a.theta[p]==0,"Initial native rest/zero stress/pressure/J state differs");
    if(id<Fixed){Need(iz>=-4&&iz<0&&a.n[p]==N0Case,"Initial fixed bottom state differs");const unsigned key=unsigned(ix)*4+unsigned(iz+4);Need(!fixed[key],"Repeated fixed initial coordinate");fixed[key]=true;}
    else{Need(iz>=0&&iz<100&&a.n[p]==N0Case,"Initial soil lattice/n0 differs");const unsigned key=unsigned(ix)+10*unsigned(iz);Need(!soil[key],"Repeated soil initial coordinate");soil[key]=true;}
  }return x0;
}
static void Read(const fs::path& dir,unsigned samples,double dt,const fs::path& out){
  const auto saveSteps=SaveSteps(samples,dt);const bool smoke=samples==3;const unsigned drainStep=dt==2.5e-6?4000:8000;
  Need(!fs::exists(out),"Retained reader output protected");Sequence(dir,samples);fs::create_directory(out);
  std::ofstream raw(out/"original15.bin",std::ios::binary),physical(out/"physical.bin",std::ios::binary),clock(out/"clock.bin",std::ios::binary),ids(out/"native_ids.csv"),fixed(out/"fixed_ids.csv"),history(out/"history.csv"),ledger(out/"ledger.csv"),markers(out/"fixed_samples.csv"),last(out/"last_poro.csv"),columns(out/"columns.csv");
  const unsigned rh[]={Total,15,samples},ph[]={Soil,Columns,samples};raw.write(reinterpret_cast<const char*>(rh),12);physical.write(reinterpret_cast<const char*>(ph),12);
  const unsigned ch[]={samples,28};clock.write(reinterpret_cast<const char*>(ch),8);
  for(auto* stream:{&ids,&fixed,&history,&ledger,&markers,&last,&columns})*stream<<std::setprecision(17);
  ids<<"row,id,x0,y0,z0\n";fixed<<"row,id,x0,y0,z0\n";last<<"id,J,n,theta\n";columns<<"column,name\n";for(unsigned c=0;c<Columns;c++)columns<<c<<','<<Fields[c]<<'\n';
  history<<"part,time_s,saved_step,dt_s,signed_dterror_s,dterror_interval_empty,dterror_used_in_noninitial_summary,pressure_RMS_Pa,material_displacement_max_mm,min_J,max_J,min_n,max_n,final_J_weighted_retained_load_x_N_per_m,final_J_weighted_retained_load_y_N_per_m,final_J_weighted_retained_load_z_N_per_m,max_ledger_relative_error,completed_step,post_open_by_completed_step,activeDrainCount\n";
  ledger<<"part,time_s,id,J,n_native,theta_native,V_derived_m2,rho_derived_kg_m3,k_derived_m_s,legacy_Rhop,PosDiv_native_present\n";
  markers<<"part,time_s,id,x,y,z,vx,vy,vz,J_native,n_native_mirror_sample,theta_native,p_native\n";
  std::vector<tdouble3> x0;double wanted=0,minError=DBL_MAX,maxError=-DBL_MAX,maxLedger=0,maxAbsJ=0;unsigned ledgerRows=0,markerRows=0,intervals=0,initialEmpty=0,previousCompleted=0,postOpenFrames=0,drainChecks=0,maxActiveDrain=0;
  for(unsigned part=0;part<samples;part++){
    JPartDataBi4 file;file.LoadFilePart(dir.string(),part,0,1);
    Need(file.GetNpiece()==1&&file.Get_Npok()==Total&&!file.Get_Nout()&&file.Get_CaseNp()==Total&&file.Get_CaseNfluid()==Soil&&file.Get_CaseNfixed()==Fixed&&!file.Get_CaseNmoving()&&!file.Get_CaseNfloat(),"Native particle identity/count/exclusion differs");
    Need(file.Get_Data2d()&&file.Get_Data2dPosY()==0&&!file.Get_Symmetry()&&!file.Get_NpDynamic()&&!file.Get_ReuseIds()&&file.Get_PeriMode()==PERI_X,"Only fixed 2D X-periodic native output admitted");
    Need(file.Get_Dp()==Dp&&file.Get_H()==double(float(.018))&&file.Get_Rhop0()==Rho&&file.Get_MassFluid()==Mass&&file.Get_MassBound()==Mass,"Native geometry/reference mass differs");
    const auto inc=file.Get_PeriXinc();Need(Finite(inc)&&std::fabs(std::fabs(inc.x)-.1)<=64.*DBL_EPSILON*.1&&inc.y==0&&inc.z==0,"Native X-periodic translation differs");
    const unsigned completed=saveSteps[part];for(unsigned it=previousCompleted;it<completed;it++)wanted+=dt;previousCompleted=completed;
    const double time=file.Get_TimeStep();const unsigned step=completed?completed-1:0;
    Need(std::isfinite(time)&&time==wanted&&file.Get_Step()==step,"Actual declared clock/zero-based saved Step differs");
    Need(file.GetPart()->ExistsValue("SymplecticDtPre",DatDouble)&&file.GetPart()->GetvDouble("SymplecticDtPre")==dt&&file.GetPart()->ExistsValue("dterror",DatDouble),"Native typed locked-dt/signed diagnostic missing");
    const double error=file.GetPart()->GetvDouble("dterror");const bool empty=error==-DBL_MAX;Need(std::isfinite(error),"Nonfinite signed dterror");Clock(clock,time,step,file.GetPart()->GetvDouble("SymplecticDtPre"),error);
    if(part){Need(!empty&&error<=1e-14,"Noninitial signed necessary-step guard failed or interval is empty");minError=(std::min)(minError,error);maxError=(std::max)(maxError,error);intervals++;}
    else{initialEmpty+=unsigned(empty);Need(empty||error<=1e-14,"Initial signed diagnostic invalid");}
    const Native a=LoadNative(file);if(!part){x0=Initial(a);for(unsigned id=0;id<Total;id++){const auto x=x0[id];if(id<Fixed)fixed<<id<<','<<id<<','<<x.x<<','<<x.y<<','<<x.z<<'\n';else ids<<id-Fixed<<','<<id<<','<<x.x<<','<<x.y<<','<<x.z<<'\n';}}
    raw.write(reinterpret_cast<const char*>(&time),8);Original15(raw,a);physical.write(reinterpret_cast<const char*>(&time),8);
    const double v0=file.Get_MassFluid()/file.Get_Rhop0();double p2=0,umax=0,jlo=DBL_MAX,jhi=-DBL_MAX,nlo=DBL_MAX,nhi=-DBL_MAX,le=0;tdouble3 loadSum=TDouble3(0);const bool postOpen=completed>drainStep;unsigned activeDrain=0;
    for(unsigned id=0;id<Total;id++){
      const unsigned p=a.slot[id];const auto x=a.pos[p];const auto v=a.vel[p];const auto s=a.sk[p];const auto q=a.si[p];
      Need(a.rhop[p]>=700&&a.rhop[p]<=3000&&a.plastic[p]==0&&a.p0[p]==0&&a.excess[p]==float(a.p[p]-a.p0[p])&&a.fstype[p]<=4,"Passive density/elastic/p0/float excess/FSType guard failed");
      Need(a.legacykk[p].x==float(s.x)&&a.legacykk[p].y==float(s.y)&&a.legacykk[p].z==float(s.z)&&a.legacyij[p].x==float(q.x)&&a.legacyij[p].y==float(q.y)&&a.legacyij[p].z==float(q.z),"Legacy stress display does not round native double state");
      if(id<Fixed){
        const double fixedN=1.-(1.-N0Case)/a.j[p];
        Need(!std::memcmp(&x,&x0[id],sizeof(tdouble3))&&Norm2(v)==0&&a.rhop[p]==Rho&&a.theta[p]==0&&a.j[p]>1.-N0Case&&fixedN>0&&fixedN<1&&a.n[p]==fixedN,"Fixed geometry/velocity/saturated GPU mirror J/n/theta differs");
        markers<<part<<','<<time<<','<<id<<','<<x.x<<','<<x.y<<','<<x.z<<','<<v.x<<','<<v.y<<','<<v.z<<','<<a.j[p]<<','<<a.n[p]<<','<<a.theta[p]<<','<<a.p[p]<<'\n';markerRows++;continue;
      }
      const double j=a.j[p],n=1.-(1.-N0Case)/j,V=v0*j,rho=Water+(Rho-Water)/j,k=KCase;
      if(postOpen&&(a.fstype[p]==2||a.fstype[p]==3)){Need(a.p[p]==0,"Post-open true FSType2/3 receiver pore pressure is not zero");activeDrain++;drainChecks++;}
      Need(j>1.-N0Case&&n>0&&n<1&&std::isfinite(V)&&V>0&&std::isfinite(rho)&&rho>0&&Close(a.n[p],n)&&std::fabs((1.-a.n[p])*j-(1.-N0Case))<=5e-13&&x.y==0&&x.z>0,"Single-J saturated/no-bottom-crossing ledger failed");
      le=(std::max)(le,std::fabs(a.n[p]-n)/n);jlo=(std::min)(jlo,j);jhi=(std::max)(jhi,j);nlo=(std::min)(nlo,n);nhi=(std::max)(nhi,n);maxAbsJ=(std::max)(maxAbsJ,std::fabs(j-1.));
      const tdouble3 u=x-x0[id];umax=(std::max)(umax,1000.*std::sqrt(Norm2(u)));p2+=double(a.p[p])*a.p[p];loadSum=loadSum+ToTDouble3(a.load[p])*(rho*V);
      // Deliberately NEW case02 schema: column21 is actual float ExcessPorePress,
      // never fabricated zero PosDiv or a relabelled old-wave26 export.
      const std::array<double,Columns> row={x.x,x.y,x.z,double(v.x),double(v.y),double(v.z),double(a.p[p]),double(a.p0[p]),j,a.theta[p],s.x,q.x,q.z,s.y,q.y,s.z,double(a.plastic[p]),double(a.fstype[p]),double(a.normal[p].x),double(a.normal[p].y),double(a.normal[p].z),double(a.excess[p]),double(a.load[p].x),double(a.load[p].y),double(a.load[p].z),double(a.rhop[p])};
      for(double value:row)Need(std::isfinite(value),"Nonfinite case02 physical export");physical.write(reinterpret_cast<const char*>(row.data()),Columns*8);
      ledger<<part<<','<<time<<','<<id<<','<<j<<','<<a.n[p]<<','<<a.theta[p]<<','<<V<<','<<rho<<','<<k<<','<<a.rhop[p]<<",0\n";ledgerRows++;
      if(part+1==samples)last<<id<<','<<j<<','<<a.n[p]<<','<<a.theta[p]<<'\n';
    }maxLedger=(std::max)(maxLedger,le);postOpenFrames+=unsigned(postOpen);maxActiveDrain=(std::max)(maxActiveDrain,activeDrain);
    history<<part<<','<<time<<','<<step<<','<<dt<<','<<error<<','<<empty<<','<<(part>0)<<','<<std::sqrt(p2/Soil)<<','<<umax<<','<<jlo<<','<<jhi<<','<<nlo<<','<<nhi<<','<<loadSum.x<<','<<loadSum.y<<','<<loadSum.z<<','<<le<<','<<completed<<','<<postOpen<<','<<activeDrain<<'\n';
  }
  Need(ledgerRows==Soil*samples&&markerRows==Fixed*samples&&intervals==samples-1,"Incomplete native/diagnostic coverage");
  for(auto* stream:{&raw,&physical,&clock,&ids,&fixed,&history,&ledger,&markers,&last,&columns}){stream->flush();Need(bool(*stream),"Reader output write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)
    <<"{\"passed\":true,\"stage\":\"upl_gpu_column_native_r1\",\"window\":\""<<(smoke?"smoke":"window25")<<"\",\"grid\":\""<<(dt==2.5e-6?"c":"h")<<"\",\"backend\":\"GPU_private\",\"model\":\"constant\",\"native_count\":1000,\"fixed_count\":40,\"total_native_count\":1040,\"samples\":"<<samples<<",\"physical_columns\":26,\"physical_schema\":\"case02_private26_col21_ExcessPorePress_NOT_wave26\",\"original_typed_arrays\":15,\"native_J_arrays\":3,\"fixed_n_is_GPU_mirror_sample_not_CPU_zero_marker\":true,\"fixed_J_n_saturated_domain_checked\":true,\"public_model_metadata_absent_global_and_part\":true,\"native_PosDiv_present\":false,\"native_V_rho_k_present\":false,\"V_rho_k_derived_not_native\":true,\"material_n0_k_Kw_from_predeclared_case_not_part_metadata\":true,\"dt_s\":"<<dt<<",\"actual_end_s\":"<<wanted<<",\"planned_completed_steps\":"<<saveSteps.back()<<",\"declared_saved_completed_steps_exact\":true,\"actual_time_step_locked_dt_exact\":true,\"noninitial_signed_dterror_intervals\":"<<intervals<<",\"initial_empty_dterror_intervals\":"<<initialEmpty<<",\"initial_dterror_excluded_from_noninitial_summary\":true,\"min_noninitial_signed_dterror_s\":"<<minError<<",\"max_noninitial_signed_dterror_s\":"<<maxError<<",\"soil_ledger_checks\":"<<ledgerRows<<",\"fixed_mirror_sample_checks\":"<<markerRows<<",\"max_ledger_relative_error\":"<<maxLedger<<",\"max_abs_J_minus_1_descriptive\":"<<maxAbsJ<<",\"no_exclusions\":true,\"initial_rest_and_decimal_lattice_verified\":true,\"double_stress_and_float_display_verified\":true,\"all_exported_physical_fields_finite\":true,\"PosDiv_fabricated_or_derived\":false,\"same_force_stage_load_budget_verified\":false,\"force_stage_guard_independently_observed\":false,\"private_solver_flags_proved_by_reader\":false,\"input_SHA_or_owned_solver_exit_verified_by_reader\":false,\"live_final_compared_by_reader\":false,\"post_open_completed_step_threshold\":"<<drainStep<<",\"post_open_frames\":"<<postOpenFrames<<",\"post_open_drained_particle_checks\":"<<drainChecks<<",\"max_activeDrainCount\":"<<maxActiveDrain<<",\"pre_open_event_pressure_not_forced_zero\":true,\"density_and_J_not_frozen_on_drained_receivers\":true,\"drainage_nonempty_acceptance_claimed\":false,\"independent_half_performed\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Reader completion write failed");
}


}
int main(int argc,char** argv){try{
  Need(argc==6&&std::string(argv[1])=="--read","Use --read DATA EXPECTED_PARTS DT NEW_REVIEW");size_t np=0,nd=0;const auto count=std::stoul(argv[3],&np);const double dt=std::stod(argv[4],&nd);
  Need(np==std::strlen(argv[3])&&nd==std::strlen(argv[4])&&count<=769&&std::isfinite(dt),"Invalid declared reader count/dt");gpucolumn::Read(argv[2],unsigned(count),dt,argv[5]);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"GPU column pure native read rejected; preserve partial review\n";return 2;}}



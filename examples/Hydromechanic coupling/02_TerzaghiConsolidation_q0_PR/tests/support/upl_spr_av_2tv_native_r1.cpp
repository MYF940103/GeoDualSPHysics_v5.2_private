// Pure typed requested u-pl full2Tv reader; all858 actual frames, never a solver.
// Common26 column21 remains ExcessPorePress; actual PosDiv and native V/rho/k are separate.
#define main RetainedColumnPublicDecoderMain
#include "upl_cpu_public_native_r1.cpp"
#undef main

namespace sprav2tv {
constexpr unsigned Soil=1000,Fixed=40,Total=1040,Columns=26,Samples=858,FullSteps=38212357,DrainStep=5243;
constexpr double Dp=.01,Rho=2100.,Water=1000.,KwCase=2e8;
static const double N0Case=double(float(.3)),KCase=double(float(.0001)),Mass=double(float(.21));
static const char* Fields[Columns]={"x","y","z","vx","vy","vz","PorePress","PorePress0","J","theta","sigma_xx","sigma_xy","sigma_xz","sigma_yy","sigma_yz","sigma_zz","Kplastic","FSType","FSNormal_x","FSNormal_y","FSNormal_z","ExcessPorePress","LoadAce_x","LoadAce_y","LoadAce_z","legacy_Rhop"};
static void Clock(std::ofstream& out,double time,unsigned step,double locked,double error){out.write(reinterpret_cast<const char*>(&time),8);out.write(reinterpret_cast<const char*>(&step),4);out.write(reinterpret_cast<const char*>(&locked),8);out.write(reinterpret_cast<const char*>(&error),8);}
static std::vector<unsigned> SaveSteps(){
  const double dt=std::ldexp(1.,-19),end=double(FullSteps)*dt;
  const double times[4]={0.,5120.*dt,5376.*dt,13120.*dt};
  const double intervals[4]={64.*dt,dt,64.*dt,.18218571428571428};
  std::vector<unsigned> steps{0};unsigned base=0;double time=0;bool finalPartial=false;
  // Independent binary64 construction of JDsOutputTime::GetNextTime, then first locked-dt crossing.
  while(steps.back()<FullSteps){
    Need(steps.size()<Samples,"Full output schedule exceeded858 frames");
    double tb=times[base],tnext=(base+1<4?times[base+1]:DBL_MAX);
    while(time>=tnext){base++;tb=times[base];tnext=(base+1<4?times[base+1]:DBL_MAX);}
    double target=0;
    if(time<tb)target=tb;
    else{
      const double interval=intervals[base];unsigned nt=unsigned((time-tb)/interval);
      target=tb+interval*nt;
      for(;target<=time;nt++)target=tb+interval*nt;
      if(target>tnext)target=tnext;
    }
    Need(std::isfinite(target)&&target>time,"Full output scheduler failed to advance");
    const unsigned completed=(target>=end?FullSteps:unsigned(std::ceil(target/dt)));
    Need(completed>steps.back(),"Full saved completed-step schedule failed to advance");
    steps.push_back(completed);time=double(completed)*dt;finalPartial=target>end;
  }
  std::vector<unsigned> startup;
  for(unsigned n=0;n<=13120;n+=64)startup.push_back(n);
  for(unsigned n=5120;n<=5376;n++)startup.push_back(n);
  std::sort(startup.begin(),startup.end());startup.erase(std::unique(startup.begin(),startup.end()),startup.end());
  Need(steps.size()==Samples&&steps.front()==0&&steps.back()==FullSteps&&time==72.8842868804931640625
    &&steps[458]==108638&&steps[Samples-2]==38124716&&finalPartial,"Declared full858 endpoint/late/final-partial schedule differs");
  Need(startup.size()==458&&std::equal(startup.begin(),startup.end(),steps.begin()),
    "Planned first458 startup integers differ; actual prefix bit comparison remains separate");
  Need(std::count_if(steps.begin(),steps.end(),[](unsigned n){return n>DrainStep;})==654,
    "Declared full654 post-open saved frames differ");
  return steps;
}
static Native LoadNative(JPartDataBi4& f){
  Need(f.ArraysCount()==22u,"Public schema requires original15 plus six native doubles and true float PosDiv");
  Metadata(f,0);return Load(f,Total,0); // Constant-law PART bool/uint/uint/double, then exact array types/counts/finite values.
}
static std::vector<tdouble3> Initial(const Native& a){
  std::vector<tdouble3> x0(Total);std::vector<bool> soil(Soil,false),fixed(Fixed,false);
  for(unsigned id=0;id<Total;id++){
    const unsigned p=a.slot[id];const auto x=a.pos[p];x0[id]=x;const long ix=long(std::llround(x.x/Dp-.5)),iz=long(std::llround(x.z/Dp-.5));
    Need(x.y==0&&ix>=0&&ix<10&&std::fabs(x.x-(double(ix)+.5)*Dp)<=64.*DBL_EPSILON&&std::fabs(x.z-(double(iz)+.5)*Dp)<=64.*DBL_EPSILON,"Initial cell-centred decimal lattice differs");
    Need(Norm2(a.vel[p])==0&&a.rhop[p]==Rho&&a.p[p]==0&&a.p0[p]==0&&a.excess[p]==0&&Norm2(a.sk[p])==0&&Norm2(a.si[p])==0&&a.plastic[p]==0&&Norm2(a.load[p])==0&&a.j[p]==1&&a.theta[p]==0,"Initial native rest/zero stress/pressure/J state differs");
    if(id<Fixed){Need(iz>=-4&&iz<0&&a.n[p]==0,"Initial fixed bottom state differs");const unsigned key=unsigned(ix)*4+unsigned(iz+4);Need(!fixed[key],"Repeated fixed initial coordinate");fixed[key]=true;}
    else{Need(iz>=0&&iz<100&&a.n[p]==N0Case,"Initial soil lattice/n0 differs");const unsigned key=unsigned(ix)+10*unsigned(iz);Need(!soil[key],"Repeated soil initial coordinate");soil[key]=true;}
  }return x0;
}
static void Read(const fs::path& dir,const fs::path& out){
  const unsigned samples=Samples,drainStep=DrainStep;const double dt=std::ldexp(1.,-19),end=double(FullSteps)*dt;
  const auto saveSteps=SaveSteps();
  Need(!fs::exists(out),"Retained reader output protected");Sequence(dir,samples);fs::create_directory(out);
  std::ofstream raw(out/"original15.bin",std::ios::binary),physical(out/"physical.bin",std::ios::binary),clock(out/"clock.bin",std::ios::binary),jt(out/"common_j_theta.bin",std::ios::binary),sn(out/"soil_n.bin",std::ios::binary),ids(out/"native_ids.csv"),fixed(out/"fixed_ids.csv"),history(out/"history.csv"),ledger(out/"ledger.csv"),markers(out/"fixed_samples.csv"),last(out/"last_poro.csv"),columns(out/"columns.csv");
  const unsigned rh[]={Total,15,samples},ph[]={Soil,Columns,samples};raw.write(reinterpret_cast<const char*>(rh),12);physical.write(reinterpret_cast<const char*>(ph),12);
  const unsigned ch[]={samples,28};clock.write(reinterpret_cast<const char*>(ch),8);
  const unsigned jh[]={Total,2,samples},nh[]={Soil,1,samples};jt.write(reinterpret_cast<const char*>(jh),12);sn.write(reinterpret_cast<const char*>(nh),12);
  for(auto* stream:{&ids,&fixed,&history,&ledger,&markers,&last,&columns})*stream<<std::setprecision(17);
  ids<<"row,id,x0,y0,z0\n";fixed<<"row,id,x0,y0,z0\n";last<<"id,J,n,theta\n";columns<<"column,name\n";for(unsigned c=0;c<Columns;c++)columns<<c<<','<<Fields[c]<<'\n';
  history<<"part,time_s,saved_step,dt_s,signed_dterror_s,dterror_interval_empty,dterror_used_in_noninitial_summary,pressure_RMS_Pa,material_displacement_max_mm,min_J,max_J,min_n,max_n,final_J_weighted_retained_load_x_N_per_m,final_J_weighted_retained_load_y_N_per_m,final_J_weighted_retained_load_z_N_per_m,max_ledger_relative_error,completed_step,post_open_by_completed_step,activeDrainCount,pressure_mean_Pa,settlement_mean_mm,top10_settlement_mean_mm,bottom10_settlement_mean_mm,settlement_abs_max_mm,velocity_XYZ_RMS_m_s,saved_theta_RMS_s_inv,saved_theta_mean_s_inv,stored_compression_zz_mean_Pa,stored_stress_Frobenius_RMS_Pa,top10_pressure_mean_Pa,bottom10_pressure_mean_Pa,native_current_rho_min_kg_m3,native_current_rho_max_kg_m3,native_current_rho_mean_kg_m3,native_current_volume_total_m2,native_rho_V_mass_kg_per_m,legacy_Rhop_min_kg_m3,legacy_Rhop_max_kg_m3\n";
  ledger<<"part,time_s,id,J,n_native,theta_native,V_native_m2,rho_native_kg_m3,k_native_m_s,PosDiv_native,V_reference_m2,rho_reference_kg_m3,k_reference_m_s,legacy_Rhop\n";
  markers<<"part,time_s,id,x,y,z,vx,vy,vz,J_native,n_zero_marker,theta_native,V_zero_marker,rho_zero_marker,k_zero_marker,PosDiv_native,p_native\n";
  std::vector<tdouble3> x0;double wanted=0,minError=DBL_MAX,maxError=-DBL_MAX,maxLedger=0,maxAbsJ=0,maxPosDiv=0;unsigned ledgerRows=0,markerRows=0,intervals=0,initialEmpty=0,previousCompleted=0,postOpenFrames=0,drainChecks=0,maxActiveDrain=0;
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
    raw.write(reinterpret_cast<const char*>(&time),8);Original15(raw,a);physical.write(reinterpret_cast<const char*>(&time),8);jt.write(reinterpret_cast<const char*>(&time),8);sn.write(reinterpret_cast<const char*>(&time),8);
    const double v0=file.Get_MassFluid()/file.Get_Rhop0();double p2=0,umax=0,jlo=DBL_MAX,jhi=-DBL_MAX,nlo=DBL_MAX,nhi=-DBL_MAX,le=0;tdouble3 loadSum=TDouble3(0);const bool postOpen=completed>drainStep;unsigned activeDrain=0;
    double pm=0,settle=0,topSettle=0,bottomSettle=0,settleAbs=0,v2=0,theta2=0,thetaMean=0,compression=0,stress2=0,topP=0,bottomP=0;
    double rhoLo=DBL_MAX,rhoHi=-DBL_MAX,rhoMean=0,volumeTotal=0,massTotal=0,legacyLo=DBL_MAX,legacyHi=-DBL_MAX;unsigned topCount=0,bottomCount=0;
    for(unsigned id=0;id<Total;id++){
      const unsigned p=a.slot[id];const auto x=a.pos[p];const auto v=a.vel[p];const auto s=a.sk[p];const auto q=a.si[p];
      jt.write(reinterpret_cast<const char*>(&a.j[p]),8);jt.write(reinterpret_cast<const char*>(&a.theta[p]),8);maxPosDiv=(std::max)(maxPosDiv,std::fabs(double(a.posdiv[p])));
      Need(a.rhop[p]>=700&&a.rhop[p]<=3000&&a.plastic[p]==0&&a.p0[p]==0&&a.excess[p]==float(a.p[p]-a.p0[p])&&a.fstype[p]<=4,"Passive density/elastic/p0/float excess/FSType guard failed");
      Need(a.legacykk[p].x==float(s.x)&&a.legacykk[p].y==float(s.y)&&a.legacykk[p].z==float(s.z)&&a.legacyij[p].x==float(q.x)&&a.legacyij[p].y==float(q.y)&&a.legacyij[p].z==float(q.z),"Legacy stress display does not round native double state");
      if(id<Fixed){
        Need(!std::memcmp(&x,&x0[id],sizeof(tdouble3))&&Norm2(v)==0&&a.rhop[p]==Rho&&a.theta[p]==0&&a.j[p]>1.-N0Case&&a.n[p]==0&&a.volume[p]==0&&a.rho[p]==0&&a.k[p]==0,"Fixed geometry/velocity/J/theta or public n/V/rho/k zero marker differs");
        markers<<part<<','<<time<<','<<id<<','<<x.x<<','<<x.y<<','<<x.z<<','<<v.x<<','<<v.y<<','<<v.z<<','<<a.j[p]<<','<<a.n[p]<<','<<a.theta[p]<<','<<a.volume[p]<<','<<a.rho[p]<<','<<a.k[p]<<','<<a.posdiv[p]<<','<<a.p[p]<<'\n';markerRows++;continue;
      }
      const double j=a.j[p],n=1.-(1.-N0Case)/j,V=v0*j,rho=Water+(Rho-Water)/j,k=KCase;
      if(postOpen&&(a.fstype[p]==2||a.fstype[p]==3)){Need(a.p[p]==0,"Post-open true FSType2/3 receiver pore pressure is not zero");activeDrain++;drainChecks++;}
      Need(j>1.-N0Case&&n>0&&n<1&&std::isfinite(V)&&V>0&&std::isfinite(rho)&&rho>0&&Close(a.n[p],n)&&std::fabs((1.-a.n[p])*j-(1.-N0Case))<=5e-13&&x.y==0&&x.z>0,"Single-J saturated/no-bottom-crossing ledger failed");
      const double got[]={a.n[p],a.volume[p],a.rho[p],a.k[p]},ref[]={n,V,rho,k};
      for(unsigned z=0;z<4;z++){Need(Close(got[z],ref[z]),"Public native n/V/rho/k does not match the same compacted J");maxLedger=(std::max)(maxLedger,std::fabs(got[z]-ref[z])/(std::max)(std::fabs(ref[z]),DBL_MIN));}
      sn.write(reinterpret_cast<const char*>(&a.n[p]),8);
      le=(std::max)(le,std::fabs(a.n[p]-n)/n);jlo=(std::min)(jlo,j);jhi=(std::max)(jhi,j);nlo=(std::min)(nlo,n);nhi=(std::max)(nhi,n);maxAbsJ=(std::max)(maxAbsJ,std::fabs(j-1.));
      const double down=-1000.*(x.z-x0[id].z);pm+=double(a.p[p]);settle+=down;settleAbs=(std::max)(settleAbs,std::fabs(down));v2+=Norm2(v);theta2+=a.theta[p]*a.theta[p];thetaMean+=a.theta[p];compression-=s.z;stress2+=Norm2(s)+2.*Norm2(q);
      rhoLo=(std::min)(rhoLo,a.rho[p]);rhoHi=(std::max)(rhoHi,a.rho[p]);rhoMean+=a.rho[p];volumeTotal+=a.volume[p];massTotal+=a.rho[p]*a.volume[p];legacyLo=(std::min)(legacyLo,double(a.rhop[p]));legacyHi=(std::max)(legacyHi,double(a.rhop[p]));
      const long layer=std::llround(x0[id].z/Dp-.5);if(layer==99){topSettle+=down;topP+=double(a.p[p]);topCount++;}if(layer==0){bottomSettle+=down;bottomP+=double(a.p[p]);bottomCount++;}
      const tdouble3 u=x-x0[id];umax=(std::max)(umax,1000.*std::sqrt(Norm2(u)));p2+=double(a.p[p])*a.p[p];loadSum=loadSum+ToTDouble3(a.load[p])*(rho*V);
      // Deliberately NEW case02 schema: column21 is actual float ExcessPorePress,
      // never fabricated zero PosDiv or a relabelled old-wave26 export.
      const std::array<double,Columns> row={x.x,x.y,x.z,double(v.x),double(v.y),double(v.z),double(a.p[p]),double(a.p0[p]),j,a.theta[p],s.x,q.x,q.z,s.y,q.y,s.z,double(a.plastic[p]),double(a.fstype[p]),double(a.normal[p].x),double(a.normal[p].y),double(a.normal[p].z),double(a.excess[p]),double(a.load[p].x),double(a.load[p].y),double(a.load[p].z),double(a.rhop[p])};
      for(double value:row)Need(std::isfinite(value),"Nonfinite case02 physical export");physical.write(reinterpret_cast<const char*>(row.data()),Columns*8);
      ledger<<part<<','<<time<<','<<id<<','<<j<<','<<a.n[p]<<','<<a.theta[p]<<','<<a.volume[p]<<','<<a.rho[p]<<','<<a.k[p]<<','<<a.posdiv[p]<<','<<V<<','<<rho<<','<<k<<','<<a.rhop[p]<<'\n';ledgerRows++;
      if(part+1==samples)last<<id<<','<<j<<','<<a.n[p]<<','<<a.theta[p]<<'\n';
    }maxLedger=(std::max)(maxLedger,le);postOpenFrames+=unsigned(postOpen);maxActiveDrain=(std::max)(maxActiveDrain,activeDrain);
    Need(topCount==10&&bottomCount==10,"Initial-material top/bottom ten-ID layers differ");
    Need(activeDrain==(postOpen?10u:0u),"Declared per-frame native drainage receiver count differs");
    for(double value:{pm,settle,topSettle,bottomSettle,settleAbs,v2,theta2,thetaMean,compression,stress2,topP,bottomP,rhoLo,rhoHi,rhoMean,volumeTotal,massTotal,legacyLo,legacyHi})Need(std::isfinite(value),"Nonfinite descriptive saved-field summary");
    history<<part<<','<<time<<','<<step<<','<<dt<<','<<error<<','<<empty<<','<<(part>0)<<','<<std::sqrt(p2/Soil)<<','<<umax<<','<<jlo<<','<<jhi<<','<<nlo<<','<<nhi<<','<<loadSum.x<<','<<loadSum.y<<','<<loadSum.z<<','<<le<<','<<completed<<','<<postOpen<<','<<activeDrain<<','<<pm/Soil<<','<<settle/Soil<<','<<topSettle/topCount<<','<<bottomSettle/bottomCount<<','<<settleAbs<<','<<std::sqrt(v2/Soil)<<','<<std::sqrt(theta2/Soil)<<','<<thetaMean/Soil<<','<<compression/Soil<<','<<std::sqrt(stress2/Soil)<<','<<topP/topCount<<','<<bottomP/bottomCount<<','<<rhoLo<<','<<rhoHi<<','<<rhoMean/Soil<<','<<volumeTotal<<','<<massTotal<<','<<legacyLo<<','<<legacyHi<<'\n';
  }
  Need(wanted==end&&ledgerRows==Soil*samples&&markerRows==Fixed*samples&&intervals==samples-1,"Incomplete dyadic-end/native/diagnostic coverage");
  Need(postOpenFrames==654&&drainChecks==6540&&maxActiveDrain==10,"Declared full654 post-open frames/6540 drainage checks differ");
  for(auto* stream:{&raw,&physical,&clock,&jt,&sn,&ids,&fixed,&history,&ledger,&markers,&last,&columns}){stream->flush();Need(bool(*stream),"Reader output write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)
    <<"{\"passed\":true,\"stage\":\"upl_spr_av_2tv_native_r1\",\"backend\":\"CPU_public\",\"window\":\"full2Tv\",\"full_completed\":true"
    <<",\"model\":\"constant\",\"conductivity_model\":0,\"conductivity_Ck\":0,\"public_schema\":true,\"native_count\":1000,\"fixed_count\":40,\"total_native_count\":1040,\"samples\":"<<samples
    <<",\"physical_columns\":26,\"physical_schema\":\"case02_common26_col21_ExcessPorePress_NOT_wave26\",\"original_typed_arrays\":15,\"native_dynamic_double_arrays\":6,\"native_total_arrays\":22"
    <<",\"native_PosDiv_present\":true,\"native_PosDiv_is_float\":true,\"native_V_rho_k_present\":true,\"PART_typed_public_metadata_verified\":true,\"public_master_on\":true,\"dt_s\":"<<dt
    <<",\"planned_end_s\":"<<end<<",\"declared_ramp_and_drain_event_s\":"<<5243.*std::ldexp(1.,-19)<<",\"event_is_declared_window_not_BI4_metadata\":true,\"actual_end_s\":"<<wanted
    <<",\"planned_completed_steps\":"<<saveSteps.back()<<",\"declared_saved_completed_steps_exact\":true,\"actual_time_step_locked_dt_exact\":true"
    <<",\"output_schedule\":\"source_equivalent_binary64_GetNextTime_four_segments\",\"planned_first458_startup_integers_verified\":true,\"first_late_completed_step\":"<<saveSteps[458]
    <<",\"penultimate_completed_step\":"<<saveSteps[Samples-2]<<",\"final_frame_is_partial_output_interval\":true,\"noninitial_signed_dterror_intervals\":"<<intervals
    <<",\"initial_empty_dterror_intervals\":"<<initialEmpty<<",\"initial_dterror_excluded_from_noninitial_summary\":true,\"min_noninitial_signed_dterror_s\":"<<minError<<",\"max_noninitial_signed_dterror_s\":"<<maxError
    <<",\"soil_ledger_checks\":"<<ledgerRows<<",\"fixed_public_zero_marker_checks\":"<<markerRows<<",\"all_native_J_theta_rows\":"<<Total*samples<<",\"soil_native_n_rows\":"<<ledgerRows
    <<",\"fixed_J_theta_original15_not_zeroed_or_masked\":true,\"max_ledger_relative_error\":"<<maxLedger<<",\"max_abs_J_minus_1_descriptive\":"<<maxAbsJ
    <<",\"max_abs_actual_native_PosDiv_descriptive\":"<<maxPosDiv<<",\"no_exclusions\":true,\"initial_rest_and_decimal_lattice_verified\":true,\"double_stress_and_float_display_verified\":true"
    <<",\"all_exported_physical_fields_finite\":true,\"PosDiv_fabricated_or_derived\":false,\"common26_column21_is_actual_ExcessPorePress\":true,\"post_open_completed_step_threshold\":"<<drainStep
    <<",\"post_open_frames\":"<<postOpenFrames<<",\"post_open_drained_particle_checks\":"<<drainChecks<<",\"max_activeDrainCount\":"<<maxActiveDrain
    <<",\"pre_open_event_pressure_not_forced_zero\":true,\"density_and_J_not_frozen_on_drained_receivers\":true,\"historical_private_comparison_performed_by_reader\":false"
    <<",\"backend_argument_proved_from_owned_program\":false,\"input_SHA_or_owned_solver_exit_verified_by_reader\":false,\"HG_RunOut_verified_by_reader\":false,\"live_final_compared_by_reader\":false"
    <<",\"same_force_stage_load_budget_verified\":false,\"force_stage_guard_independently_observed\":false,\"drainage_nonempty_acceptance_claimed\":false,\"independent_half_performed\":false"
    <<",\"descriptive_saved_field_summaries\":true,\"declared_full_window_end_s\":"<<end<<",\"full_window_prefix_data_compared\":false,\"measured_short458_prefix_bitwise_identity\":false"
    <<",\"exact_restart_equivalence_claimed\":false,\"post_open_native_receiver_coverage_verified\":true,\"new_scientific_acceptance_gate\":false,\"physical_acceptance\":false}\n";
  done.flush();Need(bool(done),"Reader completion write failed");
}



}
int main(int argc,char** argv){try{
  Need(argc==6&&std::string(argv[1])=="--read","Use --read CPU DATA full2Tv NEW_REVIEW");
  Need(std::string(argv[2])=="CPU"&&std::string(argv[4])=="full2Tv","Only CPU full2Tv native read admitted");
  sprav2tv::Read(argv[3],argv[5]);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Full2Tv typed native read rejected; preserve partial review\n";return 2;}}

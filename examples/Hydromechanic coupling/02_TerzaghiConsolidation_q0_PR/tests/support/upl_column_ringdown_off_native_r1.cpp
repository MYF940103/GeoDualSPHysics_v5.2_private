// Pure GPU-only noaux legacy u-pw OFF native reader. Never calls a solver.
// common24 omits J/theta; absent dynamic quantities are never fabricated.
#define main RetainedOffNeutralDecoderMain
#include "upl_cpu_public_native_r1.cpp"
#undef main

namespace columnringdownoff {
constexpr unsigned Soil=1000,Fixed=40,Total=1040,Columns=24,Samples=1277;
constexpr double Dp=.01,Rho=2100.;
static const double Mass=double(float(.21));
static const char* Fields[Columns]={"x","y","z","vx","vy","vz","PorePress","PorePress0","sigma_xx","sigma_xy","sigma_xz","sigma_yy","sigma_yz","sigma_zz","Kplastic","FSType","FSNormal_x","FSNormal_y","FSNormal_z","ExcessPorePress","LoadAce_x","LoadAce_y","LoadAce_z","legacy_Rhop"};
using Common=std::array<double,Columns>;
static Native Load15(JPartDataBi4& file){
  Need(file.ArraysCount()==15,"OFF requires exactly the fifteen original typed arrays");
  for(const char* key:{"HydroMechDynamicSeepage","DynamicSeepageSchema","HydroMechConductivityModel","HydroMechConductivityCk"})Need(!file.GetPart()->ExistsValue(key)&&!file.GetData()->ExistsValue(key),std::string("OFF unexpected global/PART metadata: ")+key);
  Native a=Load(file,Total,-1); // Audited original15 OFF path: exact types/counts/finite/IDs and all seven dynamic arrays absent.
  // Deliberately do not call Load(model0), Metadata, Physical, Energy or the old wave Read.
  Need(a.j.empty()&&a.n.empty()&&a.theta.empty()&&a.volume.empty()&&a.rho.empty()&&a.k.empty()&&a.posdiv.empty(),"Absent fields must remain absent");return a;
}
static Common Row24(const Native& a,unsigned p){
  const auto x=a.pos[p],s=a.sk[p],q=a.si[p];const auto v=a.vel[p],normal=a.normal[p],load=a.load[p];
  // Stored SigmaState_ij is xy,yz,xz. Column19 is real ExcessPorePress, not PosDiv.
  return{x.x,x.y,x.z,double(v.x),double(v.y),double(v.z),double(a.p[p]),double(a.p0[p]),s.x,q.x,q.z,s.y,q.y,s.z,double(a.plastic[p]),double(a.fstype[p]),double(normal.x),double(normal.y),double(normal.z),double(a.excess[p]),double(load.x),double(load.y),double(load.z),double(a.rhop[p])};
}
static std::vector<unsigned> SaveSteps(bool smoke,bool half){
  if(smoke)return{0,1,2};const unsigned factor=half?2:1;std::vector<unsigned> out;
  for(unsigned n=0;n<=65536;n+=64)out.push_back(factor*n);for(unsigned n=5120;n<=5376;n++)out.push_back(factor*n);
  std::sort(out.begin(),out.end());out.erase(std::unique(out.begin(),out.end()),out.end());Need(out.size()==Samples&&out.back()==factor*65536,"Declared dyadic saved-step set differs");return out;
}
static std::vector<tdouble3> Initial(const Native& a){
  std::vector<tdouble3> x0(Total);std::vector<bool> soil(Soil,false),fixed(Fixed,false);
  for(unsigned id=0;id<Total;id++){
    const unsigned p=a.slot[id];const auto x=a.pos[p];x0[id]=x;const long ix=long(std::llround(x.x/Dp-.5)),iz=long(std::llround(x.z/Dp-.5));
    Need(x.y==0&&ix>=0&&ix<10&&std::fabs(x.x-(double(ix)+.5)*Dp)<=64.*DBL_EPSILON&&std::fabs(x.z-(double(iz)+.5)*Dp)<=64.*DBL_EPSILON,"Initial decimal cell-centred lattice differs");
    Need(Norm2(a.vel[p])==0&&a.rhop[p]==Rho&&a.p[p]==0&&a.p0[p]==0&&a.excess[p]==0&&Norm2(a.sk[p])==0&&Norm2(a.si[p])==0&&a.plastic[p]==0&&Norm2(a.load[p])==0,"Initial original15 rest state differs");
    if(id<Fixed){Need(iz>=-4&&iz<0,"Fixed initial lattice differs");const unsigned key=unsigned(ix)*4+unsigned(iz+4);Need(!fixed[key],"Duplicate fixed initial coordinate");fixed[key]=true;}
    else{Need(iz>=0&&iz<100,"Soil initial lattice differs");const unsigned key=unsigned(ix)+10*unsigned(iz);Need(!soil[key],"Duplicate soil initial coordinate");soil[key]=true;}
  }return x0;
}
static void Read(const fs::path& dir,bool smoke,bool half,const fs::path& out){
  const auto steps=SaveSteps(smoke,half);const unsigned samples=unsigned(steps.size()),drainStep=half?10486:5243;const double dt=std::ldexp(1.,half?-20:-19),end=smoke?2.*dt:.125;
  Need(!fs::exists(out),"Retained review protected");Sequence(dir,samples);fs::create_directory(out);
  std::ofstream raw(out/"original15.bin",std::ios::binary),common(out/"common24.bin",std::ios::binary),clock(out/"clock.bin",std::ios::binary),ids(out/"native_ids.csv"),fixed(out/"fixed_ids.csv"),history(out/"history.csv"),markers(out/"fixed_samples.csv"),columns(out/"columns.csv");
  const unsigned rh[]={Total,15,samples},ph[]={Soil,Columns,samples},ch[]={samples,28};raw.write(reinterpret_cast<const char*>(rh),12);common.write(reinterpret_cast<const char*>(ph),12);clock.write(reinterpret_cast<const char*>(ch),8);
  for(auto* stream:{&ids,&fixed,&history,&markers,&columns})*stream<<std::setprecision(17);
  ids<<"row,id,x0,y0,z0\n";fixed<<"row,id,x0,y0,z0\n";columns<<"column,name\n";markers<<"part,time_s,id";for(unsigned c=0;c<Columns;c++){columns<<c<<','<<Fields[c]<<'\n';markers<<','<<Fields[c];}markers<<'\n';
  history<<"part,time_s,saved_step,dt_s,signed_dterror_s,dterror_interval_empty,dterror_used_in_noninitial_summary,completed_step,post_open_by_completed_step,activeDrainCount,pressure_RMS_Pa,pressure_mean_Pa,top10_pressure_mean_Pa,bottom10_pressure_mean_Pa,material_displacement_max_mm,settlement_mean_mm,top10_settlement_mean_mm,bottom10_settlement_mean_mm,settlement_abs_max_mm,velocity_XYZ_RMS_m_s,velocity_x_mean_m_s,velocity_y_mean_m_s,velocity_z_mean_m_s,stored_sigma_xx_mean_Pa,stored_sigma_xy_mean_Pa,stored_sigma_xz_mean_Pa,stored_sigma_yy_mean_Pa,stored_sigma_yz_mean_Pa,stored_sigma_zz_mean_Pa,stored_stress_Frobenius_RMS_Pa,legacy_Rhop_min_kg_m3,legacy_Rhop_max_kg_m3\n";
  std::vector<tdouble3> x0;double wanted=0,minError=DBL_MAX,maxError=-DBL_MAX;unsigned previous=0,intervals=0,initialEmpty=0,soilRows=0,fixedRows=0,postFrames=0,drainChecks=0,minDrain=~0u,maxDrain=0;
  for(unsigned part=0;part<samples;part++){
    JPartDataBi4 file;file.LoadFilePart(dir.string(),part,0,1);
    Need(file.GetNpiece()==1&&file.Get_Npok()==Total&&!file.Get_Nout()&&file.Get_CaseNp()==Total&&file.Get_CaseNfluid()==Soil&&file.Get_CaseNfixed()==Fixed&&!file.Get_CaseNmoving()&&!file.Get_CaseNfloat(),"Native count/type/piece/exclusion differs");
    Need(file.Get_Data2d()&&file.Get_Data2dPosY()==0&&!file.Get_Symmetry()&&!file.Get_NpDynamic()&&!file.Get_ReuseIds()&&file.Get_PeriMode()==PERI_X,"Only fixed2D X-periodic native scope admitted");
    Need(file.Get_Dp()==Dp&&file.Get_H()==double(float(.018))&&file.Get_Rhop0()==Rho&&file.Get_MassFluid()==Mass&&file.Get_MassBound()==Mass,"Native geometry/reference mass differs");
    const auto inc=file.Get_PeriXinc();Need(Finite(inc)&&std::fabs(std::fabs(inc.x)-.1)<=64.*DBL_EPSILON*.1&&inc.y==0&&inc.z==0,"X-periodic translation differs");
    const unsigned completed=steps[part],step=completed?completed-1:0;for(unsigned n=previous;n<completed;n++)wanted+=dt;previous=completed;const double time=file.Get_TimeStep();
    Need(std::isfinite(time)&&time==wanted&&file.Get_Step()==step,"Actual dyadic clock/zero-based saved Step differs");
    Need(file.GetPart()->ExistsValue("SymplecticDtPre",DatDouble)&&file.GetPart()->GetvDouble("SymplecticDtPre")==dt&&file.GetPart()->ExistsValue("dterror",DatDouble),"Typed locked dt/signed diagnostic missing");
    const double error=file.GetPart()->GetvDouble("dterror");const bool empty=error==-DBL_MAX;Need(std::isfinite(error),"Nonfinite signed dterror");
    if(part){Need(!empty&&error<=1e-14,"Noninitial original signed necessary-step guard failed or empty");minError=(std::min)(minError,error);maxError=(std::max)(maxError,error);intervals++;}else{initialEmpty+=unsigned(empty);Need(empty||error<=1e-14,"Initial diagnostic invalid");}
    clock.write(reinterpret_cast<const char*>(&time),8);clock.write(reinterpret_cast<const char*>(&step),4);clock.write(reinterpret_cast<const char*>(&dt),8);clock.write(reinterpret_cast<const char*>(&error),8);
    const Native a=Load15(file);if(!part){x0=Initial(a);for(unsigned id=0;id<Total;id++){const auto x=x0[id];if(id<Fixed)fixed<<id<<','<<id<<','<<x.x<<','<<x.y<<','<<x.z<<'\n';else ids<<id-Fixed<<','<<id<<','<<x.x<<','<<x.y<<','<<x.z<<'\n';}}
    raw.write(reinterpret_cast<const char*>(&time),8);Original15(raw,a);common.write(reinterpret_cast<const char*>(&time),8);
    double p2=0,pm=0,topP=0,bottomP=0,umax=0,settle=0,topSettle=0,bottomSettle=0,settleAbs=0,v2=0,stress2=0,rhoLo=DBL_MAX,rhoHi=-DBL_MAX;std::array<double,6> sigmaSum{};tdouble3 velocitySum=TDouble3(0);unsigned topCount=0,bottomCount=0,active=0;const bool post=completed>drainStep;
    for(unsigned id=0;id<Total;id++){
      const unsigned p=a.slot[id];const auto x=a.pos[p],s=a.sk[p],q=a.si[p];const auto v=a.vel[p];const auto row=Row24(a,p);
      Need(a.rhop[p]>=700&&a.rhop[p]<=3000&&a.plastic[p]==0&&a.p0[p]==0&&a.excess[p]==float(a.p[p]-a.p0[p])&&a.fstype[p]<=4,"Original density/elastic/p0/excess/FSType guard failed");for(double value:row)Need(std::isfinite(value),"Nonfinite common24 field");
      Need(a.legacykk[p].x==float(s.x)&&a.legacykk[p].y==float(s.y)&&a.legacykk[p].z==float(s.z)&&a.legacyij[p].x==float(q.x)&&a.legacyij[p].y==float(q.y)&&a.legacyij[p].z==float(q.z),"Float stress display does not round native double stress");
      if(id<Fixed){
        // GPU completed SymplecticCor resets stored fixed Vel/rho; mirrored p/stress are NOT zero markers.
        Need(!std::memcmp(&x,&x0[id],sizeof(tdouble3))&&Norm2(v)==0&&a.rhop[p]==Rho,"GPU saved fixed position/velocity/reference density differs");
        markers<<part<<','<<time<<','<<id;for(double value:row)markers<<','<<value;markers<<'\n';fixedRows++;continue;
      }
      Need(x.y==0&&x.z>0,"Soil left2D plane or crossed the bottom");if(post&&(a.fstype[p]==2||a.fstype[p]==3)){Need(a.p[p]==0,"Post-open actual FSType2/3 receiver p is not zero");active++;drainChecks++;}
      common.write(reinterpret_cast<const char*>(row.data()),Columns*8);soilRows++;const auto u=x-x0[id];const double down=-1000.*u.z;p2+=double(a.p[p])*a.p[p];pm+=a.p[p];umax=(std::max)(umax,1000.*std::sqrt(Norm2(u)));settle+=down;settleAbs=(std::max)(settleAbs,std::fabs(down));v2+=Norm2(v);velocitySum=velocitySum+ToTDouble3(v);stress2+=Norm2(s)+2.*Norm2(q);const double components[]={s.x,q.x,q.z,s.y,q.y,s.z};for(unsigned c=0;c<6;c++)sigmaSum[c]+=components[c];
      rhoLo=(std::min)(rhoLo,double(a.rhop[p]));rhoHi=(std::max)(rhoHi,double(a.rhop[p]));const long layer=std::llround(x0[id].z/Dp-.5);if(layer==99){topP+=a.p[p];topSettle+=down;topCount++;}if(layer==0){bottomP+=a.p[p];bottomSettle+=down;bottomCount++;}
    }
    Need(topCount==10&&bottomCount==10,"Initial-material top/bottom ten-ID layers differ");if(post){Need(active>0,"Post-open actual drainage mask is empty");postFrames++;minDrain=(std::min)(minDrain,active);maxDrain=(std::max)(maxDrain,active);}
    for(double value:{p2,pm,topP,bottomP,umax,settle,topSettle,bottomSettle,settleAbs,v2,stress2,rhoLo,rhoHi,velocitySum.x,velocitySum.y,velocitySum.z})Need(std::isfinite(value),"Nonfinite descriptive summary");for(double value:sigmaSum)Need(std::isfinite(value),"Nonfinite descriptive stress summary");
    history<<part<<','<<time<<','<<step<<','<<dt<<','<<error<<','<<empty<<','<<(part>0)<<','<<completed<<','<<post<<','<<active<<','<<std::sqrt(p2/Soil)<<','<<pm/Soil<<','<<topP/topCount<<','<<bottomP/bottomCount<<','<<umax<<','<<settle/Soil<<','<<topSettle/topCount<<','<<bottomSettle/bottomCount<<','<<settleAbs<<','<<std::sqrt(v2/Soil)<<','<<velocitySum.x/Soil<<','<<velocitySum.y/Soil<<','<<velocitySum.z/Soil;for(double value:sigmaSum)history<<','<<value/Soil;history<<','<<std::sqrt(stress2/Soil)<<','<<rhoLo<<','<<rhoHi<<'\n';
  }
  Need(wanted==end&&soilRows==Soil*samples&&fixedRows==Fixed*samples&&intervals==samples-1&&postFrames==(smoke?0:1073),"Incomplete native/clock/post-event coverage");
  for(auto* stream:{&raw,&common,&clock,&ids,&fixed,&history,&markers,&columns}){stream->flush();Need(bool(*stream),"Reader output write failed");}
  std::ofstream done(out/"completion.json");done<<std::setprecision(17)
    <<"{\"passed\":true,\"stage\":\"upl_column_ringdown_off_native_r1\",\"backend\":\"GPU_legacy_upw_OFF\",\"window\":\""<<(smoke?"smoke":"ringdown125")<<"\",\"preset\":\""<<(smoke?"smoke":(half?"half":"coarse"))<<"\",\"grid\":\""<<(half?"h":"c")<<"\",\"native_count\":1000,\"fixed_count\":40,\"total_native_count\":1040,\"samples\":"<<samples<<",\"original_typed_arrays\":15,\"native_total_arrays\":15,\"common_columns\":24,\"common_schema\":\"case02_OFF_common24_no_J_theta_column19_ExcessPorePress\",\"dynamic_arrays_and_global_PART_metadata_absent\":true,\"absent_dynamic_fields_fabricated\":false,\"native_J_n_theta_V_rho_k_PosDiv_present\":false,\"declared_conductivity_model\":0,\"declared_Ck\":0,\"runtime_model_verified_from_BI4\":false,\"dt_s\":"<<dt<<",\"planned_end_s\":"<<end<<",\"actual_end_s\":"<<wanted<<",\"planned_completed_steps\":"<<steps.back()<<",\"declared_saved_completed_steps_exact\":true,\"actual_time_step_locked_dt_exact\":true,\"declared_event_s\":"<<5243.*std::ldexp(1.,-19)<<",\"event_is_declared_preset_not_BI4_metadata\":true,\"post_open_completed_step_threshold\":"<<drainStep<<",\"post_open_frames\":"<<postFrames<<",\"post_open_drained_particle_checks\":"<<drainChecks<<",\"min_activeDrainCount_post_open\":"<<(smoke?0:minDrain)<<",\"max_activeDrainCount\":"<<maxDrain<<",\"noninitial_signed_dterror_intervals\":"<<intervals<<",\"initial_empty_dterror_intervals\":"<<initialEmpty<<",\"initial_dterror_excluded_from_noninitial_summary\":true,\"min_noninitial_signed_dterror_s\":"<<minError<<",\"max_noninitial_signed_dterror_s\":"<<maxError<<",\"original_legacy_necessary_step_telemetry_checked\":true,\"dynamic_complete_rate_necessary_bound_inferred_for_OFF\":false,\"all_native_original15_finite_elastic_no_exclusions\":true,\"initial_rest_and_decimal_lattice_verified\":true,\"soil_common_rows\":"<<soilRows<<",\"fixed_original15_rows\":"<<fixedRows<<",\"fixed_positions_bit_exact\":true,\"GPU_saved_fixed_velocity_zero_reference_density_verified\":true,\"fixed_mirrored_pressure_and_stress_preserved_not_zeroed\":true,\"soil_top_bottom_summary_uses_initial_material_IDs\":true,\"drainage_keeps_preopen_event_unprojected\":true,\"descriptive_saved_field_summaries\":true,\"owned_program_input_source_hashes_verified_by_reader\":false,\"solver_or_restart_called\":false,\"force_stage_or_half_verified\":false,\"ON_OFF_equivalence_claimed\":false,\"physical_acceptance\":false}\n";done.flush();Need(bool(done),"Completion write failed");
}
}
int main(int argc,char** argv){try{
  Need(argc==6&&std::string(argv[1])=="--read"&&std::string(argv[2])=="GPU","Use --read GPU DATA smoke|coarse|half NEW_REVIEW; CPU not admitted");
  const std::string preset=argv[4];Need(preset=="smoke"||preset=="coarse"||preset=="half","Undeclared OFF dyadic preset");columnringdownoff::Read(argv[3],preset=="smoke",preset=="half",argv[5]);return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::string& e){std::cerr<<e<<'\n';return 1;}catch(const char* e){std::cerr<<e<<'\n';return 1;}catch(...){std::cerr<<"Pure OFF native read rejected; preserve partial review\n";return 2;}}

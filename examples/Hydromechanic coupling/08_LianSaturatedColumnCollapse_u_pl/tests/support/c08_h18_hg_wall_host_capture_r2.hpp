// Private host-exception capture only; no GPU module or public class changes.
#ifndef C08_H18_HG_WALL_HOST_CAPTURE_R2_HPP
#define C08_H18_HG_WALL_HOST_CAPTURE_R2_HPP
#include "Functions.h"
#include "JCellDivDataGpu.h"
#include <cuda_runtime_api.h>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>
namespace c08wallhost {
struct Meta{
  unsigned np,npb,npbok,stage,invalid;unsigned long long nstep;double time;
  StDivDataGpu div;
  unsigned kernel,axis,cellcode,simulate2d,periactive,slipmode;
  double domx,domy,domz,dp;
  float threshold,massf,rhopzero,h,kernelsize2,poscellsize,scell,awen,bwen;
  float gravityx,gravityy,gravityz,porosity,water_rho;double solid0;
  bool sigma_pre,pore_pre,j_pre;
};
struct Arrays{
  const unsigned* id;const typecode* code;const double2* xy;const double* z;
  const float4* poscell;const unsigned* dcell;const double* j;const tmatrix3d* corr;
  const float3* normal;const byte* mode;
};
struct Copy{
  std::string name,dtype,file,error;size_t count,element_bytes;
  int cuda_status;bool allocated,copied,written;
};
inline std::string Json(const std::string& value){
  std::ostringstream out;out.imbue(std::locale::classic());out<<'"';
  for(unsigned char c:value){
    if(c=='"'||c=='\\')out<<'\\'<<char(c);
    else if(c=='\n')out<<"\\n";
    else if(c=='\r')out<<"\\r";
    else if(c=='\t')out<<"\\t";
    else if(c<32)out<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<unsigned(c)<<std::dec;
    else out<<char(c);
  }
  out<<'"';return out.str();
}
inline void Key(std::ostream& out,bool& comma,const char* name){if(comma)out<<',';comma=true;out<<Json(name)<<':';}
inline void Bool(std::ostream& out,bool& comma,const char* name,bool value){Key(out,comma,name);out<<(value?"true":"false");}
inline void Text(std::ostream& out,bool& comma,const char* name,const std::string& value){Key(out,comma,name);out<<Json(value);}
template<class T> inline void Number(std::ostream& out,bool& comma,const char* name,T value){Key(out,comma,name);out<<value;}
inline std::string Bits(float value){
  static_assert(sizeof(float)==4,"Actual float32 required");std::uint32_t v=0;std::memcpy(&v,&value,sizeof(v));
  std::ostringstream out;out.imbue(std::locale::classic());out<<std::hex<<std::setfill('0')<<std::setw(8)<<v;return out.str();
}
inline std::string Bits(double value){
  static_assert(sizeof(double)==8,"Actual float64 required");std::uint64_t v=0;std::memcpy(&v,&value,sizeof(v));
  std::ostringstream out;out.imbue(std::locale::classic());out<<std::hex<<std::setfill('0')<<std::setw(16)<<v;return out.str();
}
template<class T> inline void Scalar(std::ostream& out,T value){out<<','<<std::setprecision(17)<<double(value)<<','<<Bits(value);}
template<class T> inline typename std::enable_if<std::is_integral<T>::value>::type Columns(std::ostream& out,T*){out<<"sorted_slot,value\n";}
template<class T> inline typename std::enable_if<std::is_integral<T>::value>::type Row(std::ostream& out,T value){out<<','<<static_cast<unsigned long long>(value);}
template<class T> inline typename std::enable_if<std::is_floating_point<T>::value>::type Columns(std::ostream& out,T*){out<<"sorted_slot,value17,hex_bits\n";}
template<class T> inline typename std::enable_if<std::is_floating_point<T>::value>::type Row(std::ostream& out,T value){Scalar(out,value);}
inline void Columns(std::ostream& out,double2*){out<<"sorted_slot,x17,x_hex,y17,y_hex\n";}
inline void Row(std::ostream& out,const double2& v){Scalar(out,v.x);Scalar(out,v.y);}
inline void Columns(std::ostream& out,float4*){out<<"sorted_slot,x17,x_hex,y17,y_hex,z17,z_hex,w17,w_hex\n";}
inline void Row(std::ostream& out,const float4& v){Scalar(out,v.x);Scalar(out,v.y);Scalar(out,v.z);Scalar(out,v.w);}
inline void Columns(std::ostream& out,float3*){out<<"sorted_slot,x17,x_hex,y17,y_hex,z17,z_hex\n";}
inline void Row(std::ostream& out,const float3& v){Scalar(out,v.x);Scalar(out,v.y);Scalar(out,v.z);}
inline void Columns(std::ostream& out,tmatrix3d*){out<<"sorted_slot,a11_17,a11_hex,a12_17,a12_hex,a13_17,a13_hex,a21_17,a21_hex,a22_17,a22_hex,a23_17,a23_hex,a31_17,a31_hex,a32_17,a32_hex,a33_17,a33_hex\n";}
inline void Row(std::ostream& out,const tmatrix3d& v){Scalar(out,v.a11);Scalar(out,v.a12);Scalar(out,v.a13);Scalar(out,v.a21);Scalar(out,v.a22);Scalar(out,v.a23);Scalar(out,v.a31);Scalar(out,v.a32);Scalar(out,v.a33);}
inline void Columns(std::ostream& out,int2*){out<<"fluid_table_index,begin_sorted_slot,end_sorted_slot_exclusive\n";}
inline void Row(std::ostream& out,const int2& v){out<<','<<v.x<<','<<v.y;}
template<class T> inline void Dump(const std::string& dir,const char* name,const char* dtype,
  const T* device,size_t count,std::vector<Copy>& copies){
  Copy q={name,dtype,std::string(name)+".csv","",count,sizeof(T),-1,false,false,false};
  try{
    if(!device)throw std::runtime_error("actual device pointer is null; no invented values");
    if(count>(std::numeric_limits<size_t>::max)()/sizeof(T))throw std::runtime_error("copy byte extent overflow");
    std::vector<T> data(count);q.allocated=true;
    const cudaError_t error=cudaMemcpy(data.data(),device,count*sizeof(T),cudaMemcpyDeviceToHost);
    q.cuda_status=int(error);q.copied=(error==cudaSuccess);
    if(error!=cudaSuccess)throw std::runtime_error(cudaGetErrorString(error));
    const std::string path=dir+"/"+q.file;
    if(fun::FileExists(path)||fun::DirExists(path))throw std::runtime_error("existing capture leaf is protected");
    std::ofstream out(path);out.imbue(std::locale::classic());if(!out)throw std::runtime_error("CSV open failed");
    Columns(out,static_cast<T*>(NULL));
    for(size_t i=0;i<count;i++){out<<i;Row(out,data[i]);out<<'\n';}
    out.flush();if(!out)throw std::runtime_error("CSV write/flush failed");q.written=true;
  }catch(const std::exception& error){q.error=error.what();}
   catch(...){q.error="unknown capture array error";}
  copies.push_back(q);
}
template<class T> inline void FloatMeta(std::ostream& out,const char* name,T value,bool& comma){
  if(comma)out<<',';comma=true;out<<'{';bool c=false;
  std::ostringstream decimal;decimal.imbue(std::locale::classic());decimal<<std::setprecision(17)<<double(value);
  Text(out,c,"name",name);Number(out,c,"bytes",sizeof(T));Text(out,c,"value17",decimal.str());Text(out,c,"hex_bits",Bits(value));out<<'}';
}
inline void Schema(const std::string& dir,const Meta& m,const std::vector<Copy>& copies,
  size_t nct,bool table_valid,const std::string& capture_error){
  const std::string path=dir+"/schema.json";
  if(fun::FileExists(path)||fun::DirExists(path))throw std::runtime_error("existing schema protected");
  std::ofstream out(path);out.imbue(std::locale::classic());if(!out)throw std::runtime_error("schema open failed");
  bool complete=capture_error.empty()&&table_valid&&copies.size()==11;
  for(const auto& q:copies)complete=complete&&q.copied&&q.written;
  out<<'{';bool c=false;
  Number(out,c,"schema",1);Text(out,c,"policy","HostExceptionOnlyWallInputs");Text(out,c,"directory",dir);
  Bool(out,c,"capture_complete",complete);Text(out,c,"capture_error",capture_error);
  Text(out,c,"scope","actual_replay_aborted_substage_inputs");Bool(out,c,"committed_native",false);
  Bool(out,c,"original_old_unsaved_fault_recovered",false);Bool(out,c,"actual_failed_M_or_fitted_C_registers_captured",false);
  Bool(out,c,"CorrMat_is_input_array_not_rejected_fitted_wall_value",true);Bool(out,c,"invalid_slot_CorrMat_may_be_unwritten_or_stale",true);
  Bool(out,c,"independent_M_C_reevaluation_required",true);
  Bool(out,c,"native_IDs_from_actual_Idp",true);Text(out,c,"array_order","actual_sorted_slot");
  Text(out,c,"floating_primary_identity","memcpy_uint32_or_uint64_hex_bits");Number(out,c,"decimal_digits",17);
  Bool(out,c,"PosCell_w_hex_required",true);Bool(out,c,"host_constants_mapping_not_direct_GPU_CTE_snapshot",true);
  Bool(out,c,"physical_acceptance",false);Number(out,c,"np",m.np);Number(out,c,"npb",m.npb);Number(out,c,"npbok",m.npbok);
  Number(out,c,"stage",m.stage);Number(out,c,"invalid_sorted_slot",m.invalid);Number(out,c,"Nstep_actual_uint64",m.nstep);
  Number(out,c,"Nstep_reported_uint32",unsigned(m.nstep));Bool(out,c,"SigmaPre_present",m.sigma_pre);
  Bool(out,c,"PorePressPre_present",m.pore_pre);Bool(out,c,"PoroJPre_present",m.j_pre);
  Bool(out,c,"field_set_complete_for_stage1_input_review_only",m.stage==1);
  Number(out,c,"kernel",m.kernel);Number(out,c,"host_upload_axis",m.axis);Number(out,c,"host_cellcode",m.cellcode);
  Number(out,c,"simulate2d",m.simulate2d);Number(out,c,"periactive",m.periactive);Number(out,c,"slipmode",m.slipmode);
  Key(out,c,"sizeof");out<<'{';bool s=false;
  Number(out,s,"unsigned",sizeof(unsigned));Number(out,s,"typecode",sizeof(typecode));Number(out,s,"double",sizeof(double));
  Number(out,s,"float",sizeof(float));Number(out,s,"double2",sizeof(double2));Number(out,s,"float4",sizeof(float4));
  Number(out,s,"float3",sizeof(float3));Number(out,s,"byte",sizeof(byte));Number(out,s,"int2",sizeof(int2));Number(out,s,"tmatrix3d",sizeof(tmatrix3d));out<<'}';
  const StDivDataGpu& d=m.div;Key(out,c,"DivData");out<<'{';s=false;
  Number(out,s,"axis",unsigned(d.axis));Key(out,s,"ncells");out<<'['<<d.ncells.x<<','<<d.ncells.y<<','<<d.ncells.z<<']';
  Number(out,s,"scelldiv",d.scelldiv);Key(out,s,"nc");out<<'['<<d.nc.x<<','<<d.nc.y<<','<<d.nc.z<<','<<d.nc.w<<']';
  Key(out,s,"cellzero");out<<'['<<d.cellzero.x<<','<<d.cellzero.y<<','<<d.cellzero.z<<']';Number(out,s,"cellfluid",d.cellfluid);
  Number(out,s,"domcellcode",d.domcellcode);Number(out,s,"logical_Nct",nct);Bool(out,s,"fluid_table_copy_validated",table_valid);
  Number(out,s,"table_start_offset",d.cellfluid);Number(out,s,"table_entry_count",nct);Bool(out,s,"special_or_bound_tables_copied",false);out<<'}';
  Key(out,c,"floating_host_parameters");out<<'[';s=false;
  FloatMeta(out,"TimeStep",m.time,s);FloatMeta(out,"DomPosMin.x",m.domx,s);FloatMeta(out,"DomPosMin.y",m.domy,s);FloatMeta(out,"DomPosMin.z",m.domz,s);
  FloatMeta(out,"Dp.class",m.dp,s);FloatMeta(out,"dp.upload_float",float(m.dp),s);FloatMeta(out,"MdbcThreshold",m.threshold,s);
  FloatMeta(out,"MassFluid",m.massf,s);FloatMeta(out,"RhopZero",m.rhopzero,s);FloatMeta(out,"KernelH",m.h,s);FloatMeta(out,"KernelSize2",m.kernelsize2,s);
  FloatMeta(out,"PosCellSize",m.poscellsize,s);FloatMeta(out,"Scell",m.scell,s);FloatMeta(out,"KWend.awen",m.awen,s);FloatMeta(out,"KWend.bwen",m.bwen,s);
  FloatMeta(out,"Gravity.x",m.gravityx,s);FloatMeta(out,"Gravity.y",m.gravityy,s);FloatMeta(out,"Gravity.z",m.gravityz,s);
  FloatMeta(out,"SoilCte.Porosity",m.porosity,s);FloatMeta(out,"SoilCte.PoreWaterRho",m.water_rho,s);FloatMeta(out,"actual_solid0_argument",m.solid0,s);
  FloatMeta(out,"DivData.scell",d.scell,s);FloatMeta(out,"DivData.kernelsize2",d.kernelsize2,s);FloatMeta(out,"DivData.poscellsize",d.poscellsize,s);
  FloatMeta(out,"DivData.domposmin.x",d.domposmin.x,s);FloatMeta(out,"DivData.domposmin.y",d.domposmin.y,s);FloatMeta(out,"DivData.domposmin.z",d.domposmin.z,s);out<<']';
  Key(out,c,"copies");out<<'[';
  for(size_t i=0;i<copies.size();i++){
    if(i)out<<',';out<<'{';bool e=false;const auto& q=copies[i];
    Text(out,e,"array",q.name);Text(out,e,"dtype",q.dtype);Number(out,e,"count",q.count);Number(out,e,"element_bytes",q.element_bytes);
    Bool(out,e,"allocated",q.allocated);Number(out,e,"cudaMemcpy_status",q.cuda_status);Bool(out,e,"copied",q.copied);
    Bool(out,e,"written",q.written);Text(out,e,"file",q.file);Text(out,e,"error",q.error);out<<'}';
  }
  out<<"]}\n";out.flush();if(!out)throw std::runtime_error("schema write/flush failed");
}
inline void TryCapture(const std::string& parent,const Meta& m,const Arrays& a) noexcept{
  try{
    std::string dir=parent;if(!dir.empty()&&dir.back()!='/'&&dir.back()!='\\')dir+='/';dir+="WallFaultCaptureHostR1";
    // Existing API returns0 only for a genuinely new directory. Preserve EEXIST.
    errno=0;if(fun::Mkdir(dir)!=0){
      const int error=errno;std::fprintf(stderr,"C08_WALL_HOST_CAPTURE mkdir failed errno=%d; directory preserved: %s\n",error,dir.c_str());return;
    }
    std::vector<Copy> copies;copies.reserve(11);std::string error;size_t nct=0;bool table_valid=false;
    try{
      if(!m.np||m.npb>m.np||m.npbok>m.npb||m.invalid>=m.npbok)throw std::runtime_error("actual sorted particle extents inconsistent");
      const StDivDataGpu& d=m.div;
      if(d.axis!=MGDIV_Z||d.nc.x<=0||d.nc.y<=0||d.nc.z<=0||d.nc.w<=0||(d.scelldiv!=1&&d.scelldiv!=2))throw std::runtime_error("actual singleGPU cell dimensions/axis invalid");
      const std::uint64_t sheet=std::uint64_t(d.nc.x)*std::uint64_t(d.nc.y);
      if(sheet!=std::uint64_t(d.nc.w))throw std::runtime_error("actual cell sheet stride invalid");
      if(sheet>(std::numeric_limits<std::uint64_t>::max)()/std::uint64_t(d.nc.z))throw std::runtime_error("logical cell product overflow");
      const std::uint64_t logical=sheet*std::uint64_t(d.nc.z);
      if(logical>(std::numeric_limits<unsigned>::max)()-1u||logical>(std::numeric_limits<size_t>::max)()/sizeof(int2)
        ||logical+1!=d.cellfluid||!d.beginendcell)throw std::runtime_error("logical fluid table range invalid; allocation size not guessed");
      nct=size_t(logical);table_valid=true;
      Dump(dir,"Idp","uint32",a.id,m.np,copies);Dump(dir,"Code",sizeof(typecode)==2?"uint16":"uint32",a.code,m.np,copies);
      Dump(dir,"Posxy","float64x2",a.xy,m.np,copies);Dump(dir,"Posz","float64",a.z,m.np,copies);
      Dump(dir,"PosCell","float32x4_raw_w_cell_bits",a.poscell,m.np,copies);Dump(dir,"Dcell","uint32",a.dcell,m.np,copies);
      Dump(dir,"PoroJ","float64",a.j,m.np,copies);Dump(dir,"CorrMat","float64x9_actual_input",a.corr,m.np,copies);
      Dump(dir,"BoundNormal","float32x3",a.normal,m.npbok,copies);Dump(dir,"BoundMode","uint8",a.mode,m.npbok,copies);
      Dump(dir,"FluidCells","int32x2",d.beginendcell+d.cellfluid,nct,copies);
    }catch(const std::exception& e){error=e.what();}catch(...){error="unknown host capture extent/allocation error";}
    try{Schema(dir,m,copies,nct,table_valid,error);}
    catch(const std::exception& e){std::fprintf(stderr,"C08_WALL_HOST_CAPTURE schema incomplete: %s\n",e.what());}
    catch(...){std::fprintf(stderr,"C08_WALL_HOST_CAPTURE schema incomplete: unknown error\n");}
    std::fprintf(stderr,"C08_WALL_HOST_CAPTURE after actual GPU rejection only; copies=%llu dir=%s; original exception follows\n",static_cast<unsigned long long>(copies.size()),dir.c_str());
  }catch(const std::exception& e){std::fprintf(stderr,"C08_WALL_HOST_CAPTURE best-effort failure: %s; original exception follows\n",e.what());}
   catch(...){std::fprintf(stderr,"C08_WALL_HOST_CAPTURE unknown best-effort failure; original exception follows\n");}
}
} // namespace c08wallhost
#endif

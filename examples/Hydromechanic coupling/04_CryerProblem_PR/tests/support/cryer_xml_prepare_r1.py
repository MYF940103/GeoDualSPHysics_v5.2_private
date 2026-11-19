"""Prepare isolated CPU and GPU Cryer XML candidates from the real shared-row implementations."""
import argparse
from pathlib import Path
import shutil

T = Path(__file__).resolve().parents[1]
OUT = T/"outputs"


def replace(text, old, new):
    if text.count(old)!=1:
        raise ValueError("Expected one exact source section: "+old[:90])
    return text.replace(old,new,1)


def edit(path, transform):
    raw=path.read_bytes()
    newline=b"\r\n" if b"\r\n" in raw else b"\n"
    text=raw.replace(b"\r\n",b"\n").decode("latin1")
    path.write_bytes(transform(text).encode("latin1").replace(b"\n",newline))


def section(text,start,stop,body):
    a=text.index(start);b=text.index(stop,a)
    return replace(text,text[a:b],body)


READ = '''
  // Read the private candidate's pressure scheme from the same XML as the material.
  // The old test harness selectors must never silently activate or suppress physics.
  const char* integratorName="HydroMechPressureIntegrator";
  for(const char* key:{"UPL_TPI_CPU_R1","UPL_TPI_GPU_R1","UPL_TPI_P3_ROWS_R1","UPL_TPI_M0_DT_R1"}){
    const char* value=std::getenv(key);
    if(value && *value)Run_Exceptioon("HydroMechPressureIntegrator must be selected in XML; clear the old private environment switches.");
  }
  tpi_pressure_config::selected=tpi_pressure_config::Integrator::ExplicitKw;
  if(const TiXmlNode* soil=xml.GetNodeSimple("case.execution.special.soils",true)){
    if(soil->FirstChildElement(integratorName))Run_Exceptioon("Place HydroMechPressureIntegrator inside special/hydromechanics.");
  }
  if(const TiXmlNode* hydro=xml.GetNodeSimple("case.execution.special.hydromechanics",true)){
    if(const TiXmlElement* option=hydro->FirstChildElement(integratorName)){
      if(option->NextSiblingElement(integratorName))Run_Exceptioon("Duplicate HydroMechPressureIntegrator element.");
      const std::string choice=xml.GetAttributeStr(option,"value");
      if(choice!="0" && choice!="1")Run_Exceptioon("HydroMechPressureIntegrator requires 0 (explicit Kw) or 1 (TPI).");
      if(choice=="1"){
        if(!HydroMech || !xml.ReadElementBool(hydro,"HydroMechDynamicSeepage","value",true,false))
          Run_Exceptioon("HydroMechPressureIntegrator=1 requires HydroMech=1 and HydroMechDynamicSeepage=1.");
        if(PartBegin)Run_Exceptioon("HydroMechPressureIntegrator=1 requires a fresh start; pressure-history restart is not qualified.");
        tpi_pressure_config::selected=tpi_pressure_config::Integrator::Tpi;
      }
    }
  }
  Log->Printf("HydroMechPressureIntegrator=%u (%s)",unsigned(tpi_pressure_config::selected),
    tpi_pressure_config::UsesTpi()? "TPI M0 alpha=.5, beta=0, three pressure corrections, R_h=1":"original explicit pressure path");
'''


def configure(text):
    text=replace(text,'#include "JXml.h"','#include "JXml.h"\n#include "TpiPressureSelection.h"\n#include <cstdlib>\n'
      'tpi_pressure_config::Integrator tpi_pressure_config::selected=tpi_pressure_config::Integrator::ExplicitKw;')
    return replace(text,'  //-Execution parameters from XML.\n  LoadConfigParameters(&xml);',
                        READ+'\n  //-Execution parameters from XML.\n  LoadConfigParameters(&xml);')


def prepare(backend):
    old=OUT/("cryer_row_"+backend+"_r1_source")
    new=OUT/("cryer_xml_"+backend+"_r1_source")
    files=old/"source" if backend=="cpu" else old
    dst=new/"source" if backend=="cpu" else new
    if new.exists(): raise FileExistsError(new)
    dst.mkdir(parents=True)
    for item in files.iterdir():
        if item.is_file() and item.suffix.lower() in (".h",".cpp",".cu",".cuh",".inc"):
            shutil.copy2(item,dst/item.name)
    shutil.copy2(T/"support/TpiPressureSelection.h",dst)
    edit(dst/"JSph.cpp",configure)
    edit(dst/"upl_tpi_m0_dt_r2.h",lambda text: section(replace(text,'#include <algorithm>','#include "TpiPressureSelection.h"\n#include <algorithm>'),
        "inline bool Enabled(bool pressureBC){","inline bool AllowedDt",
        "inline bool Enabled(bool pressureBC){ return pressureBC && tpi_pressure_config::UsesTpi(); }\n"))
    if backend=="cpu":
        edit(dst/"upl_tpi_cpu_r1.h",lambda text: section(replace(text,'#include "TpiPressureRow.h"',
             '#include "TpiPressureRow.h"\n#include "TpiPressureSelection.h"'),"inline Scheme RequestedScheme(){","inline const char* Name()",
             "inline Scheme RequestedScheme(){return tpi_pressure_config::UsesTpi()? B_Tpi: A_FiniteKw;}\n"
             "inline bool Enabled(){return tpi_pressure_config::UsesTpi();}\n"))
    else:
        # Only the host implementation of this dual header is edited. The CUDA-visible
        # declarations, DeviceState, kernels and the compiled device object are unchanged.
        edit(dst/"upl_tpi_cryer_gpu_r1.h",lambda text: section(replace(text,"#include <fstream>",
             '#include "TpiPressureSelection.h"\n#include <fstream>'),"static unsigned Scheme(){","bool Enabled(){",
             "static unsigned Scheme(){return tpi_pressure_config::UsesTpi()?1u:0u;}\n"))
    name="JSphCpuSingle.cpp" if backend=="cpu" else "JSphGpuSingle.cpp"
    edit(dst/name,lambda text: replace(text,'std::getenv("UPL_TPI_'+backend.upper()+'_R1")',
                                      '(tpi_pressure_config::UsesTpi()?"B":"A")'))
    print("Prepared",dst)


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("backend",choices=("cpu","gpu"))
    prepare(ap.parse_args().backend)

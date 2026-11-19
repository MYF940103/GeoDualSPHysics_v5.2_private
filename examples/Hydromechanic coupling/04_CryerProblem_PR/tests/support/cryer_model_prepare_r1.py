"""Generate the single-selector Cryer candidate from the previously tested XML runtime."""
import argparse
from pathlib import Path
import shutil

from cryer_xml_prepare_r1 import OUT, READ, edit, replace


MODEL = '''  // Resolve the framework once, before conductivity, pressure and geometry validation.
  // Keep the existing dynamic flag for the kernels, PRE contracts and native metadata.
  const char* modelName="HydroMechModel";
  const char* dynamicName="HydroMechDynamicSeepage";
  const char* integratorName="HydroMechPressureIntegrator";
  for(const char* key:{"UPL_TPI_CPU_R1","UPL_TPI_GPU_R1","UPL_TPI_P3_ROWS_R1","UPL_TPI_M0_DT_R1"}){
    const char* value=std::getenv(key);
    if(value && *value)Run_Exceptioon("Select HydroMechModel in XML; clear the old private environment switches.");
  }
  if(solidEle->FirstChildElement(modelName) || solidEle->FirstChildElement(integratorName))
    Run_Exceptioon("Place HydroMechModel and the old HydroMechPressureIntegrator inside special/hydromechanics.");
  const TiXmlElement* modelOption=hydroEle->FirstChildElement(modelName);
  const TiXmlElement* dynamicOption=hydroEle->FirstChildElement(dynamicName);
  const TiXmlElement* integratorOption=hydroEle->FirstChildElement(integratorName);
  unsigned model=0;
  if(modelOption){
    if(modelOption->NextSiblingElement(modelName))Run_Exceptioon("Duplicate HydroMechModel element.");
    if(dynamicOption || integratorOption || solidEle->FirstChildElement(dynamicName))
      Run_Exceptioon("HydroMechModel cannot be combined with HydroMechDynamicSeepage or HydroMechPressureIntegrator.");
    const std::string value=sxml->GetAttributeStr(modelOption,"value");
    if(value!="0" && value!="1" && value!="2")Run_Exceptioon("HydroMechModel requires 0, 1 or 2.");
    model=unsigned(value[0]-'0');
  }
  else{
    if(dynamicOption && dynamicOption->NextSiblingElement(dynamicName))Run_Exceptioon("Duplicate HydroMechDynamicSeepage element.");
    // Preserve the boolean syntax and soils fallback used by existing input files.
    if(sxml->ReadElementBool(hydroReadNode,dynamicName,"value",true,false))model=1;
    if(integratorOption){
      if(integratorOption->NextSiblingElement(integratorName))Run_Exceptioon("Duplicate HydroMechPressureIntegrator element.");
      const std::string value=sxml->GetAttributeStr(integratorOption,"value");
      if(value!="0" && value!="1")Run_Exceptioon("HydroMechPressureIntegrator requires 0 (explicit Kw) or 1 (TPI).");
      if(value=="1"){
        if(model!=1)Run_Exceptioon("HydroMechPressureIntegrator=1 requires HydroMechDynamicSeepage=1.");
        model=2;
      }
    }
  }
  if(model && !HydroMech)Run_Exceptioon("Dynamic HydroMechModel requires HydroMech=1.");
  if(model==2 && PartBegin)Run_Exceptioon("HydroMechModel=2 requires a fresh start; pressure-history restart is not qualified.");
  HydroMechDynamicSeepage=(model!=0);
  tpi_pressure_config::selected=(model==2? tpi_pressure_config::Integrator::Tpi: tpi_pressure_config::Integrator::ExplicitKw);
  const char* modelNames[]={"u-pw","explicit u-pl","TPI u-pl M0 alpha=.5, beta=0, three pressure corrections, R_h=1"};
  Log->Printf("HydroMechModel=%u (%s)",model,modelNames[model]);'''


def configure(source):
    text = replace(source, READ, "")
    old = '  HydroMechDynamicSeepage=sxml->ReadElementBool(hydroReadNode,"HydroMechDynamicSeepage","value",true,false);'
    return replace(text, old, MODEL)


def prepare(backend):
    original = OUT / ("cryer_xml_" + backend + "_r1_source")
    target = OUT / ("cryer_model_" + backend + "_r1_source")
    units = Path("source") if backend == "cpu" else Path()
    # Prove the patch context before writing the fresh tree.
    host = units / "JSph.cpp"
    configure((original / host).read_text(encoding="latin1"))
    shutil.copytree(original, target)
    edit(target / host, configure)
    print(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", choices=("cpu", "gpu"))
    prepare(parser.parse_args().backend)

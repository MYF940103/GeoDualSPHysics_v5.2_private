// Private, single-case CLI selection. Configuration is read once before any force loop.
#pragma once

namespace tpi_pressure_config {
enum class Integrator { ExplicitKw, Tpi };

// Owned by the executable's JSph.cpp. Host workers only read the configured selection.
extern Integrator selected;
inline bool UsesTpi(){ return selected==Integrator::Tpi; }
}

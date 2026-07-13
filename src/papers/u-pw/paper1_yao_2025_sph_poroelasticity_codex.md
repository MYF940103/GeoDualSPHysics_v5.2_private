# 2-D SPH modelling of poroelasticity: u-w-p and u-p formulations with absorbing boundary conditions and volumetric locking treatments

**Source:** C. Yao, G. Fourtakas, B.D. Rogers, D. Lombardi. Computers and Geotechnics 179 (2025) 107016.

**Conversion purpose:** Codex-friendly Markdown. The body text is extracted in reading order using the PDF text layer; formulas are preserved as Unicode mathematical text rather than raster-only images; figure/table captions are indexed and linked to visual crops in the accompanying assets folder.

## Figure and table index

### Figures

- **Fig. 1** (page 2): Fig. 1. Cross-section of a representative elementary volume (REV) of a saturated porous medium.

  ![Fig. 1 crop](paper1_assets/figures/fig_01_page_02.png)

- **Fig. 2** (page 6): Fig. 2. Illustration of boundary particles.

  ![Fig. 2 crop](paper1_assets/figures/fig_02_page_06.png)

- **Fig. 3** (page 7): Fig. 3. Zones of applicability of various assumptions for the Biot’s model (Monforte et al., 2019) and locations of main tests presented in this paper.

  ![Fig. 3 crop](paper1_assets/figures/fig_03_page_07.png)

- **Fig. 4** (page 8): Fig. 4. 1-D consolidation problem and numerical set-up.

  ![Fig. 4 crop](paper1_assets/figures/fig_04_page_08.png)

- **Fig. 5** (page 9): Fig. 5. EPWP (in Pa) distribution at representative times in the 1-D consolidation test using the 𝒖-𝒘-𝑝model.

  ![Fig. 5 crop](paper1_assets/figures/fig_05_page_09.png)

- **Fig. 6** (page 9): Fig. 6. Isochrone of EPWP in the 1-D consolidation test.

  ![Fig. 6 crop](paper1_assets/figures/fig_06_page_09.png)

- **Fig. 7** (page 10): Fig. 7. Time history of (a) EPWP at three points and (b) surface settlement in the 1-D consolidation test.

  ![Fig. 7 crop](paper1_assets/figures/fig_07_page_10.png)

- **Fig. 8** (page 11): Fig. 8. Convergence rate of the 𝐿2(𝑝𝑤) error norm of the EPWP profile at 𝑇𝑣= 0.31 in the 1-D consolidation test.

  ![Fig. 8 crop](paper1_assets/figures/fig_08_page_11.png)

- **Fig. 9** (page 11): Fig. 9. Mandel’s problem and the numerical domain.

  ![Fig. 9 crop](paper1_assets/figures/fig_09_page_11.png)

- **Fig. 10** (page 12): Fig. 10. EPWP (in Pa) distribution at representative times in the Mandel’s problem using the 𝒖-𝒘-𝑝model.

  ![Fig. 10 crop](paper1_assets/figures/fig_10_page_12.png)

- **Fig. 11** (page 12): Fig. 11. Profiles of EPWP along the 𝑥-axis in the Mandel’s problem.

  ![Fig. 11 crop](paper1_assets/figures/fig_11_page_12.png)

- **Fig. 12** (page 13): Fig. 12. Time history of (a) EPWP and (b) 𝐸 𝑟𝑟(𝑝𝑤) at two points in the Mandel’s problem.

  ![Fig. 12 crop](paper1_assets/figures/fig_12_page_13.png)

- **Fig. 13** (page 14): Fig. 13. Effect of Poisson’s ratio on the time history of EPWP at 𝑥∕𝑎= 0 in the Mandel’s problem.

  ![Fig. 13 crop](paper1_assets/figures/fig_13_page_14.png)

- **Fig. 14** (page 14): Fig. 14. Steady state distribution of EPWP (in Pa) in the 1-D harmonic loading test with 𝑇= 2 s using the 𝒖-𝒘-𝑝model.

  ![Fig. 14 crop](paper1_assets/figures/fig_14_page_14.png)

- **Fig. 15** (page 15): Fig. 15. Envelope of EPWP at the steady state under different loadings.

  ![Fig. 15 crop](paper1_assets/figures/fig_15_page_15.png)

- **Fig. 16** (page 16): Fig. 16. Time history of EPWP of a point at 𝑧∕𝐻= 0.1 with respect to two different loading based on the 𝒖-𝒘-𝑝model.

  ![Fig. 16 crop](paper1_assets/figures/fig_16_page_16.png)

- **Fig. 17** (page 17): Fig. 17. Effect of resolution on the steady-state EPWP envelope predicted by the 𝒖-𝒘-𝑝model under 𝑇= 0.2 s.

  ![Fig. 17 crop](paper1_assets/figures/fig_17_page_17.png)

- **Fig. 18** (page 17): Fig. 18. Convergence rate of the 𝐿2(𝑝𝑤) error norm of the EPWP envelope at the steady state in the 1-D harmonic loading test with 𝑇= 1 s.

  ![Fig. 18 crop](paper1_assets/figures/fig_18_page_17.png)

- **Fig. 19** (page 18): Fig. 19. Time history of surface settlement under 𝑇= 2 s.

  ![Fig. 19 crop](paper1_assets/figures/fig_19_page_18.png)

- **Fig. 20** (page 18): Fig. 20. EPWP (in Pa) distribution at representative times in the 1-D transient wave propagation test using the 𝒖-𝒘-𝑝model.

  ![Fig. 20 crop](paper1_assets/figures/fig_20_page_18.png)

- **Fig. 21** (page 19): Fig. 21. EPWP (in Pa) distribution at representative times in the 1-D transient wave propagation test using the 𝒖-𝑝model.

  ![Fig. 21 crop](paper1_assets/figures/fig_21_page_19.png)

- **Fig. 22** (page 19): Fig. 22. Profile of EPWP at representative times in the 1-D transient wave propagation test with 𝑘= 0.001 m∕s.

  ![Fig. 22 crop](paper1_assets/figures/fig_22_page_19.png)

- **Fig. 23** (page 20): Fig. 23. Profile of EPWP at representative times in the 1-D transient wave propagation test with 𝑘= 0.0001 m∕s.

  ![Fig. 23 crop](paper1_assets/figures/fig_23_page_20.png)

- **Fig. 24** (page 20): Fig. 24. Time history of EPWP at 𝑧∕𝐻= 0.8 in the 1-D transient wave propagation test.

  ![Fig. 24 crop](paper1_assets/figures/fig_24_page_20.png)

- **Fig. 25** (page 21): Fig. 25. Time history of (a) EPWP at 𝑧∕𝐻= 0.8 and (b) 𝑧-displacement of the bottom boundary in the 1-D transient wave propagation test with respect to distinct values of the virtual viscous layer thickness.

  ![Fig. 25 crop](paper1_assets/figures/fig_25_page_21.png)

- **Fig. 26** (page 22): Fig. 26. 2-D consolidation problem and numerical set-up.

  ![Fig. 26 crop](paper1_assets/figures/fig_26_page_22.png)

- **Fig. 27** (page 22): Fig. 27. Contour of EPWP (in kPa) in the 2-D consolidation test using both the 𝒖-𝒘-𝑝and 𝒖-𝑝models with 𝑘= 0.001 m∕s.

  ![Fig. 27 crop](paper1_assets/figures/fig_27_page_22.png)

- **Fig. 28** (page 23): Fig. 28. Effect of particle distribution on EPWP at 𝑡= 15 s in the 2-D consolidation test using the 𝒖-𝒘-𝑝model.

  ![Fig. 28 crop](paper1_assets/figures/fig_28_page_23.png)

- **Fig. 29** (page 23): Fig. 29. Time history of EPWP at (a) point A and (b) point B in the 2-D consolidation test.

  ![Fig. 29 crop](paper1_assets/figures/fig_29_page_23.png)

- **Fig. 30** (page 24): Fig. 30. 2-D transient wave propagation problem and the applied impulse force.

  ![Fig. 30 crop](paper1_assets/figures/fig_30_page_24.png)

- **Fig. 31** (page 25): Fig. 31. Contour of EPWP (in kPa) in the 2-D consolidation test using both the 𝒖-𝒘-𝑝and 𝒖-𝑝models with 𝑘= 0.0001 m∕s.

  ![Fig. 31 crop](paper1_assets/figures/fig_31_page_25.png)

- **Fig. 32** (page 26): Fig. 32. Time history of EPWP at point B with (a) 𝑘= 0.0001 m∕s, (b) 𝑘= 0.001 m∕s and (c) 𝑘= 0.01 m∕s in the 2-D wave propagation test.

  ![Fig. 32 crop](paper1_assets/figures/fig_32_page_26.png)

- **Fig. 33** (page 26): Fig. 33. Distribution of EPWP (in kPa) at representative times in the 2-D wave propagation test using the 𝒖-𝒘-𝑝model.

  ![Fig. 33 crop](paper1_assets/figures/fig_33_page_26.png)

- **Fig. 34** (page 27): Fig. 34. Distribution of total displacement (in mm) at representative times in the 2-D wave propagation test using the 𝒖-𝒘-𝑝model.

  ![Fig. 34 crop](paper1_assets/figures/fig_34_page_27.png)

- **Fig. 35** (page 27): Fig. 35. Particle disorder close to the traction boundary 𝛤1 at 𝑡= 0.1 s. Particles are coloured according to EPWP (in kPa) and deformation is scaled by a factor of 500 in both directions.

  ![Fig. 35 crop](paper1_assets/figures/fig_35_page_27.png)

- **Fig. 36** (page 28): Fig. 36. Influence of resolution on the time history of EPWP at point B (left) and the in-plane motion of point A (right) using (a) the 𝒖-𝒘-𝑝model and (b) the 𝒖-𝑝model.

  ![Fig. 36 crop](paper1_assets/figures/fig_36_page_28.png)

- **Fig. 37** (page 29): Fig. 37. Influence of artificial viscosity on the time history of EPWP at point B (left) and the in-plane motion of point A (right) using (a) the 𝒖-𝒘-𝑝model and (b) the 𝒖-𝑝model.

  ![Fig. 37 crop](paper1_assets/figures/fig_37_page_29.png)


### Tables

- **Table 1** (page 5): Table 1 Properties of the poroelastic medium in the 1-D consolidation test.

  ![Table 1 crop](paper1_assets/tables/table_01_page_05.png)

- **Table 2** (page 17): Table 2 Properties of the poroelastic medium in the 1-D transient wave propagation test.

  ![Table 2 crop](paper1_assets/tables/table_02_page_17.png)

- **Table 3** (page 25): Table 3 Properties of the poroelastic medium in the 2-D transient wave propagation test.

  ![Table 3 crop](paper1_assets/tables/table_03_page_25.png)


## Extracted tables in Markdown

### Table 1. Properties of the poroelastic medium in the 1-D consolidation test

| Parameter | Symbol | Value | Unit |
|---|---:|---:|---|
| Porosity | 𝑛 | 0.3 | - |
| Density of pore water | 𝜌𝑓 | 1000 | kg/m^3 |
| Density of solid phase | 𝜌𝑠 | 2000 | kg/m^3 |
| Young's modulus of solid skeleton | 𝐸 | 30 | MPa |
| Poisson's ratio of solid skeleton | 𝜈 | 0.2 | - |
| Hydraulic conductivity | 𝑘 | 0.001 | m/s |
| Bulk modulus of pore water | 𝐾𝑓 | 100 | MPa |

### Table 2. Properties of the poroelastic medium in the 1-D transient wave propagation test

| Parameter | Symbol | Value | Unit |
|---|---:|---:|---|
| Porosity | 𝑛 | 0.4 | - |
| Density of pore water | 𝜌𝑓 | 1000 | kg/m^3 |
| Density of solid phase | 𝜌𝑠 | 2650 | kg/m^3 |
| Young's modulus of solid skeleton | 𝐸 | 5 | GPa |
| Poisson's ratio of solid skeleton | 𝜈 | 0 | - |
| Hydraulic conductivity | 𝑘 | 0.001 and 0.0001 | m/s |
| Bulk modulus of pore water | 𝐾𝑓 | 2 | GPa |

### Table 3. Properties of the poroelastic medium in the 2-D transient wave propagation test

| Parameter | Symbol | Value | Unit |
|---|---:|---:|---|
| Porosity | 𝑛 | 0.33 | - |
| Density of pore water | 𝜌𝑓 | 1000 | kg/m^3 |
| Density of solid phase | 𝜌𝑠 | 2000 | kg/m^3 |
| Young's modulus of solid skeleton | 𝐸 | 14.5 | MPa |
| Poisson's ratio of solid skeleton | 𝜈 | 0.3 | - |
| Hydraulic conductivity | 𝑘 | 0.01 | m/s |
| Bulk modulus of pore water | 𝐾𝑓 | 2.2 | GPa |


---

# Full cleaned text

## Page 1

Contents lists available at ScienceDirect
Computers and Geotechnics
journal homepage: www.elsevier.com/locate/compgeo
Research paper
2-D SPH modelling of poroelasticity: 𝒖-𝒘-𝑝 and 𝒖-𝑝 formulations with
absorbing boundary conditions and volumetric locking treatments
C. Yao a,b,∗
, G. Fourtakas a
, B.D. Rogers a
, D. Lombardi a
a
School of Engineering, The University of Manchester, Manchester M13 9PL, UK
b
Hartree Centre, STFC Daresbury Laboratory, Keckwick Lane, Warrington, WA4 4AD, UK
A R T I C L E I N F O
Keywords:
Biot’s theory
SPH
Poroelasticity
Absorbing boundary
Volumetric locking
DualSPHysics
u-w-p and u-p formulations
A B S T R A C T
This paper presents a new simulation approach for modelling strongly-coupled processes in saturated porous
media using the meshless method smoothed particle hydrodynamics (SPH). This paper proposes new SPH
formulations for the 𝒖-𝒘-𝑝 and 𝒖-𝑝 versions of Biot’s model that address key challenges including accurate
boundary conditions and numerical stability. Using corrected SPH gradient and Laplacian operators both
absorbing and explicit treatment of free-surface conditions are achieved. The improved standard viscous
boundary is then introduced into SPH as an absorbing boundary for problems involving dynamic loading. The
volumetric locking issue is observed and a new countermeasure, named volumetric strain diffusion, is proposed,
based on the well-established B-bar method and density diffusion technique. The proposed formulations are
then systematically examined with six classical poroelastic problems spanning quasi-static and dynamic ranges.
The simulated results agree with the reference solutions and display the desired order of convergence. The 𝒖-𝒘-𝑝 and 𝒖-𝑝 models perform similarly under slow to moderate loading, but show distinct behaviour under highly
dynamic loading. This observation matches existing understanding, thereby demonstrating the correctness of
the proposed formulations. The introduced absorbing boundary condition and volumetric locking treatment
also show promising results.
1. Introduction
The mechanical behaviour of saturated porous media is largely
dominated by the interaction between the solid skeleton and the pore
fluid(s) such as water. The first mathematical theory governing such
coupled processes was established by Biot (1941, 1956a,b), which is
usually termed as poroelasticity (Cheng, 2016) because of its linear
elasticity assumption of the solid skeleton. It was further expanded
to encompass scenarios involving large deformations and nonlinear
material behaviours (e.g. Zienkiewicz et al., 1999). Typical examples of application of the Biot’s theory include land subsidence in
geomechanics, soil liquefaction in earthquake engineering, fluid injection/extraction in geophysics (Torberntsson et al., 2018), wave-seabed
interaction in ocean engineering (Jeng et al., 2013), underground
carbon dioxide storage in geoenvironmental engineering (Song et al.,
2022) and deformation-driven bone fluid flow in biomechanics (Cowin,
1999).
Mathematically, a practical problem can be modelled by solving
the Biot’s model under specific initial and boundary conditions. As the
governing equations have a complex structure, some simplifying assumptions are usually introduced, leading to several simplified versions
∗ Corresponding author at: School of Engineering, The University of Manchester, Manchester M13 9PL, UK.
E-mail address: cong.yao@stfc.ac.uk (C. Yao).
of the Biot’s model. Two examples are the 𝒖-𝒘-𝑝 and 𝒖-𝑝 formulations (Zienkiewicz and Shiomi, 1984) where 𝒖 is the solid skeleton
velocity, 𝒘 is the relative velocity of the pore water and 𝑝 is pore
water pressure. The validity of these reduced models was thoroughly
discussed by Zienkiewicz et al. (1980). Nevertheless, an analytical
solution is available only in very special cases, as summarised in Cheng
(2016).
Conventional approaches such as the finite element method (FEM)
and the finite difference method (FDM) dominate current numerical solution of coupled problems of saturated porous media (e.g.
Torberntsson et al., 2018; Li and Wei, 2018; Monforte et al., 2019).
Both FEM and FDM methods use a computational mesh, which introduces challenges when dealing with large deformation due to mesh
distortion issues. However, the capability to model large deformation
processes is required for a wide number of practical coupled problems,
including large post-liquefaction deformation of saturated sand.
The development of meshless techniques in the past few decades
provides alternative tools addressing directly the prediction of large
deformation. Two well-known examples are the smoothed particle
hydrodynamics (SPH) (Monaghan, 1992; Liu and Liu, 2003; Violeau,
https://doi.org/10.1016/j.compgeo.2024.107016
Received 1 August 2024; Received in revised form 25 November 2024; Accepted 19 December 2024
Available online 1 January 2025
0266-352X/© 2024 The Authors. Published by Elsevier Ltd. This is an open access article under the CC BY license (http://creativecommons.org/licenses/by/4.0/).

## Page 2

2012; Violeau and Rogers, 2016) and the material point method
(MPM) (Sulsky et al., 1994, 1995; Soga et al., 2016). In SPH, a
continuum is discretised into a set of particles and interpolation is
achieved through the so-called kernel approximation using a summation of weighted contributions from neighbouring particles. In the
absence of a mesh, SPH is well-suited for modelling large deformation
problems, evident by its successful application to failure flow of dry
geomaterials (e.g. Bui et al., 2008; Peng et al., 2015; He et al., 2018;
Chalk et al., 2020; Bui and Nguyen, 2021).
SPH modelling of coupled problems in porous materials has recently
attracted significant attention. Example applications include seepagedriven failure of geostructures (e.g. Bui and Nguyen, 2017; Gholami Korzani et al., 2018; Zhang et al., 2019) and gravity-driven landslides (e.g.
Pastor et al., 2009, 2018; Liang et al., 2019). A common feature of
these studies is the employment of classical SPH formulations, which
inherently satisfy free-surface conditions (see Section 3.1). However,
these formulations face a significant challenge: the accurate application
of various boundary conditions, which is crucial for modelling many
strongly-coupled problems. Although some boundary conditions are
available, extending them to Biot’s model is not straightforward. More
importantly, the simulation results may be non-convergent.
Poroelastic problems are well-suited validation tests for a stronglycoupled SPH solver, as the assumed linear elastic material response
greatly simplifies the underlying physics. Once a solver performs satisfactorily on these tests, more sophisticated material models can be
introduced to capture nonlinear behaviours and large deformation
phenomena. The simplest poroelastic tests involve 1-D problems, including 1-D consolidation, 1-D harmonic loading, and 1-D transient
wave propagation, which span from quasi-static to dynamic ranges.
For the 1-D consolidation test, Blanc and Pastor (2012) presented their
simulation results without comparing with the reference data and the
results of Osorno and Steeb (2016) show discrepancies from the analytical solution. Moreover, as discussed in Section 5.1.1, the Terzaghi
consolidation problem is based on an uncoupled theory and hence
it differs from the poroelastic one. If an SPH model reproduces the
Terzaghi consolidation problem, it indicates that some coupling effects
are missing in the relevant governing equations. A strongly-coupled
solver should instead reproduce the poroelastic consolidation problem.
The 1-D harmonic loading test has only been performed by Blanc and
Pastor (2012) where the results show discrepancies from the analytical
solutions. Despite the recent advancements in SPH, the 1-D transient
wave propagation test has not yet been reproduced by any SPH model.
In higher dimensions, a strongly-coupled solver may encounter the
so-called volumetric locking issue, due to the near-incompressibility
of saturated porous media. In FEM studies, volumetric locking is
attributed to the inability of the element to exactly represent an
isochoric motion (Belytschko et al., 2013). Accordingly, the B-bar
method (Hughes, 1980) is widely employed as a countermeasure, with
the F-bar method (de Souza Neto et al., 1996) being its counterpart in
the finite deformation scenario. The essential idea of the B-bar method
is to average the volumetric strain over the neighbours of an interpolation point. When it comes to SPH, the incompressible SPH (ISPH)
approach is generally employed to model the incompressible fluid flow
based on a projection method. Blanc and Pastor (2012) and Morikawa
and Asai (2022) have extended ISPH to solve the Biot’s model. Although
the assumption of a strictly divergence-free deformation field brings
convenience for the development of a numerical model, its physical basis remains questionable, especially in the context of complex coupled
processes. The typical 2-D poroelastic tests include Mandel’s problem,
2-D consolidation and 2-D transient wave propagation. In the current
literature, the Mandel’s problem has been studied by Osorno and Steeb
(2016) and the 2-D consolidation is reproduced by Bui and Fukagawa
(2009) and Blanc and Pastor (2012). However, 2-D transient wave
propagation has not yet been reported by any SPH model.
In this paper, new SPH formulations for the 𝒖-𝒘-𝑝 and 𝒖-𝑝 versions
of Biot’s model are proposed. These formulations differ from existing ones as they necessitate the explicit enforcement of free-surface
Fig. 1. Cross-section of a representative elementary volume (REV) of a saturated porous
medium.
conditions, which provides an opportunity to apply various boundary
conditions essential for modelling the poroelastic problems. The ability
to accurately enforce stress boundary conditions makes it possible to introduce some well-established absorbing boundary conditions into SPH,
which are needed for numerical analyses involving dynamic loading.
The standard viscous boundary proposed by Lysmer and Kuhlemeyer
(1969) and improved by Jassim et al. (2013) is herein considered. The
proposed formulations and stabilisation measures are then examined
through six poroelastic tests, spanning quasi-static to dynamic ranges.
The paper is structured as follows. Section 2 presents Biot’s theory and
its simplified versions. Section 3 discusses the SPH operators and their
features. Section 4 gives the proposed SPH formulations for the 𝒖-𝒘-𝑝
and 𝒖-𝑝 versions of Biot’s model, including the necessary stabilisation
measures. Section 5 presents the validation of the developed numerical
solver, followed by the conclusions.
2. Biot’s theory
In Biot’s theory, a porous material saturated with a single fluid
(i.e. water in this paper) is considered at the macroscopic scale and the
cross-section of its representative elementary volume (REV) is shown
in Fig. 1. The density of this binary medium is:
𝜌 = 𝑛𝜌𝑓 + (1 − 𝑛)𝜌𝑠 (1)
where 𝑛 is the porosity, 𝜌𝑓 and 𝜌𝑠 are densities of its fluid and solid
constituents, respectively. By employing a positive sign stress convention in tension and pore pressure in compression, the total stress tensor
𝝈 can be decomposed as:
𝝈 = 𝝈′
− 𝛼𝑝𝑰 (2)
where 𝝈′ is the effective stress tensor quantifying the average stress
transmitted through the solid skeleton, 𝑝 is the pore pressure, 𝑰 is the
identity tensor, and 𝛼 is Biot’s coefficient defined as:
𝛼 = 1 −
𝐾𝑇
𝐾𝑠
(3)
where 𝐾𝑇 and 𝐾𝑠 are bulk moduli of the solid skeleton and the
solid constituent, respectively. Eq. (2) presents the generalised effective
stress principle as proposed by Zienkiewicz and Shiomi (1984), which
accounts for the compressibility of the solid phase in porous materials.
For such materials like soils whose solid component is almost incompressible, 𝛼 ≈ 1 and hence Eq. (2) reduces to the following well-known
form proposed by Terzaghi (1943):
𝝈 = 𝝈′
− 𝑝𝑰 (4)
In this paper, the focus is exclusively on the case of an almost incompressible solid phase, and consequently, Eq. (4) is employed.
The solid skeleton moves with a velocity denoted by 𝒖, while the
pore fluid has an additional relative velocity 𝒘, typically referred to as

## Page 3

Darcy velocity. The following governing equations in Lagrangian form
are established by considering the momentum equilibrium of the binary
mixture, the momentum equilibrium of the pore fluid, and the mass
conservation of the pore fluid, respectively (Zienkiewicz and Shiomi,
1984):
∇ ⋅ 𝝈 − 𝜌
d𝒖
d𝑡
− 𝜌𝑓
(
d𝒘
d𝑡
+ 𝒘 ⋅ ∇𝒘
)
+ 𝜌𝒃 = 0 (5)
−∇𝑝 − 𝑹 − 𝜌𝑓
d𝒖
d𝑡
−
𝜌𝑓
𝑛
(
d𝒘
d𝑡
+ 𝒘 ⋅ ∇𝒘
)
+ 𝜌𝑓 𝒃 = 0 (6)
∇ ⋅ 𝒘 + 𝛼∇ ⋅ 𝒖 +
𝑄
d𝑝
d𝑡
= 0 (7)
where 𝒃 denotes the body force such as gravity, 𝑹 represents the
interaction force between solid skeleton and pore fluid, and 𝑄 is the
bulk modulus of the mixture named the Biot’s modulus which is defined
by:
𝑄
=
𝑛
𝐾𝑓
+
𝛼 − 𝑛
𝐾𝑠
≈
𝑛
𝐾𝑓
(8)
where 𝐾𝑓 is the bulk modulus of pore fluid. Based on the validity of
linear Darcy’s law, the interaction force 𝑹 takes the following form:
𝑹 =
𝛾𝑓
𝑘
𝒘 (9)
where 𝛾𝑓 is the unit weight of pore fluid and 𝑘 is the hydraulic
conductivity.
To complete the above governing equations, a constitutive law
for the solid skeleton is needed. Since only poroelastic problems are
discussed in this paper, the following linear elastic model is employed:
̇
𝝈′
= 2𝐺 ̇
𝒆 + 𝐾𝑇 ̇
𝜀𝑣𝑰 (10)
where 𝐾𝑇 is the bulk modulus and 𝐺 is the shear modulus of the solid
skeleton, with ̇
𝒆 denoting the deviatoric part and ̇
𝜀𝑣 the volumetric
part of the strain rate tensor ̇
𝜺. Based on the updated-Lagrangian
formalism and the infinitesimal deformation assumption, ̇
𝜺 is related
to the velocity field 𝒖 by:
̇
𝜺 =
(∇ ⊗ 𝒖 + 𝒖 ⊗ ∇) (11)
Eqs (5) through (7) constitute the full formulation of the Biot’s
model, which has a complex mathematical structure. Some simplifying
assumptions are usually introduced to derive several simplified versions of the Biot’s model, whose validity has been closely examined
by Zienkiewicz et al. (1980). In this paper, the so-called 𝒖-𝒘-𝑝 and 𝒖-𝑝
formulations are discussed, with their detailed derivation from the full
formulation presented in Appendix A.
2.1. 𝒖-𝒘-𝑝 formulation
The 𝒖-𝒘-𝑝 formulation of Biot’s model is derived by neglecting the
convective term 𝒘 ⋅ ∇𝒘 in Eqs (5) and (6). Then, by introducing the
effective stress principle expressed in Eq. (4) and by assuming that the
compressibility of solid phase is negligible, i.e. 𝛼 ≈ 1, Eqs (5) to (7)
become:
d𝒖
d𝑡
=
(1 − 𝑛)𝜌𝑠
∇ ⋅ 𝝈′
−
𝜌𝑠
∇𝑝 + 𝒃 +
𝑛𝛾𝑓
(1 − 𝑛)𝜌𝑠𝑘
𝒘 (12)
d𝒘
d𝑡
= −
𝑛
(1 − 𝑛)𝜌𝑠
∇ ⋅ 𝝈′
−
𝑛(𝜌𝑠 − 𝜌𝑓 )
𝜌𝑠𝜌𝑓
∇𝑝 −
𝑛𝜌𝛾𝑓
(1 − 𝑛)𝜌𝑠𝜌𝑓 𝑘
𝒘 (13)
d𝑝
d𝑡
= −𝑄(∇ ⋅ 𝒖 + ∇ ⋅ 𝒘) (14)
2.2. 𝒖-𝑝 formulation
The 𝒖-𝑝 formulation of Biot’s model is derived by neglecting all the
derivative terms related to 𝒘, i.e. those terms in the round parentheses of Eqs (5) and (6). This is rational under low-frequency loading
and/or low permeability whereby the inertial effects related to 𝒘 are
negligible (Zienkiewicz et al., 1999). Similarly, the following governing
equations are derived based on the effective stress principle and 𝛼 ≈ 1:
d𝒖
d𝑡
=
𝜌
∇ ⋅ 𝝈′
−
𝜌
∇𝑝 + 𝒃 (15)
d𝑝
d𝑡
=
𝑘𝑄
𝛾𝑓
∇2
𝑝 − 𝑄∇ ⋅ 𝒖 (16)
3. SPH gradient and Laplacian operators
3.1. The gradient
SPH is categorised as a strong form numerical method. Its formulation for the governing equations of a physical problem can be obtained
by approximating differential operators with corresponding SPH ones.
Two popular SPH approximations for the gradient of a scalar field 𝜙(𝒙)
are as follows:
⟨∇𝜙𝑖⟩ =
∑
𝑗
𝑉𝑗(𝜙𝑗 ± 𝜙𝑖)∇𝑖𝑊𝑖𝑗 (17)
where ⟨⋅⟩ denotes an SPH approximation, the subscripts 𝑖 and 𝑗 distinguish the current and neighbouring SPH particles, 𝜙𝑖 = 𝜙(𝒙𝑖), 𝑉 is
the volume of an SPH particle, 𝑊𝑖𝑗 is the weighting function called the
smoothing kernel evaluated between particles 𝑖 and 𝑗, and ∇𝑖𝑊𝑖𝑗 is the
corresponding gradient with respect to the position 𝒙𝑖. In this paper,
the following quintic kernel (Wendland, 1995) is employed:
𝑊𝑖𝑗 = 𝛼𝐷
⎧
⎪
⎨
⎪
⎩
(
1 −
|𝒙𝑖𝑗|
2ℎ
)4 (
2|𝒙𝑖𝑗|
ℎ
+ 1
)
, 0 ≤ |𝒙𝑖𝑗| ≤ 2ℎ
0, otherwise
(18)
where 𝛼𝐷 is a normalisation factor with a value of 7∕4𝜋ℎ2 in 2-D,
𝒙𝑖𝑗 = 𝒙𝑖 − 𝒙𝑗, and ℎ is the smoothing length.
The positive variant of Eq. (17) does not exhibit the zeroth-order
consistency, as its approximation of any constant field 𝜙(𝒙) typically
deviates from zero. Meanwhile, it conserves particle–particle momentum because the magnitudes of interactions between particles 𝑖 and
𝑗, and reciprocally between 𝑗 and 𝑖, are equal. This variant is widely
used for discretising the momentum equation in the classical SPH technique, resulting in a formulation that inherently satisfies free-surface
conditions (Colagrossi et al., 2009). Such a characteristic represents a
substantial advantage of the classical SPH technique over alternative
numerical methods.
On the other hand, the negative variant of Eq. (17) possesses the
zeroth-order consistency, while it violates the conservation of particle–
particle momentum. This variant is seldom employed for discretising
the momentum equation, as the resulting formulation suffers from
severe stability issues. The accuracy of the negative variant of Eq. (17)
can be improved to achieve the first-order consistency using the socalled kernel gradient renormalisation (Randles and Libersky, 1996;
Bonet and Lok, 1999; Oger et al., 2007).
A drawback of these corrections is that their accuracy still drops
in the proximity of domain boundary, which significantly affects the
explicitly-enforced boundary conditions. To this end, the gradient operator proposed by Bonet and Lok (1999) is herein employed:
⟨∇𝜙𝑖⟩ =
∑
𝑗
𝑉𝑗𝜙𝑗
̃
∇𝑖
̃
𝑊𝑖𝑗 (19)
where the corrected kernel ̃
𝑊𝑖𝑗 = 𝑊𝑖𝑗∕
∑
𝑗 𝑉𝑗𝑊𝑖𝑗 and its renormalised
gradient ̃
∇𝑖
̃
𝑊𝑖𝑗 is defined as:
̃
∇𝑖
̃
𝑊𝑖𝑗 = ̃
𝑳𝑖 ⋅ ∇𝑖
̃
𝑊𝑖𝑗 (20)

## Page 4

where the renormalisation matrix ̃
𝑳𝑖 now takes the following form:
̃
𝑳𝑖 =
(
∑
𝑗
𝑉𝑗∇𝑖
̃
𝑊𝑖𝑗 ⊗ 𝒙𝑗
)−1
(21)
The additional accuracy of Eq. (19) can be interpreted, with the correction on the kernel changes the weight of kernel gradient, as being
especially significant close to a domain boundary and/or under highly
disordered particle distributions. Such an improvement plays a vital
role when boundary conditions are explicitly enforced. Numerical experiments show that Eq. (19) ensures numerical stability while the
kernel gradient renormalisation quickly leads to numerical instability
due to its inaccuracy.
3.2. The Laplacian
SPH operators for high-order derivatives are sensitive to particle disorder and hence they are generally not favoured (Monaghan, 2005). For
the Laplacian, Brookshaw (1985) proposed to avoid the second-order
derivative of smoothing kernel by combining a standard SPH firstorder derivative with a finite difference approximation of a first-order
derivative. Their operator takes the following form:
⟨
∇2
𝜙𝑖
⟩
= 2
∑
𝑗
𝑚𝑗
𝜌𝑗
(𝜙𝑖 − 𝜙𝑗)
𝒙𝑖𝑗 ⋅ ∇𝑖𝑊𝑖𝑗
|𝒙𝑖𝑗|2
(22)
This operator is found to be robust and stable, and hence it has been
widely employed in relevant SPH formulations (Morris et al., 1997;
Xu et al., 2009; Lind and Stansby, 2016). One drawback of Eq. (22)
is its inaccuracy around the free surface. Schwaiger (2008) discussed
this issue and proposed the following improved version:
⟨
∇2
𝜙𝑖
⟩
=
tr(𝛤−1
𝑖 )
𝑛𝑆𝐷
[
∑
𝑗
𝑚𝑗
𝜌𝑗
(𝜙𝑖 − 𝜙𝑗)
𝒙𝑖𝑗 ⋅ ∇𝑖𝑊𝑖𝑗
|𝒙𝑖𝑗|2
− 2∇𝜙𝑖 ⋅
∑
𝑗
𝑚𝑗
𝜌𝑗
∇𝑖𝑊𝑖𝑗
]
(23)
where 𝑛𝑆𝐷 is the space dimension and 𝛤𝑖 is a second-order tensor
defined by:
𝛤𝑖 =
∑
𝑗
𝑚𝑗
𝜌𝑗
(𝒙𝑖𝑗 ⊗ 𝒙𝑖𝑗)
𝒙𝑖𝑗 ⋅ ∇𝑖𝑊𝑖𝑗
|𝒙𝑖𝑗|2
(24)
Note that the kernel gradient in Eqs (23) and (24) is the original one
without any corrections applied. Eq. (23) will be used to discretise the
Laplacian term in the 𝒖-𝑝 model, as discussed in the next section.
Another Laplacian operator of particular relevance to this paper is
the one proposed by Antuono et al. (2010), which reads:
⟨
∇2
𝜙𝑖
⟩
= 2
∑
𝑗
𝑚𝑗
𝜌𝑗
[
(𝜙𝑖 − 𝜙𝑗) −
(∇𝜙𝑖 + ∇𝜙𝑗) ⋅ 𝒙𝑖𝑗
] 𝒙𝑖𝑗 ⋅ ∇𝑖𝑊𝑖𝑗
|𝒙𝑖𝑗|2
(25)
Eq. (25) will be used to discretise the Laplacian terms in the proposed
volumetric strain diffusion techniques (see Section 4.4.3), due to its
robustness, stability and less diffusivity. Both Eqs (23) and (25) involve
field gradients, and a corrected gradient operator should be used to
evaluate their values, i.e. Eq. (19). Other Laplacian operators have
also been recently proposed by Bui and Nguyen (2021) and Asai et al.
(2023), but are not considered in this paper.
4. SPH formulations for biot’s model
(i) 𝒖-𝒘-𝑝 model
The 𝒖-𝒘-𝑝 version of Biot’s model expressed in Eqs (12)–(14) only
contains first-order derivatives. By employing the corrected gradient
operator in Eq. (19), its SPH formulation is obtained as:
⟨
d𝒖𝑖
d𝑡
⟩
=
(1 − 𝑛)𝜌𝑠
∑
𝑗
𝑚𝑗
𝜌𝑗
𝝈′
𝑗 ⋅ ̃
∇𝑖
̃
𝑊𝑖𝑗 −
𝜌𝑠
∑
𝑗
𝑚𝑗
𝜌𝑗
𝑝𝑗
̃
∇𝑖
̃
𝑊𝑖𝑗 + 𝒃𝑖 +
𝑛𝛾𝑓
(1 − 𝑛)𝜌𝑠𝑘
𝒘𝑖
−
∑
𝑗
𝑚𝑗 𝛱𝑖𝑗 ∇𝑖𝑊𝑖𝑗 + 𝑭 𝑑
(26)
⟨
d𝒘𝑖
d𝑡
⟩
= −
𝑛
(1 − 𝑛)𝜌𝑠
∑
𝑗
𝑚𝑗
𝜌𝑗
𝝈′
𝑗 ⋅ ̃
∇𝑖
̃
𝑊𝑖𝑗 −
𝑛(𝜌𝑠 − 𝜌𝑓 )
𝜌𝑠𝜌𝑓
∑
𝑗
𝑚𝑗
𝜌𝑗
𝑝𝑗
̃
∇𝑖
̃
𝑊𝑖𝑗
−
𝑛𝜌𝑖𝛾𝑓
(1 − 𝑛)𝜌𝑠𝜌𝑓 𝑘
𝒘𝑖
(27)
⟨
d𝑝𝑖
d𝑡
⟩
= −𝑄
∑
𝑗
𝑚𝑗
𝜌𝑗
(𝒖𝑗 + 𝒘𝑗) ⋅ ̃
∇𝑖
̃
𝑊𝑖𝑗 (28)
where the last two terms in Eq. (26) are numerical stabilisation measures to be explained in Section 4.4.
(ii) 𝒖-𝑝 model
The 𝒖-𝑝 version of Biot’s model expressed in Eqs (15)–(16) involves both first-order and second-order derivatives. Accordingly, the
corrected gradient operator, Eq. (19), and the corrected Laplacian
operator, Eq. (23), are employed, resulting in the following SPH formulation:
⟨
d𝒖𝑖
d𝑡
⟩
=
𝜌𝑖
∑
𝑗
𝑚𝑗
𝜌𝑗
𝝈′
𝑗 ⋅ ̃
∇𝑖
̃
𝑊𝑖𝑗 −
𝜌𝑖
∑
𝑗
𝑚𝑗
𝜌𝑗
𝑝𝑗
̃
∇𝑖
̃
𝑊𝑖𝑗 + 𝒃𝑖 −
∑
𝑗
𝑚𝑗 𝛱𝑖𝑗 ∇𝑖𝑊𝑖𝑗 + 𝑭 𝑑
(29)
⟨
d𝑝𝑖
d𝑡
⟩
=
𝑘𝑄
𝛾𝑓
tr(𝛤−1
𝑖
)
𝑛𝑆𝐷
[
∑
𝑗
𝑚𝑗
𝜌𝑗
(𝑝𝑖 − 𝑝𝑗 )
𝒙𝑖𝑗 ⋅ ∇𝑖𝑊𝑖𝑗
|𝒙𝑖𝑗 |2
− 2∇𝑝𝑖 ⋅
∑
𝑗
𝑚𝑗
𝜌𝑗
∇𝑖𝑊𝑖𝑗
]
− 𝑄
∑
𝑗
𝑚𝑗
𝜌𝑗
𝒖𝑗 ⋅ ̃
∇𝑖
̃
𝑊𝑖𝑗
(30)
where again two numerical stabilisation terms are added in Eq. (29).
Moreover, as discussed in Section 2, a constitutive law is needed to
complete the governing equations in Biot’s model, which is based on
the strain rate tensor in Eq. (11). Similarly, the SPH formulation for ̇
𝜺
reads:
⟨ ̇
𝜺𝑖⟩ =
(
∑
𝑗
𝑚𝑗
𝜌𝑗
̃
∇𝑖
̃
𝑊𝑖𝑗 ⊗ 𝒖𝑗 +
∑
𝑗
𝑚𝑗
𝜌𝑗
𝒖𝑗 ⊗ ̃
∇𝑖
̃
𝑊𝑖𝑗
)
(31)
Note that in the above formulations, the corrected kernel gradient
of Bonet and Lok (1999), i.e. ̃
∇𝑖
̃
𝑊𝑖𝑗, is applied for discretising the
gradient terms in the governing equations, whereas the classical kernel
gradient, i.e. ∇𝑖𝑊𝑖𝑗 is utilised in the remaining terms including the
artificial viscosity and Schwaiger’s Laplacian operator.
In mesh-based methods, the 𝒖-𝑝 version of Biot’s model is preferred
due to its fewer nodal degrees of freedom. Conversely, within the
context of the SPH method, the 𝒖-𝒘-𝑝 formulation proves to be more
beneficial than its 𝒖-𝑝 counterpart for three reasons: (i) The 𝒖-𝒘-𝑝
formulation is applicable to a wider range of problems, notably those
associated with high-frequency loading (Zienkiewicz et al., 1980); (ii)
There is no need to solve linear systems involving all nodal variables
(e.g. the global stiffness matrix in FEM) in the current formulations, and
hence the cost of introducing an additional state variable is negligible;
(iii) Only first-order derivatives exist in the 𝒖-𝒘-𝑝 model, whereas
the 𝒖-𝑝 model contains a Laplacian term whose accurate evaluation
is not straightforward in the SPH method. Specifically, as expressed
in Eq. (30), much effort is devoted to accurately approximate ∇2𝑝,
which leads to a computational cost higher than the counterpart 𝒖-𝒘-𝑝
model. Moreover, numerical experiments show the corrected Laplacian
operator in Eq. (23) possesses a large error under highly disordered
particle distributions. Since the governing equations of Biot’s model
can be classified as stiff equations, this error would ultimately result
in failure of an SPH simulation.
Numerical implementation of the proposed SPH formulations of
Biot’s model entails further discussions, which are presented
below.

## Page 5

Table 1
Properties of the poroelastic medium in the 1-D consolidation test.
Parameter Symbol Value Unit
Porosity 𝑛 0.3 –
Density of pore water 𝜌𝑓 1000 kg/m3
Density of solid phase 𝜌𝑠 2000 kg/m3
Young’s modulus of solid skeleton 𝐸 30 MPa
Poisson’s ratio of solid skeleton 𝜈 0.2 –
Hydraulic conductivity 𝑘 0.001 m/s
Bulk modulus of pore water 𝐾𝑓 100 MPa
4.1. Single-layer approach
In this paper, a saturated porous medium is considered as a single
continuum and represented by one layer of SPH particles, known
as the single-layer approach. This method offers computational efficiency, a merit particularly notable when compared to the two-layer
approach (see e.g. Soga et al., 2016; Bui and Nguyen, 2017), where the
binary mixture is treated as a superposition of two separate continua for
the solid phase and the fluid phase. One problem with the single-layer
approach that needs a special attention is the evolution of density of
the mixture. For continua such as water, the density evolves according
to the continuity equation. However, the variation in densities of the
solid and fluid constituents of saturated porous materials, i.e. 𝜌𝑠 and
𝜌𝑓 , is negligible. The evolution in the bulk density of the mixture, 𝜌, is
attributed to deformation of the solid skeleton. When constructing the
Biot’s model expressed in Eqs (5)–(7), the reference frame is attached to
the solid skeleton and hence mass conservation of the solid constituent
in this reference frame is inherently satisfied. However, pore fluid flux
may flow through the control volume defined by the solid skeleton,
and thus, mass conservation for pore fluid is described by Eq. (7).
Macroscopically, deformation of the material, or more specifically the
solid skeleton, can be depicted by the change in porosity 𝑛. The mathematical derivation for the evolution of bulk density 𝜌 is presented in
the following.
For a saturated porous medium with an initial porosity of 𝑛0, the
initial density of the bulk mixture, 𝜌0, can be expressed as 𝜌0 = (1 −
𝑛0)𝜌𝑠 + 𝑛0𝜌𝑓 , as per Eq. (1). Considering an SPH particle with an initial
volume of 𝑉0, the volume and mass of the solid constituent carried
by this particle are 𝑉𝑠0 = (1 − 𝑛0)𝑉0 and 𝑚𝑠0 = 𝜌𝑠𝑉𝑠0, respectively.
These values remain constant throughout material deformation. At any
time instant, the volume of this SPH particle can be expressed as
𝑉 = (1 + 𝜀𝑣)𝑉0, where 𝜀𝑣 represents the volumetric strain of the solid
skeleton. The corresponding porosity is then derived as:
𝑛 =
𝑉 − 𝑉𝑠0
𝑉
=
𝑛0 + 𝜀𝑣
1 + 𝜀𝑣
(32)
As a result, the bulk density of the binary mixture at this time instant
is obtained as:
𝜌 = (1 − 𝑛)𝜌𝑠 + 𝑛𝜌𝑓
=
1 + 𝜀𝑣
[(1 − 𝑛0)𝜌𝑠 + (𝑛0 + 𝜀𝑣)𝜌𝑓 ]
(33)
It should be noted that, in such a formulation, the mass of an SPH
particle changes with material deformation, as a result of flux of pore
fluid. Moreover, the porosity varies in space but its gradient is generally
small and is therefore not accounted for in the governing Eqs. (5)–(7).
For the scenario where the spatial variation in porosity is significant,
its effect can be easily introduced into the governing equation (see e.g.
Bui and Nguyen, 2017).
4.2. Time integration
As the classical SPH integration is second-order accurate, the explicit second-order accurate symplectic scheme (Domínguez et al.,
2022) is employed to march the simulation in time. For the 𝒖-𝒘-𝑝 formulation, the time step size 𝛥𝑡 should satisfy the well-known
Courant–Friedrichs–Lewy (CFL) condition (Violeau, 2012):
𝛥𝑡𝑐 =
ℎ
𝑐𝑠
(34)
where ℎ is the smoothing length introduced in Eq. (18) and 𝑐𝑠 represents the numerical speed of sound determined by:
𝑐𝑠 =
√
𝐸𝑐 + 𝑄
𝜌
(35)
where 𝑄 is the Biot’s modulus expressed in Eq. (8) and 𝐸𝑐 is the
constrained modulus defined as:
𝐸𝑐 =
𝐸(1 − 𝜈)
(1 + 𝜈)(1 − 2𝜈)
(36)
where 𝐸 and 𝜈 are the Young’s modulus and the Poisson’s ratio of the
solid skeleton, respectively. The time step size is also limited by the
forcing terms:
𝛥𝑡𝑓 = min
𝑖
√
ℎ
|d𝒖𝑖∕d𝑡|
(37)
Moreover, the time step size is further limited by the following permeability-dependent criterion proposed by Mieremet et al. (2016):
𝛥𝑡𝑘 =
−𝛾𝑓 ∕ ̃
𝜌𝑘 +
√
(𝛾𝑓 ∕ ̃
𝜌𝑘)2 + 16𝐸∕ ̃
𝜌ℎ2
4𝐸∕ ̃
𝜌ℎ2
(38)
where ̃
𝜌 = 𝜌 + (1∕𝑛 − 2)𝜌𝑓 . As a result, the time step for the 𝒖-𝒘-𝑝
formulation is determined as follows:
𝛥𝑡𝑢−𝑤−𝑝 = 𝐶CFL min(𝛥𝑡𝑐, 𝛥𝑡𝑓 , 𝛥𝑡𝑘) (39)
where 𝐶CFL is the Courant number, with values ranging between 0.05
and 0.5 for the coupled formulation. A typical value of 0.1 is used in
most of the simulations presented in this paper.
For the 𝒖-𝑝 formulation, the time step size is also constrained by the
CFL condition, Eq. (34), and the forcing terms, Eq. (37). Moreover, it
is limited by the following criterion to ensure numerical stability of the
Laplacian term in Eq. (30):
𝛥𝑡𝑣 = 0.5
𝛾𝑓 ℎ2
𝑘𝑄
(40)
As a result, the time step for the 𝒖-𝑝 formulation is determined as
follows:
𝛥𝑡𝑢−𝑝 = 𝐶CFL min(𝛥𝑡𝑐, 𝛥𝑡𝑓 , 𝛥𝑡𝑣) (41)
In most tests presented in this paper, the time step is constrained
by the numerical speed of sound. For the material properties given in
Table 1, 𝑐𝑠 ≈ 500 m∕s and hence a typical value of 𝛥𝑡 is 2.8 × 105 s. The
responses of 𝛥𝑡 to 𝑘 differ between the two models. Specifically, the
𝒖-𝒘-𝑝 model incurs higher computational costs when 𝑘 is smaller, as
𝛥𝑡𝑘 becomes more restrictive. In contrast, the 𝒖-𝑝 model is less efficient
when 𝑘 is larger, as 𝛥𝑡𝑣 is the most dominant factor in this scenario.
Since a large speed of sound is used for strongly-coupled phenomena,
the models presented in this paper are inapplicable to porous materials
with very low permeability. This is because the physical time involved
would be significantly longer, e.g. days and weeks. For such scenarios,
further work may be required, such as introducing reduced formulations and improved time-stepping schemes (see e.g. Zhao and Choo,
2020; Lian et al., 2023).
4.3. Boundary conditions
For the SPH formulations proposed in this paper, free-surface boundary conditions must be explicitly enforced to define the problem
fully and ensure numerical stability. Similarly, other boundary conditions must also be explicitly applied, unless they are modelled using
approaches such as dummy particles. This requirement allows the

## Page 6

Fig. 2. Illustration of boundary particles.
application of various conditions at the domain boundary, which
may be challenging for a classical formulation. In general, coordinate
transformations are needed to define a local reference frame, thereby
enabling enforcing various conditions with concrete physical meanings,
e.g. normal and shear stresses. In the test cases discussed in this
paper, only simple geometry is involved and its change upon loading is insignificant due to the considered small-deformation scenario.
Consequently, boundary conditions can be applied directly without any
coordinate transformations.
In the context of a saturated porous medium, its boundary 𝛤 encompasses two distinct components: 𝛤𝑠 which represents the solid skeleton
and 𝛤𝑓 signifying the pore fluid. 𝛤𝑠 can be subdivided into velocity
(Dirichlet) and traction (Neumann) boundaries, 𝛤𝑢 and 𝛤𝑡. Similarly,
𝛤𝑓 can be decomposed into pressure (Dirichlet) and flux (Neumann)
boundaries, 𝛤𝑝 and 𝛤𝑤. Such divisions satisfy: 𝛤𝑠 = 𝛤𝑢 ∪𝛤𝑡, 𝛤𝑓 = 𝛤𝑝 ∪𝛤𝑤
and ∅ = 𝛤𝑢 ∩ 𝛤𝑡 = 𝛤𝑢 ∩ 𝛤𝑡. Fig. 2 illustrates a 2-D problem domain
with two boundaries 𝛤1 and 𝛤2. At 𝛤1, boundary SPH particles have 3
degrees of freedom (DoF): 𝑢𝑥 (or 𝜎′
𝑥𝑧), 𝑢𝑧 (or 𝜎′
𝑧𝑧), and 𝑤𝑧 (or 𝑝). If 𝛤1 is a
free surface, then 𝜎′
𝑥𝑧 = 𝜎′
𝑧𝑧 = 𝑝 = 0 is assigned to the boundary particles
representing 𝛤1. If 𝛤1 is a permeable traction boundary under normal
compression stress of 𝜎𝑐, the assigned conditions become: 𝜎′
𝑧𝑧 = −𝜎𝑐
and 𝜎′
𝑥𝑧 = 𝑝 = 0. The method for applying various boundary conditions
will be detailed in each test case presented in Section 5.
A point that merits special discussion is the boundary particle shared
by 𝛤1 and 𝛤2, i.e. the red particle displayed in Fig. 2. Although the
particles at each boundary possess 3 DoF, the corresponding number
for this specific particle is less than 6 due to coupled effects between
the two boundaries. For instance, if 𝛤1 and 𝛤2 are both free surface,
𝜎′
𝑥𝑧 = 𝜎′
𝑧𝑧 = 𝑝 = 0 is applied for 𝛤1 and thus only 𝜎′
𝑥𝑥 = 0 is needed to
enforce the free-surface conditions for 𝛤2.
4.3.1. Absorbing boundary conditions
The essential idea of absorbing boundary conditions is to apply
damping stresses at the domain boundary that absorb the incident
waves. If 𝛤1 in Fig. 2 is considered as the absorbing boundary, the
following damping stresses are applied for stress waves in the solid
skeleton (Kafaji, 2013):
𝜎′𝑎𝑏
𝑥𝑧 = −𝜌𝑐𝑠𝑢𝑥 −
𝜌𝑐2
𝑠
𝛿
𝛥𝑥
𝜎′𝑎𝑏
𝑧𝑧 = −𝜌𝑐𝑝𝑢𝑧 −
𝜌𝑐2
𝑝
𝛿
𝛥𝑧
(42)
where the superscript 𝑎𝑏 denotes the absorbing boundary, 𝛥 is the
displacement of the solid skeleton, 𝛿 is a tuning parameter, and 𝑐𝑝 and
𝑐𝑠 are the 𝑝-wave and 𝑠-wave speed of the saturated porous medium,
respectively. For pressure waves inside the pore fluid, the following
damping pressure is applied in the 𝒖-𝒘-𝑝 formulation:
𝑝𝑎𝑏
= −𝜌𝑓 𝑐𝑝𝑓
(
𝑢𝑧 +
𝑤𝑧
𝑛
)
−
𝜌𝑓 𝑐2
𝑝𝑓
𝛿
(
𝛥𝑧 +
𝛥𝑤
𝑧
𝑛
)
(43)
where 𝛥𝑤 and 𝑐𝑝𝑓 are the average relative displacement and 𝑝-wave
speed of the pore fluid, respectively. Regarding the 𝒖-𝑝 formulation, the
relative motion of pore fluid is ignored and hence the damping pressure
is reduced to:
𝑝𝑎𝑏
= −𝜌𝑓 𝑐𝑝𝑓 𝑢𝑧 −
𝜌𝑓 𝑐2
𝑝𝑓
𝛿
𝛥𝑧 (44)
The tuning parameter 𝛿 stands for the thickness of the virtual
viscous layer and 0 < 𝛿 < ∞. More specifically, the boundary reduces
to a rigid one when 𝛿 → 0, while it degrades to a dashpot boundary
when 𝛿 → ∞. According to Kafaji (2013), 𝛿 should satisfy the following
conditions to exclude its restriction on the critical time step size:
𝛿 ≥
ℎmin
2𝑎
and 𝛿 ≥
ℎmin
2𝑏
(45)
where ℎmin is the characteristic length of a discretisation, which could
be the smoothing length ℎ in the SPH formulation.
4.4. Numerical stabilisation
4.4.1. Artificial viscosity
In SPH simulations, shocks like the relaxation of initial conditions
can cause large unphysical oscillations and even numerical instability.
To damp out these oscillations, a dissipation term 𝛱𝑖𝑗 is usually introduced into the momentum equations, i.e. Eqs (26) and (29). The
artificial viscosity proposed by Monaghan (1992) is extensively employed due to its simplicity and effectiveness, which takes the following
form:
𝛱𝑖𝑗 =
⎧
⎪
⎨
⎪
⎩
−
𝛼𝛱 ̄
𝑐𝑠𝑖𝑗
̄
𝜌𝑖𝑗
ℎ𝒖𝑖𝑗 ⋅ 𝒙𝑖𝑗
|𝒙𝑖𝑗|2
, 𝒖𝑖𝑗 ⋅ 𝒙𝑖𝑗 < 0
0, 𝒖𝑖𝑗 ⋅ 𝒙𝑖𝑗 ≥ 0
(46)
where 𝛼𝛱 is an empirical coefficient, ̄
𝑐𝑠𝑖𝑗 = (𝑐𝑠𝑖 + 𝑐𝑠𝑗)∕2 is the mean
numerical speed of sound, ̄
𝜌𝑖𝑗 = (𝜌𝑖 + 𝜌𝑗)∕2 is the average density, and
𝒖𝑖𝑗 = 𝒖𝑖 − 𝒖𝑗.
4.4.2. Artificial damping
The sudden application of external loading may induce large oscillations in the problem domain due to stress wave propagation and
reflection. Since this paper focuses on poroelastic problems, the linear
elastic constitutive law, Eq. (10), is assumed for the solid skeleton. As
a result, the numerical model lacks damping effects despite the use of

## Page 7

Fig. 3. Zones of applicability of various assumptions for the Biot’s model (Monforte et al., 2019) and locations of main tests presented in this paper.
artificial viscosity. To suppress such oscillations, the following artificial
damping force, 𝑭 𝑑, is added to the momentum Eqs. (26) and (29):
𝑭 𝑑 = −𝜇𝑑𝒖 (47)
where 𝜇𝑑 is a damping coefficient. In 2-D applications, Bui and Fukagawa (2013) proposed to determine 𝜇𝑑 by the following expression:
𝜇𝑑 = 𝜉
√
𝐸
𝜌ℎ2
(48)
where 𝜉 is a non-dimensional coefficient and 𝐸 is the Young’s modulus
of the material. In general, 𝜇𝑑 can be arbitrarily tuned to obtain the
desired effects.
4.4.3. Volumetric strain diffusion
The simulation of near-incompressible materials such as saturated
porous media frequently faces the so-called volumetric locking issue. In mesh-based techniques such as FEM and MPM, the B-bar
method (Hughes, 1980) is widely employed as a countermeasure. The
essential idea of this method is to average the volumetric strain over
the neighbours of a interpolation point. However, as SPH is a truly
meshless method, the volumetric strain averaging process cannot be
accomplished based on computational meshes. Inspired by the 𝛿-SPH
model of Marrone et al. (2011), it is herein proposed to add a diffusion
term to the update of volumetric strain, that is:
d𝜀𝑣
d𝑡
= ∇ ⋅ 𝒖 + 𝛿𝑢
ℎ𝑐𝑠∇2
𝜀𝑣 (49)
where 𝛿𝑢 is a tuning parameter and, as in Marrone et al. (2011), its
typical value is 0.1. It is found that discretising the Laplacian term
in the above equation using Eq. (23) leads to excessive diffusion in
the volumetric strain field, thereby significantly changing the dominant
physics. Instead, the Laplacian operator Eq. (25) is employed, resulting
in:
⟨
d𝜀𝑣𝑖
d𝑡
⟩
=
∑
𝑗
𝑚𝑗
𝜌𝑗
𝒖𝑗 ⋅ ̃
∇𝑖
̃
𝑊𝑖𝑗
+ 2𝛿𝑢
ℎ𝑐𝑠
∑
𝑗
𝑚𝑗
𝜌𝑗
[
(𝜀𝑣𝑖 − 𝜀𝑣𝑗) −
(∇𝜀𝑣𝑖 + ∇𝜀𝑣𝑗) ⋅ 𝒙𝑖𝑗
] 𝒙𝑖𝑗 ⋅ ∇𝑖𝑊𝑖𝑗
|𝒙𝑖𝑗|2
(50)
For the 𝒖-𝒘-𝑝 formulation, the quantity ∇ ⋅ 𝒘 represents the volumetric discharge of pore fluid. By denoting the total discharge as 𝜀𝑤
𝑣 , it
is found that an extra diffusion term on 𝜀𝑤
𝑣 is needed, namely:
d𝜀𝑤
𝑣
d𝑡
= ∇ ⋅ 𝒘 + 𝛿𝑤
ℎ𝑐𝑠∇2
𝜀𝑤
𝑣 (51)
where 𝛿𝑤 is another tuning parameter whose typical value is also 0.1.
Eq. (51) is referred to as discharge diffusion term in this paper and its
SPH formulation is:
⟨
d𝜀𝑤
𝑣𝑖
d𝑡
⟩
=
∑
𝑗
𝑚𝑗
𝜌𝑗
𝒘𝑗 ⋅ ̃
∇𝑖
̃
𝑊𝑖𝑗
+ 2𝛿𝑤
ℎ𝑐𝑠
∑
𝑗
𝑚𝑗
𝜌𝑗
[
(𝜀𝑤
𝑣𝑖 − 𝜀𝑤
𝑣𝑗 ) −
(∇𝜀𝑤
𝑣𝑖 + ∇𝜀𝑤
𝑣𝑗 ) ⋅ 𝒙𝑖𝑗
] 𝒙𝑖𝑗 ⋅ ∇𝑖𝑊𝑖𝑗
|𝒙𝑖𝑗 |2
(52)
The diffusion terms, Eqs (50) and (52), average the volumetric part
of relevant strains at a particle with its neighbouring particles, which is
similar to the B-bar method in mesh-based techniques including FEM
and MPM (see e.g. Navas et al., 2016; Coombs et al., 2018; Iaconeta
et al., 2019; Moutsanidis et al., 2020; Bisht et al., 2021).
5. Numerical tests
The validity of simplified versions of Biot’s model was studied
by Zienkiewicz et al. (1980) through the 1-D harmonic loading test
(see Section 5.2.1). Three versions were considered, including the
𝒖-𝒘-𝑝 form (Eqs (12)–(14)), the 𝒖-𝑝 form (Eqs (15)–(16)), and the
consolidation form where both the inertial terms, d𝒖∕d𝑡 and d𝒘∕d𝑡,
are neglected. The main achievement of this work is the identification
of three zones of applicability shown in Fig. 3. Specifically, the two
dimensionless parameters, 𝛱1 and 𝛱2, are defined as:
𝛱1 =
𝑘𝑉 2
𝑐
𝑔𝛽𝜔𝐿2
and 𝛱2 =
𝜔2𝐿2
𝑉 2
𝑐
(53)
Interested readers are referred to Zienkiewicz et al. (1980) for a complete explanation of the involved notations. It can be simply understood
that 𝛱1 represents permeability of the porous medium and 𝛱2 relates to
frequency of the applied loading. The three zones are then summarised
in the following.
• Zone I: Slow phenomena where both the inertial terms d𝒖∕d𝑡
and d𝒘∕d𝑡 can be neglected, and hence all the three considered
formulations are applicable.
• Zone II: Moderate speed where only the inertial term d𝒘∕d𝑡 can
be neglected, and therefore the 𝒖-𝒘-𝑝 and 𝒖-𝑝 formulations are
applicable.

## Page 8

Fig. 4. 1-D consolidation problem and numerical set-up.
• Zone III: Fast phenomena where the inertial terms cannot be
neglected, and consequently only the 𝒖-𝒘-𝑝 formulation is applicable.
It should be noted that Fig. 3 was obtained from a 1-D analysis,
and it can only provide a rough estimation for problems in higher
dimensions. The position of a particular problem in this dimensionless
plane can be estimated based on Eq. (53). However, as frequency
(i.e. the parameter 𝜔) is not well defined for an arbitrary loading type
and the determination of typical length 𝐿 is not straightforward in
higher dimensions, such an estimation is only approximate for problems
other than 1-D harmonic loading.
The SPH formulations of Biot’s model proposed in Section 4 have
been implemented in the open-source DualSPHysics C++ solver
(Domínguez et al., 2022). This section presents validation of the solver
through six poroelastic tests falling within both quasi-static and dynamic categories, as illustrated in Fig. 3. Although only small deformation is involved, the accurate reproduction of these tests is essential
for any numerical solver of strongly-coupled problems, which is rarely
reported in the current literature for the SPH methodology. It is also
worth noting that all the simulations are Lagrangian and hence the SPH
particles move in space with material deformation.
5.1. Quasi-static tests
5.1.1. 1-D consolidation
1-D consolidation is a classical problem in geotechnical engineering (Terzaghi, 1943; Verruijt, 2018). As illustrated in Fig. 4, an infinite
laterally-extended stratum of saturated poroelastic medium with height
𝐻 = 10 m is considered. The bottom boundary is fixed and impermeable, whereas the top surface is free to drain. At 𝑡 = 0 s, a
constant surcharge 𝜎𝑐 is applied to the upper surface, resulting in a
sudden increase in excess pore water pressure (EPWP) denoted by
𝑝𝑤. With time, the EPWP gradually dissipates which is accompanied
by settlement of the stratum, and finally another equilibrium state is
reached.
Terzaghi (1943) first derived an analytical solution for this problem, i.e. the so-called Terzaghi consolidation problem, based on an
uncoupled theory where the EPWP is governed by a pure diffusion
equation:
𝑝𝑤 =
𝜋
𝜎𝑐
∞
∑
𝑁=0
2𝑁 + 1
sin
[
(2𝑁 + 1)𝜋𝑧
2𝐻
]
exp
[
−
(2𝑁 + 1)2𝜋2
𝑇𝑣
]
(54)
where 𝐻 is the height of the stratum as illustrated in Fig. 4 and 𝑇𝑣 is
a dimensionless time factor defined as:
𝑇𝑣 =
𝑐𝑣
𝐻2
𝑡 (55)
where 𝑐𝑣 is the coefficient of consolidation taking the following form:
𝑐𝑣 =
𝑘
𝛾𝑓 𝑚𝑣
(56)
where 𝑚𝑣 = 1∕𝐸𝑐 is the coefficient of volume expansion. To facilitate the description of surface settlement, the following degree of
consolidation 𝑈 is usually introduced (Verruijt, 2018):
𝑈 =
𝑆 − 𝑆0
𝑆∞ − 𝑆0
= 1 −
𝜋2
∞
∑
𝑁=0
(2𝑁 + 1)2
exp
[
−
(2𝑁 + 1)2𝜋2
𝑇𝑣
]
(57)
where 𝑆, 𝑆0 and 𝑆∞ are the current, initial and final surface settlements, respectively. 𝑈 varies from 0 (at the moment of loading) to 1
(after consolidation has finished). Since 𝑆0 = 0 and 𝑆∞ = 𝐻𝜎𝑐𝑚𝑣, the
analytical solution for the time variation of surface settlement is:
𝑆 = 𝐻𝜎𝑐𝑚𝑣𝑈 (58)
In the poroelastic context, pore water pressure diffusion and solid
skeleton deformation are coupled and hence there is an extra coupling
term in the governing equation of EPWP (see e.g. Eq. (16) in the 𝒖-𝑝
version of Biot’s model). Cheng (2016) pointed out that such coupled
effects are negligible in the 1-D consolidation problem due to the
constant surcharge 𝜎𝑐. Consequently, the governing equation of EPWP
degrades to the pure diffusion equation in the uncoupled Terzaghi
theory and the corresponding poroelastic solution of EPWP is identical
to Eq. (54). However, the coefficient of consolidation, 𝑐𝑣, is differently
defined from Eq. (56), that is:
𝑐𝑣 =
𝑘
𝛾𝑓 (𝑚𝑣 + 𝑛∕𝐾𝑓 )
(59)
In this section, the poroelastic medium with its properties summarised in Table 1 is considered. The numerical model consists of a
column of 1 m width under the plane strain condition, as illustrated
in Fig. 4. The SPH particles are initially positioned on a Cartesian grid
with a spacing of d𝑝. A surface surcharge, 𝜎𝑐 = 5 kPa, is employed to
ensure a small deformation and hence validity of the analytical solution
expressed in Eq. (54). The gravitation field is set to zero and the body
force 𝒃 is ignored. Accordingly, the effective stress 𝝈′ is initialised to
zero while the EPWP has the same magnitude as 𝜎𝑐, i.e. 5 kPa. The
artificial viscosity, Eq. (46), with the coefficient 𝛼𝛱 = 0.01 is used
to maintain numerical stability. To mimic the 1-D loading condition,
periodic boundary conditions are applied to the two lateral sides of
the domain. The top and bottom boundary conditions are enforced
explicitly. Due to simple geometry of the problem, the boundary conditions can be applied directly without any coordinate transformations.

## Page 9

Fig. 5. EPWP (in Pa) distribution at representative times in the 1-D consolidation test using the 𝒖-𝒘-𝑝 model.
Summaries of the boundary conditions for 𝒖-𝒘-𝑝 and 𝒖-𝑝 models are
given below.
• 𝒖-𝒘-𝑝 model: For the SPH particles at the top surface, the traction
boundary condition is applied by modifying the effective stress
as 𝜎′
𝑧𝑧 = −𝜎𝑐 and 𝜎′
𝑥𝑧 = 𝜎′
𝑧𝑥 = 0, and the free-drainage boundary
condition is enforced by fixing the pore water pressure at zero,
i.e. 𝑝𝑤 = 0. For the SPH particles at the bottom surface, the noslip boundary condition is applied by setting the velocity of the
solid skeleton as 𝑢𝑥 = 𝑢𝑧 = 0, and the no-drainage boundary
condition is enforced via modifying the Darcy velocity (i.e. the
average relative velocity of seepage) as 𝑤𝑧 = 0.
• 𝒖-𝑝 model: The boundary conditions are the same as in the 𝒖𝒘-𝑝 model except that the no-drainage boundary condition is
applied by fixing the computed gradient of pore water pressure
as 𝜕𝑝𝑤∕𝜕𝑧 = 0. This modified value is then used in the particle
interaction whereby the time derivative of 𝑝𝑤 is calculated, as
expressed in Eq. (30). A similar way of enforcing the Neumann
boundary condition was employed by Schwaiger (2008) for SPH
modelling of thermal diffusion.
Fig. 5 shows the SPH particles coloured according to EPWP at
representative times in the numerical domain, which is obtained using
the 𝒖-𝒘-𝑝 model and a resolution of d𝑝 = 0.1 m. It can be seen the 1-D
loading condition is accurately reproduced due to the applied periodic
boundaries. At 𝑡 = 0 s, there is a sharp gradient in EPWP close to the top
surface. Similar to the 1-D transient wave propagation test discussed
later in Section 5.2.2, this would lead to stress wave propagation and
reflection in the numerical domain, and thereby oscillations in the
EPWP. In this quasi-static test, such oscillations are small and the
artificial damping, Eq. (47), is applied initially for a short time, e.g. 0.1
s, to suppress them.
Fig. 6 shows the isochrone of EPWP, as well as its comparison with
the analytical solution. The EPWP is normalised with respect to the
applied surcharge, i.e. 𝑝𝑤∕𝜎𝑐, and the depth is normalised against initial
height of the column, that is 𝑧∕𝐻. The entire time evolution process
is illustrated in Fig. 7, where time histories of EPWP at three points
and of the surface settlement are recorded and compared. Overall, the
Fig. 6. Isochrone of EPWP in the 1-D consolidation test.
results of 𝒖-𝒘-𝑝 and 𝒖-𝑝 models are close, which meets the expectation
for a slow phenomenon falling within Zone I in Fig. 3. Moreover, they
agree with the corresponding analytical reference solutions, thereby
demonstrating validity of the developed solver.
A spatial convergence test is also performed where the EPWP at
𝑇𝑣 = 0.31 is used to calculate the following 𝐿2(𝑝𝑤) error norm:
𝐿2(𝑝𝑤) =
√
√
√
√
√
∑
𝑖(𝑝SPH
𝑤𝑖 − 𝑝
Analytical
𝑤𝑖 )2
∑
𝑖(𝑝
Analytical
𝑤𝑖 )2
(60)
The obtained results are shown in Fig. 8. Specifically, the 𝒖-𝒘-𝑝 model
has an approximate second-order convergence rate at low resolutions,
whereas a limiting error is observed for fine resolutions. Such a behaviour occurs because the SPH interpolation is dominated by the

## Page 10

Fig. 7. Time history of (a) EPWP at three points and (b) surface settlement in the 1-D consolidation test.
smoothing error at low resolutions, whereas it is primarily affected
by the discretisation error at fine resolutions (Quinlan et al., 2006).
Another physical interpretation is that the quasi-static problem is overresolved. The average relative velocity of seepage, 𝒘, is a small quantity
in a quasi-static process. When a fine resolution is employed, the time
step is so small (see Section 4.2 for the constraints on time step size)
that the resulting increment in average relative displacement of pore
fluid is affected by machine error. It is noted that the 𝐿2(𝑝𝑤) error norm
has a local minima at d𝑝 = 0.2 m and Quinlan et al. (2006) ascribed this
phenomenon to the existence of gaps or overlaps in the support domain
of a particle.
On the other hand, the 𝒖-𝑝 model has an approximate first-order
convergence rate in the range of resolutions considered. This is attributed to the use of the Laplacian operator proposed by Schwaiger
(2008), i.e. Eq. (23). Moreover, no significant limiting error is observed,
because the 𝒖-𝑝 formulation (see Section 2.2) is a reduced model
whereby 𝒘 is not explicitly solved. These observations are expected
for classical SPH formulations using corrected operators (Quinlan et al.,
2006; Fatehi and Manzari, 2011), and thereby validity of the developed
solver is further demonstrated. It is worth mentioning that several
recent works are devoted to improve SPH to higher-order convergence (e.g. Oger et al., 2007; Nasar et al., 2021a,b), but their discussion
is beyond the scope of this paper.
5.1.2. Mandel’s problem
The Mandel’s problem (Mandel, 1953) is a quasi-static test ideal for
examining the distinct features of a coupled poroelastic response. As
illustrated in Fig. 9, the problem consists of a plane strain rectangular
poroelastic specimen of dimensions 2𝑎 × 2𝑏 sandwiched between two
rigid, impermeable plates with frictionless surfaces. At 𝑡 = 0 s, a
compressive force 2𝐹 is suddenly applied to the rigid plates, resulting
in the generation of a uniform EPWP, 𝑝𝑤0, throughout the specimen.
According to the Skempton effect (Skempton, 1954; Cheng, 2016), 𝑝𝑤0
is determined as:
𝑝𝑤0 =
2𝐵(1 + 𝜈𝑢)
𝐹
2𝑎
(61)
where 𝐵 is the Skempton pore pressure coefficient and 𝜈𝑢 is the
undrained bulk modulus. As explained in Section 2, the compressibility
of the solid component of porous materials such as soils is negligible
and this scenario is herein considered. Accordingly, 𝐵 is defined by:
𝐵 =
𝐾𝑓
𝑛𝐾𝑇 + 𝐾𝑓
(62)
The undrained Poisson’s ratio, 𝜈𝑢, can be determined from:
𝜈𝑢 =
3𝐾𝑢 − 2𝐺
2(3𝐾𝑢 + 𝐺)
(63)
where 𝐾𝑢 is the undrained bulk modulus defined as:
𝐾𝑢 = 𝐾 +
𝐾𝑓
𝑛
(64)
The initially generated EPWP, 𝑝𝑤0, then dissipates with time through
the left and right edges of the specimen which are exposed to atmosphere. In this process, the specimen becomes more compliant near the
edges due to reduction in EPWP, i.e. the poroelastic medium becomes

## Page 11

Fig. 8. Convergence rate of the 𝐿2(𝑝𝑤) error norm of the EPWP profile at 𝑇𝑣 = 0.31 in the 1-D consolidation test.
Fig. 9. Mandel’s problem and the numerical domain.
inhomogeneous with a harder core and softer edges. Since the plates
are rigid, there is a load transfer of compressive total stress towards the
centre region according to the compatibility requirement. As a result,
the EPWP in the centre region continues to rise above 𝑝𝑤0 before its
dissipation, and finally another equilibrium state is reached when the
EPWP has completely dissipated. This non-monotonic EPWP response
is a distinctive feature of the Biot’s theory compared to the uncoupled
Terzaghi theory (Terzaghi, 1943) where only the diffusion of EPWP is
captured. Cryer (1963) reported a similar response at the centre of a
poroelastic sphere subject to hydrostatic confining pressure.
Cheng and Detournay (1988) generalised the Mandel’s incompressible solution to the more general scenario of compressible constituents
with further extensions to account for the transverse isotropy of porous
materials (Abousleiman et al., 1996) and the dynamic loadings (Mehrabian
and Liu, 2021). According to Cheng and Detournay (1988), the analytical expressions of vertical displacement, 𝛥𝑧, and EPWP, 𝑝𝑤, are as
follows:
𝛥𝑧 =
[
−
𝐹(1 − 𝜈)
2𝐺𝑎
+
𝐹(1 − 𝜈𝑢)
𝐺𝑎
∞
∑
𝑁=1
sin 𝛽𝑁 cos 𝛽𝑁
𝛽𝑁 − sin 𝛽𝑁 cos 𝛽𝑁
exp
(
−
𝛽2
𝑁
𝑐𝑣𝑡
𝑎2
)]
𝑧
(65)
𝑝𝑤 =
2𝐹𝐵(1 + 𝜈𝑢)
3𝑎
∞
∑
𝑁=1
sin 𝛽𝑁
𝛽𝑁 − sin 𝛽𝑁 cos 𝛽𝑁
(
cos
𝛽𝑁 𝑥
𝑎
− cos 𝛽𝑁
)
exp
(
−
𝛽2
𝑁
𝑐𝑣𝑡
𝑎2
)
(66)
where 𝑐𝑣 is the generalised consolidation coefficient defined by:
𝑐𝑣 =
2𝑘𝐵2𝐺(1 − 𝜈)(1 + 𝜈𝑢)2
9𝛾𝑤(1 − 𝜈𝑢)(𝜈𝑢 − 𝜈)
(67)
and 𝛽𝑁 are solutions of the following characteristic equation:
tan 𝛽𝑁 =
1 − 𝜈
𝜈𝑢 − 𝜈
𝛽𝑁 (68)
In this section, the same poroelastic medium as in the 1-D consolidation test is considered, whose properties are summarised in Table 1, except that the hydraulic conductivity is one order of magnitude smaller,
i.e. 𝑘 = 0.0001 m∕s. The specimen dimensions are 𝑎 = 1 m and 𝑏 = 0.5 m,
and the applied force is 𝐹 = 5 kN. The numerical domain consists of a
quarter of the specimen due to its symmetry about the 𝑥-axis and 𝑧-axis,
as illustrated in Fig. 9. The SPH particles are initially positioned on a
Cartesian grid with a spacing of d𝑝 = 0.02 m. A gravity-free condition is
assumed and hence the body force 𝒃 is ignored. The poroelastic medium
can be regarded as being in an undrained state with 𝜈𝑢 = 0 in response

## Page 12

Fig. 10. EPWP (in Pa) distribution at representative times in the Mandel’s problem using the 𝒖-𝒘-𝑝 model.
Fig. 11. Profiles of EPWP along the 𝑥-axis in the Mandel’s problem.
to the sudden application of the compressive force 𝐹. Therefore, the
initial total stress state is: 𝜎𝑥𝑥 = 0, 𝜎𝑥𝑧 = 0 and 𝜎𝑧𝑧 = −𝐹∕𝑎. The
initial EPWP, 𝑝𝑤0, has been already given in Eq. (61). According to
the effective stress principle, Eq. (4), the corresponding initial effective
stress state is obtained as: 𝜎′
𝑥𝑥 = 𝑝𝑤0, 𝜎′
𝑥𝑧 = 0 and 𝜎′
𝑧𝑧 = −𝐹∕𝑎 + 𝑝𝑤0.
The artificial viscosity, Eq. (46), with the coefficient 𝛼𝛱 = 0.01 is used
to maintain numerical stability.
As shown in Fig. 9, the numerical domain has four boundaries. 𝛤1
models the rigid plate where all the boundary SPH particles have the
same vertical displacement and meanwhile the constraint of ∫
𝑎
0 𝜎𝑧𝑧d𝑥 =
−𝐹 is satisfied. Following the works of Phillips and Wheeler (2007),
Mikelić et al. (2014) and Torberntsson et al. (2018), this boundary
condition is herein enforced via assigning to the relevant particles the
analytical solution of the vertical velocity, 𝑢
Analytical
𝑧 , which is obtained

## Page 13

Fig. 12. Time history of (a) EPWP and (b) 𝐸𝑟𝑟(𝑝𝑤) at two points in the Mandel’s problem.
from the time derivative of 𝛥𝑧 expressed in Eq. (65). 𝛤2 is the free
surface through which the EPWP dissipates. 𝛤3 and 𝛤4 are symmetry
boundaries where drainage is not allowed. Since a small compressive
force of 𝐹 = 5 kN is considered, the change in geometry is negligible and therefore these boundary conditions can be directly enforced
without any coordinate transformations. For the 𝒖-𝒘-𝑝 model, the four
boundaries are given below:
• 𝛤1: The rigid, impermeable, frictionless plate where 𝑢𝑧 = 𝑢
Analytical
𝑧 ,
𝜎′
𝑥𝑧 = 0, 𝑤𝑧 = 0.
• 𝛤2: The free-surface boundary where 𝜎′
𝑥𝑥 = 0, 𝜎′
𝑥𝑧 = 0, 𝑝𝑤 = 0.
• 𝛤3: The horizontal symmetry boundary where 𝑢𝑧 = 0, 𝜎′
𝑥𝑧 = 0,
𝑤𝑧 = 0.
• 𝛤4: The vertical symmetry boundary where 𝑢𝑥 = 0, 𝜎′
𝑥𝑧 = 0,
𝑤𝑥 = 0.
The corresponding boundary conditions for the 𝒖-𝑝 model are the
same except that the no-drainage condition is applied by setting the
computed gradient of EPWP to zero, i.e. 𝑤𝑥 = 0 and 𝑤𝑧 = 0 are replaced
by 𝜕𝑝𝑤∕𝜕𝑥 = 0 and 𝜕𝑝𝑤∕𝜕𝑧 = 0, respectively.
Fig. 10 shows the SPH particles coloured according to the EPWP at
representative times obtained using the 𝒖-𝒘-𝑝 model. It is evident that
the dissipation of EPWP is along the horizontal direction, which verifies
the effectiveness of the applied boundary conditions. At 𝑡 = 0 s, a sharp
gradient in EPWP exists adjacent to 𝛤1. As in the 1-D consolidation test,
the induced stress oscillations are suppressed by applying the artificial
damping, Eq. (47), for a short time, e.g. 0.1 s.
Fig. 11 shows the profile of EPWP along the 𝑥-axis with respect to
distinct values of the dimensionless time factor 𝑇𝑣 defined below:
𝑇𝑣 =
𝑐𝑣
𝑎2
𝑡 (69)
where 𝑐𝑣 is the consolidation coefficient expressed in Eq. (67) and 𝑎 is
the half width of the specimen. It is evident that there is an initial EPWP
rise in the middle of the specimen at 𝑇𝑣 = 0.046. This process is better
illustrated in Fig. 12(a), where the time history of EPWP is recorded
at two points. Clearly, the EPWP at 𝑥∕𝑎 = 0 increases first to approximately 1.1𝑝𝑤0 before its dissipation. Such a non-monotonic EPWP
behaviour is the so-called Mandel–Cryer effect, which is a distinctive
characteristic of poroelastic responses. The phenomenon becomes insignificant at 𝑥∕𝑎 = 0.6, because the consolidation process is dominated
by the diffusion of EPWP close to the drainage boundary.
The quasi-static Mandel’s problem falls within Zone I in Fig. 3,
where both the 𝒖-𝒘-𝑝 and 𝒖-𝑝 models are applicable. Overall, the results
of the two models presented in Figs. 11 and 12(a) are close, and they
agree with the analytical solution, thereby further demonstrating the
validity of the developed solver for quasi-static poroelastic problems. It
is noted in Fig. 11 that, the simulated results exhibit large discrepancies
in the proximity of the right edge at 𝑇𝑣 = 0.009. The reason is that the
𝒖-𝒘-𝑝 model suffers from stronger stress oscillations as no stabilisation
measures are introduced for the Darcy velocity 𝒘 (see Eq. (27)). Such
oscillations are evident close to the drainage boundary where 𝒘 is
not negligible. Moreover, from 𝑇𝑣 = 0.15 to 0.99, a noticeable error
can be observed in the results of the 𝒖-𝑝 model, particularly close to
𝑥∕𝑎 = 0. As discussed in the 1-D consolidation test, this is attributed to
the numerical error associated with the Schwaiger’s Laplacian operator,
Eq. (23), adjacent to boundaries. The error is insignificant when the

## Page 14

Fig. 13. Effect of Poisson’s ratio on the time history of EPWP at 𝑥∕𝑎 = 0 in the Mandel’s problem.
Fig. 14. Steady state distribution of EPWP (in Pa) in the 1-D harmonic loading test with 𝑇 = 2 s using the 𝒖-𝒘-𝑝 model.
field is constant, e.g. 𝑇𝑣 = 0.009, 0.046 and 3.1. A quantification of the
numerical error is presented in Fig. 12(b). Specifically, the following
normalised error, 𝐸𝑟𝑟(𝑝𝑤), is computed for the time histories shown in
Fig. 12(a):
𝐸𝑟𝑟(𝑝𝑤) =
𝑝SPH
𝑤 − 𝑝
Analytical
𝑤
𝑝𝑤0
(70)
The 𝐸𝑟𝑟(𝑝𝑤) of both two models first increases before then declining
with time. Moreover, the 𝒖-𝑝 model has a larger error due to the
Schwaiger’s Laplacian operator, while the error of the 𝒖-𝒘-𝑝 model exhibits stronger oscillations because of the lack of stabilisation measures
in the governing equation for 𝒘.
The Mandel–Cryer effect is affected by properties of the porous
material. The influence of Poisson’s ratio, 𝜈, on this non-monotonic
response was studied by Cryer (1963), and it is also herein discussed
as a parametric study. In Fig. 13, the time history of EPWP at 𝑥∕𝑎 = 0
is shown with respect to three values of Poisson’s ratio. It can be seen
that the magnitude of EPWP rise decreases with the increase in 𝜈, that is
the Mandel–Cryer effect becomes insignificant when the solid skeleton
is near-incompressible.
5.2. Dynamic tests
5.2.1. 1-D harmonic loading
As mentioned earlier, the 1-D harmonic loading problem was first
studied by Zienkiewicz et al. (1980). In this section, the same poroelastic medium as in the 1-D consolidation test is considered, whose

## Page 15

Fig. 15. Envelope of EPWP at the steady state under different loadings.
properties are summarised in Table 1. The geometry and boundary
conditions are the same as in the 1-D consolidation problem shown
in Fig. 4, except that the constant surcharge 𝜎𝑐 is now replaced by
a periodic one. According to Zienkiewicz et al. (1980), 𝜎𝑐 takes the
following complex form:
𝜎𝑐 = ̄
𝜎𝑐 exp(𝑖𝜔𝑡) (71)
where 𝜔 is the angular frequency of the periodic surcharge. In SPH
modelling, only the real part of Eq. (71) is applied, that is:
𝜎𝑐 = 𝜎𝑐0 cos 𝜔𝑡 = 𝜎𝑐0 cos
2𝜋𝑡
𝑇
(72)
where 𝜎𝑐0 and 𝑇 are the amplitude and period of the periodic surcharge,
respectively. In this section, 𝜎𝑐0 = 5 kPa and 𝑇 ranging from 0.1 s to 50
s are employed.
The set-up of numerical model and the application of boundary
conditions are identical to the 1-D consolidation test. The gravitational
field is again set to zero and hence the body force 𝒃 is ignored.
However, the initial conditions are different whereby both effective
stress and pore water pressure are set to zero in the 1-D harmonic
loading test. In the temporal integration, the surcharge 𝜎𝑐 is updated
based on Eq. (72) and the time instant of simulation. For instance, in the
symplectic scheme, 𝑡 = 𝑡𝑛 in the predictor sub-step and 𝑡 = 𝑡𝑛+1∕2 in the
corrector sub-step, with 𝑛 denoting a specific time step. This updated
surcharge is then assumed to be constant over the time interval. The
artificial viscosity, Eq. (46), with the coefficient 𝛼𝛱 = 0.1 is used to
maintain numerical stability.
Fig. 14 shows the particles coloured according to the steady-state
EPWP within a half loading period, which is obtained using the 𝒖𝒘-𝑝 model and a resolution of d𝑝 = 0.1 m. A quantitative comparison is shown in Fig. 15 where the steady-state envelopes of EPWP
are compared with the corresponding analytical solutions. The EPWP
is normalised with respect to amplitude of the periodic surcharge,
i.e. 𝑝𝑤∕𝜎𝑐0. It can be seen that, when the period of harmonic loading
is large, the problem degrades to the quasi-static process discussed
in Section 5.1.1. This corresponds to 𝑇 = 10 s to 50 s in Fig. 15
where the envelopes are monotonic. For the extreme case of 𝑇 = 50
s, the consolidation process dominates such that the maximum EPWP
is significantly smaller than 𝜎𝑐0. On the other hand, the loading with a
small 𝑇 causes severe inertial effects. As a result, the envelope becomes
non-monotonic due to the co-existence of a drainage layer close to the
top surface and an undrained layer near the bottom. It is interesting
to note that, for the extremely dynamic loading with 𝑇 = 0.1 s, the
maximum EPWP can be greater than 4𝜎𝑐0. Overall, in the range of
period tested, the results of 𝒖-𝒘-𝑝 and 𝒖-𝑝 models are close, which meets
the expectation for a moderate speed process, i.e. Zone II in Fig. 3.
Moreover, they agree with the corresponding analytical solutions and
therefore the validity of the developed solver is verified.
The surface surcharge expressed in Eq. (72) has a magnitude of 𝜎𝑐0
at 𝑡 = 0 s, whereas the numerical model is initialised to a state where
both effective stress and pore water pressure are zero. As can be understood from the 1-D transient wave propagation test in Section 5.2.2,
the sudden application of 𝜎𝑐 induces stress oscillations in the numerical
domain due to stress wave propagation and reflection. However, the
analytical solutions presented by Zienkiewicz et al. (1980) only correspond to the steady state. To damp out such oscillations and therefore
to quickly reach the steady state, e.g. the results shown in Figs. 14–
15, the artificial damping expressed in Eq. (47) is applied initially for
a short time period, e.g. 1.0 s. It is worth mentioning that the use
of artificial damping, Eq. (47), in this dynamic loading test requires
empirical identification of the damping coefficient 𝜇𝑑, especially when
the period is at the two extremes. On the one hand, when the period
is large, e.g. 𝑇 = 50 s in Fig. 15, a long simulation time is needed
to ensure several loading periods and therefore to minimise the effect
of artificial damping. On the other hand, when the period is small,
e.g. 𝑇 = 0.1 s in Fig. 15, both the magnitude and time of artificial
damping should be carefully tuned to ensue that, at the end of its
application, the numerical model is close to the corresponding steady

## Page 16

Fig. 16. Time history of EPWP of a point at 𝑧∕𝐻 = 0.1 with respect to two different loading based on the 𝒖-𝒘-𝑝 model.
state. This explains the slight errors in the EPWP envelopes for 𝑇 = 50
s and 0.1 s presented in Fig. 15.
The transition from the initial transient to the final steady state is
shown in Fig. 16, where the time evolutions of EPWP at a point of
𝑧∕𝐻 = 0.1 under 𝑇 = 0.5 s and 5 s are recorded. Since the responses of
the 𝒖-𝒘-𝑝 and 𝒖-𝑝 models are similar, only the results of the 𝒖-𝒘-𝑝 model
are displayed to keep the presentation clear. It can be observed that the
normalised amplitudes of these two time histories are smaller than 1
and the reason can be understood by referring to the corresponding
case in Fig. 15 with 𝑧∕𝐻 = 0.1. Clearly, the SPH solution exhibits
initial oscillations which quickly transitions to close agreement with
the analytical solution.
It can be observed in Fig. 15 that, when the period is small, e.g. 𝑇 =
0.1 s, a noticeable error exists close to the top surface in the results
of the 𝒖-𝒘-𝑝 model. This is because there is a sharp EPWP gradient
in this region and the SPH formulation for the governing equation of
Darcy velocity, Eq. (27), lacks stabilisation measures. It is found the
simulation results can be improved by using a finer resolution. For
instance, Fig. 17 shows how the EPWP envelope under 𝑇 = 0.2 s gets
closer to the analytical solution when increasing the resolution.
Moreover, the analytical solution for the deformation field is also
available in the work of Zienkiewicz et al. (1980). A comparison is
therefore made by comparing the surface settlement under 𝑇 = 2 s, as
shown in Fig. 19. Both the 𝒖-𝒘-𝑝 and 𝒖-𝑝 models accurately reproduce
the deformation field, although some oscillations are observed during
the initial transients.
A spatial convergence test is also performed for this dynamic loading problem. The steady-state EPWP envelope under the periodic loading with 𝑇 = 2 s is used to compute the 𝐿2(𝑝𝑤) error norm expressed in
Eq. (60). Results are shown in Fig. 18 where the convergence rates of
the 𝒖-𝒘-𝑝 and 𝒖-𝑝 models are approximately 1.4. As already discussed
in Section 5.1.1, this is expected for classical SPH formulations using
corrected operators, and consequently validity of the developed solver
is further demonstrated. Note that, compared to the results of 1-D
consolidation shown in Fig. 8, the 𝒖-𝒘-𝑝 model no longer suffers from a
limiting error in the range of tested resolutions, since the Darcy velocity
𝒘 is not a small quantity in this dynamic loading process. Moreover,
the 𝒖-𝒘-𝑝 model has a larger 𝐿2(𝑝𝑤) error norm and since the steadystate EPWP suffers from slightly greater oscillations due to lack of
stabilisation measures in the governing equation for the Darcy velocity,
i.e. Eq. (27).
5.2.2. 1-D transient wave propagation
The 1-D harmonic loading test presented in Section 5.2.1 only
focuses on the steady-state conditions, whereby the relevant initial
transient responses are damped out by means of the artificial damping,
Eq. (47), as illustrated in Fig. 16. This section examines transient
behaviours of the developed SPH solver through the 1-D transient wave
propagation problem which was analytically studied by Verruijt (2009)
and Carter et al. (2015). In deriving the analytical solutions, Verruijt
(2009) employed the Fourier analysis technique while (Carter et al.,
2015) used the Laplace transforms. The problem corresponds to a fast
phenomenon falling within Zone III in Fig. 3, where the 𝒖-𝒘-𝑝 and
𝒖-𝑝 models behave differently. The problem was numerically studied
by Sabetamal et al. (2016) and Monforte et al. (2019) using FEM.
However, none of coupled SPH models have performed this test in
current literature.
Following (Carter et al., 2015), the properties of the considered
poroelastic medium are summarised in Table 2. The geometry of the
problem is identical to the 1-D consolidation test illustrated in Fig. 4,
except that the height of the strata, 𝐻, now becomes 1 m. Accordingly,
the numerical domain consists of a soil column with 0.1 m width.
The bottom boundary is the same as in the 1-D consolidation test (see
Section 5.1.1), whereas the top boundary is different. Specifically, a
constant water pressure 𝜎𝑐 = 5 kPa is applied to the top surface at
𝑡 = 0 s, and therefore the top boundary conditions are summarised as:
𝜎′
𝑥𝑧 = 𝜎′
𝑧𝑥 = 𝜎′
𝑧𝑧 = 0 and 𝑝𝑤 = 𝜎𝑐. These boundary conditions are applied
explicitly. Moreover, as in Sabetamal et al. (2016) and Monforte et al.
(2019), 𝜎𝑐 is enforced at a uniform rate over a period of 1 × 10−5 s
and thereafter held constant with time, to reduce stress oscillations.
Periodic boundary conditions are applied to the two lateral sides of
the numerical domain to reproduce the 1-D loading condition. The
gravitational field is set to zero and the body force 𝒃 is ignored. The
initial conditions for effective stress and pore water pressure are hence
both zero. The artificial viscosity, Eq. (46), with the coefficient 𝛼𝛱 = 0.5
is used to maintain numerical stability.
Figs. 20 and 21 show the particles coloured according to the EPWP
at representative times obtained using the 𝒖-𝒘-𝑝 and 𝒖-𝑝 models, respectively. For this severe dynamic test, a fine resolution is needed to
obtain high quality results. The results in Figs. 20 and 21 employ the
resolution d𝑝 = 0.002 m and the hydraulic conductivity 𝑘 = 0.001 m∕s.
It can be observed from Fig. 20 that the application of 𝜎𝑐 induces two
distinct waves in the numerical domain, the existence of which has

## Page 17

Fig. 17. Effect of resolution on the steady-state EPWP envelope predicted by the 𝒖-𝒘-𝑝 model under 𝑇 = 0.2 s.
Fig. 18. Convergence rate of the 𝐿2(𝑝𝑤) error norm of the EPWP envelope at the steady state in the 1-D harmonic loading test with 𝑇 = 1 s.
Table 2
Properties of the poroelastic medium in the 1-D transient wave propagation test.
Parameter Symbol Value Unit
Porosity 𝑛 0.4 –
Density of pore water 𝜌𝑓 1000 kg/m3
Density of solid phase 𝜌𝑠 2650 kg/m3
Young’s modulus of solid skeleton 𝐸 5 GPa
Poisson’s ratio of solid skeleton 𝜈 0 –
Hydraulic conductivity 𝑘 0.001 and 0.0001 m/s
Bulk modulus of pore water 𝐾𝑓 2 GPa
been demonstrated both analytically (e.g. Biot, 1956a,b; Verruijt, 2009;
Cheng, 2016) and experimentally (e.g. Chandler, 1981; Kelder and
Smeulders, 1997; Bouzidi and Schmitt, 2009). According to Verruijt
(2009), the pore water and the solid skeleton move in phase for the
first wave, i.e. the fast wave, whereas they move essentially out of
phase for the second wave, i.e. the Biot’s slow wave. The expressions
for velocities of the fast and slow waves, 𝑐1 and 𝑐2, are:
𝑐1 =
√
𝐸𝑐 + 𝑄
𝜌
(73)
𝑐2 =
√
𝑛𝐸𝑐𝑄
[(1 − 𝑛)𝑄 + 𝐸𝑐]𝜌𝑓
(74)
However, the corresponding results of the 𝒖-𝑝 model shown in Fig. 21
only have one wave, because it is a reduced model whereby the inertial
effects related to 𝒘 are ignored.
A more quantitative analysis is then performed. In Fig. 22, the
profiles of EPWP with respect to the representative time instants shown
in Figs. 20–21 are compared with the analytical solution. Note that, the

## Page 18

Fig. 19. Time history of surface settlement under 𝑇 = 2 s.
Fig. 20. EPWP (in Pa) distribution at representative times in the 1-D transient wave propagation test using the 𝒖-𝒘-𝑝 model.
ringing phenomenon in the analytical data is simply an artefact resulting from numerical inversion of the Laplace transforms (Carter et al.,
2015). Moreover, the analytical solution corresponds to the case of an
infinitely deep layer, and therefore it only provides a rational reference
before the waves arrive at the bottom boundary, e.g. approximately
before 𝑡 = 0.00045 s in Fig. 22. After arrival of the incident wave, the
SPH model exhibits wave reflection as the applied boundary is rigid,
i.e. 𝑡 = 0.0005 s in Fig. 22. The absorbing boundary condition presented
in Section 4.3.1 can be extended to reduce such a wave reflection
and thereby to approximately simulate an infinite domain. Overall, the
results of the 𝒖-𝒘-𝑝 model agree with the analytical solution, despite
the slight numerical diffusion and dispersion across the wave front. On
the other hand, the 𝒖-𝑝 model is incapable of reproducing the physics
of this extremely dynamic process where the inertial effects related to
𝒘 play a vital role. This is expected for a fast phenomenon in Zone III
of Fig. 3.
As mentioned earlier in this section, the pore water and the solid
skeleton move essentially out of phase for the Biot’s slow wave, and
consequently it is strongly damped (Verruijt, 2009). The attenuation of
the Biot’s slow wave can be observed in Fig. 22. To magnify this effect,
another case is run with the hydraulic conductivity being one order
of magnitude smaller, i.e. 𝑘 = 0.0001 m∕s, and the results are shown
in Fig. 23. It can be observed that the Biot’s slow wave is completely
damped out at approximately 𝑡 = 0.0002 s, after which the results of

## Page 19

Fig. 21. EPWP (in Pa) distribution at representative times in the 1-D transient wave propagation test using the 𝒖-𝑝 model.
Fig. 22. Profile of EPWP at representative times in the 1-D transient wave propagation test with 𝑘 = 0.001 m∕s.
the 𝒖-𝒘-𝑝 and 𝒖-𝑝 models match with each other above the front of the
first wave. This can be interpreted that the inertial effects related to 𝒘
disappear and the loading state moves to Zone II of Fig. 3 where the 𝒖-𝑝
model is applicable. However, the results of the 𝒖-𝑝 model still have a
large numerical diffusion across the first wave front. To show the entire
time evolution process of the cases presented in Figs. 22–23, the time
histories of EPWP at a point of 𝑧∕𝐻 = 0.8, are recorded and compared
with the corresponding analytical solution, as shown in Fig. 24. Clearly,
two waves pass the recording point when 𝑘 = 0.001 m∕s, whereas only
one wave is recorded under 𝑘 = 0.0001 m∕s. Note again that the ringing
phenomenon in analytical data is simply an artefact.
5.2.2.1. Performance of the absorbing boundary. In Figs. 22 and 23,
wave reflections can be observed at 𝑡 = 0.0005 s as the applied bottom
boundary is rigid. To better illustrate this process, the time history of
EPWP at 𝑧∕𝐻 = 0.8 under 𝑘 = 0.001 m∕s is recorded for a longer

## Page 20

Fig. 23. Profile of EPWP at representative times in the 1-D transient wave propagation test with 𝑘 = 0.0001 m∕s.
Fig. 24. Time history of EPWP at 𝑧∕𝐻 = 0.8 in the 1-D transient wave propagation test.
time up to 𝑡 = 0.01 s, as shown in Fig. 25(a). It is evident that
the EPWP oscillates due to the propagation of stress waves. Since the
analytical solution is available, this test case is ideal for examining the
performance of an absorbing boundary.
The absorbing boundary condition introduced in Section 4.3.1 is
applied to the bottom of the domain. The effect of 𝛿 on the time history
of EPWP at 𝑧∕𝐻 = 0.8 under 𝑘 = 0.001 m∕s is illustrated in Fig. 25(a).
Note that, only the results of the 𝒖-𝒘-𝑝 model are presented herein,
because the 𝒖-𝑝 model cannot capture the physics of the current test
case. The performance of the absorbing boundary condition for the 𝒖𝑝 model will be examined later in Sections 5.2.3 and 5.2.4. It can be
observed that the EPWP still oscillates in the considered time interval
when 𝛿 = 0.1 m, whereas such oscillations are greatly reduced in the
result with 𝛿 = 1 m. Moreover, the time history finally agrees with
the analytical solution for infinitely deep layer when 𝛿 = 10 m. However, a large 𝛿 results in an absorbing boundary with small stiffness,
which may creep under sustained loading. To illustrate such effects,
the 𝑧-displacement of the bottom boundary is recorded, as shown in
Fig. 25(b). Clearly, the displacement increases with the increase in 𝛿.
It is worth mentioning that, although the magnitude of displacement is
small in Fig. 25(b) due to small loading and time interval, this would
not be the case under large and sustained loadings. These observations
demonstrate the validity of the developed standard viscous boundary
condition for saturated poroelastic medium. Compared to the artificial

## Page 21

Fig. 25. Time history of (a) EPWP at 𝑧∕𝐻 = 0.8 and (b) 𝑧-displacement of the bottom boundary in the 1-D transient wave propagation test with respect to distinct values of the
virtual viscous layer thickness.
damping, Eq. (47), applying absorbing boundary conditions is a more
physically consistent approach for dynamic loading problems.
5.2.3. 2-D consolidation
The test cases examined thus far mostly involve 1-D deformations, whereby numerical stability is sufficiently maintained by the
artificial viscosity expressed in Eq. (46). However, due to the nearincompressible characteristic of saturated porous materials, a stronglycoupled solver may face the so-called volumetric locking issue under
2-D and 3-D deformations, which is typically manifested by a noisy
stress field (Navas et al., 2016; Coombs et al., 2018; Iaconeta et al.,
2019; Moutsanidis et al., 2020; Bisht et al., 2021). Under such a circumstance, using the artificial viscosity alone fails to ensure numerical
stability as it does not address the fundamental cause.
To illustrate the existence of volumetric locking issue and to demonstrate the effectiveness of the proposed volumetric strain diffusion
technique (see Section 4.4.3), this section examines the developed SPH
solver through the 2-D consolidation test. Fig. 26 shows the problem
geometry where a plane-strain rectangular poroelastic stratum of dimensions 20 m (width) × 10 m (height) is loaded by a frictionless
strip foundation of 6 m width. The bottom and two sides of the
domain are subject to free-slip and no-drainage conditions, whereas the
top boundary is the free surface. Due to the symmetry, the relevant
numerical domain comprises only half of the stratum. Moreover, the
strip foundation is idealised as a uniformly distributed stress, denoted
as 𝜎𝑐(𝑡).
The same poroelastic medium as in the 1-D consolidation is considered whose properties are summarised in Table 1. The SPH particles
are initially positioned on a Cartesian grid with a spacing of d𝑝 = 0.2
m. Moreover, following (Blanc and Pastor, 2012), the strip foundation
is impermeable and 𝜎𝑐(𝑡) is a ramp loading defined by:
𝜎𝑐(𝑡) =
{
10𝜎𝑐0𝑡, 𝑡 ≤ 0.1 s
𝜎𝑐0, 𝑡 > 0.1 s
(75)
where 𝜎𝑐0 = 5 kPa is employed. The gravitational field is set to zero and
hence the body force 𝒃 is ignored. Accordingly, the initial conditions of
effective stress and EPWP are both zero. The numerical domain has
five boundaries, as shown in Fig. 26. For the 𝒖-𝒘-𝑝 model, a summary
of these boundary conditions is given below.
• 𝛤1: The impermeable, frictionless foundation where 𝜎′
𝑥𝑧 = 0,
𝜎𝑧𝑧 = −𝜎𝑐(𝑡) and 𝑤𝑧 = 0.
• 𝛤2: The free-surface boundary where 𝜎′
𝑥𝑧 = 0, 𝜎′
𝑧𝑧 = 0 and 𝑝𝑤 = 0.

## Page 22

Fig. 26. 2-D consolidation problem and numerical set-up.
Fig. 27. Contour of EPWP (in kPa) in the 2-D consolidation test using both the 𝒖-𝒘-𝑝 and 𝒖-𝑝 models with 𝑘 = 0.001 m∕s.
• 𝛤3: The vertical free-slip wall boundary where 𝑢𝑥 = 0, 𝜎′
𝑥𝑧 = 0,
𝑤𝑥 = 0.
• 𝛤4: The horizontal free-slip wall boundary where 𝑢𝑧 = 0, 𝜎′
𝑥𝑧 = 0,
𝑤𝑧 = 0.
• 𝛤5: The vertical symmetry boundary where 𝑢𝑥 = 0, 𝜎′
𝑥𝑧 = 0,
𝑤𝑥 = 0.
The corresponding boundary conditions for the 𝒖-𝑝 model are the same,
except for the enforcement of the no-drainage boundary condition.
Specifically, instead of setting 𝑤𝑥 = 0 or 𝑤𝑧 = 0, the no-drainage
condition is applied by modifying 𝜕𝑝𝑤∕𝜕𝑥 = 0 or 𝜕𝑝𝑤∕𝜕𝑧 = 0 (see the
discussion in Section 5.1.1). The artificial viscosity, Eq. (46), with the
coefficient 𝛼𝛱 = 0.1 is employed to maintain numerical stability.
The first column of Fig. 27 shows the EPWP contour at three
time instants obtained using the 𝒖-𝒘-𝑝 model. It is clear that stress
oscillations are insignificant at 𝑡 = 0.1 s, i.e. the end of the ramp
loading, but they become dominant later with the dissipation of EPWP.
The volumetric strain diffusion term, Eq. (49), is then applied and the
results are shown in the second column of Fig. 27. Although the EPWP
field is smoother compared to the original results, slight oscillations
still exist. The discharge diffusion term, Eq. (51), is therefore further
applied and the resulting EPWP field is smooth without any oscillations,
as illustrated by the third column of Fig. 27. The reason for the need
of two diffusion terms is because the 𝒖-𝒘-𝑝 model consists of two
volumetric quantities, ∇ ⋅ 𝒖 and ∇ ⋅ 𝒘, which both tend to induce the
volumetric locking issue when approaching the incompressible limit.
On the contrary, only the volumetric strain diffusion term, Eq. (49),
is needed in the 𝒖-𝑝 model as there is only one volumetric quantity,
∇ ⋅ 𝒖. The original results of the 𝒖-𝑝 model is shown in the fourth
column of Fig. 27. Although this model does not suffer from significant
volumetric locking effects in the current case, the volumetric strain
diffusion term is also applied to examine its impact on the simulation
results, as illustrated by the last column of Fig. 27. It is evident that the
use of the volumetric strain diffusion term does not produce significant
side effects. Overall, the results of the 𝒖-𝒘-𝑝 and 𝒖-𝑝 models are close,
which meets the expectation that both the two models are applicable
for this moderate (during the ramp loading) to quasi-static (during the
EPWP dissipation) process.

## Page 23

Fig. 28. Effect of particle distribution on EPWP at 𝑡 = 15 s in the 2-D consolidation test using the 𝒖-𝒘-𝑝 model.
Fig. 29. Time history of EPWP at (a) point A and (b) point B in the 2-D consolidation test.

## Page 24

Fig. 30. 2-D transient wave propagation problem and the applied impulse force.
As discussed in Section 4.4.3, volumetric locking takes place when
the material being modelled is near-incompressible. In FEM studies,
volumetric locking is attributed to the inability of the element to
exactly represent an isochoric motion (Belytschko et al., 2013). Although no element is used in an SPH interpolation, a similar issue
would exist. This is especially the case when particles are uniformly
distributed whereby the corresponding SPH interpolation resembles
a central differencing scheme, due to the anti-symmetric property
of kernel derivative. The issue can be mitigated when particles are
non-uniformly distributed. To examine the influence of particle distribution, the 2-D consolidation test is re-run using the 𝒖-𝒘-𝑝 model
and a slightly randomised initial particle distribution. The disordered
particles are distributed over a Cartesian grid with an initial particle
spacing equal to 0.2 m and then adding a random displacement value
calculated from a uniform distribution over the range 0 to 0.1 m.
The obtained results at 𝑡 = 15 s are shown in Fig. 28, together
with the corresponding results from a uniform initial particle distribution. It is clear from the top row of Fig. 28 that the EPWP
field away from the loading boundary is smoother when particles are
non-uniformly distributed. However, a noisy EPWP field can still be
observed close to the loading boundary, thereby demonstrating the
existence of volumetric locking issue. Therefore, the proposed volumetric strain diffusion technique is needed under a non-uniform particle
distribution and its effectiveness is demonstrated again in the second
row of Fig. 28.
Although spatial smoothness of the EPWP field is ensured by the
volumetric strain diffusion technique, temporal oscillations still exist.
This is attributed to propagation and reflection of stress waves, which
are more complicated compared to the 1-D scenario discussed in Section 5.2.2. Fig. 29 illustrates such oscillations where the time history of
EPWP is recorded at the point A and B shown in Fig. 26. Clearly, the
EPWP starts to oscillate at the end of the ramp loading. The absorbing
boundary presented in Section 4.3.1 is then introduced to examine its
performance in this 2-D problem. Specifically, the bottom boundary,
i.e. 𝛤4 shown in Fig. 26, is chosen as the absorbing boundary. Accordingly, the original no-slip and no-drainage conditions are replaced with
the damping stresses expressed in Eqs (42)–(44), that is 𝜎′
𝑧𝑧 = 𝜎′𝑎𝑏
𝑧𝑧 ,
𝜎′
𝑥𝑧 = 𝜎′𝑎𝑏
𝑥𝑧 , 𝑝𝑤 = 𝑝𝑎𝑏
𝑤 . The influence of the virtual viscous layer thickness,
𝛿, has been displayed in Fig. 25 and 𝛿 = 2 m is herein employed. It
is evident from the results shown in Fig. 29 that the standard viscous
boundary performs well in reducing the stress oscillations. Moreover,
it does not affect the physical process as the results match with the
ones using rigid boundaries. The results of the 𝒖-𝒘-𝑝 and 𝒖-𝑝 models
are close at point B (see Fig. 29(b)), whereas a noticeable discrepancy
exists at point A (see Fig. 29(a)), possibly due to the numerical error
associated with the Schwaiger’s Laplacian operator (see Eq. (23)).
It is worth mentioning that different 2-D consolidation tests can be
found in the literature (see e.g. Sabetamal et al., 2016; Lian et al.,
2023). The reference solutions for these tests are typically numerical
results obtained using alternative methods. In addition to the pore pressure field discussed above, the deformation field is also a crucial factor
in validating the effectiveness of a strongly-coupled solver. However,
since a reference solution is not available in Blanc and Pastor (2012),
a relevant comparison cannot be made here.
5.2.4. 2-D transient wave propagation
The 2-D transient wave propagation test is an extension of the corresponding 1-D problem presented in Section 5.2.2 and it is performed
in this section to further examine the SPH solver in a transient process.
This problem was first studied by Breuer (1999) and later by Markert
et al. (2010) and Monforte et al. (2019) using the FEM approach.
Recently, several coupled particle finite element models have been
used to reproduce this test case (Wang et al., 2021; Yuan et al., 2022;
Jin and Yin, 2022). It is worth mentioning that the models of Breuer
(1999), Markert et al. (2010) and Wang et al. (2021) only considered a
special case of saturated porous media where both the solid and fluid
phases are incompressible. The compressibility of the constituents are
accounted for in the remaining works and also in this paper.
Fig. 30 illustrates the problem geometry where a plane-strain rectangular poroelastic stratum of dimensions 21 m (width) × 10 m (height)
is considered. The two lateral sides of the domain are free-slip and nodrainage, whereas the bottom side is no-slip and no-drainage. The top
boundary is the free surface, where a uniform stress, 𝜎𝑐(𝑡), is applied
across a 1 m width and takes the form of a stress pulse expressed by:
𝜎𝑐(𝑡) =
{
𝜎𝑐0 sin(25𝜋𝑡), 𝑡 ≤ 0.04 s
0, 𝑡 > 0.04 s
(76)
where 𝜎𝑐0 = 100 kPa is employed, as illustrated in Fig. 30. In the 1-
D problem discussed in Section 5.2.2, the applied force generates two
types of body waves inside the domain, i.e. the fast wave and the Biot’s
slow wave. However, an extra elastic surface wave is expected in this
2-D scenario, which is the so-called Rayleigh wave typically manifested
by an elliptic particle movement or ground rolling during earthquake
events.
Following (Markert et al., 2010), the properties of the saturated
porous medium are summarised in Table 3, unless stated otherwise. The
SPH particles are initially positioned on a Cartesian grid with d𝑝 = 0.1
m. A gravity-free condition is assumed and hence the body force 𝒃 is
ignored. Accordingly, the initial conditions of effective stress and EPWP
are both zero. The numerical domain has four types of boundaries, as
shown in Fig. 30. For the 𝒖-𝒘-𝑝 model, a summary of the boundary
conditions is given below:

## Page 25

Fig. 31. Contour of EPWP (in kPa) in the 2-D consolidation test using both the 𝒖-𝒘-𝑝 and 𝒖-𝑝 models with 𝑘 = 0.0001 m∕s.
Table 3
Properties of the poroelastic medium in the 2-D transient wave propagation test.
Parameter Symbol Value Unit
Porosity 𝑛 0.33 –
Density of pore water 𝜌𝑓 1000 kg/m3
Density of solid phase 𝜌𝑠 2000 kg/m3
Young’s modulus of solid skeleton 𝐸 14.5 MPa
Poisson’s ratio of solid skeleton 𝜈 0.3 –
Hydraulic conductivity 𝑘 0.01 m/s
Bulk modulus of pore water 𝐾𝑓 2.2 GPa
• 𝛤1: The traction boundary where 𝜎′
𝑥𝑧 = 0, 𝜎′
𝑧𝑧 = −𝜎𝑐(𝑡) and 𝑝𝑤 = 0.
• 𝛤2: The free-surface boundary where 𝜎′
𝑥𝑧 = 0, 𝜎′
𝑧𝑧 = 0 and 𝑝𝑤 = 0.
• 𝛤3: The vertical free-slip and no-drainage wall boundary where
𝑢𝑥 = 0, 𝜎′
𝑥𝑧 = 0, 𝑤𝑥 = 0.
• 𝛤4: The horizontal no-slip and no-drainage wall boundary where
𝑢𝑥 = 0, 𝑢𝑧 = 0, 𝑤𝑧 = 0.
The relevant boundary conditions for the 𝒖-𝑝 model are the same,
except for the enforcement of the no-drainage boundary condition (see
Section 5.2.3). The artificial viscosity, Eq. (46), with the coefficient
𝛼𝛱 = 0.2 is employed to maintain numerical stability.
Before comparing with the reference solutions, the existence of
volumetric locking issue in this transient process is examined first.
Fig. 31 displays the EPWP contours for the left half of the domain at two
time instants under 𝑘 = 0.0001 m∕s. It is clear from the first column of
the figure that the 𝒖-𝒘-𝑝 model suffers from severe volumetric locking
issue. This is mitigated by applying simultaneously the volumetric
strain, Eq. (49), and the discharge, Eq. (51), diffusion terms, as shown
by the second column of Fig. 31. However, as in the 2-D consolidation
test (see Section 5.2.3), the results of the 𝒖-𝑝 model do not exhibit
significant volumetric locking effects in the considered scenario, that is
the last column of Fig. 31. Consequently, only the results of the 𝒖-𝒘-𝑝
model with volumetric strain diffusions applied are hereafter presented.
The existence of temporal oscillations due to rigid boundary conditions is then investigated. For the case presented in Fig. 31, the
time history of EPWP is recorded at the point B (see Fig. 30). As
shown in Fig. 32(a), the results of both the 𝒖-𝒘-𝑝 and 𝒖-𝑝 models
exhibit oscillations. To enable comparison with reference solutions, the
absorbing boundary presented in Section 4.3.1 is therefore introduced
to eliminate such oscillations. In Section 5.2.3, only the bottom edge
of the domain, i.e. 𝛤4 in Fig. 26, is chosen as the absorbing boundary.
According to Fig. 29, stabilisation of the domain takes a long time,
up to approximately 5 s, as stress wave reflections still occur on the
remaining boundaries. To more efficiently eliminate the oscillations, all
the three wall boundaries, i.e. 𝛤3 and 𝛤4 shown in Fig. 30, are chosen
as the absorbing boundary. Moreover, since only a stress impulse is
involved in the current case, the absorbing boundary will not exhibit
the significant creeping effect shown in Fig. 25(b). Therefore, the
thickness of the virtual viscous layer can be set to infinity, i.e. 𝛿 → ∞.
As shown in Fig. 32(a), the resulting absorbing boundary condition
performs well. Consequently, only the results with absorbing boundary
applied are shown in the following comparison with the reference
solutions.
It is noted that the results of the 𝒖-𝒘-𝑝 and 𝒖-𝑝 models match
in Fig. 32(a). This is because, for a low permeability, the inertial
effects related to the relative motion of pore water is negligible and
hence both the 𝒖-𝒘-𝑝 and 𝒖-𝑝 models are applicable, i.e. Zone II in
Fig. 3. Fig. 32(b) shows the results where the hydraulic conductivity
is increased by one order of magnitude to 𝑘 = 0.001 m∕s. Discrepancies
between the two models are evident. Specifically, the two models
exhibit different damping behaviour when using the rigid boundary,
and they predict slightly different peak values under the absorbing
boundary. Such discrepancies become even more apparent when the
hydraulic conductivity is increased to 𝑘 = 0.01 m∕s, as demonstrated in
Fig. 32(c). Under this circumstance, the problem falls within Zone III
in Fig. 3 where only the 𝒖-𝒘-𝑝 model is applicable.
The oscillations in Fig. 32(a) are also analysed analytically. Based on
Eqs (73) and (74), the calculated speeds for Biot’s fast and slow waves

## Page 26

Fig. 32. Time history of EPWP at point B with (a) 𝑘 = 0.0001 m∕s, (b) 𝑘 = 0.001 m∕s and (c) 𝑘 = 0.01 m∕s in the 2-D wave propagation test.
Fig. 33. Distribution of EPWP (in kPa) at representative times in the 2-D wave propagation test using the 𝒖-𝒘-𝑝 model.
are approximately 2000 m/s and 97 m/s, respectively. The shortest
propagation path for the arrival of the first reflection wave from the
loading boundary is approximately 20 m. This corresponds to arrival
times of 0.01 s for the fast wave and 0.18 s for the slow wave. At 𝑡 = 0.01
s, Fig. 32(a) shows a slight oscillation in the time history of EPWP
when using the rigid boundary, which demonstrates validity of the
numerical model. However, as the problem is 2-D, there are multiple
wave reflections taking place and such a simple analytical examination
is incapable of explaining the remaining oscillations. It is therefore left
to be investigated in further studies.
Next, qualitative comparisons with the reference solutions are made.
In the work of Jin and Yin (2022), the distribution of EPWP at four
representative times under 𝑘 = 0.01 m∕s was reported. The 𝒖-𝒘-𝑝 model
is used to reproduce this test and the relevant results are shown in
Fig. 33. For the same case, Wang et al. (2021) presented the distribution
of total displacement at four representative times. The corresponding
results of the 𝒖-𝒘-𝑝 model are displayed in Fig. 34. Note that, in these
two figures, the deformation is scaled in both directions by a factor of
250 and 500, respectively. It is evident that there is a surface wave
propagating towards the two sides. Overall, the results of the 𝒖-𝒘-𝑝

## Page 27

Fig. 34. Distribution of total displacement (in mm) at representative times in the 2-D wave propagation test using the 𝒖-𝒘-𝑝 model.
Fig. 35. Particle disorder close to the traction boundary 𝛤1 at 𝑡 = 0.1 s. Particles are coloured according to EPWP (in kPa) and deformation is scaled by a factor of 500 in both
directions.
model qualitatively match with the reference solutions. Slight particle
disorder can be observed close to the middle of the top surface. Fig. 35
shows a zoom-in view at 𝑡 = 0.1 s. The disorder is in the proximity of the
two edges of 𝛤1 where a sharp deformation gradient exists. This may be
attributed to either the direct application of stress boundary conditions
without any coordinate transformation or the presence of zero-energy
modes. However, it is important to note that the deformation field
depicted is magnified for visibility and the actual effects of such a
disorder are negligible.
A quantitative comparison with the FEM solution of Markert et al.
(2010) is then performed. Specifically, the time history of EPWP at
point B (see Fig. 30) and the in-plane motion of point A are recorded
and compared. Prior to presenting the results, it is important to discuss
the constraints on the time step size. Section 4.2 has outlined the
relevant details for the 𝒖-𝒘-𝑝 and 𝒖-𝑝 models, respectively. In the
considered scenario, a large permeability of 𝑘 = 0.01 m∕s is employed,
making the constraint specified in Eq. (40) very restrictive. As a result,
the 𝒖-𝑝 model becomes more computationally demanding than the 𝒖-𝒘-𝑝 model, which is why the following results utilise different resolutions
for each model. In Fig. 36, a spatial convergence test is displayed. The
time history of EPWP approaches to the FEM solution with increasing
resolution in both models, especially at the peak values. The in-plane
motion predicted by the 𝒖-𝒘-𝑝 model matches with the FEM solution.
However, a discrepancy is observed close to the end of the transient
process, whereby the SPH model predicts a slightly larger displacement.
The relevant results of the 𝒖-𝑝 model are converging, while they do not
agree well with the reference solution. This may be due to the fact that
the considered problem involves a highly dynamic transient process
and hence the simplifying assumptions made in deriving the 𝒖-𝑝 model
are inappropriate. Moreover, a notable discrepancy exists in the time
history of EPWP at around 0.07 to 0.1 s. This is found to be attributed
to the artificial viscosity. In Fig. 37, the results with respect to different
values of the tuning parameter, 𝛼𝛱 (see Eq. (46)), are shown. Note that
the finest resolutions in Fig. 36 are employed. Clearly, the discrepancy
gradually disappears with decreasing 𝛼𝛱 . Overall, the results of the 𝒖𝒘-𝑝 and 𝒖-𝑝 models match the FEM solution which employs a different
formulation and stabilisation measures.
6. Conclusions
New SPH formulations for the 𝒖-𝒘-𝑝 and 𝒖-𝑝 versions of Biot’s model
have been presented. The formulations entail explicit enforcement of

## Page 28

Fig. 36. Influence of resolution on the time history of EPWP at point B (left) and the in-plane motion of point A (right) using (a) the 𝒖-𝒘-𝑝 model and (b) the 𝒖-𝑝 model.
free-surface conditions, thereby enabling the application of various
types of boundary conditions essential for modelling strongly-coupled
processes in saturated porous media. The correct function of explicitlyenforced conditions is ensured by employing the mixed kernel and
gradient correction proposed by Bonet and Lok (1999) where the partition of unity is guaranteed. The improved absorbing boundary is then
introduced, providing a robust solution for modelling dynamic loading
scenarios. As a result of the near-incompressibility of saturated porous
media, the volumetric-locking issue arises in the 2-D problems studied
in this paper. To address this, a countermeasure named volumetric
strain diffusion is proposed, which is based on the well-established
B-bar method and density diffusion technique.
The proposed formulations have undergone rigorous validation
against six classical poroelastic problems, encompassing both quasistatic and dynamic ranges. The convergence study reveals that the
formulations display a convergence rate intermediate between first and
second order, consistent with expectations for SPH interpolation. The
𝒖-𝑝 formulation has small error close to domain boundary and this is
attributed to the error in the corrected Laplacian operator. Both 𝒖-𝒘-𝑝 and 𝒖-𝑝 formulations effectively capture slow to moderate loading
phenomena, while exhibiting distinct responses under conditions of
high dynamic loading. This is attributed to the 𝒖-𝑝 model being a significantly reduced version, limiting its ability to accurately capture the
inertial effects of pore fluid. The introduced absorbing boundary excels
in absorbing incident waves without altering the underlying physics
of the problems, thereby proving to be an efficient tool for dynamic
problems. For higher-dimension problems, the 𝒖-𝑝 formulation exhibits
no noticeable volumetric locking within the tested parameter range.
In contrast, the 𝒖-𝒘-𝑝 model demonstrates a significant volumetric
locking issue, evident from the noisy pore pressure field. The proposed
volumetric strain diffusion approach successfully mitigates this issue.
The simulation results align well with the reference solutions, validating the proposed formulations, boundary conditions, and stabilisation
measures. This lays a solid foundation for SPH modelling of stronglycoupled problems involving large deformation and inelastic material
behaviour.

## Page 29

Fig. 37. Influence of artificial viscosity on the time history of EPWP at point B (left) and the in-plane motion of point A (right) using (a) the 𝒖-𝒘-𝑝 model and (b) the 𝒖-𝑝 model.
CRediT authorship contribution statement
C. Yao: Writing – original draft, Visualization, Validation, Software,
Methodology, Formal analysis, Data curation, Conceptualization. G.
Fourtakas: Writing – review & editing, Supervision, Project administration, Methodology, Investigation, Formal analysis, Conceptualization. B.D. Rogers: Writing – review & editing, Supervision, Project
administration, Methodology, Investigation, Formal analysis, Conceptualization. D. Lombardi: Writing – review & editing, Supervision,
Project administration, Methodology, Investigation, Formal analysis,
Conceptualization.
Declaration of competing interest
The authors declare that they have no known competing financial interests or personal relationships that could have appeared to
influence the work reported in this paper.
Acknowledgements
The authors would like to acknowledge the financial support from
the China Scholarship Council and The University of Manchester.
Appendix A
In this appendix, the detailed derivation of the two simplified
versions of Biot’s model, as discussed in this paper, from the full
formulation is presented. By introducing the density relation 𝜌 = 𝑛𝜌𝑓 +
(1 − 𝑛)𝜌𝑠 and the effective stress principle 𝝈 = 𝝈′ − 𝑝𝑰, and by assuming
the incompressibility of the solid component, i.e. 𝛼 = 1 and the validity
of linear Darcy’s law, i.e. 𝑹 =
𝛾𝑓
𝑘
𝒘, Eqs (5)–(7) become:
∇⋅𝝈′
−∇𝑝−
[
𝑛𝜌𝑓 + (1 − 𝑛)𝜌𝑠
] d𝒖
d𝑡
−𝜌𝑓
(
d𝒘
d𝑡
+ 𝒘 ⋅ ∇𝒘
)
+
[
𝑛𝜌𝑓 + (1 − 𝑛)𝜌𝑠
]
𝒃 = 0
(A.1)
−∇𝑝 −
𝛾𝑓
𝑘
𝒘 − 𝜌𝑓
d𝒖
d𝑡
−
𝜌𝑓
𝑛
(
d𝒘
d𝑡
+ 𝒘 ⋅ ∇𝒘
)
+ 𝜌𝑓 𝒃 = 0 (A.2)
∇ ⋅ 𝒘 + ∇ ⋅ 𝒖 +
𝑄
d𝑝
d𝑡
= 0 (A.3)
In deriving the 𝒖-𝒘-𝑝 formulation, the convective term 𝒘 ⋅ ∇𝒘 in the
above equations is ignored, and hence Eqs (A.1) and (A.2) reduce to:
∇ ⋅ 𝝈′
− ∇𝑝 −
[
𝑛𝜌𝑓 + (1 − 𝑛)𝜌𝑠
] d𝒖
d𝑡
− 𝜌𝑓
d𝒘
d𝑡
+
[
𝑛𝜌𝑓 + (1 − 𝑛)𝜌𝑠
]
𝒃 = 0 (A.4)
−∇𝑝 −
𝛾𝑓
𝑘
𝒘 − 𝜌𝑓
d𝒖
d𝑡
−
𝜌𝑓
𝑛
d𝒘
d𝑡
+ 𝜌𝑓 𝒃 = 0 (A.5)

## Page 30

In Eqs (A.3)–(A.5), there are three primary variables, namely 𝒖, 𝒘 and
𝑝. To advance the simulation in time using an explicit time-stepping
scheme, the total time derivatives of these three variables should be
obtained. This can be done straightforwardly by solving for
d𝒖
d𝑡
,
d𝒘
d𝑡
and
d𝑝
d𝑡
from Eqs (A.3)–(A.5) and the results are displayed in Eqs (12)–(14).
In deriving the 𝒖-𝑝 formulation, the total time derivative of 𝒘 is
further ignored. As a result, Eqs (A.4)–(A.5) reduce to:
∇ ⋅ 𝝈′
− ∇𝑝 −
[
𝑛𝜌𝑓 + (1 − 𝑛)𝜌𝑠
] d𝒖
d𝑡
+
[
𝑛𝜌𝑓 + (1 − 𝑛)𝜌𝑠
]
𝒃 = 0 (A.6)
−∇𝑝 −
𝛾𝑓
𝑘
𝒘 − 𝜌𝑓
d𝒖
d𝑡
+ 𝜌𝑓 𝒃 = 0 (A.7)
From Eq. (A.7), 𝒘 can be expressed as:
𝒘 =
𝑘
𝛾𝑓
(
−∇𝑝 − 𝜌𝑓
d𝒖
d𝑡
+ 𝜌𝑓 𝒃
)
(A.8)
Substituting Eq. (A.8) into Eq. (A.3) yields:
∇ ⋅
𝑘
𝛾𝑓
(
−∇𝑝 − 𝜌𝑓
d𝒖
d𝑡
+ 𝜌𝑓 𝒃
)
+ ∇ ⋅ 𝒖 +
𝑄
d𝑝
d𝑡
= 0 (A.9)
According to Zienkiewicz and Shiomi (1984), the term
d𝒖
d𝑡
is further
ignored. Moreover, as discussed by Blanc and Pastor (2012), ∇ ⋅ 𝒃 is
zero except in cases such as centrifuge testing machine, and hence the
body force term is also omitted. As a result, Eq. (A.9) becomes:
−
𝑘
𝛾𝑓
∇2
𝑝 + ∇ ⋅ 𝒖 +
𝑄
d𝑝
d𝑡
= 0 (A.10)
In Eqs (A.6) and (A.10), there are two primary variables, i.e. 𝒖 and
𝑝. Similarly, their total derivatives can be obtained by solving for
d𝒖
d𝑡
and
d𝑝
d𝑡
from the these two equations, and the results are shown in
Eqs (15)–(16).
Data availability
No data was used for the research described in the article.
References
Abousleiman, Y., Cheng, A.H.-D., Cui, L., Detournay, E., Roegiers, J.-C., 1996. Mandel’s
problem revisited. Géotechnique 46 (2), 187–195.
Antuono, M., Colagrossi, A., Marrone, S., Molteni, D., 2010. Free-surface flows solved
by means of SPH schemes with numerical diffusive terms. Comput. Phys. Comm.
181 (3), 532–549.
Asai, M., Fujioka, S., Saeki, Y., Morikawa, D.S., Tsuji, K., 2023. A class of secondderivatives in the Smoothed Particle Hydrodynamics with 2nd-order accuracy and
its application to incompressible flow simulations. Comput. Methods Appl. Mech.
Engrg. 415, 116203.
Belytschko, T., Liu, W.K., Moran, B., Elkhodary, K., 2013. Nonlinear Finite Elements
for Continua and Structures. John Wiley & Sons, London, UK.
Biot, M.A., 1941. General theory of three-dimensional consolidation. J. Appl. Phys. 12
(2), 155–164.
Biot, M.A., 1956a. Theory of propagation of elastic waves in a fluid-saturated porous
solid. I. Low frequency range. J. Acoust. Soc. Am. 28 (2), 168–178.
Biot, M.A., 1956b. Theory of propagation of elastic waves in a fluid-saturated porous
solid. II. Higher frequency range. J. Acoust. Soc. Am. 28 (2), 179–191.
Bisht, V., Salgado, R., Prezzi, M., 2021. Simulating penetration problems in incompressible materials using the material point method. Comput. Geotech. 133,
103593.
Blanc, T., Pastor, M., 2012. A stabilized fractional step, Runge-Kutta Taylor SPH
algorithm for coupled problems in geomechanics. Comput. Methods Appl. Mech.
Engrg. 221, 41–53.
Bonet, J., Lok, T.-S., 1999. Variational and momentum preservation aspects of Smooth
Particle Hydrodynamic formulations. Comput. Methods Appl. Mech. Engrg. 180
(1–2), 97–115.
Bouzidi, Y., Schmitt, D.R., 2009. Measurement of the speed and attenuation of the Biot
slow wave using a large ultrasonic transmitter. J. Geophys. Res.: Solid Earth 114
(B08201).
Breuer, S., 1999. Quasi-static and dynamic behavior of saturated porous media with
incompressible constituents. Transp. Porous Media 34, 285–303.
Brookshaw, L., 1985. A method of calculating radiative heat diffusion in particle
simulations. Publ. Astron. Soc. Aust. 6 (2), 207–210.
Bui, H.H., Fukagawa, R., 2009. A first attempt to solve soil-water coupled problem by
SPH. J. Terramech. 29, 33–38.
Bui, H.H., Fukagawa, R., 2013. An improved SPH method for saturated soils and
its application to investigate the mechanisms of embankment failure: Case of
hydrostatic pore-water pressure. Int. J. Numer. Anal. Methods Geomech. 37 (1),
31–50.
Bui, H.H., Fukagawa, R., Sako, K., Ohno, S., 2008. Lagrangian meshfree particles
method (SPH) for large deformation and failure flows of geomaterial using elastic–
plastic soil constitutive model. Int. J. Numer. Anal. Methods Geomech. 32 (12),
1537–1570.
Bui, H.H., Nguyen, G.D., 2017. A coupled fluid-solid SPH approach to modelling flow
through deformable porous media. Int. J. Solids Struct. 125, 244–264.
Bui, H.H., Nguyen, G.D., 2021. Smoothed particle hydrodynamics (SPH) and its
applications in geomechanics: From solid fracture to granular behaviour and
multiphase flows in porous media. Comput. Geotech. 138, 104315.
Carter, J.P., Sabetamal, H., Nazem, M., Sloan, S.W., 2015. One-dimensional test
problems for dynamic consolidation. Acta Geotech. 10 (1), 173–178.
Chalk, C.M., Pastor, M., Peakall, J., Borman, D., Sleigh, P., Murphy, W., Fuentes, R.,
2020. Stress-Particle Smoothed Particle Hydrodynamics: An application to the
failure and post-failure behaviour of slopes. Comput. Methods Appl. Mech. Engrg.
366, 113034.
Chandler, R., 1981. Transient streaming potential measurements on fluid-saturated
porous structures: An experimental verification of Biot’s slow wave in the
quasi-static limit. J. Acoust. Soc. Am. 70 (1), 116–121.
Cheng, A.H.-D., 2016. Poroelasticity. Springer, Switzerland.
Cheng, A.H.-D., Detournay, E., 1988. A direct boundary element method for plane strain
poroelasticity. Int. J. Numer. Anal. Methods Geomech. 12 (5), 551–572.
Colagrossi, A., Antuono, M., Le Touzé, D., 2009. Theoretical considerations on the
free-surface role in the smoothed-particle-hydrodynamics model. Phys. Rev. E. 79
(5), 056701.
Coombs, W.M., Charlton, T.J., Cortis, M., Augarde, C.E., 2018. Overcoming volumetric
locking in material point methods. Comput. Methods Appl. Mech. Engrg. 333, 1–21.
Cowin, S.C., 1999. Bone poroelasticity. J. Biomech. 32 (3), 217–238.
Cryer, C.W.A., 1963. A comparison of the three-dimensional consolidation theories of
Biot and Terzaghi. Q. J. Mech. Appl. Math. 16 (4), 401–412.
de Souza Neto, E.A., Perić, D., Dutko, M., Owen, D.R.J., 1996. Design of simple low
order finite elements for large strain analysis of nearly incompressible solids. Int.
J. Solids Struct. 33 (20–22), 3277–3296.
Domínguez, J.M., Fourtakas, G., Altomare, C., Canelas, R.B., Tafuni, A., García-
Feal, O., Martínez-Estévez, I., Mokos, A., Vacondio, R., Crespo, A.J., et al., 2022.
DualSPHysics: from fluid dynamics to multiphysics problems. Comput. Part. Mech.
9, 867–895.
Fatehi, R., Manzari, M.T., 2011. Error estimation in smoothed particle hydrodynamics
and a new scheme for second derivatives. Comput. Math. Appl. 61 (2), 482–498.
Gholami Korzani, M., Galindo-Torres, S.A., Scheuermann, A., Williams, D.J., 2018. SPH
approach for simulating hydro-mechanical processes with large deformations and
variable permeabilities. Acta Geotech. 13, 303–316.
He, X., Liang, D.F., Bolton, M.D., 2018. Run-out of cut-slope landslides: mesh-free
simulations. Géotechnique 68 (1), 50–63.
Hughes, T.J.R., 1980. Generalization of selective integration procedures to anisotropic
and nonlinear media. Internat. J. Numer. Methods Engrg. 15 (9), 1413–1418.
Iaconeta, I., Larese, A., Rossi, R., Oñate, E., 2019. A stabilized mixed implicit material
point method for non-linear incompressible solid mechanics. Comput. Mech. 63 (6),
1243–1260.
Jassim, I., Stolle, D., Vermeer, P., 2013. Two-phase dynamic analysis by material point
method. Int. J. Numer. Anal. Methods Geomech. 37 (15), 2502–2522.
Jeng, D.-S., Ye, J.-H., Zhang, J.-S., Liu, P.-F., 2013. An integrated model for the
wave-induced seabed response around marine structures: Model verifications and
applications. Coast. Eng. 72, 1–19.
Jin, Y.-F., Yin, Z.-Y., 2022. Two-phase PFEM with stable nodal integration for large
deformation hydromechanical coupled geotechnical problems. Comput. Methods
Appl. Mech. Engrg. 392, 114660.
Kafaji, I.K.A., 2013. Formulation of a Dynamic Material Point Method (MPM) for
Geomechanical Problems (Ph.D. thesis). University of Stuttgart.
Kelder, O., Smeulders, D.M.J., 1997. Observation of the Biot slow wave in
water-saturated Nivelsteiner sandstone. Geophysics 62 (6), 1794–1796.
Li, W., Wei, C., 2018. Stabilized low-order finite elements for strongly coupled
poromechanical problems. Internat. J. Numer. Methods Engrg. 115 (5), 531–548.
Lian, Y., Bui, H.H., Nguyen, G.D., Haque, A., 2023. An effective and stabilised (upl) SPH framework for large deformation and failure analysis of saturated porous
media. Comput. Methods Appl. Mech. Engrg. 408, 115967.
Liang, H., He, S., Chen, Z., Liu, W., 2019. Modified two-phase dilatancy SPH model
for saturated sand column collapse simulations. Eng. Geol. 260, 105219.
Lind, S.J., Stansby, P.K., 2016. High-order Eulerian incompressible smoothed particle
hydrodynamics with transition to Lagrangian free-surface motion. J. Comput. Phys.
326, 290–311.
Liu, G.R., Liu, M.B., 2003. Smoothed Particle Hydrodynamics: A Meshfree Method.
World Scientific, Singapore.
Lysmer, J., Kuhlemeyer, R.L., 1969. Finite dynamic model for infinite media. J. Eng.
Mech. Div. 95 (4), 859–877.

## Page 31

Mandel, J., 1953. Consolidation des sols (étude mathématique). Géotechnique 3 (7),
287–299.
Markert, B., Heider, Y., Ehlers, W., 2010. Comparison of monolithic and splitting
solution schemes for dynamic porous media problems. Internat. J. Numer. Methods
Engrg. 82 (11), 1341–1383.
Marrone, S., Antuono, M., Colagrossi, A., Colicchio, G., Le Touzé, D., Graziani, G.,
2011. 𝛿-SPH model for simulating violent impact flows. Comput. Methods Appl.
Mech. Engrg. 200 (13–16), 1526–1542.
Mehrabian, A., Liu, C., 2021. Mandel’s problem reloaded. J. Sound Vib. 492, 115785.
Mieremet, M.M.J., Stolle, D.F., Ceccato, F., Vuik, C., 2016. Numerical stability for modelling of dynamic two-phase interaction. Int. J. Numer. Anal. Methods Geomech.
40 (9), 1284–1294.
Mikelić, A., Wang, B., Wheeler, M.F., 2014. Numerical convergence study of iterative
coupling for coupled flow and geomechanics. Comput. Geosci. 18 (3), 325–341.
Monaghan, J.J., 1992. Smoothed particle hydrodynamics. Annu. Rev. Astron. Astrophys.
30 (1), 543–574.
Monaghan, J.J., 2005. Smoothed particle hydrodynamics. Rep. Progr. Phys. 68 (8),
1703–1759.
Monforte, L., Navas, P., Carbonell, J.M., Arroyo, M., Gens, A., 2019. Low-order
stabilized finite element for the full Biot formulation in soil mechanics at finite
strain. Int. J. Numer. Anal. Methods Geomech. 43 (7), 1488–1515.
Morikawa, D.S., Asai, M., 2022. Soil-water strong coupled ISPH based on u-w-p
formulation for large deformation problems. Comput. Geotech. 142, 104570.
Morris, J.P., Fox, P.J., Zhu, Y., 1997. Modeling low Reynolds number incompressible
flows using SPH. J. Comput. Phys. 136 (1), 214–226.
Moutsanidis, G., Koester, J.J., Tupek, M.R., Chen, J.-S., Bazilevs, Y., 2020. Treatment of
near-incompressibility in meshfree and immersed-particle methods. Comput. Part.
Mech. 7 (2), 309–327.
Nasar, A.M.A., Fourtakas, G., Lind, S.J., King, J.R.C., Rogers, B.D., Stansby, P.K., 2021a.
High-order consistent SPH with the pressure projection method in 2-D and 3-D. J.
Comput. Phys. 444, 110563.
Nasar, A.M.A., Fourtakas, G., Lind, S.J., Rogers, B.D., Stansby, P.K., King, J.R.C.,
2021b. High-order velocity and pressure wall boundary conditions in Eulerian
incompressible SPH. J. Comput. Phys. 434, 109793.
Navas, P., López-Querol, S., Yu, R.C., Li, B., 2016. B-bar based algorithm applied to
meshfree numerical schemes to solve unconfined seepage problems through porous
media. Int. J. Numer. Anal. Methods Geomech. 40 (6), 962–984.
Oger, G., Doring, M., Alessandrini, B., Ferrant, P., 2007. An improved SPH method:
Towards higher order convergence. J. Comput. Phys. 225 (2), 1472–1492.
Osorno, M., Steeb, H., 2016. Smoothed Particle Hydrodynamics modelling of poroelastic
media. Proc. Appl. Math. Mech. 16 (1), 469–470.
Pastor, M., Haddad, B., Sorbino, G., Cuomo, S., Drempetic, V., 2009. A depth-integrated,
coupled SPH model for flow-like landslides and related phenomena. Int. J. Numer.
Anal. Methods Geomech. 33 (2), 143–172.
Pastor, M., Yague, A., Stickle, M.M., Manzanal, D., Mira, P., 2018. A two-phase SPH
model for debris flow propagation. Int. J. Numer. Anal. Methods Geomech. 42 (3),
418–448.
Peng, C., Wu, W., Yu, H.S., Wang, C., 2015. A SPH approach for large deformation
analysis with hypoplastic constitutive model. Acta Geotech. 10 (6), 703–717.
Phillips, P.J., Wheeler, M.F., 2007. A coupling of mixed and continuous Galerkin finite
element methods for poroelasticity I: the continuous in time case. Comput. Geosci.
11 (2), 131–144.
Quinlan, N.J., Basa, M., Lastiwka, M., 2006. Truncation error in mesh-free particle
methods. Internat. J. Numer. Methods Engrg. 66 (13), 2064–2085.
Randles, P.W., Libersky, L.D., 1996. Smoothed particle hydrodynamics: some recent
improvements and applications. Comput. Methods Appl. Mech. Engrg. 139 (1–4),
375–408.
Sabetamal, H., Nazem, M., Sloan, S.W., Carter, J.P., 2016. Frictionless contact formulation for dynamic analysis of nonlinear saturated porous media based on the mortar
method. Int. J. Numer. Anal. Methods Geomech. 40 (1), 25–61.
Schwaiger, H.F., 2008. An implicit corrected SPH formulation for thermal diffusion
with linear free surface boundary conditions. Internat. J. Numer. Methods Engrg.
75 (6), 647–671.
Skempton, A.W., 1954. The pore-pressure coefficients A and B. Géotechnique 4 (4),
143–147.
Soga, K., Alonso, E., Yerro, A., Kumar, K., Bandara, S., 2016. Trends in largedeformation analysis of landslide mass movements with particular emphasis on
the material point method. Géotechnique 66 (3), 248–273.
Song, Y., Jun, S., Na, Y., Kim, K., Jang, Y., Wang, J., 2022. Geomechanical Challenges
during Geological CO2 Storage: A Review. Chem. Eng. J. 140968.
Sulsky, D., Chen, Z., Schreyer, H.L., 1994. A particle method for history-dependent
materials. Comput. Methods Appl. Mech. Engrg. 118 (1–2), 179–196.
Sulsky, D., Zhou, S.-J., Schreyer, H.L., 1995. Application of a particle-in-cell method
to solid mechanics. Comput. Phys. Comm. 87 (1–2), 236–252.
Terzaghi, K., 1943. Theoretical Soil Mechanics. John Wiley & Sons, New York, USA.
Torberntsson, K., Stiernström, V., Mattsson, K., Dunham, E.M., 2018. A finite difference
method for earthquake sequences in poroelastic solids. Comput. Geosci. 22 (5),
1351–1370.
Verruijt, A., 2009. An Introduction to Soil Dynamics. Springer, Dordrecht, Netherlands.
Verruijt, A., 2018. An Introduction to Soil Mechanics. Springer, Switzerland.
Violeau, D., 2012. Fluid Mechanics and the SPH Method: Theory and Applications.
Oxford University Press, Oxford, UK.
Violeau, D., Rogers, B.D., 2016. Smoothed particle hydrodynamics (SPH) for free-surface
flows: past, present and future. J. Hydraul. Res. 54 (1), 1–26.
Wang, L., Zhang, X., Zhang, S., Tinti, S., 2021. A generalized Hellinger-Reissner
variational principle and its PFEM formulation for dynamic analysis of saturated
porous media. Comput. Geotech. 132, 103994.
Wendland, H., 1995. Piecewise polynomial, positive definite and compactly supported
radial functions of minimal degree. Adv. Comput. Math. 4 (1), 389–396.
Xu, R., Stansby, P., Laurence, D., 2009. Accuracy and stability in incompressible SPH
(ISPH) based on the projection method and a new approach. J. Comput. Phys. 228
(18), 6703–6725.
Yuan, W.-H., Zhu, J.-X., Liu, K., Zhang, W., Dai, B.-B., Wang, Y., 2022. Dynamic analysis
of large deformation problems in saturated porous media by smoothed particle
finite element method. Comput. Methods Appl. Mech. Engrg. 392, 114724.
Zhang, W., Zheng, H., Jiang, F., Wang, Z., Gao, Y., 2019. Stability analysis of soil slope
based on a water-soil-coupled and parallelized Smoothed Particle Hydrodynamics
model. Comput. Geotech. 108, 212–225.
Zhao, Y., Choo, J., 2020. Stabilized material point methods for coupled large deformation and fluid flow in porous materials. Comput. Methods Appl. Mech. Engrg. 362,
112742.
Zienkiewicz, O.C., Chan, A.H.C., Pastor, M., Schrefler, B.A., Shiomi, T., 1999.
Computational Geomechanics. John Wiley & Sons, West Sussex, UK.
Zienkiewicz, O.C., Chang, C.T., Bettess, P., 1980. Drained, undrained, consolidating and
dynamic behaviour assumptions in soils. Géotechnique 30 (4), 385–395.
Zienkiewicz, O.C., Shiomi, T., 1984. Dynamic behaviour of saturated porous media:
the generalized Biot formulation and its numerical solution. Int. J. Numer. Anal.
Methods Geomech. 8 (1), 71–96.

## Page 32

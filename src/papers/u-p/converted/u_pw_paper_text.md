# Converted text: A Coupled u-pw SPH Formulation

- Source PDF: `src/papers/u-p/a-coupled-u-p-sph-formulation-for-hydromechanical-modeling-of-retrogressive-landslides-and-comparison-with-a-penalty-based-approach.pdf`
- Pages: 31
- Tool: PyMuPDF text extraction


## Page 1

International Journal for Numerical and Analytical Methods in Geomechanics 
RESEARCH ARTICLE
A Coupled u –pw SPH Formulation for Hydromechanical 
Modeling of Retrogressive Landslides and Comparison With 
a Penalty-Based Approach 
Enrique M. del Castillo1 
Ronaldo I. Borja1 
Alomir H. Fávero Neto2 
1 Department of Civil and Environmental Engineering, Stanford University, Stanford, California, USA 
2 Department of Civil and Environmental Engineering, 
Bucknell University, Lewisburg, Pennsylvania, USA 
Correspondence: Alomir H. Fávero Neto ( alomir.favero@bucknell.edu) 
Received: 18 November 2025 
Revised: 26 March 2026 
Accepted: 30 March 2026 
Keywords: penalty method | retrogressive landslides | smoothed particle hydrodynamics | solid–fluid coupling | spreads and flowslides | u –p formulation 
ABSTRACT 
We present a strongly coupled displacement ( 𝒖 ) and pore water pressure ( 𝑝𝑤 ) version of the Biot–Zienkiewicz ( 𝒖 – 𝑝𝑤 ) equations in 
saturated porous media for the meshfree Lagrangian smoothed particle hydrodynamics (SPH) method. We propose two distinct 
formulations using a single particle layer, two-phase framework, one based on a one-step solution of a pressure Poisson 
equation (PPE formulation) and another allowing compressibility of the fluid resulting in an explicit rate equation for the pore 
pressure (PR formulation). We discuss both formulations from a numerical perspective and verify them using benchmark problems 
from poroelasticity, including Cryer’s problem, as well as using undrained triaxial tests, where we additionally compare the results 
against a weakly coupled penalty-based undrained framework for SPH. Beyond the formulations, the focus of this work is on 
modeling retrogressive landslides in saturated sensitive clays, which are particularly destructive due to their extended runout and 
fast movement. Our simulations emphasize performing strongly coupled hydromechanical modeling even for quasi-undrained 
conditions, contrary to the predominant practices in the literature, as the structural features of the landslides change significantly 
when pore pressure dissipation and coupled effects are included. Additionally, spreads develop under a greater variety of slope 
conditions as opposed to the more fluidized flowslide type of retrogressive landslides captured when solely considering undrained 
behavior. Lastly, we apply the PR formulation to explore how slope steepness and height influence deformation modes and 
apply the framework to simulate the 1994 Sainte-Monique landslide, recreating the topographic profile, runout, and deformation 
features post-failure. 
1 
Introduction 
The intrinsic strong coupling between the solid skeleton and pore 
fluid in saturated porous media is necessary to explain and model 
a wide range of (quasi)-static and dynamic geohazard-related 
processes, such as subsidence, pore fluid induced fault weak- 
ening, soil liquefaction, scouring, rainfall-triggered landslides, 
multiphase flows and debris flows, as well as earthen and tailings 
embankment and dam failures. Due to the increasing frequency 
and intensity of extreme weather events due to global climate 
change, the likelihood of rainfall-driven geohazards such as land- 
slides, mudflows, or flowslides is increasing [ 28 ]. Comprehending 
landslide potential runout distances, final deformation configu- 
ration, and impact forces is paramount given the considerable 
damage (economic losses of $1–3.6 billion USD annually in the 
United States [ 2 ]) and fatalities (600 + deaths per year globally on 
average [ 96 ]) caused by landslides with some individual disasters 
responsible for as many as tens of thousands of deaths. At the 
© 2026 John Wiley & Sons Ltd. 
International Journal for Numerical and Analytical Methods in Geomechanics , 2026; 0:1–31 
https://doi.org/10.1002/nag.70322
1 of 31

## Page 2

same time, as rehabilitation of aging infrastructure and design 
of new infrastructure is increasingly conducted up to safe-to-fail 
rather than fail–safe standards [ 43 ], knowledge of the expected 
range of possible post-failure behavior, particularly of dams and 
levees, is required [ 49 ]. 
The field of poromechanics, namely the mathematical theory 
describing the mechanics of coupled saturated porous media, 
owes much to the seminal work of Maurice Biot, who expanded 
upon the concept of effective stress and formalized the cou- 
pled equations of poroelasticity using mixture theory [ 5–7 ]. 
Owing to their complexity, these equations and their derivation 
using mixture theory were later synthesized into four different 
simplified formulations which are collectively denoted the so- 
called Biot-Zienkiewicz theory [ 116 ]. In the first, the 𝒖 – 𝒘 – 𝑝𝑤 
formulation, the solid skeleton displacement 𝒖 , Darcy’s velocity 
𝒘 , and the pore water pressure 𝑝𝑤 are the unknowns to be 
solved. In addition, the further simplified 𝒖 – 𝑝𝑤 , 𝒖 – 𝒘 , and 𝒖 – 𝑼
formulations, where 𝑼is the total displacement vector of the fluid 
phase, were also postulated, with the 𝒖 – 𝑝𝑤 variant considered 
valid as long as highly dynamic loading is not considered, leading 
to its widespread adoption in geotechnics and geomechanics [ 11, 
72, 74 ]. 
Mesh-dependent methods such as the finite element method 
(FEM) permit highly accurate solutions using the coupled for- 
mulations of Biot–Zienkiewicz theory, especially for problems 
that deal with small deformations or with the prefailure phase 
of geomaterials or engineered structures [ 10, 14–16 ]. In the case 
of slope stability, while FEM is particularly useful for capturing 
the failure mechanism, FEM is unable to capture the post-failure 
behavior and deformation of the slope due to issues resulting 
from mesh distortion. For the same reason, the traditional FEM is 
unable to accurately model a number of other solid–fluid coupled 
geohazard problems such as debris flows, flowslides, or levee 
failures. Modeling and quantifying the post-failure stage is crucial 
to predict travel distances and velocities of the sliding or flowing 
material, as well impact forces on any nearby structures [ 66, 90 ]. 
Continuum-based particle or meshfree methods such as the mate- 
rial point method (MPM) [ 1, 75, 88, 115 ], peridynamics [ 64, 89 ], 
particle FEM (PFEM) [ 48, 65, 77 ], element free Galerkin method 
(EFG) [ 4 ], reproducing kernel particle method (RKPM) [ 56 ], and 
smoothed particle hydrodynamics (SPH) [ 19, 20, 22, 31, 39, 40, 78 ] 
are all capable of accounting for the large deformations inherent 
of the post-failure regime. Their continuum nature allows for the 
discretization and solving of the coupled equations from Biot–
Zienkiewicz theory, and a number of formulations to account for 
fluid saturated porous media have been recently proposed [ 3, 62, 
63, 73, 85, 103–105 ]. Originally developed to deal with astrophys- 
ical applications [ 44, 60 ], SPH has a number of computational 
advantages over its peers. For example, in MPM, a background 
Eulerian mesh is utilized to solve the governing equations while 
the state variables are carried in the Lagrangian material points, 
adding to computational cost and making the method susceptible 
to cell crossing noise [ 112 ]. In PFEM, whenever the Lagrangian 
particles/nodes move such that the mesh is distorted, it must 
be deleted, and remeshed, a methodology resulting in extensive 
remeshing when dealing with large deformation problems [ 101 ]. 
Since EFG also requires integration on a mesh [ 37 ], SPH is in 
effect one of the few truly meshfree methods. 
In the SPH method, two distinct approaches have been proposed 
to account for the different phases (solid skeleton and water) in 
the case of a fluid saturated medium. In the first, each phase in 
the saturated porous medium is represented by its own set (layer) 
of Lagrangian SPH particles, and the governing equations of each 
phase are solved distinctly over the corresponding set of particles 
[ 21, 50 ]. In general, the fluid phase is modeled as incompressible 
or using the weakly compressible form of the SPH method, and 
the skeleton is modeled using an elastoplastic constitutive model, 
with the interaction between the phases given by a seepage or 
drag force. The second is the single-layer approach, which is more 
computationally inexpensive as there is only one particle type and 
no need for interaction forces, and the governing equations can 
be taken directly from Biot–Zienkiewicz theory and its simplified 
forms with minimal modification. Some of the early efforts 
to develop a strongly coupled hydromechanical framework for 
SPH based on the Biot–Zienkiewicz equations followed a depth- 
integrated approach, using fluid-like rheology models, focusing 
on debris flows [ 9, 79 ]. More recently, Morikawa and Asai [ 67 ] 
proposed a single-layer SPH 𝒖 – 𝒘 – 𝑝𝑤 framework based on 
an incompressible SPH (ISPH) approach, where both pore fluid 
and soil skeleton are incompressible, which is imposed through 
a projection method sharing features with the moving-particle 
semi-implicit method [ 51 ] resulting in a pressure Poisson equa- 
tion (PPE). However, the condition of divergence-free velocity 
field may not always hold in physical systems and adds significant 
numerical complexity. Lian and coworkers [ 54 ] extended their 
previous work on an SPH framework for seepage flow through 
unsaturated soil [ 53 ], to derive a single-layer strongly coupled 
explicit formulation for unsaturated porous media based on the 
𝒖 – 𝑝𝑤 equations. Chen et al. [ 25 ] developed a similar formulation 
to Lian et al. [ 54 ] where the pore pressure rate (PR) is calculated 
in an explicit rate equation based on volumetric strains and 
Darcy’s law, and successfully applied the model to seepage- 
induced sinkhole formation in fully saturated soils. Lian and 
coworkers further proposed a three-point integration scheme to 
reduce the dependence of the pore fluid on the fluid bulk modulus 
without relying on a fully implicit approach and permitting larger 
time increments in the time integration and saving computational 
cost [ 55 ]. The work of Yao and coauthors [ 110 ] likewise developed 
both fully explicit 𝒖 – 𝑝𝑤 and 𝒖 – 𝒘 – 𝑝𝑤 formulations, sharing 
similarities with past work [ 25, 54 ] and using absorbing boundary 
conditions demonstrated under harmonic and dynamic loading 
in one and two dimensions. Yao et al. further demonstrated that 
numerical dissipation techniques in the SPH method together 
with the explicit approach have the effect of averaging volumetric 
strains in the context of SPH, having a similar effect to the B-bar 
method in mesh-based method like FEM or MPM, thus avoiding 
volumetric locking in the near-incompressibility limit. 
In this paper, inspired by the aforementioned recent progress, we 
develop and lay out in detail the derivations, discretizations, and 
implementations of a projection method PPE approach and an 
explicit pore PR equation method for a strongly coupled 𝒖 – 𝑝𝑤 
hydromechanical formulation for fully saturated soil in the SPH 
method. We also present the required numerical stabilization 
techniques and the SPH form of boundary conditions for the 
pore pressure degree of freedom at drained and undrained 
boundaries. The hydromechanical models are implemented into 
the in-house parallel SPH code GEOSPH developed by the authors 
[ 30, 38 ] and built on the open source framework PySPH [ 82 ], 
2 of 31
International Journal for Numerical and Analytical Methods in Geomechanics, 2026

## Page 3

which has been used in a number of applications relating to 
large geomaterial deformations that involve localized failure [ 32, 
34, 35, 42, 71 ]. We verify and compare the performance of the 
presented formulations for one-dimensional, and for the first time 
in the literature, three-dimensional benchmarks in poroelasticity, 
including Cryer’s Problem. Next, we combine these formulations 
with a modified Cam Clay (MCC) model from critical state soil 
mechanics, to verify the performance against analytical solutions 
for various undrained triaxial compression stress paths, and 
against results obtained with a penalty-based framework [ 12, 13 ] 
specific to undrained loading developed in the authors’ previous 
work [ 33 ]. 
We take advantage of the strongly coupled hydromechanical 
model to study retrogressive landslides and the progressive failure 
of sensitive clays, under fluid saturated conditions. Retrogressive 
landslides involve a series of sequential failure surfaces trending 
upslope and are a product of strain softening behavior in sensitive 
clays that transforms the clay into remolded liquid-like material 
with a low shear strength during localized failure within shear 
bands. Because of their short temporal duration, retrogressive 
landslides are often treated as an undrained process, and most 
past computational modeling has completely ignored the role of 
pore pressures, with very few exceptions [ 48, 55 ], and almost all 
past studies have relied on total stress analyses capturing the soil’s 
inability to deform volumetrically by adopting incompressible 
elasticity (Poisson’s ratio close to 0.5), and by using the von Mises 
( 𝐽2 ) or Tresca plasticity model which does not allow for plastic vol- 
umetric strains [ 22, 36, 80, 87, 98, 113 ], even though this modeling 
choice is not realistic for many sensitive clays [ 48 ]. To account 
for the build-up and dissipation of pore pressures, we perform 
SPH simulations with the coupled hydromechanical framework, 
as well as an isotropic strain softening elastoplastic model with 
the Drucker–Prager yield criterion designed for describing the 
remolding and progressive failure behavior of sensitive clays. We 
contrast the simulation results against equivalent simulations 
performed with the penalty-based undrained framework, com- 
paring the runout distance, failure mechanism, pore pressure 
distributions, and respective computational efficiency. We also 
explore some of the factors promoting the distinct spreading 
versus flowslide modes of retrogressive slope failure. Lastly, we 
study the 1994 Sainte-Monique Landslide in Quebec, Canada, 
an example of a retrogressive landslide showing the ability of 
strongly coupled hydromechanical SPH simulations to capture 
the spreading mode of failure, and similar runout and post-failure 
slope configuration. 
The order of presentation in the paper is as follows. In the 
remainder of Section 1 , in Subsection 1.1 , a brief introduction 
to retrogressive landslides is presented. This is followed by an 
exposition of the governing equations in the 𝒖 – 𝑝𝑤 formulation 
in Section 2 and of the SPH discretization and implementation, 
boundary treatment, constitutive equations, as well as stabiliza- 
tion in Section 3 . In Section 4 , the strongly coupled framework 
is verified against analytical solutions pertaining to various 
benchmark problems, and in Section 5 , we explore retrogressive 
failure of two idealized slopes, comparing the results between 
the strongly coupled hydromechanical model and a penalty- 
based undrained (here forth referred to simply as undrained) 
approach. Section 6 is dedicated to the simulation of the 1994 
Sainte-Monique Landslide, and some discussion and concluding 
thoughts as well as directions for further work are presented in 
Section 7 . 
1.1 
Retrogressive Landslides in Sensitive Clays 
Retrogressive landslides, or retrogressive slope failures, are a 
type of progressive failure that occurs after an initial local slope 
failure leads to a catastrophic series of successive failures trending 
upslope in a retrogressive manner. Retrogressive landslides can 
span kilometers in their runout, are very quick, and have signifi- 
cant destructive potential [ 23, 24, 93 ], as evidenced by numerous 
events, such as the flowslides in Heifangtai, China [ 81 ], and the 
Gjerdrum slides in Norway [ 92 ]. They usually occur with minimal 
warning, and small disturbances coming from human activity 
upslope can be sufficient to trigger and propagate an instability 
[ 57 ]. Retrogressive landslides occur in sensitive clays exhibiting 
drastic strain softening behavior in undrained shear, as a result of 
remolding, a process which transforms the clay into a liquid-like 
material with a very low shear strength (often < 1 kPa) during 
localized failure. Because of their short duration, and the fact 
that they usually involve saturated soils, retrogressive landslides 
are treated as an undrained process [ 36, 95 ]. The two main 
representative types of retrogressive landslides include flowslides 
and spreads [ 57, 59, 100 ]. 
A flowslide or the slide-flow mode occurs as a series of successive 
rotational slides, where the initial slide generates a new unstable 
backscarp, and subsequent failures of these newly produced 
backscarps continue until a final stable backscarp is obtained. 
As the name implies, during and after the slide, the failed 
remolded clay mass flows out of the crater as fluid-like debris. 
On the other hand, spreads are a type of progressive failure, 
where a soil mass delimited by a surface-parallel sliding plane 
at depth begins to fail in extension forming intact blocks of 
clay known as horsts and grabens. Horsts are blocks with an 
upwards-pointing sharp wedge shape ( Δ-shape) and grabens are 
downwards-pointing wedge-shaped blocks with a flat top surface 
( ∇ -shaped). As pointed by Carson [ 23 ], tension cracks form 
between the horsts and grabens and the angle of the slip surfaces 
between graben and horsts should be oriented at 45◦+ 𝜙∕2 with 
respect to the horizontal, where 𝜙is the friction angle of the 
clay. Carson observed in the field that the bases of the grabens 
also undergo remolding, and that horsts and grabens subside 
into this remolded clay, in turn squeezing the remolded clay 
along the cracks (slip planes) between the horsts and grabens 
as they slide. To initiate a spread, it has been hypothesized that 
an initial rotational failure is often needed to reduce the lateral 
earth pressure behind the backscarp and increase the shear 
stress along the sliding plane at the bottom of the new scarp, in 
turn promoting spreading upslope [ 57 ]. Field observations have 
corroborated this line of thought as some spread failures were 
first triggered by a rotational slide, for example, as seen in the 
Sköttorp landslide in Sweden [ 76 ]. Similarly, gradual erosion 
occurring at the slope toe due to fluvial processes may also 
decrease the horizontal earth pressure and increase shear stress 
sufficiently to trigger an initial instability in the slope [ 57 ]. 
One of the main factors known to affect the particular failure 
mode is the in situ stress condition, particularly the coefficient 
of earth pressure at rest, 𝐾0 , which is the ratio of effective 
International Journal for Numerical and Analytical Methods in Geomechanics, 2026
3 of 31

## Page 4

horizontal to effective vertical stress. In their Eulerian-based 
large deformation finite-element study, Wang et al. [ 99 ] showed 
that a higher 𝐾0 increased the potential for retrogressive failure 
overall, and that a high enough 𝐾0 could change the emerging 
failure patterns. For example, for low 𝐾0 , only singular slides 
were generated, whereas for intermediate 𝐾0 values, flowslides 
occurred, and for high enough 𝐾0 ≥ 1 . 0 , spreads were observed. 
These results were largely corroborated by the MPM simulations 
of Wang et al. [ 100 ] and by the SPH simulations performed by Lian 
et al. [ 55 ]. Field evidence also points to 𝐾0 > 1 . 0 in some cases of 
large spreads in sensitive clays [ 45 ]. 
Much previous numerical modeling work has focused on improv- 
ing constitutive models, particularly strain softening models, to 
match the behavior of sensitive clays [ 84, 94, 95, 107 ]. For example, 
Wang and coworkers found that by increasing the brittleness 
of the clay by increasing the rate of post-peak undrained shear 
strength degradation, the possibility of flowslides increased, 
whereas for more gradual degradation rates, spreads dominated 
[ 100 ]. However, considerably less focus has been put on account- 
ing for the effects of pore pressures or groundwater seepage, 
in part due to the focus on strain softening and the commonly 
adopted total stress modeling approaches [ 58, 99 ]. In undrained 
shearing, the increasing pore pressure will cause a reduction in 
shearing resistance because of the decreased effective stress [ 8 ]. 
However, rather than directly modeling this hydromechanical 
process, some authors prefer to account for this feature directly 
in the softening response [ 93 ]. This modeling choice fails to 
acknowledge the important role pore pressure dissipation plays 
on ending progressive failure because of the resulting increasing 
strength and frictional resistance in the clay [ 100 ]. 
Progressive failures are highly dynamical processes. The 
remolded clay debris in flowslides often flows at up to several 
meters per second, and the horsts and grabens in spreads also 
slide at considerable speeds (although not as great). Therefore, the 
prefailure slope and the amount of gravitational potential energy 
at the moment of initial failure may also affect the resulting 
retrogressive landslide mode. From the point of view of numerical 
simulation of retrogressive landslides, it is necessary to be able to 
solve the dynamic equations of motion, and to handle the post- 
failure large deformations. Particle-based or meshfree methods 
have become the preferred approach for modeling large progres- 
sive failures [ 26, 91, 99, 104, 108 ], and SPH, which solves the fully 
dynamic equations of motion, is a natural method of choice [ 22 ]. 
2 
Governing Equations for the Coupled Problem 
In this section, we present the continuum equations for a fully 
saturated soil–water mixture derived using continuum mixture 
theory, which follows an approach similar to that taken by Biot 
[ 5, 6 ] and Zienkiewicz [ 116 ]. In addition, we provide an overview 
of the assumptions, variables of interest, and equations needed to 
solve the strongly coupled problem. More details about the deriva- 
tion of the mixture equations and their underlying assumptions 
can be found in Appendix I. 
The equations for the balance of mass and of linear momentum 
for the mixture, in their general form, are given by Equations ( 1 ) 
and ( 2 ). 
1 
𝑄 
𝑑 𝑝𝑤 
𝑑𝑡 − ∇ ⋅𝒗 − ∇ ⋅𝒗𝑠 −∇ 𝜌𝑤 
𝜌𝑤 
⋅𝒗 = 0 . 
(1) 
𝜌𝑑𝒗𝑠 
𝑑𝑡 + 𝜌𝑤 
( 𝑑𝑤 𝒗𝑤 
𝑑𝑡 −𝑑𝒗𝑠 
𝑑𝑡 
) 
= ∇ ⋅𝝈′ + ∇ 𝑝𝑤 + 𝜌𝒈 . 
(2) 
Here, 𝑝𝑤 is the pore (water) pressure, 𝝈′ is the effective Cauchy 
stress tensor, 𝒗 is Darcy’s velocity, or the difference between 
fluid ( 𝒗𝑤 ) and solid ( 𝒗𝑠 ) velocities per unit area of the mixture, 
𝜌is the density of the mixture, 𝜌𝑤 is the density of the fluid 
phase, 𝜌𝑤 = 𝑛𝜌𝑤 is the partial density of the fluid phase, 𝑛
is the mixture porosity, and 1∕ 𝑄 = (1 − 𝑛)∕ 𝐾𝑠 + 𝑛∕𝐾𝑤 , where 
𝐾𝑠 and 𝐾𝑤 are correspondingly the bulk moduli of the solid 
and fluid phases. In terms of notation, 𝑑 ()∕ 𝑑 𝑡is a material 
time derivative following the motion of the solid phase, and 
𝑑𝑤 ()∕ 𝑑𝑡is following the fluid phase. It is important to note 
that the porous medium in this work is assumed to have 
isotropic and homogeneous hydraulic conductivity, 𝒌 ( 𝒙 ) = 𝑘𝟏 . 
The formulation presented, in what follows, is limited to isotropic 
and transversely isotropic (e.g., layered soils) hydraulic con- 
ductivity conditions. For situations where conductivities are 
anisotropic, an approach using the framework proposed in 
[ 55 ], with more robust approximations of second derivatives, 
is recommended. 
2.1 
𝒖 – 𝒑𝒘 Pressure Poisson Equation (PPE) 
Formulation 
To derive the so-called 𝒖 – 𝑝𝑤 formulation, where only the 
displacement of the solid 𝒖 and the pore water pressure 𝑝𝑤 are 
the independent variables, a few assumptions are necessary: 
1. Intrinsically incompressible pore fluid and solid fractions: 
𝐾𝑠 →∞and 𝐾𝑤 →∞, such that 1∕ 𝑄 →0 and ∇ 𝜌𝑤 = 0 . 
2. The relative material acceleration between the fluid and solid 
phases is zero, that is, 𝑑𝑤 𝒗𝑤 ∕𝑑 𝑡 − 𝑑 𝒗𝑠 ∕𝑑 𝑡 = 0 . 
For the mixture balance of mass equation, Equation ( 1 ), 
applying the first assumption and substituting the definition 
of Darcy’s velocity (Equation A12 in Appendix I) gives the 
following: 
∇ ⋅𝒗𝑠 +
𝑘 
𝜌𝑤 𝑔 ∇2 𝑝𝑤 + 𝑘∇2 𝑧 = 0 . 
(3) 
where 𝑧is the elevation head, and ∇2 is the Laplacian operator. 
Now, considering the mixture momentum balance, Equation ( 2 ), 
and applying the second assumption results in 
𝑑𝒗𝑠 
𝑑𝑡 = 1 
𝜌∇ ⋅𝝈′ + 1 
𝜌∇ 𝑝𝑤 + 𝒈 . 
(4) 
We see that the two governing equations in the 𝒖 – 𝑝𝑤 formulation 
are Equations ( 3 ) and ( 4 ). Because the pore pressure 𝑝𝑤 is present 
in both equations, the system is solved through a PPE type 
equation and a projection method. 
4 of 31
International Journal for Numerical and Analytical Methods in Geomechanics, 2026

## Page 5

2.1.1 
PPE Solution and Time Integration 
The implicit solution of the PPE at time 𝑡𝑛+ 1 , corresponding to 
time step 𝑛 + 1 , is written as follows: 
∇2 𝑝𝑤 
𝑛+ 1 = −𝜌𝑤 𝑔 
𝑘 ∇ ⋅𝒗𝑛+ 1 
𝑠 
− 𝜌𝑤 𝑔 ∇2 𝑧𝑛+ 1 . 
(5) 
The projection method consists of a predictor–corrector scheme 
to determine the velocities at 𝑡𝑛+ 1 such that the corrected velocity 
enforces the incompressibility of the saturated mixture, in line 
with the assumptions used to derive the formulation. First, 
a so-called predicted velocity, which does not depend on the 
pore-water pressure, is calculated explicitly as follows: 
𝒗∗ 
𝑠 = 𝒗𝑛 
𝑠 + Δ𝑡
( 1 
𝜌𝑛 
∇ ⋅𝝈′
𝑛 + 𝒈
) 
, 
(6) 
where Δ𝑡 = 𝑡𝑛+ 1 − 𝑡𝑛 . Then, the final solid velocity that satis- 
fies the incompressibility condition is determined implicitly, by 
adding the contribution of the pore-water pressure 
𝒗𝑛+ 1 
𝑠 
= 𝒗∗ 
𝑠 + Δ𝑡1 
𝜌∗ ∇ 𝑝𝑤 
𝑛+ 1 , 
(7) 
where 𝜌∗ is the projected mass density of the mixture, calculated 
using the projected velocity 
𝜌∗ = 𝜌𝑛 + Δ𝑡𝜌𝑛 ∇ ⋅𝒗∗ 
𝑠 . 
(8) 
Finally, substituting Equation ( 7 ) into ( 5 ) and assuming that 
𝑧𝑛+ 1 ≈𝑧∗ , after some algebra, the Laplacian of 𝑝𝑤 becomes 
∇2 𝑝𝑤 
𝑛+ 1 = − 𝑎∗ (
∇ ⋅𝒗∗ 
𝑠 + 𝑘∇2 𝑧∗ )
, 
(9) 
where 
𝑎∗ =
𝑏𝜌∗ 
𝜌∗ + 𝑏Δ𝑡 , 
(10) 
with 𝑏 = 𝜌𝑤 𝑔∕𝑘. Equation ( 9 ) is then used to find the pore- 
w ater pressure, as we will see in upcoming sections, using an 
explicit solution. 
2.2 
𝒖 – 𝒑𝒘 Pore Pressure Rate 
Equation Formulation 
An alternative formulation for the 𝒖 – 𝑝𝑤 can be cast such that 
the incompressibility of the pore water phase is enforced using 
the bulk modulus of the water 𝐾𝑤 itself, to ultimately obtain a 
rate equation for the pore pressure 𝑝𝑤 that can be integrated in 
time explicitly. The following assumptions are the same as those 
in the PPE version of the 𝒖 – 𝑝𝑤 formulation, with a slight change 
in the first assumption: 
1. Intrinsically incompressible solid fraction: 𝐾𝑠 →∞. Spatial 
gradient of water density is negligible, ∇ 𝜌𝑤 ≈0 although its 
compressibility is determined by the water bulk modulus. 
Hence, 𝐾𝑤 →∞is no longer assumed and therefore 1∕ 𝑄 →0 
does not hold. 
Applying the revised first assumption, such that 
1 
𝑄 =
1 − 𝑛 
𝐾𝑠 +
𝑛 
𝐾𝑤 ≈
𝑛 
𝐾𝑤 , we rewrite Equation ( 1 ) as follows: 
𝑛 
𝐾𝑤 
𝑑 𝑝𝑤 
𝑑𝑡 − ∇ ⋅𝒗 − ∇ ⋅𝒗𝑠 = 0 . 
(11) 
Now, using Darcy’s law (Equation A12 in Appendix I) to 
determine the relative water–solid velocity, we arrive at, 
𝑑 𝑝𝑤 
𝑑𝑡 = 𝐾𝑤 
𝑛 
( 𝑘 
𝜌𝑤 𝑔 ∇2 𝑝𝑤 + 𝑘∇2 𝑧 + ∇ ⋅𝒗𝑠 
) 
, 
(12) 
which is a rate equation for the pore pressure 𝑝𝑤 that can be 
explicitly integrated in time. Unlike the PPE approach, which 
assumes the solid and fluid phases are incompressible, by relaxing 
the assumption of incompressibility of the fluid phase, we arrive 
at a slightly more generalizable and computationally simpler 
formulation. Note that gravity (potential energy) is introduced 
into the calculation of pore water pressure through an elevation 
head in Equation ( 12 ) (Laplacian of the vertical position, 𝑧). 
It is important to emphasize that the PR equation, Equation ( 12 ), 
presented here can be seen as a slightly modified and particular 
case of the PR equation presented in [ 54 ]. Equation ( 12 ) assumes 
that the soil is fully saturated and, hence, cannot accommodate 
unsaturated flow. For a more general framework that accounts 
for the three phases of the porous medium, the reader is referred 
to the works of Lian and co-authors [ 53, 54 ] and refe3ein. 
3 
SPH Discretization and Implementation 
The SPH method is a continuum-based meshfree Lagrangian 
method that discretizes the problem domain into a set of particles, 
which are both mathematical discretization points used to solve 
the governing equations in addition to Lagrangian particles that 
evolve physical properties of the domain (e.g., mass, mass density, 
stress, and strain). The interactions between these particles are 
dictated by a weighting or kernel function 𝑊whose value 
depends on the distance between two particles of interest, and 
on a length scale called the smoothing length ℎ, which defines 
the size of the support domain of the kernel. The value of a field 
function 𝑓( 𝒙 ) can then be determined for a particular particle 
using a convolution integral over a domain Ω
⟨𝑓( 𝒙 ) ⟩= ∫Ω
𝑓( 𝒙′) 𝑊( 𝒙 − 𝒙′, ℎ)d 𝒙′ , 
(13) 
where 𝒙 is the position vector in three dimensions, and 𝑡is time. 
The exact integral in Equation ( 13 ) can be approximated using the 
following summation: 
⟨𝑓 ( 𝒙 ) ⟩𝑖 =
𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑗 
𝑓 ( 𝒙𝑗 ) 𝑊𝑖𝑗 , 
(14) 
where ⟨⟩signifies approximation, the subscript 𝑗represents the 
𝑁-numbered neighboring particles of particle 𝑖, located at 𝒙 = 
𝒙𝑖 , 𝑊𝑖𝑗 = 𝑊( 𝒙𝑖 − 𝒙𝑗 , ℎ) , 𝑚𝑗 is the mass, and 𝜌𝑗 is mass density 
of the 𝑗th particle. Note that the summation is performed over 
all neighboring particles of particle 𝑖, including itself. Only 
particles within a radius 𝑘ℎ ℎpertaining to the 𝑖th particle will 
International Journal for Numerical and Analytical Methods in Geomechanics, 2026
5 of 31

## Page 6

be considered neighbors ( 𝑗) and included in the summations in 
Equations 14 and 15 . The coefficient 𝑘ℎ = 2 . 0 is usually chosen in 
most SPH applications and in this work [ 39 ]. Replacing 𝑓( 𝒙 ) with 
its spatial derivative, applying the divergence theorem, and taking 
advantage of the symmetric and positive nature of the kernel, 
yields a similar expression for the gradient of a field function, 
approximated as follows: 
⟨∇ 𝑓 ( 𝒙 ) ⟩𝑖 =
𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑗 
𝑓 ( 𝒙𝑗 )∇ 𝑊𝑖𝑗 , 
(15) 
where ∇ = ( 𝜕 ∕𝜕 𝑥, 𝜕 ∕𝜕 𝑦 , 𝜕 ∕𝜕 𝑧)𝑖 is the vector of partial derivatives 
with respect to the three spatial coordinates, evaluated at the 
position of particle 𝑖. 
3.1 
SPH Discrete Operators 
In order to spatially discretize the partial differential equa- 
tions (PDEs) seen in Section 2 , and to transform the PDEs into 
ordinary differential equations in time, we make use of the SPH 
approximations, or so-called SPH operators for fields, gradients 
of fields, and for Laplacians of fields. We note that the previously 
mentioned SPH approximation (operator) in Equation ( 15 ) is not 
ideal as it does not guarantee the vanishing of the gradient of a 
constant field function 𝑓, which can be tensor- or scalar-valued. 
One way to mitigate these errors is to use the following commonly 
adopted operator for the gradient: 
⟨∇ 𝑓⟩𝑖 =
𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑗 
( 𝑓𝑗 − 𝑓𝑖 ) ⊗̃∇ 𝑊𝑖𝑗 , 
(16) 
where ̃∇ 𝑊𝑖𝑗 = 𝑳𝑖 ⋅∇ 𝑊𝑖𝑗 is the corrected gradient of the kernel 
function, with 
∇ 𝑊𝑖𝑗 =
𝜕𝑊𝑖𝑗 
𝜕𝒙𝑖 
, 
(17) 
and 
𝑳𝑖 =
[ 𝑛 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑗 
( 𝒙𝑗 − 𝒙𝑖 ) ⊗∇ 𝑊𝑖𝑗 
] − 1 
, 
(18) 
which enables first-order consistency in the approximation of the 
gradient of 𝑓. 
For the divergence operator used to discretize the balance of 
linear momentum and the velocity divergence in the balance of 
mass, three operators are commonly utilized as follows: 
⟨∇ ⋅𝑓⟩𝑖 = 𝜌𝑖 
𝑁 
∑
𝑗= 1 
𝑚𝑗 
( 
𝑓𝑖 
𝜌2 
𝑖 
+
𝑓𝑗 
𝜌2 
𝑗 
) 
∇ 𝑊𝑖𝑗 , 
(19) 
⟨∇ ⋅𝑓⟩𝑖 =
𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑗 
(
𝑓𝑗 + 𝑓𝑖 
)
∇ 𝑊𝑖𝑗 , 
(20) 
and 
⟨∇ ⋅𝑓⟩𝑖 =
𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑗 
(
𝑓𝑗 − 𝑓𝑖 
)
∇ 𝑊𝑖𝑗 . 
(21) 
For the conservation of momentum, Equation ( 4 ), we use Equa- 
tion ( 19 ) to discretize the divergence of the effective stress ∇ ⋅𝝈, 
and Equation ( 20 ) for the gradient of the pore water pressure ∇ 𝑝𝑤 . 
For the divergence of the solid velocity in the balance of mass 
equation (namely Equation 3 for the PPE approach or in the PR 
form of the equation, Equation 12 ), we use the SPH operator in 
Equation ( 21 ) with the corrected kernel gradient. For more details 
on the proper selection of operators, see [ 22, 67 ]. 
To discretize the Laplacian of the pore pressure in the balance of 
mass equations, we utilize the operator in Equation ( 22 ), proposed 
by Morris et al. [ 70 ], 
⟨∇2 𝑓⟩𝑖 = 2
𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑗 
( 𝑓𝑖 − 𝑓𝑗 )
𝒙𝑖𝑗 
|𝒙𝑖𝑗 |2 ⋅̃∇ 𝑊𝑖𝑗 , 
(22) 
where 𝒙𝑖𝑗 = 𝒙𝑖 − 𝒙𝑗 . Although alternative SPH operators for 
the Laplacian exist [ 41 ], they require additional computational 
and arithmetic cost. Furthermore, recent work has shown that 
Morris’s operator for the Laplacian does not cause accuracy 
losses for large deformation problems with significant amounts 
of particle disorder [ 67–69 ]. 
3.2 
SPH Discretization of the PPE Equation 
In the PPE version of the 𝒖 – 𝑝𝑤 formulation, Equations ( 4 ) and 
( 3 ) are discretized using the previously mentioned SPH operators 
yielding Equations ( 23 ) and ( 24 ), which are highlighted in the box 
below. 
PPE 𝒖 – 𝒑𝒘 Governing Equations and Discretization 
Let  ⊂ℝ𝑑 ( 𝑑 = 2 , 3 ) be the domain occupied by the porous 
medium, with 𝑡 ∈(0 , 𝑇] . The governing equations are: 
𝑑𝒗𝑠 
𝑑𝑡 = 1 
𝜌∇ ⋅𝝈′+ 1 
𝜌∇ 𝑝𝑤 + 𝒈 →
⟨ 𝑑𝒗𝑠 
𝑑𝑡 
⟩ 
𝑖 
=
𝑁 
∑
𝑗= 1 
𝑚𝑗 
( 
𝝈′
𝑖 
𝜌2 
𝑖 
+
𝝈′
𝑗 
𝜌2 
𝑗 
) 
⋅∇ 𝑊𝑖𝑗 
+
𝑁 
∑
𝑗= 1 
𝑚𝑗 
( 𝑝𝑤 
𝑖 + 𝑝𝑤 
𝑗 
𝜌𝑖 𝜌𝑗 
) 
𝟏 ⋅∇ 𝑊𝑖𝑗 + 𝒈 ,
in  × 𝑡 
(23) 
∇ ⋅𝒗𝑠 +
𝑘 
𝜌𝑤 𝑔 ∇2 𝑝𝑤 + 𝑘∇2 𝑧 = 0 →
𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑗 
(
𝒗𝑠𝑗 − 𝒗𝑠𝑖 
)
⋅̃∇ 𝑊𝑖𝑗 
+ 2 𝑘𝑖 
𝜌𝑤 𝑔 
[ 𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑗 
(
𝑝𝑤 
𝑖 − 𝑝𝑤 
𝑗 
) 𝒙𝑖𝑗 
|𝒙𝑖𝑗 |2 ⋅̃∇ 𝑊𝑖𝑗 
+ 𝜌𝑤 𝑔
𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑗 
(
𝑧𝑖 − 𝑧𝑗 
) 𝒙𝑖𝑗 
|𝒙𝑖𝑗 |2 ⋅̃∇ 𝑊𝑖𝑗 
] 
= 0 ,
in  × 𝑡 
(24) 
We notice that in the PPE approach, the pore pressure appears 
in both Equations ( 23 ) and ( 24 ) and these are coupled. To solve 
the PPE, the projection method is used, taking Equation ( 9 ) from 
the projection method and applying it to the SPH operators, and 
making ( 𝑝𝑤 
𝑖 )𝑛+ 1 an explicit function of parameters at 𝑡𝑛 , we obtain 
the following: 
6 of 31
International Journal for Numerical and Analytical Methods in Geomechanics, 2026

## Page 7

2
𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑛 
𝑗 
[
( 𝑝𝑤 
𝑖 )𝑛+ 1 − ( 𝑝𝑤 
𝑗 )𝑛 ] 𝒙𝑛 
𝑖𝑗 
|𝒙𝑛 
𝑖𝑗 |2 ⋅̃∇ 𝑊𝑛 
𝑖𝑗 = 
− 𝑎∗ 
[ 𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑛 
𝑗 
(
𝒗∗ 
𝑠𝑗 − 𝒗∗ 
𝑠𝑖 
)
⋅̃∇ 𝑊𝑛 
𝑖𝑗 + 2 𝑘
𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑛 
𝑗 
(
𝑧∗ 
𝑖 − 𝑧∗ 
𝑗 
) 𝒙𝑛 
𝑖𝑗 
|𝒙𝑛 
𝑖𝑗 |2 ⋅̃∇ 𝑊𝑛 
𝑖𝑗 
] 
.
(25) 
The second and last step is to isolate the term containing 
( 𝑝𝑤 
𝑖 )𝑛+ 1 on the left-hand side of the equation, which after some 
manipulation, yields the explicit solution for the PPE 
(
𝑝𝑤 
𝑖 
)𝑛+ 1 =
𝑁 
∑
𝑗= 1 
[
𝐴𝑗 ( 𝑝𝑤 
𝑗 )𝑛 ]
+ 𝐵𝑖 
𝐴𝑖 
, 
(26) 
where 
𝐴𝑖 = 2
𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑛 
𝑗 
𝒙𝑛 
𝑖𝑗 
|𝒙𝑛 
𝑖𝑗 |2 ⋅̃∇ 𝑊𝑛 
𝑖𝑗 , 
(27) 
so 
𝑁 
∑
𝑗= 1 
[ 
𝐴𝑗 
(
𝑝𝑤 
𝑗 
)𝑛 ] 
= 2
𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑛 
𝑗 
(
𝑝𝑤 
𝑗 
)𝑛 𝒙𝑛 
𝑖𝑗 
|𝒙𝑛 
𝑖𝑗 |2 ⋅̃∇ 𝑊𝑛 
𝑖𝑗 , 
(28) 
and 
𝐵𝑖 = − 𝑎∗ 
[ 𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑛 
𝑗 
(
𝒗∗ 
𝑠𝑗 − 𝒗∗ 
𝑠𝑖 
)
⋅̃∇ 𝑊𝑛 
𝑖𝑗 
+ 2 𝑘
𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑛 
𝑗 
(
𝑧∗ 
𝑖 − 𝑧∗ 
𝑗 
) 𝒙𝑛 
𝑖𝑗 
|𝒙𝑛 
𝑖𝑗 |2 ⋅̃∇ 𝑊𝑛 
𝑖𝑗 
] 
. 
(29) 
The overall algorithm and solution flow for the PPE 𝒖 – 𝑝𝑤 
formulation is summarized in Algorithm B1 of Appendix II. 
Note that the PPE solution above is based on an explicit time 
integration scheme. This scheme, while only first-order accurate, 
provides good results for the small time steps required, is in 
line with the explicit nature of SPH, and is computationally 
inexpensive. However, second- or higher-order methods, such 
as Runge–Kutta integrators, could likely provide more accurate 
solutions, albeit requiring more computational time. The choice 
of integrator that best balances accuracy and computational time 
is outside the scope of this work. 
3.3 
SPH Discretization of the Pressure Rate 
Formulation 
In the PR version of the 𝒖 – 𝑝𝑤 formulation, Equations ( 4 ) and ( 12 ) 
are discretized using the SPH operators yielding Equations ( 30 ) 
and ( 31 ). We note that only Equation ( 31 ) is different from 
Equation ( 24 ) in the PPE approach. 
Pressure Rate 𝒖 – 𝒑𝒘 Discretized Formulation 
Let  ⊂ℝ𝑑 ( 𝑑 = 2 , 3 ) be the domain occupied by the porous 
medium, with 𝑡 ∈(0 , 𝑇] . The governing equations are: 
𝑑𝒗𝑠 
𝑑𝑡 = 1 
𝜌∇ ⋅𝝈′+ 1 
𝜌∇ 𝑝𝑤 + 𝒈 →
⟨ 𝑑𝒗𝑠 
𝑑𝑡 
⟩ 
𝑖 
=
𝑁 
∑
𝑗= 1 
𝑚𝑗 
( 
𝝈′
𝑖 
𝜌2 
𝑖 
+
𝝈′
𝑗 
𝜌2 
𝑗 
) 
⋅∇ 𝑊𝑖𝑗 
+
𝑁 
∑
𝑗= 1 
𝑚𝑗 
( 𝑝𝑤 
𝑖 + 𝑝𝑤 
𝑗 
𝜌𝑖 𝜌𝑗 
) 
𝟏 ⋅∇ 𝑊𝑖𝑗 + 𝒈 ,
in  × 𝑡 
(30) 
𝑑 𝑝𝑤 
𝑑𝑡 = 𝐾𝑤 
𝑛 
( 𝑘 
𝜌𝑤 𝑔 ∇2 𝑝𝑤 + 𝑘∇2 𝑧 + ∇ ⋅𝒗𝑠 
) 
→
⟨ 𝑑 𝑝𝑤 
𝑑𝑡 
⟩ 
𝑖 
= 𝐾𝑤 
𝑛 
[ 𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑗 
(
𝒗𝑠𝑗 − 𝒗𝑠𝑖 
)
⋅̃∇ 𝑊𝑖𝑗 
+ 2 𝑘𝑖 
𝜌𝑤 𝑔 
𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑗 
(
𝑝𝑤 
𝑖 − 𝑝𝑤 
𝑗 
) 𝒙𝑖𝑗 
|𝒙𝑖𝑗 |2 ⋅̃∇ 𝑊𝑖𝑗 
+ 2 𝑘𝑖 
𝑁 
∑
𝑗= 1 
𝑚𝑗 
𝜌𝑗 
(
𝑧𝑖 − 𝑧𝑗 
) 𝒙𝑖𝑗 
|𝒙𝑖𝑗 |2 ⋅̃∇ 𝑊𝑖𝑗 
] 
,
in  × 𝑡 
(31) 
To determine the pore water pressure at time step 𝑛 + 1 , we can 
explicitly integrate Equation ( 31 ) in time, 
( 𝑝𝑤 
𝑖 )𝑛+ 1 = ( 𝑝𝑤 
𝑖 )𝑛 +
⟨ 𝑑 𝑝𝑤 
𝑑𝑡 
⟩ 
𝑖 
Δ𝑡 
(32) 
The overall algorithm and solution flow for the PR 𝒖 – 𝑝𝑤 
formulation is summarized in Algorithm B2 of Appendix II. 
3.4 
Boundary Conditions 
For a domain  ⊂ℝ𝑑 ( 𝑑 = 2 , 3 ) with boundary 𝜕 , partitioned 
into velocity, traction, pressure, and flux boundaries 𝜕 𝑣 , 𝜕 ℎ , 
𝜕 𝑝 , and 𝜕 𝑞 , respectively, with mutually disjoint intersections, 
and with 𝑡 ∈(0 , 𝑇] , the following boundary conditions must be 
satisfied in the initial boundary value problem, 
⎧ 
⎪ 
⎪ 
⎪ 
⎨ 
⎪ 
⎪ 
⎪ 
⎩ 
𝝈⋅𝒏 = 𝒉 , 
on 𝜕ℎ × 𝑡
(Neumann: prescribed traction) , 
𝒗 = ̂𝒗 , 
on 𝜕𝑣 × 𝑡
(Dirichlet: prescribed velocity) , 
𝑝𝑤 = ̄𝑝𝑤 , 
on 𝜕𝑝 × 𝑡
(Dirichlet: prescribed pore pressure) , 
−𝑘 
𝜌𝑤 𝑔 ∇ 𝑝𝑤 ⋅𝒏 = ̄𝑞𝑤 , on 𝜕𝑞 × 𝑡
(Neumann: prescribed fluid flux) . 
(33) 
where 𝒏 is the unit normal vector to the boundary, 𝒉 is the 
prescribed traction vector, ̂𝒗 is a prescribed velocity, ̄𝑝𝑤 is a 
prescribed pore pressure, and ̄𝑞𝑤 is a prescribed fluid flux (equal 
to zero for undrained boundaries). 
For the Dirichlet-type boundary conditions for the solid veloc- 
ity, so-called dummy or boundary particles are used, where 
International Journal for Numerical and Analytical Methods in Geomechanics, 2026
7 of 31

## Page 8

the domain particles are enveloped by 3–4 layers of boundary 
particles in lieu of solid physical walls, helping to enforce no 
penetration of the boundaries by the domain particles, and also 
ensuring that the particles near the domain edges do not have 
truncated kernels. The boundary particles can be fixed in space 
or may move at a prescribed velocity, and their stresses are 
determined through an extrapolation from the stress pertaining 
to neighboring domain particles, using the formulation seen in 
[ 109 ]. For Neumann boundary conditions (e.g., to apply tractions 
or confining stresses), we use the flexible confined boundary 
conditions method proposed by [ 114 ], as seen in the examples of 
Cryer’s problem and in undrained triaxial tests. 
To apply Dirichlet boundary conditions for the pore pressure, 
it is important to first identify the location of the free surfaces, 
and here the tracking method of [ 52 ] is used. Dirichlet boundary 
conditions for the pore pressure are applied by either setting 
the pore pressure to zero at the free surfaces, as in the method 
of Skillen [ 86 ], or applied by setting a desired value of the 
pore pressure at the boundary (dummy particles). However, to 
enforce Neumann boundary conditions for the pore pressure, 
and to ensure ∇ 𝑝𝑤 ⋅𝒏 = 0 for undrained boundary conditions, 
some additional treatment is needed. We adopt the moving least 
square (MLS) formulation presented in Chow et al. [ 27 ], which 
extrapolates the pore pressure from the domain particles to the 
boundary particles using a specially corrected (MLSs) kernel that 
is zero- and first-order consistent, allowing for linear pressure 
fields to be recovered exactly. 
3.5 
Constitutive Relations 
We assume that the effective stress is driven by the deformation 
rate and can be evaluated using any elastoplastic constitutive 
model. In this work, we postulate a hypo-elastoplastic model that 
relates the Jaumann rate of the effective stress tensor directly to 
the deformation rate tensor, as follows: 
𝝈
▿′ = 𝒄ep ∶ 𝒅 . 
(34) 
The Jaumann rate of the effective stress is given by the following: 
𝝈
▿′ = ̇𝝈′ − 𝝎 ⋅𝝈′ + 𝝈′ ⋅𝝎 . 
(35) 
In Equation ( 34 ), 𝒄ep denotes the elastoplastic stress–strain 
response tensor. For purely elastic behavior, 𝒄ep reduces to the 
elastic tensor 𝒄e . For an isotropic material, 𝒄e can be expressed in 
terms of the bulk modulus, 𝐾, and shear modulus, 𝜇, as follows: 
𝒄e = 𝐾𝟏 ⊗𝟏 + 2 𝜇
( 
𝑰 −1 
3 𝟏 ⊗𝟏
) 
. 
(36) 
Here, 𝑰is the fourth rank symmetric identity tensor with com- 
ponents 𝐼𝑖 𝑗 𝑘𝑙 = ( 𝛿𝑖𝑘 𝛿𝑗𝑙 + 𝛿𝑖𝑙 𝛿𝑗𝑘 )∕2 (Einstein’s notation is assumed) 
and 𝟏 is the second-order identity tensor. Two different yield 
criteria are adopted in this study to simulate the elastoplastic 
behavior of soils, the Drucker–Prager and the MCC models. For 
further details on the yield criteria, the reader is referred to [ 17, 18 ], 
and for the return mappings in the context of the SPH method to 
[ 33 ]. 
3.6 
Time Stepping and Numerical Stability 
Time integration stability of the discretized equations is guaran- 
teed by choosing the minimum time step required to calculate 
both the solid displacement 𝒖 , and the pore fluid pressure 𝑝𝑤 , 
Δ𝑡 ≤min (Δ𝑡𝑠 , Δ𝑡𝑤 ) 
(37) 
where the time step for the solid displacement arises from the CFL 
condition, 
Δ𝑡𝑠 ≤ 𝑎ℎ 
𝑐 
(38) 
with 𝑐the numerical sound speed of the solid phase. The 
maximum time step for fluid pressure is given by a similar von 
Neumann stability analysis (see [ 53 ]), 
Δ𝑡𝑤 ≤𝑎𝐶𝑤 ℎ2 
𝑘 
(39) 
where 𝑎 ≤ 1 , ℎ = 𝑘ℎ Δ is the smoothing length with 𝑘ℎ the 
smoothing length factor, and 𝐶𝑤 =
𝜌𝑤 𝑔𝑛 
𝐾𝑤 . In general, 𝑎 = 0 . 1 [ 20, 
38 ] not only provides the method with stability, but also the 
necessary accuracy in the integration process. 
The stability of the PPE approach, while still constrained by 
the CFL condition, is also governed by the parameter 𝑎∗ , which 
multiplies the pressure correction and effectively acts as a gain or 
amplification factor in the explicit Poisson update. The implicit 
correction step introduces this feedback parameter 𝑎∗ 
𝑎∗ ( 𝑘 , Δ𝑡 ) =
𝑏𝜌∗ 
𝜌∗ + 𝑏Δ𝑡 , 
𝑏 = 𝜌𝑤 𝑔 
𝑘 , 
(40) 
which controls the amplitude of the pore-pressure adjustment. 
For very small time increments, Δ𝑡 →0 , 𝑎∗ →𝑏, which can 
become arbitrarily large as the permeability decreases. In this 
regime the pressure correction acts with excessive gain, leading to 
numerical instability. Conversely, for Δ𝑡 →∞, one obtains 𝑎∗ →
𝜌∗ ∕Δ𝑡 →0 , which damps the feedback and stabilizes the scheme. 
Therefore, admissible time steps must lie within a bounded 
interval 
Δ𝑡min ( 𝑘) ≤ Δ𝑡 ≤ Δ𝑡CFL 
max , 
(41) 
where the lower limit Δ𝑡min ( 𝑘) is defined implicitly by requiring 
that 𝑎∗ ( 𝑘 , Δ𝑡 ) remain below a prescribed stability threshold, for 
example, 𝑎∗ < 1 . In practice, stability is achieved by choosing 
Δ𝑡within the overlap between the CFL restriction and the 𝑎∗ - 
based lower bound, ensuring both accurate resolution of wave 
propagation and controlled pressure correction. In contrast to 
the hypothesis of Morikawa and Asai [ 67 ] for the 𝒖 – 𝒘 – 𝑝𝑤 
formulation, where the additional stability condition on 𝑘and Δ𝑡
imposed an upper bound on the admissible time step, the PPE 
formulation introduces a lower bound through 𝑎∗ . This reversal 
creates an additional challenge: Stability in the 𝒖 – 𝑝𝑤 system 
requires time steps that are neither too large (CFL) nor too small 
( 𝑎∗ ), restricting the feasible range more severely. For a discussion 
on the stabilization techniques employed in the paper, the reader 
is referred to Supporting Information Section I. 
8 of 31
International Journal for Numerical and Analytical Methods in Geomechanics, 2026

## Page 9

FIGURE 1 
Setup (left) and contours of the normalized pore pres- 
sure 𝑝𝑤 ∕𝑞0 at different values of the dimensionless time factor 𝑇𝑣 
(right) for the 1-D consolidation problem. Solution obtained with the PR 
formulation. 
4 
Formulation Verification 
In this section, we verify the performance of the two different 
𝒖 – 𝑝𝑤 formulations against analytical solutions from a series of 
different poroelasticity problems as well as against the analytical 
solutions to stress paths in undrained triaxial tests using the 
MCC model. 
4.1 
1D Consolidation 
As a first problem, we consider the one-dimensional consolida- 
tion of a poroelastic column, known as the Terzaghi consolidation 
problem, both under an applied external load and due to self- 
weight. R esults from self-weight consolidation are provided in 
Supporting Information Section II (see Figures S1 and S2 ). The 
soil column is 1.0-m high and 0.1-m wide and is discretized into 
1000 particles with an initial interparticle distance of Δ = 0 . 01 m 
(following [ 53–55, 67, 110 ], see the schematic in Figure 1 ). The 
effects of gravity are not included in the consolidation problem 
under external load. The Young’s modulus and the Poisson’s 
ratio of the solid skeleton were 𝐸 = 2e 6 Pa and 𝜈= 0 . 3 , the bulk 
modulus of the fluid was 𝐾𝑤 = 2e 8 Pa, the porosity was 𝑛 = 0 . 3 , 
the conductivity was 𝑘 = 1e − 3 m/s, and the chosen time step was 
Δ𝑡= 1e − 6 s. The bottom and lateral boundaries were assumed 
undrained, and a free surface with zero pore pressure is assigned 
to the top. To initiate consolidation, an external load of magnitude 
𝑞0 = − 10 kPa was applied to the free surface particles in the form 
of an equivalent acceleration. Simulations are performed both 
with the PPE and PR formulations. 
Terzaghi, in his one-dimensional consolidation theory, proposed 
an analytical solution for the excess pore pressure build-up, and 
then dissipation, as a function of time and of soil column depth, 
𝑧, 
𝑝𝑤 ( 𝑧) =
𝑗=∞
∑
𝑗= 1 
2 𝑝𝑤 
0 
𝑀 sin 
( 𝑀𝑧 
𝐻 
) 
exp ( − 𝑀2 𝑇𝑣 ) 
(42) 
where 𝑝𝑤 
0 = 𝑞0 is the initial excess pore pressure which holds if the 
fluid and the solid particles are incompressible, 𝐻is the column 
height, 𝑇𝑣 = 𝑐𝑣 𝑡∕𝐻2 is a dimensionless time factor, 𝑀 = 0 . 5(2 𝑗 − 
1) 𝜋, and 
𝑐𝑣 =
𝑘(1 − 𝜈) 𝐸 
(1 + 𝜈)(1 − 2 𝜈) 𝜌𝑤 𝑔 
(43) 
is the consolidation coefficient. 
In Figure 2 , we compare the results of the analytical solutions for 
the pore pressure against the pore pressure histories determined 
from the SPH simulations using the PR formulation, given 
different combinations of the numerical stabilization parameters, 
𝛼and 𝜉, from the artificial viscosity and kinematic damping, 
respectively. The artificial viscosity parameter 𝛽is kept at a value 
of 0.0. Contours of the normalized pore pressure 𝑝𝑤 ∕𝑞0 are 
displayed at different elapsed dimensionless time in Figure 1 for 
the simulation with 𝛼= 0 and 𝜉= 4e − 5 . 
As seen from the simulation results, some combination of 
artificial viscosity and kinematic damping is needed in order for 
the solution not to diverge. In general, the artificial viscosity 
alone is enough to stabilize the solution, although there is some 
slight error for the earlier dimensionless times of 𝑇𝑣 = 0 . 005 and 
𝑇𝑣 = 0 . 05 towards the bottom of the soil column. Greater accuracy 
relative to the analytical solution is shown for simulations with 
kinematic damping and 𝜉> 0 , although if the kinematic damping 
becomes too large, the system becomes overdamped, leading to 
errors in the earlier dimensionless times, although in the case of 
𝜉= 1e-4, these are still small. From testing, we see that the ideal 
range for 𝜉is between 10 and 50 times the magnitude of the time 
step, and that the stabilization effects of 𝛼on the solution are 
largely superfluous. Thus, because large 𝛼is known to excessively 
dissipate energy from the system, we keep 𝛼= 0 . 1 going forward 
in the coupled hydromechanical simulations, a value agreeing 
with other works in the literature [ 22 ]. 
To test the robustness of the PR formulation under different 
hydraulic conductivities, we perform two additional simulations 
with 𝑘 = 1e − 2 and 𝑘 = 1e − 4 m/s noting good agreement with 
the analytical solutions as seen in Figure 3 especially as the 
conductivity is decreased. 
Similarly, we compare the performance of the PPE formulation 
under different conductivities against the analytical solutions, 
as seen in Figure 4 . In all three simulations, the time step 
is kept fixed at Δ𝑡 = 1e − 6 s. The simulation with 𝑘 = 1e − 
4 m/s does not converge and the simulation with 𝑘 = 1e − 
3 m/s has some error at 𝑇𝑣 = 0.005 towards the bottom half 
of the soil column but is otherwise satisfactory. For 𝑘 = 1e 
− 2 m/s however, the simulation results follow the analytical 
solution closely. The loss of stability in the 𝑘 = 1e − 4 m/s 
simulation can be attributed to the amplification factor 𝑎∗ , 
which significantly outgrows that of the 𝑘 = 1e − 3 m/s and 
𝑘 = 1e − 2 m/s simulations (see Figure 5 ), requiring a larger 
time step, which is at odds with the requirement from the 
CFL condition. In the case of 𝑘 = 1e − 3 m/s, increasing the 
time step by an order of magnitude to Δ𝑡 = 1e − 5 s has the 
effect of decreasing the amplification factor by around 5%–
10%, which is enough to improve fidelity with respect to the 
analytical solutions, see Figure 6A . Note that for the range 
of parameters used in the simulations presented in this work, 
the PPE formulation is limited to 𝑘 > 10e − 4 m/s. For those 
International Journal for Numerical and Analytical Methods in Geomechanics, 2026
9 of 31

## Page 10

FIGURE 2 
Normalized pore pressure 𝑝𝑤 ∕𝑞0 profiles compared to the theoretical solutions at 𝑇𝑣 = 0 . 005 , 0.05, 0.1, 0.25, 0.4, 0.5, 0.7, 1.0 for 𝑘 = 1e 
− 3 m/s and Δ𝑡 = 1e − 6 s, for varying values of the artificial viscosity parameter 𝛼and the damping coefficient 𝜉. Solutions obtained with the PR 
formulation. 
FIGURE 3 
Normalized pore pressure 𝑝𝑤 ∕𝑞0 profiles compared to the theoretical solutions at 𝑇𝑣 = 0 . 005 , 0.05, 0.1, 0.25, 0.4, 0.5, 0.7, 1.0 for 𝑘 = 1e 
− 2 m/s, 𝑘 = 1e − 3 m/s, and 𝑘 = 1e − 4 m/s. Δ𝑡 = 1e − 6 s, 𝜉= 4e − 5 and 𝛼= 0 . 1 . 
conditions, time steps obtained using the CFL condition (Equa- 
tion 39 ) can be used without significantly affecting the accuracy 
of results. 
The analytical solution for free surface settlement 𝑆of the soil 
column as a function of time is expressed as 𝑆( 𝑇𝑣 ) = 𝐻 𝑞0 𝑚𝑣 𝑈 , 
and 𝑈is the degree of consolidation given by the following: 
𝑈 = 1 −
𝑗=∞
∑
𝑗 
2 
𝑀2 exp ( − 𝑀2 𝑇𝑣 ) . 
(44) 
10 of 31
International Journal for Numerical and Analytical Methods in Geomechanics, 2026

## Page 11

FIGURE 4 
Normalized pore pressure 𝑝𝑤 ∕𝑞0 profiles for PPE approach compared to the theoretical solutions at 𝑇𝑣 = 0 . 005 , 0.05, 0.1, 0.25, 0.4, 0.5, 
0.7, 1.0 for 𝑘 = 1e − 2 m/s, 𝑘 = 1e − 3 m/s, and 𝑘 = 1e − 4 m/s. Δ𝑡 = 1e − 6 s, 𝜉= 4e − 5, and 𝛼= 0 . 1 . 
FIGURE 5 
Amplification factor 𝑎∗ as a function of time step Δ𝑡for 
three different conductivity values, highlighting excessive gain for smaller 
conductivities at smaller time steps. 
We note that 𝐻𝑞0 𝑚𝑣 is the final surface settlement of the soil 
column after the excess pore pressure is fully dissipated, and 𝑚𝑣 
is the compression index defined as follows: 
𝑚𝑣 = (1 + 𝜈)(1 − 2 𝜈) 
(1 − 𝜈) 𝐸 
. 
(45) 
In Figure 6B , the normalized settlement 𝑆∕𝐻is plotted as a 
function of 𝑇𝑣 comparing the performance of both PPE and PR 
formulations against the analytical solutions. We see that the PR 
formulation follows the analytical solution very closely, but the 
solution from the PPE formulation is not as close with increasing 
dimensionless time, and experiences some slight oscillation 
around the theoretical solution. This oscillation may be attributed 
to the lower stability of the PPE formulation for usual time steps, 
and to an increased susceptibility to boundary effects near solid 
boundaries. The lower consistency on the approximation of pore 
water pressures on the boundaries potentially counteract the 
numerical damping necessary to reduce oscillations in the pore 
pressure field. 
Overall, because of the decreased stability and additional time 
stepping restrictions in the PPE formulation, especially so around 
small conductivities pertaining to the undrained regime, which 
are of interest in the retrogressive landslides studied in this paper, 
we opt to use the pore PR form of the 𝒖 – 𝑝𝑤 formulation for the 
remaining examples in the paper. The PR formulation also has 
the additional advantage that some degree of compressibility is 
allowed for the fluid phase. 
4.2 
Cryer’s Problem 
A classical problem from poroelasticity is Cryer’s problem, where 
a poroelastic sphere with a drained exterior surface boundary 
is subjected to a uniform normal traction 𝑝0 at the surface. At 
the center of the sphere, the pore pressure initially attains the 
value of the traction 𝑝0 and then continues to rise to a peak 
value before dissipating to zero. The pore pressure increase past 
𝑝0 is caused by fluid draining along the surface boundary of the 
sphere, in turn leading to the transfer of a significant portion 
of the external applied load towards the center of the sphere 
as the region facing the surface contracts due to pore pressure 
dissipation. This nonmonotonic pore pressure behavior is known 
as the Mandel–Cryer effect [ 29, 61 ], and can only be modeled 
through a fully coupled solution such as that from the 𝒖 – 𝑝𝑤 
set of equations stemming from Biot–Zienkiewicz theory, and 
not from uncoupled solutions such as Terzaghi’s one-dimensional 
consolidation theory. Thus, Cryer’s problem is used as a final 
example to check the accuracy of the 𝒖 – 𝑝𝑤 pore PR formulation 
for poroelasticity. 
The analytical solution for the pore pressure at the center of the 
sphere, that is, at 𝑅 = 0 , is given by the following: 
𝑝𝑤 ( 𝑅 = 0) 
𝑝0 
= 𝜂
∞
∑
𝑗= 1 
sin 𝜉𝑗 − 𝜉𝑗 
𝜂𝜉𝑗 cos 𝜉𝑗 ∕2 + ( 𝜂− 1) sin 𝜉𝑗 
exp 
(
− 𝜉2 
𝑗 𝑐𝑣 𝑡∕𝑎2 )
(46) 
where the coefficients 𝜉𝑗 are the positive roots of the equation 
(
1 − 𝜂𝜉2 
𝑗 ∕2
)
tan 𝜉𝑗 = 𝜉𝑗 . 
(47) 
Here the parameter 𝜂= (1 − 𝜈)∕(1 − 2 𝜈) holds for the case of 
incompressible fluid and incompressible solid matrix [ 97 ]. 
Figure 7B plots the normalized pore pressure at the center of the 
sphere as a function of dimensionless time 𝑇𝑣 for four different 
simulations with different Poisson’s ratios, agreeing well with 
the theoretical solution, and capturing the Mandel–Cryer effect. 
As expected, decreasing the Poisson’s ratio has the effect of 
International Journal for Numerical and Analytical Methods in Geomechanics, 2026
11 of 31

## Page 12

FIGURE 6 
(A) Normalized pore pressure 𝑝𝑤 ∕𝑞0 profiles compared to the theoretical solutions at 𝑇𝑣 = 0 . 005 , 0.05, 0.1, 0.25, 0.4, 0.5, 0.7, 1.0 for 
𝑘 = 1e − 3 m/s and Δ𝑡 = 1e − 5 s, 𝛼= 0 . 1 , 𝜉= 4e − 4 and the PPE formulation. (B) Comparison of the normalized settlement 𝑆∕𝐻as a function of 𝑇𝑣 
for both the PPE and PR formulations. Note the results from the PR formulation are those shown with Δ𝑡 = 1e − 6 s, 𝛼= 0 . 1 , and 𝜉= 4e − 5. 
FIGURE 7 
(A) Schematic of Cryer’s problem with the poroelastic sphere of radius 𝑅 = 𝑎subjected to an all-around pressure 𝑝0 , and snapshots at 
different 𝑇𝑣 showing a cross section of the sphere with contours of the normalized pore pressure 𝑝𝑤 ∕𝑝0 for the simulation with Poisson’s ratio 𝜈= 0 . 3 . 
(B) Normalized pore pressure at the center of the sphere as a function of 𝑇𝑣 from the analytical solutions [ 97 ] compared to the GEOSPH simulations 
for 𝜈= 0 . 1 , 0 . 2 , 0 . 3 , 0 . 45 . Δ𝑡 = 1e − 6 s, 𝛼= 0 . 1 , 𝜉= 4e − 5. Other than the varying Poisson’s ratio, the same elastic and material parameters as the 
one-dimensional Terzaghi consolidation simulation are used. 
enhancing the pore pressure peak past the magnitude of the 
external traction. In Panel A of the figure, contours of the pore 
pressure are shown over a hemisphere to visualize the pore 
pressure increase and decay at the center. 
4.3 
Triaxial Testing in Undrained Limit 
To test the 𝒖 – 𝑝𝑤 formulation in conjunction with an elastoplastic 
constitutive model, we perform a series of triaxial tests under 
undrained conditions using the MCC model. We also compare 
these simulation results against those from similar triaxial simu- 
lations conducted with the weakly coupled undrained framework 
in [ 33 ]. The soil cylinder used in the simulations is 0.15-m high, 
has a diameter of 0.05 m, and is discretized using 53,175 particles, 
with an initial interparticle distance of 0.002 m. The top and 
bottom surfaces of the cylinder are constrained by a layer of 
boundary particles, with the bottom fixed, and the top subjected 
to a constant velocity 𝑉 = 0 . 01 m/s in the vertical direction 
to compress the soil cylinder. Free-slip boundary conditions 
are applied to both sets of boundary particles at the top and 
bottom surfaces of the cylinder. All relevant material parameters 
from the soil pertaining to the MCC model are the same as 
in [ 33 ]. A permeability of 𝑘 = 1e − 8 m/s is used to achieve 
undrained conditions within the sample. To avoid any pore 
fluid dissipation at the boundaries and to ensure the sample is 
completely undrained, the free surfaces are treated as undrained, 
and the free surface detection procedure for drained free surfaces 
is not performed. To apply the confining pressure 𝜎𝑐 , the flexible 
confined boundary conditions of Zhao et al. [ 114 ] are imposed on 
the lateral free surfaces of the cylinder. 
Following the same procedure outlined in [ 33 ], stress and 
deformation data are averaged from all the particles within 
a measurement region (cube) with a side length of 0.03 m 
located at the center of the sample to ensure that the stress 
state of the measured particles follows a triaxial state and to 
mitigate any particle disorder effects within the sample. In total, 
three undrained simulations are performed, the first consisting 
of a lightly overconsolidated soil test (TU-L), a moderately 
12 of 31
International Journal for Numerical and Analytical Methods in Geomechanics, 2026

## Page 13

FIGURE 8 
Results of undrained triaxial test simulation using the 𝒖 – 𝑝𝑤 formulation and GEOSPH for a lightly overconsolidated soil (TU-L). The 
stress history in 𝑝′ − 𝑞space is shown in (A) whereas the trajectory in log ( 𝑝′) − 𝑒space is displayed in (B), and both are compared against the theoretical 
solutions of Wood, see Supporting Information Section IV [ 102 ]. The blue to red color scheme depicts the temporal evolution of the load path computed 
with SPH. In panel (C), a magnified region of panel (A) is shown comparing the 𝒖 – 𝑝𝑤 solution to the undrained framework of [ 33 ]. Snapshots of pore 
pressure 𝑝𝑤 are shown at initial yielding (D) and at the CSL line (E) for the implementation without (left) and with (right) the Shepard regularization 
technique. 
overconsolidated test (TU-M), and a normally consolidated test 
(TU-N). The initial preconsolidation pressure, ( 𝑝𝑐 )0 , was 200 kPa, 
and the applied confining pressure, which equaled the initial 
mean effective stress, was 150 kPa for TU-L, 200 kPa for TU-N, 
and 30 kPa for TU-M. Results for the TU-L test can be seen in 
Figure 8 , whereas for the TU-N and TU-M simulations, they are 
displayed in Figure S3 and Figure S4 , respectively, in Supporting 
Information Section III. For all three tests, the stress paths from 
the SPH simulations closely follow the theoretical solution in 𝑝′ − 
𝑞space as seen in Panel A, as well as in log ( 𝑝′) − 𝑒space in Panel 
B, and the sample exhibits undrained behavior. In Panel C, we also 
plot the stress path of the equivalent undrained simulation for 
reference, showing how the 𝒖 – 𝑝𝑤 solution follows a stress path 
closer to the analytical solution than does the undrained solution, 
and also reaches the critical state line closer to the point where 
the analytical solution intersects. A discussion of the relative 
computational efficiency and costs of the undrained versus 𝒖 – 𝑝𝑤 
formulations is shown in Supporting Information Section V (see 
Figure S5 ). 
The evolution of the pore pressure within the measurement 
region in the SPH simulations is evaluated against predictions 
from theoretical solutions, and is shown in Figure 9 . The pore 
pressure compensates for the stresses not captured by the mean 
effective pressure 𝑝′. For the lightly overconsolidated (TU-L) and 
normally consolidated (TU-N) soils, it rises and asymptotically 
FIGURE 9 
Pore pressure ( 𝑝𝑤 ) histories for the three undrained 
simulations TU-M ( 𝑝0 = 30 and ( 𝑝𝑐 )0 = 200 kPa), TU-L ( 𝑝0 = 150 and 
( 𝑝𝑐 )0 = 200 kPa), and TU-N ( 𝑝0 = 200 and ( 𝑝𝑐 )0 = 200 kPa), performed 
with the 𝒖 – 𝑝𝑤 formulation compared to the undrained framework of [ 33 ] 
both implemented in GEOSPH , and to the theoretical solutions of Wood 
[ 102 ]. 
approaches a peak value as the stress state reaches the CSL. In 
TU-L, a slight kink appears at yielding, consistent with theoretical 
predictions. In contrast, for the moderately overconsolidated (TU- 
M) soil, yielding causes the yield locus to contract, leading to 
International Journal for Numerical and Analytical Methods in Geomechanics, 2026
13 of 31

## Page 14

FIGURE 10 
(A) Retrogressive slope failure simulation setup. (B) Initialized pore pressure 𝑝𝑤 and initialized effective vertical stress (C) after 
𝐾0 = 0 . 5 and gravity loading. 
a reduced difference between total and effective loading paths 
and a gradual decline in pore pressure. Again the 𝒖 – 𝑝𝑤 solution 
shows slightly improved accuracy over the undrained framework, 
especially for axial strains greater than 5% in magnitude. 
5 
Retrogressive Slope Failure 
In this section, we compare the ability of the 𝒖 – 𝑝𝑤 formulation 
developed in this work and the undrained framework of [ 33 ] to 
capture the flowslide and spread type retrogressive failures of 
slopes under undrained conditions using the SPH method. In the 
case of the 𝒖 – 𝑝𝑤 simulation, a very low permeability is used 
to achieve the undrained limit or quasi-undrained conditions. 
We take advantage of a benchmark slope geometry employed for 
simulating retrogressive slope failure behavior in sensitive clays 
in previous studies [ 22, 80 ], and focus on the effects of slope height 
and inclination on the landslide characteristics by considering 
two distinct computational models. 
To capture the behavior of sensitive clay, an elastoplastic model 
with isotropic strain softening behavior is used in conjunction 
with the Drucker–Prager yield criterion. The strain softening 
component degrades the strength parameters of the soil, namely 
the friction angle 𝜙and the cohesion 𝑐as a function of the accu- 
mulated plastic strain 𝜀𝑝 
𝑎 𝑐 𝑐 , following the exponential softening 
rules of [ 106 ]: 
⎧ 
⎪ 
⎨ 
⎪ 
⎩ 
𝑐 = 𝑐𝑟 + ( 𝑐𝑝 − 𝑐𝑟 ) 𝑒− 𝜂𝜀𝑝 
𝑎 𝑐 𝑐 
𝜙= 𝜙𝑟 + ( 𝜙𝑝 − 𝜙𝑟 ) 𝑒− 𝜂𝜀𝑝 
𝑎 𝑐 𝑐 
(48) 
where the subscripts 𝑝and 𝑟denote peak and residual values 
of cohesion and friction, respectively, while 𝜂is the softening 
coefficient (or shape factor), which controls the rate of strength 
degradation as a function of the plastic strain. 
Two distinct sensitive clay slopes are analyzed with their respec- 
tive geometries shown in Figure 10 . The computational domain 
of the first (Panel A) consists of a 5-m-high slope at an inclination 
of 45 ◦, with a length of 25 m along the base and a length 
along the top of 20 m. The slope is discretized into 11,275 SPH 
particles, with an initial interparticle distance of Δ = 0 . 1 m, and 
the slope is supported by boundary particles along the base 
(no-slip condition) and left side wall (free-slip condition). The 
computational domain of the second (Panel D) steeper slope, is 
8-m-high, and possesses a length along the top of 16 m, and a 
length along the base of 17 m. The domain is also discretized 
with the interparticle distance of Δ = 0 . 1 m, into 8470 particles, 
and with similar boundary conditions as in the shallower slope 
model. In the simulations, we use the Wendland 𝐶2 kernel, with 
a smoothing length factor of 1.5. To compare the strongly coupled 
poromechanical model with a penalty-based approach suited 
for undrained conditions, two different sets of simulations are 
performed for each slope model, one with the 𝒖 – 𝑝𝑤 formulation 
presented here, and the second with the undrained framework of 
[ 33 ]. 
The sensitive clay material comprising both slope models 
is assumed spatially homogeneous with an isotropic elastic 
response with Young’s modulus 𝐸 = 25 . 0 MPa, and Poisson’s 
ratio 𝜈= 0 . 3 . The density of the mixture is 𝜌= 2 , 150 kg/ m3 , 
while that of water is 𝜌𝑤 = 1000 kg/ m3 , and the porosity is 
𝑛 = 0 . 4 . Since undrained conditions are assumed, the value of 
the internal friction angle is set to 𝜙= 𝜙𝑢 = 0◦, which reduces 
the Drucker–Prager model to the isochoric von Mises model, 
preventing the accumulation of volumetric plastic strains. The 
peak cohesion is 𝑐𝑝 = 15 . 1 kPa, the residual cohesion, 𝑐𝑟 = 1 . 5 
kPa, the softening coefficient is 𝜂= 5 , and the dilatancy angle 
is 𝜓 = 0◦. In both undrained and 𝒖 – 𝑝𝑤 simulations, the bulk 
modulus of the fluid equals 𝐾𝑤 = 0 . 2 GPa, and in the 𝒖 – 𝑝𝑤 
simulation, the permeability is 𝑘 = 1e − 8 m/s to create quasi- 
undrained conditions. The soil is assumed fully saturated with 
the water table coinciding with the slope’s free surfaces. In the 
simulations, stresses are first initialized using the earth pressure 
coefficient of 𝐾0 = 0 . 5 , and then with a gravity loading such that 
the stresses achieve a geostatic state, where the particles reach 
a minimum kinetic energy. In the gravity loading simulation, 
the peak strength parameters are used for the soil together with 
𝜂= 0 to stabilize the slope and achieve consolidation (for the 
𝒖 – 𝑝𝑤 simulation). The resulting effective stresses and pore 
pressures are taken for the retrogressive landslide simulation, 
which is triggered by setting 𝜂= 5 and applying a strength 
reduction factor of 1.65 to the soil’s cohesion. In the undrained 
simulation, the pore pressure is initialized to the hydrostatic 
condition prior to the strength reduction procedure, and the 
14 of 31
International Journal for Numerical and Analytical Methods in Geomechanics, 2026

## Page 15

FIGURE 11 
Retrogressive failure simulation progression over time for the simulation conducted with the undrained model. Contours show 
accumulated plastic strain. 
gravity loading step is performed under dry conditions. In terms 
of other simulation parameters, the time step is Δ𝑡 = 1e − 6 s, the 
artificial viscosity, 𝛼𝜋= 0 . 1 , and the damping coefficient is 𝜉= 1e 
− 5. Both simulations were run for a duration of 20 s. 
5.1 
5-m-High Slope Simulation 
In Figure 11 , snapshots at different moments in time, over the 
duration of the undrained simulation, show contours of the 
accumulated plastic strain and the evolution of the retrogressive 
slope failure process, with emerging slip planes and zones of 
localized plastic strain. In Figure 12 , contours of the displacement 
are shown at the same time steps. Due to the strength reduction, 
the clay slope becomes unstable and lateral spreading initiates, 
leading to the development of an initial horizontal zone of 
localized plastic strain or shear band along the base of the slope 
propagating inwards away from the slope toe. Within the localized 
zones of plastic strain, the clay undergoes remolding and the 
strength is reduced through the strain softening model promoting 
sliding. The bottom horizontal shear band proceeds to curve 
upwards as it continues propagating, and reaches the top surface 
after 0.6 s of simulation time. Subsequently, a secondary shear 
band forms, located closer to the slope toe, forming two distinct 
and competing slip surfaces leading to sliding events with circular 
failure surfaces, denoted Slides 1a and 1b (Figure 12 ). As the 
initial slope failure continues, the sliding masses disintegrate, 
breaking up into pieces delimited by secondary shear bands, as 
first seen around 1.5 s of simulation time with the development of 
a secondary v-shaped band, characteristic of some retrogressive 
landslides. The broken up soil blocks spread and flow as they 
are deposited on the base, and an unstable back-scarp is exposed 
behind the sliding soil mass along the slip plane of Slide 1b, 
causing the development of a second slip surface (for Slide 2) 
after 3.5 s of simulation time. Slide 2 lasts until around 6.5 s of 
simulation time and is followed by a third slide whose slip surface 
is fully traced after around 8 s. After the third sliding event, 
sufficient failed mass is in place to buttress the exposed back- 
scarp, ending the retrogressive failure process. In the simulation, 
the final run-out distance was approximately 21.6 m and the final 
retrogression distance was 14.0 m (see Figure 12 ). 
A few noteworthy observations can be drawn pertaining to the 
structure of the retrogressive slope failure. The slope fails under 
a series of successive retrogressive slides involving rotational slip 
surfaces, typical of flowslides. After the rotational failure part of 
the different sliding events is concluded, however, the disturbed 
failed soil mass now experiences spreading, reshaping the soil 
into intact Δ-shaped horsts and ∇ -shaped grabens. The horsts 
and grabens become especially visible after 5.5–8.0 s of simulation 
time, and the angle between the sliding surface and the horsts 
is close to the theoretical prediction of 45 ◦± 𝜙𝑢 ∕2 = 45◦. The 
undrained simulation manages to successfully capture the flow 
of remolded clay between the model base and the graben and 
horst blocks in addition to the squeezing of this clay through 
localized strain zones between the intact blocks. Lastly, the mass 
displaced by the three main sliding events is similar, matching 
field observations [ 48, 93 ]. In this way, the undrained simulations 
predict flow and then some degree of spread behavior in the 
same landslide. 
Results from the counterpart strongly coupled hydromechanical 
simulation using the 𝒖 – 𝑝𝑤 formulation, instead of the undrained 
framework, are displayed in Figures 13 and 14 , again showing 
International Journal for Numerical and Analytical Methods in Geomechanics, 2026
15 of 31

## Page 16

FIGURE 12 
Retrogressive failure simulation progression over time for the simulation conducted with the undrained framework. Contours show 
displacement. 
FIGURE 13 
Retrogressive failure simulation progression over time for the simulation conducted with the 𝒖 – 𝑝𝑤 formulation and 𝑘 = 1e − 8 m/s. 
Contours show accumulated plastic strain. 
16 of 31
International Journal for Numerical and Analytical Methods in Geomechanics, 2026

## Page 17

FIGURE 14 
Retrogressive failure simulation progression over time for the simulation conducted with the 𝒖 – 𝑝𝑤 formulation and 𝑘 = 1e − 8 m/s. 
Contours show displacement. 
FIGURE 15 
(A) Evolution of the kinetic energy and (B) horizontal velocities over progressive failure for the undrained and 𝒖 – 𝑝𝑤 simulations. 
the accumulated plastic strains and displacements, respectively. 
Initially, the slope fails through two competing curved failure 
surfaces, which exhibit less curvature than those forming in 
the undrained simulation, and are accompanied by an inclined 
v-shaped band pointing towards the slope toe. After 1.5 s of 
simulation time, the soil between the first failure surface and 
the v-shaped band begins to subside, leaving the toe of the 
slope relatively untouched, and leading to the development of 
an additional failure surface upslope (Slide 2). The failing soil 
mass resulting from these two slides is gradually reshaped into 
blocks of horsts and grabens. From here on out, the retrogressive 
landslide becomes fully dominated by the spreading mechanism, 
and by 5.5 s, two inclined shear bands are fully traced forming an 
additional set of graben and horsts after active failure, and the 
subsidence of the block is bounded by the two inclined bands 
(graben). The slope continues to spread with some of the grabens 
splitting into subblocks, until a total runout distance of 19.5 m 
is reached, and a retrogression distance of 20 m is obtained (in 
part due to a lack of more soil material left to fail in the crater). 
As is common in spread-type retrogressive landslides [ 94 ], the 
retrogression distance is larger than the runout distance, and 
it is noteworthy that despite the structural differences between 
the undrained and the 𝒖 – 𝑝𝑤 simulations, the runout distances 
are similar. 
In Figure 15 , the evolution of the kinetic energy (Panel A) and 
the horizontal velocities, that is, both the maximum and front 
velocities (Panel B) are reported for the undrained simulation 
in Figure 15 . Three peaks correspond in time to the three major 
sliding events that release significant pulses of kinetic energy. At 
the conclusion of the slide, the kinetic energy of the mobilized 
mass dissipates considerably, leading to an overall decrease of 
International Journal for Numerical and Analytical Methods in Geomechanics, 2026
17 of 31

## Page 18

FIGURE 16 
Comparison of pore pressure ( 𝑝𝑤 ) and excess pore pressure (excess 𝑝𝑤 ) contours for the undrained and 𝒖 – 𝑝𝑤 simulations. 
the kinetic energy of the whole slope. In terms of the front and 
maximum velocities, only one main peak is observed after the 
first slide, followed by a gradual decrease of the velocities. Addi- 
tionally, we note that the front velocity is close to the maximum 
velocity of the system, and generally tracks its behavior. As the 
third slide comes to a conclusion and sufficient mass stabilizes, 
both the kinetic energy and the velocity reduce to near zero. 
In Figure 15 , the kinetic energy evolution indicates three pulses 
corresponding to the temporal locations of the three main sliding 
events (the third, being the subsidence of a horst–graben com- 
plex). The magnitude of the kinetic energy is slightly less in the 
𝒖 – 𝑝𝑤 simulation relative to the undrained simulation for the first 
two peaks, although for the third and the rest of the simulation is 
slightly larger. This fact, and the smaller velocities, both at the 
slide front and the maximum velocity within the slope as seen in 
Panel B, can be explained with the larger kinetic energy released 
over a shorter time span in the rotational slides, as opposed to the 
horst–graben active failure events seen in spreading. In addition, 
the 𝒖 – 𝑝𝑤 formulation naturally dissipates energy via fluid–solid 
coupling and excess pore pressure dissipation, leading to lower 
kinetic energy over time compared to the undrained simulation, 
which lacks this mechanism. In both simulations, despite their 
different hydromechanical models, the kinetic energy eventually 
decays, as basal friction and viscosity-like resistance arrests the 
spreading (or flowing) sensitive clay. 
One of the main advantages of the 𝒖 – 𝑝𝑤 formulation in its 
application to retrogressive landslides is its ability to capture 
long-term drainage and pore pressure diffusion, which is a 
prominent feature of spreading failures. In Figure 16 , contours of 
the pore pressure and of the excess pore pressure at different time 
steps are juxtaposed for both undrained and 𝒖 – 𝑝𝑤 simulations. 
In the 𝒖 – 𝑝𝑤 simulation, the horsts undergo extension, even 
though the dilatancy angle is zero, which leads to negative excess 
pore pressures. This feature is visible as early as 4.5 s into the 
simulation after the failed mass resulting from the second slide 
begins to reshape into horsts and grabens. By 14.0 s of simulation 
time, after significantly more spreading, positive excess pore 
pressure is visible in the grabens where contraction occurs as 
a result of subsidence, as they depress between the inclined 
bounding slip surfaces. The excess pore pressure is localized 
towards the bottom of the model as pore fluid is pressed-up 
against the model base. In the undrained simulation, similar 
negative pore pressures are obtained in the horsts and, to a 
lesser extent, positive excess pore pressures are found in the 
grabens, although both horsts and grabens are less-well developed 
than in the 𝒖 – 𝑝𝑤 simulation. Also notable of the undrained 
simulation is the substantial positive excess pore pressure that 
occurs in the highly compacted toe of the landslide as well as 
in other regions experiencing elastic compressive strains. This 
feature also differs substantially from the run-out zone of the 
𝒖 – 𝑝𝑤 simulation where the dissipation of pore pressures within 
the flowing debris occurs as the disturbed clay consolidates. We 
note the dissipation/consolidation of pore pressures can only be 
modeled in the strongly coupled solid–fluid deformation 𝒖 – 𝑝𝑤 
simulation. In the majority of the shear bands in the undrained 
simulation, however, some amount of dilative elastic strains are 
observed, as seen in the snapshot at 𝑡 = 4.5 s, leading to large 
negative excess pore pressures, in many cases far larger than those 
observed in the 𝒖 – 𝑝𝑤 simulation. 
It is worth pointing out that no special treatment for negative pore 
water pressures was implemented, but our numerical experience 
18 of 31
International Journal for Numerical and Analytical Methods in Geomechanics, 2026

## Page 19

FIGURE 17 
Retrogressive failure simulation progression over time for the 8-m-high slope simulation conducted with the undrained formulation. 
Contours show accumulated plastic strain. 
shows that for the typical problems of geotechnical engineering 
and the ones simulated here, the negative water pressures are 
relatively low and arising from small volumetric dilation, which 
in practice would not cause significant tensile failure in the 
soil. Nonetheless, a more robust treatment of tensile stresses, 
including improvements at the constitutive level, should be 
considered in future works. 
5.2 
8-m-High Slope Simulation 
We introduce the second slope geometry (8-m-high, steeper, and 
taller) to analyze the role of slope geometry on the predominance 
of flow versus spread mechanisms in retrogressive landslides. The 
material parameters of the sensitive clay in the slope and the other 
simulation parameters, excluding the geometry, are identical to 
the shallower, 5-m-high, slope shown in Section 5.1 . Figures 17 
and 18 show contours of the accumulated plastic strain and 
of the displacement, respectively, for the undrained approach. 
Meanwhile Figures 19 and 20 do the same but for the simulation 
with the strongly coupled 𝒖 – 𝑝𝑤 formulation. 
Both 𝒖 – 𝑝𝑤 and undrained simulations are initially unstable 
and begin to fail via a rotational slip surface (Slide 1) which 
is fully developed around 0.8 s of simulation time. In both 
simulations, the soil that is ejected out of the slide crater breaks 
apart and begins sliding, although a large intact block is left 
behind, originating from the top right corner of the slope. In the 
undrained simulation, a second rotational failure occurs around 
2.0 s of simulation time, whereas in the 𝒖 – 𝑝𝑤 simulation, the 
second failure develops after roughly 1.6 s of elapsed time. An 
inclined shear band forms a triangular soil mass against the back 
boundary of the slope in the undrained simulation, and a similar 
band also forms in the strongly coupled simulation, although in 
the latter case, a large amount of secondary inclined v-shaped 
bands form, further splitting the soil mass after the second slide 
has formed, and leading to a significant zone of lateral spreading. 
In fact, after around 3.0 s, the slope can be divided into an area 
undergoing spreading, located towards the back boundary, and 
an area that is fully fluidized and flowing towards the slope 
toe. This contrasts with the undrained simulation, where the 
sensitive clay slope flows in its entirety after the collapse of the 
final back scarp and the triangular soil mass adjacent to the back 
boundary. In the 𝒖 – 𝑝𝑤 simulation, the spreading zone does not 
form well-developed horst-graben complexes, with only one true 
horst visible, as the grabens further disintegrate, breaking up into 
pieces delimitated by secondary shear bands. In both simulations, 
the retrogression distance consisted of the entire 16 m of the top 
of the clay deposit, and the runout distances at 41.1 and 40.9 m 
for the undrained and strongly coupled simulations, respectively, 
are also very close to each other, alluding to the fact that despite 
some evidence of spreading in the 𝒖 – 𝑝𝑤 case, the overall failure 
behavior is dominated by the flowing of the failed mass. 
The steeper, 8-m-high, slope model reaches a substantially greater 
kinetic energy peak in both undrained and strongly coupled 
cases than the shallower, 5-m-high, slope model, as can be 
seen by comparing Panel A of Figure 21 with Figure 15 . The 
greater kinetic energy resulting from the steeper and taller slope 
makes the retrogressive landslide favor flow behavior as opposed 
to spreading. In addition, the kinetic energy for the steeper 
slope in Figure 21A shows only one peak, which is typical of 
rapid flow-dominated landslides, as the failure occurs almost 
nearly at once with most of the gravitational potential energy 
International Journal for Numerical and Analytical Methods in Geomechanics, 2026
19 of 31

## Page 20

FIGURE 18 
Retrogressive failure simulation progression over time for the 8-m-high slope simulation conducted with the undrained formulation. 
Contours show displacement. 
FIGURE 19 
Retrogressive failure simulation progression over time for the 8-m-high slope simulation conducted with the 𝒖 – 𝑝𝑤 formulation and 
𝑘 = 1e − 8 m/s. Contours show accumulated plastic strain. 
20 of 31
International Journal for Numerical and Analytical Methods in Geomechanics, 2026

## Page 21

FIGURE 20 
Retrogressive failure simulation progression over time for the 8-m-high slope simulation conducted with the 𝒖 – 𝑝𝑤 formulation and 
𝑘 = 1e − 8 m/s. Contours show displacement. 
FIGURE 21 
(A) Evolution of the kinetic energy and (B) horizontal velocities over progressive failure for the undrained and 𝒖 – 𝑝𝑤 simulations of 
the 8-m-high slope. 
released into kinetic energy in a single burst. The peak for the 
strongly coupled simulation occurs slightly prior to that of the 
undrained simulation, at 1.2 s, versus 2.2 s, and the kinetic energy 
drops off more rapidly for the undrained simulation, which 
can be explained by some of the ongoing spreading and soil 
block rearrangements (which also cause some later spikes in the 
maximum but not the front velocities). In spreading dominated 
systems, or under a combination of flowslides and then spreading, 
as seen in the shallower slope model, sequential block failure, 
either through the formation of graben–horst complexes or 
rotational slides, leads to multiple peaks as the soil mass re- 
accelerates and reconfigures. These observations further suggest 
that despite structural differences in the post-failure state of 
the shallower slope between undrained and strongly coupled 
modeling approaches, they share significant similarities from 
an energy-based standpoint. At the same time, in the steeper 
model, both the undrained and strongly coupled approaches 
generate failure responses that are clearly dominated by rapid 
flow behavior, despite the presence of some lateral spreading in 
the post-failure configuration of the 𝒖 – 𝑝𝑤 simulation. 
Figure 22 presents a comparison of pore pressures and excess pore 
pressures generated from the undrained and strongly coupled 
analyses for the steeper slope model. Some similar features can 
be observed with respect to the shallower model (Figure 16 ) such 
as the generation of negative excess pore pressures forming in 
the horsts and high positive excess pore pressures towards the 
bottom of the highly-broken up grabens in the strongly coupled 
International Journal for Numerical and Analytical Methods in Geomechanics, 2026
21 of 31

## Page 22

FIGURE 22 
Comparison of pore pressure ( 𝑝𝑤 ) and excess pore pressure (excess 𝑝𝑤 ) contours for the undrained simulations of the 8-m-high slope. 
model due to contractive behavior. In the undrained model, the 
toe of the slide shows significant compression leading again to 
large positive excess pore pressures. At 𝑡 = 3 s, there is a delay in 
the build-up of excess pore pressures in the strongly coupled sim- 
ulation towards the rear of the slope, whereas in the undrained 
simulation, large excess pore pressures are spatially distributed 
across the whole model, leading to larger strength loss, and 
promoting flow. It is probable that the undrained method tends 
to exaggerate fluidization of the clay by overestimating the excess 
pore pressure, leading to more uniform and rapid mobility. The 
strongly coupled model maintains a more fragmented failure 
style near the rear of the slope, suggestive of spreading, and 
consistent with the episodic failure and more heterogeneous 
drainage response enabled by the 𝒖 – 𝑝𝑤 formulation. However, 
the relatively steep geometry of the 8-m-high model still favors 
a dominant flow-type behavior, evident from the lack of fully 
detached grabens. 
In the two simplified slope models considered in this paper, 
the undrained formulation, while more computationally effi- 
cient (see Supporting Information Section V for a discussion 
of computational efficiency), likely tends to over predict pore 
pressure buildup and hence slope mobility, often leading to flow- 
like behavior irrespective of geometry. Conversely, the 𝒖 – 𝑝𝑤 
formulation introduces realistic fluid–solid coupling that can 
suppress or delay failure, especially in upslope regions, allowing 
for complex episodic failure sequences and spreading. It is worth 
emphasizing the good agreement between the internal physics 
of the models and the overall failure modes captured. Looking 
at Figures 16 and 22 , it is evident that the capability of the 𝒖 –
𝑝𝑤 formulation to model pore water dissipation generates less 
positive excess pore water pressure at the base and free surface 
of the models, allowing the upslope regions adjacent to the shear 
bands to experience negative excess pore water pressures, which 
tend to stabilize the soil in that region, favoring the formation 
of horsts, and hence, a progressive spread failure mechanism. 
Conversely, the more generalized generation of positive excess 
pore water pressures in the undrained formulation is coherent 
with the flow-like mode of failure observed in those simula- 
tions. This comparison underscores the importance of using 
strongly coupled formulations in simulations aiming to resolve 
the nuanced dynamics of retrogressive landslides, especially for 
shallow slopes, or where spreading and drainage are expected 
to be central to the failure process. The authors note that an 
exhaustive exploration of the different factors promoting flow 
versus spreading behavior is outside the scope of this work and 
is left for future work. Here, we have shown the importance 
of slope geometry and on the hydromechanical model, but the 
constitutive model, boundary conditions, and initial stress state 
𝐾0 value are also known to contribute [ 55, 57–59 ] 
6 
Sainte-Monique Landslide 
As a final numerical example, we validate the PR formulation 
by recreating the representative, spread-type, retrogressive failure 
case-study, which took place at Sainte-Monique, Quebec, Canada, 
on April 21, 1994. Located about 130 km northeast of Montreal, 
the landslide occurred along the Siméon-Provencher brook which 
likely eroded into the initial sensitive clay slope generating 
enough of a decrease in horizontal buttress to propagate a 
progressive failure [ 58 ]. Specifically, the soil mass of the slope 
formed distinct horst and graben blocks, typical of spreads, and 
the failure propagated in undrained conditions in a sensitive 
22 of 31
International Journal for Numerical and Analytical Methods in Geomechanics, 2026

## Page 23

FIGURE 23 
(A) Sainte-Monique landslide simulation setup. (B) Initialized pore pressure 𝑝𝑤 and initialized vertical stress (C) after 𝐾0 = 0 . 5 and 
gravity loading. 
clay undergoing strain-softening behavior. The geometry of the 
computational model based on a cross section of the initial 
prefailure slope is shown in Figure 23A . The left side slope is 
inclined at 24.0 ◦whereas the right-hand side slope has a tilt of 
26.0 ◦. The right-hand slope was formed from debris originating 
in an earlier landslide in the same location in 1979. A total of 
7723 domain SPH particles are used to model the slope with an 
initial interparticle distance of Δ = 0 . 6 m, and the base and right 
hand slope are treated as boundary particles, as the right side 
slope did not fail during the 1994 landslide. In the simulations, 
the Wendland 𝐶2 kernel and a smoothing length factor of 1.5 
are employed. A strongly coupled hydromechanical analysis with 
the 𝒖 – 𝑝𝑤 formulation is performed (PR formulation), and the 
water table is assumed to be at the slope ground surface. A 
modeling simplification, following previous works [ 84, 87 ], is 
made in excluding the sandy crust layer found at the top of the 
sensitive clay deposit, as it had limited influence on the runout 
and spread behavior, due to its negligible tensile strength, being 
simply carried away by the underlying sensitive clay. To model 
the sensitive clays, the Drucker–Prager yield criterion is used in 
conjunction with the same softening model seen in Equation ( 48 ) 
[ 106 ]. Due to its ability to best describe the behavior of different 
geomaterials, including sensitive clays, a nonassociative flow 
rule is also used. The simulation’s numerical, geometric, and 
constitutive parameters are summarized in Table 1 . Important to 
note is that site investigations found the in situ clay to be slightly 
overconsolidated with an earth pressure coefficient of 𝐾0 = 0 . 5 
[ 58 ]. 
In the computational model, stresses are first initialized using 
the earth pressure coefficient of 𝐾0 = 0 . 5 , and then subjected to 
a gravity loading where the peak material property values and 
𝜂= 0 are used to stabilize the slope. Next, the resulting effective 
stresses and pore pressures are taken for the actual retrogressive 
landslide simulation, which is triggered by setting the desired 
softening coefficient 𝜂> 0 and allowing for softening behavior. 
The simulation ended after either 55 s or when the sliding ceased 
and the system reached a stable point in terms of kinetic energy 
and displacement. 
Figure 24 shows the accumulated plastic strains and the displace- 
ments at different snapshots in time for the simulation with 𝜂= 5 . 
The failure process begins with the propagation of a horizontal 
band along the model base, which then curves upwards forming 
TABLE 1 
Sainte-Monique landslide simulation simulation parame- 
ters. The constitutive parameters are based on field measurements from 
sensitive clays [ 57, 58, 95 ]. 
Parameter 
Value 
Initial interparticle distance, Δ [m] 
0.6 
Smoothing length factor, 𝑘ℎ 
1.5 
Artificial viscosity parameters, 𝛼𝜋and 𝛽𝜋
0.1 and 0.0 
Damping coefficient, 𝜉
1.0e − 5 
Mixture density, 𝜌[kg/ m3 ] 
1700.0 
Porosity, 𝑛
0.2 
Elastic modulus, 𝐸[MPa] 
13.0 
Poisson’s ratio, 𝜈
0.33 
Bulk modulus of water, 𝐾𝑤 [MPa] 
200.0 
Peak internal friction angle, 𝜙[ ◦] 
10.0 
Residual internal friction angle, 𝜙[ ◦] 
0.0 
Peak cohesion, 𝑐𝑝 [kPa] 
45.0 
Residual cohesion, 𝑐𝑟 [kPa] 
1.0 
Permeability, 𝑘[m/s] 
1.0e − 8 
Softening coefficient, 𝜂
2.0, 5.0, 10.0 
a first circular rotational slide after 2.0 s of simulation time. How- 
ever, the reduction of lateral support causes subsequent failures 
or slides to occur in the form of horst–graben wedges, which 
subside. In total, five major slides occur, with the first four leaving 
behind visible signatures in the kinetic energy and maximum 
horizontal velocities, and the fifth only affecting the front velocity, 
plotted over time for the system in Figure 25 . An additional horst 
also forms at the tip of the slope as the initial rotational failure 
is more upslope. The final configuration for the simulation, in 
terms of accumulated plastic strain and displacement for the 𝜂= 
5 simulation, is visible in the left middle panels of Figure 26 . 
After around 18.0 s of simulation time, disturbed clay material 
at the tip of the slide front begins to override the rightmost 
slope, inclined at 26.0 ◦(modeled with boundary particles), as 
was observed in the post-failure site analysis [ 58 ]. After 55 s of 
simulation time, the post-failure topographic profile of the slope 
is close to that measured in the field for the particular chosen 
International Journal for Numerical and Analytical Methods in Geomechanics, 2026
23 of 31

## Page 24

FIGURE 24 
(Left) Contours of the accumulated plastic strain 𝜀𝑝 
𝑎 𝑐 𝑐 and (right) displacement at different snapshots in time for the Sainte-Monique 
landslide simulation. 
FIGURE 25 
(A) Evolution of the kinetic energy and (B) horizontal velocities over progressive failure for the Sainte-Monique landslide simulation. 
initial cross section at Sainte-Monique (displayed as a red line), 
and the simulation runout of 52 m is close to the field-measured 
runout of 50 m. The final retrogression distance predicted by 
the simulation was 116 m which is slightly larger than the 100 
m measured in the field, but the sensitivity of the retrogression 
distance to the softening coefficient 𝜂, as seen in the other panels 
of Figure 26 , indicates that the roughly selected 𝜂parameter can 
be calibrated to match the expected retrogression distance in our 
model. Overall, increasing 𝜂has the effect of promoting wedge 
formation, sliding events, and greater runout and retrogression 
distance. We also see that increasing 𝜂(akin to a more brittle 
behavior) has the effect of removing the horst at the slide toe, and 
the initial rotational failure propagates from the toe itself. 
The right-hand side panels of Figure 26 show the pore pressure 
and excess pore pressure contours for the Sainte-Monique simu- 
lation for different values of 𝜂. When horsts and grabens develop 
more clearly, like in the 𝜂= 5 , 10 cases, extension occurs in the 
horsts leading to negative excess pore pressures and positive pore 
pressures are observed in areas undergoing contraction, such as 
in the grabens, which undergo subsidence. Positive excess pore 
pressures are also seen in the remolded clay, which is squeezed 
out in-between and below the grabens, and in other zones (e.g., 
near the top surface or the slope toe). Pore pressures dissipate 
as the clay reconsolidates post-failure. A discussion on the state 
of stress during the formation of the slip surfaces and the horst 
and grabens during the Sainte-Monique landslide is provided in 
Supporting Information Section VI (see Figure S6 ). 
7 
Discussion and Conclusions 
In this paper, we derived and presented two distinct strongly 
coupled hydromechanical 𝒖 – 𝑝𝑤 formulations for fully saturated 
soils using the SPH method: a projection method PPE approach, 
and an explicit pore PR scheme based on the single-layer two- 
phase model. Unlike in the PPE approach, where both fluid and 
solid phases are assumed incompressible, the PR formulation 
24 of 31
International Journal for Numerical and Analytical Methods in Geomechanics, 2026

## Page 25

FIGURE 26 
Accumulated plastic strain ( 𝜀𝑝 
𝑎 𝑐 𝑐 ), displacement, pore pressure ( 𝑝𝑤 ), and excess pore pressure (Excess 𝑝𝑤 ) contours for the Sainte- 
Monique landslide simulation, performed with the 𝒖 – 𝑝𝑤 formulation after 55 s, given varying values of the softening coefficient 𝜂. The red line 
superimposed over the 𝜀𝑝 
𝑎 𝑐 𝑐 plots indicates the observed in field ground surface profile after the slope failure. 
allows variability in the fluid phase’s bulk modulus, offering more 
flexibility. The accuracy and stability of the two approaches are 
compared in the context of multiple one-dimensional poroelastic- 
ity problems including one-dimensional (Terzaghi) consolidation 
and self-weight consolidation. In addition, we explore the param- 
eter space of the different numerical stabilization terms added 
into the formulation, ultimately choosing the explicit PR formu- 
lation. We show that it is subject to less stringent restrictions 
pertaining to stability, because of the amplification term that 
arises in the explicit update for the pore pressure when solving 
the PPE equation. Furthermore, the challenges arising with the 
amplification term become markedly more acute for poroelastic 
media with lower permeabilities, which is of interest in the 
case of undrained retrogressive landslides which we study in 
this work. Nevertheless, the PPE formulation may be applicable 
in soils with permeabilities of approximately 𝑘 ≥ 1e-3 m/s, and 
particularly useful when both pore fluid and soil skeleton are 
incompressible, as it enforces the instantaneous, global drained 
response and smooth pressure equilibration expected in this 
regime. We next upscale to three dimensions, modeling Cryer’s 
problem and lastly, we verify the results of stress paths and pore 
pressures from undrained triaxial tests using the MCC model 
generated from both 𝒖 – 𝑝𝑤 and a penalty-based approach for 
undrained conditions against analytical solutions, noting that the 
𝒖 – 𝑝𝑤 formulation gave slightly more accurate results. 
When applying the proposed 𝒖 – 𝑝𝑤 framework to retrogressive 
landslides, we show that the height and relative steepness of a 
slope may contribute to the predominant flowslide versus spread 
mode of failure. Furthermore, our simulations are consistent 
with field observations indicating that circular slides are often 
required prior to the onset of spreading [ 76 ]. In the 5-m-high 
slope, the strongly-coupled simulation predicted spread behavior 
after the first initial rotational failure, whereas the undrained 
approach predicted a series of successive rotational slides with 
some spreading occurring in the debris flowing out of the scarp. 
On the contrary, in the 8-m-high and steeper slope, both fully 
coupled and undrained models predicted flowslide behavior with 
significant fluidization of the debris, although some spreading 
was also present in the strongly coupled simulation. Overall, the 
proclivity of the strongly coupled 𝒖 – 𝑝𝑤 formulation towards 
generating spreading in the landslides, points to the importance 
of incorporating pore fluid pressures in the analysis, as well 
as pore pressure dissipation, and further suggests that penalty- 
based undrained modeling approaches may overestimate the 
potential for flow-like failures under certain conditions. Lastly, 
we demonstrate that the strongly coupled 𝒖 – 𝑝𝑤 PR framework 
successfully models the 1994 Sainte-Monique landslide and its 
deformation patterns without the need for any of the additional 
assumptions originating in the undrained approach. The SPH 
simulation reproduces the field-measured runout distance, as 
well as the final topographic profile quite closely, in addition to 
the expected spreading deformation mechanism. 
Our numerical simulations also capture various important fea- 
tures, for example, that (1) the major slides or horst-graben 
(wedge) forming events release kinetic energy bursts; (2) pore 
pressure dissipation and the resulting increase in effective stress 
and shear strength recovery helps arrest the landslide flow; and 
(3) contractile positive excess pore pressure builds up in the 
grabens and in areas compacted by subsidence, whereas exten- 
sional negative excess pore pressures are observed in the horsts. 
Simulation of these features is mostly outside the scope of the 
undrained framework, but it is worth noting that irrespective of 
the pore fluid modeling approach and the differing deformation 
modes produced, both types of simulations tended to have similar 
runout distances. Despite the inexpensive computational cost of 
the undrained framework relative to the 𝒖 – 𝑝𝑤 (wall-clock time 
International Journal for Numerical and Analytical Methods in Geomechanics, 2026
25 of 31

## Page 26

speed-ups of 3–5 times for a fixed CPU-core count), the latter 
experiences better scalability under parallelization and better 
agreement with theoretical speed-ups for lower CPU-core counts 
( < 10 cores), owing to its higher arithmetic intensity. More details 
about computational costs and efficiency of the formulations 
can be found in supplemental materials. Given the relative 
computational efficiency of both methods, and the advantages 
of the strongly coupled modeling approach, this work shows the 
viability and potential of a large deformation 𝒖 – 𝑝𝑤 formulation 
in SPH towards retrogressive landslides and other geotechnical 
problems involving large material deformations. 
Some limitations of the current work include the fact that the PR 
formulation is explicit in time, and the time step is regulated by 
the CFL condition, which in turn depends on the bulk modulus 
of the pore water phase. Here, different integration schemes 
such as that proposed in [ 55 ] may help resolve this challenge. 
However, even such formulations may still encounter instabilities 
in the pore pressure field, which are common of coupled solid–
fluid deformation analyses in the limit of low permeability with 
incompressible pore fluid, and currently, the state-of-the-art is 
limited to smoothing out nonphysical oscillations. Further work 
on mitigating some of the effects of violating the so-called inf-sup 
or Ladyzenskaja–Babuška–Brezzi (LBB) conditions, and porting 
or adapting techniques from FEM or MPM to SPH would be 
valuable, but is outside the scope of this work. Other directions 
for future research include the addition of newly developed 
absorbing boundary conditions [ 46, 110 ] allowing for dynamic 
loading of saturated soil, which is crucial in earthquakes and 
soil liquefaction–related failures. Lastly, the incorporation of 
more advanced constitutive models which can naturally model 
sands and surmount the limitations of the Drucker–Prager or 
MCC models, or capture anisotropic effects important in some 
geological media [ 47, 83, 111 ] is currently being considered by 
the authors. 
Author Contributions 
Enrique M. Del Castillo: conceptualization, validation, data generation 
and analysis, visualization, writing – original draft, review and editing. 
Ronaldo I. Borja: writing – review, funding acquisition. Alomir H. 
Fávero Neto: conceptualization, methodology, validation, supervision, 
writing – original draft, review and editing. 
Acknowledgments 
This material is based upon work supported by the National Science 
Foundation under Award Number CMMI-1914780 and Grant Number 
1659397. The first author acknowledges the support by the U.S. National 
Science Foundation (NSF) Graduate Research Fellowship under Grant 
DGE 1656518, as well as by the Stanford Graduate Fellowship, and 
the Siebel Scholars Award in Energy Science. Some of the parallel 
computations for this project were performed on the Stanford University 
Research Computing Center’s Sherlock cluster. 
Data Availability Statement 
All data presented in the work can be made available upon reasonable 
request to the corresponding author. 
References 
1 . K. Abe, K. Soga, and S. Bandara, “Material Point Method for Coupled 
Hydromechanical Problems,” Journal of Geotechnical and Geoenviron- 
mental Engineering 140, no. 3 (2014): 04013033. 
2 . Y. Alimohammadlou, A. Najafi, and A. Yalcin, “Landslide Process and 
Impacts: A Proposed Classification Method,” Catena 104 (2013): 219–232. 
3 . S. Bandara and K. Soga, “Coupling of Soil Deformation and Pore Fluid 
Flow Using Material Point Method,” Computers and Geotechnics 63 (2015): 
199–214. 
4 . T. Belytschko, Y. Y. Lu, and L. Gu, “Element-Free Galerkin Methods,”
International Journal for Numerical Methods in Engineering 37, no. 2 
(1994): 229–256. 
5 . M. A. Biot, “General Theory of Three-Dimensional Consolidation,”
Journal of Applied Physics 12, no. 2 (1941): 155–164. 
6 . M. A. Biot, “Theory of Propagation of Elastic Waves in a Fluid-Saturated 
Porous Solid. I. Low Frequency Range,” Journal of the Acoustical Society 
of America 28, no. 2 (1956): 168–178. 
7 . M. A. Biot, “Theory of Propagation of Elastic Waves in a Fluid-Saturated 
Porous Solid. II. Higher Frequency Range,” Journal of the Acoustical 
Society of America 28, no. 2 (1956): 179–191. 
8 . L. Bjrrum, “The Efective Shear Strength Parameters of Sensitive 
Clays,” in 5th International Conference on Soil Mechanics and Foundation 
Engineering (International Society for Soil Mechanics and Geotechnical 
Engineering, 1961). 
9 . T. Blanc and M. Pastor, “A Stabilized Fractional Step, Runge–Kutta Tay- 
lor SPH Algorithm for Coupled Problems in Geomechanics,” Computer 
Methods in Applied Mechanics and Engineering 221-222 (2012): 41–53. 
10 . R. I. Borja and E. Alarcón, “A Mathematical Framework for Finite 
Strain Elastoplastic Consolidation Part 1: Balance Laws, Variational For- 
mulation, and Linearization,” Computer Methods in Applied Mechanics 
and Engineering 122, no. 1-2 (1995): 145–171. 
11 . R. I. Borja, C. Tamagnini, and E. Alarcón, “Elastoplastic Consolidation 
at Finite Strain Part 2: Finite Element Implementation and Numerical 
Examples,” Computer Methods in Applied Mechanics and Engineering 159, 
no. 1-2 (1998): 103–122. 
12 . R. I. Borja, “Free Boundary, Fluid Flow, and Seepage Forces in 
Excavations,” Journal of Geotechnical Engineering 118, no. 1 (1992): 
125–146. 
13 . R. I. Borja, “Analysis of Incremental Excavation Based on Critical State 
Theory,” Journal of Geotechnical Engineering 116, no. 6 (1990): 964–985. 
14 . R. I. Borja and J. A. White, “Continuum Deformation and Stability 
Analyses of a Steep Hillside Slope Under Rainfall Infiltration,” Acta 
Geotechnica 5 (2010): 1–14. 
15 . R. I. Borja, J. A. White, X. Liu, and W. Wu, “Factor of Safety in a 
Partially Saturated Slope Inferred From Hydro-Mechanical Continuum 
Modeling,” International Journal for Numerical and Analytical Methods 
in Geomechanics 36, no. 2 (2012): 236–248. 
16 . R. I. Borja, X. Liu, and J. A. White, “Multiphysics Hillslope Processes 
Triggering Landslides,” Acta Geotechnica 7 (2012): 261–269. 
17 . R. I. Borja, Plasticity Modeling & Computation (Springer, 2013). 
18 . R. I. Borja and S. R. Lee, “Cam-Clay plasticity, Part I: Implicit 
Integration of Elasto-Plastic Constitutive Relations,” Computer Methods 
in Applied Mechanics and Engineering 78, no. 1 (1990): 49–72. 
19 . H. H. Bui, R. Fukagawa, K. Sako, and J. C. Wells, “Slope Stability 
Analysis and Discontinuous Slope Failure Simulation by Elasto-Plastic 
Smoothed Particle Hydrodynamics (SPH),” Géotechnique 61, no. 7 (2011): 
565–574. 
20 . H. H. Bui, R. Fukagawa, K. Sako, and S. Ohno, “Lagrangian Meshfree 
Particles Method (SPH) for Large Deformation and Failure Flows of 
Geomaterial Using Elastic–Plastic Soil Constitutive Model,” International 
26 of 31
International Journal for Numerical and Analytical Methods in Geomechanics, 2026

## Page 27

Journal for Numerical and Analytical Methods in Geomechanics 32 (2008): 
1537–1570. 
21 . H. H. Bui and G. D. Nguyen, “A Coupled Fluid-Solid SPH Approach 
to Modelling Flow Through Deformable Porous Media,” International 
Journal of Solids and Structures 125 (2017): 244–264. 
22 . H. H. Bui and G. D. Nguyen, “Smoothed Particle Hydrodynamics 
(SPH) and Its Applications in Geomechanics: From Solid Fracture to 
Granular Behaviour and Multiphase Flows in Porous Media,” Computers 
and Geotechnics 138 (2021): 104315. 
23 . M. A. Carson, “On the Retrogression of Landslides in Sensitive 
Muddy Sediments,” Canadian Geotechnical Journal 14, no. 4 (1977): 582–
602. 
24 . X. Chen, S. Ren, X. Guo, Y. Wang, F. Liu, H. Nguyen, and R. L. 
Sousa, “Comparative Modelling of Retrogressive Landslide Runout: 2D 
and 3D Random Large-Deformation Analyses Using Coupled Eulerian- 
Lagrangian Method,” International Journal of Mining Science and Tech- 
nology 35, no. 11 (2025): 2011–2030. 
25 . X. Chen, Y. Leung, H. Mori, S. Uchida, and K. Takumi, “Single- 
Layer Soil-Water Coupled SPH Method and Its Application to Sinkhole 
Simulation,” Acta Geotechnica 19 (2024): 991–1018. 
26 . D. Chen, W. Huang, and C. Liang, “A Three-Dimensional Smoothed 
Particle Hydrodynamics Analysis of Multiple Retrogressive Landslides in 
Sensitive Soil,” Computers and Geotechnics 170 (2024): 106284. 
27 . A. D. Chow, B. D. Rogers, S. J. Lind, and P. K. Stansby, “Incompressible 
SPH (ISPH) With Fast Poisson Solver on a GPU,” Computer Physics 
Communications 226 (2018): 81–103. 
28 . M. J. Crozier, “Deciphering the Effect of Climate Change on Landslide 
Activity: A Review,” Geomorphology 124, no. 3-4 (2010): 260–267. 
29 . C. W. Cryer, “A Comparison of the Three-Dimensional Consolidation 
Theories of Biot and Terzaghi,” Quarterly Journal of Mechanics and 
Applied Mathematics 16, no. 4 (1963): 401–412. 
30 . E. M. del Castillo, A. H. Fávero Neto, and R. I. Borja, “Fault 
Propagation and Surface Rupture in Geologic Materials With a Meshfree 
Continuum Method,” Acta Geotechnica 16 (2021): 2463–2486. 
31 . E. M. del Castillo, A. H. Fávero Neto, and R. I. Borja, “A Continuum 
Meshfree Method for Sandbox-Style Numerical Modeling: Application to 
Accretionary and Doubly Vergent Wedges,” Journal of Structural Geology 
153 (2021): 104466. 
32 . E. M. del Castillo, A. H. Fávero Neto, and R. I. Borja, “Modeling 
Fault Rupture Through Layered Geomaterials with SPH,” in Multiscale 
Processes of Instability, Deformation and Fracturing in Geomaterials , 
Springer Series in Geomechanics and Geoengineering, IWBDG 2022, ed. 
A. Dyskin and E. Pasternak (Springer, 2023). 
33 . E. M. del Castillo, A. H. Fávero Neto, J. Geng, and R. I. Borja, “An 
SPH Framework for Drained and Undrained Loading Over Large Defor- 
mations,” International Journal for Numerical and Analytical Methods in 
Geomechanics 48, no. 12 (2024): 3227–3257. 
34 . E. M. del Castillo, J. Geng, and R. I. Borja, “A Nonlocal Kernel- 
Based Continuum Damage Model for Compaction Band Formation in 
Porous Sedimentary Rock,” Computational Mechanics 75 (2025): 1745–
1768. 
35 . E. M. del Castillo, A. H. Fávero Neto, and R. I. Borja, “Fault Rupture 
Propagation Through Stratified Sand-Clay Deposits and Engineered Earth 
Structures: A Meshfree and Critical-State Modeling Approach,” Acta 
Geotechnica 19 (2024): 7767–7798. 
36 . R. Dey, B. Hawlader, R. Phillips, and K. Soga, “Large Defor- 
mation Finite-Element Modelling of Progressive Failure Leading to 
Spread in Sensitive Clay Slopes,” Géotechnique 65, no. 8 (2015): 657–
668. 
37 . Q. Duan and T. Belytschko, “Gradient and Dilatational Stabilizations 
Dilatational Stabilizations for Stress-Point Integration in the Element- 
Free Galerkin Method,” International Journal for Numerical Methods in 
Engineering 77, no. 6 (2009): 776–798. 
38 . A. H. Favero Neto, “A Continuum Lagrangian Finite Deformation 
Computational Framework for Modeling Granular Flows,” (PhD thesis, 
Stanford University, 2020). 
39 . A. H. Fávero Neto and R. I. Borja, “Continuum Hydrodynamics 
of Dry Granular Flows Employing Multiplicative Elastoplasticity,” Acta 
Geotechnica 13 (2018): 1027–1040. 
40 . A. H. Fávero Neto, A. Askarinejad, S. M. Springman, and R. I. 
Borja, “Simulation of Debris Flow on an Instrumented Test Slope Using 
an Updated Lagrangian Particle Method,” Acta Geotechnica 15 (2020): 
2757–2777. 
41 . R. Fatehi and M. Manzari, “Error Estimation in Smoothed Particle 
Hydrodynamics and a New Scheme for Second Derivatives,” Computers 
& Mathematics with Applications 61, no. 2 (2011): 482–498. 
42 . A. H. Favero Neto, G. R. A. Oliveira, L. L. Rasmussen, and E. Rógenes, 
“Large Deformation and Critical State Analysis of the Fundão Tailings 
Dam,” in Proceedings of Geo-Extreme 2025 (ASCE, 2025). 
43 . A. H. Favero Neto, P. D. G. Orlando, and R. Rocha, “The Impacts 
of Aging Infrastructure and Evolving Load Conditions: Case Study of 
an Earth Retaining Wall Failure,” in Proceedings of the 9th Forensic 
Engineering Conference (ASCE, 2022). 
44 . R. Gingold and J. Monaghan, “Smoothed Particle Hydrodynamics: 
Theory and Application to Nonspherical Stars,” Monthly Notices of the 
Royal Astronomical Society 181 (1977): 375–389. 
45 . K. K. Hamouche, S. Leroueil, M. Roy, and A. J. Lutenegger, “In 
Situ Evaluation of K0 in Eastern Canada Clays,” Canadian Geotechnical 
Journal 32, no. 4 (1995): 677–688. 
46 . T. N. Hoang, H. H. Bui, T. T. Nguyen, T. V. Nguyen, and G. D. Nguyen, 
“Development of Free-Field and Compliant Base SPH Boundary Condi- 
tions for Large Deformation Seismic Response Analysis of Geomechanics 
Problems,” Computer Methods in Applied Mechanics and Engineering 432, 
no. A (2024): 117370. 
47 . S. C. Y. Ip and R. I. Borja, “Hydromechanical Coupling in Unsaturated 
Clayey Rocks With Double Porosity Based on a Multiscale Homogeniza- 
tion Procedure,” Computers and Geotechnics 171 (2024): 106380. 
48 . Y.-F. Jin and Z.-Y. Yin, “Two-Phase PFEM With Stable Nodal Inte- 
gration for Large Deformation Hydromechanical Coupled Geotechnical 
Problems,” Computer Methods in Applied Mechanics and Engineering 392 
(2022): 114660. 
49 . Y. Kim, T. Carvalhaes, A. Helmrich, et al., “Leveraging SETS 
Resilience Capabilities for Safe-to-Fail Infrastructure Under Climate 
Change,” Current Opinion in Environmental Sustainability 54 (2022): 
101153. 
50 . M. G. Korzani, S. A. Galindo-Torres, A. Scheuermann, and D. J. 
Williams, “SPH Approach for Simulating Hydro-Mechanical Processes 
With Large Deformations and Variable Permeabilities,” Acta Geotechnica 
13 (2018): 303–316. 
51 . S. Koshizuka and Y. Oka, “Moving-Particle Semi-Implicit Method for 
Fragmentation of Incompressible Fluid,” Nuclear Science and Engineering 
123, no. 3 (1996): 421–434. 
52 . E.-S. Lee, C. Moulinec, R. Xu, D. Violeau, D. Laurence, and P. Stansby, 
“Comparisons of weakly Compressible and Truly Incompressible Algo- 
rithms for the SPH Mesh Free Particle Method,” Journal of Computational 
Physics 227, no. 18 (2008): 8417–8436. 
53 . Y. Lian, H. H. Bui, G. D. Nguyen, H. Tran, and A. Haque, “A General 
SPH Framework for Transient Seepage Flows Through Unsaturated 
Porous Media Considering Anisotropic Diffusion,” Computer Methods in 
Applied Mechanics and Engineering 387 (2021): 114169. 
54 . Y. Lian, H. H. Bui, G. D. Nguyen, S. Zhao, and A. Haque, “A 
Computationally Efficient SPH Framework for Unsaturated Soils and Its 
Application to Predict the Entire Rainfall-Induced Slope Failure Process,”
Géotechnique 74 (2022): 787–805. 
55 . Y. Lian, H. H. Bui, G. D. Nguyen, and A. Haque, “An Effective and 
Stabilised ( 𝑢 − 𝑝𝑙 ) SPH Framework for Large Deformation and Failure 
International Journal for Numerical and Analytical Methods in Geomechanics, 2026
27 of 31

## Page 28

Analysis of Saturated Porous Media,” Computer Methods in Applied 
Mechanics and Engineering 308 (2023): 115967. 
56 . W. K. Liu, S. Jun, and Y. F. Zhang, “Reproducing Kernel Particle 
Methods,” International Journal for Numerical Methods in Fluids 20, no. 
8–9 (1995): 1081–1106. 
57 . A. Locat, S. Leroueil, S. Bernander, D. Demers, H. P. Jostad, and 
L. Ouehb, “Progressive Failures in Eastern Canadian and Scandinavian 
Sensitive Clays,” Canadian Geotechnical Journal 48 (2011): 1696–1712. 
58 . A. Locat, S. Leroueil, A. Fortin, D. Demers, and H. P. Jostad, “The 
1994 Landslide at Sainte-Monique, Quebec: Geotechnical Investigation 
and Application of Progressive Failure Analysis,” Canadian Geotechnical 
Journal 52 (2015): 490–504. 
59 . A. Locat, “Canadian Geotechnical Colloquium: Understanding 
Spreads in Canadian Sensitive Clays,” Canadian Geotechnical Journal 62 
(2025): 1–14. 
60 . L. B. Lucy, “A Numerical Approach to the Testing of the Fission 
Hypothesis,” Astronomical Journal 82, no. 12 (1977): 1013–1024. 
61 . J. Mandel, “Consolidation Des Sols (Étude Mathématique),” Géotech- 
nique 3, no. 7 (1953): 287–299. 
62 . S. Menon and X. Song, “Computational Coupled Large-Deformation 
Periporomechanics for Dynamic Failure and Fracturing in Variably Satu- 
rated Porous Media,” International Journal for Numerical and Analytical 
Methods in Geomechanics 124 (2023): 80–118. 
63 . S. Menon and X. Song, “Computational Multiphase Periporomechan- 
ics for Unguided Cracking in Unsaturated Porous Media,” International 
Journal for Numerical and Analytical Methods in Geomechanics 123 (2023): 
2837–2871. 
64 . S. Mohajerani, G. Wang, Y. Zhao, and F. Jin, “A Novel Peridynamics 
Modelling of Cemented Granular Materials,” Acta Geotechnica 18 (2023): 
2529–2548. 
65 . L. Monforte, M. Arroyo, J. M. Carbonell, and A. Gens, “Numerical 
Simulation of Undrained Insertion Problems in Goetechnical Engineer- 
ing With the Particle Finite Element Method (PFEM),” Computers and 
Geotechnics 82 (2017): 144–156. 
66 . S. Moriguchi, R. I. Borja, A. Yashima, and K. Sawada, “Estimating the 
Impact Force Generated by Granular Flow on a Rigid Obstruction,” Acta 
Geotechnica 4 (2009): 57–71. 
67 . D. S. Morikawa and M. Asai, “Soil-Water Strong Coupled ISPH Based 
on u-w-p Formulation for Large Deformation Problems,” Computers and 
Geotechnics 142, no. 104570 (2022): 104570. 
68 . D. S. Morikawa and M. Asai, “A Phase-Change Approach to Landslide 
Simulations: Coupling Finite Strain Elastoplastic TLSPH With Non- 
Newtonian IISPH,” Computers and Geotechnics 148 (2022): 104815. 
69 . D. S. Morikawa and M. Asai, “Coupling Total Lagrangian SPH–EISPH 
for Fluid–Structure Interaction With Large Deformed Hyperelastic Solid 
Bodies,” Computer Methods in Applied Mechanics and Engineering 381 
(2021): 113832. 
70 . J. P. Morris, P. J. Fox, and Y. Zhu, “Modeling Low Reynolds Number 
Incompressible Flows Using SPH,” Journal of Computational Physics 136, 
no. 1 (1997): 214–226. 
71 . B. Mullet, P. Segall, and A. H. Fávero Neto, “Numerical Modeling 
of Caldera Formation Using Smoothed Particle Hydrodynamics (SPH),”
Geophysical Journal International 234, no. 2 (2023): 887–902. 
72 . P. Navas, M. Pastor, A. Yagüe, M. M. Stickle, D. Manzanal, and M. 
Molinos, “Fluid Stabilization of the 𝒖 − 𝒘 Biot’s Formulation at Large 
Strain,” International Journal for Numerical and Analytical Methods in 
Geomechanics 45 (2021): 336–352. 
73 . P. Navas, M. Molinos, M. M. Stickle, D. Manzanal, A. Yagüe, and 
M. Pastor, “Explicit Meshfree 𝒖 − 𝑝𝑤 Solution of the Dynamic Biot 
Formulation at Large Strain,” Computational Particle Mechanics 9 (2022): 
655–671. 
74 . P. Navas, M. M. Stickle, A. Yagüe, D. Manzanal, M. Molinos, and M. 
Pastor, “Stabilized Explicit 𝒖 − 𝑝𝑤 Solution in Soil Dynamic Problems 
Near the Undrained-Incompressible Limit,” Acta Geotechnica 18 (2023): 
1199–1213. 
75 . M. Neuner, A. Dummer, S. Abrari Vajari, et al., “A B-Spline Based 
Gradient-Enhanced Micropolar Implicit Material Point Method for 
Large Localized Inelastic Deformations,” Computer Methods in Applied 
Mechanics and Engineering 431 (2024): 117291. 
76 . S. Odenstad, “The Landslide at Sköttorp on the Lidan River, February 
2, 1946,” Royal Swedish Institute Proceedings 4 (1951): 1–38. 
77 . E. Oñate, S. R. Idelsohn, F. D. Pin, and R. Aubry, “The Particle Finite 
Element Method. An Overview,” International Journal of Computational 
Methods 1, no. 2 (2004): 267–307. 
78 . M. Pastor, B. Haddad, G. Sorbino, S. Cuomo, and V. Drempetic, “A 
Depth-Integraded, Coupled SPH Model for Flow-Like Landslides and 
Related Phenomena,” International Journal for Numerical and Analytical 
Methods in Geomechanics 33 (2009): 143–172. 
79 . M. Pastor, A. Yague, M. M. Stickle, D. Manzanal, and P. Mira, 
“A Two-Phase SPH Model for Debris Flow Propagation,” International 
Journal for Numerical and Analytical Methods in Geomechanics 42 (2017): 
418–448. 
80 . Z. Qiao, W. Shen, P. Xin, T. Li, P. Li, and H. Jiao, “Simulation of 
the Failure and Run-Out Processes of Rotational–Translational Loess 
Landslides Using an SPH Model Considering Strain Softening,” Acta 
Geotechnica 19 (2024): 7799–7820. 
81 . X. Qi, Q. Xu, and F. Liu, “Analysis of Retrogressive Loess Flowslides 
in Heifangtai, China,” Engineering Geology 236 (2018): 119–128, https://doi. 
org/10.1016/j.enggeo.2017.08.028 . 
82 . P. Ramachandran, A. Bhosale, and K. Puri, “PySPH: A Python-Based 
Framework for Smoothed Particle Hydrodynamics,” ACM Transactions 
on Mathematical Software (TOMS) 47, no. 4 (2021): 1–38. 
83 . E. Rógenes, I. T. Paes, B. G. Delgado, et al., “Assessing Static 
Liquefaction Triggers in Tailings Dams Using the Critical State 
Constitutive Models CASM and NorSand,” International Journal for 
Numerical and Analytical Methods in Geomechanics 49, no. 4 (2025): 
1092–1112. 
84 . Z. Shan, W. Zhang, D. Wang, and L. Wang, “Numerical Inves- 
tigations of Retrogressive Failure in Sensitive Clays: Revisiting 1994 
Sainte-Monique Slide, Quebec,” Landslides 18 (2021): 1327–1336. 
85 . T. Siriaksorn, S. W. Chi, C. Foster, and A. Mahdavi, “u-p Semi- 
Lagrangian Reproducing Kernel Formulation for Landslide Modeling,”
International Journal for Numerical and Analytical Methods in Geome- 
chanics 2018 42, no. 2 (2018): 209–376. 
86 . A. Skillen, S. Lind, P. K. Stansby, and B. D. Rogers, “Incompress- 
ible Smoothed Particle Hydrodynamics (SPH) With Reduced Temporal 
Noise and Generalised Fickian Smoothing Applied to Body–Water Slam 
and Efficient Wave–Body Interaction,” Computer Methods in Applied 
Mechanics and Engineering 265 (2013): 163–173. 
87 . X. Song, H. Pashazad, and A. Whittle, “Computational Large- 
Deformation-Plasticity Periporomechanics for Localization and Instabil- 
ity in Deformable Porous Media,” International Journal for Numerical and 
Analytical Methods in Geomechanics 49 (2025): 1278–1298. 
88 . D. Sulsky, S.-J. Zhou, and H. L. Schreyer, “Application of a Particle-in- 
Cell Method to Solid Mechanics,” Computer Physics Communications 87, 
no. 1-2 (1995): 236–252. 
89 . W. Sun and J. Fish, “Coupling of Non-Ordinary State-Based Peridy- 
namics and Finite Element Method for Fracture Propagation in Saturated 
Porous Media,” International Journal for Numerical and Analytical 
Methods in Geomechanics 45 (2021): 1260–1281. 
90 . H. Teufelsbauer, Y. Wang, S. P. Pudasaini, R. I. Borja, and W. Wu, 
“DEM Simulation of Impact Force Exerted by Granular Flow on Rigid 
Structures,” Acta Geotechnica 6 (2011): 119–133. 
28 of 31
International Journal for Numerical and Analytical Methods in Geomechanics, 2026

## Page 29

91 . Q.-A. Tran and W. So ł owski, “Generalized Interpolation Material Point 
Method Modelling of Large Deformation Problems Including Strain-Rate 
Effects – Application to Penetration and Progressive Failure Problems,”
Computers and Geotechnics 106 (2018): 249–265. 
92 . Q.-A. Tran, A. Rogstad, I. Depina, et al., “3D Large Deformation 
Modeling of the 2020 Gjerdrum Quick Clay Landslide,” Canadian 
Geotechnical Journal 62 (2024): 1–21, https://doi.org/10.1139/cgj-2024- 
0044 . 
93 . Z. A. Urmi, A. Saeidi, R. V. P. Chavali, and A. Yerro, “Failure 
Mechanism, Existing Constitutive Models and Numerical Modeling of 
Landslides in Sensitive Clay: A Review,” Geoenvironmental Disasters 10 
(2023): 14. 
94 . Z. A. Urmi, A. Saeidi, A. Yerro, and R. V. P. Chavali, “Prediction of Post- 
Peak Stress-Strain Behavior for Sensitive Clays,” Engineering Geology 323 
(2023): 107221. 
95 . Z. A. Urmi, A. Yerro, A. Saeidi, and R. V. P. Chavali, “Prediction of 
Retrogressive Landslide in Sensitive Clays by Incorporating a Novel Strain 
Softening Law Into the Material Point Method,” Engineering Geology 340 
(2024): 107669. 
96 . D. J. Varnes, “Slope-Stability Problems of the Circum-Pacific Region 
as Related to Mineral and Energy Resources,” in Energy resources of the 
Pacific Region. American Association of Petroleum Geologist Studies in 
Geology , ed. M. T. Halbouty, vol. 12 (1981), 489–505. 
97 . A. Verrujit, An Introduction to Soil Dynamics (Springer, 2010). 
98 . B. Wang, P. J. Vardon, and M. A. Hicks, “Investigation of Retrogressive 
and Progressive Slope Failure Mechanisms Using the Material Point 
Method,” Computers and Geotechnics 78 (2016): 88–98. 
99 . C. Wang, B. Hawlader, D. Perret, K. Soga, and J. Chen, “Modeling 
of Initial Stresses and Seepage for Large Deformation Finite-Element 
Simulationof Sensitive Clay Landslides,” Journal of Geotechnical and 
Geoenvironmental Engineering 147, no. 11 (2021): 04021111. 
100 . C. Wang, B. Hawlader, D. Perret, and K. Soga, “Effects of Geometry 
and Soil Properties on Type and Retrogression of Landslides in Sensitive 
Clays,” Géotechnique 72, no. 4 (2022): 322–336. 
101 . L. Wang, X. Zhang, Q. Lei, S. Panayides, and S. Tinti, “A Three- 
Dimensional Particle Finite Element Model for Simulating Soil Flow With 
Elastoplasticity,” Acta Geotechnica 17 (2022): 5639–5653. 
102 . D. M. Wood, Soil Behavior and Critical State Soil Mechanics (Cam- 
bridge University Press, 1990). 
103 . M. Xie, P. Navas, and S. López-Querol, “A Stabilised Semi-Implicit 
Double-Point Material Point Method for Soil–Water Coupled Problems,”
Computational Particle Mechanics 12 (2025): 3389–3419. 
104 . J. Yu, W. Liang, and J. Zhao, “Enhancing Dynamic Modeling of 
Porous Media With Compressible Fluid: A THM Material Point Method 
With Improved Fractional Step Formulation,” Computer Methods in 
Applied Mechanics and Engineering 444 (2025): 118100. 
105 . W.-H. Yuan, M. Liu, X.-W. Zhang, H.-L. Wang, W. Zhang, and W. Wu, 
“Stabilized Smoothed Particle Finite Element Method for Coupled Large 
Deformation Problems in Geotechnics,” Acta Geotechnica 18 (2023): 1215–
1231. 
106 . F. Zabala and E. E. Alonso, “Progressive Failure of Aznalcóllar Dam 
Using the Material Point Method,” Géotechnique 61, no. 9 (2011): 795–808. 
107 . X. Zhang, S. W. Sloan, and E. Oñate, “Dynamic Modelling of 
Retrogressive Landslides With Emphasis on the Role of Clay Sensi- 
tivity,” International Journal for Numerical and Analytical Methods in 
Geomechanics 42 (2018): 1806–1822. 
108 . X. Zhang, L. Wang, K. Krabbenhoft, and S. Tini, “Dynamic Mod- 
elling of Retrogressive Landslides With Emphasis on the Role of Clay 
Sensitivity,” Landeslides 17 (2020): 1117–1127. 
109 . E. Yang, H. H. Bui, H. D. Sterck, and G. D. Nguyen, “A Scalable 
Parallel Computing SPH Framework for Predictions of Geophysical 
Granular Flows,” Computers and Geotechnics 121 (2020): 103474. 
110 . C. Yao, G. Fourtakas, B. D. Rogers, and D. Lombardi, “2-D SPH 
Modelling of Poroelasticity: 𝒖 − 𝒘 − 𝑝and 𝒖 − 𝑝Formulations With 
Absorbing Boundary Conditions and Volumetric Locking Treatments,”
Computers and Geotechnics 179 (2025): 107016. 
111 . Y. Zhao and R. I. Borja, “A Double-Yield-Surface Plasticity Theory for 
Transversely Isotropic Rocks,” Acta Geotechnica 17 (2022): 5201–5221. 
112 . D. Z. Zhang, X. Ma, and P. T. Giguere, “Material Point Method 
Enhanced by Modified Gradient of Shape Function Author Links Open 
Overlay Panel,” Journal of Computational Physics 231, no. 16 (2011): 
6379–6398. 
113 . X. Zhang, D. Sheng, S. W. Sloan, and J. Bleyer, “Lagrangian Modelling 
of Large Deformation Induced by Progressive Failure of Sensitive Clays 
With Elastoviscoplasticity,” International Journal for Numerical Methods 
in Engineering 112 (2017): 963–989. 
114 . S. Zhao, H. H. Bui, V. Lemiale, G. D. Nguyen, and F. Darve, “A Generic 
Approach to Modelling Flexible Confined Boundary Conditions in SPH 
and Its Application,” International Journal for Numerical and Analytical 
Methods in Geomechanics 43, no. 5 (2019): 1005–1031. 
115 . Y. Zhao, J. Choo, Y. Jiang, and L. Li, “Coupled Material Point 
and Level Set Methods for Simulating Soils Interacting With Rigid 
Objects With Complex Geometry,” Computers and Geotechnics 163 (2023): 
105708. 
116 . O. C. Zienkiewicz, A. H. C. Chan, M. Pastor, B. A. Schrefler, and T. 
Shiomi, Computational Geomechanics (John Wiley & Sons, 1999). 
Supporting Information 
Additional supporting information can be found online in the Supporting 
Information section. 
Supporting file 
Appendix A: Coupled Formulation Derivation Details 
To derive the equations, we rely on the following set of assumptions: 
1. The soil is fully saturated, that is, the void fraction of the material is 
full of water. 
2. The water is inviscid. 
3. There is no mass or heat exchange between solid and water phases, 
and processes are isothermic. 
4. Terzaghi’s effective stress theory is valid. 
We now consider a two-phase soil consisting of solid matrix (subscript 
𝑠) and water (subscript 𝑤) filling the void space between the solid 
matrix ( 𝑉𝑣 ). We define the intrinsic mass densities as the mass of 
the phase divided by the volume of the phase. Hence, 𝜌𝑠 and 𝜌𝑤 
are the corresponding intrinsic mass densities of the solids and water, 
respectively. Moreover, we define porosity 𝑛 = 𝑉𝑣 
𝑉 , where 𝑉is the total 
volume of the mixture. Porosity is also related to the void ratio of the soil 
through the relationship 𝑛 = 𝑒∕(1 + 𝑒) . 
Based on the previous definitions, the partial densities (ratio of phase 
mass and total volume) of the solid and water phases are defined, 
respectively, as 
𝜌𝑠 = 𝑛𝑠 𝜌𝑠 
(A1) 
𝜌𝑤 = 𝑛𝜌𝑤 , 
(A2) 
with 𝑛𝑠 = 1 − 𝑛, such that 𝜌𝑠 + 𝜌𝑤 = 𝜌, where 𝜌is the bulk mass density 
of the mixture. 
International Journal for Numerical and Analytical Methods in Geomechanics, 2026
29 of 31

## Page 30

In terms of stress, we can also define partial stresses acting on the solid 
and water phases as 𝝈𝑠 = 𝑛𝑠 𝝈𝑠 and 𝝈𝑤 = 𝑛𝝈𝑤 , where 𝝈𝑠 and 𝝈𝑤 are the 
intrinsic total stresses in the solid and water phases, respectively. It is 
worth pointing out a few relationships pertaining to stress in the mixture 
𝝈= 𝝈𝑠 + 𝝈𝑤 = 𝝈′ + 𝝈𝑤 
(A3) 
𝝈𝑤 = 𝑝𝑤 𝟏 
(A4) 
𝝈𝑤 = 𝑛𝑝𝑤 𝟏 
(A5) 
𝝈𝑠 = 𝝈′ + 𝑛𝑠 𝑝𝑤 𝟏 
(A6) 
In the previous equations, 𝟏 is the second order identity tensor, and 𝝈′ is 
the partial effective stress acting on the solid phase, which is determined 
from any constitutive model selected to represent the behavior of the 
solid skeleton. 
Material Time Derivatives 
We define a material time derivative following the motion of phase 𝛼( 𝛼= 
𝑠or 𝑤) as follows: 
𝑑𝛼() 
𝑑𝑡 = 𝜕() 
𝜕𝑡 + 𝒗𝛼⋅∇() , 
(A7) 
where 𝒗𝛼is the phase velocity, and “∇() ” is the gradient operator. Hence, 
for the solid and water phases, the material time derivatives following 
each phase’s own motion are as follows: 
𝑑𝑠 () 
𝑑𝑡 = 𝜕() 
𝜕𝑡 + 𝒗𝑠 ⋅∇() , 
(A8) 
𝑑𝑤 () 
𝑑𝑡 = 𝜕() 
𝜕𝑡 + 𝒗𝑤 ⋅∇() . 
(A9) 
If we subtract the previous equations, we obtain the relationship between 
material time derivatives following the water and solid phases: 
𝑑𝑤 () 
𝑑𝑡 = 𝑑𝑠 () 
𝑑𝑡 + ( 𝒗𝑤 − 𝒗𝑠 ) ⋅∇() . 
(A10) 
For small relative velocities ( 𝒗𝑤 − 𝒗𝑠 ), we can use a Lagrangian frame- 
work and perform any analyses with respect to the solid motion only. 
The difference between fluid and solid velocities per unit area of the 
mixture is also known as Darcy’s velocity, defined as follows: 
𝒗 = 𝑛( 𝒗𝑤 − 𝒗𝑠 ) . 
(A11) 
Darcy’s velocity is related to the hydraulic conductivity tensor of the soil 
mixture, 𝒌 , and the head loss ℎalong the fluid through Darcy’s law 
𝒗 = 𝒌 ⋅∇ ℎ = 𝒌 ⋅∇
( 𝑝𝑤 
𝜌𝑤 𝑔 + 𝑧
) 
, 
(A12) 
where 𝒌 = 𝑘𝟏 in case of isotropic and homogeneous conductivity. Thus, 
we can rewrite Equation ( A10 ) as follows: 
𝑑𝑤 () 
𝑑𝑡 = 𝑑() 
𝑑𝑡 + 𝒗 
𝑛 ⋅∇() . 
(A13) 
In Equation ( A13 ) and moving forward, for simplicity of notation, we will 
drop the superscript 𝑠for the time derivative following the motion of the 
solid phase. In what follows, we will use Equation ( A13 ) to determine 
the differential governing equations with respect to the motion of the 
solid phase. 
Balance of Mass 
In general, for a given phase 𝛼in mixture theory, the balance of mass (in 
Eulerian form) is given by the following: 
𝑑𝛼𝑀𝛼
𝑑𝑡 
= 𝑑𝛼
𝑑𝑡 ∫𝑉 
𝜌𝛼𝑑 𝑉 = 𝑑𝛼
𝑑 𝑡 ∫𝑉0 
𝜌𝛼𝐽𝑑 𝑉0 
= ∫𝑉0 
( 𝑑𝛼𝜌𝛼
𝑑𝑡 𝐽 + 𝜌𝛼∇ ⋅𝒗𝛼𝐽
) 
𝑑𝑉0 = 0 , 
(A14) 
where 𝐽is the deformation gradient tensor Jacobian, which maps the 
current configuration of a deformed body (with volume, 𝑉) to its 
undeformed shape (reference volume, 𝑉0 ), and “∇ ⋅() ” is the divergence 
operator. Hence, 
𝑑𝛼𝑀𝛼
𝑑𝑡 
= ∫𝑉 
( 𝑑𝛼𝜌𝛼
𝑑𝑡 + 𝜌𝛼∇ ⋅𝒗𝛼
) 
𝑑𝑉 = 0 . 
(A15) 
Making use of the fundamental theorem of calculus and the fact that the 
balance of mass should hold for any arbitrary differential volume element, 
the general equation for the balance of mass for a given phase 𝛼is finally 
𝑑𝛼𝜌𝛼
𝑑𝑡 + 𝜌𝛼∇ ⋅𝒗𝛼= 0 . 
(A16) 
For the present case where we have two phases, solid and water, the 
balance of mass for the solid phase, written in terms of volume fractions 
and intrinsic mass densities, is given by the following: 
𝑑( 𝑛𝑠 𝜌𝑠 ) 
𝑑𝑡 
+ ( 𝑛𝑠 𝜌𝑠 ) ∇ ⋅𝒗𝑠 = 0 , →𝑑𝑛𝑠 
𝑑𝑡 + 𝑛𝑠 1 
𝜌𝑠 
𝑑𝜌𝑠 
𝑑𝑡 + 𝑛𝑠 ∇ ⋅𝒗𝑠 = 0 . (A17) 
Similarly, for the water phase, we have the following: 
𝑑𝜌𝑤 
𝑑𝑡 = 𝑑( 𝑛𝜌𝑤 ) 
𝑑𝑡 
+ ∇ ⋅𝒘 + ( 𝑛𝜌𝑤 ) ∇ ⋅𝒗𝑠 
= 0 , →𝑑𝑛 
𝑑𝑡 + 𝑛1 
𝜌𝑤 
𝑑𝜌𝑤 
𝑑𝑡 + 1 
𝜌𝑤 
∇ ⋅𝒘 + 𝑛∇ ⋅𝒗𝑠 = 0 . 
(A18) 
where 𝒘 = 𝜌𝑤 ( 𝒗𝑤 − 𝒗𝑠 ) = 𝜌𝑤 𝒗 is the Eulerian relative fluid velocity. 
Now, assuming that solid phase’s and pore-water’s mass densities changes 
(i.e., volumetric deformations) are due solely to the intrinsic pore-water 
pressure, 𝑝𝑤 , and that these changes arise from an elastic response [ 116 ], 
we have 
1 
𝜌𝛼
𝑑𝜌𝛼
𝑑𝑡 = − ∇ ⋅𝒗𝛼= −1 
𝐾𝛼
𝑑 𝑝𝑤 
𝑑𝑡 , 
(A19) 
where 𝐾𝛼is the intrinsic bulk modulus of phase 𝛼. 
Therefore, we can rewrite Equation ( A17 ) using Equation ( A19 ), which 
gives the following: 
𝑑𝑛𝑠 
𝑑𝑡 − 𝑛𝑠 1 
𝐾𝑠 
𝑑 𝑝𝑤 
𝑑𝑡 + 𝑛𝑠 ∇ ⋅𝒗𝑠 = 0 . 
(A20) 
Similarly, for the water phase, rewriting Equation ( A18 ) using Equa- 
tion ( A19 ), we get the following: 
𝑑𝑛 
𝑑𝑡 − 𝑛1 
𝐾𝑤 
𝑑 𝑝𝑤 
𝑑𝑡 + 1 
𝜌𝑤 
∇ ⋅𝒘 + 𝑛∇ ⋅𝒗𝑠 = 0 . 
(A21) 
Adding Equations ( A20 ) and ( A21 ), recalling that 𝑛𝑠 + 𝑛 = 1 , and rewrit- 
ing it in terms of Darcy’s velocity gives the mixture balance of mass, 
1 
𝑄 
𝑑 𝑝𝑤 
𝑑𝑡 − ∇ ⋅𝒗 − ∇ ⋅𝒗𝑠 −∇ 𝜌𝑤 
𝜌𝑤 
⋅𝒗 = 0 . 
(A22) 
where 1∕ 𝑄 = 𝑛𝑠 ∕𝐾𝑠 + 𝑛∕𝐾𝑤 . 
30 of 31
International Journal for Numerical and Analytical Methods in Geomechanics, 2026

## Page 31

Balance of Linear Momentum 
The balance of linear momentum for a given phase 𝛼is as follows: 
𝑑𝛼
𝑑𝑡 ∫𝑉 
𝜌𝛼𝒗𝛼𝑑𝑉 = ∫𝐴 
𝒕𝛼𝑑𝐴 + ∫𝑉 
𝜌𝛼𝒈 𝑑𝑉 + ∫𝑉 
𝑹𝛼𝑑𝑉 , 
(A23) 
where 𝒈 is the gravity acceleration vector, 𝒕𝛼is the partial traction vector 
for phase 𝛼, and 𝑹𝛼is the body force per unit total volume exerted 
on phase 𝛼by the other phase. Recalling that 𝒕𝛼= 𝒎 ⋅𝝈𝛼, with 𝒎 the 
unit normal vector to the traction surface, and applying the fundamental 
theorem of calculus and the divergence theorem, it can be shown that the 
balance of linear momentum for phase 𝛼becomes the following: 
𝜌𝛼𝑑𝛼𝒗𝛼
𝑑𝑡 = ∇ ⋅𝝈𝛼+ 𝜌𝛼𝒈 + 𝑹𝛼. 
(A24) 
Now, if we use the definitions of partial solid stress, 𝝈𝑠 , and of partial water 
stress, 𝝈𝑤 , from Equations ( A6 ) and ( A5 ), respectively, we can write the 
balance of linear momentum for the solid and water phases, 
𝜌𝑠 𝑑𝒗𝑠 
𝑑𝑡 = ∇ ⋅𝝈′ + 𝑛𝑠 ∇ 𝑝𝑤 + 𝑝𝑤 ∇ 𝑛𝑠 + 𝜌𝑠 𝒈 + 𝑹𝑠 
(A25) 
[2 𝑒 𝑥] 𝜌𝑤 𝑑𝑤 𝒗𝑤 
𝑑 𝑡 = 𝑛∇ 𝑝𝑤 + 𝑝𝑤 ∇ 𝑛 + 𝜌𝑤 𝒈 + 𝑹𝑤 . 
(A26) 
Alternatively, the balance of linear momentum of the water phase, 
following the motion of the solid phase (using Equation A13 ), is given by 
the following: 
𝜌𝑤 𝑑𝒗𝑤 
𝑑𝑡 = 𝑛∇ 𝑝𝑤 + 𝑝𝑤 ∇ 𝑛 + 𝜌𝑤 𝒈 + 𝑹𝑤 − 𝜌𝑤 𝒗 ⋅∇ 𝒗𝑤 . 
(A27) 
To determine an equation for the balance of linear momentum of the 
whole mixture, we add Equations ( A25 ) and ( A26 ). Noting that 𝜌𝑠 + 𝜌𝑤 = 
𝜌(the mass density of the mixture), 𝑛 + 𝑛𝑠 = 1 , and recalling that 𝑹𝑠 = 
− 𝑹𝑤 , we obtain the following: 
𝜌𝑑𝒗𝑠 
𝑑𝑡 + 𝜌𝑤 
( 𝑑𝑤 𝒗𝑤 
𝑑𝑡 −𝑑𝒗𝑠 
𝑑𝑡 
) 
= ∇ ⋅𝝈′ + ∇ 𝑝𝑤 + 𝜌𝒈 . 
(A28) 
We denote Equation ( A28 ) as the mixture balance of momentum equa- 
tion. 
Appendix B: Algorithms 
ALGORITHM B1
Proposed 𝒖 – 𝑝𝑤 formulation method using PPE approach. 
ALGORITHM B2
Proposed 𝒖 – 𝑝𝑤 formulation method using pressure rate approach. 
International Journal for Numerical and Analytical Methods in Geomechanics, 2026
31 of 31
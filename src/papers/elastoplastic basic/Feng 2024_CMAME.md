# A general smoothed particle hydrodynamics (SPH) formulation for coupled liquid flow and solid deformation in porous media

> Auto-converted from PDF for Codex/code-reference reading. Formatting, equations, figures, and tables may require checking against the original PDF.

- Source PDF: `Feng 2024_CMAME.pdf`
- Pages: 34
- PDF metadata author: Ruofeng Feng

## Extracted Text

### Page 1

Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

                                          Contents lists available at ScienceDirect
              Computer Methods in Applied Mechanics
                        and Engineering

                                     journal homepage: www.elsevier.com/locate/cma

A general smoothed particle hydrodynamics (SPH) formulation for
coupled liquid flow and solid deformation in porous media
Ruofeng Feng *, Georgios Fourtakas, Benedict D. Rogers, Domenico Lombardi
School of Engineering, Faculty of Science and Engineering, The University of Manchester M13 9PL,

A R T I C L E  I N F O                 A B S T R A C T

Keywords:                                 The method of smoothed particle hydrodynamics (SPH) has been recently developed to study the
Smoothed particle hydrodynamics (SPH)            coupled flow-deformation problems in porous material and considerable success has been ach
Unsaturated porous materials                      ieved comparing to traditional mesh-based method, especially for treating large deformation and
Seepage flow                                                      post-failure. However, computational challenges remain for the hydro-mechanical boundaryLarge deformation                                              treatment as well as the accuracy and stability of the numerical scheme. It is shown that the use ofHydro-mechanical coupling
DualSPHysics                                   conventional SPH operator for the solution of the coupled problem can lead to several issues
                                                including numerical instabilities, inaccuracies and unphysical particle clumping as well as par
                                                          ticle disorders near the boundary. To address these issues, a general SPH scheme with enhanced
                                             accuracy for saturated/unsaturated porous material is proposed in this paper. An improved SPH
                                              formulation for seepage analysis is proposed to allow an accurate prediction of liquid flow in
                                            porous material. A new stabilisation technique that combines the use of a density diffusion term, a
                                             modified particle shifting algorithm, and a new viscous damping term is developed to further
                                          improve the accuracy, stability and robustness of the proposed method. The implementations of
                                                       stress boundary conditions and hydraulic boundary conditions in SPH, such as confining stress,
                                               hydraulic head, infiltration/evaporation, and potential seepage face, using either wall boundary
                                                     particles or free-surface domain particles, are discussed in detail. A range of benchmark examples
                                                               is adopted to verify the validity of the present coupled framework. The proposed model is finally
                                               applied to simulate the failure process of embankment dam due to rapid drawdown. Results
                                                  indicate that the methodology proposed herein can be a promising tool for the analysis of the
                                            coupled hydro-mechanical process in porous material involving large deformations.

1. Introduction

   Coupled liquid flow and solid deformation in porous materials is one of the most fundamental processes in engineering with a wide
range of applications, such as wave-porous structure interaction in coastal engineering, hydraulic fracturing in geotechnical engi
neering, and carbon dioxide sequestration in environmental engineering. It is also an important factor responsible for the occurrence of
many geohazards, including rainfall-induced landslides, embankment instabilities due to seepage, and dam failure caused by internal
erosion [1,2]. Accurate predictions of flow regimes, solid deformations, and material failure are crucial for preventing structural
failure and designing effective mitigation measures. However, computational challenges arise due to the complexity of multi-physics
phenomena, phase interactions within the porous mixture, the requirement for rigorous treatment of hydraulic and mechanical

 * Corresponding author.
    E-mail address: ruofeng.feng@manchester.ac.uk (R. Feng).

https://doi.org/10.1016/j.cma.2023.116581
Received 3 August 2023; Received in revised form 29 October 2023; Accepted 29 October 2023
Available online 14 November 2023
0045-7825/©  2023  The  Author(s).     Published  by  Elsevier  B.V.  This   is  an  open  access  article  under  the  CC  BY  license
(http://creativecommons.org/licenses/by/4.0/).

### Page 2

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

boundary conditions, and the occurrence of large deformations during the post-failure stage.
   Conventional mesh-based methods, such as the finite element method, are commonly utilized in practice to solve the coupled flowdeformation problem, e.g., Plaxis [3], Geostudio [4], and ICFEP [5]. However, these methods cannot efficiently treat the large de
formations experienced during the post-failure stage, as they often become unstable and encounter issues with mesh distortions.
   The emergence of meshfree methods, such as smoothed particle hydrodynamics (SPH), provides a promising solution to address all
above-mentioned challenges due to the ability to handle multi-physics coupled phenomena and to simulate large deformations. Several
SPH models have been proposed in the literature for the coupled flow-deformation analysis in porous material. Maeda et al. [6] made
the first attempt to use SPH for the coupled analysis of gas-water-soil interaction within the porous material. In their method, different
phases were treated on different particle layers, with interaction force exchanged between each particle layer at every time step. Later,
this so-called multi-layer SPH framework has been widely adopted for applications including wave-porous structure interaction [7],
seepage failure of dikes subjected to water impoundment and rainfall [8], and stability analysis of soil slope [9].
   In recent years, the single-layer approach has gradually received research attention due to its computational efficiency and con
venience in boundary treatment. In this approach, the multi-phase porous media is conceptualised as a mixture and solved using a
single set of particles. Pastor et al. [10] derived a quasi-Lagrangian formulation of depth-integrated equation and applied to the u-p
version of the Biot-Zienkiewicz mixture model (u denotes the displacement of solid skeleton, and p represents liquid pressure) to study
the propagation of landslide. Later, Blanc and Pastor [11] developed a fractional step, Runge–Kutta Taylor SPH algorithm for the
solution of the u-p mixture model to reduce the numerical oscillation in pore pressure and to mitigate tensile instability. More recently,
Morikawa and Asai [12] applied the incompressible smoothed particle hydrodynamics (ISPH) projection method to solve coupled
soil–water interaction in saturated soil using the u-w-p Biot’s formulation (w denotes seepage discharge). Feng et al. [13] proposed a
single-layer two-phase SPH model for saturated/unsaturated soils based on a similar u-w-p formulation but with the weakly
compressible assumption. It was shown that their model enables the analysis of slope failure under extreme rainfall events with a
noise-free stress field. Lian et al. [14] developed a single-layer multi-phase SPH method based on velocity-hydraulic head (u-h)
formulation to solve for the coupled problems in unsaturated soils. In their method, an adaptive time stepping scheme that links the
time step with plastic strain was proposed to improve the computational efficiency. Ma et al. [15] further extended the SPH model by
Lian et al. [14] to allow the analysis of internal erosion problems in porous materials.
   The above-mentioned studies demonstrate that the state-of-the-art SPH approaches have achieved some success in addressing
complex physics and phase interaction within porous mixtures, as well as the post-failure large deformations. However, there are still
some remaining computational challenges that need to be addressed, including boundary conditions, as well as convergence, con
sistency, and stability of the numerical scheme [16]. The particle nature of SPH and the presence of kernel truncation issues introduce
challenges in treating both the solid wall boundary condition and the free-surface boundary condition in SPH. The arbitrary particle
distributions, lack of appropriate dissipation terms, and the inherent inconsistency error in SPH further contribute to the difficulty in
achieving robust, accurate, and stable numerical solutions. Addressing these issues is crucial for the coupling problems because the
boundary conditions and the accurate prediction of liquid seepage flow are essential for the reliability of the numerical results, and the
analysis of coupled problems is very prone to instability.
   To address the boundary condition for the coupled flow-deformation analysis in SPH, several attempts have been made in recent
studies. Lian et al. [17] proposed a set of hydraulic boundary conditions for the transient seepage analysis with SPH in their
single-phase unsaturated seepage framework. Xu et al. [18] developed a solid wall boundary treatment for the 3-D non-Newtonian
flows using two types of virtual particles, namely wall particles and dummy particles. For the coupled formulation, Morikawa and
Asai [12] formulated a boundary treatment for solid phase that includes non-penetration and friction, while the liquid boundary
condition is implemented as a Dirichlet boundary condition for simple applications such as zero-pressure and zero liquid velcotiy
boundary. Similarly, Feng et al. [13] developed a wall boundary treatment for non-slip and free-slip condition for both liquid phase
and solid phase, but only zero-pressure free-surface boundary condition is adopted in their application and the hydro-mechanical
condition at the free surface for complex scenarios  is not discussed. There  is  still a lack of rigorous methods for enforcing
hydro-mechanical boundary conditions for the coupled problem in SPH. In addition, although the existing SPH formulation for the
coupled flow-deformation analysis adopts some stabilisation techniques to improve the stability of the solution, such as the artificial
stress method for tensile instability (e.g., Bui and Nguyen [19]), the Shepard filter for smoothing out the numerical noise (e.g., [15]),
and the artificial damping term for reducing unphysical numerical oscillation (e.g., [14,20]), these techniques are known to have
certain limitations. For example, the incorporation of artificial stress requires case-dependant tuning of two parameters, and extending
it to 3-D applications is considerably complex [19]. The use of the Shepard filter introduces empiricism in selecting the applied fre
quency and the potential for over-filtering in long-duration simulations. The adoption of artificial damping term by Nguyen et al. [20]
does not strictly conserve momentum. Therefore, the investigation of alternative stabilisation techniques to improve these limitations
is necessary.
   This paper develops a general SPH framework for coupled flow-deformation problems in porous materials. The new framework is
built upon the SPH formulations proposed by Feng et al. [13]. Several enhancements are introduced to improve the accuracy and
stability of the numerical solution, and to extend the applicability to complex hydro-mechanical scenarios. These enhancements
include an enhanced SPH formulation for seepage analysis to improve predictions of liquid flow in porous materials. Additionally, the
wall boundary treatment by Feng et al. [13] is extended to accommodate hydraulic head boundary conditions, and the methodology
for the implementation of the stress boundary condition and the hydraulic boundary condition at the free surface is developed.
Furthermore, a novel stabilisation technique is proposed, which combines the use of a density diffusion term, a modified particle
shifting algorithm, and a new viscous damping term. The proposed computational framework is validated through a range of
benchmark tests, including the 1-D infiltration test, the 1-D consolidation test, the fully/partially submerged still soil column test, the

                                                                2

### Page 3

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

2-D seepage flow test, and the rainfall-induced landslide experiment. Finally, the proposed model is applied to study the embankment
failure due to rapid drawdown.
   The remaining part of this paper is organised as follows: Section 2 presents the basic definition of the computational model,
governing equations for the multi-phase porous mixture and the hydraulic/mechanical constitutive models. This is followed by the
improved SPH formulation for unsaturated porous material, along with development of the stabilisation technique as well as the
numerical implementation of the hydro-mechanical boundary condition, given in Section 3. The validity of the proposed methodology
is examined in Section 4. In Section 5, the application of the proposed SPH model to study the embankment failure due to rapid
drawdown is investigated. Finally, conclusions are summarized in Section 6.

2. Continuum based mathematical model for porous material

2.1. Basic definitions

   In this study, the problem of interest is to investigate the response of a porous material in unsaturated/saturated states under a
specified hydro-mechanical condition. Fig. 1 shows a typical example for the coupled flow-deformation problem in an earth slope
under natural conditions.
   As shown in Fig. 1, the presence of ground liquid flow and the capillary effect in the pore space give rise to three distinct regions: the
impermeable bedrock, the fully saturated zone, and the unsaturated zone, which can be observed from bottom to top. Various hy
draulic conditions, such as evaporation/infiltration, fluctuations in groundwater level, and plant intake, may apply to the natural
slope.
   The porous materials can be generally categorised into three phases, including solid S, liquid L, and air A, as shown in Fig. 2. Each
phase within the multi-phase porous mixture has its own set of physical quantities and interacts with the other phases through mass or
momentum exchange. The continuum mixture theory [21] is introduced to establish the mathematical model of the porous material.
   Given a representative elementary volume (REV) of the porous material, three different phases are involved. Based on the
assumption that each phase is homogenous and continuous within the REV, phases within the REV are treated as continua and can be
described using continuum theory. Each phase occupies an individual volume, and the sum equals the total volume. The concept of the
volume fraction is then introduced for the purpose of quantifying the mass and momentum contribution of each individual phase to the
entire mixture. The volume fraction nα of a phase {α} is defined as the ratio of the volume occupied by that phase Vα to the total volume
V, i.e., nα=Vα/V. Consequently, the following relation is established:
       nS + nL + nA = 1                                                                                                           (1)
where nS, nL, and nA are respectively the volume fraction for the solid phase, liquid phase and air phase
   For a three-phase problem, two variables are required to describe the volume fraction of all phases. Taking the advantages of the
well-defined terminologies in soil mechanics, the porosity and degree of saturation are introduced for the volume fraction variables.
The porosity ϕ denotes the volume fraction of pore spaces, i.e., ϕ = nL + nA, and the degree of saturation SL stands for the relative
volume fraction of liquid to the pore spaces, i.e., SL = nL / ϕ. As a result, the volume fraction of solid phase, liquid phase, and air phase
can be respectively expressed as nS = 1 – ϕ, nL = SL ϕ, and nA = (1 – SL)ϕ.
   Upon determining the volume fraction, the partial (or apparent) physical quantities, i.e., partial density ρα and partial stress σα, can
be evaluated by relating them to their intrinsic density ρα and intrinsic stress σα through their corresponding volume fraction, as
expressed by the following equations:

     Fig. 1. Typical example of the coupled flow-deformation problem with (a) full saturation (b) capillary saturation (c) partial saturation.

                                                                3

### Page 4

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

                                            Fig. 2. Multi-phase continuum model for porous material.

       ρα = nαρα                                                                                                             (2a)

       σα = nασα                                                                                                         (2b)
   Accordingly, the total density and total stress of the mixture can be calculated as,
    ∑
      ρm =    ρα = (1 −ϕ)ρS + SLϕρL + (1 −SL)ϕρA                                                                           (3a)
                α

    ∑
      σm =    σα = (1 −ϕ)σS + SLϕσL + (1 −SL)ϕσA                                                                       (3b)
                 α
   To solve the continuum mixture model in a Lagrangian mesh-free method, the single-layer approach is adopted due to its efficiency
in computation as well as boundary treatment [13,14]. In this approach, only a single set of particles is adopted to describe the physical
domain of concern, and the governing equations of each phase are solved within each individual particle. In the present analysis, the
deformation of the solid skeleton is of particular interest for characterizing failure. Therefore, the geometry of the physical domain is
defined as the solid phase of the porous material, represented by a single set of particles. These particles carry all the information of
each phase and move according to the deformation of the solid skeleton. The motion of kinematic variables in other phases is described
relative to the solid skeleton.

2.2. Governing equations

   The governing equation for the porous mixture is obtained based on the mass conservation and momentum conservation of each
phase, together with the hydro-mechanical constitutive models. The applied assumptions and derivation of governing equations in this
study are in accordance with the work by Feng et al. [13]. In their model, the three-phase problem is simplified to a two-phase problem
by assuming that the mass and momentum contribution from the air phase to the mixture is negligible. The presence of the air phase is
taken into account by evolving the degree of saturation and the suction pressure. In addition, the relative acceleration of the liquid with
respect to the solid skeleton is also assumed to be negligible in the derivation.
    It is worth noting that the formulation by Feng et al. [13] is established based on the u-w-p form of Biot’s model. Compared to other
single-layer multi-phase SPH formulation using the u-p formulation, such as Blanc and Pastor [11], and Lian et al. [14], the use of u-w-p
form requires the solution of an extra state variable, i.e., seepage discharge w, which may introduce extra computational costs, but it
offers certain advantages. Firstly, only the first derivative is involved in the u-w-p form, which simplifies the implementation and
avoids the issues associated with the SPH Laplacian operator required in the u-p form. Moreover, the enforcement of the seepage
discharge boundary condition, especially at the free surface, can be achieved straightforwardly and conveniently in u-w-p form as
Dirichlet boundary condition rather than Neumann boundary condition in u-p form.
   The formulations presented in this study follow a specific sign convention: (i) compressive stress and strains in the solid phase are
taken as negative; (ii) pore liquid pressures in the liquid phase are assumed to be positive under compression; (iii) flow discharge is
considered positive for inflow situations.

2.2.1. Mass and momentum conservation
   Following Feng et al. [13], the mass and momentum conservation equations for the porous material in unsaturated/saturated
condition can be expressed as follows:

                                                                4

### Page 5

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

   (a) Mass conservation equation for the solid phase:

            dsϕ
          = (1 −ϕ)∇⋅vS                                                                                             (4a)
                dt

   (b) Mass conservation equation for the liquid phase:
             (              dsρL               )−1ρL          = −   SL −∂SL KL     (∇⋅qL + SL∇⋅vS)                                                                  (4b)                 dt             ∂pc     ϕ

   (c) Momentum conservation equation for the mixture:

                dsv            ρm  = ρmaS = ∇⋅σ + ρmb                                                                                       (4c)
                   dt

   (d) Momentum conservation equation for the liquid phase:
            (          )
            K     1
             qL =        −   ∇pL −aS + b                                                                                   (4d)
                 g     ρL

where v is the velocity in the solid phase, pc is the suction pressure, KL is the bulk modulus of liquid, qL is the seepage discharge, as is the
solid acceleration, σ is the total stress, b is the body force vector, K is the hydraulic conductivity, g is the magnitude of the gravity, and
pL is the pore liquid pressure. The superscript S denotes that the material derivative is attached to the reference system of the solid
phase.
    It is noted that the suction pressure only exists when the porous material is unsaturated, i.e., SL < SL.max. Its value is normally taken
as the difference between the air pressure and liquid pressure, given by pc = pA - pL. As the pore-air pressure is assumed to be 0 in this
study (pA = 0), the suction pressure is simply calculated as the negative pore liquid pressure when SL < SL.max. The total stress tensor σ
is calculated using the concept of Bishop’s effective stress for unsaturated porous material and takes form as
      σ = σ′ −SLpLI                                                                                                             (5)

in which σ′ is the effective stress tensor, I is the unit vector.
   Therefore, the primary variables in the formulation include: (1) volume fraction: ϕ, SL, ρL, (2) kinematic variables: qL, vS, and (3)
mechanics variables: pL, σ’. There are 4 governing equations with 7 unknown variables in the proposed formulations. Additional
constitutive relations are required to complete the governing equations, which are discussed in the following section.

2.2.2. Mechanical constitutive models
   In this study, the mechanical behaviour of porous materials is assumed to follow the elastic-plastic theory, and the effective stresses
σ′ are calculated from the strain increment dε based on elasto-plastic analysis. The weakly compressible assumption is made for the
liquid, and the pore liquid pressure pL is related the variation of liquid density ρL.
   The stress increment can be calculated according to,
        dσ′ = Depdε −dω ⋅σ′ + σ′ ⋅dω                                                                                              (6)
where Dep is the elasto-plastic stiffness tensor, which depends on the constitutive model adopted, ε is the strain tensor, and ω is the spin
tensor. In the above equation, the Jaumann stress rate of Cauchy stress is also adopted to ensure the objectivity of stress under rigid
body rotation.
   The strain rate tensor ˙ε and the spin rate tensor ˙ω can be related to velocity gradient from kinematic relations according to,
          1 (              ˙ε =  ∇v + (∇v)T)                                                                                                   (7a)
          2

          1 (         ˙ω =  ∇v −(∇v)T)                                                                                                (7b)
          2
    It is noted that numerous advanced constitutive models for unsaturated porous materials have been proposed in the literature.
These models can be readily incorporated into the proposed SPH method, as the algorithm for the constitutive model is independent of
the numerical framework. In this study, a simple attempt is made by adopting the elastic-plastic Drucker-Prager model with the
suction-dependant strength and strain softening presented by Bui and Nguyen [19] and Lian et al. [14]. The primary focus of this study
is the development of a general SPH method for the coupled flow-deformation analysis in porous materials. The implementation of
more advanced constitutive models will be considered as part of future work.

                                                                5

### Page 6

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

   With the Drucker-Prager yield criterion, the yield function and plastic potential function are given by,
        √̅̅̅̅
           f = αϕI1 +   J2 −kc                                                                                                   (8a)

        √̅̅̅̅
      g = αψI1 +   J2                                                                                                     (8b)

where I1 and J2 are respectively the first principal stress invariant and the second deviatoric stress, αϕ and kc are Drucker-Prager
constants that can be related to cohesion c and internal friction ϕ according to,

                tanϕ
      αϕ = √̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅                                                                                                    (9a)
             9 + 12tan2ϕ

                3c
        kc = √̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅                                                                                                 (9b)
            9 + 12tan2ϕ

αψ is the parameter associated with dilatancy, and its value is related to the dilation angle ψ in a similar manner as αϕ is linked with the
friction angle φ.
   To evaluate the strength parameters, two mechanisms are considered in this work. One is the softening of material strength when
subjected to large deformations, while the other pertains to the hardening of material strength due to the presence of suction in the
unsaturated condition. Accordingly, the strength parameter is defined as follows,
       c = c′r + cs                                                                                                      (10a)

     φ = φ′r + φs                                                                                                   (10b)
where c′ and φ′ denote the effective cohesion and friction angle, respectively, while cs and φs represent the additional cohesion and
friction angle gained due to the presence of suction.
   The strain-softening is taken into account by assuming the effective strength parameters, i.e., effective cohesion and friction angle,
decrease exponentially with the equivalent deviatoric strain κ according to Bui and Nguyen [19], given by,
                            (       )
           c′ = c′r +  c′p −c′r e−ηcκ                                                                                           (11a)

                             (        )
        φ′ = φ′r +  φ′ p −φ′r e−ηφκ                                                                                        (11b)

where c′p and c′r denote the peak and residual effective cohesion, φ′p and φ′r represent the peak and residual effective friction angle,
respectively. ηc and ηφ are the softening coefficients that control the degradation rate of cohesion and friction angle, respectively.
  On the other hand, the suction-dependant component of cohesion and friction angle are assumed to increase with suction pressure,
which is expressed as [22],
             ( )
          (      −Bs   patmpc  )
         cs = csp 1 −e                                                                                                   (12a)

        (  )
                  pc       φs = As                                                                                                       (12b)
                   patm

where csp denote the maximum cohesion due to suction, As and Bs are the rate of change of friction angle and cohesion with respect to
suction, respectively, patm is the atmosphere pressure normally taken as 101 kPa.
   In the present analysis, the semi-implicit stress updating algorithm is adopted to update the effective stress. The details of the
algorithm is shown in Appendix A.
   By assuming the liquid is weakly compressible, the liquid pressure is related to the variation in liquid density, and is calculated
according to the following relationship,

          KL       pL =    (ρL −ρL0)                                                                                                  (13)
             ρL0

where ρL0 is the initial density of the liquid and KL is the liquid bulk modulus.

2.2.3. Hydraulic constitutive models
   To fully complete the governing equations, it is also essential to establish the hydraulic constitutive models for the relationships
between the degree of saturation SL and the suction pressure pc. These relationships are provided by the soil-water characteristic curve
(SWCC) model. In the present analysis, the linear model and Van Genuchten model are considered. These models are given by the
following equations,

                                                                6

### Page 7

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

      ⎧
      ⎨     SL.max          pc ≥0
       SL =    SL.max −avpc  0 < pc < pcs                                                                                 (14a)      ⎩
                       SL.min         pc ≥pcs

                                                                                  1   −λ                      ⎡  (  )1−λ⎤
       SL = SL.min + (SL.max −SL.min)⎣1 +                                              pc   ⎦                                                                       (14b)
                                                          pref

where av, λ, and pref denote the fitting parameters, SL.min and SL.max represent the residual saturation degree and the maximum
saturation degree, and pcs is the threshold suction to reach the residual saturation degree whose value is calculated as pcs = (SL.max - SL.
min)/ av.
   In addition to the SWCC model, the hydraulic conductivity curve (HCC) model is required to describe the influence of saturation on
the permeability. A parameter named relative hydraulic conductivity Krel is introduced, which is defined as the ratio of the hydraulic
conductivity K at a specific saturation to the saturated hydraulic conductivity Ksat. The equations of the HCC model adopted in this
study for the linear relation model and the Van Genuchten model are expressed as follows,
       ⎧
                1                               pc ≥0       ⎪⎪⎨                           (                   ) pc
         Krel =               Krrel  pcr  0 < pc < pcr ,                                                                                   (15a)
       ⎪⎪⎩
                Krrel       pc ≥pcr

      √[̅̅         (         Krel =  S 1 −  1 −S1/λ)λ]2 ,                                                                                     (15b)

where pcr represents the suction value at which the relative permeability is reduced to the residual permeability, denoted as Krelr  .

3. Numerical implementations using SPH

3.1. Improved SPH formulations for unsaturated porous material

3.1.1. SPH fundamentals
   In SPH, the approximation of the gradient of a scalar f and the divergence of a vector f are calculated as,

     ∑N  mj (     )       〈∇f〉i =               fj + fi ∇iWij,                                                                                      (16a)
                    j=1 ρj

      ∑N  mj (      )      〈∇⋅f〉i = −              fi −fj  ⋅∇iWij,                                                                               (16b)
                         j=1 ρj

where 〈…〉denotes the quantities in SPH approximation, the subscript i and j represent the interpolating particle and its neighbours,
respectively, ∇iWij=∇iW(xi-xj, h) and fj=f(xj) are respectively the gradient of the kernel function W with respect to the coordinate of
particle i and the value of function f for the particle j at the position xj, N is the number of neighbour particles j within the interpolating
radius of particle i, and mj is the mass of the particle j.
   In the present analysis, the density ρj and mass mj of SPH particles are taken as the partial density of the solid skeleton ρss = (1 −ϕ)ρS
and its corresponding mass. As a result, the mass of the physical domain is conserved and can be kept as a constant throughout the
calculation.

3.1.2.  Discretised governing equations
   Conventionally, the discretised form of the governing equations for unsaturated porous material in SPH can be obtained by
substituting the SPH gradient and divergence operators expressed in Eq. (16a) and Eq. (16b) into the continuous form of governing

  Fig. 3. Contour plot of vertical seepage discharge for a rainfall infiltration simulation using (a) standard SPH; (b) kernel gradient correction.

                                                                7

### Page 8

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

equation in Eq. (4a) ~ Eq. (4d), as done in the work by Feng et al. [13]. However, it is observed that numerical fluctuations may be
present in the liquid phase due to the local inconsistency. This issue becomes particularly noticeable when a hydraulic boundary
condition is imposed on the free surface. Fig. 3(a) illustrates this situation with an example of rainfall infiltration simulation, in which a
specified infiltration rate is prescribed at the free-surface particles. It is clear that the calculated pressure profile with the use of
standard SPH exhibits significant fluctuations and numerical noise near the free-surface boundary. These inconsistent errors may
accumulate during the simulation and could also potentially trigger numerical instabilities.
  An attempt to mitigate this issue is made in this study by applying kernel corrections to the SPH approximation of pressure gradient
and seepage discharge divergence in the liquid phase. The adoption of the kernel gradient correction significantly improves the ac
curacy of the predictions in the liquid phase as shown in Fig. 3(b). Another important reason for this selection is that it can address the
issue of kernel truncation near the boundary without requiring additional boundary particles. This allows for the implementation of
complex hydraulic boundary conditions at the free surface with greater ease.
  A wide variety of kernel correction technique has been proposed in the literature [23,24,25]. amongst them, the most widely-used
one could be the kernel renormalisation, which adopts a renormalisation matrix to restore the first-order consistency. However, the
challenge of adopting the kernel renormalisation in the present application is that while the corrected kernel gradient performs well for
particles with a complete kernel, it still encounters truncation problems near the free surface, i.e., ∑ ∇̃WijVj ∕= 0, and inconsistency can
                                                                                                                                                                                                                                j
still be present near the boundary. Therefore, the first-order correction method proposed by Liu and Liu [25] is adopted in this study to
improve the inconsistent issue near the free surface. This corrective technique ensures a first-order consistent SPH approximation
across the entire domain. It is also found from numerical experiments that the simulation remains stable with this technique from small
to large deformations, and it requires fewer boundary layer particles for a specified free-surface boundary condition.
   For the field variable f, its value and gradient can be computed according to
        ∑                ⎡        ⎤
     ⎡    ⎤                 fjWijVj
           〈f〉Ri    ∑j
                                   fj∂xWijVj   ,                                                                                   (17)              ⎢⎢⎣ 〈∂xf〉Ri ⎥⎥⎦= R−1ij   ⋅         j                                                                                                 ⎢⎢⎢⎢⎢⎣ ∑                                ⎥⎥⎥⎥⎥⎦
          〈∂zf〉Ri                   fj∂zWijVj
                                                                    j

where the corrective matrix Rij is given by,
     ∑    ∑     ∑     ⎤        ⎡
                    WijVj        xjiWijVj        zjiWijVj
                                         j                            j                               j
    ∑    ∑     ∑
                   ∂xWijVj                                  xji∂xWijVj        Rij =                                                  zji∂xWijVj   .                                                                       (18)                                                                   j                                                                                                   j                                      j                                                 ⎢⎢⎢⎢⎢⎣ ∑    ∑     ∑                                   ⎥⎥⎥⎥⎥⎦
                   ∂zWijVj      xji∂zWijVj      zji∂zWijVj
                                      j                            j                               j
   Therefore, Eq. (17) is adopted to evaluate the divergence of liquid discharge and pressure gradient in the liquid phase. Accordingly,
the discretised form of Eqs. (4a)~(4d) can be written as in Eqs. (19a)~(19d). Herein, it is noted that for clarity the governing equations
are presented in indicial notation and Einstein convention, in which α, β and γ denote the Cartesian coordinates.
     〈dϕ〉
        = (1 −ϕi)˙εv.i                                                                                             (19a)
          dt     i
      〈dρL 〉   (       ∂SL )−1 ρLi (〈∂qγL 〉R    )        = −   SL −KL           + SLi˙εv.i   ,                                                                (19b)
          dt      i               ∂pc     i  ϕi     ∂xγ     i

               (                        )
              ∏αβ      〈dvα 〉    1 ∑                      N  mj                                                ∂Wij        =              σαβi + σαβj +      + gαi                                                                      (19c)
          dt      i    ρm.i  j=1 ρj                                    ij    ∂xβi

          (        〉R      )      〈  〉    Ki     1 〈∂p
        qαL   i =         −       + gαi −aαsi   ,                                                                            (19d)             g       ρLi  ∂xα    i

where ˙εv is the volumetric strain rate, which is calculated from the strain rate as ˙εv = ˙εγγ, Παβij  is the stabilisation term to reduce
numerical oscillations in the velocity field, which will be discussed in Section 3.2.
   For the strain rate and spin rate, a standard SPH divergence operator is applied, and the discretised forms of strain rate and spin rate
equation are respectively written as
                                    )
      〈dεαβ 〉   1 ( ∑                       N  mj (     ) ∂Wij ∑N  mj (       ) ∂Wij         =             vαj −vαi    +         vβj −vβi                                                                (20a)
           dt       i   2    j=1 ρj            ∂xβi      j=1 ρj           ∂xαi

                                                                8

### Page 9

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

                                    )
      〈dωαβ 〉   1 ( ∑                       N  mj (     ) ∂Wij ∑N  mj (       ) ∂Wij         =             vαj −vαi             −          vβj −vβi                                                              (20b)
           dt       i   2    j=1 ρj            ∂xβi      j=1 ρj           ∂xαi
    Finally, the position of the particles is updated according to the calculated velocity using the following equation:
       dxαi      = 〈vα〉i.                                                                                                        (21)        dt

3.2.  Stabilisation technique

3.2.1.  Artificial dissipation term
   In the absence of a numerical dissipative term in the governing equations, the SPH solutions may suffer from unphysical oscillations
and numerical instabilities. A common way to mitigate this issue is to include an artificial viscosity term by Monaghan [26] into the
momentum equation. As a result, the momentum equation is rewritten as,
      〈dvα 〉    1 ∑                      N  mj (        ) ∂Wij   ∑N  mj  ∂Wij        =             σαβi + σαβj    + αμcs0h         μij   + gαi                                                          (22)
          dt      i    ρm.i  j=1 ρj             ∂xβi              j=1 ρij   ∂xαi

where
      ⎧
                                                   ij       vβijxβij < 0      ⎪⎪⎨    vβijxβ2
          μij =   ‖ xβij ‖ + η2                                                                                                 (23)
      ⎪⎪⎩
             0              vβijxβij > 0

and αμ is the viscous constant controlling the magnitude                                                         of dissipation, cs0 is the numerical speed of sound for solid material, which is                       √̅̅̅̅̅̅̅̅̅̅
related to the Young’s modulus of the solid E by cs0 =  E/ρS , ρij is the mean particle density, defined as ρij = (ρi + ρj) /2, η=0.1 h is the
numerical parameter introduced to avoid numerical singularity, and ‖ … ‖ denote L2 norm of a vector.
   However, in some cases, the use of artificial viscosity cannot effectively mitigate the numerical oscillation and prevent the
instability. There is a need to investigate an appropriate damping term as an alternative technique for stabilisation. Nguyen et al. [20]
formulated a damping term for the SPH application to the simulation of elastic-plastic materials, in which the proposed damping term
is linearly dependant on the velocity. However, the conservative properties of the damping term are not considered in their study,
which could potentially lead to the over-dissipation. In this study, a linear viscous damper based on the linear viscoelasticity theory is
considered, in which the viscous stress component σαβD by the damper is related to the strain rate by,
        σαβD = η˙εαβ                                                                                                         (24)
   This type of damper has been applied in the total Lagrangian SPH method for solid dynamics by Zhang et al. [27]. In their approach,
the damper stress term is directly integrated into the constitutive equation. A distinct approach is adopted in the present analysis
wherein the viscous damping term is incorporated into the momentum equation. The formulation is derived by imitating the artificial
viscosity, in which the new viscous damping term shares the similar scaling factor with the artificial viscosity, i.e., η = αchρ, while the
strain rate for the viscous damper is formulated in finite difference approximation. Consequently, the momentum equation is rewritten
as follows:
      〈dvα 〉    1 ∑                      N  mj (        ) ∂Wij   ∑N  mj   ∂Wij        =             σαβi + σαβj    + αdcs0h       dαβij   + gαi                                                         (25)
          dt      i    ρm.i  j=1 ρj             ∂xβi              j=1 ρij    ∂xβi

where αd is the damping coefficient, and the damping term dαβij  is calculated as
        (              )
           1      vαijxβij           vβijxαij
       dαβij =             2   +        2                                                                                       (26)
           2  ‖ xβij ‖ + η2  ‖ xβij ‖ + η2
    It can be found that, different from the artificial viscosity term that mainly operates on the bulk deformation, the new viscous
damping term incorporates dissipation for both the bulk deformation and shear deformation. The conservative properties of the new
artificial term are discussed in Appendix B.

3.2.2. Diffusion algorithm
   Although the solution in the liquid phase can be much improved with the new SPH formulation, numerical noise can still be
present, particularly when encountering large deformations and when the liquid flow reaches a boundary with geometric singularities
such as sharp corners. To solve this issue, the diffusion algorithm [28] is considered in this study and the diffusion term is incorporated
into the liquid density equation, given by

                                                                9

### Page 10

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

                                                   ]
                ∑N  mj      ∂Wij      〈dρL 〉     1 [  (〈∂qαL 〉R     )        = −       ρLi      + SLi˙εv.i + δLhcl0      ψαρL.ij           ,                                                       (27)
          dt      i      Cri        ∂xα     i                         j=1 ρj       ∂xαi

where Cr is the storage term for the that can be expressed as,
        (      )
                      ∂SL       Cr = ϕ  SL −KL                                                                                                    (28)                       ∂pc

cl0 is the characteristic speed of seepage discharge. It is estimated as ten times possible maximum seepage discharge magnitude in the
numerical analysis, given by cl0 = 10qL.max. δL is the dimensionless diffusion coefficient, typically taken as δL = 0.1. The diffusion
operators ψαρL.ij are formulated according to the structure by Antuono et al. [28], as follows,
                           (        )    xαij     (                 )      ψαρL.ij = 2 ρL.i −ρL.j                   −   〈∂ρL/∂xα〉Lj + 〈∂ρL/∂xα〉Li   ,                                                             (29)
                              xβijxβij + η2

3.2.3.  Particle shifting
   In the application of SPH to solid mechanics, challenges such as particle clustering and numerical voids can arise due to the
presence of tensile instability in SPH. In addition, it is observed that when material failure occurs and shear deformation develops
along the boundary, noticeable particle disorder and particle penetration into the boundary may occur. To avoid these issues, the
particle shifting technique is applied to regularise disordered particles. The shifting technique was originally proposed by Nestor et al.
[29] for particle methods and was subsequently extended to incompressible SPH approach by Xu et al. [30]. It was later further
generalised in SPH for free-surface flows by Lind et al. [31], and applied to weakly compressible SPH scheme by Shadloo et al. [32].
Additionally, Xu et al. [33] extended the application of the shifting technique to the simulation of viscoelastic free surface flows to
mitigate the tensile instability issue.
   With the shifting method, each particle is shifted a certain distance at the end of each time step according to the concentration of
particles, allowing particles in denser areas to move towards areas with lower particle concentration. In this study, the optimized
particle scheme (OPS) proposed by Khayyer et al. [7] is modified for the present application. The shifting distance is computed
proportionally to the concentration gradient of SPH particles with the shifting coefficient Dshift, based on the Fick’s first law of
diffusion, which is expressed as,

                   ∂Ci       δxαi = −Dshift                                                                                                       (30)                    ∂xα
   The gradient of SPH particle concentration is computed by the summation of SPH gradient operator according to,
       ∂Ci ∑mj ∂Wij      =                                                                                                             (31)
       ∂xα           j  ρj  ∂xαi
   Different from the original OPS, in the present analysis, the shifting coefficient Dshift is computed based on the velocity-dependant
formulation by Skillen et al. [34]. This modification is to mitigate the numerical noise observed in the stationary region of the domain
due to the application of particle shifting. As a result, the shifting distance can be further expressed as,

                            ∂Ci       δxαi = −Cshifthδt‖ vβ ‖i                                                                                               (32)                             ∂xα
where Cshift is the dimensionless shifting coefficient, whose value is independent of the case scenario and is taken as 2 in this study. The
maximum shifting distance is set 0.1dp, in which dp is the initial particle space.
   Due to the truncated kernel support of particles near the free surface, the application of the shifting technique using Eq. (32) may
result in unphysical diffusion of free-surface particles. Following the algorithm by Khayyer et al. [7], a free-surface correction is
applied to the free-surface particles, which removes the shifting normal to the free-surface but allows the tangential shifting. The
shifting distance with free surface correction is given by,
                                                 (   /              (   /      )
       δxαi = −Cshifthδt‖ vβ ‖i ∂Ci  ∂xα −̃nβi  ∂Ci  ∂xβ )̃nαi                                                                       (33)

where ̃nαi  is the corrected unit normal vector of particle i, which is computed as,
                                (        )
                Lαβi  ∂Ci /∂xβ          ̃nαi = −          (        )                                                                                              (34)            ‖ Lαβi  ∂Ci /∂xβ  ‖

in which the Lαβi   is the renormalisation matrix for kernel gradient correction, given by,
     (∑(     )      )−1                             ∂Wij mj       Lαβi =        xαj −xαi                                                                                                 (35)
                                       j            ∂xβi   ρj

                                                                10

### Page 11

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

   In addition to the corrected shifting method, a particle classification scheme is also required to apply appropriate shifting distances
to certain particles. In this new treatment, the simulation domain is classified into four groups: external particles, free-surface particles,
free-surface vicinity particles and internal particles, as shown in Fig. 4. The first three groups apply to a particle with an incomplete
kernel support while the last one denotes the inner particle with a full kernel support. The searching procedure is as follows: in the first,
the free-surface particles are identified based on the calculated particle divergence, i.e., ∇⋅x < FST, in which FST is the threshold for
free-surface particles, and the particle divergence is calculated as,
     ∑  (     )                   mj           ∂Wij      〈∇⋅x〉i =         xαi −xαj                                                                                             (36)
                                            j  ρj           ∂xαi
   Then, the free-surface vicinity particles are detected as the particles that have distance less than h from the nearest free-surface
neighbours. For the free-surface particle with very few neighbouring particles, they are further subgrouped as external particles.
The remaining particles that have a full kernel support are identified as internal particles.
   Note that the parameters for the threshold values of different particle types shown in Fig. 4 are specific to 2-D cases. The extension
of the shifting algorithm to 3-D and the associated parameter settings have not been tested in this work and are suggested for future
research. For such a development, one can refer to the work by Mokos et al. [35], which discussed the 3D extension of the shifting
algorithm by Lind et al. [31] for multi-phase problems.
   For the internal particles with a complete kernel support, the shifting is applied without correction. The free-surface correction is
only applied to free-surface particles and free-surface vicinity particles. In addition, it is found that, for external particles, the lack of
neighbouring particles can result in inaccuracies in the calculation of the corrected particle concentration, leading to unphysical
shifting movement. As a result, the shifting is not applied to those particles. Consequently, the shifting distance is calculated as,
      ⎧
             0                                                                                               i                                   ∈E
                                                     (      ⎪⎪⎪⎪⎪⎪⎨                                                                                               i                                   ∈F                 −Cshifthδt‖ vβ ‖i                               ∂Ci /∂xα −  [̃nβi ( ∂Ci /∂xβ )]̃nαi )
       δxαi =                               (           [    (        )]  )                                                                  (37)
                                                     ∈If                                 /∂xα −    ̃nβi  ∂Ci /∂xβ   ̃nαi      i
                                                                                                i                                         ∈I      ⎪⎪⎪⎪⎪⎪⎩ −Cshifthδt‖−Cshifthδt‖ vβvβ ‖i‖i(∂Ci/∂xα)∂Ci

3.3. Boundary conditions

   Appropriate boundary conditions are essential for the solution of the coupled problem. Fig. 5 presents typical boundary conditions
for the general application [36]. In the proposed formulation, the primary variables requiring boundary values include velocity v,
effective stress σ’ for solid phase, and seepage discharge qL, liquid density/pressure ρL/pL for liquid phase. Two types of boundary
treatment are considered, namely the solid wall boundary condition and the free-surface boundary condition.

3.3.1. Solid wall boundary condition
   The solid wall boundary refers to the type of boundary that prevents the flow of liquids or restricts solid movement. A velocity
condition is usually specified for this boundary to enforce the no-slip/free-slip boundary conditions. In this treatment, a particle-based
boundary methodology originally proposed by English et al. [37] but later extended by Feng et al. [38,13] is adopted for the solid wall
boundary. As shown in Fig. 6, several layers of dummy boundary particles are created to characterise the physical boundary. For each
boundary particle b, a ghost node g is mirrored into the simulation domain to interpolate field variables. The interpolation follows the

  Fig. 4. The particle shifting scheme: (a) particle classification criteria; (b) particle shifting distance vector; (c) example of slope failure case.

                                                                11

### Page 12

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

                           Fig. 5. Illustrative diagrams of boundary conditions for (a) liquid phase and (b) solid phase.

                                         Fig. 6. Schematic diagram of the solid wall boundary treatment.

first-order consistent correction by Liu and Liu [25]. For details of the implementation, the reader can refer to Feng et al. [38].
   The liquid density and stress of the boundary particle are extrapolated from the interpolated values and gradients at ghost nodes, as
given by the following equation,
                                (                           (
       σαβb = σαβg +  xb −xg )∂xσαβg +  zb −zg )∂zσαβg                                                                           (38a)

                                (                           (
        ρLb = ρLg +  xb −xg )∂xρLg +  zb −zg )∂zρLg                                                                         (38b)
   For the no-slip boundary condition in the liquid phase and solid phase (or impermeable boundary for liquid phase and fully-fixed
boundary for solid phase), the velocity of boundary particles is constructed as,
        vαb = −vαg,                                                                                                       (39a)

       qαLb = −qαLg,                                                                                                   (39b)

where the velocity at the ghost nodes is calculated as,
     ∑
                vαj WgjVj
        vαg =    j∑          ,                                                                                                 (40a)
               WgjVj
                                 j

     ∑
               qαLjWgjVj
       qαLg =    j∑          .                                                                                              (40b)
                WgjVj
                                    j
   For the free-slip boundary condition, the liquid density remains the same as for the no-slip boundary, as determined by Eq. (38b),
while the stress of boundary particles is calculated differently and can be expressed as follows,
      ⎧           (                           (
      ⎨ σαβg +  xb −xg )∂xσαβg +  zb −zg )∂zσαβg   α = β
       σαβb =                                                                                                             (41)
      ⎩              −σαβg               α ∕= β

                                                                12

### Page 13

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

   The velocity of boundary particles for a free-slip condition is calculated according to,
        vαb = vαg −2vαg.n,                                                                                                  (42a)

       qαLb = qαLg −2qαLg.n.                                                                                              (42b)
   In certain scenarios, a prescribed pressure condition is required for the solid wall boundary, such as when simulating the
groundwater level at the lateral side of the simulation domain. Therefore, a new extension of the original boundary treatment has been
developed to allow the implementation of hydraulic head boundary conditions in the solid wall boundary. The liquid density and the
seepage discharge of boundary particles are written as,
        ρLb = 2ρL.pres −ρLg                                                                                               (43a)

       qαLb = qαLg                                                                                                     (43b)

where the liquid density ρL.pres corresponds to the prescribed pressure pL.pres for a given hydraulic head Hpres. Its value is calculated as,
                               (       /   )
          ρL.pres = ρL0 1 + pL.pres  KL                                                                                           (44)

in which the relationship between pL.pres and Hpres can be expressed as,
                                 (        )
          pL.pres = ρL0g Hpres −z                                                                                               (45)
   In addition, the porosity of boundary particles is set to remain constant at the initial porosity ϕ0 throughout the simulation in the
current application.

3.3.2. Free-surface boundary condition
   In the work by Feng et al. [13], a zero-pressure free-surface boundary condition is applied to simulate the rainfall-induced land
slide. While this boundary treatment simplifies the formulation, it is limited to rainfall events with extreme infiltration rates and
cannot handle cases with a given infiltration rate and other complex scenarios. This section presents a more general framework to treat
the free-surface boundary condition for a wide of application, such as rainfall infiltration, impoundment or drawdown, steady/
transient seepage.
   To enforce the free-surface boundary condition with a prescribed seepage flux or a prescribed pressure, the surface searching
algorithm is required to identify free-surface particles. This is aligned with the particle classification scheme applied in the shifting
algorithm, in which the particle divergence is calculated each time step to identify the free-surface particles. It should be noted that in
cases involving large deformations, it may be necessary to slightly increase the threshold for identifying free-surface particles. For
example, in a 2D problem, in reference to Eq. (37), a threshold of ∇⋅x > 1.7 could be used to prevent the potential omission of freesurface particles in particle searching when encountering large deformations. Once the free-surface particles are identified, the pre
scribed field variables, such as the infiltration rate or pressures, are then imposed for those particles.
   In addition, to implement the seepage flux boundary condition that the direction of liquid flow is not a constant but depends on the
normal direction of the boundary, such as zero normal flux boundary, the normal vectors at those free-surface boundary particles need
to be updated during the computation as the shape of domain changes. The calculation of normal vectors follows the free-surface
normal calculation in the shifting algorithm as shown in Eq. (34).
   In the present application, the free-surface threshold is tuned due to the limitation of the adopted free-surface searching method in
predicting free-surface particles in complex geometries such as those involved in large deformations. Alternative free-surface detection
methods, which may employ more complex algorithms but offer better accuracy, such as the work by Marrone et al. [39], could
potentially eliminate the need for tunable parameters but results in an increase in computational cost and algorithm complexity. The
implementation of such methods for the hydro-mechanical boundary condition at the free surface could be a future development.

3.3.2.1. Hydraulic boundary condition.

   (a) Hydraulic head boundary condition

   The hydraulic head boundary is the most commonly applied boundary condition and has various practical applications. The
prescribed hydraulic head can either remain constant for a steady-state seepage problem or change with time to simulate transient
processes such as fluctuations in groundwater level, flooding, or drawdown.
   Herein, the hydraulic head boundary condition is converted to the prescribed pressure boundary condition, using Eq. (44), and the
liquid density of the free-surface particles is prescribed as,
       ραLi−FS = ραL.pres                                                                                                      (46)

where the subscript i-FS denotes the particle belong to the free-surface particles.

   (a) Specified flow boundary condition

                                                                13

### Page 14

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

   The specified flow boundary condition is necessary for the description of the flow condition along the boundary with a given flow
rate, such as infiltration/evaporation, and undrained boundary condition. A prescribed seepage discharge boundary is needed for this
case, in which the given seepage discharge along the boundary is assigned to the free-surface particles according to
       qαLi−FS = qαL.pres                                                                                                      (47)

where qαL.pres is the prescribed liquid seepage discharge.
   However, the infiltration of liquid cannot continuously increase the pore liquid pressure, as the material has a limited capacity to
accommodate the infiltrated liquid. When the infiltration rate exceeds the material’s capacity, a condition known as "ponding" occurs.
In such a situation, the prescribed seepage discharge boundary condition is switched to a prescribed hydraulic head condition with a
maximum allowable hydraulic head Hmax. This switch is also applied during the desaturation process. When the porous material is
drying and reaches its loss capacity, the head boundary condition with the minimum allowable hydraulic head Hmin is activated. It is
noted that Hmax and Hmin represent the maximum and minimum capability of porous material to store the water content, whose value
can be calibrated from experiments.
   The specified flow boundary can be also applied to represent the impermeable layer or to describe the zero normal flux, where there
is no liquid flow normal to the boundary surface. In such cases, the seepage discharge for free-surface particles is calculated as follows,
       qαLi−FS = qαLi −̃nβi qβLĩnαi                                                                                                (48)

   (a) Potential seepage face boundary condition

   There is a situation where the boundary has neither a prescribed seepage discharge nor a prescribed pressure, and the boundary
condition is part of the solution. This is the case for the prediction of a seepage face, and this type of boundary condition can be referred
as the potential seepage face boundary. The seepage face, denoted as DF in the Fig. 5, is defined as the portion of the phreatic line that
interacts with the atmosphere, allowing the liquid to exit freely. However, the location of the seepage face is unknown prior to the
analysis, and requires numerical solutions. The boundary area within which the seepage face could potentially be located is referred to
as the potential seepage face boundary, illustrated as CF in Fig. 5.
   The pressure and seepage discharge along the potential seepage face boundary is defined as,
       pL ≤0, qL.n ≤0, pLqL.n = 0                                                                                          (49)
    Clearly, along the potential seepage face boundary, it is assumed that liquid accumulation pL > 0 and liquid inflow qL.n > 0 are not
allowd. The boundary condition can be either qL.n ≤0, pL = 0 for the liquid outflow under saturated condition, or qL.n = 0, pL ≤0 for
zero normal flux under unsaturated condition. There is a special case known as the seepage exit point, where the phreatic line first
reaches the boundary and starts to flow out (point D in the Fig. 5). It is the transition point from qL.n = 0 condition to pL = 0 condition
that satisfies qL.n = 0, pL = 0.
   In such a situation, a trial solution of the boundary condition is required. This is achieved by predicting the seepage discharge along
the potential seepage face boundary with drained condition pL = 0. If the predicted seepage discharge indicates an outflow condition
qL.n ≤0, the boundary is set to be drained pL = 0, otherwise the hydraulic boundary is set to be undrained qL.n = 0 as the inflow qL.n >
0 is not permitted. The flow chart of the boundary treatment of the seepage face prediction is shown in Fig. 7.
    It is also worth noting that since this type of boundary condition relies on the SPH solution for the location of the seepage face, it can
be sensitive to the error in the numerical calculation. Errors in the liquid phase can impact the accuracy of the seepage face prediction,
and inaccuracies in the boundary treatment may potentially lead to numerical instability. However, it will be shown later in Section 4,
the use of diffusion term helps mitigate these issues, resulting in a stable and accurate simulation.

                                            Fig. 7. Flow chart of the potential seepage face boundary.

                                                                14

### Page 15

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

3.3.2.2. Mechanical boundary condition. Apart from the hydraulic boundary conditions, the free surface of a porous material may also
be subjected to external stresses, such as liquid pressure loading under submerged condition or surcharge loading. The implementation
of those stress boundary conditions is present in this section.

   (a) Confining stress boundary condition

   Inspired by the surface tension model by Vergnaud et al. [40] that provides surface and continuous force along the interface, a
similar term is formulated in this study and included into the momentum equation for a prescribed stress along the free surface, which
is given by,
      〈dvα 〉    1 ∑                      N  mj (                   ∂Wij   βcσc        =            σαβi + σαβj + Πijδαβ)   +      δΣ.ĩnαi + gαi ,                                                          (50)
          dt      i    ρmi  j=1 ρj                     ∂xβi     ρmi

where σc is the prescribed confining stress, δ∑ .i is the interfacial function which vanishes as the distance to the free-surface increases
and is computed according to,
     ∑∂Wij          δΣ.i = 2 ‖         Vj ‖,                                                                                               (51)
                                           j  ∂xβi

βc is a switch for the confining stress boundary condition. In the present analysis, the extra term is only included in the free-surface
particles such that βc is expressed as
       {
            0  i⊂innerparticle       βc =                                                                                                              (52)            1     otherwise
   However, it has been observed that stress fluctuations near the free surface occur when including the extra term in the momentum
equation for a prescribed confining stress. To address this issue, the kernel gradient renormalization technique shown in Eq. (35) is
applied to the governing equation of free-surface particles in the solid phase, including the momentum equation i.e., Eqs. (50) and (51),
and the strain rate equation i.e., Eq. (20). This corrective approach helps to mitigate the stress fluctuations and improve the accuracy of
the simulation.

   (a) Submerged boundary condition

   For the porous material fully submerged in the liquid, its free surface could be under pressure loading from the liquid, resulting in
the increase of total stress at the free surface. To reproduce this submerged condition, the confining stress boundary condition is
adopted with the prescribed stress set as,
       {
                  pLi    pLi > 0       σc =                                                                                                              (53)             0   otherwise
    Clearly, with the proposed submerged boundary condition, the free surface of the solid can experience the confining stress caused
by the liquid pressure, while no extra stresses are applied to the surface if the porous mixture is in an unsaturated condition. This type
of boundary condition is crucial for the simulation of saturated porous material immersed in the liquid. Without the consideration of
liquid pressure loading in the solid phase, the total stress at the free surface remains zero due to the dynamic free-surface boundary
condition in SPH, resulting in unphysical results, such as the free-surface instability identified in Bui et al., [9]

3.4. Time integration scheme

   In present analysis, the explicit second-order Symplectic Position Verlet scheme by Leimkuhler and Matthews (2015) as described
in Domínguez et al. [41] is adopted to integrate the governing equations in time. For the two-phase coupled hydro-mechanical problem
with explicit time integration schemes, the size of time step is dependant on the CFL (Courant-Friedrichs-Levy) condition, the
maximum force term, the numerical speed of sound, and the diffusion of liquid flow. The variable time step is computed according to
[13],
            (√̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅/   α )
        Δtf = min                 h ‖ f i ‖                                                                                            (54a)
                                   i

                       h
        Δtcv = min                                                          ,                                                                                   (54b)                                     i                     hvαijxαij
                      cs0 + max                       ‖ xαijxαij+η2 ‖                                                          j
              (γL h2cv )
        Δtsp = min                                                                                                                        (54c)
                                     i   KL 2K

                                                                15

### Page 16

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

                                (            )
      Δt = C0min Δtcv, Δtf , Δtsp                                                                                      (54d)

where
        (      )
                    ∂S
        cv = ϕ  SL −KL                                                                                                    (55)                       ∂pc

4. Validation cases

   The new fully-coupled SPH model described above is implemented in the CPU branch of open-source SPH code DualSPHysics [41].
The performance and accuracy of the proposed numerical scheme is assessed in this section through several benchmark examples,
including 1-D infiltration, fully/partially submerged still soil column, 1-D consolidation, 2-D seepage flow, and landslides in unsat
urated slope due to rainfall, with the comparison to available analytical solution, numerical solution and experimental data.

4.1. 1-D infiltration test

   This case refers to one-dimensional infiltration within a rigid unsaturated porous column, which is used to examine the capability of
proposed scheme in solving transient unsaturated seepage problem. Analytical solutions are available for this case as derived in Feng
et al. [13]. Results of using standard SPH formulation are also presented for comparison.
    Fig. 8(a) illustrates the geometries and boundary conditions of the 1-D infiltration test. To reproduce one-dimensional liquid flow,
periodic boundary conditions are applied in the x-direction of the domain. The bottom boundary of the porous column is set as
impermeable while a zero-pressure boundary condition is imposed at the free surface for the water infiltration. A uniform suction
pressure of pc = 5 kPa is assigned to all particles as their initial conditions. The simulation is conducted in the absence of gravity and the
water infiltration is driven by the pressure difference. The linearised SWCC model is used, and the permeability is assumed to be
constant to make the simulation comparable with the available analytical solutions.
   Table 1 presents the material properties and the numerical parameters required for the simulation. Three sets of particle resolutions
of 0.1, 0.05 and 0.02 m are adopted, resulting in H/dp equals to 10, 20 and 50, respectively, in which H is the height of the column.
   The evolution of liquid pressure of the unsaturated porous column due to water infiltration presented in Fig. 8(b) shows a clear
wetting process with noise-free pressure profile. Fig. 9 reports the comparisons of numerical results of the evolution of suction
pressure, using standard SPH formulations (e.g., [13]) and improved SPH formulations in this study, against the analytical solutions.
As shown in Fig. 9, with the use of traditional SPH formulations, the calculated suction profile fluctuates and shows deviations from the
analytical solution. This discrepancy is noticeable for a coarse resolution but can be reduced with a finer dp. By contrast, the use of
proposed formulations results in the predicted pressure evolution closer to its analytical solutions even for a relatively large dp.

4.2.  Fully/partially submerged soil column under gravitational loading

   The simulations of the static soil column fully/partially submerged in water are performed to investigate the effectiveness of the
proposed wall boundary condition treatment and the applicability of the submerged boundary condition to the coupled problem. This
type of test case has been studied by Bui and Fukagawa [42] to validate their two-phase double-layer approaches for saturated soils.
The geometries and applied boundary conditions of the soil column are shown in Fig. 10. The height of the soil column is set as H = 1.0
m. For the fully submerged condition, the free surface of the water body is 2.0 m above the ground (i.e., z = 3 m), while the water table
is positioned at the bottom of the soil column (i.e., z = 0 m) for the partially submerged soil. Periodic boundary conditions are applied
to both lateral sides to achieve one-dimensional soil deformation and water flow. The bottom boundary of the soil column is set as
impermeable for the liquid phase and no-slip for solid phase using the wall boundary particles, in reference to Eqs (38) ~ (39). The

                     Fig. 8. 1-D infiltration test: (a) geometry and numerical configuration; (b) evolution of liquid pressure.

                                                                16

### Page 17

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

                  Table 1
                    Material and hydraulic properties for the 1-D infiltration test.
                       Paramters                                                     Unit                            Value
                      h/dp                                                       –                                 1.8
                      Courant number                                             –                                 0.2
                          Solid density ρS0                                        kg/m3                        2100
                        Liquid density ρL0                                       kg/m3                        1000
                         Porosity ϕ                                                  –                                 0.3
                        Liquid bulk modulus KL                                   Pa                           8.00E+06
                        Saturated hydraulic conductivity Ksat                        m/s                             5.00E-03
                 SWCC constant as                                          Pa−1                            1.00E-04

Fig. 9. The evolution of suction pressure along depth z without the gradient correction (left column) and with the gradient correction (right
column). First row H/dp = 10, second row H/dp = 20, third row H/dp =50.

                                                                17

### Page 18

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

                    Fig. 10. Schematic diagram of the soil column (a) fully submerged and (b) partially submerged in water.

hydraulic head boundary condition using Eq. (46), along with the submerged boundary condition using Eqs (50) and (53), is applied to
the free surface for a specific submerged condition and its corresponding stress state at the free surface.
   The soil behaviour is simulated using a linear elastic model, and the relationship between the suction pressure and the degree of
saturation is described by the linear SWCC model. The parameters used in the simulation are listed in Table 2. Four sets of particle
resolutions of 0.2, 0.1, 0.05 and 0.02 m are adopted, resulting in H/dp = 5, 10, 20 and 50. The liquid pressure is initialised to its
theoretical solution under hydrostatic conditions, while the initial stress is set as zero.
    Fig. 11 plots the distributions of the pore liquid pressure, effective stress, and total stress at steady state obtained from SPH against
theoretical solutions. Clearly, with the use of hydraulic boundary condition, the pressure values at the free surface of the soil domain
can be properly specified. It is noted that in the partially submerged case, the pressure-loading boundary condition is inactive, resulting
in a zero total stress condition at the free surface due to the dynamic free-surface boundary condition in SPH [43]. On the other hand, in
the fully submerged case, the total stress at the free surface should be non-zero due to the weight of liquid and this is achieved with the
proposed method, in which the magnitude of total stress at the free surface becomes equal to the corresponding liquid pressure, thanks
to the submerged boundary condition. However, without the use of a submerged boundary condition, the total stress at the free surface
in the submerged case tends to be zero, and the effective stress becomes negative, indicating a tensile state. This can result in
unphysical estimations of the stress state in the porous materials, and it is also the cause of the numerical instability observed in
previous studies [9], where particles were expelled from the domain due to the tension experienced by the soil at the free surface as a
result of neglecting the liquid loading.
   Overall, the SPH results show satisfactory agreements with theoretical solutions for both fully/partially submerged cases. In
addition, the convergence behaviour of the total stress is shown in Fig. 12. with the order of convergence from dp = 0.2 to dp = 0.05 of
approximately 1.35 before tending to a constant value as expected (Quinlan et al. [44]) for partially submerged case and 1.06 for fully
submerged case. These results indicate the proposed formulations are applicable to study the fully/partially saturated problems and
the proposed boundary condition can accurately capture the change of submerged condition in the soil.
   The time series of the kinetic energy of all the particles (presented in a logarithmic scale) is shown in Fig. 13. It is found that the
submerged case exhibits less oscillation, while the partially submerged case demonstrates significant fluctuations. With the same

                  Table 2
                    Material and hydraulic properties for the soil column test.
                       Paramters                                                     Unit                            Value
                     h/dp                                                       –                                 1.8
                      Courant number                                             –                                 0.2
                        Viscous damping αd                                          –                                 0.1
                          Solid density ρS0                                        kg/m3                        2100
                      Young’s modulus E                                MPa                         20
                         Poisson’s ratio ν                                             –                                 0.3
                        Liquid density ρL0                                       kg/m3                        1000
                         Porosity ϕ                                                  –                                 0.3
                        Liquid bulk modulus KL                                   Pa                           2.00E+07
                        Saturated hydraulic conductivity Ksat                        m/s                             1.00E-03
                 SWCC constant as                                          Pa−1                            2.00E-05

                                                                18

### Page 19

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

Fig. 11. Comparisons of the pressure, effective stress and total stress profile between the SPH results and theoretical solutions for partially sub
merged case HL = −1 m (left) and submerged case HL = 2 m (right) with H/dp = 20.

       Fig. 12. Normalised L2 norm error of the total stress profile (a) partially saturated case HL = −1 m; (b) submerged case HL = 2 m.

                              Fig. 13. Time series of kinetic energy (a) partially saturated case; (b) submerged case.

                                                                19

### Page 20

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

dissipation coefficient, the use of proposed artificial damping term in Eq. (25) effectively damps out the numerical oscillations in
velocity with a faster stabilisation than the use of artificial viscosity. This is particularly noticeable in the partially saturated case,
where the use of artificial viscosity cannot efficiently dissipate the violent particle movement and the kinetic energy remains high even
after 30 s simulation for this stationary case.

4.3. 1-D consolidation test

   In this case, the proposed SPH scheme is adopted to solve the classical one-dimensional Terzhaghi consolidation problem to
examine the coupling of seepage flow and solid deformation. Fig. 14(a) shows the problem definition.
   In the consolidation test, a constant vertical load is applied to the top of a fully saturated porous column. Initially, the pore liquid
pressure increases due to the applied surcharge, but over time, the pressure begins to dissipate as the top of the porous column is open
to drainage and the pore liquid drains out of the porous column. This expulsion of liquid results in a gradual increase in the effective
stress within the solid grains, which causes the solid grains to rearrange and settle. It is a popular benchmark example for coupled
hydro-mechanical numerical schemes with analytical solution available for comparison (e.g., [14,12]).
    Fig. 14 (b) shows the numerical configuration of the 1-D consolidation problem. The porous column is 1 m in height and 0.4 m in
width. The porous column is initially fully saturated in an equilibrium condition with both pore liquid pressure and effective stress
initialised as 0 kPa due to the assumption of zero gravity. Similar to the 1-D infiltration test, periodic boundary conditions are applied
to both sides to enable 1-D solid deformation and 1-D liquid flow. The proposed solid wall boundary treatment is adopted to enforce the
impermeable and no-slip boundary condition at the bottom of the porous column, while two consecutive stages are considered for the
free-surface top boundary. In the first stage, namely the loading stage, the top boundary is set as undrained and a surcharge of q0 = 50
kPa is applied with the use of the proposed stress boundary condition. To mitigate the oscillations induced by a sudden load, the
applied surcharge is linearly increased to the designed value within a short period of tL = 0.01 s. Ideally, the applied loading condition
results in a sudden rise in the pore liquid pressure to 50 kPa, while the effective stress remains at 0 kPa at the end of loading stage.
Then, in the second stage, namely the dissipation stage, the top of the porous column is open for drainage (i.e., enforcing pL = 0 kPa)
while the applied load of 50 kPa is maintained. As a result, the excess pore liquid pressure dissipates gradually, leading to the increase
of effective stress and vertical settlement.
   The porous column is modelled as a linear elastic material. The material properties and numerical parameters are listed in Table 3.
The initial particle space is set as 0.1, 0.05 and 0.02 m, respectively, corresponding to H/dp = 10, 20 and 50.
    Fig. 15(a) shows the build-up of the pore liquid pressure at the loading stage. It is noted that the predicted pore liquid pressure near
the wall boundary is slightly larger than the anticipated value of q0. This is due to the numerical oscillation caused by the sudden
application of a surcharge load and a relatively low dissipation term applied in this case. To settle down those dynamic oscillations, an
additional 1 s simulation is conducted with all the boundaries kept undrained and the surcharge maintained. It is found that the pore
liquid pressure reaches the applied load q0 in an equilibrium condition at the end of the additional 1 s simulation, and results obtained
in this stage are the initial condition (t = 0 s) for next dissipation stage.
   The isochrone of excess pore pressure in the dissipation stage obtained from SPH against the analytical solutions for all the three
particle resolutions is shown in Fig. 15(b) ~ 15(d). It is found that the prediction by SPH achieves an overall agreement with reference

                               Fig. 14. 1-D consolidation test: (a) problem definition; (b) numerical configuration.

                                                                20

### Page 21

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

                       Table 3
                       Numerical parameters and material properties for the 1-D consolidation test.
                             Paramters                                          Unit                            Value
                            h/dp                                             –                                 1.3
                            Courant number                                  –                                 0.2
                              Viscous damping αd                               –                                 0.1
                                Solid density ρS0                              kg/m3                        2100
                            Young’s modulus E                        MPa                             20.0
                                Poisson’s ratio ν                                   –                                 0.3
                               Liquid density ρL                              kg/m3                        1000
                                Porosity ϕ                                        –                                 0.3
                               Liquid bulk modulus KL                          Pa                            2.0e+09
                              Hydraulic conductivity K                        m/s                              1e-4

Fig. 15. The isochrone of excess pore pressure: (a) loading stage H/dp = 20; and (b) dissipation stage H/dp = 10; (c) dissipation stage H/dp = 20; (d)
dissipation stage H/dp = 50.

solutions. The solution with the coarsest particle resolution shows a slight deviation from the analytical solution, but it can be
improved with a smaller dp. In Fig. 16, the convergence study of the pore liquid pressure at initial transient stage t = 0.05 s indicates a
satisfactory order of convergence of 1.44. The estimation of convergence order is obtained by following the standard practice, which
involves taking the gradient of the best fit line of L2-error vs. dp on the log-log plot.
    Fig. 17 plots the isochrone of effective stress obtained from the use of proposed stress boundary condition in standard SPH and the
improved method incorporating kernel renormalisation. It is evident that using the proposed stress boundary condition with standard
SPH can lead to a fluctuating stress profile near the free surface. However, this issue can be much improved by applying kernel
renormalisation for the free-surface particles.
   Furthermore, Fig. 18 reports the temporal variation of effective stress at three different heights and of the surface settlement, as
predicted by the SPH method, alongside the corresponding analytical solutions. Once again, a close agreement is observed between the
SPH results and the analytical solutions. These findings indicate that the proposed scheme effectively captures the hydro-mechanical
coupling within the porous material.

                                                                21

### Page 22

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

                                     Fig. 16. Normalised L2 norm error of the pressure profile at t = 0.05 s.

Fig. 17. The isochrone of effective stress: (a) stress boundary condition with standard SPH, (b) stress boundary condition with kernel correction.
(H/dp = 20).

       Fig. 18. Evolution of mechanical variables: (a) effective stress at three different height and (b) the surface settlement. (H/dp =20).

4.4. 2-D seepage flow test

   The 2-D seepage flows in porous media are studied in this case to test the implementations of the hydraulic head BC and potential
seepage face BC, and to demonstrate the capability of the proposed SPH model in predicting seepage surface (or phreatic line). The
predicted free-surface at steady-state is compared with the FEM results presented by Pedroso [45] for validation. Two different shapes,

                                                                22

### Page 23

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

        Fig. 19. 2-D seepage flow: numerical configurations of (a) flow through rectangular dam and (b) flow through trapezoidal dam.

i.e., rectangular and trapezoidal, of porous domain (or embankment) are considered in this study. The geometries and boundary
conditions of these two configurations are shown in Fig. 19. The water level at the upstream side is equal to the height of the porous
media while a certain range of water level is sustained at the downstream side. The hydraulic head BC is applied at the upstream side of
the embankment while the mix of hydraulic head BC and potential seepage face BC is imposed at the downstream side of the
embankment.
   The Van Genuchten model is applied in this study. The model parameters used in the simulation are calibrated against the hydraulic
model by Pedroso [45], and the resulting curves are plotted in Fig. 20. Table 4 lists the model parameters used in the simulation.
   The particle spacings are set to be dp = 0.2 m for both cases. The phreatic line is assumed to be initially equal to the height of
domain and the pore liquid pressure is approximately linearly distributed below the initial water table (i.e., fully saturated, hydrostatic
condition). Then, the porous domain will be desaturated due to the gravity and the water level sustained at the downstream side. The
transient process is simulated for 500 s physical time and the steady state is reached at the end of the simulation.
    Fig. 21 shows the calculated pressure field of the seepage flow through the rectangular embankment and the trapezoidal
embankment at final instant, respectively. The resulting phreatic lines are highlighted with dashed blue line in Fig. 21, while those by
the reference FEM solutions [45] are highlighted with red line. Note that the predicted phreatic lines (or zero-pressure lines) in this
study are evaluated by linear interpolation of the pressure field. Clearly, the predicted phreatic line from SPH match well with the
reference solutions, indicating the capability of the present method in solving the transient seepage problem involving seepage surface
and complex geometries such as a sharp corner.
   Furthermore, the predicted degree of saturation with and without the use of diffusion term is plotted in Fig. 22. It is noted that
without the use of the diffusion term (Eq. (25)), numerical noise is observed at the top right corner. This can be attributed to the local
inconsistency and the numerical errors in the calculation of normal at the corner. However, as shown in Fig. 22(b), the use of diffusion
significantly smooths out the numerical noise in pressure. Another benefit of using the diffusion term is that the smoothing of pressure
also helps to stabilise the simulation. As observed in the numerical experiment, errors at the corner grow with time if the diffusion term
is not applied, resulting in the crash of the simulation. In addition, the use of the diffusion term also helps with the treatment of the

                                       Fig. 20. SWCC model used by Pedroso et al. (2015) and this study.

                                                                23

### Page 24

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

                      Table 4
                       Numerical parameters and material properties for the 2-D seepage flow test.
                            Paramters                                          Unit                            Value
                            h/dp                                             –                                 1.3
                            Courant number                                  –                                 0.2
                              Liquid density ρL                              kg/m3                        1000
                               Porosity ϕ                                        –                                 0.3
                              Liquid bulk modulus KL                          Pa                           8.00E+06
                             Hydraulic conductivity K                        m/s                             5.00E-03
                     SWCC constant λ                                  –                               0.780
                     SWCC constant pref                              Pa                           1030

                      Fig. 21. Pressure contour of flow through porous dam: (a) trapezoidal dam, and (b) rectangular dam.

   Fig. 22. Contour plot of degree of saturation of flow through porous dam at t = 500 s: (a) without diffusion term; (b) with diffusion term.

potential seepage face boundary, as this type of boundary condition requires the solution of the numerical problem, and the accurate
prediction of the pressure profile is therefore essential. Numerical noise in the pressure profile could lead to an incorrect boundary
condition as shown in Fig. 22(a), which potentially further makes the simulation prone to instability.

4.5.  Full-scale experiment of rainfall-induced landslides

   The full-scale landslide experiment performed by Moriwaki et al. [46] is simulated to examine the validity of the proposed scheme
for the coupling of unsaturated seepage flow and soil deformation. Artificial rainfall was sprinkled above the test flume in the
experiment to initiate the failure. The model slope had dimensions of 21.6 m in length, 7.4 m in height, 3 m in width and 1.2 m in
depth. It consisted of four sections: a 1-m-long horizontal segment at the upper portion, followed by a 10-m-long main slope with an
inclination of 30◦, a lower 6-m-long segment inclined at 10◦, and a 6 m horizontal segment at the slope toe, as shown in Fig. 23.

                                                                24

### Page 25

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

                Fig. 23. Rainfall-induced landslides experiment by Moriwaki et al. [46]: geometries and numerical configuration.

   The slope was prepared using loose Sakuragawa River sand, and was instrumented with extensometers and piezometers during the
experiment for the evolution of surface displacement and pore liquid pressure. A constant rainfall intensity of 100 mm/h was
maintained throughout the test. About 105 min after the start of water sprinkling, the piezometer placed at the bottom of the 6 m
horizontal slope segment recorded the first rise of pore liquid pressure and a rapid landslide was observed at 154 min, on the upper 30◦
slope segment.
   The numerical configuration for the landslide experiment is shown in Fig. 23. The initial particle spacings of 0.1 m is adopted,
resulting a total of 3806 particles. For the mechanical boundary conditions, the bottom of the computational domain is modelled using
the no-slip wall boundary condition to assume a perfectly rough interaction with the above soil layer, while free-slip conditions are
enforced to the two lateral side boundaries. As for the hydraulic boundary, an impermeable boundary is applied to both the bottom and
sides to enforce zero normal flux along the boundaries while the infiltration boundary condition is assigned to the free-surface particles
with a prescribed rainfall intensity of 3 × 10−5 m/s. The slope is assumed to be initially unsaturated with a uniform pore liquid pressure
distribution of −7.0 kPa, which is estimated from the initial water content reported in the experiment. Initial stress profiles are
generated through gravitational loading with the use of damping term to fast stabilisation. After the initial conditions are obtained,
water infiltration is then allowed to initiate the simulations.
   The soil behaviour is simulated using the elasto-plastic Drucker-Prager model. The Van Genuchten model is used to characterise the
hydraulic behaviour of pore fluid. The material and hydraulic properties are listed in Table 5. The mechanical properties of Sakur
agawa River sand are referenced from Nguyen et al. [47], and some of them are calibrated for the suction-dependant model. The
parameters of the hydraulic constitutive model are taken from Yang et al. [48], which are estimated based on the grain-size distri
bution and index properties of the test soils reported by Moriwaki et al. [46].
   In the following, comparisons are made between the numerical results and experimental measurements, for the phreatic surface,
pore pressure evolution, the sliding surface, and the ground surface displacements at pre-failure and post-failure stage.
   The evolutions of vertical seepage discharge and pore liquid pressure at different time instants due to rainfall infiltration are plotted

                  Table 5
                  Numerical parameters and material properties for the full-scale landslides experiment.
                       Paramters                                                     Unit                            Value
                      h/dp                                                       –                                 1.3
                      Courant number                                             –                                 0.1
                        Viscous damping αd                                          –                                 0.1
                        Density of solid grain ρS                                  kg/m3                        2690
                        Density of liquid ρL                                      kg/m3                        1000
                         Porosity ϕ                                                  –                                0.46
                        Saturated hydraulic conductivity Ksat                        m/s                            3E-04
                        Liquid bulk modulus KL                                   Pa                           2.00E+06
                  Maximum degree of saturation Smax                            –                                 1.0
                        Residual degree of saturation Smin                             –                               0.087
                 SWCC constant λ                                             –                                0.61
                 SWCC constant pref                                       Pa                           4350
                      Young’s modulus E                                MPa                         6
                         Poisson’s ratio ν                                             –                                 0.3
                       Cohesion c                                              Pa                           0
                      Peak friction angle φp                                                         ◦                            34
                        Residual friction angle φr                                                     ◦                            18
                         Softening coefficient ηφ                                       –                            2
                        Suction hardening coefficient As                                            ◦                            0
                        Suction hardening coefficient Bs                               –                            30
                       Suction-dependant cohesion cs0                             Pa                           2000

                                                                25

### Page 26

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

  Fig. 24. Contour plot of vertical seepage discharge (left column) and pore liquid pressure (right column) for the rainfall-induced landslides.

Fig. 25. Improvement by the particle shifting: prediction of deviatoric plastic strain and vertical seepage discharge (a) without particle shifting and
(b) with particle shifting.

in Fig. 24. It is evident that the wetting process caused by water infiltration is well reproduced, with a noise-free pressure profile
throughout the entire simulation. The proposed model successfully captures the prediction from the onset of instability due to water
saturation to the subsequent motion of the sliding mass after failure.
   In addition, the simulation results without the use of particle shifting are also presented in Fig. 25, where the deviatoric plastic
strain and the vertical seepage discharge are plotted and compared with the results obtained when particle shifting is applied. It is
evident that without particle shifting, particle disorder near the boundary can be observed, leading to particle penetration into the wall
boundary. This local instability also introduces numerical noise in the vertical seepage discharge profile, as shown in Fig. 25(a).
Furthermore, a noticeable particle clumping occurs in the deformed region where negative liquid pore pressure exists, possibly due to
the tensile instability issue in SPH. However, these issues are significantly improved when particle shifting is utilized, as depicted in
Fig. 25(b), resulting in a stable and accurate solution. It is also noteworthy that in some cases involving volume expansion during the
post-failure stage, a sparse particle distribution may be observed in the deformed region, even after applying particle shifting. In such
situations, finer particle resolution could be adopted to better capture the particle motion and dynamics in the volume expansion
region.
    Fig. 26(a) presents the calculated phreatic surface level (or zero-pressure line) against the measured water table, while the com
parison of the sliding surface found in experiments with the localised plasticly-deformed surface obtained from the simulation is shown

                                                                26

### Page 27

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

Fig. 26. Comparison of SPH results with experimental observation just prior to the failure: (a) location of phreatic surface, and (b) location of
failure surface.

in Fig. 26(b). The predicted locations of both the water table and sliding surface are in agreement with the experimental measure
ments. More importantly, the proposed model captures the observed failure mechanism in the experiments, where failure initiates in
the upper 30◦slope section and the shape of the failure surface exhibits a mixture of curved and planar surfaces, resulting in trans
lational movement of the sliding mass.
   In addition, the prediction of the pore liquid pressure evolution along the bottom boundary of the slope is compared with the
experimental measurements, as shown in Fig. 27. The measured results from piezometers, labelled as G1, G3, G5, G7, G9, and G11 in
Fig. 23, are adopted for comparisons. An overall good agreement is achieved between the SPH results and the measured results, except
for the prediction at G-1, G-3, and G-5 where a notable deviation is observed. The lesser liquid accumulation in this region can also be
reflected in the prediction of phreatic surface in Fig. 26, where the phreatic line at the upper portion of the slope is slightly lower than
the one measured in experiment. It is noted that the prediction of rising speed of liquid pressure at G-1, G-3, and G-5 is lower than the
experiment data, but the start time for the first pressure rise matches well with the experiment. The underlying reasons for this result
can be attributed to the isotropic assumptions made in the model, where the permeability is assumed to be the same in all directions.
Our numerical experiments showed that a closer agreement can be achieved by setting the horizontal permeability to be lower than the
vertical permeability, resulting in less liquid flowing from the upper portion to the lower portion. However, due to the lack of relevant
data, the analysis with the anisotropic permeability will not be considered in this study.
    Fig. 28 shows the comparisons between numerical simulation and experiment of surface displacement during the rapid slide at
three different locations, namely, D1, D3, and D5. In the experiment, the slope failure in experiment was initiated 154 min after the
start of sprinkling, and the failure process lasted approximately 6 s. The maximum cumulative surface displacements recorded in the
post-failure stage were reported to be between 3 m and 3.7 m. In contrast, the failure is triggered at 156 min in the simulation, and the
sliding mass continues to move for approximately 7 s. The predicted maximum cumulative surface displacements are found to be 2.9 m
at D5. Overall, the present model generally captures the failure process, although certain disparities with the experimental

            Fig. 27. Comparison of the pore liquid evolution before the slide between the numerical simulation and the experiment.

                                                                27

### Page 28

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

Fig. 28. Comparison of the surface displacement between the numerical simulation and the experiment: (a) before the failure, (b) during the
post-failure.

measurements exist. The measured surface displacement evolution before failure tends to be more gradual than the SPH predictions,
and there is an underestimation of the maximum cumulative surface displacements, particularly for D3, at the post-failure stage.
Similar results have also been reported in other numerical studies [49,47], and the resulting differences could be attributed to the
complexity of the soil behaviour in the experiment, which the adopted constitutive model cannot fully capture.
    It is worth noting that in the FEM study conducted by Yang et al. (2020), [48] an elastoplastic constitutive model with nonlinear
and stress-dependant modulus was adopted and a closer agreement with experimental results of the surface displacement before the
failure was attained. However, their investigation did not extend to capturing post-failure behaviour due to the inherent limitations of
FEM in handling large deformations. The effectiveness of their constitutive model to account for post-failure displacements remains
unclear. The implementation of the model by Yang et al. (2020) [48] or other advanced constitutive model and exploration of their
performance for better capturing the surface displacement evolution at both pre-failure and post-failure could be considered for future
investigations.
   In general, the obtained results indicate that the coupled hydro-mechanical model is able to capture the deformation behaviour and
hydraulic response as well as the failure mechanism of unsaturated porous media. It is finally noted that comparing to the previous
study of this case which only focuses on either the pre-failure/failure stage (e.g., [48]) or post-failure stage (e.g., [47]), the proposed
study integrates the analysis of both the pre-failure triggering and post-failure flow with the predictions and measurements in a
favourable agreement.

5. Application example: failure of embankment dam due to rapid drawdown

   Rapid drawdown refers to the process of the quick reduction of water levels, which is a classical scenario in embankment and slope
engineering. The lowering of the water level has two main effects: firstly, it reduces the stabilising external hydrostatic pressure acting
on the structure, and secondly, it modifies the internal pore liquid pressures within the structure. As a result, the porous materials in the
embankment may become unstable, leading to potential sliding or collapse. This case is devoted to simulating the rapid drawdown
process in an embankment to explore the potential applicability of the proposed method in treating complex case scenarios with
different mechanisms.
   The numerical model has dimensions of 18 m in length, 5 m in height, and includes a slope with an inclination of 45◦to the
horizontal ground, as shown in Fig. 29. The initial particle spacing of 0.1 m is adopted, resulting in a total of 5211 domain particles.
  A free-slip condition is applied to the left side of the domain, while the bottom is set to be no-slip. The hydraulic head boundary

                                                 Fig. 29. Geometries of the embankment model.

                                                                28

### Page 29

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

condition is applied to the free surface, in which the prescribed pressure is set as a function of time to simulate the change in water
level, according to,
                               (        )
          pL.pres = ρL0 Hpres −z g                                                                                              (56)

where Hpres is given by,
        {
              3                                        t < 100        Hpres =                                                                                                            (57)              max(3 −0.01(t −100), 1)    t ≥100
    It is noted that, with the adopted boundary condition, the water level at downstream side is maintained at 3 m for 100 s, and then
the drawdown develops for 200 s at a rate of 0.01 m/s until the water level reaches 1 m. In addition, the submerged boundary condition
for the solid phase is also active along the free surface as the removal of the external liquid pressure is the main triggering factor for the
failure.
   For the pressure values of free-surface boundary particles above the water level, two assumptions can be made: (i) constant
approximation and (ii) linear approximation [36]. The former describes the atmosphere effect governed by the climate conditions,
while the latter represents the linear variation of suction due to capillary effect. In the present application, these two approximations
are combined in a way that the linear approximation is adopted, but with a maximum constant suction pressure of 7 kPa. This allows
the capillary effect to be reproduced near the phreatic line, while also considering the atmosphere effect at locations away from the
phreatic line. This treatment also enables a smooth transition between the zero-pressure line and the constant suction, and avoids
unphysical high suction when solely using linear approximation.
   The initial pressure profile and stress profiles are generated through gravitational loading with the application of the adopted
boundary condition. The soil behaviour is simulated using the elasto-plastic Drucker-Prager model, while the hydraulic behaviour of
the pore liquid is characterized using the linear model expressed in Eq. (14a). The numerical parameters as well as material properties
used in the simulation are present in Table 6.
    Fig. 30 shows the evolution of pore pressure and deviatoric plastic strain predicted by SPH at different time instant, in which the
resulting phreatic lines are marked with dashed red line. Again, an accurate and noise-free pressure field is reproduced by the proposed
method. As the lowering of the water level at downstream side, the sliding surface develops, leading to the instability of the
embankment.
   Additionally, the predicted pressure profile with and without the application of the diffusion term is compared in Fig. 31. Without
the use of the diffusion term, the solution of pore liquid pressure exhibits numerical fluctuations and noise when encountering large
deformations. This, in turn, affects the prediction of the phreatic surface. However, the inclusion of the diffusion term effectively
smooths out the numerical noise, resulting in an accurate prediction of the pressure profile as well as the phreatic line.
    Fig. 32(a) reports the simulation results using artificial viscosity (αμ = 0.1). It is observed that particle wiggles occur along the free
surface, particularly in the submerged area, which can be possibly attributed to the presence of liquid pressure loading.
   However, the instability at the free surface is not observed when the new viscous damping term is applied, as shown in Fig. 32(b)
with the damping coefficient set to αd = 0.1, indicating the new viscous damping term is necessary for the coupled problem to stabilise
the simulation.
    It is worthwhile to mention that in the work by Bui et al. [9] and Bui and Fukagawa [42], a similar phenomenon of unphysical

                  Table 6
                  Numerical parameters and material properties for the embankment failure due to rapid drawdown.
                       Paramters                                                     Unit                            Value
                      h/dp                                                       –                                 1.3
                      Courant number                                             –                                 0.2
                        Viscous damping αd                                          –                                 0.1
                        Liquid density diffusion δL                                    –                                 0.1
                          Shifting coefficient Cshift                                      –                            2
                        Density of solid grain ρS0                                 kg/m3                        2690
                        Density of liquid ρL0                                     kg/m3                        1000
                         Porosity ϕ                                                  –                                0.46
                        Saturated hydraulic conductivity Ksat                        m/s                            1E-04
                        Liquid bulk modulus KL                                   Pa                           2.00E+06
                  Maximum degree of saturation Smax                            –                                 1.0
                        Residual degree of saturation Smin                             –                                 0.1
                 SWCC constant av                                            –                                1e-5
                      Young’s modulus E                                MPa                         15
                         Poisson’s ratio ν                                             –                                 0.3
                          Friction angle φ                                                                 ◦                            32
                      Peak cohesion cp                                         kPa                          7
                        Residual cohesion cr                                      kPa                          0
                         Softening coefficient ηc                                       –                            8
                        Suction hardening coefficient As                                            ◦                            0
                        Suction hardening coefficient Bs                               –                            50
                       Suction-dependant cohesion cs0                             Pa                           500

                                                                29

### Page 30

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

Fig. 30. Pore pressure contour (left column) with the phreatic line (dots) and accumulated deviatoric plastic strain contour (right column) for the
embankment failure due to rapid drawdown.

              Fig. 31. Pore pressure contour without (left column) and with (right column) the use of density diffusion technique.

free-surface particle motion is observed in submerged cases. However, the causes of the problem may differ from the current appli
cation. As mentioned in Section 3.3.2.2, the issue reported in Bui et al. [9] arises from the dynamic free-surface boundary condition,
where the total stress tends to zero at the free surface. This free-surface boundary condition, combined with the submerged condition
that leads to positive liquid pressure at the free surface, induces negative effective stress and, consequently, unphysical tractions. In
their approach, this issue is solved by changing the pressure gradient approximation in the momentum equation from pressure
summation to pressure difference to alter the dynamic free-surface boundary condition. However, the use of pressure difference in the
approximation of pressure gradient may sacrifice the momentum conservation properties, and its applicability to unsaturated con
dition with negative liquid pressure and positive effective stress at free surface is unclear. In the present method, the pressure sum
mation formulation is retained in the momentum equation to ensure momentum conservation. The submerged boundary condition is
explicitly enforced to mitigate the aforementioned issues.

6. Conclusions

   This paper presents a new general fully-coupled SPH framework for the flow-deformation problems in porous material. An
improved SPH formulation for hydro-mechanical coupling is developed, along with novel boundary treatments to implement various

                                                                30

### Page 31

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

       Fig. 32. Pore pressure contour (a) with the use of artificial viscosity αμ = 0.1; (b) with the use of viscous damping term αd = 0.1.

hydro-mechanical boundary conditions in SPH. The stabilisation technique that combines the use of the density diffusion term, a
modified particle shifting algorithm, and a new viscous damping term is also proposed, for an enhanced accuracy, stability, and
robustness of the numerical solution.
   The proposed method is validated through a series of benchmark tests, showing reasonable agreements with analytical, numerical
solutions, and experimental data, and is successfully applied to study the embankment instability due to rapid drawdown. It is shown
that the new SPH formulation for saturated/unsaturated porous material allows an accurate prediction of the seepage flow and fa
cilitates the implementation of hydraulic boundary conditions. The newly introduced hydro-mechanical boundary conditions enable a
comprehensive description of the common scenarios encountered in practice. Additionally, the proposed stabilisation technique en
hances the accuracy and stability of the numerical framework. Overall, the results indicate an enhanced predictive capacity of the
proposed method that allows the analysis of the porous structure behaviour under complex scenarios, from failure initiation to postfailure large deformations.
   In addition, it is worth noting that the proposed method adopts a conventional elastic-plastic model for the mechanical behaviour of
porous material. To enhance predictive capacity of the model, a more sophisticated constitutive model should be incorporated to
capture other features relevant to unsaturated porous materials, such as the wetting-induced volume change or collapse. Moreover, the
current analysis is limited to considering isotropic permeability, which may not accurately represent fluid flow patterns and distri
bution in real-world systems as many natural materials exhibit anisotropic permeability. Therefore, further investigations are needed
to incorporate anisotropic permeability into the analysis. Furthermore, the proposed model neglects the mass and momentum
contribution from air phase. Although this simplification saves the computational costs and facilitates implementation, it may limit the
model’s applicability in cases where variations in air pressure play an important role. Future extensions of the proposed model could
consider incorporating the air phase to provide a complete representation of phase interactions within the porous materials.

Declaration of Competing Interest

   The authors declare that they have no known competing financial interests or personal relationships that could have appeared to
influence the work reported in this paper.

Data availability

   Data will be made available on request.

Acknowledgements

   The first author would like to acknowledge the financial support provided by the China Scholarship Council. The authors would like
to acknowledge the use of the Computational Shared Facility at The University of Manchester. The authors would also like to thank the
reviewers of this paper for their constructive feedback, and the first author would like to express gratitude for the valuable discussion
with Professor Ha Bui from Monash University.

                                                                31

### Page 32

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

APPENDIX A. Effective stress update

   For the elastic-plastic material, the total strain increment, denoted as dε, can be divided into two components: the elastic strain
increment, dεe, and the plastic strain increment, dεp. The computation of the effective stress increment, dσ’, follows the Hooke’s law
and is given by
        dσ′ = De : (dε −dεp)                                                                                          (A1)
where De is the elastic stiffness matrix. The plastic strain increment dεp is computed according to the plastic flow rule,

              ∂g
       dεp = dλ                                                                                                    (A2)              ∂σ
in which is dλ the plastic multiplier that governs the magnitude of the plastic strain increment, and g is the plastic potential function
that determines the direction of the plastic strain increment.
   To predict the effective stress at the next step, i.e., σ′t+δt, this work employs a semi-implicit approach, consisting of an elastic
predictor step and a plastic corrector step. In the elastic predictor step, a trial solution based on the elastic assumption is computed
using the following equation,
          σ′t+δttrial = σ′t + De : dε                                                                                           (A3)

     If the trial solution violates the yield criteria f (σ) ≥0, then the plastic corrector is required to return the trial stress back to the yield
surface, satisfying the condition f (σ) = 0,
          σ′t+δt = σ′t+δttrial −dσ′ p                                                                                            (A4)

where the plastic corrected stress is computed as,

                  ∂g
        dσ′ p = dλDe :                                                                                                 (A5)                  ∂σ

   In this treatment, the predicted stress is iteratively adjusted to return it to the yield surface. The following relationship is established
during each iteration in the plastic corrector,
         σ′(k+1) −σ′(k) = −δσ′(k)p = −δλ(k)De : ∂g                                                                           (A6)                                                  ∂σ(k)
where k is the iteration number.
   At each iteration of the plastic corrector, the yield function at the corrected stress state is linearised around the current stress state.
Since the pressure is evaluated using Eq. (13) and no iteration is required for its solution, the suction pressure remains constant in the
plastic corrector step. The following relationship is then established,
              (              )       (          )     ∂f      (                  ∂f (                  ∂f           f  σ′(k+1), κ(k+1), pc ≈f  σ′(k), κ(k), pc +         :  σ′(k+1) −σ′(k)) +     κ(k+1) −κ(k)) +    (pc −pc)                              (A7)
                                                           ∂σ′(k)                 ∂κ                ∂pc

   To satisfy the yield condition for the corrected stress state f(σ′(k+1), κ(k+1), pc) = 0, and according to Eq. (A6), Eq. (A7) can be
rewritten as
              (          )     ∂f             ∂f
           f  σ′(k), κ(k), pc   −           : δσ′(k)p +    δκ(k) = 0                                                                        (A8)
                                ∂σ′(k)         ∂κ

   Substitute Eq. (A6) into Eq. (A8) and rearranging the obtained equation, the plastic multiplier for the iteration is computed as,

                                                                     f (k)
         δλ(k) =           /       √ ̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅                                               (A9)
                (∂f/∂σ′(k))T : De : ∂g   ∂σ′(k) + (∂f/∂κ(k))  (2/3)∂g/∂σ′(k) : ∂g/∂σ′(k)

   In Table A1, the iterative algorithm for the effective stress updating is provided. It is noted that the algorithm receives the strain
increment dε, spin increment dω, current plastic strain εtp, current internal variable κt, and current effective stress σ′t, and the suction
pressure at next time step pt+δtc   as input, while outputs updated effective stress, updated plastic strain as well as updated internal
variable for next time step.

                                                                32

### Page 33

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

                       Table A1
                            Effective stress updating algorithm.
                                 Input ˙ε, ˙ω, εtp, κt, σ′t, pt+δtc
                                  1. Variables initialisation
                                  Iteration number: k = 0, Strain increment: dε = ˙εdt, Spin increment: dω = ˙ωdt, Stress: σ′(0) = σ′t,
                                       Plastic strain: ε(0)p = εtp, Internal variable: κ(0) = κt
                                  2. Elastic predictor
                                            σ′(1) = σ′(0) + De : dε − dω ⋅σ′(0) + σ′(0) ⋅dω, κ(1) = κ(0),ε(1)p = ε(0)p  , k = k + 1
                                             if f(σ′(1),κ(1),pt+δtc   ) ≤0, elastic
                             go to Output
                                     else, go to Step 3 plastic corrector
                                  3. Plastic corrector
                             while f(σ′(k), κ(k), pt+δtc   ) > εTOL & k < kmax do
                                   (1) Compute plastic multiplier
                                                                                                  f(k)  √ ̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅                                          δλ(k) =
                                                (∂f/∂σ′(k))T : De : ∂g/∂σ′(k) + (∂f/∂κ(k))  (2/3)∂g/∂σ′(k) : ∂g/∂σ′(k)
                                   (2) Compute sub-increments in the iteration   √̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅
                                                                                                             δe(k)p   : δe(k)p                                                                      δε(k)p = [De]−1δσ′(k)p  , δκ(k) =  2                                             δσ′(k)p = δλ(k)De : ∂σ(k),∂g                                                                    3
                                   (3) Update stress, plastic strain, and internal variables
                                           σ′(k+1) = σ′(k) −  δσ′(k)p  , ε(k+1)p   = ε(k)p + δε(k)p  , κ(k+1) = κ(k) + δκ(k)
                              k = k + 1
                          end
                              Output σ′t+δt = σ′(k), εt+δtp  = ε(k)p  , κt+δt = κ(k)

APPENDIX B. Momentum Conservation

   As a new dissipation term is included in the momentum equations, it is necessary to check whether this term might affect the global
conservation of momentum. The discrete form of the globally conservative principles for an artificial quantity is written as,
  ∑
        Παi = 0                                                                                                      (B1)
                    i

In this study, the artificial quantity Παi  is the damping term that is expressed as,
    ∑      ∂Wij      Παi =    mjΨαβij                                                                                                   (B2)
                                  j        ∂xβi

where Ψαβij  is given by

              αdcs0h      Ψαβij =       dαβij                                                                                                   (B3)                       ρij
   Substituting Eq. (B2) into Eq. (B1), the conservative principle is rewritten as,
  ∑∑      ∂Wij            mjΨαβij   = 0                                                                                             (B4)
                    i       j        ∂xβi
   Since the mass mj is a constant for all the particles, the damping term παβij  is symmetric, that is Ψαβij = Ψαβji , while the kernel gradient is
antisymmetric ∂Wij/∂xβi = ∂Wij/∂xβj , the total sum of Παi for all the particle, which are interacting as pairs, vanish, and the condition in
Eq. (B1) is satisfied.

References

 [1] M. Foster, R. Fell, M. Spannagle, The statistics of embankment dam failures and accidents, Can. Geotech. J. 37 (5) (2000) 1000–1024.
 [2] O. Korup, Recent research on landslide dams-a literature review with special attention to New Zealand, Prog. Phys. Geogr. 26 (2) (2002) 206–235.
 [3] Galavi, V. 2010. Groundwater flow, fully coupled flow deformation and undrained analyses in PLAXIS 2D and 3D. Plaxis Report.
 [4] Krahn, J. 2012. Seepage Modeling With SEEP/W: An engineering Methodology. GEO-SLOPE International Ltd. Calgary, Alberta, Canada.
 [5] D.M. Potts, L. Zdravkovi´c, T.I. Addenbrooke, K.G. Higgins, et al., Finite Element Analysis in Geotechnical engineering: Application, Thomas Telford, London,
     2001.

                                                                33

### Page 34

R. Feng et al.                                                                     Computer Methods in Applied Mechanics and Engineering 419 (2024) 116581

 [6] K. Maeda, H. Sakai, M. Sakai, Development of seepage failure analysis method of ground with smoothed particle hydrodynamics, Struct. Engineer./Earthquake
      Engineer. 23 (2) (2006) 307s–319s.
 [7] A. Khayyer, H. Gotoh, Y. Shimizu, Comparative study on accuracy and conservation properties of two particle regularization schemes and proposal of an
     optimized particle shifting scheme in ISPH context, J. Comput. Phys. 332 (2017) 236–256.
 [8] W. Zhang, K. Maeda, H. Saito, Z. Li, et al., Numerical analysis on seepage failures of dike due to water level-up and rainfall using a water-soil-coupled smoothed
      particle hydrodynamics model, Acta Geotech. 11 (6) (2016) 1401–1418.
 [9] H.H. Bui, R. Fukagawa, K. Sako, J.C. Wells, Slope stability analysis and discontinuous slope failure simulation by elasto-plastic smoothed particle
     hydrodynamics (SPH), G´eotechnique 61 (7) (2011) 565–574.
[10] M. Pastor, B. Haddad, G. Sorbino, S. Cuomo, et al., A depth-integrated, coupled SPH model for flow-like landslides and related phenomena, Int. J. Numer. Anal.
     Methods Geomech. 33 (2) (2009) 143–172.
[11] T. Blanc, M. Pastor, A stabilized fractional step, Runge-Kutta Taylor SPH algorithm for coupled problems in geomechanics, Comput. Methods Appl. Mech. Eng.
     221 (2012) 41–53.
[12] D.S. Morikawa, M. Asai, Soil-water strong coupled ISPH based on u-w-p formulation for large deformation problems, Comput. Geotech. 142 (2022), 104570.
[13] R. Feng, G. Fourtakas, B.D. Rogers, D. Lombardi, Two-phase fully-coupled smoothed particle hydrodynamics (SPH) model for unsaturated soils and its
      application to rainfall-induced slope collapse, Comput. Geotech. 151 (2022), 104964.
[14] Y. Lian, H.H. Bui, G.D. Nguyen, S. Zhao, et al., A computationally efficient SPH framework for unsaturated soils and its application to predicting the entire
      rainfall-induced slope failure process, Geotechnique (2022) 1–19.
[15] G. Ma, H.H. Bui, Y. Lian, K.M. Tran, et al., A five-phase approach, SPH framework and applications for predictions of seepage-induced internal erosion and
      failure in unsaturated/saturated porous media, Comput. Methods Appl. Mech. Eng. 401 (2022), 115614.
[16] R. Vacondio, C. Altomare, M. De Leffe, X. Hu, et al., Grand challenges for smoothed particle hydrodynamics numerical schemes, Comput. Part. Mech. 8 (2021)
     575–588.
[17] Y. Lian, H.H. Bui, G.D. Nguyen, H.T. Tran, et al., A general SPH framework for transient seepage flows through unsaturated porous media considering
      anisotropic diffusion, Comput. Methods Appl. Mech. Eng. 387 (2021), 114169.
[18] X. Xu, J. Ouyang, B. Yang, Z. Liu, SPH simulations of three-dimensional non-newtonian free surface flows, Comput. Methods Appl. Mech. Eng. 256 (2013)
     101–116.
[19] H.H. Bui, G.D. Nguyen, Smoothed particle hydrodynamics (SPH) and its applications in geomechanics: from solid fracture to granular behaviour and multiphase
      flows in porous media, Comput. Geotech. 138 (2021), 104315.
[20] C.T. Nguyen, C.T. Nguyen, H.H. Bui, G.D. Nguyen, et al., A new SPH-based approach to simulation of granular flows using viscous damping and stress
      regularisation, Landslides 14 (1) (2017) 69–81.
[21] R.J. Atkin, R. Craine, Continuum theories of mixtures: basic theory and historical development, Quarterly J. Mech. Appl. Math. 29 (2) (1976) 209–244.
[22] A. Yerro, E.E. Alonso, N.M. Pinyol, The material point method for unsaturated soils, G´eotechnique 65 (3) (2015) 201–217.
[23]  J. Bonet, T.-S. Lok, Variational and momentum preservation aspects of smooth particle hydrodynamic formulations, Comput. Methods. Appl. Mech. Eng. 180
     (1–2) (1999) 97–115.
[24]  J. Chen, J. Beraun, A generalized smoothed particle hydrodynamics method for nonlinear dynamic problems, Comput. Methods Appl. Mech. Eng. 190 (1–2)
     (2000) 225–239.
[25] M. Liu, G.-R. Liu, Restoring particle consistency in smoothed particle hydrodynamics, Appl. numerical math. 56 (1) (2006) 19–36.
[26]  J.J. Monaghan, Smoothed particle hydrodynamics, Annu. Rev. Astron. Astrophys. 30 (1) (1992) 543–574.
[27] C. Zhang, Y. Zhu, Y. Yu, D. Wu, et al., An artificial damping method for total lagrangian SPH method with application in biomechanics, Eng. Anal. Bound. Elem.
     143 (2022) 1–13.
[28] M. Antuono, A. Colagrossi, S. Marrone, D. Molteni, Free-surface flows solved by means of SPH schemes with numerical diffusive terms, Comput. Phys. Commun.
     181 (3) (2010) 532–549.
[29] R.M. Nestor, M. Basa, M. Lastiwka, N.J. Quinlan, Extension of the finite volume particle method to viscous flow, J. Comput. Phys. 228 (5) (2009) 1733–1749.
[30] R. Xu, P. Stansby, D. Laurence, Accuracy and stability in incompressible SPH (ISPH) based on the projection method and a new approach, J. Comput. Phys. 228
      (18) (2009) 6703–6725.
[31]  S.J. Lind, R. Xu, P.K. Stansby, B.D. Rogers, Incompressible smoothed particle hydrodynamics for free-surface flows: a generalised diffusion-based algorithm for
       stability and validations for impulsive flows and propagating waves, J. Comput. Phys. 231 (4) (2012) 1499–1523.
[32] M.S. Shadloo, A. Zainali, M. Yildiz, A. Suleman, A robust weakly compressible SPH method and its comparison with an incompressible SPH, Int. J. Numer.
     Methods Eng. 89 (8) (2012) 939–956.
[33] X. Xu, P. Yu, A technique to remove the tensile instability in weakly compressible SPH, Comput. Mech. 62 (2018) 963–990.
[34] A. Skillen, S. Lind, P.K. Stansby, B.D. Rogers, Incompressible smoothed particle hydrodynamics (SPH) with reduced temporal noise and generalised Fickian
     smoothing applied to body-water slam and efficient wave-body interaction, Comput. Methods Appl. Mech. Eng. 265 (2013) 163–173.
[35] A. Mokos, B.D. Rogers, P.K. Stansby, A multi-phase particle shifting algorithm for SPH simulations of violent hydrodynamics with a large number of particles,
       J. Hydraulic Res. 55 (2) (2017) 143–162.
[36]  F. Ceccato, A. Yerro, V. Girardi, P. Simonini, Two-phase dynamic MPM formulation for unsaturated soil, Comput. Geotech. 129 (2021), 103876.
[37] A. English, J.M. Domínguez, R. Vacondio, A. Crespo, et al., Modified dynamic boundary conditions (mDBC) for general-purpose smoothed particle
     hydrodynamics (SPH): application to tank sloshing, dam break and fish pass problems. Comput. Part. Mech., 2021, pp. 1–15.
[38] R. Feng, G. Fourtakas, B.D. Rogers, D. Lombardi, Large deformation analysis of granular materials with stabilized and noise-free stress treatment in smoothed
      particle hydrodynamics (SPH), Comput. Geotech. 138 (2021), 104356.
[39]  S. Marrone, A. Colagrossi, D. Le Touz´e, G. Graziani, Fast free-surface detection and level-set function definition in SPH solvers, J. Comput. Phys. 229 (10) (2010)
     3652–3663.
[40] A. Vergnaud, G. Oger, D. Le Touz´e, M. Deleffe, et al., C-CSF: accurate, robust and efficient surface tension and contact angle models for single-phase flows using
     SPH, Comput. Methods Appl. Mech. Eng. 389 (2022), 114292.
[41] J.M. Domínguez, G. Fourtakas, C. Altomare, R.B. Canelas, et al., DualSPHysics: from fluid dynamics to multiphysics problems, Comput. Part. Mech. 9 (5) (2022)
     867–895.
[42] H.H. Bui, R. Fukagawa, An improved SPH method for saturated soils and its application to investigate the mechanisms of embankment failure: case of
      hydrostatic pore-water pressure, Int. J. Numer. Anal. Methods Geomech. 37 (1) (2013) 31–50.
[43] A. Colagrossi, M. Antuono, D. Le Touz´e, Theoretical considerations on the free-surface role in the smoothed-particle-hydrodynamics model, Phys. Rev. E . 79 (5)
     (2009) 056701.
[44] N.J. Quinlan, M. Basa, M. Lastiwka, Truncation error in mesh-free particle methods, Int. J. Numer. Methods Eng. 66 (13) (2006) 2064–2085.
[45] D.M. Pedroso, A solution to transient seepage in unsaturated porous media, Comput. Methods Appl. Mech. Eng. 285 (2015) 791–816.
[46] H. Moriwaki, T. Inokuchi, T. Hattanji, K. Sassa, et al., Failure processes in a full-scale landslide experiment using a rainfall simulator, Landslides 1 (4) (2004)
     277–288.
[47] T.S. Nguyen, K.-H. Yang, C.-C. Ho, F.-C. Huang, Postfailure characterization of shallow landslides using the material point method, Geofluids 2021 (2021).
[48] K.-H. Yang, T.S. Nguyen, H. Rahardjo, D.-G. Lin, Deformation characteristics of unstable shallow slopes triggered by rainfall infiltration, Bull. Eng. Geol.
      Environ. 80 (1) (2021) 317–344.
[49] Lee, W., Martinelli, M. & Shieh, C. 2021. An investigation of rainfall-induced landslides from the pre-failure stage to the post-failure stage using the material
      point method. Front. Earth Sci, 9, 764393.

                                                                34

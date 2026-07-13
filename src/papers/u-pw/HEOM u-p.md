# Modeling large-deformation dynamic behavior of saturated soils using the Hybrid Element Particle Method (HEPM)

> Auto-converted from PDF for Codex/code-reference reading. Formatting, equations, figures, and tables may require checking against the original PDF.

- Source PDF: `HEOM u-p.pdf`
- Pages: 19
- PDF metadata author: Yuanyi Qiu

## Extracted Text

### Page 1

Computers and Geotechnics 199 (2026) 108390

                                                 Contents lists available at ScienceDirect

                        Computers and Geotechnics

                                         journal homepage: www.elsevier.com/locate/compgeo

Research paper

Modeling large-deformation dynamic behavior of saturated soils using the
Hybrid Element Particle Method (HEPM)
Yuanyi Qiu b,c, Huangcheng Fang a,∗, Zhen-Yu Yin b,c,∗, Yuqiong Li d,e

a Key Laboratory for Urban Underground Engineering of Ministry of Education, Beijing Jiaotong University, Beijing, China
b Department of Civil and Environmental Engineering, The Hong Kong Polytechnic University, Hung Hom, Kowloon, Hong Kong, China
c State Key Laboratory of Climate Resilience for Coastal Cities, The Hong Kong Polytechnic University, Hong Kong, China
d Key Laboratory for Mechanics in Fluid Solid Coupling Systems, Institute of Mechanics, Chinese Academy of Sciences, Beijing 100190, China
e State Key Laboratory of Nonlinear Mechanics, Institute of Mechanics, Chinese Academy of Sciences, Beijing 100190, China

A R T I C L E   I N F O            A B S T R A C T

Keywords:                                     Modeling the dynamic behavior of saturated porous media is crucial for predicting geotechnical hazards.
Dynamic consolidation                          However, simulating coupled hydro-mechanical processes involving large deformations and extensive plastic
Hydro-mechanical coupling                         flow remains challenging, as traditional grid-based methods suffer from severe mesh distortion that hinders
Hybrid Element Particle Method                      accurate post-failure analysis. To address these issues, this study extends the Hybrid Element Particle Method
Geotechnical large deformation
                                       (HEPM) to dynamic coupled problems in saturated porous media. The proposed framework utilizes the
                                                           flexibility of Lagrangian particles to track material history and plastic deformation, and employs an auxiliary
                                        mesh to solve the coupled momentum and mass balance equations based on a stabilized Biot’s dynamic
                                𝑢−𝑝 formulation. This dual-discretization strategy effectively overcomes the mesh distortion issues inherent
                                                     in conventional methods, enabling robust simulation of the entire process from  initial loading to post-
                                                        failure evolution. The accuracy of the algorithm is validated through dynamic benchmarks, including wave
                                               propagation and dynamic consolidation  tests, showing excellent agreement with analytical solutions and
                                                       effective suppression of spurious pressure oscillations. Finally, the practical applicability of the proposed
                                 HEPM is demonstrated through simulations of seepage-induced embankment collapse and progressive landslide
                                                          failure. The results highlight the method’s robustness in predicting the entire transition from localized
                                              deformation to extensive failure under coupled hydro-mechanical conditions, providing a powerful tool for
                                                 the analysis of dynamic geohazards.

1. Introduction                                                 must simultaneously resolve the high-frequency dynamic waves and
                                                                           track extreme material deformations, a requirement that often exceeds
   Modeling the dynamic response of saturated porous media is a fun-     the capabilities of traditional grid-based methods due to severe mesh
damental challenge in geotechnical engineering, crucial for assessing     distortion.
the stability of infrastructure against catastrophic failures. Unlike quasi-       The Finite Element Method (FEM), particularly within the 𝑢−𝑝
static deformations, real-world geohazards, such as seepage-induced    framework, is widely regarded as the standard approach for modeling
embankment collapses and progressive landslides, are characterized by     the coupled hydro-mechanical response of saturated soils (Li et al.,
rapid post-failure flow and extreme geometric nonlinearities. Conse-                                                                   2003; Han et al., 2015). Ideally suited for small-strain analysis, this
quently, a rigorous analysis of these dynamic consolidation processes                                                            method offers a rigorous mathematical basis and effectively handles
is essential to accurately predict the failure mechanisms and the post-
                                                                complex boundary conditions (Soares, 2008; Sabetamal, 2015). Howfailure run-out behavior of saturated soils. In these dynamic scenarios,
                                                                             ever, the traditional Lagrangian FEM encounters significant difficulties
the behavior of the soil is governed by the interplay of inertial forces,
                                                        when applied to large-deformation problems. In dynamic geohazards
wave propagation, and transient pore pressure evolution, a coupled
                                                                   such as landslides (Li et  al., 2020; Wen et  al., 2024), the soil unprocess collectively known as dynamic consolidation. Neglecting these
                                                                     dergoes extreme geometric changes. This often leads to severe mesh
dynamic effects can lead to severe underestimation of the geohazard’s
                                                                                 distortion, which degrades numerical accuracy and frequently causesrun-out distance and impact force. However, numerically simulating
                                                                   convergence failure. While the Arbitrary Lagrangian-Eulerian (ALE)these coupled processes presents a significant difficulty. The analysis

  ∗Corresponding authors.
     E-mail addresses:  valy_f@bjtu.edu.cn (H. Fang), zhenyu.yin@polyu.edu.hk (Z.-Y. Yin).

https://doi.org/10.1016/j.compgeo.2026.108390
Received 24 March 2026; Received in revised form 23 June 2026; Accepted 23 June 2026
Available online 2 July 2026
0266-352X/© 2026 Elsevier Ltd. All rights are reserved, including those for text and data mining, AI training, and similar technologies.

### Page 2

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

method attempts to mitigate these issues by decoupling the mesh       The mathematical models governing the hydro-mechanical coumotion from the material motion, it introduces its own set of chal-     pled dynamics of porous media are established upon Biot’s theory
lenges. The complex treatment of convective terms and the frequent      (Biot, 1962). To accurately characterize the interaction between the
data mapping required between meshes often induce excessive nu-     solid skeleton and pore fluids, fully coupled approaches – such as
merical dissipation (Gadala and Wang, 1998; Liu et  al., 2021). To     the 𝑢-𝑣 (Ceccato et  al., 2021) or 𝑢-𝑤-𝑝 (Morikawa and Asai, 2022;
overcome the limitations of grid-based methods in handling large defor-    Feng et  al., 2024b) formulations – have been proposed to account
mations, various meshfree and particle-based techniques have emerged.     for the complete inertial effects of both phases. Although theoretAs a representative of fully meshfree Lagrangian approaches, Smoothed      ically rigorous, these formulations incur high computational costs,
Particle Hydrodynamics (SPH) has been widely adopted in computa-     particularly in three-dimensional analyses where resolving additional
tional geomechanics for simulating slope failure (Morikawa and Asai,                                                                                  fluid kinematic variables substantially increases the degrees of free-
2022), fault rupturing (del Castillo et al., 2024), earthquake-induced                                                    dom per node. To balance computational efficiency with the accuracy
failure (Hoang et al., 2024), and soil arching (Zhang et al., 2026).                                                                        required for geotechnical applications, this study adopts the 𝑢-𝑝 formuHowever, the standard SPH formulation is often compromised by in-
                                                                               lation (Zienkiewicz et al., 1999). By neglecting the relative acceleration
herent tensile instability (Bui and Nguyen, 2017), boundary deficiency
                                                                              of the pore fluid with respect to the solid skeleton, this approxi-
(Afrasiabi et al., 2019), and the reliance on additional techniques for
                                                                 mation simplifies the governing equations and reduces the size of
the imposition of boundary conditions (Hoang et  al., 2024). Alter-
                                                                        the global system. Despite this simplification, the 𝑢-𝑝 formulation has
natively, the Particle Finite Element Method (PFEM) was introduced
                                                                   demonstrated robustness and accuracy in handling low- to mediumto combine the rigorous boundary treatment of FEM with the flexi-
                                                                     frequency dynamic problems, such as earthquake engineering, ocean
bility of particle methods. By integrating Lagrangian particle motion
                                                          wave loading, and complex soil–structure interactions (Wang et al.,
with continuous remeshing based on Delaunay tessellation, PFEM ef-
                                                                   2021, 2023; Zhang et al., 2025). Moreover, when coupled with implicitfectively captures evolving free surfaces (Idelsohn et al., 2004). To
                                                                    time integration, it offers a highly stable and efficient framework forextend its applicability to saturated porous media, mixed stabilized
                                                                               practical large-deformation analysis. However, the use of equal-orderformulations and strain smoothing techniques (e.g., NS-PFEM) have
been developed to alleviate volumetric locking and enhance stress in-     linear interpolation for both displacement and pressure fields violates
tegration accuracy (Monforte et al., 2017; Zhang et al., 2018; Jin et al.,     the LBB condition, which can induce spurious pressure oscillations
2021). Crucially, the framework has been successfully adapted to model     near the undrained incompressible limit (Brezzi and Bathe, 1990).
the dynamic response of fully coupled hydro-mechanical systems, en-    To overcome this, the Finite Increment Calculus (FIC) stabilization
abling the rigorous simulation of multiphase geohazards such as rapid     technique is employed (Oñate, 1998; Oñate et al., 2014). By incorpolandslides (Sun et al., 2021; Wang et al., 2023, 2024, 2025). Neverthe-     rating stabilization terms derived directly from the balance equations,
less, in three-dimensional scenarios, the standard Delaunay tessellation     the FIC method ensures numerical stability while maintaining the
struggles to guarantee element quality and inevitably generates degen-     computational efficiency of linear elements.
erate sliver elements, introducing additional computational overhead        This paper extends the HEPM for fully implicit, coupled hydrofor mesh optimization and compromising the stability of the numer-    mechanical dynamic analyses. By integrating a 𝑢-𝑝 formulation, the
ical solver (Lacroix et al., 2026). Another powerful alternative is the    method captures coupling mechanics while inherently overcoming
material point method (MPM), which utilizes a dual mesh-particle    mesh distortion, ensuring robust simulations of large-deformation conframework to simulate dynamic large deformations in saturated soils     solidation. Furthermore, the linearized governing equations are derived
(Bandara and Soga, 2015; Zhao and Choo, 2020; Yu et al., 2024; Li    by incorporating the FIC stabilization technique to effectively suppress
et al., 2026). This method employs a fixed Eulerian background grid                                                                    pore pressure instabilities. The accuracy and robustness of the proposed
and moving Lagrangian material points, effectively decoupling them to                                                               framework are rigorously validated through a series of benchmark
overcome mesh distortion issues. Each step involves mapping variables                                                                      problems, including one-dimensional (1D) dynamic consolidation unto the grid to solve the equations of motion, followed by a reverse
                                                                      der both compressible and incompressible limits, wave propagation in
mapping to update particle kinematics. However, this dual-framework
                                                                  a two-dimensional (2D) porous foundation, and a comparative study
feature introduces several inherent drawbacks, including cell-crossing
                                                                    with SPH in a three-dimensional (3D) triaxial shear test. Finally, the
errors (Nguyen et  al., 2023) and difficulties in precisely imposing
                                                                             capability of the method to handle complex geomechanical failures is
boundary conditions (Zheng et al., 2024).
                                                                   demonstrated through practical simulations of seepage-induced slope
   Recently, the Hybrid Element Particle Method (HEPM) (Fang and
                                                                                    instability and the progressive failure mechanism of soft soil landslides.
Yin, 2025b; Qiu et  al., 2026) has emerged as a promising alternative that mitigates several inherent challenges associated with both
MPM and PFEM. This method adopts a hybrid discretization scheme:     2. Governing equations and methodology
Lagrangian particles store all history-dependent variables, while an
auxiliary mesh is employed to construct interpolation functions for
                                                                           This section details a dynamic hydro-mechanical coupling algorithm
particles. Compared to PFEM, the remeshing procedure in HEPM does
                                                                   based on the Hybrid Element Particle Method (HEPM) within the
not require preserving the original node set. It solely relies on the exter-
                                                               framework of Biot’s theory (Biot, 1962), aiming to resolve geotechnicalnal geometric boundaries, which inherently prevents the generation of
                                                                        large-deformation problems while inherently avoiding mesh distortiondegenerate elements and ensures consistently high mesh quality. Fur-
                                                                                   issues. To capture geometric nonlinearities during dynamic processes,thermore, unlike standard MPM, the dynamically generated auxiliary
mesh in HEPM inherits the advantages of an updated Lagrangian FEM    an updated Lagrangian formulation is adopted, where the governing
framework. This enables the exact enforcement of boundary conditions     equations, including inertial terms, are established based on the current
without diffuse approximations, while simultaneously avoiding the cell-     configuration at each time step. In addition, the particle interpolation
crossing noise and quadrature errors caused by unfavorable integration    and gradient reconstruction strategies are presented, which enable the
point locations in MPM (Nguyen et al., 2023). Consequently, owing     establishment of discrete system equations directly at the particle level
to the complete decoupling of the auxiliary mesh from the material     to solve the dynamic coupled 𝑢-𝑝 system. Crucially, a particle-level
history, the spatial discretization can be regenerated at any given time     Finite Increment Calculus (FIC) scheme is incorporated, enabling the
step, thereby enabling the rigorous simulation of post-failure large     use of equal low-order discretization for both the displacement and
deformations involving extensive plastic flow.                           pore pressure fields.

                                                                        2

### Page 3

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

2.1. Dynamic governing equations for saturated porous media                To evaluate these spatial integrals based on the known reference
                                                                          configuration 𝛺𝑡, a geometric transformation is employed. This map-
   The mechanical response of a saturated porous medium is governed     ping  is governed by the deformation gradient 𝐅=  𝜕𝐱∕𝜕𝐱𝑡 and  its
by the hydro-mechanical coupling between the solid skeleton deforma-     Jacobian determinant 𝐽, which relates the differential volume elements
tion and pore fluid flow. While sufficient for long-term consolidation,     via 𝑑𝛺= 𝐽𝑑𝛺𝑡. By mapping both the internal virtual work and the
quasi-static frameworks are inadequate for high-frequency phenom-      inertial contributions from the current unknown configuration to the
ena, such as wave propagation and rapid landslides, where inertial     previous reference state, the total virtual work is expressed as:
effects are significant. To explicitly capture the acceleration of the solid                                                                                       [(∇𝑡𝛿𝐮) ⋅𝐅−1] ∶(𝐽𝝈𝑡+𝛥𝑡) 𝑑𝛺                              (7)skeleton, a dynamic 𝑢−𝑝 formulation based on Biot’s poroelasticity     𝛿𝛱int =                                                                                ∫𝛺𝑡
theory  is adopted. Within the updated Lagrangian framework, the
linear momentum balance is expressed as:                                      𝛿𝛱inertia = ∫𝛺𝑡𝜌𝑡𝛿𝐮⋅𝐚𝑡+𝛥𝑡𝑑𝛺                                        (8)
∇⋅(𝝈′ −𝛼𝑝𝐈) + 𝜌𝐛= 𝜌𝐚                                              (1)     Linearizing this equation with respect to the incremental displacement
                                                                                     field 𝛥𝐮 is essential for constructing the consistent tangent operator. To
Here, 𝝈′ and 𝑝 denote the effective stress tensor of the soil skeleton
                                                                      achieve this, the variations of the Jacobian and the inverse deformation
and the pore water pressure, respectively. Assuming incompressible
                                                                         gradient are formulated in terms of the spatial displacement gradient:
solid grains (i.e., 𝛼= 1), the total Cauchy stress tensor of the mixture is
defined as 𝝈= 𝝈′ −𝑝𝐈. Additionally, 𝜌 represents the mixture density,   𝛥𝐽= 𝐽(∇⋅𝛥𝐮),  𝛥(𝐅−1) = −𝐅−1 ⋅(∇𝛥𝐮)                             (9)
𝐛 is the body force, and 𝐚 denotes the solid skeleton acceleration.
                                                              where the gradient operator ∇ is defined with respect to the current   For the pore fluid phase, the mass balance equation is derived by
                                                                            configuration. Substituting the kinematic relations into the weak form,substituting Darcy’s law into the mass continuity condition, yielding:
           [              ]                                           the linearized incremental internal and inertial work terms are derived𝜕(𝜌𝑓𝑛)         𝐤                                                                 as:     −∇⋅  𝜌𝑓   (∇𝑝−𝜌𝑓𝐠) = 0                                  (2)   𝜕𝑡           𝜇𝑓                                                                                 [
                                                                            𝛥(𝛿𝛱int) =      ∇𝑡+𝛥𝑡𝛿𝐮∶ C ∶∇𝑡+𝛥𝑡𝛥𝐮−𝛥𝑝𝐈+ 𝝈𝑡+𝛥𝑡(∇𝑡+𝛥𝑡⋅𝛥𝐮)
where 𝑛 is the porosity, 𝑝 is the pore pressure, and 𝜌𝑓 and 𝜇𝑓 represent                  ∫𝛺𝑡+𝛥𝑡
the fluid density and dynamic viscosity. The term 𝐤 denotes the intrinsic                            𝑇]                                                                             −𝝈𝑡+𝛥𝑡⋅(∇𝑡+𝛥𝑡𝛥𝐮)  𝑑𝛺                              (10)
permeability tensor, while 𝐠 is the gravitational acceleration vector.
Assuming the pore fluid is weakly compressible, the rate of fluid density
change is linearly related to the pore pressure rate via the fluid bulk                           (𝜌𝑡+𝛥𝑡 )
                                                                                 𝛿𝐮⋅                                                                            𝛥𝐮𝑑𝛺                           (11)                                                                                      𝛥(𝛿𝛱inertia) =modulus 𝐾𝑓:                                                                                                  𝛽𝛥𝑡2                                                                                                    ∫𝛺𝑡+𝛥𝑡
 1 𝜕𝜌𝑓    1 𝜕𝑝                                                 where C denotes the fourth-order material tangent tensor (refer to
     =                                                           (3)
𝜌𝑓  𝜕𝑡   𝐾𝑓 𝜕𝑡                                                  Fang and Yin (2025b) for the detailed formulation) and 𝛽 is the New-
                                                           mark time integration parameter. Assuming deformation-independent
By substituting Eq. (3) into the mass balance equation, the governing
                                                                           external loading, the linearized momentum equation for the Newton–
equation for the coupled flow field is formulated as:
(       )             [                                    Raphson iteration is established as:
 𝛼−𝑛    𝑛   𝜕𝑝            𝐤
     +                        (−∇𝑝+ 𝜌𝑓𝐠)] = 𝑄              (4)                                                                                      𝛥(𝛿𝛱inertia) + 𝛥(𝛿𝛱int) = (𝐫𝑡+𝛥𝑡)                                   (12)   𝐾𝑠        𝐾𝑓  𝜕𝑡+ ∇⋅̇𝐮+ ∇⋅  𝜇𝑓
where 𝑄 denotes the source term and 𝐾𝑠 represents the bulk modulus     Here, 𝐫 represents the dynamic residual vector, quantifying the force
of the solid grains. To rigorously capture geometric non-linearities    imbalance at the current configuration:
within the updated Lagrangian framework, the volumetric strain rate
                                                                                         (𝐫𝑡+𝛥𝑡) =     𝜌𝛿𝐮⋅𝐛𝑑𝛺+                      ∇𝑡+𝛥𝑡𝛿𝐮∶𝝈𝑡+𝛥𝑡𝑑𝛺is evaluated as ∇⋅̇𝐮= ̇𝐽∕𝐽. Here, 𝐽 is the Jacobian determinant. Addi-                ∫𝛺𝑡+𝛥𝑡               ∫𝛤𝑡+𝛥𝑡 𝛿𝐮⋅𝐭𝑡+𝛥𝑡𝑑𝛤−∫𝛺𝑡+𝛥𝑡
tionally, a Neumann-type boundary condition is specified to represent
the prescribed fluid flux across the boundary 𝛤𝑓:                                  −∫𝛺𝑡+𝛥𝑡 𝜌𝛿𝐮⋅(𝐚𝑡+𝛥𝑡)𝑑𝛺                                  (13)
   𝐤
𝜌𝑓   (−∇𝑝+ 𝜌𝑓𝐠) ⋅𝐧= 𝑞𝑓  on  𝛤𝑓                                  (5)     Crucially, the stress tensor 𝝈 in the geometric stiffness terms denotes
  𝜇𝑓                                                                        the total Cauchy stress, derived from the effective stress and pore
where 𝐧 denotes the outward unit normal vector to the boundary     pressure, ensuring the accurate capture of hydro-mechanical geometric
surface, and 𝑞𝑓 represents the prescribed fluid mass flux                     non-linearities.

2.2. Weak formulation and linearization of the dynamic system                2.2.2. Mass conservation
                                                                The weak form of the mass balance equation  is established on
   To capture dynamic large deformations, this study adopts an up-     the current configuration. Starting from the governing equation Eq.
dated Lagrangian framework. This section presents the governing equa-      (4), applying the divergence theorem, and utilizing a fully implicit
tions, explicitly accounting for geometric nonlinearities associated with    backward Euler scheme for time integration, the discretized weak form
the evolving configuration.                                                   at time 𝑡+ 𝛥𝑡 is obtained as:
                                                                        𝛿𝑝𝑚(𝑝𝑡+𝛥𝑡−𝑝𝑡)𝑑𝛺 +    𝛿𝑝𝛼𝐽−1 𝑑𝛺
2.2.1. Momentum conservation                                                    ∫𝛺𝑡+𝛥𝑡                       ∫𝛺𝑡+𝛥𝑡     𝐽
                                                                                                                   ⏟⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏟⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏟   ⏟⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏟⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏟   For large-deformation analysis, the principle of virtual work  is
                                                                                                              Compressibility term              Coupling term
applied to the current configuration, yielding the following weak form:
                                                   +       ∇𝑡+𝛥𝑡𝛿𝑝⋅𝐤 (∇𝑝)𝑡+𝛥𝑡𝑑𝛺 =      𝛿𝑝𝑄𝑑𝛺            (14)                                                                                   𝛥𝑡∫𝛺𝑡+𝛥𝑡         𝜇𝑓               𝛥𝑡∫𝛺𝑡+𝛥𝑡
  𝜌𝛿𝐮⋅𝐚𝑑𝛺+  ∇𝛿𝐮∶𝝈𝑑𝛺=   𝛿𝐮⋅𝐭𝑑𝛤+   𝜌𝛿𝐮⋅𝐛𝑑𝛺         (6)                ⏟⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏟⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏞⏟    ⏟⏞⏞⏞⏞⏞⏞⏞⏞⏞⏟⏞⏞⏞⏞⏞⏞⏞⏞⏞⏟
∫𝛺         ∫𝛺            ∫𝛤        ∫𝛺                                                        Permeability term                    Source term

This equation balances the inertial and internal virtual work against the    where 𝑚 is the total compressibility and the boundary flux term and
external work done by boundary tractions 𝐭 and body forces 𝐛. Here,     fluid gravity terms are omitted for brevity. For the Newton–Raphson
𝛿𝐮 denotes the virtual displacement vector.                            scheme, the continuity equation is linearized with respect to 𝛥𝑝 and 𝛥𝐮.

                                                                        3

### Page 4

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

                             Fig. 1. Schematic illustration of the spatial discretization and particle reconstruction scheme in HEPM.

By   neglecting             the                   insignificant                            geometric                                              stiffness                                             terms                                                       associated                                                           with                                                                     Based                                                                     on                                                                                         volume                                                                                                                                    radius                                                                                                                       𝑉𝑘, an effective                                                                                                                                                           𝑟𝑘  is                                                                                     the3√representative3𝑉𝑘Jacobian        and             permeability                             variations,                                     the                                           simplified                                                      linearized                                                      form                                                                                        is     defined                                                                                              as:                                                                                                                         coefficient                                                                                                               computed                                                               𝑟𝑘=                                                                                                                    𝜑𝑝𝑘 is then                                                                                        4𝜋. The smoothing
obtained as:                                                               via a two-step process (Fig. 1). First, for an active Gauss point 𝑘, the
𝛥(𝛿𝛱Mint) = ∫𝛺𝑡+𝛥𝑡𝛿𝑝𝑚𝛥𝑝𝑑𝛺                                                   interaction function 𝜙𝑝𝑘  is evaluated using a cubic spline kernel as
                                                           shown in Fig. 1(a):
𝛥(𝛿𝛱Cint) = ∫𝛺𝑡+𝛥𝑡𝛿𝑝𝛼(∇𝑡+𝛥𝑡⋅𝛥𝐮)𝑑𝛺                               (15)                                                                   (                                                                        )                                                                                                   2                                                         ⎧                                                      −4                                                                                                                                                                                   ,  0 ≤𝑑𝑝𝑘< 0.5                                                                                   𝑑2𝑝𝑘−𝑑3𝑝𝑘                                                                                                   3                                                         ⎪𝛥(𝛿𝛱Hint) = 𝛥𝑡∫𝛺𝑡+𝛥𝑡(∇𝑡+𝛥𝑡𝛿𝑝)𝑇𝐤𝜇𝑓∇𝑡+𝛥𝑡(𝛥𝑝)𝑑𝛺
                                                         ⎪
By assembling these contributions, the final system of equations for the    𝜙𝑝𝑘=                                                         ⎨ 16(2 −2𝑑𝑝𝑘)3,        0.5 ≤𝑑𝑝𝑘< 1                         (19)
updated Lagrangian Newton iteration is obtained:                      ⎪
                                                                                                                  ⎪⎩ 0,             𝑑𝑝𝑘≥1
    𝛿𝑝𝑚𝛥𝑝𝑑𝛺+     𝛿𝑝𝛼∇𝑡+𝛥𝑡⋅𝛥𝐮𝑑𝛺+         (∇𝑡+𝛥𝑡𝛿𝑝)𝑇                                                              where 𝑑𝑝𝑘= ‖𝐱𝑝−𝐱𝑘‖∕(𝜂𝑟𝑘) is the normalized distance, with 𝜂 typically∫𝛺𝑡+𝛥𝑡              ∫𝛺𝑡+𝛥𝑡                    𝛥𝑡∫𝛺𝑡+𝛥𝑡
                                                                                  set to 2. Second, the kernel values are normalized to obtain 𝜑𝑝𝑘=     𝐤
  ×   ∇𝑡+𝛥𝑡(𝛥𝑝)𝑑𝛺= 𝐫𝑡+𝛥𝑡𝑐                                       (16)                 𝑘     𝜇𝑓                                                        𝜙𝑝𝑘∕∑𝑛𝑝𝑗=1 𝜙𝑗𝑘, ensuring the partition of unity condition (∑𝜑𝑝𝑘= 1).
                                                                                                                           Consequently,                                                                                           𝑘 denotes the number of neighboring particles.where the residual force 𝐫𝑡+𝛥𝑡𝑐    is defined as:                              Here, 𝑛𝑝                                                                                                           ∑𝑛𝑔𝑝
              [                           ]                          the lumped particle volume is determined by 𝑉𝑝=   𝑘=1 𝜑𝑝𝑘𝑉𝑘, where
𝐫𝑡+𝛥𝑡𝑐  =        𝛿𝑝⋅𝑄−(∇𝑡+𝛥𝑡𝛿𝑝)𝑇𝐤 ∇𝑡+𝛥𝑡𝑝𝑡+𝛥𝑡 𝑑𝛺                        𝑛𝑔𝑝 represents the number of Gauss points within the particle’s support        𝛥𝑡∫𝛺𝑡+𝛥𝑡                  𝜇𝑓                               domain (Fig. 1(b)).
                 [            ( 𝐽−1 )]
       −∫𝛺𝑡+𝛥𝑡 𝛿𝑝 𝑚(𝑝𝑡+𝛥𝑡−𝑝𝑡) + 𝛼   𝐽   𝑑𝛺                  (17)     2.3.2. Gradient reconstruction
                                                                      Within the finite element framework, the displacement gradient is
2.3. Computational framework of the proposed HEPM
                                                                      obtained via the interpolation of nodal displacements. For a specific
                                                                  Gauss point 𝑘 in element 𝑒, the gradient ∇𝐮(𝐱𝑘) is formulated as:
   This section extends the HEPM framework (Fang and Yin, 2025b) to
                                                                                          𝜕𝐍𝑒 𝜕𝝃
dynamic analysis by introducing a particle-based interpolation scheme.     ∇𝐮(𝐱𝑘) = 𝐋𝑘𝐮𝑒,  with 𝐋𝑘=                                                                    𝝃= 𝝃𝑘                      (20)By reconstructing element shape functions onto particles, the governing                                𝜕𝝃 𝜕𝐱  ||||
equations are discretized in a fully Lagrangian manner, inherently     Here, 𝐋𝑘 denotes the discrete gradient operator evaluated at the 𝑘th
overcoming mesh distortion limitations.                               Gauss point. Specifically, for a linear tetrahedral element, 𝐮𝑒∈R12
                                                                           represents the nodal displacement vector collecting the degrees of
2.3.1. Lagrangian particle discretization                                freedom of all four nodes:
   Spatial discretization assigns a representative volume 𝑉𝑘 to each
Lagrangian particle associated with Gauss points. This volume is de-    𝐮𝑒= [𝑢1𝑥, 𝑢1𝑦, 𝑢1𝑧, … , 𝑢4𝑧]𝑇                                       (21)
fined as the product of the quadrature weight 𝑤𝑘 and the Jacobian    To facilitate matrix operations, the second-order displacement gradient
determinant:                                                                          tensor is vectorized into a 9 × 1 column vector:
                                                                           [                                                                                                         ]𝑇𝑉𝑘= 𝑤𝑘det(𝐉𝑘),  𝑘= 1, 2, … , 𝑛𝑔                                 (18)                                                                                   𝜕𝑢𝑥  𝜕𝑢𝑥  𝜕𝑢𝑥     𝜕𝑢𝑧
                                                                     ∇𝐮(𝐱𝑘) =  𝜕𝑥, 𝜕𝑦, 𝜕𝑧, … , 𝜕𝑧                                 (22)
where 𝐉𝑘 denotes the Jacobian matrix at the 𝑘th Gauss point, computed
from the nodal coordinates 𝐱𝑒 and shape function derivatives, and 𝑛𝑔 is     Correspondingly, the gradient operator matrix 𝐋𝑘  is assembled by
the number of Gauss points per element.                                 concatenating the nodal sub-matrices 𝐋𝑖𝑘∈R9×3 for all element nodes

                                                                        4

### Page 5

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

(𝑖= 1 … 4):                                                                     2.3.4. Discrete system for the coupled dynamic problem
𝐋𝑖𝑘= 𝐈3 ⊗∇𝑁𝑖                                                  (23)         Utilizing particle discretization under the HEPM scheme, the dywhere 𝐈3  is the 3 × 3 identity matrix, and ∇𝑁𝑖=  [𝑁𝑖,𝑥, 𝑁𝑖,𝑦, 𝑁𝑖,𝑧]𝑇     namic momentum balance is reformulated as a particle-based summais the spatial gradient vector of the shape function. Following the
                                                                                   tion. This formulation decouples state variable storage from the mesh,
computation of ∇𝐮(𝐱𝑘), the smoothed gradient at particle 𝑝, denoted
as ̃∇𝐮𝑝, is derived via a weighted average:                           making it ideal for handling large deformations. The discretized and
      ∑𝑛𝑔𝑝                            𝑛𝑔𝑝                                           linearized momentum equation at iteration (𝑖) for time 𝑡+𝛥𝑡 is expressed
         𝑘=1 𝜑𝑝𝑘𝑉𝑘∇𝐮(𝐱𝑘)    1 ∑
̃∇𝐮𝑝=             =      𝜑𝑝𝑘𝑉𝑘𝐋𝑘𝐮𝑒𝑘= ̃𝐋𝑝𝐮𝑝             (24)     as follows (note that the subscript 𝑝 denotes particle quantities but is         ∑𝑛𝑔𝑝              𝑉𝑝 𝑘=1             𝑘=1 𝜑𝑝𝑘𝑉𝑘                                                  suppressed for pore pressure 𝑝 to avoid notation conflict):
where ̃𝐋𝑝 denotes the smoothed gradient operator for particle 𝑝, which
                                                                                            𝑛  𝜌𝑡+𝛥𝑡,[𝑖]𝑝transforms           the surrounding nodal displacements 𝐮𝑒𝑘 into the smoothed  ∑                                                                                                            𝛿𝐮[𝑖]𝑝⋅𝛥𝐮[𝑖]𝑝𝑉[𝑖]𝑝                                                                              𝛽𝛥𝑡2gradient ̃∇𝐮𝑝:                                                                                 𝑝=1
        [                                   ]                                              [                                                               ]                                                           {                           ∑𝑛
                                                  +̃𝐋𝑝= 1                               and 𝐮𝑝=        𝜑𝑝1𝑉1𝐋1 ⋯   𝜑𝑝𝑛𝑔𝑝𝑉𝑛𝑔𝑝𝐋𝑛𝑔𝑝                                                                                                     ̃∇𝑡+𝛥𝑡(𝛿𝐮[𝑖]𝑝) ∶                                                                                                                      C[𝑖] ∶̃∇𝑡+𝛥𝑡(𝛥𝐮[𝑖]𝑝) −𝛼𝛥𝑝[𝑖]𝐈+ ( ̃𝝈𝑡+𝛥𝑡𝑝    )[𝑖]         (30)                                                  𝐮𝑒1 …   𝐮𝑒𝑛𝑔𝑝
     𝑉𝑝                                                                            𝑝=1
                                                               (25)        [                                                     ×  ̃∇𝑡+𝛥𝑡⋅𝛥𝐮[𝑖]𝑝−( ̃∇𝑡+𝛥𝑡𝛥𝐮[𝑖]𝑝)𝑇]} 𝑉[𝑖]𝑝
For the mass balance equation, the volumetric strain rate is evaluated
                                                  = (𝐑𝑡+𝛥𝑡𝑢    )[𝑖]directly as ∇⋅̃𝐮𝑝= ̃𝐁𝑝𝐮𝑝, where the smoothed divergence operator ̃𝐁𝑝
is extracted from the normal components of ̃𝐋𝑝.                                                                    with ̃𝝈𝑝 denoting the total Cauchy stress tensor carried by material
    Similarly, the smoothed pressure  ̃𝑝𝑝 at a particle 𝑝 is derived by
interpolating nodal pressures 𝐩𝑒𝑘 from surrounding elements. This dis-     particle 𝑝 and (𝐑𝑡+𝛥𝑡𝑢    )[𝑖] representing the dynamic imbalance between
cretization allows the system equations to be solved in the particle do-     external, internal, and inertial forces:
main. By defining a collective nodal pressure vector 𝐩𝑝= [𝐩𝑒1, … , 𝐩𝑒𝑛𝑔𝑝]T,                                𝑛
                                 ∑the particle pressure and its smoothed gradient ̃∇𝑝𝑝 can be concisely                                                                                 (𝐑𝑡+𝛥𝑡𝑢    )[𝑖] = (𝐅ext)[𝑖] −                                                                                                                           ̃∇𝑡+𝛥𝑡(𝛿𝐮[𝑖]𝑝) ∶( ̃𝝈𝑡+𝛥𝑡𝑝   )[𝑖]𝑉[𝑖]𝑝
expressed as:                                                                                         𝑝=1
̃𝑝𝑝= ̃𝐍𝑝𝑝𝐩𝑝  and  ̃∇𝑝𝑝= ̃∇𝐍𝑝𝑝𝐩𝑝                                 (26)      ∑𝑛
                                                        −     𝛿𝐮[𝑖]𝑝⋅(𝐚𝑡+𝛥𝑡𝑝    )[𝑖]𝜌𝑡+𝛥𝑡,[𝑖]𝑝     𝑉[𝑖]𝑝                           (31)
Here, the smoothed shape function matrix ̃𝐍𝑝𝑝 and the gradient matrix                   𝑝=1
̃∇𝐍𝑝𝑝 are constructed from the standard shape functions 𝐍𝑘:
        1 [                        ]                                Assuming a summation over all 𝑛 particles, the discretized mass con-
 ̃𝐍𝑝𝑝=    𝜑𝑝1𝑉1𝐍1, … , 𝜑𝑝𝑛𝑔𝑝𝑉𝑛𝑔𝑝𝐍𝑛𝑔𝑝                                       servation equation for the 𝑖th Newton–Raphson iteration is expressed        𝑉𝑝
        1 [                           ]                         (27)      as:
̃∇𝐍𝑝𝑝=    𝜑𝑝1𝑉1∇𝐍1, … , 𝜑𝑝𝑛𝑔𝑝𝑉𝑛𝑔𝑝∇𝐍𝑛𝑔𝑝        𝑉𝑝
   By adopting identical interpolation functions for the displacement  ∑𝑛         ∑𝑛
and pressure fields, the smoothed shape function matrix ̃𝐍𝑢𝑝 is equiva-           𝛿𝑝[𝑖]𝛼̃∇𝑡+𝛥𝑡⋅(𝛥𝐮[𝑖]𝑝)𝑉[𝑖]𝑝 +    𝛿𝑝[𝑖]𝑚𝛥𝑝[𝑖]𝑉[𝑖]𝑝
lent to ̃𝐍𝑝𝑝. Consequently, the increments of particle velocity 𝛥̃𝐯𝑝 and       𝑝=1     𝑛                    𝑝=1                                 (32)                             ∑acceleration 𝛥̃𝐚𝑝 are interpolated from the assembled nodal vectors,       +𝛥𝑡    (̃∇𝑡+𝛥𝑡𝛿𝑝[𝑖])𝑇𝐤𝑝 (̃∇𝑡+𝛥𝑡𝛥𝑝[𝑖])𝑉[𝑖]𝑝 = (𝐑𝑡+𝛥𝑡𝑐    )[𝑖]
                                                                                         𝑝=1           𝜇𝑓defined as 𝛥𝐕𝑝= [(𝛥𝐯)𝑒1, … , (𝛥𝐯)𝑒𝑛𝑔𝑝] and 𝛥𝐀𝑝= [(𝛥𝐚)𝑒1, … , (𝛥𝐚)𝑒𝑛𝑔𝑝], as
follows:
                                                              where ̃∇ denotes the smoothed gradient operator acting on the particle
𝛥̃𝐯𝑝= ̃𝐍𝑢𝑝𝛥𝐕𝑝  and  𝛥̃𝐚𝑝= ̃𝐍𝑢𝑝𝛥𝐀𝑝                               (28)
                                                                                          field. The corresponding residual vector 𝐑𝑐 at the current configuration

                                                                                                is defined as:
2.3.3. Temporal discretization
   Temporal discretization employs an implicit scheme to ensure nu-                             𝑛                             𝑛
merical stability. The solid phase utilizes the Newmark-𝛽 method to        ∑    ( 𝐽−1 )[𝑖]  ∑                                                                                 (𝐑𝑡+𝛥𝑡𝑐    )[𝑖] =𝛥𝑡𝐅[𝑖]𝑝−    𝛿𝑝[𝑖]𝛼            𝑉[𝑖]𝑝 −    𝛿𝑝[𝑖]𝑚((𝑝𝑡+𝛥𝑡)[𝑖] −𝑝𝑡) 𝑉[𝑖]𝑝
integrate the equations of motion. For the fluid phase, following the                         𝑝=1        𝐽            𝑝=1
standard 𝑢-𝑝 formulation for low- to medium-frequency geohazards,       ∑𝑛fluid inertia is neglected, thereby intrinsically omitting the second-           −𝛥𝑡    (̃∇𝑡+𝛥𝑡𝛿𝑝[𝑖])𝑇𝐤𝑝 ̃∇𝑡+𝛥𝑡(𝑝𝑡+𝛥𝑡)[𝑖]𝑉[𝑖]𝑝
order time derivative of pore pressure. Since fluid flow is essentially                      𝑝=1           𝜇𝑓
a diffusion-dominated process, the first-order time derivative in the                                                                                                                                       (33)
continuity equation is implicitly evaluated through the pressure increment 𝛥𝐩 using the Backward Euler algorithm. This treatment effectively
suppresses numerical noise and is completely consistent with standard     Here, the fluid flux source term 𝐅[𝑖]𝑝   is computed via standard finite
practices in recent advanced coupled frameworks (Zhao and Choo,    element integration on the auxiliary mesh. Then, substituting Eqs. (25)
2020; Wang et al., 2025). With 𝛥𝐮 and 𝛥𝐩 as the primary unknowns,
                                                              and (27) into the governing equations yields the final form of the
the update equations are given by
          1                   1    ( 1   )                               system equations:𝐚𝑡+𝛥𝑡=          𝛽𝛥𝑡2           (𝐮𝑡+𝛥𝑡−𝐮𝑡) − 𝛽𝛥𝑡𝐯𝑡− 2𝛽−1  𝐚𝑡
𝐯𝑡+𝛥𝑡= 𝐯𝑡+ 𝛥𝑡[(1 −𝛾)𝐚𝑡+ 𝛾𝐚𝑡+𝛥𝑡]                                 (29)    [                                                                                                                                   ][𝑖] {𝛥𝐮 }[𝑖]                                                                                              1 𝐌+ 𝐊𝐶&𝐺   −𝐐                                                                               {𝐑𝑢 }[𝑖]                                                                                                  𝛽𝛥𝑡2                                                                           =                                                                                                                                       (34)
𝐩𝑡+𝛥𝑡= 𝐩𝑡+ 𝛥𝐩                                                    𝐐𝑇     𝐒+ 𝛥𝑡𝐇    𝛥𝐩       𝐑𝑐

where 𝐮, 𝐯, 𝐚, and 𝐩 represent the solid displacement, velocity, ac-
                                                              where 𝛥𝐮 and 𝛥𝐩 are the vectors of incremental nodal displacementsceleration, and pore pressure, respectively. Unconditional stability is
guaranteed by selecting Newmark parameters such that 2𝛽≥𝛾≥0.5.     and pore water pressures. The component matrices on the left-hand side

                                                                        5

### Page 6

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

are defined as:                                                              study), the redundant particles are removed. Because this removal is
   ∑𝑛                                                                            strictly limited to overly crowded areas, a sufficient number of particles
  𝐌=     (̃𝐍[𝑖]𝑢𝑝)𝑇𝜌𝑡+𝛥𝑡,[𝑖]𝑝       ̃𝐍[𝑖]𝑢𝑝𝑉[𝑖]𝑝                                                will always remain to maintain accurate spatial integration.
         𝑝=1                                                              Unlike conventional meshless methods with fixed intrinsic particle
   ∑𝑛 (                                                                    volumes, HEPM dynamically derives 𝑉𝑝 from the auxiliary mesh via                     ̃𝐋[𝑖]𝑝 )𝑇(C+𝐆𝑡+𝛥𝑡)[𝑖]̃𝐋[𝑖]𝑝𝑉[𝑖]𝑝𝐊[𝑖]𝐶&𝐺=
         𝑝=1                                                             the partition of unity detailed in Section 2.3.1. Provided the global
   ∑𝑛 (                                                mesh boundary remains intact, the total volume is strictly conserved   𝐐[𝑖] =        ̃𝐁[𝑖]𝑝 )𝑇̃𝐍[𝑖]𝑝𝑝𝑉[𝑖]𝑝                                        (35)    (∑𝑉𝑝≡𝑉𝑚𝑒𝑠ℎ), which inherently guarantees global mass conserva-
         𝑝=1                                                                       tion. To quantitatively verify this absolute mass conservation, two
   ∑𝑛 (   )𝑇                                                                 static benchmark scenarios were simulated under extreme particle
    𝐒[𝑖] =        ̃𝐍[𝑖]𝑝𝑝    𝑚̃𝐍[𝑖]𝑝𝑝𝑉[𝑖]𝑝                                              adjustments (Fig. 2): (a) particle insertion, where an initially sparse
         𝑝=1
           𝑛                                                                    distribution (0.3 m particle spacing within a 0.1 m fine mesh) trig-                 )𝑇𝐤𝑡+𝛥𝑡𝑝   ∑ (
   𝐇[𝑖] =                ̃∇𝐍[𝑖]𝑝𝑝                                ̃∇𝐍[𝑖]𝑝𝑝𝑉[𝑖]𝑝                                          gers massive continuous particle generation toward a final crowded
         𝑝=1          𝜇𝑓                                                          state; and (b) particle deletion, where an initially crowded distribution
                                                                                   (0.1 m particle spacing within a 0.3 m coarse mesh) causes extensiveCorrespondingly, the residual vectors and internal force terms on the
                                                                   redundant particle removal toward a final sparse state. The trackingright-hand side are given by:
                                                                                  results demonstrate that despite the drastic accumulation of inserted
      ∑𝑛                                                     or deleted particles in both scenarios, the relative mass change  is𝐑[𝑖]𝑢= 𝐅[𝑖]ext −𝐅[𝑖]int −     (̃𝐍[𝑖]𝑢𝑝)𝑇(𝐚𝑡+𝛥𝑡𝑝    )[𝑖]𝜌𝑡+𝛥𝑡,[𝑖]𝑝     𝑉[𝑖]𝑝
                    𝑝=1                                                   zero within numerical precision (i.e., <10−12). This rigorously proves
  ∑𝑛                                                                    that the adaptive strategy guarantees global mass conservation without𝐅[𝑖]  int =      (̃𝐋[𝑖]𝑝)𝑇(̃𝝈𝑡+𝛥𝑡𝑝   )[𝑖]𝑉[𝑖]𝑝                                                introducing any numerical dissipation.
       𝑝=1
𝐑[𝑖]𝑐= 𝛥𝑡(𝐅[𝑖]𝑃) −𝐅[𝑖]𝑄−𝐅[𝑖]𝑆−𝐅[𝑖]𝐻                                                 2.4. FIC stabilized method in particle field
  ∑𝑛 (   )𝑇                                               (36)
 𝐅[𝑖]𝑄=        ̃𝐍[𝑖]𝑝𝑝    (𝑉𝑡+𝛥𝑡,[𝑖]𝑝    −𝑉𝑡𝑝)                                                              To suppress spurious pressure oscillations and enable the use of       𝑝=1
  ∑𝑛 (   )𝑇                                                         equal-order interpolation, the Finite Increment Calculus (FIC) stabiliza-
 𝐅[𝑖]𝑆=        ̃𝐍[𝑖]𝑝𝑝    𝑚(𝑝𝑡+𝛥𝑡,[𝑖] −𝑝𝑡)𝑉[𝑖]𝑝                                           tion technique (Oñate et al., 2014; de Pouplana and Oñate, 2017) is
       𝑝=1                                                               incorporated into the HEPM framework. As illustrated in Fig. 3, the
   ∑𝑛 (     )𝑇𝐤𝑡+𝛥𝑡𝑝                                              fundamental concept of the FIC procedure involves establishing the
 𝐅[𝑖]𝐻= 𝛥𝑡      ̃∇𝐍[𝑖]𝑝𝑝         ∇(𝑝𝑡+𝛥𝑡)[𝑖]𝑉[𝑖]𝑝                                        flux balance over a finite segment (e.g., a 1D domain of length 𝑑).
         𝑝=1          𝜇𝑓
                                                           By expressing the entering and exiting fluxes (𝑞𝐴 and 𝑞𝐵) using Taylor
In these expressions, 𝐌 represents the consistent mass matrix derived     series expansions around an arbitrary point 𝐶, higher-order terms
from the mixture density 𝜌𝑝. 𝐐, 𝐒, and 𝐇 denote the coupling, compress-     proportional to the characteristic length are naturally introduced into
ibility, and permeability matrices, respectively. The global stiffness     the standard governing equations. Extending this finite-domain balmatrix 𝐊𝐶&𝐺 incorporates both the material constitutive tensor C and    ance concept to the multidimensional HEPM framework, the stabilized
the geometric stiffness 𝐆 (see Fang and Yin (2025b) for the detailed     residual equation is reformulated as:
formulation).
                                                 𝑟= 𝐐𝑇𝛥𝐮+ (𝐓𝑠𝑡𝑎𝑏𝑃  + 𝐒+ 𝛥𝑡𝐇)𝛥𝐩−𝐑𝑠𝑡𝑎𝑏𝑐  = 0                       (37)
2.3.5. Adaptive particle management strategy
                                                              where the stabilization matrix 𝐓𝑠𝑡𝑎𝑏𝑃  and the modified residual vector   In large deformations, uneven particle distributions can cause nu-
                                                                                    𝐑𝑠𝑡𝑎𝑏𝑐   are defined as:merical instability (from clustering) or integration errors (from sparsity). To resolve this, the current HEPM employs an adaptive particle    ∑𝑛
management scheme synchronized with the auxiliary mesh regenera-      𝐓𝑠𝑡𝑎𝑏𝑃  =     (̃∇𝐍𝑝𝑝)𝑇(̃∇𝐍𝑝𝑝)(𝜏𝛼)𝑉𝑝
                                                                                         𝑝=1                                                     (38)
tion (Fang and Yin, 2025a,b). Guided by active Gaussian points, this
dynamic adjustment operates under three criteria:                            𝐑𝑠𝑡𝑎𝑏𝑐  = 𝛥𝑡𝐅𝑃−𝐅𝑄−𝐅𝐻−𝐅𝑆−𝐓𝑠𝑡𝑎𝑏𝑃  (𝐩𝑡+𝛥𝑡−𝐩𝑡)
    1. Removal of isolated particles: During extensive material flow,    where 𝐩 represents the global vectors of nodal pore pressure. The
some particles may move outside the influence zones of all active                                                                                 stabilization parameter is directly derived from the governing equaGaussian points. If the normalized distance between a particle and its                                                                              tions (de Pouplana and Oñate, 2017) and  is given by 𝜏= ℎ2𝛼∕(8𝐺),
nearest Gaussian point exceeds the boundary, namely 𝑑𝑝𝑘>  1, the    where 𝛼 is the Biot coefficient as previously defined, 𝐺 denotes the
particle is identified as kinematically disconnected. These redundant                                                                       shear modulus and ℎ= 3√6𝑉𝑝∕𝜋 represents the characteristic length of
particles are deleted to optimize computational efficiency.
                                                                        the particle volume 𝑉𝑝. Incorporating these terms, the final stabilized
    2. Insertion in sparse regions: If severe material deformation leaves
                                                                    hydro-mechanical system is expressed in a monolithic matrix form:
a Gaussian point’s influence zone entirely without particles, a new
                                                   [                                                                                                                                }[𝑖]                                                             {                                                                                                                                              }[𝑖]particle           is generated                       at the                            center of                                           this zone                                                  to guarantee                                                                 integra-                                                                                              1 𝐌+                                                                                                                                            ][𝑖] {𝛥𝐮                                                                      −𝐐𝑃                                                              𝐊𝐶&𝐺                                                                                                         𝐑𝑢                                                                                                  𝛽𝛥𝑡2                                                                               =                                                                                                                                       (39)tion accuracy.            To maintain                            physical                                      continuity,                                              the                                                  history-dependent                                                                                         𝛥𝐩                                                                                                                                            𝐑𝑠𝑡𝑎𝑏                                                              𝐐𝑇                                                                 + 𝐒+ 𝛥𝑡𝐇                                                                                                                                                                                       𝑐                                                                                                            𝐓𝑠𝑡𝑎𝑏𝑃variables of this new particle are evaluated using an Inverse Distance
Weighting (IDW) interpolation from its nearest neighboring particles (5
                                                                                 2.5. Comparison with related numerical methodsin this study). Since only a very small number of particles are inserted
globally, this local interpolation has a negligible impact on the overall
accuracy of the solution.                                          To highlight the novelty of the proposed HEPM framework,  it
    3. Deletion in clustered regions: In areas of intense compression, an      is essential to distinguish  it from prominent alternative approaches,
excessive number of particles can gather within a single influence zone,    namely MPM and the PFEM. While these methods share the fundapotentially leading to numerical issues. To prevent this, a predefined    mental concept of combining Lagrangian particles with a spatial mesh,
density threshold 𝑁𝑚𝑎𝑥 is introduced. If the local particle count within     they differ significantly in spatial discretization, which provides the
a Gaussian influence domain exceeds this limit (set to 𝑁𝑚𝑎𝑥= 10 in this    proposed HEPM approach with distinct advantages.

                                                                        6

### Page 7

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

                Fig. 2. Quantitative verification of mass conservation under extreme particle changes: (a) particle insertion; (b) particle deletion.

                                                                boundary over successive remeshing steps, leading to unphysical mass
                                                                                  loss and boundary oscillation (Lacroix et al., 2026).

                                                                           3. Numerical verification and benchmarking

                                                              To evaluate the performance of the proposed HEPM framework,
                                                                                    this section conducts a series of numerical simulations ranging from
                                                                          element-level verification to field-scale applications. The validation
                   Fig. 3. Fluxes balance of finite segment.
                                                                                suite includes 1D dynamic consolidation, 2D wave propagation bench-
                                                                    marks, and 3D triaxial tests to ensure algorithmic accuracy. Further-
                                                                  more, the method’s capacity to handle geometric non-linearities and
2.5.1. Comparison with MPM                                        complex failure mechanisms is demonstrated through practical land-
   Standard MPM employs a dual-discretization framework, utilizing     slide scenarios, specifically focusing on seepage-induced softening and
moving Lagrangian particles to track material history alongside a sta-     progressive slope failure.
tionary background grid to solve the governing equations. While this
fixed grid prevents element distortion, it requires continuous variable     3.1. Dynamic consolidation
mapping between particles and nodes, thereby introducing numerical
dissipation. In contrast, the proposed HEPM replaces the background       To validate the accuracy of the proposed HEPM framework in
grid with a dynamic, boundary-conforming auxiliary mesh used ex-     solving dynamic coupled problems, three benchmark cases of 1D dyclusively to construct particle interpolation functions. Through this    namic consolidation are presented. These cases cover different loading
approach, all state variables are permanently stored on the particles,     conditions and fluid compressibility characteristics.
fundamentally avoiding variable mapping and the resulting numerical
dissipation. Additionally, since the mesh exactly tracks the domain     Case 1: Step loading with incompressible fluid
boundary, the imposition of 𝑢-𝑝 boundary conditions  is direct and       The first validation benchmark examines a saturated soil column
accurate.                                                                subjected to a sudden step load, comparing the results against the
                                                                              analytical solution provided by De Boer et  al. (1993). The model
2.5.2. Comparison with PFEM                                                 consists of a soil column with dimensions of 1 m × 1 m × 10 m, as
   Unlike MPM and HEPM, standard PFEM does not rely on a tradi-      illustrated in Fig. 4(a). While this benchmark can be simplified to a
tional dual-discretization scheme with independent mesh and particle    1D or 2D problem, a full three-dimensional configuration is employed
fields. Instead, PFEM is based on node reconnection, wherein moving     here to validate the numerical stability and accuracy of the HEPM
particles themselves serve directly as the nodes of the finite element    framework, thereby confirming its capability for practical applications.
mesh, and mesh distortion is resolved by modifying the connectiv-     For the numerical discretization, the domain is mapped onto approxiity of these nodes while preserving their positions. While standard    mately 2000 auxiliary elements, with a corresponding set of material
PFEM successfully avoids global mapping errors, tracking large de-     particles initialized within the active region. The boundary conditions
formations causes the particle distribution to become highly irregu-     are defined as follows: the lateral surfaces are horizontally constrained
lar. Reconstructing elements directly on these unevenly distributed    and impermeable, the base is fully fixed and impermeable, while the
nodes often leads to poor mesh quality and numerical instability. Since     top surface is free to drain and deform (𝑝=  0). A step load with
element regeneration in PFEM  is restricted to the existing moving    a magnitude of 𝑞0 = 3 kN/m2  is instantaneously applied to the top
nodes, the resulting mesh quality often deteriorates. This limitation     surface at 𝑡=  0. The material properties are selected to represent
is especially pronounced in three-dimensional simulations. Moreover,    a soft soil saturated with an incompressible fluid. The solid phase
advanced PFEM variants  (e.g., SNS-PFEM) frequently require addi-     properties include a Young’s modulus of 𝐸= 20.1 MPa, a Poisson’s ratio
tional stabilizing terms, inherently increasing the algorithmic complex-     of 𝜈= 0.2, and a solid density of 𝜌𝑠= 2000 kg/m3. The fluid phase
ity compared to the HEPM framework (Fang and Yin, 2025b). Another      is characterized by a density of 𝜌𝑓= 1000 kg/m3, and the coupling
critical limitation of conventional PFEM lies in extracting the 𝛼-shape     parameters include a porosity of 𝑛= 0.33, a hydraulic conductivity of
from Delaunay tessellation for boundary recognition. However, relying   𝑘= 0.01 m/s, and a Biot coefficient of 𝛼= 1.0. Fig. 4(b) compares
solely on the 𝛼-shape criterion can improperly distort the physical     the vertical displacements at depths of 𝑧=  0 m, 0.4 m, and 1.0 m

                                                                        7

### Page 8

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

Fig. 4. Validation of 1D dynamic consolidation results against the analytical solution for Case 1: (a) model geometry and boundary conditions, (b) time histories
of vertical displacement at various depths, and (c) pore pressure profiles at selected times.

obtained from the HEPM simulation against the analytical solution. The     rate confirms that the dynamically regenerated auxiliary mesh effecresults exhibit excellent agreement, accurately capturing the transient     tively suppresses mesh dependency, ensuring spatial accuracy for fully
deformation characteristics. Furthermore, the pore pressure evolution     coupled analysis.
presented in Fig. 4(c) demonstrates that the proposed framework cor-       To quantitatively evaluate the stabilization effect, an additional
rectly reproduces the dynamic wave propagation and the subsequent     high-gradient consolidation scenario (𝑘= 1.0 × 10−3 m/s at 𝑡= 0.01 s)
consolidation process. The pore pressure dissipates gradually from the      is designed to intentionally trigger numerical instability. A dimensiondrainage surface downwards, with the numerical predictions matching      less factor 𝑐ℎ is introduced to scale the baseline characteristic length
                                                                   such that ℎ𝑒𝑓𝑓= 𝑐ℎℎ, where ℎ= 3√6𝑉𝑝∕𝜋 as defined in Section 2.4.the analytical curves remarkably well.
                                                               As shown in Fig. 6(a), the near-surface pore pressure profiles reveal
   To rigorously evaluate the spatial convergence of the proposed
                                                                             that without stabilization (𝑐ℎ= 0), the results suffer from severe, nonHEPM framework while isolating the spatial discretization error from
                                                                          physical spatial oscillations due to the violation of the inf-sup condition.
temporal integration errors, a mesh sensitivity analysis is deliberately
                                                                        Conversely, an oversized parameter (𝑐ℎ≥1.5) introduces excessive arconducted in the quasi-static limit. The one-dimensional consolidation
                                                                                               tificial diffusion, which severely blurs the physical pressure gradient.
benchmark is simulated using four different auxiliary mesh discretiza-
                                                           To provide a rigorous assessment, Fig. 6(b) plots the relative 𝐿2 error
tions with average element sizes decreasing from ℎ= 0.05 m to 0.025 m.                                                         norm of pore pressure against the analytical solution. The error curve
To quantitatively assess the pure spatial accuracy, the numerical pore     explicitly demonstrates a U-shaped trend: the error is distinctly high at
water pressure  is compared against the classic Terzaghi analytical    𝑐ℎ= 0 due to spurious oscillations, rises again for 𝑐ℎ> 1.0 due to oversolution, and the relative 𝐿2 error norm is calculated following Feng     smoothing, and reaches a strict minimum precisely at 𝑐ℎ= 1.0. This
et al. (2024a). As shown in Fig. 5, the relative 𝐿2 error norm steadily     quantitatively confirms that the proposed default formulation achieves
decreases with mesh refinement, yielding an average spatial conver-     the optimal balance between suppressing numerical instability and
gence order of approximately 1.86. This near-optimal convergence    minimizing artificial dissipation.

                                                                        8

### Page 9

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

                                                                     Case 3: Step loading with compressible fluid
                                                                        Following the validation of incompressible fluid scenarios, the final
                                                              benchmark in 1D consolidation introduces fluid compressibility to ex-
                                                              amine wave propagation characteristics in a fully poroelastic medium,
                                                                 comparable to the study by Dubner and Abate (1968). The model
                                                                 geometry and boundary conditions remain identical to those in Case 1,
                                                                     but the material properties are modified to consider compressible solid
                                                                           grains and pore fluid. The specific parameters are assigned as follows:
                                                                    Young’s modulus 𝐸= 2.544 × 108 Pa, Poisson’s ratio 𝜈= 0.298, solid
                                                                          density 𝜌𝑠= 2700 kg/m3, porosity 𝑛= 0.48, and hydraulic conductivity
                                     𝑘= 1.1 × 10−9 m/s. The compressibility of the phases is defined by
                                                                  a fluid bulk modulus of 𝐾𝑓 =  3.3 × 109 Pa and a solid grain bulk
                                                              modulus of 𝐾𝑠= 1.1 × 1010 Pa. A constant step load of 1 Pa is applied
                                                                            to the surface. Distinct from the incompressible cases, the surface
                                                                         settlement in Fig. 9(a) exhibits sustained oscillations even under a
                                                                        constant load. This phenomenon is attributed to the inertial effects and
                                                                        the reflection of elastic waves within the compressible medium, which
                                                                         are not immediately damped. Similarly, the pore pressure evolution at
                                                                        the column base, depicted in Fig. 9(b), displays a characteristic stepwise
         Fig. 5. Relative 𝐿2 norm error of the pore pressure profile.             periodic fluctuation. The proposed HEPM framework accurately repro-
                                                                    duces these complex wave interaction features, yielding results that are
                                                                        highly consistent with established numerical solutions in the literature.
Case 2: Harmonic loading with incompressible fluid                        The minor overshoots following the pressure jumps are natural
   The second benchmark investigates the dynamic response of a soil     high-frequency oscillations excited by the instantaneous step loading.
column under harmonic surface loading, as presented by Han et al.    Such localized transient phenomena are typical in complete dynamic
(2015). The physical model, including the 10 m column geometry and     formulations (Soares et al., 2006; Soares, 2008; Jassim et al., 2013;
the hydraulic boundary conditions, is identical to that described in the    Yuan et  al., 2022), and the proposed HEPM framework accurately
first benchmark (Case 1). Specifically, the top surface remains a fully     captures the macroscopic stepwise trend.
drained boundary with zero excess pore pressure (𝛥𝑝= 0), while the
lateral and bottom boundaries are assumed to be impermeable. The                                                                                 3.2. Wave propagation in a strip foundation
linear elastic material properties are defined as: Young’s modulus 𝐸=
10 MPa, density 𝜌= 2000 kg/m3, Poisson’s ratio 𝜈= 0.2, and porosity
                                                                           This section validates the model’s capability to simulate coupled
𝑛= 0.35. To examine the numerical stability under a consolidation
                                                          wave propagation under plane-strain conditions, referencing the bench-process, a relatively high hydraulic conductivity of 𝑘= 1.0 × 10−2 m/s is
                                                           mark problem established by Markert et al. (2010). The computationaladopted. The solid and fluid phases are assumed to be incompressible.
The simulation employs a time integration step of 𝛥𝑡= 0.001 s. The    domain comprises a rectangular soil profile with a width of 10.5 m
applied surface load 𝐹(𝑡) is divided into a linear ramp phase followed    and a height of 10 m. To accurately capture the steep stress gradients,
by a harmonic oscillation, mathematically expressed as:                     local mesh refinement is implemented in the top-right region near the
                                                                       loading zone. The schematic representation of the model geometry is
     ⎧   𝑡
     ⎪ 0.02𝑃𝑠𝑢𝑟𝑓                       0 < 𝑡≤0.02 s                       illustrated in Fig. 10. The boundary conditions are defined as follows:
𝐹(𝑡) = ⎨                                                       (40)     the top surface is fully drained (𝑝= 0) and mechanically free; the
        𝑃𝑠𝑢𝑟𝑓[1 + 0.25 sin (20𝜋(𝑡−0.02))]  𝑡> 0.02 s                                                                                   lateral boundaries are impermeable and constrained horizontally (roller         ⎪⎩
                                                                            support); the bottom boundary is fixed and impermeable. A harmonicwhere 𝑃𝑠𝑢𝑟𝑓  is the reference surface pressure amplitude. Fig. 7(a)
illustrates the settlement history of the top node, which oscillates     load is applied to a strip of 0.5 m width on the right side of the top
in phase with the applied harmonic loading. Significantly, Fig. 7(b)     surface. The load is applied within 0.04 s and subsequently removed
presents the pore pressure evolution at the column base. The HEPM    when  𝑡 >  0.04  s. To analyze the transient response, two specific
simulation precisely captures the rapid pressure fluctuations induced     monitoring points are established: Point A at (5.0, 10.0) m for recording
by the inertial loading. The excellent agreement between the numerical     vertical displacement, and Point B at (8.0, 8.0) m for tracking pore water
results and the analytical solution validates the framework’s capability     pressure evolution.
in handling transient loads under undrained conditions.                   The dynamic responses obtained from the HEPM simulation are
   To quantitatively evaluate the impact of particle change on momen-     quantitatively validated against existing numerical solutions (Markert
tum conservation, an extreme-case analysis was conducted using the     et  al., 2010; Wang et  al., 2025). Fig. 11(a) plots the displacement
above 1D harmonic loading model. We compared a constant-particle     trajectory of Point A in the x-z plane. The HEPM results reproduce
baseline case with two modified cases where extreme variations, in-                                                                        the characteristic closed-loop motion of the surface wave, demonstratcluding a 50% particle insertion and a 30% particle deletion, were                                                                         ing excellent agreement with the reference data. Similarly, Fig. 11(b)
artificially triggered at 𝑡= 0.1 s. To track the momentum fluctuation,
                                                                            depicts the temporal evolution of pore water pressure at Point B.
the relative difference of the linear momentum in the Z-direction is de-
                                                             The simulation accurately captures the rapid pressure transient and
fined as 𝑒𝑧(𝑡) = (𝐿𝑧,𝑚(𝑡)−𝐿𝑧,𝑏(𝑡))∕𝐿𝑧,𝑏(𝑡) × 100%, where 𝐿𝑧,𝑏(𝑡) and 𝐿𝑧,𝑚(𝑡)
                                                                        the subsequent dissipation, matching the benchmark results with high
are the momenta of the baseline and modified simulations, respectively.
                                                                                        fidelity.
Fig. 8 illustrates the time history of the relative difference in global
                                                                The spatial distribution of pore pressure at 𝑡= 0.05 s is comparedmomentum. Remarkably, even with such massive and instantaneous
particle variations, the relative difference remains strictly bounded     with 2D and 3D PFEM solutions (Wang et al., 2024, 2025) in Fig.
within 0.01%. Considering that particle changes typically occur only     12. While the global pressure fields predicted by both methods are
in highly localized regions during large-deformation processes, the     consistent, distinct differences are observed in the soil heaving region.
numerical perturbation introduced by these changes is negligibly small,     In this zone, where negative pore pressures develop due to volumetric
ensuring the robustness of momentum conservation in the proposed     dilation, the standard Galerkin spatial discretization with equal-order
framework.                                                          elements (as typically used in conventional PFEM) inherently violates

                                                                        9

### Page 10

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

Fig. 6. Quantitative analysis of the scaling factor (𝑐ℎ): (a) Pore pressure distribution under different 𝑐ℎ values compared with the analytical solution; (b) Relative
𝐿2 error of the pore pressure versus 𝑐ℎ.

Fig. 7. Validation of 1D dynamic consolidation results for Case 2 under harmonic loading: (a) time history of surface settlement, and (b) pore pressure evolution
at the column base compared with the analytical solution.

                                                                        the inf-sup condition, leading to visible numerical oscillations. Con-
                                                                               versely, the proposed HEPM yields a much smoother and physically
                                                                            consistent pressure distribution. This improvement is directly attributed
                                                                            to the integration of the FIC stabilization technique, which overcomes
                                                                        the inf-sup restriction. This comparative analysis demonstrates that
                                                                        the proposed stabilized framework effectively addresses the shared
                                                                        challenge of spurious oscillations in regions undergoing complex defor-
                                                                      mation, thereby providing robust solutions for coupled boundary value
                                                                  problems under undrained conditions.

                                                                                 3.3. Triaxial compression tests

                                                              To evaluate the efficacy of the proposed HEPM framework in cap-
                                                                           turing post-failure volumetric behavior – specifically shear-induced
                                                                               dilation and contraction – a series of three-dimensional triaxial com-
                                                                          pression tests are simulated. The results are benchmarked against ref-
                                                                      erence solutions from SPH (Morikawa and Asai, 2022; del CastilloFig. 8. Quantitative validation of dynamic momentum conservation during
massive particle change in HEPM.                                                et al., 2024), providing a comparative performance analysis between
                                                                        the proposed approach and existing pure particle-based methods. The
                                                                    numerical model represents a cylindrical soil specimen with a diameter
                                                                              of 𝐷= 0.06 m and a height of 𝐻= 0.15 m, as illustrated in Fig. 13. A

                                                                        10

### Page 11

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

Fig. 9. Validation of 1D dynamic consolidation results for Case 3 for compressible fluid: (a) time history of surface settlement showing inertial oscillations, and
(b) stepwise pore pressure evolution at the column base.

                     Fig. 10. Geometric setup and boundary conditions for simulating dynamic wave propagation under a strip foundation.

distinct advantage of the proposed HEPM over pure particle methods—     conditions (UC). The mechanical behavior of the soil is described by the
which typically necessitate complex treatments like ghost particles or     Modified Cam-Clay (MCC) model. Key constitutive parameters adopted
boundary repulsive forces to enforce confinement (Morikawa and Asai,     in this study include the slope of the normal consolidation line 𝜆=
2022)—is the utilization of the auxiliary mesh to rigorously impose      0.2, the slope of the swelling line 𝜅= 0.05, and a Poisson’s ratio of
boundary constraints. The mechanical boundary conditions are defined   𝜈= 0.3. The pre-consolidation pressure is fixed at 𝑝′𝑐= 600 kPa. To
as follows: the base is fully fixed, while a constant scalar confining     investigate the response of heavily over-consolidated (HOC) soil, the
pressure, denoted as 𝜎𝑟= 𝑝′0, is applied to the lateral surface to simulate      initial confining pressure is prescribed as 𝑝′0 = 100 kPa, corresponding
the cell pressure. Axial compression is induced by a prescribed vertical     to an over-consolidation ratio (OCR) of 6.0. Physically, the mixture is
velocity 𝑣top = −0.1 m/s at the top surface. Hydraulically, the lateral     characterized by a particle density of 𝜌𝑠= 3000 kg/m3, a fluid density
and bottom boundaries are impermeable. The top boundary condition     of 𝜌𝑓= 1000 kg/m3, and an initial porosity of 𝑛0 = 0.5. The hydraulic
varies by case: a zero pore pressure (𝑝= 0) is prescribed for drained     response is controlled by the hydraulic conductivity 𝑘, which is set to
conditions (DC), whereas a no-flux boundary is applied for undrained     10−1 m/s to simulate drained conditions and reduced to 10−8 m/s for

                                                                        11

### Page 12

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

                Fig. 11. Comparison of dynamic responses: (a) displacement trajectory of Point A; (b) pore water pressure evolution at Point B.

Fig. 12. Comparison of pore pressure contours at 𝑡= 0.05 s: (a) proposed 3D HEPM; (b) 3D N-PFEM by Wang et al. (2025); (c) 2D N-PFEM by Wang et al. (2024).

undrained scenarios. Numerically, the simulation employs a particle     adheres to this kinematic constraint. Conversely, the SPH results exhibit
size of 𝑑= 0.002 m and a uniform time increment of 𝛥𝑡= 10−6 s to     significant spurious volumetric drift, indicating a failure to rigorously
ensure stability. To mitigate boundary effects, the evolution of stress     enforce incompressibility.
variables (mean effective stress 𝑝′ and deviatoric stress 𝑞) and specific       The contrasting performance between HEPM and SPH across both
volume 𝑣 are monitored and averaged over a representative volume     drainage conditions highlights the fundamental algorithmic differences.
element (RVE) located at the geometric center of the specimen.          As explicitly noted by  Morikawa and Asai (2022), the divergence
    Fig. 14 illustrates the drained response of heavily overconsolidated     of SPH near the critical state  is primarily attributed to unsatisfacsoils in terms of effective stress paths (𝑝′ −𝑞) and specific volume     tory boundary conditions. Indeed, enforcing rigorous stress-controlled
evolution (ln 𝑝′ −𝑣). To clarify the underlying elastoplastic behavior,     boundaries (for drained tests) and isochoric constraints (for undrained
the critical state line (CSL, 𝑀= 1.2), normal consolidation line (NCL),      tests) during large dilatant deformations remains a general challenge
and swelling line (SL) are plotted as benchmarks. In the effective stress     for conventional meshfree methods (Hosseini and Feng, 2011; Peng
space (Fig. 14(a)), the HEPM results exhibit excellent agreement with     et al., 2015; Xiao et al., 2020; Park and Seo, 2024). Due to inherthe analytical solution. This benchmark solution, labeled as ‘Theory’ in     ent particle deficiency near surfaces, SPH heavily relies on artificial
the plot, is generated by a single-point constitutive driver integrating     ghost particles. The degradation of these boundary approximations
the MCC rate equations via a fully implicit return mapping algorithm.    under significant volume expansion inevitably leads to the pronounced
The proposed HEPM accurately reproduces the characteristic post-yield     volumetric errors and spurious  drift observed in Figs. 14 and 15.
strain softening and the subsequent convergence toward the CSL. In     This comparison shows a distinct advantage of the proposed HEPM:
the ln 𝑝′ −𝑣 plane (Fig. 14(b)), HEPM captures the complex volumet-    by combining particle advection with a dynamically updated mesh,
ric reversal—initial elastic contraction followed by substantial plastic       it accurately resolves the intricate dilatant and isochoric behaviors
shear dilation. In contrast, the SPH results (Morikawa and Asai, 2022)     without suffering from boundary-induced numerical divergence.
deviate significantly during the later loading stages in both planes,
failing to attain the theoretical critical state.                                 3.4. Seepage-induced embankment failure
    Fig. 15 presents the simulation results under undrained conditions,
where a strict isochoric (constant volume) constraint is enforced. In        This section investigates the instability mechanisms of embankment
the 𝑝′ −𝑞 space (Fig. 15(a)), HEPM accurately reproduces the effec-     slopes induced by reservoir seepage, a critical failure mode in hytive stress evolution, capturing the strain softening that drives the     draulic engineering (Foster et al., 2000; Ma et al., 2022). The upstream
stress path rightward toward the CSL. The algorithmic distinction is     reservoir creates a hydraulic gradient that drives flow through the
most pronounced in the ln 𝑝′ −𝑣 plane (Fig. 15(b)). Theoretically, the    embankment. While the upstream slope is stabilized by the external
undrained trajectory must remain perfectly horizontal. HEPM strictly     confining effect of hydrostatic pressure, the downstream slope and toe

                                                                        12

### Page 13

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

                                     Fig. 13. Schematic of the model and boundary conditions of triaxial compression tests.

Fig. 14. Comparison of HEPM results with SPH data (Morikawa and Asai, 2022) under drained condition: (a) effective stress path in the 𝑝′ −𝑞 space; (b) specific
volume evolution in the ln 𝑝′ −𝑣 space.

are identified as the critical zones. In these regions, the advancing     accurately capture suction effects in unsaturated soils and saturationphreatic surface increases pore water pressure and reduces effective    induced strength degradation within a unified framework, the model
stress, thereby diminishing the soil’s shear strength without the benefit     integrates a pore pressure cut-off strategy with a cohesion weakening
of external support. Consequently, the proposed HEPM framework is    law (Yuan et al., 2023). A pore water pressure threshold, 𝑝𝑡ℎ= 10 Pa
employed to simulate the complete evolution from seepage flow to     serves as the criterion for the saturation: particle with pore pressure 𝑝≥
progressive slope failure, providing a high-precision tool for evaluating      𝑝𝑡ℎ are deemed fully saturated (𝑆𝑟= 1.0). Conversely, particle satisfying
the stability of hydraulic structures.                        𝑝< 𝑝𝑡ℎ are treated as unsaturated with a residual saturation of 𝑆𝑟= 𝑆0.
   The numerical model of a homogeneous embankment is established    Mechanical behavior is governed by the Mohr–Coulomb yield criterion,
with a base width of 1.2 m and a height of 0.3 m (Bui and Nguyen, 2017;     incorporating a saturation-dependent cohesion weakening formula: 𝑐=
Yuan et al., 2023). A hydrostatic pressure boundary is applied to the     𝑐𝑠𝑎𝑡+ (1.0 −𝑆𝑟)(𝑐0 −𝑐𝑠𝑎𝑡); This mechanism describes the reduction of
upstream slope to simulate a 0.3 m reservoir level (see Fig. 16). The     effective cohesion as saturation 𝑆𝑟 increases, thereby capturing local
base is fixed and impermeable, while the downstream slope and top      instabilities triggered by wetting. The material parameters adopted in
are defined as free-drainage boundaries (𝑝= 0). The upstream regions,     the simulation are: Young’s modulus 𝐸 =  3.0 MPa, Poisson’s ratio
identified as non-failure zones, utilize a coarser auxiliary mesh with   𝜈= 0.3, internal friction angle 𝜙= 31.2◦, hydraulic conductivity 𝑘=
a spacing of 0.015 m, while the downstream toe and potential sliding     1.1 × 10−4 m/s, porosity 𝑛= 0.4, bulk modulus of water 𝐾𝑓= 2200 MPa,
surfaces undergo local mesh refinement with a spacing of 0.01 m to    and the densities of water and soil grains are 𝜌𝑓= 1000 kg/m3 and
accurately resolve the formation and propagation of shear bands. To    𝜌𝑠= 2600 kg/m3, respectively; furthermore, to account for the softening

                                                                        13

### Page 14

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

Fig. 15. Comparison of HEPM results with SPH data (Morikawa and Asai, 2022) under undrained condition: (a) effective stress path in the 𝑝′ −𝑞 space; (b)
specific volume evolution in the ln 𝑝′ −𝑣 space.

                             Fig. 16. Model setup and boundary conditions for the seepage-induced embankment failure simulation.

effect, the  initial dry cohesion  is set to 𝑐0 =  0.55 kPa, while the     3.5. Progressive failure of landslide
saturated residual cohesion is significantly reduced to 𝑐𝑠𝑎𝑡= 0.01 kPa.
The simulation proceeds in two stages. First, gravity loading is applied       To further demonstrate the capability of the HEPM framework in
under purely elastic conditions to establish the initial geostatic stress     simulating large-deformation elastoplastic failure, this section presents
                                                                  a simulation of the progressive collapse of a soft soil slope governed byfield, after which the displacement field is reset. Subsequently, the
                                                                  a strain-softening constitutive model. The problem geometry consistselastoplastic constitutive model and the saturation-induced weakening
                                                                              of a slope with a bottom length of 25 m, a height of 5 m, and a
mechanism are activated. Hydrostatic pressure is then applied to drive
                                                                                 crest length of 20 m. A dual-spatial discretization scheme is employed,
the seepage flow, initiating the progressive failure of the embankment.
                                                                                   utilizing approximately 30,000 auxiliary elements to facilitate spatial
    Fig. 17 illustrates the evolution of the pore pressure distribution     interpolation and an equivalent number of Lagrangian particles to track
as the seepage flow propagates from the upstream toe toward the     large plastic deformations and history variables (Fang and Yin, 2025b),
downstream side. The HEPM results correctly reproduce the hydrostatic     as illustrated in Fig. 19(a). The hydraulic and mechanical boundary
profile, characterized by a linear increase with depth and a 0.3 m     conditions are defined as follows: the bottom boundary is fully fixed
pressure head at the upstream boundary. As the simulation progresses,    and impermeable; the left lateral boundary is constrained horizontally
the phreatic surface advances steadily downstream, showing excellent      (roller support) and is also impermeable. Conversely, the top surface
agreement with the FEM benchmark (Bui and Nguyen, 2017). Notably,    and the right slope face are set as free boundaries for solid displacement
the global pore pressure field remains smooth and linear. Fig. 18 depicts    and drained boundaries (𝑝= 0) for the fluid phase, allowing for free
                                                                         drainage. The mechanical behavior of the soil skeleton is described bythe progressive collapse of the embankment triggered by saturation-
                                                                  a linear strain-softening Drucker–Prager (DP) constitutive law with an
induced softening at the downstream toe. Plastic yielding initiates at
                                                                           associated flow rule (𝜓= 0◦).
the toe, accompanied by significant accumulation of plastic strain.
                                                                The material properties are summarized in Table 1. The baseline
Subsequently, this plastic zone propagates upward, coalescing into a
                                                                     parameters are primarily informed by Sang et al. (2025). However,
continuous shear band that results in a distinct rotational failure mode,                                                                     while the reference study employed a Mohr–Coulomb (MC) model,
which is consistent with experimental observations. Furthermore, the                                                                   our HEPM utilizes a smooth Drucker–Prager (DP) criterion to avoid
comparisons with SPH and PFEM results (Bui and Nguyen, 2017; Yuan     singularity-induced divergence. Consequently, slight adjustments to the
et al., 2023) in Fig. 18(b) and (c) demonstrate that the proposed method     cohesion (𝑐) were implemented to optimally capture the progressive
is fully capable of reproducing the complex failure patterns captured by     failure behavior. The simulation proceeds in two stages. First, a gravity
these established advanced algorithms.                                   loading phase (10 s with 𝛥𝑡= 1 s) is performed under purely elastic

                                                                        14

### Page 15

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

Fig. 17. Evolution of the pore pressure distribution: (a) results computed by the proposed HEPM, with the final steady-state phreatic surface compared against
the FEM benchmark; (b) corresponding SPH results (Bui and Nguyen, 2017).

Fig. 18. Contours of accumulated plastic strain showing the progressive rotational failure: (a) results computed by the proposed HEPM compared with the
experimental failure surface; (b) SPH solutions (Bui and Nguyen, 2017); (c) PFEM solutions (Yuan et al., 2023).

conditions to establish geostatic equilibrium and a uniform hydrostatic         Fig. 20(a) illustrates the kinematic evolution of the simulated retropore pressure field. The resulting initial pore pressure distribution is     gressive landslide. The failure initiates with strain localization at the
shown in Fig. 19(b). The pressure at the bottom-left corner reaches     slope toe (𝑡=  1.5 s), leading to the formation of a primary shear
50 kPa, which precisely agrees with the theoretical hydrostatic value,    band and the detachment of the frontal soil block. Following this initial
confirming the accuracy of the initial state generation. To facilitate     collapse, the loss of lateral support triggers a chain reaction: successive
the transition to the second stage, the established effective stresses     rotational slip surfaces continuously propagate upslope (𝑡= 4.5 and
and pore pressures are strictly inherited as the initial state, while the     8.5  s). The final configuration  (𝑡 =  20 s) reveals a characteristic
background nodal displacements and particle velocities are reset to     long-runout deposition, where the collapsed mass exhibits extensive
zero. Concurrently, the material behavior is switched to the strain-     quasi-fluid lateral spreading. To validate these numerical observations,
softening DP constitutive model, and the time increment is significantly     Fig. 20(b) presents a physical conceptual model of a serial progresreduced to 𝛥𝑡= 5 × 10−4 s to stably resolve the subsequent continuous     sive flow slide (Locat et  al., 2011; Urmi et  al., 2023). Comparing
collapse and extensive plastic flow of the slope.                           the simulated evolution with the conceptual schematic demonstrates

                                                                        15

### Page 16

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

Fig. 19. Model configuration and initialization for the slope: (a) geometry, boundary conditions, and mesh discretization; (b) initial particle distribution with
hydrostatic pore pressure at the geostatic equilibrium stage.

Table 1                                                                   excess pore pressure develop along the basal slip surfaces. This pheMaterial properties of the soil skeleton and pore fluid.                    nomenon is attributed to the intense volumetric contraction associated
 Parameter                          Symbol        Value            Unit       with plastic shearing in these undrained zones. Consequently, the fi-
  Saturated density                                 𝜌𝑠𝑎𝑡           2040           kg/m3      nal depositional profile displays a heterogeneous pressure distribution
  Porosity                               𝑛               0.4              –          within the runout debris, contrasting sharply with the uniform linear
 Hydraulic conductivity                𝑘                 1.0 × 10−8       m/s
                                                                              distribution preserved in the remnant stable slope.
 Young’s modulus                𝐸               1.0           MPa            Fig. 22 presents a comparative assessment of mesh quality between
  Poisson’s ratio                            𝜈              0.33             –
                                                                        the traditional FEM and the proposed HEPM. The element quality
  Initial friction angle                             𝜙init          10                    ◦                                                                                                is quantified using the radius ratio metric (Shewchuk, 2002), where
  Residual friction angle                       𝜙res             0.5                   ◦
                                                                  a value closer to unity (1.0) indicates optimal mesh geometry. As  Initial cohesion                                         𝑐init           10              kPa
  Residual cohesion                                  𝑐res           2               kPa         illustrated in Fig. 22(a), the FEM simulation terminates prematurely
  Residual plastic deviatoric strain          𝜀𝑝res             0.20             –         due to severe mesh distortion at the slope toe, where the radius ratio
  Dilatancy angle                  𝜓            0                      ◦          reaches a critical value of approximately 90. In contrast, the HEPM
                                                                                  results in Fig. 22(b) demonstrate superior mesh quality even at the final
                                                                           depositional stage. The majority of elements maintain a radius ratio
a remarkable phenomenological alignment. As documented in classic     within the optimal range of 1.0 to 2.0, with only minor degradation
field observations like the Ullensaker landslide in Norway (Bjerrum,     (reaching ≈3.0) observed at the landslide tip. This comparison confirms
1955; Locat et al., 2011), the initial local failure remoulds the sensitive     that the dynamic remeshing strategy effectively resolves the mesh disclay into a fluidized state. As this debris flows away, it leaves an unsup-     tortion limitations inherent in Lagrangian FEM, ensuring high-quality
ported steep back-scarp that naturally triggers continuous sequential     discretization throughout the large deformation process.
retrogressions (Zhang et al., 2023). The proposed HEPM framework
successfully replicates this complex physical process, capturing both the     4. Conclusions
multi-stage kinematic mechanism and the post-failure runout without
any predefined slip surfaces. The contour plots in Fig. 21 show the        This study extended a stabilized Hybrid Element Particle Method
hydraulic response of the slope, offering both an algorithmic validation    (HEPM) framework to simulate dynamic hydro-mechanical interactions
and a physical analysis of the failure process. Fig. 21(a) presents a     involving extreme large deformations. By employing a dual spatial
critical comparison at 𝑡= 1.5 s between simulations with and without     discretization strategy, the method rigorously couples solid deformaFIC stabilization. In the absence of stabilization, the pore pressure field     tion with pore pressure while effectively eliminating the mesh distorexhibits significant spurious oscillations and spatial irregularity, a com-      tion. Additionally, the implementation of FIC stabilization eliminates
mon numerical issue under extremely low permeability conditions. In     spurious pressure oscillations. This enables the robust use of equalcontrast, the application of FIC effectively suppresses these instabilities,     order interpolation, thereby ensuring both numerical stability and high
yielding a smooth and physically consistent distribution. Notably, the     computational efficiency.
stabilized result clearly resolves a continuous zone of intense excess       The reliability and accuracy of the proposed method are thoroughly
pore pressure at the base of the detached soil block. The subsequent     validated through systematic benchmarks involving dynamic consolidynamic evolution (Fig. 21(b)) reveals that while the stable portion     dation and wave propagation. Comparative analyses demonstrate that
of the slope retains a hydrostatic profile, the failing mass deviates     the HEPM effectively suppresses spurious numerical noise in pore water
significantly from this equilibrium. Specifically, localized zones of high     pressure, yielding a significantly smooth pressure field. Simultaneously,

                                                                        16

### Page 17

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

Fig. 20. Evolution of the strain-softening induced progressive failure: (a) simulated equivalent plastic strain contours at various stages (𝑡= 1.5, 4.5, 8.5, and 20 s);
(b) schematic of the serial flow slide mechanism (Locat et al., 2011).

in contrast to pure particle methods, the reliance on an auxiliary mesh    Declaration of generative AI in scientific writing
greatly simplifies the enforcement of essential boundary conditions
while maintaining superior precision in modeling post-failure plastic       During the preparation of this work the authors used ‘‘ChatGPT’’ in
flow. In terms of engineering applications, this study highlights the     order to improve language. After using this tool, the authors reviewed
                                                              and edited the content as needed and take full responsibility for thedistinct advantages of HEPM in simulating seepage-induced failure.
                                                                       content of the published article.
Results indicate that the method not only matches the accuracy of
traditional FEM during the initial seepage phase but also accurately
                                                                   Declaration of competing interest
reproduces rotational slope failure driven by saturation-induced softening. Furthermore, simulations of progressive failure demonstrate that       The authors declare that they have no known competing finanHEPM completely overcomes the mesh distortion inherent in traditional      cial interests or personal relationships that could have appeared to
grid-based methods during large plastic deformation. Crucially, it ef-     influence the work reported in this paper.
fectively captures the formation of continuous failure surfaces and the
dynamic redistribution of pore pressure under undrained condition.    Acknowledgments
Consequently, the proposed method provides a robust tool for addressing complex geotechnical hazards involving extensive plastic flows and       The authors gratefully acknowledge the financial support from the
                                                                        Science and Technology Innovation Program of Xiongan New Areahydro-mechanical coupled behavior.
                                                                      (Grant No. 2024XAGG0016), from the Research Grants Council (RGC)
                                                                              of the Hong Kong Special Administrative Region Government (HKCRediT authorship contribution statement                       SARG) of China under Grant Nos. 15229223, 15232224, and T22-
                                                                  607/24-N, and from the State Key Laboratory of Climate Resilience for
                                                                         Coastal Cities at the Hong Kong Polytechnic University.
   Yuanyi Qiu: Writing –  original  draft,  Visualization, Software,
Methodology,  Investigation, Formal  analysis. Huangcheng Fang:    Data availability
Writing – review & editing, Supervision, Software, Conceptualization.
Zhen-Yu Yin: Writing – review & editing, Supervision, Methodology.       Data will be made available on request.
Yuqiong Li: Writing – review & editing, Supervision.

                                                                        17

### Page 18

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

Fig. 21. Contours of pore pressure: (a) comparison between simulations with and without the FIC stabilization at 𝑡= 1.5 s; (b) dynamic evolution of the hydraulic
response during progressive failure at 𝑡= 4.5, 8.5, and 20 s.

               Fig. 22. Comparison of element quality using the radius ratio metric: (a) FEM simulation; (b) HEPM simulation at the final state.

References                                                                                 Bui, H.H., Nguyen, G.D., 2017. A coupled fluid-solid SPH approach to modelling flow
                                                                                        through deformable porous media. Int. J. Solids Struct. 125, 244–264.
Afrasiabi, M., Röthlin, M., Klippel, H., Wegener, K., 2019. Meshfree simulation of metal      del Castillo, E.M., Fávero Neto, A.H., Geng, J., Borja, R.I., 2024. An SPH framework
    cutting: an updated Lagrangian approach with dynamic refinement. Int. J. Mech.           for drained and undrained loading over large deformations. Int. J. Numer. Anal.
     Sci. 160, 451–466.                                                              Methods Geomech. 48 (12), 3227–3257.
Bandara, S., Soga, K., 2015. Coupling of soil deformation and pore fluid flow using      Ceccato,  F., Yerro,  A.,  Girardi,  V., Simonini,  P., 2021. Two-phase dynamic MPM
    material point method. Comput. Geotech. 63, 199–214.                                   formulation for unsaturated soil. Comput. Geotech. 129, 103876.
Biot, M.A., 1962. Generalized theory of acoustic propagation in porous dissipative     De Boer, R., Ehlers, W., Liu, Z., 1993. One-dimensional transient wave propagation in
    media. J. Acoust. Soc. Am. 34 (9A), 1254–1264.                                              fluid-saturated incompressible porous media. Arch. Appl. Mech. 63 (1), 59–72.
Bjerrum,  L., 1955.  Stability  of natural slopes  in quick  clay. Géotechnique 5  (1),      Dubner, H., Abate,  J., 1968. Numerical inversion of Laplace transforms by relating
    101–119.                                                                   them to the finite Fourier cosine transform. J. ACM 15 (1), 115–123.
Brezzi, F., Bathe, K.-J., 1990. A discourse on the stability conditions for mixed finite      Fang, H., Yin, Z.-Y., 2025a. Lagrangian Hybrid Element Particle Method (LHEPM) for
    element formulations. Comput. Methods Appl. Mech. Engrg. 82 (1–3), 27–57.              incompressible fluid dynamics. J. Comput. Phys. 114281.

                                                                        18

### Page 19

Y. Qiu et al.                                                                                                                  Computers and Geotechnics 199 (2026) 108390

Fang, H., Yin, Z.-Y., 2025b. A novel Hybrid Particle Element Method (HPEM) for large     de Pouplana, I., Oñate, E., 2017. A FIC-based stabilized mixed finite element method
    deformation analysis in solid mechanics. Comput. Methods Appl. Mech. Engrg. 433,         with equal order interpolation for solid–pore fluid interaction problems. Int. J.
    117530.                                                                      Numer. Anal. Methods Geomech. 41 (1), 110–134.
Feng, R., Fourtakas, G., Rogers, B.D., Lombardi, D., 2024a. A general smoothed particle      Qiu,  Y.,  Yin,   Z.-Y.,  Fang,  H.,  2026.  Stabilized  hepm  for  large-deformation
    hydrodynamics (SPH) formulation for coupled liquid flow and solid deformation         hydro-mechanics in saturated porous media. Internat. J. Mech. Sci. 111343.
    in porous media. Comput. Methods Appl. Mech. Engrg. 419, 116581.                  Sabetamal, H., 2015. Finite Element Algorithms for Dynamic Analysis of Geotechnical
Feng, R., Fourtakas, G., Rogers, B.D., Lombardi, D., 2024b. Modelling internal erosion          Problems. (PhD Thesis). The University of Newcastle, Australia.
    using 2D smoothed particle hydrodynamics (SPH). J. Hydrol. 639, 131558.            Sang, Q.-y., Xiong, Y.-l., Zheng, R.-y., Bao, X.-h., Ye, G.-l., Zhang, F., 2025. An implicit
Foster, M., Fell, R., Spannagle, M., 2000. The statistics of embankment dam failures         coupled MPM formulation for static and dynamic simulation of saturated soils based
   and accidents. Can. Geotech. J. 37 (5), 1000–1024.                                  on a hybrid method. Comput. Mech. 75 (3), 1033–1060.
Gadala, M.S., Wang, J., 1998. ALE formulation and its application in solid mechanics.     Shewchuk, J.R., 2002. What is a good linear element? Interpolation, conditioning, and
   Comput. Methods Appl. Mech. Engrg. 167 (1–2), 33–55.                                     quality measures. In: 11th International Meshing Roundtable. IMR 2002.
Han, B., Zdravkovic, L., Kontoe, S., 2015. Stability investigation of the generalised-𝛼      Soares, Jr., D., 2008. A time-domain FEM approach based on implicit Green’s functions
    time integration method  for dynamic coupled consolidation  analysis. Comput.           for the dynamic analysis of porous media. Comput. Methods Appl. Mech. Engrg.
    Geotech. 64, 83–95.                                                           197 (51–52), 4645–4652.
Hoang, T.N., Bui, H.H., Nguyen, T.T., Nguyen, T.V., Nguyen, G.D., 2024. Development      Soares,  Jr.,  D.,  Telles,  J., Mansur, W., 2006. A time-domain boundary element
    of free-field and compliant base SPH boundary conditions for large deformation          formulation for the dynamic analysis of non-linear porous media. Eng. Anal. Bound.
    seismic response analysis of geomechanics problems. Comput. Methods Appl. Mech.         Elem. 30 (5), 363–370.
    Engrg. 432, 117370.                                                                Sun, Z., Liu, K., Wang, J., Zhou, X., 2021. Hydro-mechanical coupled B-spline material
Hosseini,  S.M.,  Feng,  J.J.,  2011.  Pressure  boundary  conditions  for  computing          point method for large deformation simulation of saturated soils. Eng. Anal. Bound.
    incompressible flows with SPH. J. Comput. Phys. 230 (19), 7473–7487.                   Elem. 133, 330–340.
Idelsohn, S.R., Oñate, E., Pin, F.D., 2004. The particle finite element method: a powerful      Urmi, Z.A., Saeidi, A., Chavali, R.V.P., Yerro, A., 2023. Failure mechanism, existing
    tool to solve incompressible flows with free-surfaces and breaking waves. Internat.           constitutive models and numerical modeling of landslides in  sensitive  clay: a
     J. Numer. Methods Engrg. 61 (7), 964–989.                                               review. Geoenvironmental Disasters 10 (1), 14.
Jassim, I., Stolle, D., Vermeer, P., 2013. Two-phase dynamic analysis by material point     Wang,  Z.-Y.,  Jin,  Y.-F.,  Yin,  Z.-Y., Wang,  Y.-Z.,  2023. A  dynamic SNS-PFEM
    method. Int. J. Numer. Anal. Methods Geomech. 37 (15), 2502–2522.                    with generalized-𝛼 method for hydro-mechanical coupled geotechnical problems.
Jin, Y.-F., Yin, Z.-Y., Zhou, X.-W., Liu, F.-T., 2021. A stable node-based smoothed PFEM         Comput. Geotech. 159, 105466.
    for solving geotechnical large deformation 2D problems. Comput. Methods Appl.     Wang, L., Xue, Q., Wan, Y., Meng, J., Sun, X., Zhao, T., Wei, H., Zhang, X., 2025. An
   Mech. Engrg. 387, 114179.                                                                      implicit nodal integration-based three-dimensional particle finite element model for
Lacroix, M., Fernández, E., Février, S., Papeleux, L., Boman, R., Ponthot, J.-P., 2026.          simulating dynamic saturated porous media. Comput. Geotech. 186, 107372.
   An efficient level set-based mesh adaptation for the particle finite element method.     Wang, L., Zhang, X., Meng, J., Lei, Q., 2024. A stable implicit nodal integration-based
   Comput. Methods Appl. Mech. Engrg. 450, 118644.                                            particle finite element method (N-PFEM) for modelling saturated soil dynamics. J.
Li, X., Han, X., Pastor, M., 2003. An iterative stabilized fractional step algorithm for         Rock Mech. Geotech. Eng. 16 (6), 2172–2183.
     finite element analysis in saturated soil dynamics. Comput. Methods Appl. Mech.     Wang,  L., Zhang,  X., Zhang,  S.,  Tinti,  S., 2021. A generalized Hellinger-Reissner
    Engrg. 192 (35–36), 3845–3859.                                                               variational principle and its PFEM formulation for dynamic analysis of saturated
Li,  S.,  Li,  C., Yao,  D.,  Liu,  C., 2020. Interdisciplinary asperity theory to analyze         porous media. Comput. Geotech. 132, 103994.
    nonlinear motion of loess landslides with weak sliding interface. Landslides 17     Wen,  H.,  Xiao,  J.,  Xiang,  X., Wang,  X.,  Zhang,  W.,  2024.  Singular  spectrum
    (12), 2957–2965.                                                                            analysis-based hybrid PSO-GSA-SVR model for predicting displacement of step-like
Li, Y., Wu, G., Chen, W., Yuan, J., Chen, P., Huo, M., 2026. 3D coupled material point           landslides: A case of jiuxianping landslide. Acta Geotech. 19 (4), 1835–1852.
   method investigation of water-soil inrush at a tunnel face in saturated stratified      Xiao, Y., Hong, X., Tang, Z., 2020. Normalized SPH without boundary deficiency and its
    ground. Tunn. Undergr. Space Technol. 169, 107296.                                       application to transient solid mechanics problems. Meccanica 55 (11), 2263–2283.
Liu, S., Tang, X., Li, J., 2021. Extension of ALE method in large deformation analysis      Yu, J., Zhao, J., Liang, W., Zhao, S., 2024. A semi-implicit material point method for
    of saturated soil under earthquake loading. Comput. Geotech. 133, 104056.               coupled thermo-hydro-mechanical simulation of saturated porous media in large
Locat,  A., Leroueil,  S., Bernander,  S., Demers,  D., Jostad, H.P., Ouehb,  L., 2011.          deformation. Comput. Methods Appl. Mech. Engrg. 418, 116462.
    Progressive failures in eastern Canadian and Scandinavian sensitive clays. Can.      Yuan, W.-H., Liu, M., Zhang, X.-W., Wang, H.-L., Zhang, W., Wu, W., 2023. Stabilized
    Geotech. J. 48 (11), 1696–1712.                                                   smoothed particle finite element method for coupled large deformation problems
Ma, G., Bui, H.H., Lian, Y., Tran, K.M., Nguyen, G.D., 2022. A five-phase approach,           in geotechnics. Acta Geotech. 18 (3), 1215–1231.
   SPH framework and applications for predictions of seepage-induced internal erosion      Yuan, W.-H., Zhu, J.-X., Liu, K., Zhang, W., Dai, B.-B., Wang, Y., 2022. Dynamic analysis
   and failure in unsaturated/saturated porous media. Comput. Methods Appl. Mech.           of large deformation problems in saturated porous media by smoothed particle
    Engrg. 401, 115614.                                                                                     finite element method. Comput. Methods Appl. Mech. Engrg. 392, 114724.
Markert,  B., Heider,  Y., Ehlers, W., 2010. Comparison of monolithic and  splitting      Zhang, R.-X., Su, D., Chen, X.-S., Shi, X.-S., Zhang, D.-J., 2026. Evolution of soil arching
    solution schemes for dynamic porous media problems. Internat. J. Numer. Methods         under different initial water-saturation conditions via coupled SPH-DEM method.
    Engrg. 82 (11), 1341–1383.                                                       Comput. Geotech. 190, 107693.
Monforte,  L., Arroyo, M., Carbonell, J.M., Gens, A., 2017. Numerical simulation of      Zhang, W., Sun, W., Yuan, W., Liu, M., 2025. Progress and prospect of particle finite
    undrained insertion problems in geotechnical engineering with the Particle Finite         element method  for large deformation simulation in geotechnical engineering.
    Element Method (PFEM). Comput. Geotech. 82, 144–156.                             Comput. Part. Mech. 1–19.
Morikawa, D.S., Asai, M., 2022. Soil-water strong coupled ISPH based on u- w- p      Zhang, L., Wang, Y., Liu, J., Liao, K., Zhang, C., 2023. Retrogressive failure pattern and
    formulation for large deformation problems. Comput. Geotech. 142, 104570.                retrogression distance in sensitive clays induced by river erosion. Int. J. Numer.
Nguyen, V.P., De Vaucorbeil, A., Bordas, S., 2023. The material point method. Springer          Anal. Methods Geomech. 47 (4), 585–608.
    International Publishing, Cham.                                                   Zhang, W., Yuan, W., Dai,  B., 2018. Smoothed particle finite-element method for
Oñate, E., 1998. Derivation of stabilized equations for numerical solution of advective-          large-deformation problems in geomechanics. Int. J. Geomech. 18 (4), 04018010.
    diffusive transport and fluid flow problems. Comput. Methods Appl. Mech. Engrg.      Zhao, Y., Choo, J., 2020. Stabilized material point methods for coupled large deforma-
   151 (1–2), 233–265.                                                                           tion and fluid flow in porous materials. Comput. Methods Appl. Mech. Engrg. 362,
Oñate, E., Franci, A., Carbonell, J.M., 2014. Lagrangian formulation for finite element         112742.
    analysis of quasi-incompressible fluids with reduced mass losses. Internat. J. Numer.      Zheng, X., Wang, S., Yang, F., Yang, J., 2024. Material point method simulation of
   Methods Fluids 74 (10), 699–731.                                                      hydro-mechanical behaviour in two-phase porous geomaterials: A state-of-the-art
Park, H.-J., Seo, H.-D., 2024. A new SPH-FEM coupling method for fluid–structure          review. J. Rock Mech. Geotech. Eng. 16 (6), 2341–2350.
    interaction  using  segment-based  interface  treatment.  Eng.  Comput.  40  (2),      Zienkiewicz, O.C., Chan, A., Pastor, M., Schrefler, B., Shiomi, T., 1999. Computational
    1127–1143.                                                                      Geomechanics with Special Reference to Earthquake Engineering. University of
Peng, C., Wu, W., Yu, H.-s., Wang, C., 2015. A SPH approach for large deformation         Tasmania.
    analysis with hypoplastic constitutive model. Acta Geotech. 10 (6), 703–717.

                                                                        19

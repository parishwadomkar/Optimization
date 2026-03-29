# Large-Scale Optimization
## PV- and BESS-enabled public EV charging with user redirection

This repository implements a large-scale mixed-integer linear optimization model for the joint planning of public EV charging infrastructure and distributed energy resources, namely photovoltaic (PV) generation and battery energy storage (BESS). It also includes incentive-based short-range spatial redirection of charging demand so that overloaded locations can be partially relieved through nearby available charging capacity.

The optimization is solved using a **Logic-Based Benders Decomposition (LBBD)**, which makes the problem tractable at city scale while preserving the key couplings between infrastructure investment, energy operation, and redirected charging demand.

The model is driven by spatiotemporal charging-demand data generated from the MATSim-based simulation framework [`UrbanEV-v2`](https://github.com/parishwadomkar/UrbanEV-v2), and is intended for large-scale urban charging infrastructure planning under realistic variation in charging demand, electricity tariffs, solar generation, and battery operation.

<p align="center">
  <img src="./Considerations.png" alt="Research considerations for the integrated EV charging, PV, BESS, and redirection planning problem" width="85%">
</p>

<p align="center"><em>Conceptual scope of the integrated charger–PV–BESS–redirection planning problem.</em></p>

---

## Conceptual scope

This repository addresses the planning problem from the perspective of a **Charging Point Operator (CPO)**. The goal is to determine how public charging infrastructure, PV panels, and battery storage should be deployed and operated so that annual net profit is maximized while aggregated charging demand is satisfied across space and time.

The framework combines long-term infrastructure investment with short-term operational scheduling in one model. It considers:

- multi-class public charger siting and sizing,
- co-located PV and battery deployment,
- tariff-aware battery charging and discharging,
- and incentive-based short-range spatial redirection of charging demand.

In this way, the model captures both the planning value of where assets are placed and the operational value of how energy and demand flexibility are used.

At a system level, the repository is meant to support the following question:

> How should a charging network operator jointly invest in chargers, PV, and battery storage, while selectively redirecting charging demand across nearby locations, in order to improve profitability and infrastructure utilization under time-varying demand and electricity prices?

The model is spatially aggregated over urban grid cells and temporally resolved using representative monthly days and half-hour intervals. It is therefore suitable for city-scale studies where the interaction between charging demand, local renewable generation, storage scheduling, and nearby demand redistribution must be represented explicitly, but where a direct monolithic solve becomes computationally burdensome.

This repository focuses on:

- joint charger, PV, and battery planning,
- operational scheduling under time-of-use electricity tariffs,
- incentive-based local demand redistribution,
- and scalable decomposition-based optimization for large problem instances.

The emphasis is on integrated urban-scale charging planning rather than detailed distribution-network power-flow physics.

---

## Solution approach

The main implementation of the decomposition-based solution is provided in [`LBBD_Small.ipynb`](./LBBD_Small.ipynb), which contains the master problem, slot-level subproblems, cut generation logic, and iterative bound updates used to solve the model.

<p align="center">
  <img src="./LBBD.jpg" alt="Logic-Based Benders Decomposition workflow" width="58%">
</p>

<p align="center"><em>Conceptual LBBD workflow used to solve the large-scale charging planning problem.</em></p>

### Why decomposition is needed..

The original optimization problem is a large-scale MILP that jointly decides:

- where and how many public chargers to install,
- how many PV panels and battery units to deploy,
- how batteries should be charged and discharged over time,
- and how charging demand can be spatially redirected across nearby cells.

At city scale, this creates a strong coupling between long-term investment decisions and short-term operational decisions across many space-time combinations. A direct solve quickly becomes computationally expensive.

LBBD is therefore used to split the problem into a **master problem** and many **slot-level subproblems**, so that the planning structure is retained while the redirection logic is evaluated separately and iteratively.

### Why a logic-based Benders decomposition is used..

A classical Benders decomposition is effective when the recourse problem is cleanly linear. In this case, however, the redirection layer is not only a continuous transportation problem. It also includes:

- discrete trip logic,
- charger-type-specific receiving capacity,
- and operational coupling that must remain feasible when redirected demand is served.

For this reason, the repository uses a **Logic-Based Benders Decomposition** rather than a purely classical Benders scheme.

In practice:

- the **LP subproblem** is used to generate strong dual-based Benders cuts,
- the **MIP subproblem** is used to recover feasible discrete recourse values,
- and the master is tightened iteratively using both dual-based and logic-based cuts.

### Optimization model at a glance

At a high level, the optimization maximizes annual profit from the perspective of the CPO:

$$
\max \; \big[\text{charging revenue} - \text{grid electricity cost} - \text{slack penalty} - \text{annualized infrastructure cost}\big] + \Theta
$$

where $\Theta$ represents the value of redirection recourse in the implemented LBBD scheme.

The decomposition is organized as follows.

**Master problem**
- decides public charger deployment,
- decides PV and battery installation,
- optimizes local charging dispatch, grid usage, PV usage, and battery operation,
- exposes residual public demand and spare charging capacity to the subproblems,
- and carries the redirection value variables $\Theta_{m,t}$.

**Slot-level subproblems**
- are defined for each month-slot pair $(m,t)$,
- receive sendable public demand and spare receiving capacity from the master,
- evaluate profitable redirection over active nearby arcs,
- and return cuts that tighten the master problem.

### Implemented LBBD workflow

The implemented algorithm follows this sequence:

1. Solve the **master problem** with the current cut set.  
2. Extract the interface quantities from the master solution:
   - residual public demand that can be redirected,
   - spare charger-type-specific receiving capacity,
   - and the energy-balance dual information used to price recourse.  
3. Solve the **LP subproblems** for active time slots to obtain:
   - continuous redirection values,
   - dual multipliers,
   - and strengthened Benders cuts.  
4. Solve the **MIP subproblems** to recover feasible discrete recourse values for redirected trips.  
5. Add the generated cuts to the master and update:
   - the **upper bound** from the master objective,
   - the **lower bound** from feasible recourse evaluation.  
6. Repeat until the optimality gap is below tolerance.  

The current implementation also includes practical stabilization devices such as:

- slot-wise value variables for redirection recourse,
- safe initialization bounds on recourse values,
- charger-type-specific spare-capacity interfaces,
- Pareto-type strengthening of Benders cuts,
- and a box trust region on design variables to reduce oscillation between successive master solutions.

---

## Repository contents

The repository is organized to keep the optimization model, sample input data, and exported results easy to navigate.

- [`LBBD_Small.ipynb`](./LBBD_Small.ipynb): main notebook for building and running the LBBD-based optimization model  
- [`small/`](./small): sample spatial input data for a smaller study area in Gothenburg, Sweden  
- [`Results/`](./Results): exported figures and solution files from optimization runs  
- [`Considerations.png`](./Considerations.png): conceptual problem scope and planning considerations  
- [`LBBD.jpg`](./LBBD.jpg): conceptual LBBD workflow  

The sample data are included so users can understand the structure of the model inputs and reproduce a smaller-scale version of the optimization before extending it to larger study areas.

### Input data

The [`small/`](./small) folder contains sample input data for a smaller region in Gothenburg. These files support testing, reproducibility, and understanding of the model setup.

They represent the core spatial inputs required by the optimization, including:

- candidate grid cells and spatial boundaries,
- parking and charger-siting attributes,
- PV-related site information,
- and shortest-path distance data used for short-range user redirection.

---

## Results

The [`Results/`](./Results) folder contains exported solution outputs, figures, and summary files from the optimization runs.

The model is designed to quantify investment trade-offs and operational value under:

- public charger deployment decisions,
- PV and battery co-installation,
- time-of-use electricity prices,
- and short-range user redirection across nearby cells.

A representative result is shown below.

<p align="center">
  <img src="./Results/PV_BattMarchRedir_full.png" alt="Illustrative optimization result showing PV, battery, and redirection-related outputs" width="52%">
</p>

<p align="center"><em>Illustrative optimization output showing the interaction between PV, battery deployment, and user redirection.</em></p>

For the detailed numerical solution, see:

- [`Results_OptiSmall.xlsx`](./Results/Results_OptiSmall.xlsx)

That file provides exported optimization outputs in spreadsheet form and can be used to inspect installed assets, operational values, and aggregated performance indicators in more detail.

### Main findings from the optimization

For the full Gothenburg case study discussed in the associated paper, the integrated optimization shows that:

- **medium chargers dominate** the public charging network because they provide the best cost-throughput trade-off for typical urban dwell times,
- **user redirection alone** yields modest gains, mainly by reducing local peak-capacity needs,
- **battery storage without PV** has limited value because it mainly shifts grid purchases in time,
- **PV materially changes the economics**, reducing grid purchases and making more locations attractive for redirected charging demand,
- and the **combined PV + BESS + redirection configuration** yields the strongest profit improvement and the largest reduction in purchased grid electricity.

These results illustrate the core message of the repository: charger deployment, local renewable generation, storage scheduling, and spatial flexibility should be planned together rather than in isolation.

---

## Contact / support

**Omkar Parishwad**  
Urban Mobility Research Group  
Chalmers University of Technology  
Email: [omkarp@chalmers.se](mailto:omkarp@chalmers.se)

For issues, feature requests, or reproducibility questions, please open a GitHub issue in this repository.

---

## Associated articles and data sources

### Charging infrastructure optimization

Parishwad, Omkar; Najafi, Arsalan; Gao, Kun — *Joint optimization of charging infrastructure and renewable energies with battery storage considering user redirection incentives* (SSRN preprint, Aug 15, 2025)

- [SSRN preprint](https://doi.org/10.2139/ssrn.5395539)  
- [LargeScaleOptimization codebase](https://github.com/parishwadomkar/Optimization/tree/main/LargeScaleOptimization)

### Demand simulation source

The charging-demand inputs used in this optimization are based on the MATSim-driven simulation framework:

- [UrbanEV-v2](https://github.com/parishwadomkar/UrbanEV-v2)

Published demand-modeling article:

Parishwad, Omkar; Gao, Kun; Najafi, Arsalan — *Integrated and Agent-Based Charging Demand Prediction Considering Cost-Aware and Adaptive Charging Behavior*. *Transportation Research Part D: Transport and Environment*, 154 (2026) 105285.

- [Article DOI](https://doi.org/10.1016/j.trd.2026.105285)

### PhD work (Licentiate Thesis):

Omkar Parishwad — PhD thesis / Chalmers publication page:

- [Chalmers publication page](https://research.chalmers.se/publication/547894)
``

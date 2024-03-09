#########################################################
# Sets
#########################################################

set NODEINDEX := 1..11;

set GENERATORINDEX := 1..9;

#########################################################
# Parameters
#########################################################

param cost{GENERATORINDEX};
param max_capacity{GENERATORINDEX};
param demaind{NODEINDEX};
param b{NODEINDEX, NODEINDEX};
param g{NODEINDEX, NODEINDEX};

#########################################################
# Variables
#########################################################

var v{NODEINDEX};
var theta{NODEINDEX};
var active{GENERATORINDEX};
var reactive{GENERATORINDEX};
var G{NODEINDEX};
var R{NODEINDEX};

var p_var {k in NODEINDEX, l in NODEINDEX};
var q_var {k in NODEINDEX, l in NODEINDEX};

#########################################################
# Objective function
#########################################################

minimize Cost1: 
	sum {i in GENERATORINDEX} cost[i] * active[i];

#########################################################
# Constraints
#########################################################
subject to vbounds {i in NODEINDEX}: 0.98 <= v[i] <= 1.02;

subject to thetabounds {i in NODEINDEX}: -3.14159 <= theta[i] <= 3.14159;

subject to activebounds {i in GENERATORINDEX}: 0 <= active[i] <= max_capacity[i];

subject to reactivebounds {i in GENERATORINDEX}: -0.003 * max_capacity[i] <= reactive[i] <= 0.003 * max_capacity[i];

subject to p_constraint {k in NODEINDEX, l in NODEINDEX}:
    p_var[k, l] = v[k]^2 * g[k,l] - v[k] * v[l] * g[k,l] * cos(theta[k] - theta[l]) - v[k] * v[l] * b[k,l] * sin(theta[k] - theta[l]);

subject to q_constraint {k in NODEINDEX, l in NODEINDEX}:
    q_var[k, l] = -v[k]^2 * b[k,l] + v[k] * v[l] * b[k,l] * cos(theta[k] - theta[l]) - v[k] * v[l] * g[k,l] * sin(theta[k] - theta[l]);

subject to Conservation_active {k in NODEINDEX}:
    sum {i in NODEINDEX} p_var[k, i] - G[k] + demaind[k] = 0;
    
subject to Conservation_reactive {k in NODEINDEX}:
	sum {i in NODEINDEX} q_var[k, i] - R[k] = 0;

subject to G1: G[1] = 0;
subject to G2: G[2] = active[1] + active[2] + active[3];
subject to G3: G[3] = active[4];
subject to G4: G[4] = active[5];
subject to G5: G[5] = active[6];
subject to G6: G[6] = 0;
subject to G7: G[7] = active[7];
subject to G8: G[8] = 0;
subject to G9: G[9] = active[8] + active[9];
subject to G10: G[10] = 0;
subject to G11: G[11] = 0;

subject to R1: R[1] = 0;
subject to R2: R[2] = reactive[1] + reactive[2] + reactive[3];
subject to R3: R[3] = reactive[4];
subject to R4: R[4] = reactive[5];
subject to R5: R[5] = reactive[6];
subject to R6: R[6] = 0;
subject to R7: R[7] = reactive[7];
subject to R8: R[8] = 0;
subject to R9: R[9] = reactive[8] + reactive[9];
subject to R10: R[10] = 0;
subject to R11: R[11] = 0;
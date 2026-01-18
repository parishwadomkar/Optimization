# -*- coding: utf-8 -*-
"""
Created on Tue Aug 26 10:52:21 2025

@author: arsalann
"""

# -*- coding: utf-8 -*-
"""
Created on Tue Aug 12 12:01:57 2025

@author: arsalann
"""
import pyomo.environ as pyo
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from PowerFlow import PowerFlow
from PowerFlow import PowerFlow
from DataCuration import DataCuration
from MaxOverlap import max_overlaps_per_parking

from GlobalData import GlobalData



[parking_to_bus, ChargerCap, SampPerH, Vmin, Ch_cost, nChmax, PgridMax, NYearCh, NYearRob, RobotTypes, robotCC, IR, DCchargerCap, PeakPrice, MaxRobot, NevSame] = GlobalData()



 

 

def build_master(s, parking_data, parking_to_bus, SampPerH, Ch_cost, robotCC, Pattern, Price):
    [parking_to_bus, ChargerCap, SampPerH, Vmin, Ch_cost, nChmax, PgridMax, NYearCh, NYearRob, RobotTypes, robotCC, IR, DCchargerCap, PeakPrice, MaxRobot, NevSame] = GlobalData()

    model = pyo.ConcreteModel()

    
    EVdata = parking_data[parking_data['ParkingNo'] == s].reset_index(drop=True)
     
    # Calculate and print results
    max_overlaps = max_overlaps_per_parking(EVdata)
    print('max_overlaps=', max_overlaps)
    print('s ==',s)
    model.nCharger = max_overlaps[s]
    


    
    #Price = pd.DataFrame(Price, columns=['Price'])





    data = pyo.DataPortal()
    data.load(filename='iee33_bus_data.dat')
    
    line_data = data['lineData']
    
    #################
    ATT = EVdata['AT']
    DTT = EVdata['DT']
    
    
    plt.subplot(2,1,1)
    plt.hist(ATT, bins=20, color='skyblue', edgecolor='black',label = 'Arrival time')
    plt.legend()
    plt.grid()
    plt.ylabel('Frequency')
    
    plt.xlim(1,48)
    plt.subplot(2,1,2)
    plt.hist(DTT, bins=20, color='red', edgecolor='black', label = 'Departure time')
    plt.xlim(1,48)
    plt.grid()
    plt.legend()
    plt.xlabel('Time sample')
    plt.ylabel('Frequency')
    plt.savefig('Histogram.png', dpi = 300)
    
    plt.show()
    #######################

    
    
    # Export to Excel
    #output_filename = "AlphaSensi_Matrix.xlsx"
    #df_alpha.to_excel(output_filename, index=True)
    
    #print(f"AlphaSensi matrix successfully exported to {output_filename}")
    
    
    M = 50 #Big number
    M2 = 5000 # Big number
    # present value factors
    PFV_Charger = (1 / 365) * ((IR * (1 + IR) ** NYearCh) / (-1 + (1 + IR) ** NYearCh))
    PFV_Rob = (1 / 365) * ((IR * (1 + IR) ** NYearRob) / (-1 + (1 + IR) ** NYearRob))
    
    print(len(EVdata))
    model.HORIZON = SampPerH * 24
    model.nEV = len(EVdata) - 1
    
#    if s == 1 or s == 3:
    model.nMESS = 12
#    elif s == 2:
#        model.nMESS = 15
        
        
    model.RobType = 1 * len(robotCC)
    model.Nodes = pyo.Set(initialize=range(33))  # Buses 0 to 32
    model.T = pyo.Set(initialize=[x + 1 for x in range(model.HORIZON)])
    model.I = pyo.Set(initialize=[x + 1 for x in range(model.nCharger)])
    model.K = pyo.Set(initialize=[x + 1 for x in range(model.nEV)])
    model.J = pyo.Set(initialize=[x + 1 for x in range(model.nMESS)])
    model.KK = pyo.Set(initialize=[x + 1 for x in range(model.RobType)])
    
    
    
    
    #for i in range(33):
    #    for j in range(33):
    #        if AlphaSensi[i,j] != 0:
    #            print(f'AlphaSensi[{i},{j}] = {AlphaSensi[i,j]:.4f}')
    
    
    # x = binary varible for CS, y = binary variable for robot charger, z = binary variable for choosing CS, zz= number of robots

    
    model.x_indices = pyo.Set(dimen=3, initialize=lambda model: (
        (k, i, t)
        for k in model.K
        for i in model.I
        for t in range(EVdata['AT'][k], EVdata['DT'][k] + 1)
    ))
    
    model.y_indices = pyo.Set(dimen=3, initialize=lambda model: (
        (k, j, t)
        for k in model.K
        for j in model.J
        for t in range(EVdata['AT'][k], EVdata['DT'][k] + 1)
    ))
    
    # Then create the variables using these sparse index sets
    model.x = pyo.Var(model.x_indices, within=pyo.Binary)
    model.y = pyo.Var(model.y_indices, within=pyo.Binary)
    
    model.z = pyo.Var(model.I, within=pyo.Binary)
    model.zz = pyo.Var(model.J, within=pyo.Binary)
    
    model.assign = pyo.Var(model.K, model.I, within=pyo.Binary)  # EV-charger assignment
    model.assignRobot = pyo.Var(model.K, model.J, within=pyo.Binary)  # Robot assignment
    
    # u = binary variable to buy either from the grid or from the robots
    model.u = pyo.Var(model.K, within=pyo.Binary)
    model.u_rob = pyo.Var(model.J,  model.T, within=pyo.Binary)
    
    # binary variable to define the type of the robot
    model.u_rob_type = pyo.Var(model.J,  model.KK, within=pyo.Binary)
    
    # Ns = number of chargers, Nrob = number of robots
    model.Ns = pyo.Var( within=pyo.Integers)
    model.Nrob = pyo.Var(within=pyo.Integers)
    
    # P_btot = P_buy_total from the grid to charge the EVs and robots, P_b_EV= Purchased electricity to charge EVS, P_b_rob = Purchased electricity to charge robots
    model.P_btot = pyo.Var( model.T, within=pyo.NonNegativeReals)
    model.P_btotS = pyo.Var(model.T, within=pyo.NonNegativeReals)

    model.P_b_EV = pyo.Var(model.x_indices, within=pyo.NonNegativeReals)
    model.P_b_rob = pyo.Var(model.J, model.T, within=pyo.NonNegativeReals)
    model.Out1_P_b_EV = pyo.Var(model.T, within=pyo.NonNegativeReals)

    model.P_btotBar = pyo.Var(model.T, within=pyo.NonNegativeReals)
    
    # P_ch_EV= charging to EV, P_dch_EV = discharging from the EV, SOC_EV = state of charge of the EV
    model.P_ch_EV = pyo.Var(model.K, model.T, within=pyo.NonNegativeReals)
    model.P_dch_EV = pyo.Var(model.K, model.I, model.T, within=pyo.NonNegativeReals)
    model.SOC_EV = pyo.Var(model.K, model.T, within=pyo.NonNegativeReals)
    model.P_ch_rob = pyo.Var(model.J, model.I, model.T, within=pyo.NonNegativeReals)
    model.P_dch_rob = pyo.Var(model.y_indices, within=pyo.NonNegativeReals)
    model.SOC_rob = pyo.Var(model.J, model.T, within=pyo.NonNegativeReals)
    
    # Capacity of the robot
    model.CapRobot = pyo.Var(model.J, model.KK, within=pyo.NonNegativeReals)
    model.PeakPower = pyo.Var(within=pyo.NonNegativeReals)  # Peak grid power
    model.robot_parking_assignment = pyo.Var(model.J, within=pyo.Binary)
    
    model.assignRobToCh = pyo.Var(model.J, model.I, within=pyo.Binary)  
    model.x_rob = pyo.Var(model.J, model.I, model.T, within=pyo.Binary)  # time occupancy of robot on charger
    
    # Decomposition variables
    model.Alpha = pyo.Var(within=pyo.Reals)  # Subproblem approximation
    model.AlphaDown = pyo.Param(initialize=-100, mutable=True)  # Lower bound
    
    voltage_at_bus = {b: 1.0 for b in model.Nodes}  # All buses start feasible
    
    
    ################ Energy constraints ###########
    def PowerPurchased(model, t):
        ev_power = sum(
            model.P_b_EV[k, i, t] 
            for k in model.K 
            for i in model.I 
            if (k, i, t) in model.x_indices
        )
        
        robot_power = sum(model.P_ch_rob[j, i, t] for j in model.J for i in model.I)
        
        return model.P_btot[t] == (ev_power + robot_power)
    
    model.ConPurchasedPower = pyo.Constraint(model.T, rule=PowerPurchased) 
    
    def Out1_P_b_EV(model, t):
        ev_power = sum(
            model.P_b_EV[k, i, t] 
            for k in model.K 
            for i in model.I 
            if (k, i, t) in model.x_indices
        )
    
        return model.Out1_P_b_EV[t] == ev_power 
    model.ConOut1_P_b_EV = pyo.Constraint(model.T, rule=Out1_P_b_EV)  
   

    
#    model.ConPurchasedPower = pyo.Constraint(model.T, rule=PowerPurchased)
    
    
    def PowerPurchasedLimit(model, t):
        return model.P_btot[t] <= PgridMax
    
    
    model.ConPowerPurchasedLimit = pyo.Constraint(model.T, rule=PowerPurchasedLimit)
    
    
    ##################### Charger assignment constraints ###############
    def NoCharger(model, k, i):
        return model.assign[k, i]  <= model.z[i]   
    model.ConNoCharger1 = pyo.Constraint(model.K, model.I, rule=NoCharger)


    def NoChargerRob(model, j, i):
        return model.assignRobToCh[j,i] <= model.z[i]   
    model.NoChargerRob = pyo.Constraint(model.J, model.I, rule=NoChargerRob)    
    
    def NoCharger2(model):
        return model.Ns == sum(model.z[i] for i in model.I)   
    model.ConNoCharger2 = pyo.Constraint( rule=NoCharger2)
    
    
    def ChargingOptions(model, k):
        return sum(model.assign[k, i] for i in model.I) + sum(model.assignRobot[k, j] for j in model.J) <= 1
    
    
    model.ConChargingOptions = pyo.Constraint(model.K, rule=ChargingOptions)
    
    
    # Each EV assigned to <= 1 charger
    def SingleChargerAssignment(model, k):
        return sum(model.assign[k, i] for i in model.I) <= 1
    
    
    model.ConSingleAssign = pyo.Constraint(model.K,  rule=SingleChargerAssignment)
    
    
    def x_zero(model, k, i, t):
        if t < EVdata['AT'][k] or t > EVdata['DT'][k]:
            return model.x[k, i, t] == 0
        else:
            return pyo.Constraint.Skip  # nothing to enforce outside the relevant time range
    
    
    model.Conx_zero = pyo.Constraint(model.x_indices, rule=x_zero)
    

    
    
    def ChargerSingleEV_(model, i, t):
        """Ensures each charger (i,s) is used by at most one EV at time t"""
        # Find all EVs that could use this charger at this time
        relevant_evs = [
            k for k in model.K
            if EVdata['ParkingNo'][k - 1] == s and  # EV is at this parking
               EVdata['AT'][k] <= t <= EVdata['DT'][k]  # EV is present at time t
        ]
    
        if not relevant_evs:
            # No EVs could use this charger at this time
            return pyo.Constraint.Feasible
    
        # Sum over x variables that actually exist
        sum_x = sum(model.x[k, i, t] for k in relevant_evs if (k, i, t) in model.x)
        return sum_x <= 1
    
    
    # Declare the constraint over all possible (i,s,t) combinations
    model.ConChargerSingleEV_ = pyo.Constraint(
        model.I, model.T,
        rule=ChargerSingleEV_
    )
    
    
    def Link_x_charge(model, k, i, t):
        return model.x[k, i, t] <= model.assign[k, i]
    
    
    model.ConLink_x_charge = pyo.Constraint(model.x_indices, rule=Link_x_charge)
    
    
    # Constraint: If an EV is assigned to a fixed charger, the charger is occupied from AT to DT
    def charger_occupancy(model, k, i):
        """Ensures charger i at parking s is occupied from AT to DT if EV k is assigned"""
        # Only apply if EV is at this parking and AT <= DT
        if  EVdata['AT'][k] > EVdata['DT'][k]:
            return pyo.Constraint.Skip
    
        # Calculate required occupancy duration
        duration = EVdata['DT'][k] - EVdata['AT'][k] + 1
    
        # Sum only existing x variables (sparse-aware)
        occupied_sum = sum(
            model.x[k, i, t]
            for t in range(EVdata['AT'][k], EVdata['DT'][k] + 1)
            if (k, i, t) in model.x  # Check if variable exists
        )
    
        # Big-M constraint reformulated for better numerical stability
        return occupied_sum >= duration * model.assign[k, i] - M * (1 - model.assign[k, i])
    
    
    model.ConChargerOccupancy = pyo.Constraint(
        model.K, model.I, 
        rule=charger_occupancy
    )
    
    
    # Constraint: No other EV can be assigned to the same charger during an occupied period
    def no_overlapping_assignments(model, k1, k2, i):
        """Prevents EV k2 from being assigned to charger i at parking s if it overlaps with EV k1's stay"""
        if k1 != k2:
            # Check if time windows overlap
            overlap_condition = (EVdata['AT'][k1] <= EVdata['DT'][k2]) and (EVdata['AT'][k2] <= EVdata['DT'][k1])
            if overlap_condition:
                return model.assign[k1, i] + model.assign[k2, i] <= 1
        return pyo.Constraint.Skip
    
    
    model.ConNoOverlappingAssignments = pyo.Constraint(model.K, model.K, model.I, rule=no_overlapping_assignments)
    
    
    ###############  Robot assignment constraints
    def robot_single_connection(model, k, j, t):
        """Ensures each robot (j,s) charges at most one EV at any time t"""
        # Since we're using y_indices, we know (k,j,s,t) is valid
        # We need to sum over all EVs that could be served by this robot at this time
        return sum(model.y[k, j, t] for k in model.K
                   if (k, j, t) in model.y_indices) <= NevSame
    
    
    model.ConRobotSingleConnection = pyo.Constraint(model.y_indices, rule=robot_single_connection)
    
    # Create a mapping from (k,s,t) to possible robots
    # First create proper index sets
    model.ev_active_indices = pyo.Set(
        dimen=2,
        initialize=lambda model: [
            (k,  t)
            for k in model.K
            for t in range(EVdata['AT'][k], EVdata['DT'][k] + 1)
        ]
    )
    
    
    def single_robot_connection(model, k, t):
        """Ensures each EV is connected to ≤1 robot at any time"""
        # Get all robots at this parking location
        available_robots = [j for j in model.J
                            if (k, j, t) in model.y_indices]
    
        return sum(model.y[k, j, t] for j in available_robots) <= 1
    
    
    model.ConSingleRobotConnection = pyo.Constraint(
        model.ev_active_indices,
        rule=single_robot_connection
    )
    
    
    def Link_y_charge(model, k, j, t):
        return model.y[k, j, t] <= model.assignRobot[k, j]
    
    
    model.ConLink_y_charge = pyo.Constraint(model.y_indices, rule=Link_y_charge)
    
    
    ########## charging constraints###################
    
    def Charging_toEV(model, k, t):
        robot_contrib = sum(
            model.P_dch_rob[k,j,t] 
            for j in model.J 
             if (k,j, t) in model.y_indices
        )
        
        grid_contrib = sum(
            model.P_b_EV[k,i,t] 
            for i in model.I 
             if (k,i, t) in model.x_indices
        )
        
        
        
        
        
        return model.P_ch_EV[k,t] == grid_contrib + robot_contrib
    
    model.ConCharging_toEV = pyo.Constraint(model.K, model.T, rule=Charging_toEV)
    
    
    def Charging_UpLimit(model, k, i, t):
        return model.P_b_EV[k,i,t]  <= ChargerCap
    
    
    model.ConCharging_UpLimit = pyo.Constraint(model.x_indices, rule=Charging_UpLimit)
    
    
    def SOC_EV_f1(model, k, t):
        if t < EVdata['AT'][k]:
            return model.SOC_EV[k, t] == 0
        elif t == EVdata['AT'][k]:
            return model.SOC_EV[k, t] == EVdata['SOCin'][k] * EVdata['EVcap'][k]
        elif t > EVdata['AT'][k] and t <= EVdata['DT'][k]:
            return model.SOC_EV[k, t] == model.SOC_EV[k, t - 1] + (1 / SampPerH) * model.P_ch_EV[k, t]
        else:
            return pyo.Constraint.Skip  # nothing to enforce outside the relevant time range
    
    
    def SOC_EV_f2(model, k, t):
        if t == EVdata['DT'][k]:
            return model.SOC_EV[k, t] == 1 * EVdata['SOCout'][k] * EVdata['EVcap'][k]
        else:
            return pyo.Constraint.Skip  # nothing to enforce outside the relevant time range
    
    
    model.ConSOC_EV_f1 = pyo.Constraint(model.K, model.T, rule=SOC_EV_f1)
    model.ConSOC_EV_f2 = pyo.Constraint(model.K, model.T, rule=SOC_EV_f2)
    
    
    def SOC_Charge_limit1(model, k, i, t):
        return model.P_b_EV[k, i,  t] <= EVdata['EVcap'][k] * model.assign[k, i]
    model.ConSOC_Charge_limit1 = pyo.Constraint(model.x_indices, rule=SOC_Charge_limit1)

    
    def SOC_Charge_limit2(model, k, i, t):
        return model.P_b_EV[k, i, t] <= EVdata['EVcap'][k] * model.x[k, i, t]
    
    
    model.ConSOC_Charge_limit2 = pyo.Constraint(model.x_indices, rule=SOC_Charge_limit2)
    
    
    def SOC_Limit(model, k, t):
        return model.SOC_EV[k, t] <= EVdata['EVcap'][k]
    
    
    model.ConSOC_Limit = pyo.Constraint(model.K, model.T, rule=SOC_Limit)
    
    
    ############## Robot charging constraints #####################
    
    
    def Ch_robot_limit(model, j,  t):
        return sum(model.P_ch_rob[j, i, t] for i in model.I) <= model.u_rob[j, t] *  (1)*ChargerCap
    model.ConCh_robot = pyo.Constraint(model.J, model.T, rule=Ch_robot_limit)
    
    
    def Dch_robot_limit1(model, j, t):
        active_discharges = sum(
            model.P_dch_rob[k,j, t] 
            for k in model.K 
            if (k,j, t) in model.y_indices  # Only sum existing variables
        )
        return active_discharges <= (1-model.u_rob[j,t])*NevSame*DCchargerCap
    model.ConDch_robot1 = pyo.Constraint(model.J,  model.T, rule=Dch_robot_limit1)
    
    
    
    
    def Dch_robot_limit2(model, k, j, t):
            return model.P_dch_rob[k, j, t] <= 1*DCchargerCap * model.y[k, j, t]
    model.Dch_robot_limit2 = pyo.Constraint(model.y_indices, rule=Dch_robot_limit2)
    
    
    

    
    
    def Dch_robot_limit3(model, k, j, t):
        return model.P_dch_rob[k, j, t] <= sum(model.CapRobot[j, kk] for kk in model.KK)
    model.Dch_robot_limit3 = pyo.Constraint(model.y_indices, rule=Dch_robot_limit3)
    
    
    def SOC_Robot(model, j,  t):
        if t == 1:
            return model.SOC_rob[j,t] == 0.2*sum(model.CapRobot[j,kk] for kk in model.KK)
        else:
            active_discharges = sum(
                model.P_dch_rob[k,j,t] 
                for k in model.K 
                if (k,j,t) in model.y_indices
            )
            return model.SOC_rob[j, t] == model.SOC_rob[j,t-1] + (1/SampPerH)*sum(model.P_ch_rob[j, i, t] for i in model.I) - (1/SampPerH)*active_discharges
    model.ConSOC_Robot = pyo.Constraint(model.J, model.T, rule=SOC_Robot)
    
    
    def SOC_Robot2(model, j, t):
        return model.SOC_rob[j, t] >= 0.2 * sum(model.CapRobot[j, kk] for kk in model.KK)
    
    
    model.ConSOC_Robot2 = pyo.Constraint(model.J, model.T, rule=SOC_Robot2)
    
    
    def SOC_Robot_limit(model, j, t):
        return model.SOC_rob[j, t] <= sum(model.CapRobot[j, kk] for kk in model.KK)
    
    
    model.ConSOC_Robot_limit = pyo.Constraint(model.J,  model.T, rule=SOC_Robot_limit)
    
    

    
    
    def Ch_Robot_limit3(model, j, t):
        return sum(model.P_dch_rob[k, j, t] for k in model.K) <= (NevSame)*DCchargerCap
    
    
    #model.ConCh_Robot_limit3 = pyo.Constraint(model.J, model.S, model.T, rule= Ch_Robot_limit3 )
    
    def RobotCapLimit4(model, j, kk):
        return model.CapRobot[j, kk] <= RobotTypes[kk - 1] * model.u_rob_type[j, kk]
    
    
    model.ConRobotCapLimit4 = pyo.Constraint(model.J, model.KK, rule=RobotCapLimit4)
    
    
    def RobotCapLimit2(model, j, kk):
        return sum(model.u_rob_type[j, kk] for kk in model.KK) <= 1
    
    
    model.ConRobotCapLimit2 = pyo.Constraint(model.J, model.KK, rule=RobotCapLimit2)
    
    
    
    def RobotTotNum(model, j, kk):
        return sum(model.u_rob_type[j,  kk] for kk in model.KK for j in model.J) <= MaxRobot
    #model.ConRobotTotNum = pyo.Constraint(model.J, model.S, model.KK, rule=RobotTotNum)
    
    def Dch_rob_zero(model, k, j, t):
        if t < EVdata['AT'][k] or t > EVdata['DT'][k]:
            return model.P_dch_rob[k, j, t] == 0
        else:
            return pyo.Constraint.Skip  # nothing to enforce outside the relevant time range
    
    
    #model.ConDch_rob_zero = pyo.Constraint(model.K, model.J, model.S, model.T, rule=Dch_rob_zero)
    
    ################## Robot to charger
    def Link_x_rob(model, j, i, t):
        return model.x_rob[j, i, t] <= model.assignRobToCh[j, i]
    model.ConLink_x_rob = pyo.Constraint(model.J, model.I, model.T, rule=Link_x_rob)

    def ChargerSingleUse2(model, i, t):
        ev_load = sum(model.x[k, i, t] for k in model.K if (k, i, t) in model.x_indices)
        rob_load = sum(model.x_rob[j, i, t] for j in model.J)
        return ev_load + rob_load <= 1
    model.ConChargerSingleUse2 = pyo.Constraint(model.I, model.T, rule=ChargerSingleUse2)

    def ChargerOneRobot(model, i, t):
        return sum(model.x_rob[j, i, t] for j in model.J) <= 1
    model.ConChargerOneRobot = pyo.Constraint(model.I, model.T, rule=ChargerOneRobot)
    
    
    
    def Ch_robot_limit4(model, j, i, t):
        return model.P_ch_rob[j, i, t] <= model.x_rob[j, i, t] *  (1)*ChargerCap
    model.ConCh_robot4 = pyo.Constraint(model.J, model.I, model.T, rule=Ch_robot_limit4)



    ##################### PARKING CONSTRAINTS ##################
    
    
    
    
    def PeakPowerConstraint(model, t):
        return model.PeakPower >= model.P_btot[t]               
    model.ConPeakPower = pyo.Constraint( model.T, rule=PeakPowerConstraint)
    
 
    def PTotalS(model, t):
        return model.P_btotS[t] == model.P_btot[t]               
    #model.ConPTotalS = pyo.Constraint( model.S, model.T, rule=PTotalS)

    
    def AlphaFun(model):
        return model.Alpha >= model.AlphaDown
        #return model.Alpha[s] >= -100
    
    model.ConAlphaFun = pyo.Constraint( rule=AlphaFun)
    
    
    ######################### TO CONSIDER BESS ##################
    def NoCharger3(model):
        return  model.Ns >= max_overlaps[s] - 1 
    #model.ConNoCharger3 = pyo.Constraint(rule = NoCharger3)
    
    ############## OBJECTIVE FUNCTION ##################
    
    model.obj = pyo.Objective(expr=(1) * (PFV_Charger * model.Ns * Ch_cost ) +
                                   (1) * PFV_Rob * sum(
        model.u_rob_type[j, kk] * robotCC[kk - 1] for j in model.J  for kk in model.KK) +
                                   (1/SampPerH)*sum(Price.iloc[t - 1] * (0.001) * model.P_btot[ t]  for t in model.T) +
                                   (1 / 30) * PeakPrice * model.PeakPower
                                    + 1*(model.Alpha), sense=pyo.minimize)
    
    #####################################################
    
    #####################
    
    
    # model.cuts = pyo.Constraint(model.Nodes, rule=voltage_feasibility_cut)
    model.cuts = pyo.ConstraintList()  # THIS IS CRUCIAL
    return model
    
   
    
   
 ####################################################################################################################################################################################################
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
##########  ONLY FIXED CHARGER 555555555555555555555
def build_masterOnlyFC(s, parking_data, parking_to_bus, SampPerH, Ch_cost, robotCC, Pattern, Price):
    [parking_to_bus, ChargerCap, SampPerH, Vmin, Ch_cost, nChmax, PgridMax, NYearCh, NYearRob, RobotTypes, robotCC, IR, DCchargerCap, PeakPrice, MaxRobot, NevSame] = GlobalData()

    modelFC = pyo.ConcreteModel()

    
    EVdata = parking_data[parking_data['ParkingNo'] == s].reset_index(drop=True)
     
    # Calculate and print results
    max_overlaps = max_overlaps_per_parking(EVdata)
    print('max_overlaps=', max_overlaps)
    print('s ==',s)
    modelFC.nCharger = max_overlaps[s]
    


    
    #Price = pd.DataFrame(Price, columns=['Price'])





    data = pyo.DataPortal()
    data.load(filename='iee33_bus_data.dat')
    
    line_data = data['lineData']
    
    #################
    ATT = EVdata['AT']
    DTT = EVdata['DT']
    
    
    plt.subplot(2,1,1)
    plt.hist(ATT, bins=20, color='skyblue', edgecolor='black',label = 'Arrival time')
    plt.legend()
    plt.grid()
    plt.ylabel('Frequency')
    
    plt.xlim(1,48)
    plt.subplot(2,1,2)
    plt.hist(DTT, bins=20, color='red', edgecolor='black', label = 'Departure time')
    plt.xlim(1,48)
    plt.grid()
    plt.legend()
    plt.xlabel('Time sample')
    plt.ylabel('Frequency')
    plt.savefig('Histogram.png', dpi = 300)
    
    plt.show()
    # -*- coding: utf-8 -*-
    data = pyo.DataPortal()
    data.load(filename='iee33_bus_data.dat')
    line_data = data['lineData']
    M = 50 #Big number
    M2 = 5000 # Big number
    # present value factors
    PFV_Charger = (1 / 365) * ((IR * (1 + IR) ** NYearCh) / (-1 + (1 + IR) ** NYearCh))
    print(len(EVdata))
    modelFC.HORIZON = SampPerH * 24
    modelFC.nEV = len(EVdata) - 1
    modelFC.Nodes = pyo.Set(initialize=range(33)) # Buses 0 to 32
    modelFC.T = pyo.Set(initialize=[x + 1 for x in range(modelFC.HORIZON)])
    modelFC.I = pyo.Set(initialize=[x + 1 for x in range(modelFC.nCharger)])
    modelFC.K = pyo.Set(initialize=[x + 1 for x in range(modelFC.nEV)])
    
    # x = binary varible for CS, y = binary variable for robot charger, z = binary variable for choosing CS, zz= number of robots
    modelFC.x_indices = pyo.Set(dimen=3, initialize=lambda modelFC: (
    (k, i, t)
    for k in modelFC.K
    for i in modelFC.I
    for t in range(EVdata['AT'][k], EVdata['DT'][k] + 1)
    ))
    # Then create the variables using these sparse index sets
    modelFC.x = pyo.Var(modelFC.x_indices, within=pyo.Binary)
    modelFC.z = pyo.Var(modelFC.I,  within=pyo.Binary)
    modelFC.assign = pyo.Var(modelFC.K, modelFC.I,  within=pyo.Binary) # EV-charger assignment
    # u = binary variable to buy either from the grid or from the robots
    modelFC.u = pyo.Var(modelFC.K, within=pyo.Binary)
    modelFC.P_btotBar = pyo.Var( modelFC.T, within=pyo.NonNegativeReals)
    # Ns = number of chargers, Nrob = number of robots
    modelFC.Ns = pyo.Var( within=pyo.Integers)
    # P_btot = P_buy_total from the grid to charge the EVs and robots, P_b_EV= Purchased electricity to charge EVS, P_b_rob = Purchased electricity to charge robots
    modelFC.P_btot = pyo.Var( modelFC.T, within=pyo.NonNegativeReals)
    modelFC.P_b_EV = pyo.Var(modelFC.K, modelFC.I,  modelFC.T, within=pyo.NonNegativeReals)
    # P_ch_EV= charging to EV, P_dch_EV = discharging from the EV, SOC_EV = state of charge of the EV
    modelFC.P_ch_EV = pyo.Var(modelFC.K, modelFC.T, within=pyo.NonNegativeReals)
    modelFC.P_dch_EV = pyo.Var(modelFC.K, modelFC.I, modelFC.T, within=pyo.NonNegativeReals)
    modelFC.SOC_EV = pyo.Var(modelFC.K, modelFC.T, within=pyo.NonNegativeReals)
    # Capacity of the robot
    modelFC.PeakPower = pyo.Var( within=pyo.NonNegativeReals) # Peak grid power
    modelFC.Alpha = pyo.Var(within=pyo.Reals)  # Subproblem approximation
    modelFC.AlphaDown = pyo.Param(initialize=-100, mutable=True)  # Lower bound
    voltage_at_bus = {b: 1.0 for b in modelFC.Nodes} # All buses start feasible
    
    
    
    ################ Energy constraints ###########
    def PowerPurchased(modelFC, t):
        return modelFC.P_btot[ t] == (
        sum(modelFC.P_b_EV[k, i, t] for k in modelFC.K for i in modelFC.I) 
    )
    modelFC.ConPurchasedPower = pyo.Constraint( modelFC.T, rule=PowerPurchased)
    
    def PowerPurchasedLimit(modelFC, t):
        return modelFC.P_btot[ t] <= PgridMax
    modelFC.ConPowerPurchasedLimit = pyo.Constraint( modelFC.T, rule=PowerPurchasedLimit)
    
    ##################### Charger assignment constraints ###############
    def NoCharger(modelFC, k, i):
        return modelFC.assign[k, i] <= modelFC.z[i]
    modelFC.ConNoCharger1 = pyo.Constraint(modelFC.K, modelFC.I,  rule=NoCharger)
    
    def NoCharger2(modelFC):
        return modelFC.Ns == sum(modelFC.z[i] for i in modelFC.I)
    modelFC.ConNoCharger2 = pyo.Constraint( rule=NoCharger2)
    # Each EV assigned to <= 1 charger
    
    def SingleChargerAssignment(modelFC, k):
        return sum(modelFC.assign[k, i] for i in modelFC.I) <= 1
    modelFC.ConSingleAssign = pyo.Constraint(modelFC.K,  rule=SingleChargerAssignment)
    
    def x_zero(modelFC, k, i, t):
        if t < EVdata['AT'][k] or t > EVdata['DT'][k]:
            return modelFC.x[k, i, t] == 0
        else:
            return pyo.Constraint.Skip # nothing to enforce outside the relevant time range
    modelFC.Conx_zero = pyo.Constraint(modelFC.x_indices, rule=x_zero)
 
    def ChargerSingleEV_(modelFC, i, t):
        """Ensures each charger (i,s) is used by at most one EV at time t"""
        # Find all EVs that could use this charger at this time
        relevant_evs = [
            k for k in modelFC.K
            if EVdata['ParkingNo'][k - 1] == s and  # EV is at this parking
               EVdata['AT'][k] <= t <= EVdata['DT'][k]  # EV is present at time t
        ]
    
        if not relevant_evs:
            # No EVs could use this charger at this time
            return pyo.Constraint.Feasible
    
        # Sum over x variables that actually exist
        sum_x = sum(modelFC.x[k, i, t] for k in relevant_evs if (k, i, t) in modelFC.x)
        return sum_x <= 1
    
    
    # Declare the constraint over all possible (i,s,t) combinations
    modelFC.ConChargerSingleEV_ = pyo.Constraint(
        modelFC.I, modelFC.T,
        rule=ChargerSingleEV_
    )
    def Link_x_charge(modelFC, k, i, t):
        return modelFC.x[k, i, t] <= modelFC.assign[k, i]
    modelFC.ConLink_x_charge = pyo.Constraint(modelFC.x_indices, rule=Link_x_charge)
    # Constraint: If an EV is assigned to a fixed charger, the charger is occupied from AT to DT
    
    def charger_occupancy(modelFC, k, i):
        """Ensures charger i at parking s is occupied from AT to DT if EV k is assigned"""
        # Only apply if EV is at this parking and AT <= DT
        if  EVdata['AT'][k] > EVdata['DT'][k]:
            return pyo.Constraint.Skip
    
        # Calculate required occupancy duration
        duration = EVdata['DT'][k] - EVdata['AT'][k] + 1
    
        # Sum only existing x variables (sparse-aware)
        occupied_sum = sum(
            modelFC.x[k, i, t]
            for t in range(EVdata['AT'][k], EVdata['DT'][k] + 1)
            if (k, i, t) in modelFC.x  # Check if variable exists
        )
    
        # Big-M constraint reformulated for better numerical stability
        return occupied_sum >= duration * modelFC.assign[k, i] - M * (1 - modelFC.assign[k, i])
    
    
    modelFC.ConChargerOccupancy = pyo.Constraint(
        modelFC.K, modelFC.I, 
        rule=charger_occupancy
    )
    
    
    # Constraint: No other EV can be assigned to the same charger during an occupied period
    def no_overlapping_assignments(modelFC, k1, k2, i):
        """Prevents EV k2 from being assigned to charger i at parking s if it overlaps with EV k1's stay"""
        if k1 != k2:
            # Check if time windows overlap
            overlap_condition = (EVdata['AT'][k1] <= EVdata['DT'][k2]) and (EVdata['AT'][k2] <= EVdata['DT'][k1])
            if overlap_condition:
                return modelFC.assign[k1, i] + modelFC.assign[k2, i] <= 1
        return pyo.Constraint.Skip
    
    
    modelFC.ConNoOverlappingAssignments = pyo.Constraint(modelFC.K, modelFC.K, modelFC.I, rule=no_overlapping_assignments)
    
    
    ############### Robot assignment constraints
    # Create a mapping from (k,s,t) to possible robots
    # First create proper index sets
    modelFC.ev_active_indices = pyo.Set(
    dimen=3,
    initialize=lambda modelFC: [
    (k, EVdata['ParkingNo'][k - 1], t)
    for k in modelFC.K
    for t in range(EVdata['AT'][k], EVdata['DT'][k] + 1)
    ]
    )
    ########## charging constraints###################
    def Charging_toEV(modelFC, k, t):
        return modelFC.P_ch_EV[k,t] == sum(modelFC.P_b_EV[k, i, t] for i in modelFC.I) 
    modelFC.ConCharging_toEV = pyo.Constraint(modelFC.K, modelFC.T, rule=Charging_toEV)
  
    def Charging_UpLimit(modelFC, k, t):
        return modelFC.P_ch_EV[k, t] <= ChargerCap
    modelFC.ConCharging_UpLimit = pyo.Constraint(modelFC.K, modelFC.T, rule=Charging_UpLimit)
    
    def SOC_EV_f1(modelFC, k, t):
        if t < EVdata['AT'][k]:
            return modelFC.SOC_EV[k, t] == 0
        elif t == EVdata['AT'][k]:
            return modelFC.SOC_EV[k, t] == EVdata['SOCin'][k] * EVdata['EVcap'][k]
        elif t > EVdata['AT'][k] and t <= EVdata['DT'][k]:
            return modelFC.SOC_EV[k, t] == modelFC.SOC_EV[k, t - 1] + (1 / SampPerH) * modelFC.P_ch_EV[k, t]
        else:
            return pyo.Constraint.Skip # nothing to enforce outside the relevant time range
    def SOC_EV_f2(modelFC, k, t):
        if t == EVdata['DT'][k]:
            return modelFC.SOC_EV[k, t] == 1 * EVdata['SOCout'][k] * EVdata['EVcap'][k]
        else:
            return pyo.Constraint.Skip # nothing to enforce outside the relevant time range
    modelFC.ConSOC_EV_f1 = pyo.Constraint(modelFC.K, modelFC.T, rule=SOC_EV_f1)
    modelFC.ConSOC_EV_f2 = pyo.Constraint(modelFC.K, modelFC.T, rule=SOC_EV_f2)
   
    def SOC_Charge_limit1(modelFC, k, i, t):
        return modelFC.P_b_EV[k, i, t] <= EVdata['EVcap'][k] * modelFC.assign[k, i]
  
    
    def SOC_Charge_limit2(modelFC, k, i, t):
        return modelFC.P_b_EV[k, i, t] <= EVdata['EVcap'][k] * modelFC.x[k, i, t]
    modelFC.ConSOC_Charge_limit1 = pyo.Constraint(modelFC.K, modelFC.I,  modelFC.T, rule=SOC_Charge_limit1)
    modelFC.ConSOC_Charge_limit2 = pyo.Constraint(modelFC.x_indices, rule=SOC_Charge_limit2)
   
    def SOC_Limit(modelFC, k, t):
        return modelFC.SOC_EV[k, t] <= EVdata['EVcap'][k]
    modelFC.ConSOC_Limit = pyo.Constraint(modelFC.K, modelFC.T, rule=SOC_Limit)
    ############## Robot to Charger  #####################
    
  
    
    
    
    
    
    
    ##################### PARKING CONSTRAINTS ##################
 
    
    def PeakPowerConstraint(modelFC, t):
        return modelFC.PeakPower >= modelFC.P_btot[t]
    modelFC.ConPeakPower = pyo.Constraint( modelFC.T, rule=PeakPowerConstraint)
    
    def AlphaFun(modelFC):
        return modelFC.Alpha >= modelFC.AlphaDown
        #return model.Alpha[s] >= -100
    
    modelFC.ConAlphaFun = pyo.Constraint( rule=AlphaFun)

    ############## OBJECTIVE FUNCTION ##################
    modelFC.obj = pyo.Objective(expr=(1) * (PFV_Charger * modelFC.Ns * Ch_cost) +
    (1/SampPerH)*sum(Price.iloc[t - 1] * (0.001) * modelFC.P_btot[t] for t in modelFC.T) +
    (1 / 30) * PeakPrice *modelFC.PeakPower + 1*(modelFC.Alpha) , sense=pyo.minimize)
    
    
    modelFC.cuts = pyo.ConstraintList()  # THIS IS CRUCIAL
    return modelFC
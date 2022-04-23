import os
import model as m
import optimize as opt

model = m.Model ( 
    filepath = os.path.join(os.getcwd(), 'Simulation 5.bkp'), 
    N = 101,
    RR = 0.924,
    tray_spacing = 0.63636,
    # Tray Type: SIEVE, CAPS
    tray_type="CAPS",
    tray_eff_1 = 1.0,
    tray_eff_2 = 1.0,
    feed_stage = 51,
    P_cond = 1.013,
    main_component = "BENZENE",
    hydraulics = False
)

model.run()
print (model.TAC)


import conversions

model.update_manipulated(
    P_cond = 1.013, 
    P_drop_1 = 0.06,
    P_drop_2 = 0.06,
    RR = 0.9002, 
    N = 50, 
    feed_stage = 35, 
    tray_spacing = 0.6364, 
    tray_type = "SIEVE",
    hydraulics = False
)
model.run()
tac = model.TAC
diameter = model.diameter
Q_cond = conversions.calPerSec_to_kJPerSec(abs(model.Q_cond))
Q_reb = conversions.calPerSec_to_kJPerSec(abs(model.Q_reb))
energy_cost = model.calc_energy_cost("hp" if model.T_stage[-2] > 150 else "lp")
capital_cost = (model.TAC - energy_cost)

print ("TAC: %f, Diameter: %f, Q_cond: %f, Q_reb: %f, energy: %f, capital: %f"%(tac, diameter, Q_cond, Q_reb, energy_cost, capital_cost))

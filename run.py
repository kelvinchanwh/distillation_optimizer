import os
import model as m

model = m.Model ( 
    filepath = os.path.join(os.getcwd(), 'Simulation 1.bkp'), 
    components = ["BENZENE", "TOLUENE"], 
    z_feed = [70, 30], # % 
    T_feed = 300, # K
    P_feed = 1.12, # bar
    F = 100, # kmol/hr
    calculation_type = 'EQUILIBRIUM', 
    N = 36,
    condenser_type = 'TOTAL', 
    reboiler_type = 'KETTLE',
    RR = 0.924, 
    D = 63.636, 
    feed_stage = 23, 
    P_cond = 1.12, #bar 
    P_drop = 0,
)

model.run()
print (model.z_feed_out)
import os
import model as m

model = m.Model ( 
    filepath = os.path.join(os.getcwd(), 'Simulation 1.bkp'), 
    components = ["BENZENE", "TOLUENE"], 
    N = 36,
    RR = 0.924,
    tray_spacing = 0.63636,
    feed_stage = 23,
    P_cond = 1.12,
    P_drop_1 = 0.1, 
    P_drop_2 = 0.2
)

model.run()
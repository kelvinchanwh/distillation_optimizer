import os
import model as m

model = m.Model ( 
    filepath = os.path.join(os.getcwd(), 'Simulation 1.bkp'), 
    components = ["BENZENE", "TOLUENE"], 
    N = 36,
    RR = 0.924,
    feed_stage = 23, 
    P_cond = 1.12, #bar 
    P_drop = 0,
)

model.run()
print (model.z_feed_out)
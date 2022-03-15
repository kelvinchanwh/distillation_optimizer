import os
import model as m

model = m.Model ( 
    filepath = os.path.join(os.getcwd(), 'Simulation 2.bkp'), 
    N = 36,
    RR = 0.924,
    tray_spacing = 0.63636,
    feed_stage = 23,
    P_cond = 1.12,
)

print (model.run())
# model.obj.Close()
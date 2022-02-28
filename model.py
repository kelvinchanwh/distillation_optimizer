import os
import win32com.client as win32

class Model:
    def __init__(self, filepath, components, F, P, P_drop, z_feed, E, RR, D, N, feed_stage):
        self.filepath = filepath
        self.components = components
        self.F = F
        self.P = P
        self.P_drop = P_drop
        self.z_feed = z_feed
        self.E = E
        self.RR = RR
        self.D = D
        self.N = N
        self.feed_stage = feed_stage
    
    def set_parameters(self, components, F, P, P_drop, z_feed, E, RR, D, N, feed_stage):
        self.components = components
        self.F = F
        self.P = P
        self.P_drop = P_drop
        self.z_feed = z_feed
        self.E = E
        self.RR = RR
        self.D = D
        self.N = N
        self.feed_stage = feed_stage

    def run(self):
        # Create COM object
        self.obj = win32.Dispatch("Apwn.Document")
        self.obj.InitFromArchive2(self.filepath)

        # Set input parameters
        self.obj.SetParameter("F", self.F)
        self.obj.SetParameter("P", self.P)
        self.obj.SetParameter("P_drop", self.P_drop)
        self.obj.SetParameter("z_feed", self.z_feed)
        self.obj.SetParameter("E", self.E)
        self.obj.SetParameter("RR", self.RR)
        self.obj.SetParameter("D", self.D)
        self.obj.SetParameter("N", self.N)
        self.obj.SetParameter("feed_stage", self.feed_stage)

        # Run model
        self.obj.Run()
        
        # Get output parameters
        self.z_feed_out = self.obj.GetParameter("z_feed")
        self.z_feed_out = [round(i, 3) for i in self.z_feed_out]
        self.z_feed_out = [str(i) for i in self.z_feed_out]
        self.z_feed_out = ','.join(self.z_feed_out)
        self.z_feed_out = '[' + self.z_feed_out + ']'
        self.z_feed_out = eval(self.z_feed_out)
        self.z_feed_out
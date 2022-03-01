import os
import win32com.client as win32

class Model:
    def __init__(self, filepath, components, z_feed, T = 300, P = 1., F = 100, calculation_type = 'EQUILIBRIUM', N = 36, \
        condenser_type = 'TOTAL', reboiler_type = 'KETTLE', RR = 1.0, D = 63.636, feed_stage = 23, P_cond = 1.0, P_drop = 0):
        """
        :param filepath: path to the model file
        :param base_method: base method for the model (e.g. 'IDEAL','PENG-ROB',...)
        :param components: list of component names
        :param z_feed: mole fractions of each component, ordered [%]
        :param T: feed temperature [K]
        :param P: pressure, [bar]
        :param F: feed molar flow rate [kmol/hr]
        :param calculation_type: 'EQUILIBRIUM' or 'RIG-RATE'
        :param N: number of stages
        :param condenser_type: 'TOTAL' or 'PARTIAL-V' or 'PARTIAL-V-L' or 'NONE'
        :param reboiler_type: 'KETTLE' or 'THERMOSYPHON' or 'NONE'
        
        :param RR: reflux ratio (L/D)
        :param D: distillate molar flow rate [kmol/hr]
        
        :param feed_stage: stage number of the input feed [on-stage]
        
        :param P_cond: condenser pressure [bar]
        :param P_drop: pressure drop per stage, [bar]
        """
        self.filepath = filepath
        self.components = components
        self.z_feed = z_feed
        self.T = T
        self.P = P
        self.F = F
        self.calculation_type = calculation_type
        self.N = N
        self.condenser_type = condenser_type
        self.reboiler_type = reboiler_type
        self.RR = RR
        self.D = D
        self.feed_stage = feed_stage
        self.P_cond = P_cond
        self.P_drop = P_drop

        # Create COM object
        self.obj = win32.Dispatch("Apwn.Document")
        self.obj.InitFromArchive2(self.filepath)
        
    
    def set_parameters(self, filepath, components, z_feed, T, P, F, calculation_type, N, \
        condenser_type, reboiler_type, RR, D, feed_stage, P_cond, P_drop):
        self.filepath = filepath
        self.components = components
        self.z_feed = z_feed
        self.T = T
        self.P = P
        self.F = F
        self.calculation_type = calculation_type
        self.N = N
        self.condenser_type = condenser_type
        self.reboiler_type = reboiler_type
        self.RR = RR
        self.D = D
        self.feed_stage = feed_stage
        self.P_cond = P_cond
        self.P_drop = P_drop
    
    def set_raw(self, path, value):
        self.obj.Tree.FindNode(path).Value = value

    def get_raw(self, path):
        return self.obj.Tree.FindNode(path).value

    def run(self):
        # Set input parameters
        # Input Stream (Stream 1)
        self.obj.Tree.FindNode("\Data\Streams\1\Input\TEMP\MIXED").Value = self.T
        self.obj.Tree.FindNode("\Data\Streams\1\Input\PRES\MIXED").Value = self.P
        self.obj.Tree.FindNode("\Data\Streams\1\Input\TOTFLOW\MIXED").Value = self.F
        assert self.z_feed.sum() == 100 # mole fractions must sum to 100%
        for component in self.components:
            self.obj.Tree.FindNode("\Data\Streams\1\Input\FLOW\MIXED\%s"%component.upper()).Value = self.z_feed[self.components.index(component)]

        # Column
        self.obj.Tree.FindNode("\Data\Blocks\B1\Input\CALC_MODE").Value = self.calculation_type
        self.obj.Tree.FindNode("\Data\Blocks\B1\Input\NSTAGE").Value = self.N
        self.obj.Tree.FindNode("\Data\Blocks\B1\Input\CONDENSER").Value = self.condenser_type
        self.obj.Tree.FindNode("\Data\Blocks\B1\Input\REBOILER").Value = self.reboiler_type
        self.obj.Tree.FindNode("\Data\Blocks\B1\Input\BASIS_D").Value = self.D
        self.obj.Tree.FindNode("\Data\Blocks\B1\Input\BASIS_RR").Value = self.RR
        self.obj.Tree.FindNode("\Data\Blocks\B1\Input\FEED_STAGE\1").Value = self.feed_stage
        self.obj.Tree.FindNode("\Data\Blocks\B1\Input\PRES1").Value = self.P_cond
        self.obj.Tree.FindNode("\Data\Blocks\B1\Input\DP_STAGE").Value = self.P_drop

        # Run model
        self.obj.Run2()
        
        # Get output parameters
        self.z_feed_out = self.obj.GetParameter("z_feed")
        self.z_feed_out = [round(i, 3) for i in self.z_feed_out]
        self.z_feed_out = [str(i) for i in self.z_feed_out]
        self.z_feed_out = ','.join(self.z_feed_out)
        self.z_feed_out = '[' + self.z_feed_out + ']'
        self.z_feed_out = eval(self.z_feed_out)
        self.z_feed_out
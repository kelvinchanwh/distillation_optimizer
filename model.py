import os
import win32com.client as win32

class Model:
    def __init__(self, filepath, components, z_feed, T_feed = 300, P_feed = 1., F = 100, D = 63.636, \
        P_cond = 1.0, P_drop = 0, RR = 1.0, N = 36, feed_stage = 23, \
        calculation_type = 'EQUILIBRIUM', condenser_type = 'TOTAL', reboiler_type = 'KETTLE'):
        """
        Design Parameters
        :param filepath: path to the model file
        :param components: list of component names
        :param z_feed: mole fractions of each component, ordered [%]
        :param T_feed: feed temperature [K]
        :param P_feed: feed pressure, [bar]
        :param F: feed molar flow rate [kmol/hr]
        :param D: distillate molar flow rate [kmol/hr]

        Manipulated Variables
        :param P_cond: condenser pressure [bar]
        :param P_drop: pressure drop per stage, [bar]
        :param RR: reflux ratio (L/D)
        :param N: number of stages
        :param feed_stage: stage number of the input feed [on-stage]

        Model Parameters
        :param calculation_type: 'EQUILIBRIUM' or 'RIG-RATE'
        :param condenser_type: 'TOTAL' or 'PARTIAL-V' or 'PARTIAL-V-L' or 'NONE'
        :param reboiler_type: 'KETTLE' or 'THERMOSYPHON' or 'NONE'
        """

        self.filepath = filepath
        self.components = components
        self.z_feed = z_feed
        self.T_feed = T_feed
        self.P_feed = P_feed
        self.F = F
        self.D = D

        self.P_cond = P_cond
        self.P_drop = P_drop
        self.RR = RR
        self.N = N
        self.feed_stage = feed_stage

        self.calculation_type = calculation_type
        self.condenser_type = condenser_type
        self.reboiler_type = reboiler_type

        # Create COM object
        self.obj = win32.Dispatch("Apwn.Document")
        self.obj.InitFromArchive2(self.filepath)
        
    
    def set_parameters(self, filepath, components, z_feed, T_feed, P_feed, F, D, \
        P_cond = 1.0, P_drop = 0, RR = 1.0, N = 36, feed_stage = 23, \
        calculation_type = 'EQUILIBRIUM', condenser_type = 'TOTAL', reboiler_type = 'KETTLE'):

        self.filepath = filepath
        self.components = components
        self.z_feed = z_feed
        self.T_feed = T_feed
        self.P_feed = P_feed
        self.F = F
        self.D = D

        self.P_cond = P_cond
        self.P_drop = P_drop
        self.RR = RR
        self.N = N
        self.feed_stage = feed_stage

        self.calculation_type = calculation_type
        self.condenser_type = condenser_type
        self.reboiler_type = reboiler_type

    def update_manipulated(self, P_cond = None, P_drop = None, RR = None, N = None, feed_stage = None):
        if P_cond is not None:
            self.P_cond = P_cond
        if P_drop is not None:
            self.P_drop = P_drop
        if RR is not None:
            self.RR = RR
        if N is not None:
            self.N = N
        if feed_stage is not None:
            self.feed_stage = feed_stage
    
    def set_raw(self, path, value):
        self.obj.Tree.FindNode(path).Value = value

    def get_raw(self, path):
        return self.obj.Tree.FindNode(path).value

    def run(self):
        """
        Intermediate Variables
        :param L: liquid molar flow rate [kmol/hr]
        :param V: vapor molar flow rate [kmol/hr]
        :param x: liquid composition of each component, ordered [%]
        :param y: liquid composition of each component, ordered [%]
        :param h: liquid enthalpy [kJ/kmol]
        :param H: vapor enthalpy [kJ/kmol]

        Responding Variables
        :param T_stage: temperature of each stage [K]
        :param diameter: diameter of each stage [m]
        :param Q_cond: condenser duty [kW]
        :param Q_reb: reboiler duty [kW]
        """
        # Set input parameters
        # Input Stream (Stream 1)
        self.obj.Tree.FindNode("\Data\Streams\1\Input\TEMP\MIXED").Value = self.T_feed
        self.obj.Tree.FindNode("\Data\Streams\1\Input\PRES\MIXED").Value = self.P_feed
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
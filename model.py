import os
import win32com.client as win32

class Model:
    def __init__(self, filepath: str, components: list, \
        P_cond: float = None, P_drop: float = None, RR: float = None, N: float = None, feed_stage: float = None):
        """
        Design Parameters
        :param filepath: path to the model file
        :param components: list of component names [ordered]

        Manipulated Variables
        :param P_cond: condenser pressure [bar]
        :param P_drop: pressure drop per stage, [bar]
        :param RR: reflux ratio (L/D)
        :param N: number of stages
        :param feed_stage: stage number of the input feed [on-stage]
        """

        # Initialize variables
        self.filepath = filepath
        self.components = components

        self.P_cond = P_cond if P_cond is not None else self.init_var()["P_cond"]
        self.P_drop = P_drop if P_drop is not None else self.init_var()["P_drop"]
        self.RR = RR if RR is not None else self.init_var()["RR"]
        self.N = N if N is not None else self.init_var()["N"]
        self.feed_stage = feed_stage if feed_stage is not None else self.init_var()["feed_stage"]

        # Create COM object
        self.obj = win32.Dispatch("Apwn.Document")
        self.obj.InitFromArchive2(self.filepath)
        
    def init_var(self):
        # Get initial values
        return dict(
            P_cond = 1.12, #bar 
            P_drop = 0,
            RR = 0.924, 
            N = 36,
            feed_stage = 23, 
        )

    def update_manipulated(self, P_cond: float = None, P_drop: float = None, RR: float = None, N: float = None, feed_stage: float = None):
        # Update manipulated variables
        self.P_cond = P_cond if P_cond is not None else self.P_cond
        self.P_drop = P_drop if P_drop is not None else self.P_drop
        self.RR = RR if RR is not None else self.RR
        self.N = N if N is not None else self.N
        self.feed_stage = feed_stage if feed_stage is not None else self.feed_stage
    
    def set_raw(self, path, value):
        self.obj.Tree.FindNode(path).Value = value

    def get_raw(self, path):
        return self.obj.Tree.FindNode(path).value

    def run(self):
        """
        Responding Variables
        :param T_stage: temperature of each stage [K]
        :param diameter: diameter of each stage [m]
        :param Q_cond: condenser duty [kW]
        :param Q_reb: reboiler duty [kW]
        """
        # Set manipulated variables in Aspen
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Input\DP_STAGE").Value = self.P_drop
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Input\PRES1").Value = self.P_cond
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Input\BASIS_RR").Value = self.RR
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Input\NSTAGE").Value = self.N
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Input\FEED_STAGE\1").Value = self.feed_stage

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
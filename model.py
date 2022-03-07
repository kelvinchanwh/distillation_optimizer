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

    def getLeafs(self, path):
        cacheList = list()
        node = self.obj.Tree.FindNode(path)
        if node.HasChildren:
            output = list()
            for child in node.Elements:
                self.getLeafs(path + "\\" + child)
            return output
        else:
            output =  node.Value
        return output

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
        
        """
        Blocks Output Catalog
        {'Name': 'TOP_TEMP', 'Description': 'Temperature of Condenser/Top Stage'},
        {'Name': 'SCTEMP', 'Description': 'Subcooled temperature of Condenser/Top Stage'},
        {'Name': 'COND_DUTY', 'Description': 'Heat duty of Condenser/Top Stage'},
        {'Name': 'SCDUTY', 'Description': 'Subcooled duty of Condenser/Top Stage'},
        {'Name': 'MOLE_D', 'Description': 'Distillate rate'},
        {'Name': 'MOLE_L1', 'Description': 'Reflux rate'},
        {'Name': 'MOLE_RR', 'Description': 'Reflux ratio'},
        {'Name': 'MOLE_DW', 'Description': 'Free water distillate rate'},
        {'Name': 'RW', 'Description': 'Free water reflux ratio'},
        {'Name': 'MOLE_DFR', 'Description': 'Distillate to feed ratio'},
        {'Name': 'BOTTOM_TEMP', 'Description': 'Temperature of Reboiler Bottom Stage'},
        {'Name': 'REB_DUTY', 'Description': 'Heat duty of Reboiler Bottom Stage'},
        {'Name': 'MOLE_B', 'Description': 'Bottoms rate'},
        {'Name': 'MOLE_VN', 'Description': 'Boilup rate'},
        {'Name': 'MOLE_BR', 'Description': 'Boilup ratio'},
        {'Name': 'MOLE_BFR', 'Description': 'Bottoms to feed ratio'},
        {'Name': 'B_PRES', 'Description': 'Pressure profile'},
        {'Name': 'B_TEMP', 'Description': 'Temperature profile'},
        {'Name': 'X', 'Description': 'Liquid phase molar composition profile'},
        {'Name': 'Y', 'Description': 'Vapour phase molar composition profile'}

        Stream Output Catalog
        {'Name': 'TEMP_OUT', 'Description': 'Temperature'},
        {'Name': 'PRES_OUT', 'Description': 'Pressure'},
        {'Name': 'VFRAC_OUT', 'Description': 'Molar Vapor Fraction'},
        {'Name': 'LFRAC', 'Description': 'Molar Liquid Fraction'},
        {'Name': 'SFRAC', 'Description': 'Molar Solid Fraction'},
        {'Name': 'MASSVFRA', 'Description': 'Mass Vapor Fraction'},
        {'Name': 'MASSSFRA', 'Description': 'Mass Solid Fraction'},
        {'Name': 'HMX', 'Description': 'Molar Enthalpy'},
        {'Name': 'HMX_MASS', 'Description': 'Mass Enthalpy'},
        {'Name': 'SMX', 'Description': 'Molar Entropy'},
        {'Name': 'SMX_MASS', 'Description': 'Mass Entropy'},
        {'Name': 'RHOMX', 'Description': 'Molar Density'},
        {'Name': 'RHOMX_MASS', 'Description': 'Mass Density'},
        {'Name': 'HMX_FLOW', 'Description': 'Enthalpy Flow'},
        {'Name': 'MWMX', 'Description': 'Average Molecular Weight'},
        {'Name': 'MOLEFLMX', 'Description': 'Total Mole Flow'},
        {'Name': 'MOLEFLOW', 'Description': 'Mole Flow of Component'},
        {'Name': 'MOLEFRAC', 'Description': 'Mole Fraction of Component'},
        {'Name': 'MASSFLMX', 'Description': 'Total Mass Flow'},
        {'Name': 'MASSFLOW', 'Description': 'Mass Flow of Component'},
        {'Name': 'MASSFRAC', 'Description': 'Mass Fraction of Component'},
        {'Name': 'VOLFLMX', 'Description': 'Total Volume Flow'}
        """

        # List of output variables
        blockOutput = ["TOP_TEMP", "SCTEMP", "COND_DUTY", "SCDUTY", "MOLE_D", "MOLE_L1", \
            "MOLE_RR", "MOLE_DW", "RW", "MOLE_DFR", "BOTTOM_TEMP", "REB_DUTY", "MOLE_B", \
                "MOLE_VN", "MOLE_BR", "MOLE_BFR", "B_PRES", "B_TEMP", "X", "Y"]

        streamOutput = ["TEMP_OUT", "PRES_OUT", "VFRAC_OUT", "LFRAC", "SFRAC", "MASSVFRA", \
            "MASSSFRA", "HMX", "HMX_MASS", "SMX", "SMX_MASS", "RHOMX", "RHOMX_MASS", "HMX_FLOW", \
                "MWMX", "MOLEFLMX", "MOLEFLOW", "MOLEFRAC", "MASSFLMX", "MASSFLOW", "MASSFRAC", \
                    "VOLFLMX"]
        
        self.blockOutputList = []
        self.streamOutputList = []
        
        # Get output values
        for var in blockOutput:
            self.blockOutput[var] = self.getLeafs(var)
        
        for var in streamOutput:
            self.streamOutput[var] = self.getLeafs(var)
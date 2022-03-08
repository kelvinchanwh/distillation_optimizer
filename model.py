import os
import win32com.client as win32

class Model:
    def __init__(self, filepath: str, components: list, \
        P_cond: float = None, P_start_1: int = None, P_start_2: int = None, P_end_1: int = None, P_end_2: int = None, P_drop_1: float = None, P_drop_2: float = None, \
            RR: float = None, N: float = None, feed_stage: float = None, tray_spacing: float = None, num_pass: int = None):
        """
        Design Parameters
        :param filepath: path to the model file
        :param components: list of component names [ordered]

        Manipulated Variables
        :param P_cond: condenser pressure [bar]
        :param P_start_1: start stage of first section
        :param P_start_2: start stage of second section
        :param P_end_1: end stage of first section
        :param P_end_2: end stage of second section
        :param P_drop_1: pressure drop per stage of first section, [bar]
        :param P_drop_2: pressure drop per stage of second section, [bar]
        :param RR: reflux ratio (L/D)
        :param N: number of stages
        :param feed_stage: stage number of the input feed [on-stage]
        :param tray_spacing: tray spacing [m]
        :param num_pass: number of passes on each tray; max 4
        """

        # Initialize variables
        self.filepath = filepath
        self.components = components

        self.RR = RR if RR is not None else self.init_var()["RR"]
        self.N = N if N is not None else self.init_var()["N"]
        self.feed_stage = feed_stage if feed_stage is not None else self.init_var()["feed_stage"]
        self.tray_spacing = tray_spacing if tray_spacing is not None else self.init_var()["tray_spacing"]
        self.num_pass = num_pass if num_pass is not None else self.init_var()["num_pass"]
        self.P_cond = P_cond if P_cond is not None else self.init_var()["P_cond"]
        self.P_start_1 = P_start_1 if P_start_1 is not None else self.init_var()["P_start_1"]
        self.P_start_2 = P_start_2 if P_start_2 is not None else self.init_var()["P_start_2"]
        self.P_end_1 = P_end_1 if P_end_1 is not None else self.init_var()["P_end_1"]
        self.P_end_2 = P_end_2 if P_end_2 is not None else self.init_var()["P_end_2"]
        self.P_drop_1 = P_drop_1 if P_drop_1 is not None else self.init_var()["P_drop_1"]
        self.P_drop_2 = P_drop_2 if P_drop_2 is not None else self.init_var()["P_drop_2"]

        # Create COM object
        self.obj = win32.Dispatch("Apwn.Document")
        self.obj.InitFromArchive2(self.filepath)
        
    def init_var(self):
        # Get initial values
        return dict(
            RR = 0.924, 
            N = 36,
            feed_stage = 23, 
            tray_spacing = 0.6096,
            num_pass = 4,
            P_cond = 1.12, #bar
            P_start_1 = 2,
            P_start_2 = self.feed_stage + 1,
            P_end_1 = self.feed_stage - 1,
            P_end_2 = self.N - 1,
            P_drop_1 = 0,
            P_drop_2 = 0,
        )

    def update_manipulated(self, P_cond: float = None, P_start_1: int = None, P_start_2: int = None, P_end_1: int = None, P_end_2: int = None, P_drop_1: float = None, P_drop_2: float = None, \
            RR: float = None, N: float = None, feed_stage: float = None, tray_spacing: float = None, num_pass: int = None):
        # Update manipulated variables
        self.RR = RR if RR is not None else self.RR
        self.N = N if N is not None else self.N
        self.feed_stage = feed_stage if feed_stage is not None else self.feed_stage
        self.tray_spacing = tray_spacing if tray_spacing is not None else self.tray_spacing
        self.num_pass = num_pass if num_pass is not None else self.num_pass
        self.P_cond = P_cond if P_cond is not None else self.P_cond
        self.P_start_1 = P_start_1 if P_start_1 is not None else self.P_start_1
        self.P_start_2 = P_start_2 if P_start_2 is not None else self.P_start_2
        self.P_end_1 = P_end_1 if P_end_1 is not None else self.P_end_1
        self.P_end_2 = P_end_2 if P_end_2 is not None else self.P_end_2
        self.P_drop_1 = P_drop_1 if P_drop_1 is not None else self.P_drop_1
        self.P_drop_2 = P_drop_2 if P_drop_2 is not None else self.P_drop_2
    
    def set_raw(self, path, value):
        self.obj.Tree.FindNode(path).Value = value

    def get_raw(self, path):
        return self.obj.Tree.FindNode(path).value

    def getLeafs(self, path):
        output = dict()
        node = self.obj.Tree.FindNode(path)
        # Check if node has children
        if node.AttributeValue(38):
            for child in node.Elements:
                output[child.Name] = self.getLeafs(path + "\\" + child.Name)
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
        # Pressure
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Input\PRES1").Value = self.P_cond
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Input\PRES_STAGE1\1").Value = self.P_start_1
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Input\PRES_STAGE2\1").Value = self.P_end_1
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Input\PRES_STAGE1\2").Value = self.P_start_2
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Input\PRES_STAGE2\2").Value = self.P_end_2
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Input\PDROP_SEC\1").Value = self.P_drop_1
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Input\PDROP_SEC\2").Value = self.P_drop_2
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Input\BASIS_RR").Value = self.RR
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Input\NSTAGE").Value = self.N
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Input\FEED_STAGE\1").Value = self.feed_stage
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Subobjects\Tray Sizing\1\Input\TS_TSPACE\1").Value = self.tray_spacing
        # Hydraulic Ending Stage = N - 1
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Subobjects\Tray Sizing\1\Input\TS_STAGE2\1").Value = self.N - 1
        self.obj.Tree.FindNode(r"\Data\Blocks\B1\Subobjects\Tray Sizing\1\Input\TS_NPASS\1").Value = self.num_pass

        # Reinit before run
        self.obj.Reinit()

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
        
        self.blockOutput = dict()
        self.streamOutput = dict()
        
        # Get output values
        for var in blockOutput:
            self.blockOutput[var] = self.getLeafs("\\Data\\Blocks\\B1\\Output\\" + var)
        
        for i in range(1, 4):
            for var in streamOutput:
                self.streamOutput[var] = self.getLeafs("\\Data\\Streams\\" + str(i) + "\\Output\\" + var)

        self.T_stage = list(self.blockOutput["B_TEMP"].values())
        self.diameter = self.obj.Tree.FindNode(r"\Data\Blocks\B1\Subobjects\Tray Sizing\1\Output\DIAM4\1").Value
        self.Q_cond = self.blockOutput["COND_DUTY"]
        self.Q_reb = self.blockOutput["REB_DUTY"]

import os
import win32com.client as win32
import conversions

class Model:
    def __init__(self, filepath: str, components: list, \
        P_cond: float = None, P_start_1: int = None, P_start_2: int = None, P_end_1: int = None, P_end_2: int = None, P_drop_1: float = None, P_drop_2: float = None, \
            RR: float = None, N: float = None, feed_stage: float = None, tray_spacing: float = None, num_pass: int = None, tray_eff: float = None, \
            n_years: int = None):
        """
        Design Parameters
        :param filepath: path to the model file
        :param components: list of component names [ordered]

        Manipulated Variables
        :param P_cond: condenser pressure [bar]
        :param P_start_1: start stage of rectifying section
        :param P_start_2: start stage of stripping section
        :param P_end_1: end stage of rectifying section
        :param P_end_2: end stage of stripping section
        :param P_drop_1: pressure drop per stage of rectifying section, [bar]
        :param P_drop_2: pressure drop per stage of stripping section, [bar]
        :param RR: reflux ratio (L/D)
        :param N: number of stages
        :param feed_stage: stage number of the input feed [on-stage]
        :param tray_spacing: tray spacing [m]
        :param num_pass: number of passes on each tray; max 4
        :param tray_eff: tray efficiency
        :param n_years: number of years to for payback period
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

        # Ensure stage pressure does not overlap
        assert self.stage_pressure_check(), "Stage pressure overlaps"

        self.tray_eff = tray_eff if tray_eff is not None else self.init_var()["tray_eff"]
        self.n_years = n_years if n_years is not None else self.init_var()["n_years"]

        # Create COM object (Import Aspen File as an Object)
        self.obj = win32.Dispatch("Apwn.Document")
        self.obj.InitFromArchive2(self.filepath)
        self.obj.Visible = 1
        self.obj.SuppressDialogs = 1
        
    def init_var(self):
        # Get initial values
        return dict(
            RR = 0.924, 
            N = 36,
            feed_stage = 23, 
            tray_spacing = 0.6096,
            num_pass = 4,
            tray_eff = 0.5,
            P_cond = 1.12, #bar
            P_start_1 = 2,
            P_start_2 = self.feed_stage + 1,
            P_end_1 = self.feed_stage - 1,
            P_end_2 = self.N - 1,
            P_drop_1 = 0,
            P_drop_2 = 0,
            n_years = 4
        )

    def update_manipulated(self, P_cond: float = None, P_start_1: int = None, P_start_2: int = None, P_end_1: int = None, P_end_2: int = None, P_drop_1: float = None, P_drop_2: float = None, \
            RR: float = None, N: float = None, feed_stage: float = None, tray_spacing: float = None, num_pass: int = None, tray_eff: float = None, \
                n_years: int = None):
        # Update manipulated variables
        self.RR = RR if RR is not None else self.RR
        self.N = N if N is not None else self.N
        self.feed_stage = feed_stage if feed_stage is not None else self.feed_stage
        self.tray_spacing = tray_spacing if tray_spacing is not None else self.tray_spacing
        self.num_pass = num_pass if num_pass is not None else self.num_pass
        self.tray_eff = tray_eff if tray_eff is not None else self.tray_eff
        self.P_cond = P_cond if P_cond is not None else self.P_cond
        self.P_start_1 = P_start_1 if P_start_1 is not None else self.P_start_1
        self.P_start_2 = P_start_2 if P_start_2 is not None else self.P_start_2
        self.P_end_1 = P_end_1 if P_end_1 is not None else self.P_end_1
        self.P_end_2 = P_end_2 if P_end_2 is not None else self.P_end_2
        self.P_drop_1 = P_drop_1 if P_drop_1 is not None else self.P_drop_1
        self.P_drop_2 = P_drop_2 if P_drop_2 is not None else self.P_drop_2
        self.n_years = n_years if n_years is not None else self.n_years

        # Ensure stage pressure does not overlap
        assert self.stage_pressure_check(), "Stage pressure overlaps"

    def stage_pressure_check(self):
        # Minimum pressure drop is 0.01 bar
        self.P_drop_1 = 0.01 if self.P_drop_1 == 0 else self.P_drop_1
        self.P_drop_2 = 0.01 if self.P_drop_2 == 0 else self.P_drop_2
        # Check if stage pressure overlaps
        return (True if (self.P_start_1 >= 1 and self.P_end_1 < self.P_start_2 and self.P_end_2 <= self.N) else False)
    
    def setValue(self, path, value):
        self.obj.Tree.FindNode(path).Value = value

    def getValue(self, path):
        return self.obj.Tree.FindNode(path).Value

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

    def simulate(self):
        """
        Responding Variables
        :param T_stage: temperature of each stage [K]
        :param diameter: diameter of each stage [m]
        :param Q_cond: condenser duty [kW]
        :param Q_reb: reboiler duty [kW]
        """
        # Set manipulated variables in Aspen
        # Pressure
        self.setValue(r"\Data\Blocks\B1\Input\PRES1", self.P_cond)
        self.setValue(r"\Data\Blocks\B1\Input\PRES_STAGE1\1", self.P_start_1)
        self.setValue(r"\Data\Blocks\B1\Input\PRES_STAGE2\2", self.P_end_2)
        self.setValue(r"\Data\Blocks\B1\Input\PDROP_SEC\1", self.P_drop_1)
        self.setValue(r"\Data\Blocks\B1\Input\PDROP_SEC\2", self.P_drop_2)
        # If current 2nd start stage is smaller then upcoming 1st end stage, then set the upcoming 2nd start stage first
        curr2start = self.getValue(r"\Data\Blocks\B1\Input\PRES_STAGE1\2")
        if (self.P_end_1 > curr2start):
            self.setValue(r"\Data\Blocks\B1\Input\PRES_STAGE1\2", self.P_start_2)
            self.setValue(r"\Data\Blocks\B1\Input\PRES_STAGE2\1", self.P_end_1)
        else:
            self.setValue(r"\Data\Blocks\B1\Input\PRES_STAGE2\1", self.P_end_1)
            self.setValue(r"\Data\Blocks\B1\Input\PRES_STAGE1\2", self.P_start_2)

        
        self.setValue(r"\Data\Blocks\B1\Input\BASIS_RR", self.RR)
        self.setValue(r"\Data\Blocks\B1\Input\NSTAGE", self.N)
        self.setValue(r"\Data\Blocks\B1\Input\FEED_STAGE\1", self.feed_stage)
        self.setValue(r"\Data\Blocks\B1\Subobjects\Tray Sizing\1\Input\TS_TSPACE\1", self.tray_spacing)
        # Hydraulic Ending Stage = N - 1
        self.setValue(r"\Data\Blocks\B1\Subobjects\Tray Sizing\1\Input\TS_STAGE2\1", self.N - 1)
        self.setValue(r"\Data\Blocks\B1\Subobjects\Tray Sizing\1\Input\TS_NPASS\1", self.num_pass)

        self.setValue(r"\Data\Blocks\B1\Input\STAGE_EFF\2", self.tray_eff)

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
                "MOLE_VN", "MOLE_BR", "MOLE_BFR", "B_PRES", "B_TEMP", "X", "Y", \
                    "PROD_LFLOW", "HYD_MWL", "HYD_MWL", "HYD_RHOL", "HYD_RHOV", "HYD_VVF", \
                        "HYD_LVF"]

        streamOutput = ["TEMP_OUT", "PRES_OUT", "VFRAC_OUT", "LFRAC", "SFRAC", "MASSVFRA", \
            "MASSSFRA", "HMX", "HMX_MASS", "SMX", "SMX_MASS", "RHOMX", "RHOMX_MASS", "HMX_FLOW", \
                "MWMX", "MOLEFLMX", "MOLEFLOW", "MOLEFRAC", "MASSFLMX", "MASSFLOW", "MASSFRAC", \
                    "VOLFLMX"]

        trayOutput = ["DIAM4", "DCLENG2", "DCAREA"]
        
        self.blockOutput = dict()
        self.streamOutput = dict()
        self.trayOutput = dict()
        
        # Get output values
        for var in blockOutput:
            self.blockOutput[var] = self.getLeafs("\\Data\\Blocks\\B1\\Output\\" + var)

        for var in trayOutput:
            self.trayOutput[var] = self.getLeafs("\\Data\\Blocks\\B1\\Subobjects\\Tray Sizing\\1\\Output\\" + var + "\\1")
        
        for i in range(1, 4):
            for var in streamOutput:
                self.streamOutput[var] = self.getLeafs("\\Data\\Streams\\" + str(i) + "\\Output\\" + var)

        self.feed_flow_rate = self.getValue("\\Data\\Streams\\1\\Input\\TOT_FLOW")

        self.T_stage = list(self.blockOutput["B_TEMP"].values())
        self.molecular_weight_liquid = list(self.blockOutput["HYD_MWL"].values())
        self.molecular_weight_vapour = list(self.blockOutput["HYD_MWV"].values())
        self.density_liquid = list(map(conversions.gmCc_to_kgM3, self.blockOutput["HYD_RHOL"].values()))
        self.density_vapour = list(map(conversions.gmCc_to_kgM3, self.blockOutput["HYD_RHOV"].values()))
        self.volume_flow_vapour = list(self.blockOutput["HYD_VVF"].values())
        self.volume_flow_liquid = list(self.blockOutput["HYD_LVF"].values())
        self.weir_length = trayOutput["DCLENG2"]
        self.diameter = trayOutput["DIAM4"]
        self.Q_cond = self.blockOutput["COND_DUTY"]
        self.Q_reb = self.blockOutput["REB_DUTY"]
        self.D = self.blockOutput["PROD_LFLOW"]
        self.A_c = self.blockOutput["DCAREA"]
        self.A_d = self.blockOutput["MOLE_RR"]

    def calc_energy_cost(self, steam_type):
        energy_cost = 0.0
        # Energy cost
        energy_cost = 0.354 * conversions.calPerSec_to_GJPerYear(self.Q_cond)
        if steam_type == "hp":
            energy_cost += 9.88 * conversions.calPerSec_to_GJPerYear(self.Q_reb)
        else:
            energy_cost += 7.78 * conversions.calPerSec_to_GJPerYear(self.Q_reb)

        return energy_cost

    def calc_tac(self):
        # Calculate Total Annualized Cost
        # Cooling Water
        t_in_hot_cond = self.T_stage[1]
        t_out_cold_cond = 35.0
        t_out_hot_cond = self.T_stage[0]
        t_in_cold_cond = 25.0
        
        # Steam
        t_in_cold_reb = self.T_stage[-2]
        t_out_cold_reb = self.T_stage[-1]
        # T_in_cold_reb must be at least 10 deg C below T_in_cold_reb
        if t_in_cold_reb > 160.0 - 10.0:
            # Use hp steam temp
            steam = "hp"
            t_in_hot_reb = 254.0
            t_out_hot_reb = 253.0
        else:
            # Use lp steam temp
            steam = "lp"
            t_in_hot_reb = 160.0
            t_out_hot_reb = 159.0

        del_t_mean_cond = (0.5 * (t_in_hot_cond - t_out_cold_cond) * (t_out_hot_cond - t_in_cold_cond) * (t_in_hot_cond - t_out_cold_cond + t_out_hot_cond - t_in_cold_cond)) ** (1./3)
        del_t_mean_reb = (0.5 * (t_in_hot_reb - t_out_cold_reb) * (t_out_hot_reb - t_in_cold_reb) * (t_in_hot_reb - t_out_cold_reb + t_out_hot_reb - t_in_cold_reb)) ** (1./3)

        U_cond = 0.852
        U_reb = 0.568
        A_cond = abs(conversions.calPerSec_to_kJPerSec(self.Q_cond))/(U_cond * del_t_mean_cond)
        A_reb = abs(conversions.calPerSec_to_kJPerSec(self.Q_reb))/(U_reb * del_t_mean_reb)

        self.height = 1.2 * self.tray_spacing * self.N

        C_cap_cond = 7296 * (A_cond ** 0.65)
        C_cap_reb = 7296 * (A_reb ** 0.65)
        C_cap_hx = C_cap_cond + C_cap_reb
        C_cap_col = 17640 * (self.diameter ** 1.066) * (self.height ** 0.802)

        self.energy_cost = self.calc_energy_cost(steam)

        self.TAC = ((C_cap_hx + C_cap_col) / self.n_years) + self.energy_cost

    def run(self):
        self.simulate()
        self.calc_tac()
        return self.TAC

    def close(self):
        self.obj.Close()
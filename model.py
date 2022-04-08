import os
import win32com.client as win32
import conversions
import time
import collections
import initialize
class Model:
    def __init__(self, filepath: str, main_component: str = None, \
        P_cond: float = None, P_drop_1: float = None, P_drop_2: float = None, \
            RR: float = None, N: float = None, feed_stage: float = None, tray_spacing: float = None, num_pass: int = None, tray_eff: float = None, \
            n_years: int = None):
        """
        Design Parameters
        :param filepath: path to the model file
        :param components: list of component names [ordered]

        Manipulated Variables
        :param P_cond: condenser pressure [bar]
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

        self.RR = RR if RR is not None else self.init_var()["RR"]
        self.N = N if N is not None else self.init_var()["N"]
        self.feed_stage = feed_stage if feed_stage is not None else self.init_var()["feed_stage"]
        self.tray_spacing = tray_spacing if tray_spacing is not None else self.init_var()["tray_spacing"]
        self.num_pass = num_pass if num_pass is not None else self.init_var()["num_pass"]
        self.P_cond = P_cond if P_cond is not None else self.init_var()["P_cond"]
        self.P_drop_1 = P_drop_1 if P_drop_1 is not None else self.init_var()["P_drop_1"]
        self.P_drop_2 = P_drop_2 if P_drop_2 is not None else self.init_var()["P_drop_2"]

        # Minimum pressure drop is 0.01 bar
        self.P_drop_1 = 0.01 if self.P_drop_1 == 0 else self.P_drop_1
        self.P_drop_2 = 0.01 if self.P_drop_2 == 0 else self.P_drop_2

        self.tray_eff = tray_eff if tray_eff is not None else self.init_var()["tray_eff"]
        self.n_years = n_years if n_years is not None else self.init_var()["n_years"]

        # Create COM object (Import Aspen File as an Object)
        self.obj = win32.Dispatch("Apwn.Document")
        self.obj.InitFromArchive2(self.filepath)
        self.obj.Visible = 1
        self.obj.SuppressDialogs = 1

        # Get all components
        self.components = list(self.getLeafs("\\Data\\Streams\\1\\Input\\FLOW\\MIXED").keys())
        self.main_component = main_component if main_component is not None else self.components[0]
        
    def init_var(self):
        # Get initial values
        return dict(
            RR = 0.924, 
            N = 36,
            feed_stage = 23, 
            tray_spacing = 0.6096,
            num_pass = 1,
            tray_eff = 0.5,
            P_cond = 1.12, #bar
            P_drop_1 = 0,
            P_drop_2 = 0,
            n_years = 3
        )

    def update_manipulated(self, P_cond: float = None, P_drop_1: float = None, P_drop_2: float = None, \
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
        self.P_drop_1 = P_drop_1 if P_drop_1 is not None else self.P_drop_1
        self.P_drop_2 = P_drop_2 if P_drop_2 is not None else self.P_drop_2
        self.n_years = n_years if n_years is not None else self.n_years

        # Minimum pressure drop is 0.01 bar
        self.P_drop_1 = 0.01 if self.P_drop_1 == 0 else self.P_drop_1
        self.P_drop_2 = 0.01 if self.P_drop_2 == 0 else self.P_drop_2
    
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

    def set_pressure_stages(self):
        # Pressure
        self.setValue(r"\Data\Blocks\B1\Input\PRES1", self.P_cond)       
        self.setValue(r"\Data\Blocks\B1\Input\PDROP_SEC\1", self.P_drop_1)
        self.setValue(r"\Data\Blocks\B1\Input\PDROP_SEC\2", self.P_drop_2)
        # If current 2nd start stage is smaller then upcoming 1st end stage, then set the upcoming 2nd start stage first
        self.setValue(r"\Data\Blocks\B1\Input\PRES_STAGE1\1", self.P_start_1)
        curr2start = self.getValue(r"\Data\Blocks\B1\Input\PRES_STAGE1\2")
        curr2end = self.getValue(r"\Data\Blocks\B1\Input\PRES_STAGE2\2")
        if (self.P_end_1 >= curr2start):
            if (self.P_end_2 >= curr2end):
                self.setValue(r"\Data\Blocks\B1\Input\PRES_STAGE2\2", self.P_end_2)
                self.setValue(r"\Data\Blocks\B1\Input\PRES_STAGE1\2", self.P_start_2)
            else:
                self.setValue(r"\Data\Blocks\B1\Input\PRES_STAGE1\2", self.P_start_2)
                self.setValue(r"\Data\Blocks\B1\Input\PRES_STAGE2\2", self.P_end_2)
            self.setValue(r"\Data\Blocks\B1\Input\PRES_STAGE2\1", self.P_end_1)
        else:
            self.setValue(r"\Data\Blocks\B1\Input\PRES_STAGE2\1", self.P_end_1)
            self.setValue(r"\Data\Blocks\B1\Input\PRES_STAGE1\2", self.P_start_2)
            self.setValue(r"\Data\Blocks\B1\Input\PRES_STAGE2\2", self.P_end_2)
        # Hydraulic Ending Stage = N - 1
        self.setValue(r"\Data\Blocks\B1\Subobjects\Tray Sizing\1\Input\TS_STAGE2\1", self.N - 1)

    def set_general_variables(self):
        self.setValue(r"\Data\Blocks\B1\Input\NSTAGE", self.N)
        self.setValue(r"\Data\Blocks\B1\Input\FEED_STAGE\1", self.feed_stage)
        self.setValue(r"\Data\Blocks\B1\Subobjects\Tray Sizing\1\Input\TS_TSPACE\1", self.tray_spacing)    
        self.setValue(r"\Data\Blocks\B1\Input\BASIS_RR", self.RR)
        self.setValue(r"\Data\Blocks\B1\Subobjects\Tray Sizing\1\Input\TS_NPASS\1", self.num_pass)
        self.setValue(r"\Data\Blocks\B1\Input\STAGE_EFF\2", self.tray_eff)

    def simulate(self):
        """
        Responding Variables
        :param T_stage: temperature of each stage [K]
        :param diameter: diameter of each stage [m]
        :param Q_cond: condenser duty [kW]
        :param Q_reb: reboiler duty [kW]
        """
        # Set manipulated variables in Aspen

        self.P_start_1 = 2
        self.P_start_2 = self.feed_stage + 1
        self.P_end_1 = self.feed_stage
        self.P_end_2 = self.N - 1

        currN = self.getValue(r"\Data\Blocks\B1\Input\NSTAGE")
        if currN > self.N:
            self.set_pressure_stages()
            self.set_general_variables()
        else:
            self.set_general_variables()
            self.set_pressure_stages()

        # Reinit before run
        self.obj.Reinit()

        # Run model
        self.obj.Run2()

        # List of output variables
        blockOutput = ["COND_DUTY", "REB_DUTY", "B_PRES", "B_TEMP", "B_K", "PROD_LFLOW", \
            "HYD_MWL", "HYD_MWV", "HYD_RHOL", "HYD_RHOV", "HYD_VVF", "HYD_LVF"]

        streamOutput = ["MOLEFLMX", "MOLEFLOW", "STR_MAIN"]

        trayOutput = ["DIAM4", "DCLENG1", "TOT_AREA", "SIDE_AREA"]
        
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
                stream = dict()
                stream[var] = self.getLeafs("\\Data\\Streams\\" + str(i) + "\\Output\\" + var)
            self.streamOutput[str(i)] = stream

        self.feed_flow_rate = self.getValue("\\Data\\Streams\\1\\Input\\TOTFLOW\\MIXED")
        self.stream_input_pres = self.getValue("\\Data\\Streams\\1\\Input\\PRES\\MIXED")

        self.T_stage = list(self.blockOutput["B_TEMP"].values())
        self.P_stage = list(self.blockOutput["B_PRES"].values())
        self.molecular_weight_liquid = list(self.blockOutput["HYD_MWL"].values())
        self.molecular_weight_vapour = list(self.blockOutput["HYD_MWV"].values())
        self.density_liquid = list(self.blockOutput["HYD_RHOL"].values()) # gm_cc
        self.density_vapour = list(self.blockOutput["HYD_RHOV"].values()) # gm_cc
        self.volume_flow_vapour = list(self.blockOutput["HYD_VVF"].values()) #l_min
        self.volume_flow_liquid = list(self.blockOutput["HYD_LVF"].values()) #l_min
        self.Q_cond = self.blockOutput["COND_DUTY"] # cal_sec
        self.Q_reb = self.blockOutput["REB_DUTY"] #  cal_sec
        self.D = list(self.blockOutput["PROD_LFLOW"].values()) #kmol_hr
        self.A_c = max(self.trayOutput["TOT_AREA"].values()) #sqm
        self.A_d = max(self.trayOutput["SIDE_AREA"].values()) # sqm
        self.weir_length = self.trayOutput["DCLENG1"]
        self.diameter = self.trayOutput["DIAM4"]

        self.K = dict()
        self.recovery = dict()
        self.purity = dict()
        self.mole_frac = dict()
        self.mole_flow = dict()
        for component in self.components:
            self.recovery[component] = self.streamOutput["2"]["STR_MAIN"]["MOLEFLOW"]["MIXED"][component] \
                / (self.streamOutput["2"]["STR_MAIN"]["MOLEFLOW"]["MIXED"][component] \
                    +self.streamOutput["3"]["STR_MAIN"]["MOLEFLOW"]["MIXED"][component])
            self.purity[component] = self.streamOutput["2"]["STR_MAIN"]["MOLEFLOW"]["MIXED"][component] \
                / self.streamOutput["2"]["STR_MAIN"]["MOLEFLMX"]["MIXED"]
            self.K[component] = self.blockOutput["B_K"][str(self.feed_stage)][component]
            self.mole_flow[component] = self.getValue("\\Data\\Streams\\1\\Input\\FLOW\\MIXED\\" + component)
            self.mole_frac[component] = self.mole_flow[component]/self.streamOutput["1"]["STR_MAIN"]["MOLEFLMX"]["MIXED"]

        # Order K by compoenent K
        self.K = collections.OrderedDict(sorted(self.K.items(), key=lambda t: t[1]))
        self.LK = self.main_component
        self.HK = list(self.K.items())[list(self.K).index(self.main_component) - 1][0]

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
        start_time = time.time()
        self.simulate()
        self.calc_tac()
        return (time.time() - start_time)

    def close(self):
        self.obj.Close()
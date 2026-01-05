import sys
import os
import json
import logging

# Setup basic logging to avoid errors if the class tries to log
logging.basicConfig(level=logging.INFO)

# Add project root to path
sys.path.append(os.path.abspath(r"g:\Meu Drive\Doutorado - IME\Tese\DoseToRisk\Programa_Python_AR"))

from dose2risk.core.risk_calculator import CalculadoraRisco

class MockRiskCalc(CalculadoraRisco):
    def __init__(self):
        # Skip init logic that requires files
        pass

def reproduction():
    print("--- REPRODUCTION TEST START ---")
    config_path = r"g:\Meu Drive\Doutorado - IME\Tese\DoseToRisk\Programa_Python_AR\config\beir_hotspot_parameters.json"
    
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        return

    with open(config_path, 'r') as f:
        data = json.load(f)
    
    # Extract Leukemia configuration
    beir_v_config = data['configurations']['red_marrow']['beir_v']
    
    # User Scenario: Age Exp 10, Age Att 30 (Time since = 20)
    # Expected: Beta ~ 4.885
    # Current: Beta ~ 2.38 (Adult-like)
    
    calc = MockRiskCalc()
    
    print("Test Case: Age Expose=10, Age Current=30 (Time Since=20 years)")
    
    # Arguments: dose_Sv, age_exp, age_att, gender, beir_v_config
    res, eq, extras = calc.beir_v_risk(
        dose_Sv=1.3, 
        age_exp=10, 
        age_att=30, 
        gender='male', 
        beir_v_config=beir_v_config
    )
    
    beta_used = extras.get('Internal_Beta_V')
    print(f"Beta Used: {beta_used}")
    print(f"Equation Symbolic: {eq}")
    
    if beta_used is not None:
        if abs(beta_used - 2.38) < 0.1:
            print("RESULT: CONFIRMED - System is using adult-like beta (2.38). This matches user complaint.")
        elif abs(beta_used - 4.885) < 0.1:
            print("RESULT: DESIRED - System is using child beta (4.885).")
        else:
            print(f"RESULT: UNEXPECTED - System is using beta {beta_used}")
    else:
        print("RESULT: FAILED - Beta not returned")

    print("--- REPRODUCTION TEST END ---")

if __name__ == "__main__":
    reproduction()

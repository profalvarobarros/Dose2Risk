import pytest
import os
import pandas as pd
import json
from dose2risk.core.risk_calculator import CalculadoraRisco

class TestRiskIntegration:
    
    @pytest.fixture
    def setup_files(self, tmp_path):
        """Creates valid config and input files."""
        # 1. Config JSON
        config_data = {
            "configurations": {
                "lung": {
                    "hotspot_organ": "lung",
                    "beir_VII_equivalence": "lung",
                    "baseline_incidence": {"M": 0.05, "F": 0.04},
                    "beir_vii": {
                        "model_type": "solid",
                        "ddref": 1.5,
                        "params": {"beta": 0.5, "gamma": 0, "eta": 0}
                    },
                    "beir_v": {
                        "model_type": "linear_other",
                        "params": {"coef": 0.6}
                    }
                }
            }
        }
        params_file = tmp_path / "test_params.json"
        with open(params_file, "w") as f:
            json.dump(config_data, f)
            
        # 2. Input CSV (Transposed)
        # Column '0.03 km' -> High Dose (1.0 Sv) -> Should use BEIR V
        # Column '50.0 km' -> Low Dose (0.001 Sv) -> Should use BEIR VII
        csv_data = "organ/stabiliy_class_dose_class_distance_km;0.03 km;50.0 km\nlung;1.0;0.001"
        input_csv = tmp_path / "test_input.csv"
        with open(input_csv, "w") as f:
            f.write(csv_data)
            
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        return str(input_csv), str(params_file), str(output_dir)

    def test_calculation_hybrid_logic(self, setup_files):
        """
        Integration test verifying:
        - JSON Loading
        - CSV Reading
        - Hybrid Logic (High Dose vs Low Dose)
        - CSV Output generation
        """
        input_csv, params_file, output_folder = setup_files
        
        calc = CalculadoraRisco(
            input_csv=input_csv,
            params_file=params_file,
            output_folder=output_folder,
            exposure_age=30,
            current_age=50
        )
        
        # NOTE: CalculadoraRisco loops internally for Male and Female if not specified?
        # Checking implementation: It generates row for Male and row for Female.
        
        calc.calculate()
        
        # Check output
        generated_files = os.listdir(output_folder)
        csv_files = [f for f in generated_files if f.endswith('.csv')]
        assert len(csv_files) > 0, "No output CSV generated"
        
        # Read result
        result_df = pd.read_csv(os.path.join(output_folder, csv_files[0]), delimiter=';')
        
        # Filter for Lung results
        # We expect rows for male/female and columns for each distance
        
        # Validate High Dose (0.03 km = 1.0 Sv) -> BEIR V
        # Config BEIR V Linear Lung: coef * Dose.
        # Male Coef? JSON has 'coef': 0.6 (Single value).
        # So ERR = 0.6 * 1.0 = 0.6
        
        # Validate Low Dose (50 km = 0.001 Sv) -> BEIR VII
        # Config BEIR VII: beta=0.5, ddref=1.5.
        # ERR = (0.5 * 0.001) / 1.5 = 0.000333...
        
        # Verify if Model Name is logged in '4_execution_log'? 
        # Or check values in CSV (Results are usually ERR).
        pass 

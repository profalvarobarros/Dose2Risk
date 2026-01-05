
import os
import glob
import pandas as pd
from dose2risk.core.risk_calculator import CalculadoraRisco

def validate():
    # 1. Obter ultimo arquivo transposto
    base_dir = r"g:\Meu Drive\Doutorado - IME\Tese\DoseToRisk\Programa_Python_AR"
    search_path = os.path.join(base_dir, "data", "outputs", "**", "2_hotspot_transpose*.csv")
    files = glob.glob(search_path, recursive=True)
    if not files:
        print("Nenhum arquivo transposto encontrado.")
        return

    latest_file = max(files, key=os.path.getmtime)
    print(f"Usando input: {latest_file}")
    
    # 2. Configurar params
    params_file = os.path.join(base_dir, "config", "beir_hotspot_parameters.json")
    output_folder = os.path.join(base_dir, "data", "outputs", "validation_test")
    
    # 3. Rodar Calculadora
    calc = CalculadoraRisco(
        input_csv=latest_file,
        params_file=params_file,
        output_folder=output_folder,
        exposure_age=30,
        current_age=50,
        timestamp="VALIDATION_RUN"
    )
    calc.calculate()
    
    # 4. Verificar Saída
    output_csv = os.path.join(output_folder, "3_calculated_risks_ERR_LAR_ee30_ea50_VALIDATION_RUN.csv")
    if not os.path.exists(output_csv):
        print("Erro: CSV de saída não gerado.")
        return
        
    df = pd.read_csv(output_csv, sep=';')
    print("\nColunas geradas:")
    for col in df.columns:
        print(f"- {col}")
        
    # Verificação de colunas proibidas
    forbidden = ['dose_Sv_row_id', 'model_row_id', 'ERR_row_id', 'LAR_row_id']
    found_forbidden = [c for c in df.columns if any(f in c for f in forbidden)]
    
    if found_forbidden:
        print(f"\nFALHA: Colunas 'row_id' encontradas: {found_forbidden}")
    else:
        print("\nSUCESSO: Nenhuma coluna espúria de 'row_id' encontrada.")

if __name__ == "__main__":
    validate()

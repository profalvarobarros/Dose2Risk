import pandas as pd
import os
import shutil
import sys

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dose2risk.vis.charts import RiskChartGenerator

def verify_charts():
    # Caminho do CSV de exemplo existente
    input_csv = r"g:\Meu Drive\Doutorado - IME\Tese\DoseToRisk\Programa_Python_AR\data\outputs\20260112123003_e5ae8e10_20260112123007\3_calculated_risks_ERR_LAR_ee20_ea30_20260112123007.csv"
    output_dir = r"g:\Meu Drive\Doutorado - IME\Tese\DoseToRisk\Programa_Python_AR\tests\temp_charts"
    
    # Limpar diretório de teste anterior
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    print(f"Carregando dados de: {input_csv}")
    df = pd.read_csv(input_csv, sep=';', decimal='.')
    
    print(f"Dados carregados. Linhas: {len(df)}")
    
    generator = RiskChartGenerator(output_dir)
    generator.generate_plots(df)
    
    charts_dir = os.path.join(output_dir, "charts")
    if os.path.exists(charts_dir):
        files = os.listdir(charts_dir)
        print(f"Arquivos gerados ({len(files)}):")
        for f in files[:5]:
            print(f" - {f}")
        if len(files) > 5:
            print(" ...")
            
        if len(files) > 0:
            print("SUCESSO: Gráficos gerados.")
        else:
            print("FALHA: Diretório de gráficos vazio.")
    else:
        print("FALHA: Diretório de gráficos não criado.")

if __name__ == "__main__":
    verify_charts()

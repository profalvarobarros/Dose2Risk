
import os
import sys
import pandas as pd

# Adiciona o diretório raiz ao path para importar dose2risk
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dose2risk.core.extractor import ExtratorHotspot

def reproduce():
    input_folder = r"g:\Meu Drive\Doutorado - IME\Tese\DoseToRisk\Programa_Python_AR\data\examples\InputHotSpotExamples"
    output_file = r"g:\Meu Drive\Doutorado - IME\Tese\DoseToRisk\Programa_Python_AR\tests\reproduce_issue_0_output.csv"
    
    # Remove arquivo de saída se existir
    if os.path.exists(output_file):
        os.remove(output_file)

    extractor = ExtratorHotspot(input_folder, output_file)
    extractor.extract()

    if not os.path.exists(output_file):
        print("FALHA: Arquivo de output não foi gerado.")
        return

    df = pd.read_csv(output_file, sep=';')
    print(f"Total de linhas extraídas: {len(df)}")
    print("Distâncias extraídas:")
    print(df['distance_km'].unique())

    if len(df) == 1 and df['distance_km'].iloc[0] == 0.03:
        print("REPRODUZIDO: Apenas a primeira distância (0.03 km) foi extraída.")
    elif len(df) > 1:
        print("NÃO REPRODUZIDO: Mais de uma linha foi extraída.")
    else:
        print("RESULTADO INESPERADO.")

if __name__ == "__main__":
    reproduce()

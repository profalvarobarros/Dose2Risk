
import os
import sys
import hashlib
import logging
import shutil

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
sys.path.append(project_root)

from dose2risk.core.risk_calculator import CalculadoraRisco

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DO TESTE DE REGRESSÃO
# -----------------------------------------------------------------------------
GOLDEN_INPUT_CSV = os.path.join(current_dir, 'golden_input.csv')
PARAMS_FILE = os.path.join(project_root, 'config', 'beir_hotspot_parameters.json')
OUTPUT_DIR = os.path.join(current_dir, 'temp_output')

# HASH ESPERADO (BASELINE)
# Na primeira execução, este valor será desconhecido. O script imprimirá o hash calculado.
# Copie o valor impresso e atualize esta variável para "congelar" o comportamento esperado.
GOLDEN_HASH_SHA256 = "01dcbd3ade9d7a74f548224f27ec86db391f362ffd2ece4e2d5328de75d3a507"

def calculate_file_hash(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def run_regression():
    print(f"--- INICIANDO TESTE DE REGRESSÃO ---")
    print(f"Input: {GOLDEN_INPUT_CSV}")
    
    # Limpeza prévia
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Execução Determinística (Timestamp fixo para nome de arquivo previsível)
    # exposure_age=30, current_age=50
    calc = CalculadoraRisco(
        input_csv=GOLDEN_INPUT_CSV,
        params_file=PARAMS_FILE,
        output_folder=OUTPUT_DIR,
        exposure_age=30,
        current_age=50,
        timestamp="REGRESSION_BASELINE"
    )
    
    try:
        calc.calculate()
        print("Pipeline executado com sucesso.")
    except Exception as e:
        print(f"ERRO CRÍTICO NA EXECUÇÃO DO PIPELINE: {e}")
        sys.exit(1)
        
    # Identificar arquivo de saída
    expected_filename = "3_calculated_risks_ERR_LAR_ee30_ea50_REGRESSION_BASELINE.csv"
    output_file = os.path.join(OUTPUT_DIR, expected_filename)
    
    if not os.path.exists(output_file):
        print(f"FALHA: Arquivo de saída não encontrado: {output_file}")
        sys.exit(1)
        
    # Calcular Hash
    calculated_hash = calculate_file_hash(output_file)
    print(f"\nHASH CALCULADO DO CSV DE SAÍDA: {calculated_hash}")
    print(f"HASH GOLDEN ESPERADO:           {GOLDEN_HASH_SHA256}")
    
    if GOLDEN_HASH_SHA256 == "PENDING_FIRST_RUN":
        print("\n[AVISO] Esta parece ser a primeira execução (Bootstrap).")
        print(f"Por favor, verifique se o arquivo output '{output_file}' está correto.")
        print(f"Se estiver, atualize a variável GOLDEN_HASH_SHA256 no script com: '{calculated_hash}'")
        sys.exit(0) # Neutro para primeira execução
        
    if calculated_hash == GOLDEN_HASH_SHA256:
        print("\n[SUCESSO] O HASH CORRESPONDE! A Lógica Matemática está estável.")
        sys.exit(0)
    else:
        print(f"\n[FALHA] O HASH NÃO CORRESPONDE!")
        print(f"EXPECTED: {GOLDEN_HASH_SHA256}")
        print(f"ACTUAL:   {calculated_hash}")
        sys.exit(1)

if __name__ == "__main__":
    run_regression()

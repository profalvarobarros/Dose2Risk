import os
import sys
import argparse
from dose2risk.core.auditor import AuditorConformidadeBeir

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def obter_caminho_arquivo(mensagem: str, padrao: str = None) -> str:
    """Solicita um caminho de arquivo ao usuário e valida sua existência."""
    while True:
        prompt = f"{mensagem}"
        if padrao:
            prompt += f" [Padrão: {os.path.basename(padrao)}]"
        prompt += ": "
        
        caminho = input(prompt).strip()
        
        if not caminho and padrao:
            caminho = padrao
            
        # Remover aspas que o Windows Adiciona ao copiar caminho como texto
        caminho = caminho.replace('"', '').replace("'", "")
        
        if os.path.isfile(caminho):
            return caminho
        else:
            print(f"❌ Erro: Arquivo não encontrado: {caminho}")

def main():
    limpar_tela()
    print("========================================================")
    print("   🛡️  AUDITOR DE CONFORMIDADE BEIR V/VII - DoseToRisk")
    print("========================================================")
    print("Este utilitário realiza uma auditoria cruzada independente")
    print("dos cálculos de risco, verificando conformidade matemática")
    print("e integridade dos parâmetros utilizados.\n")

    parser = argparse.ArgumentParser(description='Executar Auditoria BEIR.')
    parser.add_argument('--log', help='Caminho para o arquivo de log de execução (.log)')
    parser.add_argument('--params', help='Caminho para o arquivo risk_parameters.json')
    args = parser.parse_args()

    # 1. Obter Log de Execução
    if args.log:
        caminho_log = args.log
    else:
        print("Módulo 1: Seleção de Fonte de Dados")
        caminho_log = obter_caminho_arquivo("📂 Arraste ou cole o caminho do arquivo de LOG (.log)")

    # 2. Obter Parâmetros de Referência
    # Tenta adivinhar o location padrão
    caminho_base = os.path.dirname(os.path.abspath(__file__))
    # Assumindo estrutura dose2risk/executar_auditoria.py -> voltar um nivel
    # Ajuste se o script estiver na raiz dose2risk ou fora
    # O arquivo parameters costuma ficar em dose2risk/core/data ou na raiz?
    # Vou chutar um padrão razoável ou deixar vazio.
    padrao_params = os.path.join(caminho_base, "dose2risk", "core", "data", "risk_parameters.json")
    if not os.path.exists(padrao_params): padrao_params = None

    if args.params:
        caminho_params = args.params
    else:
        print("\nMódulo 2: Parâmetros de Referência")
        caminho_params = obter_caminho_arquivo("⚙️  Arraste ou cole o caminho do arquivo risk_parameters.json", padrao_params)

    # 3. Definir saída
    pasta_saida = os.path.dirname(caminho_log)
    
    print("\n--------------------------------------------------------")
    print(f"🚀 Iniciando Auditoria...")
    print(f"   Log Alvo: {os.path.basename(caminho_log)}")
    print(f"   Ref Config: {os.path.basename(caminho_params)}")
    print("--------------------------------------------------------")

    try:
        auditor = AuditorConformidadeBeir(caminho_log, caminho_params, pasta_saida)
        caminho_relatorio = auditor.auditar_execucao()
        
        print("\n✅ Auditoria Concluída com Sucesso!")
        print(f"📄 Relatório gerado em:\n   {caminho_relatorio}")
        print("--------------------------------------------------------")
        
        # Tenta abrir o relatório automaticamente no Windows
        if os.name == 'nt':
            os.startfile(caminho_relatorio)
            
    except Exception as e:
        print(f"\n❌ FALHA CRÍTICA NA AUDITORIA: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

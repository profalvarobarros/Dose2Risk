
import os
import logging
from datetime import datetime
from dose2risk.core.extractor import ExtratorHotspot
from dose2risk.core.transposer import TranspositorHotspot
from dose2risk.core.risk_calculator import CalculadoraRisco

class HotspotPipeline:
    """
    Orquestrador (Facade) para o fluxo de processamento do HotSpot.

    Esta classe encapsula a complexidade da chamada sequencial dos três módulos principais do sistema:
    1. **Extração:** Leitura de arquivos brutos (.txt) e estruturação tabular.
    2. **Transposição:** Conversão dos dados para formato matriz (Órgão x Cenário).
    3. **Cálculo de Risco:** Aplicação dos modelos BEIR V/VII para estimativa de risco oncológico.

    Padrão de Projeto:
    ------------------
    Atua como um 'Pipeline Controller', garantindo que a saída de uma etapa seja validada
    antes de servir como entrada para a próxima. Gerencia também a criação de diretórios
    e a nomenclatura consistente de arquivos baseada em carimbos de tempo (Timestamp).
    """
    def __init__(self, input_folder: str, exposure_age: float, current_age: float, output_folder: str, params_file: str, filters: dict = None) -> None:
        """
        Inicializa o pipeline de processamento.

        Parâmetros:
        -----------
        input_folder : str
            Diretório raiz contendo os arquivos de texto (.txt) gerados pelo HotSpot.
        exposure_age : float
            Idade do indivíduo no momento da exposição (em anos).
        current_age : float
            Idade atual do indivíduo (em anos).
        output_folder : str
            Diretório onde todos os artefatos gerados (CSVs, Logs) serão salvos.
        params_file : str
            Caminho para o arquivo mestre de parâmetros biológicos (BEIR).
        filters : dict, optional
            Dicionário contendo critérios de filtragem (sexo, órgãos, etc).
        """
        self.input_folder = input_folder
        self.exposure_age = exposure_age
        self.current_age = current_age
        self.output_folder = output_folder
        self.params_file = params_file
        self.filters = filters if filters else {}

    def run(self) -> None:
        """
        Executa o pipeline completo de forma síncrona.

        Fluxo de Execução:
        ------------------
        1. **Prepara Ambiente:** Cria pastas de saída e gera Timestamp único para a execução.
        2. **Etapa 1 (Extração):** Instancia e executa `ExtratorHotspot`. Gera CSV '1_hotspot_extract'.
        3. **Checkpoint:** Verifica sucesso da extração.
        4. **Etapa 2 (Transposição):** Instancia e executa `TranspositorHotspot`. Gera CSV '2_hotspot_transpose'.
        5. **Checkpoint:** Verifica sucesso da transposição.
        6. **Etapa 3 (Cálculo):** Instancia e executa `CalculadoraRisco`. Gera CSVs finais de risco e Logs.

        Tratamento de Erros:
        --------------------
        Falhas em qualquer etapa interrompem a cadeia e registram o erro no Log global, garantindo
        que não sejam gerados resultados parciais ou inválidos.
        """
        try:
            os.makedirs(self.output_folder, exist_ok=True)
            
            # Gera timestamp único para rastreabilidade da execução
            now = datetime.now()
            ts = now.strftime("%Y%m%d%H%M%S")
            
            # Definição dos nomes dos artefatos intermediários
            csv_tabular = os.path.join(self.output_folder, f'1_hotspot_extract_ee{int(self.exposure_age)}_ea{int(self.current_age)}_{ts}.csv')
            csv_transposed = os.path.join(self.output_folder, f'2_hotspot_transpose_ee{int(self.exposure_age)}_ea{int(self.current_age)}_{ts}.csv')
            
            # -------------------------------------------------------------
            # Etapa 1: Extração (Ingestão de Dados Brutos)
            # -------------------------------------------------------------
            extractor = ExtratorHotspot(self.input_folder, csv_tabular)
            extractor.extract()
            
            # -------------------------------------------------------------
            # Etapa 2: Transposição (Transformação Estrutural)
            # -------------------------------------------------------------
            if os.path.exists(csv_tabular):
                transposer = TranspositorHotspot(csv_tabular, csv_transposed)
                transposer.transpose()
            else:
                logging.error("Arquivo CSV Tabular de entrada não encontrado. Abortando transposição.")
                return

            # -------------------------------------------------------------
            # Etapa 3: Cálculo de Risco (Modelagem BEIR V/VII)
            # -------------------------------------------------------------
            if os.path.exists(csv_transposed):
                calculator = CalculadoraRisco(
                    input_csv=csv_transposed,
                    params_file=self.params_file,
                    output_folder=self.output_folder,
                    exposure_age=self.exposure_age,
                    current_age=self.current_age,
                    timestamp=ts,
                    filters=self.filters
                )
                calculator.calculate()
            else:
                logging.error("Arquivo CSV Transposto não encontrado. Abortando cálculo de risco.")
                return

            print('Pipeline executado com sucesso.')
            logging.info('Pipeline executado com sucesso.')

        except Exception as e:
            logging.error(f"Erro Crítico no Pipeline HotSpot: {e}")
            print(f"Erro ao executar o pipeline: {e}")

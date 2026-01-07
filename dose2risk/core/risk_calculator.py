import math
import logging
import os
import json
from typing import Tuple, Dict, Any, Optional, Union
import pandas as pd
from datetime import datetime
import hashlib
import platform
import getpass
import sys
from dose2risk.core.validator import validate_risk_parameters
from dose2risk.core.reporter import ValidationReporter

class CalculadoraRisco:
    """
    Motor computacional para estimativa de Risco Radiológico Biológico.

    Esta classe implementa os algoritmos de cálculo de Excesso de Risco Relativo (ERR) e 
    Risco Atribuível ao Longo da Vida (LAR), baseando-se nos relatórios científicos BEIR.

    Arquitetura Híbrida:
    --------------------
    O sistema decide dinamicamente qual modelo matemático aplicar para cada célula de cálculo
    (combinação de Órgão Específico vs. Cenário de Exposição), baseado na dose absorvida:
    
    1. **Modelo BEIR VII (Fase 2):** Aplicado para doses baixas (< 100 mSv). Ideal para exposições ambientais.
       Incorpora o fator de redução DDREF e dependências complexas de idade.
    2. **Modelo BEIR V (1990):** Aplicado para doses altas (>= 100 mSv) ou acidentais.
       Utiliza modelos lineares-quadráticos robustos para regimes de alta taxa de dose.

    Outras Responsabilidades:
    -------------------------
    - Leitura e fusão de dados de entrada (Doses) com parâmetros biológicos (Coeficientes de Risco).
    - Mapeamento de anatomia do HotSpot para órgãos epidemiológicos do BEIR.
    - Geração de Logs de Auditoria detalhados para rastreabilidade matemática.
    - Formatação de saída em CSV científico.
    """
    def __init__(self, input_csv: str, params_file: str, output_folder: str, exposure_age: float, current_age: float, model: str = 'auto', timestamp: Optional[str] = None, filters: Dict[str, Any] = None) -> None:
        """
        Inicializa a Calculadora de Risco.

        Args:
            input_csv (str): Caminho para o CSV transposto contendo as doses.
            params_file (str): Caminho para o arquivo JSON de configurações dos modelos BEIR.
            output_folder (str): Diretório para salvar os arquivos de resultado.
            exposure_age (float): Idade na exposição.
            current_age (float): Idade atual (na avaliação).
            model (str, optional): 'auto', 'vii' (BEIR VII), ou 'v' (BEIR V). Padrão é 'auto'.
            timestamp (str, optional): String de data/hora personalizada para nomeação de arquivos.
            filters (dict, optional): Filtros de processamento (sexo, órgãos, colunas, limite 4Sv).
        """
        self.input_csv = input_csv
        self.params_file = params_file
        self.output_folder = output_folder
        self.exposure_age = exposure_age
        self.current_age = current_age
        self.model = model
        self.timestamp = timestamp
        self.filters = filters if filters else {}

    def beir_vii_risk(self, beta: float, gamma: float, eta: float, dose_Sv: float, age_exp: float, age_att: float, model_type: str, latency: float, ddref: float, beta_M: Any, beta_F: Any, theta: Any, delta: Any, phi: Any, e_star: float, organ: Optional[str] = None, baseline_rate: Optional[float] = None, scenario: Optional[str] = None, sex: Optional[str] = None) -> Tuple[float, str]:
        """
        Calcula o Excesso de Risco Relativo (ERR) utilizando o formalismo matemático do relatório BEIR VII (Fase 2).

        Este método resolve as equações diferenciais parametrizadas para estimar o risco estocástico de indução
        de câncer em regimes de baixa transferência linear de energia (LET) e baixas doses.

        O modelo distingue fundamentalmente entre cânceres sólidos e leucemia devido às diferenças na
        cinética biológica e dependência temporal da indução.

        Parâmetros Matemáticos:
        -----------------------
        beta (float): Coeficiente angular primário de risco (slope factor), dependente do sexo e do tipo de câncer.
        gamma (float): Coeficiente de modificação exponencial pela idade na exposição (sensibilidade etária).
        eta (float): Expoente de decaimento ou incremento do risco em função da idade atingida (efeito temporal).
        dose_Sv (float): Dose absorvida equivalente em Sieverts (Sv).
        age_exp (float): Idade do indivíduo no momento da exposição à radiação.
        age_att (float): Idade atual (attained age) para a qual o risco está sendo projetado.
        model_type (str): Tipo do modelo a ser aplicado ('solid' para tumores sólidos ou 'leukemia' para leucemias).
        latency (float): Período de latência biológica mínima (anos) antes que o risco se manifeste.
        ddref (float): Fator de Eficácia de Dose e Taxa de Dose (Dose and Dose-Rate Effectiveness Factor).
                       Utilizado para reduzir o risco estimado linearmente em casos de baixas doses/taxas.
        e_star (float): Variável auxiliar de idade efetiva na exposição, ajustada para modelar a penalidade
                        de risco aumentada em exposições durante a infância e adolescência (geralmente (age_exp - 30)/10).
        theta, delta, phi (Any): Parâmetros específicos para a equação complexa de Leucemia (modelo linear-quadratico modificado).

        Retorna:
        --------
        Tuple[float, str]
            - excess (float): O valor calculado do Excesso de Risco Relativo (ERR) adimensional.
            - eq_symbolic (str): A representação simbólica da equação utilizada, essencial para auditoria e validação.
        """
        try:
            # ---------------------------------------------------------
            # Variáveis Auxiliares de Cálculo
            # a: Idade atingida (attained age)
            # D: Dose absorvida (Sieverts)
            # t: Tempo decorrido desde a exposição (anos)
            # ---------------------------------------------------------
            a = age_att
            D = dose_Sv
            t = age_att - age_exp
            
            # Validação do Período de Latência
            # Se o tempo decorrido for menor que a latência biológica do câncer, o risco é nulo.
            if t < latency:
                 return 0.0, f"ERR = 0 (Tempo decorrido {t:.1f} < Latência {latency})"

            # ---------------------------------------------------------
            # Ramo 1: Modelo para Cânceres Sólidos
            # Utiliza uma dependência exponencial da idade de exposição e 
            # uma dependência de potência da idade atingida.
            # ---------------------------------------------------------
            if model_type == 'solid':
                # Representação simbólica para auditoria matemática
                eq_symbolic = "ERR = beta * dose_Sv * exp(gamma * e_star) * (age_after / 60)^eta / ddref"
                
                # Cálculo termo a termo para precisão numérica
                term_exp = math.exp(gamma * e_star)       # Fator de sensibilidade à idade de exposição
                term_age = pow(a / 60, eta)               # Fator de evolução com a idade atingida
                
                # O ERR bruto é calculado linearmente com a dose e ajustado pelos termos temporais
                err_calc = beta * D * term_exp * term_age
                
                # Aplicação do DDREF para correção de baixa dose/taxa de dose
                excess = err_calc / ddref 

            # ---------------------------------------------------------
            # Ramo 2: Modelo para Leucemia
            # Utiliza um modelo linear-quadrático (D + theta*D^2) com 
            # dependência temporal complexa (log do tempo desde exposição).
            # ---------------------------------------------------------
            else:
                # Representação simbólica da equação complexa de Leucemia
                eq_symbolic = "ERR = beta * dose_Sv * (1 + theta * dose_Sv) * exp(gamma * e_star + delta * log(time_since_exposure/25) + phi * e_star * log(time_since_exposure/25))"
                
                if t <= 0:
                     excess = 0.0
                else:
                    # Termos de ajuste temporal logarítmico
                    log_t_25 = math.log(t / 25)
                    
                    # Expoente composto que combina idade na exposição e tempo decorrido
                    term_exp_inner = gamma * e_star + delta * log_t_25 + phi * e_star * log_t_25
                    term_exp = math.exp(term_exp_inner)
                    
                    # Cálculo final combinando componente linear-quadrática da dose com o termo temporal
                    # Nota: Leucemias geralmente não aplicam DDREF da mesma forma que sólidos no BEIR VII,
                    # pois a curvatura já é tratada pelo termo quadrático (theta).
                    excess = beta * D * (1 + theta * D) * term_exp

            return excess, eq_symbolic

        except Exception as error:
            logging.error(f"Erro crítico no cálculo BEIR VII: {error}")
            return float('nan'), f"Erro de Execução: {error}"

    def beir_v_risk(self, dose_Sv: float, age_exp: float, age_att: float, sex: str, beir_v_config: Dict[str, Any]) -> Tuple[float, str, Dict[str, Any]]:
        """
        Calcula o Excesso de Risco Relativo (ERR) utilizando os modelos legados do Relatório BEIR V (1990).
        
        Aplicação:
        ----------
        Este método é automaticamente selecionado para doses absorvidas altas (>= 100 mSv) ou cenários
        acidentais onde o modelo linear (LNT) do BEIR VII pode subestimar ou superestimar efeitos determinísticos 
        ou quadráticos.

        Arquitetura Dinâmica:
        ---------------------
        Diferente do BEIR VII, o BEIR V não possui uma Equação Mestra Unificada. Ele define modelos matemáticos
        distintos (Linear, Linear-Quadrático, Dependente do Tempo) para diferentes grupos de órgãos.
        Nesta implementação v2.0, os coeficientes não são "hardcoded", mas injetados via arquivo de 
        configuração JSON, garantindo flexibilidade e agnosticismo do código.

        Parâmetros:
        -----------
        dose_Sv (float): Dose absorvida em Sieverts.
        age_exp (float): Idade na exposição.
        age_att (float): Idade atingida (no momento da avaliação de risco).
        sex (str): Sexo do indivíduo ('male' ou 'female').
        beir_v_config (dict): Dicionário contendo a configuração do modelo ('model_type') e seus parâmetros ('params').

        Retorna:
        --------
        Tuple[float, str, dict]
            - O valor numérico do ERR.
            - A string da equação simbólica usada.
            - Dicionário com parâmetros extras calculados ou utilizados (ex: coeficientes Alpha).
        """
        try:
            D = dose_Sv
            t = age_att - age_exp
            
            # Verificação de segurança temporal
            if t < 0: 
                return 0.0, "ERR = 0 (Tempo de projeção negativo)", {}
            
            # Extração da estratégia de modelo do JSON
            model_type = beir_v_config.get('model_type', 'linear_other')
            params = beir_v_config.get('params', {})
            extra_params = {}

            eq_symbolic = ""
            result = 0.0

            # -------------------------------------------------------------------------
            # 1. LEUCEMIA (Modelo Linear-Quadrático com Janelas Temporais)
            # -------------------------------------------------------------------------
            # O modelo de leucemia do BEIR V é altamente sensível ao tempo decorrido
            # desde a exposição, com coeficientes que mudam abruptamente em janelas
            # de 15, 25 e 30 anos.
            # -------------------------------------------------------------------------
            if model_type == 'leukemia_lq':
                ALPHA2 = params.get('alpha2', 0.243)
                ALPHA3 = params.get('alpha3', 0.271)
                extra_params['ALPHA2'] = ALPHA2
                extra_params['ALPHA3'] = ALPHA3
                
                # ---------------------------------------------------------------------
                # Implementação Genérica Baseada em Configuração (JSON)
                # ---------------------------------------------------------------------
                # 'time_windows' definida no arquivo de parâmetros.
                # ---------------------------------------------------------------------
                time_windows = params.get('time_windows', [])
                beta = -999.0 # Valor padrão (risco nulo/janela excedida)

                # 1. Seleciona o bloco de regras baseado na Idade de Exposição
                selected_block = None
                for block in time_windows:
                    if age_exp <= block.get('max_age_exposure', 999):
                        selected_block = block
                        break
                
                # 2. Se encontrou um bloco aplicável, verifica o Tempo Decorrido (t) dentro das janelas
                if selected_block:
                    beta = selected_block.get('fallback_beta', -999.0)
                    for interval in selected_block.get('intervals', []):
                        if t <= interval['max_years_since']:
                            beta = interval['beta']
                            break
                
                # Caso de fallback para compatibilidade se o JSON antigo for usado (Hardcoded Backup)
                # Pode ser removido futuramente se garantirmos migração total do JSON
                if not time_windows:
                   if age_exp <= 20:
                        if t <= 15: beta = 4.885
                        elif t <= 25: beta = 2.380
                        else: beta = -999.0
                   else: 
                        if t <= 25: beta = 2.367
                        elif t <= 30: beta = 1.638
                        else: beta = -999.0
                
                # Registro do coeficiente temporal calculado para auditoria
                extra_params['Internal_Beta_V'] = beta
                
                # Verificação se caiu fora da janela de risco
                if beta == -999.0:
                    result = 0.0
                    eq_symbolic = "ERR = 0 (Janela de tempo de risco para Leucemia excedida)"
                else:
                    # Inserimos o valor de beta na string da equação para facilitar validação visual
                    eq_symbolic = f"ERR = ({ALPHA2:.3f} * dose_Sv + {ALPHA3:.3f} * dose_Sv^2) * exp({beta:.3f})"
                    term_quad = (ALPHA2 * D + ALPHA3 * D**2)
                    term_exp = math.exp(beta)
                    result = term_quad * term_exp

            # -------------------------------------------------------------------------
            # 2. MAMA (Câncer de Mama - Modelo Dependente da Idade)
            # -------------------------------------------------------------------------
            # Este modelo se aplica exclusivamente ao sexo feminino e varia o coeficiente
            # de risco baseando-se em faixas etárias na exposição (<15, <25, <35, etc).
            # -------------------------------------------------------------------------
            elif model_type == 'breast_age_dependent':
                if sex != 'female': 
                    result = 0.0
                    eq_symbolic = "ERR = 0 (Risco de Câncer de Mama aplicável apenas para sexo feminino neste modelo)"
                else:
                    brackets = params.get('age_brackets', [])
                    coef = params.get('default_coef', 0.1)
                    
                    # Seleção do coeficiente apropriado para a faixa etária
                    for b in brackets:
                        if age_exp < b['max_age']:
                            coef = b['coef']
                            break
                    
                    extra_params['Internal_Coef_V'] = coef

                    # Nota de Implementação: Mantida consistência com conversão de unidades legada.
                    # A multiplicação por 2.0 é um fator de escala específico derivado da metodologia original.
                    eq_symbolic = f"ERR = {coef} * 2.0 * dose_Sv" 
                    result = coef * 2.0 * D

            # -------------------------------------------------------------------------
            # 3. TIREOIDE (Alta Sensibilidade Infantil)
            # -------------------------------------------------------------------------
            # O risco para tireoide é drasticamente maior para exposições na infância/adolescência.
            # O modelo aplica um 'threshold' (limiar) de idade para trocar o coeficiente.
            # -------------------------------------------------------------------------
            elif model_type == 'thyroid_age_dependent':
                threshold = params.get('threshold_age', 18)
                c_young = params.get('coef_young', 7.5)
                c_adult = params.get('coef_adult', 0.5)
                
                coef = c_young if age_exp < threshold else c_adult
                extra_params['Internal_Coef_V'] = coef
                
                eq_symbolic = f"ERR = {coef} * dose_Sv"
                result = coef * D

            # -------------------------------------------------------------------------
            # 4. MODELOS LINEARES GERAIS (Digestivo, Respiratório, Outros)
            # -------------------------------------------------------------------------
            # Para a maioria dos órgãos sólidos no BEIR V, assume-se uma relação linear simples,
            # sem complexidade temporal ou quadratica, diferenciando-se apenas pelo sexo.
            # -------------------------------------------------------------------------
            elif model_type in ['linear', 'linear_digestive', 'linear_other']:
                raw_coef = params.get('coef')
                
                if isinstance(raw_coef, dict):
                    sex_key = 'M' if sex == 'male' else 'F'
                    coef = raw_coef.get(sex_key, 0.0)
                else:
                    coef = float(raw_coef)
                
                extra_params['Internal_Coef_V'] = coef

                eq_symbolic = f"ERR = {coef} * dose_Sv"
                result = coef * D

            else:
                 # Tratamento de erro para tipos de modelo desconhecidos
                 result = 0.0
                 eq_symbolic = f"Modelo Desconhecido ou Não Implementado ({model_type})"

            return result, eq_symbolic, extra_params

        except Exception as e:
            logging.error(f"Exceção no cálculo BEIR V para o modelo {model_type}: {e}")
            return float('nan'), f"Erro Interno: {e}", {}

    def _calculate_file_hash(self, filepath: str) -> str:
        """
        Calcula o hash SHA-256 de um arquivo para garantir integridade e não-repúdio.
        
        Args:
            filepath (str): Caminho absoluto do arquivo.
            
        Returns:
            str: Hash SHA-256 hexadecimal.
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                # Leitura em blocos de 4K para eficiência de memória
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            return "HASH_ERROR_OR_FILE_NOT_FOUND"

    def calculate(self):
        """
        Método Orquestrador (Mestre) do fluxo de cálculo de risco.

        Este método gerencia todo o pipeline de processamento, desde a ingestão de dados
        até a exportação dos resultados finais e auditoria.

        Fluxo de Execução:
        ------------------
        1. **Inicialização**: Prepara diretórios de saída e configura o sistema de logging dedicado.
        2. **Ingestão**: Carrega a matriz de doses (CSV) e os parâmetros biológicos (JSON).
        3. **Iteração Matricial**: Percorre cada Célula de Cálculo (Combinação única de Orgão x Cenário x Sexo).
        4. **Tomada de Decisão (Switch de Modelo)**:
           - Analisa a dose absorvida na célula.
           - Se Dose < 100 mSv: Seleciona Modelo BEIR VII (Baixa Dose).
           - Se Dose >= 100 mSv: Seleciona Modelo BEIR V (Alta Dose).
        5. **Computação**: Executa o cálculo de ERR (Excesso de Risco Relativo) e LAR (Risco Atribuível ao Longo da Vida).
        6. **Auditoria**: Registra um LOG granular detalhando qual equação e parâmetros foram usados para CADA ponto de dado.
        7. **Exportação**: Consolida os resultados em um DataFrame Pandas e exporta para CSV formatado.

        Exceções:
        ---------
        Erros durante o processamento de uma linha específica são logados, mas tentam não interromper
        o processo global a menos que sejam críticos (ex: falha de I/O).
        """
        try:
            os.makedirs(self.output_folder, exist_ok=True)
            ts = self.timestamp if self.timestamp else datetime.now().strftime("%Y%m%d%H%M%S")
            base_filename = f"3_calculated_risks_ERR_LAR_ee{int(self.exposure_age)}_ea{int(self.current_age)}_{ts}"
            base_log = f"4_execution_log_ee{int(self.exposure_age)}_ea{int(self.current_age)}_{ts}"
            
            out_csv = os.path.join(self.output_folder, base_filename + ".csv")
            out_log = os.path.join(self.output_folder, base_log + ".log")

            # Configuração de Log
            logger = logging.getLogger()
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            
            file_handler = logging.FileHandler(out_log, mode='w', encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            # Removemos a formatação de mensagem padrão para permitir payload JSON puro no campo 'message'
            # O timestamp e levelname ainda são úteis fora do JSON para grep rápido
            formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.setLevel(logging.INFO)
            
            # ---------------------------------------------------------------------
            # HEADER DE AUDITORIA (Integridade e Ambiente)
            # ---------------------------------------------------------------------
            input_hash = self._calculate_file_hash(self.input_csv)
            params_hash = self._calculate_file_hash(self.params_file)
            
            audit_header = {
                "Event": "EXECUTION_START",
                "Timestamp_ISO": datetime.now().isoformat(),
                "Environment": {
                    "User": getpass.getuser(),
                    "Host": platform.node(),
                    "OS": platform.system(),
                    "Python_Version": sys.version.split()[0]
                },
                "Inputs_Integrity": {
                    "Dose_Matrix_CSV": self.input_csv,
                    "Dose_Matrix_Hash_SHA256": input_hash,
                    "Params_JSON": self.params_file,
                    "Params_JSON_Hash_SHA256": params_hash
                },
                "Configuration": {
                    "Exposure_Age": self.exposure_age,
                    "Attained_Age": self.current_age,
                    "Model_Override": self.model
                }
            }
            logging.info(f"METADATA_HEADER: {json.dumps(audit_header, ensure_ascii=False)}")
            
            try:
                if not os.path.exists(self.input_csv):
                   logging.error(f"Arquivo de entrada não encontrado: {self.input_csv}")
                   return
    
                df_doses = pd.read_csv(self.input_csv, sep=';', decimal='.')
                
                # Carregar Parâmetros JSON
                with open(self.params_file, 'r') as f:
                    config_data = json.load(f)
                
                # Validação de Schema (Audit REC-01) - Fail Fast
                validate_risk_parameters(config_data)
                
                risk_configs = config_data.get('configurations', {})

                # Tratamento e Renomeação
                if 'organ/stabiliy_class_dose_class_distance_km' in df_doses.columns:
                    df_doses = df_doses.rename(columns={'organ/stabiliy_class_dose_class_distance_km': 'organ'})
                else:
                    logging.error("Coluna 'organ/stabiliy_class_dose_class_distance_km' não encontrada.")
                    return

                scenarios = [c for c in df_doses.columns if c not in ['organ', 'row_id']]
                final_rows = []
                
                # Não fazemos mais merge com CSV. Iteramos e buscamos no dict.

                # Extração de Filtros
                selected_organs = self.filters.get('organs') # Se None, processa todos?
                selected_sexes = self.filters.get('sexes', ['M', 'F'])
                selected_models = self.filters.get('models', ['ERR', 'LAR'])
                show_4sv = self.filters.get('show_4sv', True)

                # Tracking para Supressão de Colunas (>4Sv)
                # Dicionário: { 'cenario_X': {'total': 0, 'high_dose': 0} }
                scenario_stats = {c: {'total': 0, 'high_dose': 0} for c in scenarios}

                for sex_code in ['M', 'F']:
                    sex = 'male' if sex_code == 'M' else 'female'
                    
                    # Filtro de Sexo
                    if sex_code not in selected_sexes:
                        continue

                    for idx, row in df_doses.iterrows():
                        organ = row['organ']
                        
                        # Filtro de Órgão
                        # Se selected_organs for None ou vazio E filters foi passado como dict vazio (default init), 
                        # assumimos processar tudo?
                        # Se filters foi populado via UI, 'organs' será uma lista.
                        # Lógica: Se self.filters não estiver vazio, respeitar estritamente a lista.
                        if self.filters and selected_organs is not None:
                             if organ not in selected_organs:
                                 continue
                        
                        # Extração antecipada do ID para logs de erro
                        row_id_val = row.get('row_id')
                        if pd.isna(row_id_val):
                            row_id_val = idx + 1
                        row_id_safe = int(row_id_val)

                        # Busca Configuração do Órgão
                        if organ not in risk_configs:
                            warn_payload = {
                                "Row_ID": row_id_safe,
                                "Context": f"{sex}|{organ}",
                                "Status": "SKIPPED",
                                "Reason": "Órgão não encontrado no JSON de parâmetros (risk_parameters.json).",
                                "Action": "Ignorando linha de cálculo."
                            }
                            logging.warning(f"CONFIG_WARNING: {json.dumps(warn_payload, ensure_ascii=False)}")
                            continue
                            
                        org_config = risk_configs[organ]
                        
                        # Extração BEIR VII Params do JSON
                        vii_conf = org_config.get('beir_vii', {})
                        v_conf = org_config.get('beir_v', {})
                        
                        vii_params = vii_conf.get('params', {})
                        model_type = vii_conf.get('model_type', 'solid')
                        latency = vii_conf.get('latency', 5)
                        ddref = vii_conf.get('ddref', 1.0)
                        
                        # Baseline Incidence e Beir Eq
                        organ_beir = org_config.get('beir_VII_equivalence', organ)
                        base_inc_dict = org_config.get('baseline_incidence', {})
                        base_inc = base_inc_dict.get(sex_code, 0.0)
                        
                        # Parâmetros Específicos VII
                        # Helper local para conversão segura
                        def safe_cast(v: Any) -> float:
                            try:
                                if v == "N/A" or v is None:
                                    return float('nan')
                                return float(v)
                            except (ValueError, TypeError):
                                return float('nan')

                        # Parâmetros Específicos VII
                        gamma = safe_cast(vii_params.get('gamma', 0.0))
                        eta = safe_cast(vii_params.get('eta', 0.0))
                        theta = safe_cast(vii_params.get('theta', "N/A"))
                        delta = safe_cast(vii_params.get('delta', "N/A"))
                        phi = safe_cast(vii_params.get('phi', "N/A"))
                        
                        # Beta pode ser dict ou valor (ex testes/uterus só tem 1 sexo)
                        raw_beta = vii_params.get('beta')
                        beta_val = 0.0
                        if isinstance(raw_beta, dict):
                             beta_val = raw_beta.get(sex_code, "N/A")
                        else:
                             beta_val = raw_beta
                        
                        beta = safe_cast(beta_val)
                        
                        # Mapeamento para log/CSV legado (apenas visualização)
                        beta_M = raw_beta.get('M', "N/A") if isinstance(raw_beta, dict) else raw_beta
                        beta_F = raw_beta.get('F', "N/A") if isinstance(raw_beta, dict) else raw_beta

                        res_row = {
                            'sex': sex,
                            'age_at_exposure': int(self.exposure_age),
                            'attained_age': int(self.current_age)
                        }
                        
                        # ID Linkage (Agora validado pelo valor antecipado)
                        res_row['row_id'] = row_id_safe


                        row_extra_params = {'ALPHA2': "N/A", 'ALPHA3': "N/A"}

                        if self.exposure_age < 30:
                            e_star = (self.exposure_age - 30)/10
                        else:
                            e_star = 0

                        # Variáveis para coleta de metadados da linha
                        used_models_set = set() # Modelos únicos usados (ex: {'BEIR_VII'} ou {'BEIR_VII', 'BEIR_V'})
                        used_err_eqs_set = set() # Equações simbólicas únicas usadas
                        logged_combinations = set()

                        # Cálculo por Cenário
                        for cen in scenarios:
                            dose_Sv = float(row.get(cen, 0.0))
                            if pd.isna(dose_Sv): dose_Sv = 0.0
                            
                            scenario_stats[cen]['total'] += 1

                            dose_mSv_check = dose_Sv * 1000.0

                            if dose_mSv_check > 4000:
                                result_skipped_high_dose = True
                                scenario_stats[cen]['high_dose'] += 1 # Contabiliza falha por dose alta
                                
                                err_val = "N/A"
                                lar_val = "N/A"
                                model_name = "N/A"

                                log_details = {
                                    "Row_ID": row_id_safe,
                                    "Context": f"{sex}|{organ}|{cen}",
                                    "Status": "SKIPPED",
                                    "Reason": "dose acima de 4000 mSv",
                                    "Dose_Measured_mSv": f"{dose_mSv_check:.2f}",
                                    "Result_ERR": "N/A",
                                    "Result_LAR": "N/A"
                                }
                                logging.warning(f"CALC_LOG: {json.dumps(log_details, ensure_ascii=False)}")

                            elif math.isnan(beta):
                                err_val = "N/A" # String para indicar dado ausente no CSV
                                lar_val = "N/A"
                                model_name = "N/A"
                                used_err_eq = "Coeficiente Inexistente para o Sexo"

                                # ---------------------------------------------------------------------
                                # AUDIT LOG para Casos Ignorados (N/A)
                                # ---------------------------------------------------------------------
                                # Essencial para rastreabilidade: documenta explicitamente por que o cálculo
                                # foi pulado (ex: câncer de mama em homens, próstata em mulheres).
                                # ---------------------------------------------------------------------
                                log_details = {
                                    "Row_ID": row_id_safe,
                                    "Context": f"{sex}|{organ}|{cen}",
                                    "Status": "SKIPPED",
                                    "Reason": "Modelo biológico não aplicável para este sexo (Coeficiente Beta = NaN)",
                                    "Result_ERR": "N/A",
                                    "Result_LAR": "N/A"
                                }
                                # Loga como INFO mas com status SKIPPED claro no JSON
                                logging.warning(f"CALC_LOG: {json.dumps(log_details, ensure_ascii=False)}")

                            else:
                                # ---------------------------------------------------------------------
                                # Lógica de Seleção Híbrida de Modelo (High Dose vs Low Dose)
                                # ---------------------------------------------------------------------
                                # O limiar de 100 mSv (0.1 Sv) é um consenso comum em proteção radiológica.
                                # Abaixo deste valor, predominam os efeitos estocásticos modelados pelo BEIR VII
                                # com fator de redução (DDREF). Acima, aproxima-se de regimes determinísticos
                                # ou lineares-quadráticos puros do BEIR V.
                                # ---------------------------------------------------------------------
                                if self.model == 'auto':
                                    limit_mSv = 100
                                    dose_mSv = dose_Sv * 1000
                                    modelo = 'vii' if dose_mSv < limit_mSv else 'v'
                                else:
                                    modelo = self.model
                                
                                # Define o nome do modelo usado
                                if modelo == 'vii':
                                    model_name = "BEIR_VII"
                                    err_val, eq_s = self.beir_vii_risk(
                                        beta=beta, gamma=gamma, eta=eta, dose_Sv=dose_Sv, 
                                        age_exp=self.exposure_age, age_att=self.current_age, 
                                        model_type=model_type, latency=latency, ddref=ddref, 
                                        beta_M=beta_M, beta_F=beta_F, theta=theta, delta=delta, 
                                        phi=phi, e_star=e_star, organ=organ, 
                                        baseline_rate=base_inc, scenario=cen, sex=sex
                                    )
                                    row_extra_params['ALPHA2'] = "N/A"
                                    row_extra_params['ALPHA3'] = "N/A"
                                else:
                                    model_name = "BEIR_V"
                                    # Passamos o config do BEIR V direto
                                    err_val, eq_s, extras = self.beir_v_risk(
                                        dose_Sv=dose_Sv, age_exp=self.exposure_age, 
                                        age_att=self.current_age, sex=sex,
                                        beir_v_config=v_conf
                                    )
                                    if extras:
                                        row_extra_params.update(extras)
                                
                                used_models_set.add(model_name)
                                used_err_eqs_set.add(eq_s)
                                
                                lar_val = err_val * base_inc
                                
                                # Logging Inteligente:
                                # Registra um log de auditoria detalhado para cada célula calculada.
                                # Isso permite rastrear exatamente por que um valor de risco foi gerado,
                                # inspecionando as variáveis intermediárias que não vão para o CSV final.
                                log_details = {
                                    "Row_ID": row_id_safe,
                                    "Context": f"{sex}|{organ}|{cen}",
                                    "Dose_Sv": f"{dose_Sv:.4e}",
                                    "Dose_mSv": f"{dose_Sv*1000:.2f}",
                                    "Model": model_name,
                                    "Result_ERR": f"{err_val:.4e}" if isinstance(err_val, float) else str(err_val),
                                    "Result_LAR": f"{lar_val:.4e}" if isinstance(lar_val, float) else str(lar_val),
                                    "Equation": eq_s,
                                    "Baseline_Incidence": f"{base_inc:.2e}",
                                    "Params": {}
                                }
                                
                                if model_name == "BEIR_VII":
                                    log_details["Params"] = {
                                        "Model_Type": model_type,
                                        "Latency": latency,
                                        "DDREF": ddref,
                                        "Gamma": gamma,
                                        "Eta": eta,
                                        "Beta": beta,
                                        "Theta": theta,
                                        "Delta": delta,
                                        "Phi": phi,
                                        "E_Start": f"{e_star:.2f}"
                                    }
                                else: # Modelo BEIR V
                                    log_details["Params"] = extras
                                    # Detalhes internos (Coef/Beta) já foram populados pelo método beir_v_risk,
                                    # garantindo transparência total no log.

                                logging.info(f"CALC_LOG: {json.dumps(log_details, ensure_ascii=False)}")

                            # Atribuição final para o dicionário de resultados que irá para o CSV
                            res_row[f"dose_Sv_{cen}"] = dose_Sv
                            res_row[f"model_{cen}"] = model_name
                            
                            if isinstance(err_val, str) and err_val == "N/A":
                                res_row[f'ERR_{cen}'] = "N/A"
                                res_row[f'LAR_{cen}'] = "N/A"
                                # Para efeito de supressão, N/A já foi contado se foi por high dose
                            else:
                                res_row[f'ERR_{cen}'] = f"{err_val:.2e}"
                                res_row[f'LAR_{cen}'] = f"{lar_val:.2e}"

                        # Consolidação das Equações Usadas
                        # Como cada cenário (coluna de dose) pode ter usado um modelo diferente (V ou VII) dependendo da magnitude da dose,
                        # agregamos todas as equações simbólicas únicas usadas nesta linha (órgão) para referência no CSV.
                        # Se houver mistura de modelos, ambas as equações aparecerão separadas por pipe "|".
                        res_row['used_ERR_eq'] = " | ".join(sorted(list(used_err_eqs_set))) if used_err_eqs_set else "N/A"
                        
                        # Padronização final da equação LAR
                        res_row['used_LAR_eq'] = "LAR = ERR * baseline_incidence"
                        
                        # Lógica de N/A para parâmetros
                        is_leukemia_vii = (model_type == 'leukemia')
                        
                        res_row['hotspot_organ'] = organ
                        res_row['beir_VII_organ_equivalence'] = organ_beir
                        res_row['model_type'] = model_type
                        res_row['latency'] = latency
                        
                        res_row['ddref'] = ddref if not is_leukemia_vii else "N/A"
                        res_row['gamma'] = gamma
                        res_row['eta'] = eta if not is_leukemia_vii else "N/A"
                        
                        res_row['beta_M'] = beta_M
                        res_row['beta_F'] = beta_F
                        
                        res_row['theta'] = theta if is_leukemia_vii else "N/A"
                        res_row['delta'] = delta if is_leukemia_vii else "N/A"
                        res_row['phi'] = phi if is_leukemia_vii else "N/A"
                        
                        res_row['baseline_incidence_M'] = row.get('baseline_incidence_M', "N/A")
                        res_row['baseline_incidence_F'] = row.get('baseline_incidence_F', "N/A")
                        
                        res_row['ALPHA2'] = row_extra_params['ALPHA2']
                        res_row['ALPHA3'] = row_extra_params['ALPHA3']

                        final_rows.append(res_row)

                # Criar DataFrame
                df_final = pd.DataFrame(final_rows)
                
                # Definição Dinâmica de Colunas baseada nos Filtros
                cols = ['row_id', 'sex', 'age_at_exposure', 'attained_age', 'hotspot_organ', 'beir_VII_organ_equivalence']
                
                # Lista de cenários a serem removidos (Supressão 4Sv)
                scenarios_to_suppress = []
                if not show_4sv:
                    for cen, stats in scenario_stats.items():
                        # Se total > 0 (evita div por zero) E total == high_dose (100% dos dados filtrados por dose alta)
                        if stats['total'] > 0 and stats['total'] == stats['high_dose']:
                            scenarios_to_suppress.append(cen)
                
                for cen in scenarios:
                    # Se cenário marcado para supressão, pula todas as colunas dele
                    if cen in scenarios_to_suppress:
                        continue
                        
                    # Coluna de Dose sempre vai? "Suprimir grupo de colunas (dose_Sv_..., model_..., ERR_..., LAR_...)"
                    cols.append(f"dose_Sv_{cen}")
                    cols.append(f"model_{cen}")
                    
                    if 'ERR' in selected_models:
                         cols.append(f"ERR_{cen}")
                    if 'LAR' in selected_models:
                         cols.append(f"LAR_{cen}")
                
                # Extensão final de colunas (se houver metadados adicionais futuros)
                # Nota: Detalhes finos de parâmetros foram removidos do CSV para evitar poluição visual,
                # mantendo-os acessíveis via Log de Auditoria (.log)
                
                # Filtrar colunas existentes (necessário pois dynamic cols podem não estar no df se logic falhar)
                # Porém df_final tem tudo que foi colocado em res_row.
                # Precisamos garantir que df_final tenha as chaves.
                # As chaves foram inseridas: dose_Sv_{cen}, model_{cen}, ERR_{cen}, LAR_{cen}.
                # Se filtramos colunas aqui (ex: removemos LAR do 'cols'), o to_csv abaixo vai respeitar 'cols'.
                
                # Verificação se df_final não está vazio
                if df_final.empty:
                     # Cria df vazio com as colunas esperadas para não quebrar contrato?
                     df_final = pd.DataFrame(columns=cols)
                
                existing_cols = [c for c in cols if c in df_final.columns or c in cols] # Mantém cols mesmo que vazias?
                # Ajuste: df_final pode ter rows com chaves extras que não queremos (ex: LAR se filtro desligado),
                # ou pode não ter chaves se o filtro as removeu?
                # O 'res_row' populou tudo. O 'cols' define o que sai.
                # O df_final criado a partir de list dicts tem todas chaves.
                
                df_final = df_final[[c for c in cols if c in df_final.columns]]

                df_final.to_csv(out_csv, sep=';', index=False, decimal='.', float_format='%.2e')
                
                # ---------------------------------------------------------------------
                # FOOTER DE ENCERRAMENTO (Confirmação de Sucesso)
                audit_footer = {
                    "Event": "EXECUTION_END",
                    "Timestamp_ISO": datetime.now().isoformat(),
                    "Status": "SUCCESS",
                    "Output_Generated": out_csv,
                    "Total_Rows_Processed": len(df_final)
                }
                
                logging.info(f"METADATA_footer: {json.dumps(audit_footer, ensure_ascii=False)}")
                
                # Geração do Relatório de Validação HTML (REC-03)
                try:
                    reporter = ValidationReporter(out_log, self.output_folder)
                    reporter.generate_report()
                except Exception as report_err:
                    logging.error(f"Failed to generate HTML report: {report_err}")
            
            except Exception as inner_e:
                # Loga o erro em formato JSON estruturado antes de subir a exceção
                error_log = {
                    "Event": "EXECUTION_FAILURE",
                    "Timestamp_ISO": datetime.now().isoformat(),
                    "Error_Type": type(inner_e).__name__,
                    "Error_Message": str(inner_e)
                }
                logging.error(f"CRITICAL_FAILURE: {json.dumps(error_log, ensure_ascii=False)}")
                raise inner_e
                
            finally:
                file_handler.close()
                logger.removeHandler(file_handler)
            
        except Exception as e:
             print(f"Erro ao calcular riscos: {e}")


import os
import re
import logging
import pandas as pd

class ExtratorHotspot:
    """
    Classe responsável pela extração e análise de dados provenientes dos arquivos de saída do software HotSpot.

    O HotSpot gera relatórios em formato texto (.txt) contendo simulações de dispersão atmosférica e dosimetria.
    Esta classe processa esses arquivos não estruturados, aplica expressões regulares (Rgx) para identificar
    parâmetros físicos e meteorológicos, e estrutura os dados em formato tabular (CSV).

    Principais Funcionalidades:
    --------------------------
    - Varredura de diretórios em busca de arquivos de output do HotSpot.
    - Parsing inteligente de números, tratando notação científica e formatação local (vírgula/ponto).
    - Extração de metadados do cabeçalho (ex: altura da chaminé, velocidade do vento, classe de estabilidade).
    - Extração de tabelas de dose por órgão e distância.
    - Adição de um identificador único sequencial (`row_id`) para rastreabilidade.

    Atributos:
    ----------
    input_folder : str
        Caminho absoluto ou relativo para a pasta contendo os arquivos .txt do HotSpot.
    output_file : str
        Caminho completo onde o arquivo CSV consolidado será salvo.
    """
    def __init__(self, input_folder, output_file):
        """
        Inicializa a instância do ExtratorHotspot.

        Parâmetros:
        -----------
        input_folder : str
            Diretório de origem contendo os arquivos brutos (.txt).
        output_file : str
            Arquivo de destino (.csv) para os dados estruturados.
        """
        self.input_folder = input_folder
        self.output_file = output_file

    def parse_number(self, s):
        """
        Converte uma string numérica bruta em um objeto float do Python, com tratamento robusto de erros.
        
        O formato de saída do HotSpot pode variar dependendo da configuração de localidade do sistema operacional 
        (uso de vírgula vs. ponto decimal) e da magnitude do valor (notação científica 'E', 'e' ou ausência dela).

        Lógica de Conversão:
        1. Remove espaços em branco.
        2. Normaliza separadores decimais (substitui ',' por '.').
        3. Remove caracteres não numéricos espúrios, mantendo apenas dígitos, '.', '+', '-' e 'E'.
        4. Tenta a conversão direta para float.

        Parâmetros:
        -----------
        s : str ou int ou float
            A string ou valor numérico a ser convertido.

        Retorna:
        --------
        float
            O valor numérico convertido. Retorna `float('nan')` caso a conversão falhe.
        """
        try:
            s = str(s).strip().replace(',', '.')
            # Sanitização: mantém apenas caracteres válidos para notação científica
            s = re.sub(r'[^0-9.\+\-eE]', '', s)
            return float(s)
        except Exception as e:
            logging.error(f"Erro de conversão numérica para o valor '{s}': {e}")
            return float('nan')

    def parse_hotspot_file(self, path):
        """
        Processa (parse) um único arquivo de saída do HotSpot, extraindo metadados e dados tabulares.

        Esta função lê o arquivo linha a linha, identifica padrões de cabeçalho (utilizando Regex) 
        para capturar variáveis ambientais (vento, estabilidade, etc.) e itera sobre as seções de 
        dados de dose para extrair valores específicos por órgão e distância.

        Parâmetros:
        -----------
        path : str
            Caminho completo do arquivo .txt a ser processado.

        Retorna:
        --------
        list[dict]
            Uma lista de dicionários, onde cada dicionário representa uma linha consolidada de dados 
            (metadados do cenário + dados de dose para uma distância específica).
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            text = ''.join(lines)
        except Exception as e:
            logging.error(f"Falha crítica ao ler o arquivo {path}: {e}")
            return []

        # -----------------------------------------------------------------------------
        # Dicionário de Padrões Regex (Expressões Regulares)
        # -----------------------------------------------------------------------------
        # Mapeia chaves normalizadas (nomes de variáveis) para padrões de busca no texto bruto.
        # Captura metadados cruciais de física de dispersão e geometria de irradiação.
        # -----------------------------------------------------------------------------
        header_patterns = {
            'physical_stack_height_m': r'Physical Stack Height\s*:\s*([^\s]+)\s*m',
            'stack_exit_velocity_m_s': r'Stack Exit Velocity\s*:\s*([^\s]+)\s*m/s',
            'stack_diameter_m': r'Stack Diameter\s*:\s*([^\s]+)\s*m',
            'stack_effluent_temp_deg_c': r'Stack Effluent Temp\.\s*:\s*([^\s]+)\s*deg C',
            'air_temperature_deg_c': r'Air Temperature\s*:\s*([^\s]+)\s*deg C',
            'effective_release_height_m': r'Effective Release Height\s*:\s*([^\s]+)\s*m',
            'wind_speed_h=10_m_m_s': r'Wind Speed \(h=10 m\)\s*:\s*([^\s]+)\s*m/s',
            'wind_direction_degrees': r'Wind Direction\s*:\s*([0-9]+,[0-9]+)\s*degrees',
            'wind_from_the': r'Wind Direction\s*:\s*[0-9]+,[0-9]+\s*degrees\s*Wind from the\s*([A-Za-z]+)',
            'wind_speed_h=h-eff_m_s': r'Wind Speed \(h=H-eff\)\s*:\s*([^\s]+)\s*m/s',
            'stability_class': r'Stability Class[^:]*:\s*([A-Za-z])',
            'receptor_height_m': r'Receptor Height\s*:\s*([^\s]+)\s*m',
            'inversion_layer_height': r'Inversion Layer Height\s*:\s*([^\s]+)',
            'sample_time_min': r'Sample Time\s*:\s*([^\s]+)\s*min',
            'breathing_rate_m3_sec': r'Breathing Rate\s*:\s*([^\s]+)\s*m3/sec',
            'distance_coordinates': r'Distance Coordinates\s*:\s*(\S+)',
            'maximum_dose_distance_km_': r'Maximum Dose Distance\s*:\s*([^\s]+)\s*km',
            'maximum_tede_sv': r'Maximum TEDE\s*:\s*([^\s]+)\s*Sv',
            'inner_contour_dose_sv': r'Inner\s*Contour Dose\s*:\s*([^\s]+)\s*Sv',
            'middle_contour_dose_sv': r'Middle Contour Dose\s*:\s*([^\s]+)\s*Sv',
            'outer_contour_dose_sv': r'Outer\s*Contour Dose\s*:\s*([^\s]+)\s*Sv',
            'exceeds_inner_dose_out_to_km': r'Exceeds Inner\s*Dose Out To\s*:\s*([^\s]+)\s*km',
            'exceeds_middle_dose_out_to_km': r'Exceeds Middle Dose Out To\s*:\s*([^\s]+)\s*km',
            'exceeds_outer_dose_out_to_km': r'Exceeds Outer Dose Out To\s*:\s*([^\s]+)\s*km',
        }
        header_vals = {}
        for key, pat in header_patterns.items():
            m = re.search(pat, text)
            if not m:
                header_vals[key] = None
            else:
                val = m.group(1).strip()
                if key in ('stability_class', 'inversion_layer_height', 'distance_coordinates', 'wind_from_the'):
                    header_vals[key] = val
                else:
                    # Parse numérico robusto para campos quantitativos
                    header_vals[key] = self.parse_number(val)
        rows = []
        i = 0
        
        # -----------------------------------------------------------------------------
        # Loop Principal de Parsing de Linhas
        # -----------------------------------------------------------------------------
        # Itera pelo arquivo identificando blocos de dados tabulares.
        # O cabeçalho do HotSpot é seguido por múltiplas tabelas, uma para cada distância.
        # -----------------------------------------------------------------------------
        while i < len(lines):
            line = lines[i]
            # Detecção de início de linha de dados: Procura padrão "distância, dose" (ex: "0.03, 1.5E-2")
            if re.match(r'^\s*\d+,\d+', line):
                tokens = re.split(r'\s+', line.strip())
                
                # Desestruturação dos dados principais da linha
                dist, tede, resp_int, ground_surf, ground_shine, arrival = tokens[:6]
                
                # Inicializa linha com metadados do cabeçalho
                row = dict(header_vals)
                row.update({
                    'distance_km': self.parse_number(dist),
                    'tede_sv': self.parse_number(tede),
                    'respirable_time-integrated_air_concentration_bq-sec_m3': self.parse_number(resp_int),
                    'ground_surface_deposition_kbq_m2': self.parse_number(ground_surf),
                    'ground_shine_dose_rate_sv_hr': self.parse_number(ground_shine),
                    'arrival_time_hour:min': arrival.strip('<>'), # Remove marcadores de tempo
                })
                
                # Avança cursor para ler bloco de órgãos
                j = i + 1
                while j < len(lines) and '[' not in lines[j]:
                    j += 1
                
                # Extração dos dados de dose por órgão (formato: "Nome do Órgão.....[Valor]")
                while j < len(lines) and '[' in lines[j]:
                    for org, val in re.findall(r'([A-Za-z ]+?)\.+\[(.*?)\]', lines[j]):
                        col = org.strip().lower().replace(' ', '_')
                        row[col] = self.parse_number(val)
                    j += 1
                
                # Extração de componentes específicos de dose (Inalação, Submersão, Solo)
                for label, colname in [
                    ('Inhalation', 'inhalation_plume_passage'),
                    ('Submersion', 'submersion_plume_passage'),
                    ('Ground Shine', 'ground_shine'),
                ]:
                    while j < len(lines) and label not in lines[j]:
                        j += 1
                    if j < len(lines):
                        m2 = re.search(rf'{label}\s*:\s*([^\s]+)', lines[j])
                        row[colname] = self.parse_number(m2.group(1)) if m2 else None
                    j += 1
                
                rows.append(row)
                i = j
            else:
                # Avança linha se não for começo de bloco de dados
                i += 1
        return rows

    def extract(self):
        """
        Executa o fluxo completo de extração: varredura, processamento e persistência.

        1. Varre o diretório `input_folder` em busca de arquivos `.txt`.
        2. Para cada arquivo, invoca `parse_hotspot_file` para extrair os dados.
        3. Consolida todos os dados extraídos em um único DataFrame do Pandas.
        4. Adiciona uma coluna `row_id` sequencial para garantir integridade referencial.
        5. Exporta o resultado para um arquivo CSV estruturado (`output_file`).

        Tratamento de Exceções:
        -----------------------
        Erros de I/O ou parsing são logados, mas não interrompem a execução de outros arquivos, 
        garantindo a resiliência do pipeline.
        """
        try:
            all_lines = []
            if not os.path.exists(self.input_folder):
                logging.error(f"Pasta de entrada não encontrada: {self.input_folder}")
                return

            for fn in sorted(os.listdir(self.input_folder)):
                if fn.lower().endswith('.txt'):
                    # Processamento sequencial de cada arquivo de simulação encontrados
                    all_lines.extend(self.parse_hotspot_file(os.path.join(self.input_folder, fn)))
            
            # Definição do esquema de colunas para o DataFrame Pandas
            columns = [
                'physical_stack_height_m','stack_exit_velocity_m_s','stack_diameter_m',
                'stack_effluent_temp_deg_c','air_temperature_deg_c','effective_release_height_m',
                'wind_speed_h=10_m_m_s','wind_direction_degrees','wind_from_the',
                'wind_speed_h=h-eff_m_s','stability_class','receptor_height_m','inversion_layer_height',
                'sample_time_min','breathing_rate_m3_sec','distance_coordinates',
                'maximum_dose_distance_km_','maximum_tede_sv','inner_contour_dose_sv',
                'middle_contour_dose_sv','outer_contour_dose_sv','exceeds_inner_dose_out_to_km',
                'exceeds_middle_dose_out_to_km','exceeds_outer_dose_out_to_km',
                'distance_km','tede_sv','respirable_time-integrated_air_concentration_bq-sec_m3',
                'ground_surface_deposition_kbq_m2','ground_shine_dose_rate_sv_hr',
                'arrival_time_hour:min','skin','surface_bone','spleen','breast','uli_wall','thymus',
                'kidneys','pancreas','lung','red_marrow','ovaries','stomach_wall','lli_wall',
                'esophagus','testes','brain','thyroid','liver','adrenals','si_wall','bladder_wall',
                'muscle','uterus','inhalation_plume_passage','submersion_plume_passage','ground_shine'
            ]
            
            # Garante a existência do diretório de saída antes da escrita
            out_dir = os.path.dirname(self.output_file)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            
            df = pd.DataFrame(all_lines, columns=columns)
            
            # Adição de Chave Primária Sintética (Row ID) para rastreabilidade
            df.insert(0, 'row_id', range(1, 1 + len(df)))
            
            df.to_csv(self.output_file, sep=';', index=False, decimal='.', float_format='%.2e')
            logging.info(f"Arquivo CSV Tabular gerado com sucesso: {self.output_file}")
            
        except Exception as e:
            logging.error(f"Erro fatal durante a extração dos arquivos HotSpot: {e}")

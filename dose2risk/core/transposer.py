
import pandas as pd
import logging
import os

class TranspositorHotspot:
    """
    Classe responsável pela transformação estrutural (transposição) dos dados de dose.

    O fluxo de dosimetria gera dados em formato "Longo" (Tabular), onde cada linha representa uma distância
    e contém colunas para todos os órgãos. Para o cálculo de risco, é necessário um formato "Largo" ou matriz,
    onde cada linha é um Órgão e cada coluna representa um Cenário (combinação de Classe de Estabilidade + Distância).

    Esta classe realiza a operação de PIVOT (rotação) da tabela, essencial para que o calculador de risco
    possa iterar vetor por vetor (órgão a órgão) e aplicar os modelos biológicos de forma eficiente.

    Arquitetura de Dados:
    ---------------------
    Transformação de Tidy Data (Long Format) -> Matrix Format (Wide Format).
    Essa etapa é crítica para garantir que todos os cenários de exposição (distâncias e estabilidades atmosféricas)
    estejam alinhados nas colunas para cada órgão alvo.

    Atributos:
    ----------
    input_csv : str
        Caminho para o arquivo CSV tabular gerado pelo Extrator.
    output_csv : str
        Caminho onde a matriz transposta será salva.
    """
    def __init__(self, input_csv, output_csv):
        """
        Inicializa o TranspositorHotspot.

        Parâmetros:
        -----------
        input_csv : str
            Caminho do arquivo CSV de entrada (formato tabular/longo).
        output_csv : str
            Caminho do arquivo CSV de saída (formato matriz/pivotado).
        """
        self.input_csv = input_csv
        self.output_csv = output_csv

    def transpose(self):
        """
        Executa a transposição dos dados (Operação Pivot).

        Algoritmo de Transposição:
        --------------------------
        1. **Carga**: Leitura do arquivo CSV tabular (output da etapa de extração).
        2. **Filtragem de Colunas**: Separação entre metadados estáticos (ex: meteorologia) e variáveis biológicas (órgãos).
        3. **Melting (Unpivot)**: Transformação de colunas de órgãos em linhas, normalizando a tabela para o formato Tidy.
           - De: [Dist, Org1, Org2...]
           - Para: [Dist, 'Org1', Val1], [Dist, 'Org2', Val2]...
        4. **Pivoting (Crosstab)**: Reorganização ortogonal onde os Órgãos tornam-se o índice principal e as
           combinações de Cenário (Estabilidade + Distância) tornam-se as colunas.
        5. **Flattening**: Achatamento do Multi-Index hierárquico resultante das colunas para um formato plano acessível (ex: 'A_0.03').
        6. **Indexação**: Geração de um identificador único (`row_id`) para a nova entidade 'Órgão'.

        Saída:
        ------
        Gera um arquivo CSV matricial otimizado para iteração pelo motor de cálculo de risco.
        """
        try:
            if not os.path.exists(self.input_csv):
                logging.error(f"Arquivo CSV de entrada não encontrado: {self.input_csv}")
                return

            df = pd.read_csv(self.input_csv, sep=';', decimal='.')
            static_cols = [
                'physical_stack_height_m','stack_exit_velocity_m_s','stack_diameter_m',
                'stack_effluent_temp_deg_c','air_temperature_deg_c','effective_release_height_m',
                'wind_speed_h=10_m_m_s','wind_direction_degrees','wind_from_the',
                'wind_speed_h=h-eff_m_s','stability_class','receptor_height_m',
                'inversion_layer_height','sample_time_min','breathing_rate_m3_sec',
                'distance_coordinates','maximum_dose_distance_km_','maximum_tede_sv',
                'inner_contour_dose_sv','middle_contour_dose_sv','outer_contour_dose_sv',
                'exceeds_inner_dose_out_to_km','exceeds_middle_dose_out_to_km',
                'exceeds_outer_dose_out_to_km','distance_km','tede_sv',
                'respirable_time-integrated_air_concentration_bq-sec_m3',
                'ground_surface_deposition_kbq_m2','ground_shine_dose_rate_sv_hr',
                'arrival_time_hour:min','inhalation_plume_passage',
                'submersion_plume_passage','ground_shine'
            ]
            
            # Identifica dinamicamente as colunas de órgãos (aquelas que não estão na lista de colunas estáticas conhecidas)
            organ_cols = [c for c in df.columns if c not in static_cols]
            
            # -------------------------------------------------------------------------
            # Passo 1: Melting (Derretimento / Normalização para Long Format)
            # -------------------------------------------------------------------------
            # Transforma a estrutura "Larga" original (muitas colunas de órgãos) em uma estrutura "Longa".
            # Cria uma tupla única para cada medição (Cenário, Órgão, Valor).
            # -------------------------------------------------------------------------
            df_long = df.melt(
                id_vars=['stability_class','distance_km'],
                value_vars=organ_cols,
                var_name='organ',
                value_name='dose'
            )
            
            # -------------------------------------------------------------------------
            # Passo 2: Pivot (Rotação / Matriz Cruzada)
            # -------------------------------------------------------------------------
            # Reorganiza o DataFrame para que:
            # - Índice (Linhas): Órgãos.
            # - Colunas: Tuplas de (Classe de Estabilidade, Distância).
            # -------------------------------------------------------------------------
            df_pivot = df_long.pivot(
                index='organ',
                columns=['stability_class','distance_km'],
                values='dose'
            )
            
            # -------------------------------------------------------------------------
            # Passo 3: Flattening (Achatamento de Colunas Hierárquicas)
            # -------------------------------------------------------------------------
            # Converte o MultiIndex resultante do pivot (ex: ('A', 0.03)) em strings planas 
            # compatíveis com CSV simples (ex: 'A_0.03').
            # -------------------------------------------------------------------------
            df_pivot.columns = [f"{cls}_{dist}" for cls, dist in df_pivot.columns]
            
            df_pivot = df_pivot.reset_index().rename(
                columns={'organ': 'organ/stabiliy_class_dose_class_distance_km'}
            )
            df_pivot.insert(0, 'row_id', range(1, 1 + len(df_pivot)))
            
            out_dir = os.path.dirname(self.output_csv)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            df_pivot.to_csv(self.output_csv, sep=';', index=False, decimal='.', float_format='%.2e')
            logging.info(f"CSV Transposto gerado com sucesso: {self.output_csv}")
            
        except Exception as e:
            logging.error(f"Erro ao transpor CSV de HotSpot: {e}")

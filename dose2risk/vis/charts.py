import os
import logging
import re
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Configurar backend não-interativo para servidor
matplotlib.use('Agg')

class RiskChartGenerator:
    """
    Gerador de gráficos para visualização de riscos radiológicos (ERR/LAR).
    Gera plots log-lineares similares aos relatórios BEIR/NUREG.
    """
    
    def __init__(self, output_folder: str):
        self.output_folder = output_folder
        self.charts_folder = os.path.join(output_folder, "charts")
        os.makedirs(self.charts_folder, exist_ok=True)
        
        # Estilo "Acadêmico"
        self.markers = {
            'A': 'o', # Círculo
            'B': 's', # Quadrado
            'C': '^', # Triângulo cima
            'D': 'v', # Triângulo baixo
            'E': 'D', # Diamante
            'F': 'P'  # Plus/Pentagon
        }
        self.colors = {
            'A': 'black',
            'B': 'black',
            'C': 'black',
            'D': 'black',
            'E': 'black',
            'F': 'white' # Círculo vazio geralmente em P&B, mas aqui usaremos facecolor 'none'
        }

    def generate_plots(self, df: pd.DataFrame):
        """
        Gera gráficos para cada linha do DataFrame (Combinação Órgão + Sexo).
        
        Espera um DataFrame no formato "wide" produzido pelo RiskCalculator:
        ERR_A_0.03, ERR_A_0.1, ... 
        """
        logging.info("Iniciando geração de gráficos de risco...")
        
        # Identificar colunas de risco e extrair metadados
        # Padrão esperado: {RISK}_{CLASS}_{DISTANCE} ex: ERR_A_0.03
        dist_cols = [c for c in df.columns if c.startswith('ERR_') or c.startswith('LAR_')]
        
        if not dist_cols:
            logging.warning("Nenhuma coluna de risco (ERR/LAR) encontrada para plotagem.")
            return

        # Iterar por cada "Cenário Biológico" (Linha do CSV)
        count = 0
        for idx, row in df.iterrows():
            try:
                self._plot_row(row)
                count += 1
            except Exception as e:
                logging.error(f"Erro ao plotar linha {idx}: {e}")
        
        logging.info(f"Geração de gráficos concluída. {count} figuras geradas.")

    def _plot_row(self, row: pd.Series):
        """Processa uma única linha e gera os gráficos ERR e LAR."""
        organ = row.get('hotspot_organ', 'unknown')
        sex = row.get('sex', 'unknown')
        age_at_exposure = row.get('age_at_exposure', 'N/A')
        
        # Estrutura para armazenar dados extraídos
        # data[RiskType][StabilityClass] = [(Distance, Value), ...]
        data = {'ERR': {}, 'LAR': {}}
        
        # Parsing das colunas
        for col_name, val in row.items():
            # Tenta casar com padrão TYPE_CLASS_DISTANCE
            # Regex: (ERR|LAR)_([A-F])_([0-9.]+)
            match = re.match(r'^(ERR|LAR)_([A-Z])_([0-9.]+)$', str(col_name))
            if match:
                r_type, s_class, dist_str = match.groups()
                
                # Ignorar valores N/A ou inválidos
                try:
                    val_float = float(val)
                    dist_float = float(dist_str)
                    
                    if np.isnan(val_float) or val_float <= 0:
                        continue
                        
                    if s_class not in data[r_type]:
                        data[r_type][s_class] = []
                    
                    data[r_type][s_class].append((dist_float, val_float))
                    
                except (ValueError, TypeError):
                    continue

        # Gerar Plot ERR
        if data['ERR']:
            self._create_figure(data['ERR'], 'ERR', organ, sex, age_at_exposure)
            
        # Gerar Plot LAR
        if data['LAR']:
            self._create_figure(data['LAR'], 'LAR', organ, sex, age_at_exposure)

    def _create_figure(self, class_data: dict, risk_type: str, organ: str, sex: str, age: str):
        """
        Cria e salva a figura usando Matplotlib.
        """
        fig, ax = plt.subplots(figsize=(8, 6))
        
        # Plotar cada Classe de Estabilidade
        # Ordenar classes para legenda consistente
        for s_class in sorted(class_data.keys()):
            points = sorted(class_data[s_class], key=lambda x: x[0]) # Ordenar por distância
            if not points:
                continue
                
            x_vals = [p[0] for p in points]
            y_vals = [p[1] for p in points]
            
            # Estilo específico para simular o artigo (Preto e Branco / Tons de Cinza)
            marker = self.markers.get(s_class, 'o')
            
            # Se for 'F', usamos circulo vazio (ou similar) para contraste, 
            # mas simplificaremos usando markers filled preto para a maioria e F vazio
            if s_class == 'F':
                ax.plot(x_vals, y_vals, label=s_class, marker='o', linestyle='None', 
                        markeredgecolor='black', markerfacecolor='white', markersize=8)
            else:
                ax.plot(x_vals, y_vals, label=s_class, marker=marker, linestyle='None', 
                        color='black', markersize=8, alpha=0.7)

        # Configurações de Eixo estilo Artigo
        ax.set_yscale('log')
        ax.set_xlabel('Location (km)', fontsize=12)
        
        # Título do Eixo Y dinâmico
        # Ex: "ERR leukemia 20 years old male (Sv-1)" - Nota: Unidade Sv-1 é para ERR, LAR é adimensional (probabilidade)
        # O CSV calculator já dá o valor absoluto? O RiskCalculator retorna "excess = err_calc / ddref" ou "lar = err * baseline"
        # O LAR é probabilidade absoluta (adimensional). O ERR geralmente é Sv-1 se for por dose, 
        # mas aqui o valor 'ERR' no CSV já é o calculado (Risco Relativo).
        # Se o valor é ERR, é adimensional (Relative Risk - 1). 
        # Porém, nas figuras do usuário (Fig 3), mostra "ERR ... (Sv-1)". 
        # Isso sugere que eles plotam o COEFICIENTE DE RISCO e não o Risco total?
        # NÃO. O CSV contem "calculated_risks". O método `calculate` faz `beta * D * ...`.
        # Se multiplicou por D (Sv), o resultado é Risco (adimensional).
        # Se a figura diz (Sv-1), ela está mostrando "Excess Relative Risk per Sievert"?
        # O usuário pediu "com base nos cálculos gerados (CSV)". O CSV tem o Risco Absoluto calculado para aquela dose.
        # Vou assumir que o eixo Y é "Risk" (adimensional).
        
        label_sex = "male" if sex == 'male' else "female"
        y_unit = "[dimensionless]" 
        
        ax.set_ylabel(f'{risk_type} {organ} {age}y {label_sex} {y_unit}', fontsize=10)
        
        # Grid
        ax.grid(True, which="both", ls=":", color='gray', alpha=0.5)
        
        # Legenda
        ax.legend(title="Stability Class", bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Ajuste de Layout
        plt.tight_layout()
        
        # Salvar
        safe_organ = str(organ).replace(' ', '_').replace('/', '_')
        filename = f"{risk_type}_{safe_organ}_{sex}_{age}y.png"
        filepath = os.path.join(self.charts_folder, filename)
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close(fig)

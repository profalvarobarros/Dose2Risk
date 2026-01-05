import json
import math
import os
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List

class AuditorConformidadeBeir:
    """
    Auditor independente para verificação de conformidade dos cálculos de risco radiológico
    com os modelos BEIR V e BEIR VII.
    
    Esta classe opera de forma isolada do motor de cálculo principal, utilizando sua própria
    implementação das equações matemáticas para realizar uma "Auditoria Sombra" (Shadow Audit).
    """
    
    TOLERANCIA_NUMERICA = 1e-6 # Tolerância para comparação de float

    def __init__(self, caminho_log_execucao: str, caminho_params_json: str, pasta_saida: str):
        """
        Inicializa o Auditor.

        Args:
            caminho_log_execucao (str): Caminho absoluto para o arquivo de log (.log) gerado pela calculadora.
            caminho_params_json (str): Caminho absoluto para o arquivo de parâmetros (risk_parameters.json).
            pasta_saida (str): Diretório onde o relatório de auditoria será salvo.
        """
        self.caminho_log = caminho_log_execucao
        self.caminho_params = caminho_params_json
        self.pasta_saida = pasta_saida
        self.params_ref = {}
        self.registros_auditoria = []
        self.resumo_auditoria = {
            "total_linhas": 0,
            "aprovados": 0,
            "reprovados": 0,
            "erros_modelo": 0,
            "erros_parametro": 0,
            "erros_calculo": 0
        }

    def carregar_referencias(self):
        """Carrega os parâmetros de referência do arquivo JSON oficial."""
        try:
            with open(self.caminho_params, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                self.params_ref = dados.get('configurations', {})
        except Exception as e:
            raise RuntimeError(f"Falha ao carregar parâmetros de referência: {e}")

    def auditar_execucao(self) -> str:
        """
        Executa o processo principal de auditoria.
        Lê o log linha a linha, valida cada cálculo e gera o relatório final.

        Returns:
            str: Caminho do arquivo de relatório gerado.
        """
        self.carregar_referencias()
        
        arquivo_relatorio = os.path.join(
            self.pasta_saida, 
            f"relatorio_auditoria_beir_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        
        # Variáveis globais da execução (extraídas do Header do Log)
        idade_exposicao = 0.0
        idade_atingida = 0.0
        header_lido = False
        
        try:
            with open(self.caminho_log, 'r', encoding='utf-8') as f_log:
                for linha in f_log:
                    # 1. Tenta capturar o Header de Metadados na primeira passagem
                    if not header_lido and "METADATA_HEADER" in linha:
                        try:
                            json_str = linha.split("METADATA_HEADER:", 1)[1].strip()
                            header_data = json.loads(json_str)
                            config = header_data.get("Configuration", {})
                            idade_exposicao = float(config.get("Exposure_Age", 0))
                            idade_atingida = float(config.get("Attained_Age", 0))
                            header_lido = True
                        except Exception:
                            pass

                    # 2. Processa logs de cálculo
                    if "CALC_LOG:" in linha:
                        try:
                            conteudo_json = linha.split("CALC_LOG:", 1)[1].strip()
                            dados_log = json.loads(conteudo_json)
                            
                            if dados_log.get("Status") == "SKIPPED":
                                continue

                            resultado_auditoria = self._validar_entrada(dados_log, idade_exposicao, idade_atingida)
                            self.registros_auditoria.append(resultado_auditoria)
                            
                            self.resumo_auditoria["total_linhas"] += 1
                            if resultado_auditoria["status_geral"] == "APROVADO":
                                self.resumo_auditoria["aprovados"] += 1
                            else:
                                self.resumo_auditoria["reprovados"] += 1
                                if "MODELO" in resultado_auditoria["erros"]: self.resumo_auditoria["erros_modelo"] += 1
                                if "PARAMETRO" in resultado_auditoria["erros"]: self.resumo_auditoria["erros_parametro"] += 1
                                if "CALCULO" in resultado_auditoria["erros"]: self.resumo_auditoria["erros_calculo"] += 1

                        except json.JSONDecodeError:
                            continue 
                        except Exception as e:
                            self.registros_auditoria.append({
                                "id_linha": "N/A",
                                "status_geral": "ERRO_AUDITORIA",
                                "detalhes": f"Exceção interna no auditor: {str(e)}",
                                "dump_entrada": linha[:100],
                                "trace_calculo": "Erro fatal ao processar linha."
                            })
            
            self._gerar_relatorio_markdown(arquivo_relatorio)
            return arquivo_relatorio

        except FileNotFoundError:
            raise FileNotFoundError(f"Arquivo de log não encontrado: {self.caminho_log}")

    def _validar_entrada(self, dados_log: Dict[str, Any], idade_exp_global: float, idade_att_global: float) -> Dict[str, Any]:
        """
        Audita uma única entrada de cálculo.
        """
        erros = []
        avisos = []
        trace = []
        
        # 1. Extração de Dados do Log
        id_linha = dados_log.get("Row_ID")
        contexto = dados_log.get("Context", "||").split("|")
        if len(contexto) < 3:
             return {"id_linha": id_linha, "status_geral": "FALHA_ESTRUTURA", "erros": ["Estrutura de contexto inválida"], "trace_calculo": "N/A"}
             
        sexo_log = contexto[0]
        orgao_log = contexto[1]
        
        dose_sv = float(dados_log.get("Dose_Sv", 0.0))
        err_sistema = float(dados_log.get("Result_ERR", 0.0))
        modelo_sistema = dados_log.get("Model")
        params_usados = dados_log.get("Params", {})

        sexo_chave = 'M' if sexo_log == 'male' else 'F'
        
        trace.append(f"**Dados de Entrada**: Dose={dose_sv:.6f} Sv, Sexo={sexo_log}, Órgão={orgao_log}")
        trace.append(f"**Idades Agregadas**: Exposição={idade_exp_global}, Atingida={idade_att_global}")

        # 2. Validação da Seleção do Modelo
        modelo_esperado = "BEIR_VII" if dose_sv < 0.1 else "BEIR_V"
        
        if modelo_sistema != modelo_esperado:
            if not math.isclose(dose_sv, 0.1, rel_tol=1e-5):
                erros.append("MODELO")
                avisos.append(f"Seleção de modelo incorreta. Dose requer {modelo_esperado}, usada {modelo_sistema}.")
                trace.append(f"❌ **Decisão de Modelo**: ERRO. Esperado {modelo_esperado} (Dose < 0.1), detectado {modelo_sistema}.")
            else:
                trace.append(f"⚠️ **Decisão de Modelo**: Limiar (Edge Case). Dose aprox 0.1 Sv. Aceito.")
        else:
            trace.append(f"✅ **Decisão de Modelo**: Correta ({modelo_sistema}).")

        # 3. Auditoria e Recálculo
        err_auditor = 0.0
        
        config_orgao = self.params_ref.get(orgao_log)
        if not config_orgao:
            erros.append("CONFIG_AUSENTE")
            return self._formatar_resultado(id_linha, contexto, erros, avisos, err_sistema, 0.0, modelo_sistema, ["Configuração do órgão não encontrada."])

        if modelo_sistema == "BEIR_VII":
            config_vii = config_orgao.get('beir_vii', {})
            params_vii_ref = config_vii.get('params', {})
            
            err_auditor, trace_calc = self._recálculo_sombra_vii(
                dose_sv, 
                params_usados,
                params_vii_ref, 
                sexo_chave,
                idade_exp_global,
                idade_att_global
            )
            trace.extend(trace_calc)
            
        elif modelo_sistema == "BEIR_V":
             err_auditor, trace_calc = self._recalculo_sombra_v(
                 dose_sv, 
                 config_orgao, 
                 sexo_log, 
                 params_usados,
                 idade_exp_global,
                 idade_att_global
             )
             trace.extend(trace_calc)

        # 4. Comparação
        trace.append(f"**Confronto de Resultados**:")
        if math.isnan(err_sistema):
            if not math.isnan(err_auditor):
                 erros.append("CALCULO")
                 trace.append(f"❌ Sistema=NaN vs Auditor={err_auditor:.4e}")
            else:
                 trace.append(f"✅ Ambos NaN (Risco Indefinido)")
        else:
            diferenca = abs(err_sistema - err_auditor)
            if diferenca > self.TOLERANCIA_NUMERICA:
                if err_auditor != 0:
                    erro_rel = diferenca / abs(err_auditor)
                    if erro_rel > 0.01:
                        erros.append("CALCULO")
                        trace.append(f"❌ DISCREPÂNCIA > 1%. Sist: {err_sistema:.4e}, Audit: {err_auditor:.4e}")
                    else:
                         trace.append(f"⚠️ Diferença marginal ({erro_rel:.2%}). Aceitável.")
                else:
                    erros.append("CALCULO")
                    trace.append(f"❌ Erro Crítico. Sist: {err_sistema:.4e} vs Audit: 0.0")
            else:
                trace.append(f"✅ Valores idênticos (Delta={diferenca:.2e}).")

        return self._formatar_resultado(id_linha, contexto, erros, avisos, err_sistema, err_auditor, modelo_sistema, trace)

    def _recálculo_sombra_vii(self, dose: float, params_log: Dict, params_ref: Dict, sexo_chave: str, ie: float, ia: float) -> Tuple[float, List[str]]:
        """Recálculo BEIR VII com trace."""
        trace = []
        tipo_modelo = params_log.get('Model_Type', 'solid')
        
        def get_val(key):
            val = params_ref.get(key)
            if val == "N/A" or val is None: return 0.0
            return float(val)

        beta_raw = params_ref.get('beta')
        if isinstance(beta_raw, dict):
            beta = float(beta_raw.get(sexo_chave, 0.0))
        else:
            beta = float(beta_raw) if beta_raw else 0.0
            
        gamma = get_val('gamma')
        eta = get_val('eta')
        ddref = float(params_log.get('DDREF', 1.0))

        trace.append(f"- **Parâmetros Lidos (JSON)**: Beta={beta}, Gamma={gamma}, Eta={eta}, DDREF={ddref}")

        latencia = float(params_log.get('Latency', 0))
        tempo = ia - ie
        
        if tempo < latencia:
            trace.append(f"- ⚠️ Tempo decorrido ({tempo}) < Latência ({latencia}). Risco = 0.")
            return 0.0, trace

        e_star = (ie - 30) / 10 if ie < 30 else 0
        trace.append(f"- **Variáveis de Idade**: E*={e_star:.2f}, IdadeExp={ie}, IdadeAtt={ia}, Tempo={tempo}")
        
        if tipo_modelo == 'solid':
            # ERR = beta * D * exp(gamma * e_star) * (a/60)^eta / ddref
            termo_exp = math.exp(gamma * e_star)
            termo_age = math.pow(ia / 60, eta)
            
            trace.append(f"- **Termos**: Exp(g*e)={termo_exp:.4f}, PotenciaIdade={termo_age:.4f}")
            
            raw_err = beta * dose * termo_exp * termo_age
            final_err = raw_err / ddref
            trace.append(f"- **Cálculo**: {beta} * {dose:.4f} * {termo_exp:.4f} * {termo_age:.4f} / {ddref}")
            trace.append(f"- **Resultado Final**: {final_err:.6e}")
            return final_err, trace
            
        else: # leukemia
            theta = get_val('theta')
            delta = get_val('delta')
            phi = get_val('phi')
            
            trace.append(f"- **Params Leucemia**: Theta={theta}, Delta={delta}, Phi={phi}")
            
            if tempo <= 0: return 0.0, trace
            
            log_t_25 = math.log(tempo / 25)
            termo_inner = (gamma * e_star) + (delta * log_t_25) + (phi * e_star * log_t_25)
            termo_temporal = math.exp(termo_inner)
            
            trace.append(f"- **Termo Temporal**: Exp({termo_inner:.4f}) = {termo_temporal:.4f}")
            
            quad_dose = (1 + theta * dose)
            final_err = beta * dose * quad_dose * termo_temporal
            trace.append(f"- **Cálculo**: {beta} * {dose:.4f} * (1 + {theta}*{dose:.4f}) * {termo_temporal:.4f}")
            return final_err, trace

    def _recalculo_sombra_v(self, dose: float, config_orgao: Dict, sexo: str, params_log: Dict, ie: float, ia: float) -> Tuple[float, List[str]]:
        """Recálculo BEIR V com trace."""
        trace = []
        conf_v = config_orgao.get('beir_v', {})
        tipo_modelo = conf_v.get('model_type', 'linear')
        params_v = conf_v.get('params', {})
        
        tempo = ia - ie
        trace.append(f"- **Modelo Selecionado**: BEIR_V / {tipo_modelo}")
        
        if tempo < 0: return 0.0, trace
        
        if tipo_modelo == 'leukemia_lq':
            alpha2 = params_v.get('alpha2', 0.243)
            alpha3 = params_v.get('alpha3', 0.271)
            
            time_windows = params_v.get('time_windows', [])
            beta = -999.0
            
            # Trace da busca logica
            trace.append("- Buscando Janela Temporal para Leucemia:")
            block_selecionado = None
            for block in time_windows:
                if ie <= block.get('max_age_exposure', 999):
                    block_selecionado = block
                    trace.append(f"  - Bloco Encontrado (Age Exp <= {block.get('max_age_exposure')})")
                    break
            
            if block_selecionado:
                beta = block_selecionado.get('fallback_beta', -999.0)
                for interval in block_selecionado.get('intervals', []):
                    if tempo <= interval['max_years_since']:
                        beta = interval['beta']
                        trace.append(f"  - Intervalo Encontrado (Tempo <= {interval['max_years_since']}): Beta={beta}")
                        break
            
            if beta == -999.0: 
                trace.append("  - ⚠️ Nenhuma janela temporal válida (Risco=0).")
                return 0.0, trace
            
            termo_dose = (alpha2 * dose + alpha3 * (dose**2))
            termo_exp = math.exp(beta)
            res = termo_dose * termo_exp
            
            trace.append(f"- **Cálculo**: ({alpha2}*D + {alpha3}*D^2) * exp({beta})")
            return res, trace

        elif tipo_modelo == 'breast_age_dependent':
            if sexo != 'female': 
                trace.append("- Sexo masculino: Risco Mama = 0.")
                return 0.0, trace
                
            brackets = params_v.get('age_brackets', [])
            coef = params_v.get('default_coef', 0.1)
            for b in brackets:
                if ie < b['max_age']:
                    coef = b['coef']
                    trace.append(f"- Faixa Etária detectada < {b['max_age']}: Coef={coef}")
                    break
            
            res = coef * 2.0 * dose # Fator explicito
            trace.append(f"- **Cálculo**: {coef} * 2.0 * {dose}")
            return res, trace

        elif tipo_modelo == 'thyroid_age_dependent':
            threshold = params_v.get('threshold_age', 18)
            c_young = params_v.get('coef_young', 7.5)
            c_adult = params_v.get('coef_adult', 0.5)
            coef = c_young if ie < threshold else c_adult
            trace.append(f"- Idade Exp {ie} vs Limiar {threshold} -> Coef={coef}")
            return coef * dose, trace

        elif 'linear' in tipo_modelo:
            raw_coef = params_v.get('coef')
            key = 'M' if sexo == 'male' else 'F'
            if isinstance(raw_coef, dict):
                coef = float(raw_coef.get(key, 0.0))
            else:
                coef = float(raw_coef)
            trace.append(f"- Coeficiente Linear: {coef}")
            return coef * dose, trace

        return 0.0, ["Modelo Desconhecido"]

    def _formatar_resultado(self, id_linha, contexto, erros, avisos, sistemat_val, auditor_val, modelo, trace):
        return {
            "id_linha": id_linha,
            "contexto": contexto,
            "status_geral": "REPROVADO" if erros else "APROVADO",
            "erros": erros,
            "avisos": avisos,
            "valor_sistema": sistemat_val,
            "valor_auditor": auditor_val,
            "modelo": modelo,
            "trace": trace
        }

    def _gerar_relatorio_markdown(self, caminho_arquivo: str):
        """Escreve o relatório final completo em Markdown."""
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            f.write(f"# Relatório Detalhado de Auditoria BEIR\n")
            f.write(f"**Data**: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            
            f.write(f"## 1. Resumo Executivo\n")
            f.write(f"- **Total Auditado**: {self.resumo_auditoria['total_linhas']}\n")
            f.write(f"- **Status**: {'✅ APROVADO' if self.resumo_auditoria['reprovados'] == 0 else '⚠️ REPROVADO'}\n\n")
            
            f.write(f"## 2. Auditoria Individual (Linha a Linha)\n")
            f.write(f"> Este relatório contém o rastreamento matemático detalhado de TODAS as linhas processadas.\n\n")
            
            for reg in self.registros_auditoria:
                icon = "✅" if reg['status_geral'] == "APROVADO" else "❌"
                ctx = ' | '.join(reg['contexto'])
                
                f.write(f"### {icon} Linha {reg['id_linha']}: {ctx}\n")
                f.write(f"**Comparativo**: Sistema=`{reg['valor_sistema']:.4e}` | Auditor=`{reg['valor_auditor']:.4e}`\n\n")
                
                if reg['erros']:
                    f.write("**⚠️ Falhas Detectadas:**\n")
                    for e in reg['erros']: f.write(f"- {e}\n")
                    f.write("\n")
                
                f.write("**Rastreamento do Cálculo (Step-by-Step)**:\n")
                for line in reg.get('trace', []):
                    f.write(f"{line}\n")
                
                f.write("\n---\n")


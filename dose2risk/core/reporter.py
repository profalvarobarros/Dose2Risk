
import os
import json
import logging
from datetime import datetime
from jinja2 import Template

# -----------------------------------------------------------------------------
# HTML Template (Embedded for single-file portability)
# -----------------------------------------------------------------------------
# Design militar/científico: Cores sóbrias, foco em dados, layout denso.
REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Relatório de Validação - Dose2Risk</title>
    <style>
        :root {
            --primary-color: #0F172A;
            --accent-color: #0EA5E9;
            --bg-color: #F8FAFC;
            --text-color: #334155;
            --border-color: #E2E8F0;
            --success-color: #10B981;
            --warning-color: #F59E0B;
            --error-color: #EF4444;
        }
        body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg-color); color: var(--text-color); margin: 0; padding: 40px; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border: 1px solid var(--border-color); }
        
        /* Header */
        header { border-bottom: 2px solid var(--primary-color); padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: flex-end; }
        .title h1 { margin: 0; font-size: 24px; color: var(--primary-color); text-transform: uppercase; letter-spacing: 1px; }
        .title span { font-size: 14px; color: #64748B; }
        .meta { text-align: right; font-size: 13px; color: #64748B; font-family: monospace; }

        /* Sections */
        h2 { font-size: 18px; color: var(--primary-color); border-left: 4px solid var(--accent-color); padding-left: 12px; margin-top: 40px; margin-bottom: 20px; }
        
        /* Key Metrics Grid */
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .metric-card { background: #F1F5F9; padding: 15px; border-radius: 6px; border: 1px solid var(--border-color); }
        .metric-card strong { display: block; font-size: 12px; text-transform: uppercase; color: #64748B; margin-bottom: 5px; }
        .metric-card span { font-size: 24px; font-weight: bold; color: var(--primary-color); }
        
        /* Integrity Box (Hash) */
        .integrity-box { background: #FFFBEB; border: 1px solid var(--warning-color); padding: 15px; border-radius: 6px; font-family: monospace; font-size: 12px; overflow-x: auto; }
        .hash-row { display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px dashed #D4D4D8; padding-bottom: 4px; }
        .hash-row:last-child { border: none; margin: 0; padding: 0; }
        .hash-label { font-weight: bold; color: #78350F; min-width: 150px; }
        .hash-value { color: #451A03; }

        /* Tables */
        table { width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 10px; }
        th { text-align: left; background: #F8FAFC; padding: 12px; border-bottom: 2px solid var(--border-color); font-weight: 600; color: var(--text-color); }
        td { padding: 10px 12px; border-bottom: 1px solid var(--border-color); }
        tr:last-child td { border-bottom: none; }
        .status-skipped { color: var(--warning-color); font-weight: bold; }
        
        /* Footer */
        footer { margin-top: 60px; padding-top: 20px; border-top: 1px solid var(--border-color); text-align: center; font-size: 12px; color: #94A3B8; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="title">
                <h1>Relatório de Validação</h1>
                <span>Dose2Risk - Sistema de Cálculo de Risco Radiológico</span>
            </div>
            <div class="meta">
                EXECUÇÃO ID: {{ execution_id }}<br>
                DATA: {{ timestamp }}
            </div>
        </header>

        <!-- Integrity Section -->
        <section>
            <h2>1. Integridade & Rastreabilidade (SHA-256)</h2>
            <div class="integrity-box">
                <div class="hash-row">
                    <span class="hash-label">Input CSV (Doses):</span>
                    <span class="hash-value">{{ hashes.input_csv }}</span>
                </div>
                <div class="hash-row">
                    <span class="hash-label">Parâmetros (JSON):</span>
                    <span class="hash-value">{{ hashes.params_json }}</span>
                </div>
            </div>
        </section>

        <!-- Stats Section -->
        <section>
            <h2>2. Resumo da Execução</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <strong>Total Processado</strong>
                    <span>{{ stats.total_rows }}</span>
                </div>
                <div class="metric-card">
                    <strong>Sucesso</strong>
                    <span style="color: var(--success-color)">{{ stats.success_count }}</span>
                </div>
                <div class="metric-card">
                    <strong>Ignorados (Skipped)</strong>
                    <span style="color: {{ 'var(--warning-color)' if stats.skipped_count > 0 else '#64748B' }}">{{ stats.skipped_count }}</span>
                </div>
                <div class="metric-card">
                    <strong>Modelos (V / VII)</strong>
                    <span>{{ stats.beir_v_count }} / {{ stats.beir_vii_count }}</span>
                </div>
            </div>
        </section>

        <!-- Skipped Details -->
        {% if skipped_items %}
        <section>
            <h2>3. Detalhe de Itens Ignorados</h2>
            <p style="font-size: 14px; color: #64748B;">As seguintes entradas foram ignoradas devido a restrições do modelo ou dados inválidos.</p>
            <table>
                <thead>
                    <tr>
                        <th>Contexto (Sexo|Órgão|Cenário)</th>
                        <th>Dose (Sv)</th>
                        <th>Motivo (Razão Técnica)</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in skipped_items %}
                    <tr>
                        <td>{{ item.context }}</td>
                        <td>{{ item.dose }}</td>
                        <td class="status-skipped">{{ item.reason }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </section>
        {% endif %}

        <footer>
            Gerado automaticamente pelo módulo <code>dose2risk.core.reporter</code><br>
            Este documento serve como evidência de validação técnica da execução.
        </footer>
    </div>
</body>
</html>
"""

class ValidationReporter:
    """
    Gera relatórios HTML de validação para execuções do Dose2Risk.
    Analisa os logs estruturados para compilar estatísticas e provas de integridade.
    """
    
    def __init__(self, log_path: str, output_folder: str):
        self.log_path = log_path
        self.output_folder = output_folder
        self.hashes = {"input_csv": "N/A", "params_json": "N/A"}
        self.stats = {
            "total_rows": 0,
            "success_count": 0,
            "skipped_count": 0,
            "beir_v_count": 0,
            "beir_vii_count": 0
        }
        self.skipped_items = []
        self.execution_meta = {"id": "UNKNOWN", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    def _parse_logs(self):
        """Lê o arquivo de log linha a linha e extrai metadados JSON."""
        if not os.path.exists(self.log_path):
            logging.error(f"Reporter: Arquivo de log não encontrado: {self.log_path}")
            return

        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if "METADATA_HEADER:" in line:
                    try:
                        json_str = line.split("METADATA_HEADER:", 1)[1].strip()
                        meta = json.loads(json_str)
                        self.hashes["input_csv"] = meta.get("Inputs_Integrity", {}).get("Dose_Matrix_Hash_SHA256", "N/A")
                        self.hashes["params_json"] = meta.get("Inputs_Integrity", {}).get("Params_JSON_Hash_SHA256", "N/A")
                        self.execution_meta["timestamp"] = meta.get("Timestamp_ISO", self.execution_meta["timestamp"])
                        # ID simples baseado no timestamp
                        self.execution_meta["id"] = meta.get("Timestamp_ISO", "").replace("-","").replace(":","").replace(".","")
                    except Exception as e:
                        logging.warning(f"Reporter: Erro ao parsear header: {e}")

                elif "CALC_LOG:" in line:
                    try:
                        json_str = line.split("CALC_LOG:", 1)[1].strip()
                        entry = json.loads(json_str)
                        self.stats["total_rows"] += 1
                        
                        if entry.get("Status") == "SKIPPED":
                            self.stats["skipped_count"] += 1
                            self.skipped_items.append({
                                "context": entry.get("Context", "N/A"),
                                "dose": entry.get("Dose_Sv", "N/A") if entry.get("Dose_Sv") else "N/A",
                                "reason": entry.get("Reason", "Unknown")
                            })
                        else:
                            self.stats["success_count"] += 1
                            model = entry.get("Model", "")
                            if "BEIR_V" in model and "VII" not in model: # Simples verificação string
                                self.stats["beir_v_count"] += 1
                            elif "BEIR_VII" in model:
                                self.stats["beir_vii_count"] += 1
                    except Exception:
                        continue

    def generate_report(self):
        """Compila os dados e escreve o relatório HTML."""
        self._parse_logs()
        
        # Renderizar Template
        template = Template(REPORT_TEMPLATE)
        html_content = template.render(
            execution_id=self.execution_meta["id"],
            timestamp=self.execution_meta["timestamp"],
            hashes=self.hashes,
            stats=self.stats,
            skipped_items=self.skipped_items
        )
        
        # Salvar Arquivo
        filename = f"5_validation_report_exec_{self.execution_meta['id'][:14]}.html"
        output_path = os.path.join(self.output_folder, filename)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logging.info(f"AUDIT_SUCCESS: Relatório de validação gerado em {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"Reporter: Falha ao salvar relatório HTML: {e}")
            return None

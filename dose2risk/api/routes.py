
import os
import shutil
import uuid
import zipfile
import io
import logging
from datetime import datetime
import json
from flask import Blueprint, render_template, request, send_from_directory, redirect, url_for, flash, session, current_app, send_file
from flask_babel import gettext as _
from werkzeug.utils import secure_filename
from dose2risk.core.pipeline import HotspotPipeline

main_bp = Blueprint('main', __name__, template_folder='templates', static_folder='static')

EXTENSOES_PERMITIDAS = {'txt'}

def extensao_permitida(nome_arquivo):
    return '.' in nome_arquivo and nome_arquivo.rsplit('.', 1)[1].lower() in EXTENSOES_PERMITIDAS

def validar_arquivo_hotspot(stream):
    """
    Validates if the file resembles a HotSpot report.
    """
    try:
        inicio_arquivo = stream.read(4096).decode('utf-8', errors='ignore')
        stream.seek(0)
        
        palavras_chave_obrigatorias = [
            "HotSpot", "General Plume", "Wind Speed", "Stability Class"
        ]
        
        texto_lower = inicio_arquivo.lower()
        if not all(palavra.lower() in texto_lower for palavra in palavras_chave_obrigatorias):
            return False
            
        return True
    except Exception as e:
        print(f"Error validating file: {e}")
        return False

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/lang/<string:lang>')
def set_language(lang):
    if lang in current_app.config['LANGUAGES']:
        session['lang'] = lang
    else:
        flash(_('Language not supported.'))
    return redirect(request.referrer or url_for('main.index'))

# Static Pages
@main_bp.route('/sobre')
def sobre(): return render_template('sobre.html')

@main_bp.route('/documentacao')
def documentacao(): return render_template('documentacao.html')

@main_bp.route('/tutorial')
def tutorial(): return render_template('tutorial.html')

@main_bp.route('/tutorial/hotspot')
def hotspot_tutorial(): return render_template('hotspot_tutorial.html')

@main_bp.route('/manual_resultados')
def manual_resultados(): return render_template('manual_resultados.html')

@main_bp.route('/manual_logs')
def manual_logs(): return render_template('manual_logs.html')

@main_bp.route('/privacidade')
def privacidade(): return render_template('privacidade.html')

@main_bp.route('/termos')
def termos(): return render_template('termos.html')

@main_bp.route('/suporte')
def suporte(): return render_template('suporte.html')

@main_bp.route('/contato')
def contato(): return render_template('contato.html')

@main_bp.route('/upload', methods=['POST'])
def upload_arquivos():
    try:
        if 'arquivos' not in request.files:
            flash(_('Nenhum campo de arquivo na requisição.'), 'error')
            return redirect(request.url)

        arquivos = request.files.getlist('arquivos')
        
        if not arquivos or all(not f.filename for f in arquivos):
            flash(_('Nenhum arquivo selecionado.'), 'warning')
            return redirect(url_for('main.index'))

        nomes_validos = []
        nomes_invalidos = []
        
        id_execucao = datetime.now().strftime('%Y%m%d%H%M%S') + '_' + str(uuid.uuid4())[:8]
        pasta_upload = os.path.join(current_app.config['UPLOAD_FOLDER'], id_execucao)
        
        for arquivo in arquivos:
            if not arquivo.filename: continue

            nome_seguro = secure_filename(arquivo.filename)
            if extensao_permitida(nome_seguro) and validar_arquivo_hotspot(arquivo.stream):
                os.makedirs(pasta_upload, exist_ok=True)
                caminho = os.path.join(pasta_upload, nome_seguro)
                arquivo.save(caminho)
                nomes_validos.append(nome_seguro)
            else:
                nomes_invalidos.append(nome_seguro)

        if nomes_invalidos:
            msg = _('Arquivos rejeitados: %(files)s', files=', '.join(nomes_invalidos))
            flash(msg, 'error')

        if not nomes_validos:
            if os.path.exists(pasta_upload):
                shutil.rmtree(pasta_upload)
            if not nomes_invalidos:
                 flash(_('Nenhum arquivo válido enviado.'), 'error')
            return redirect(url_for('main.index'))

        return redirect(url_for('main.processar', id_execucao=id_execucao))

    except Exception as e:
        flash(_('Erro durante upload: %(error)s', error=str(e)), 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/processar', methods=['GET', 'POST'])
def processar():
    try:
        id_execucao = request.args.get('id_execucao') or request.form.get('id_execucao')
        if not id_execucao:
            flash(_('Execução não identificada.'))
            return redirect(url_for('main.index'))
            
        pasta_upload = os.path.join(current_app.config['UPLOAD_FOLDER'], id_execucao)
        pasta_saida = os.path.join(current_app.config['OUTPUT_FOLDER'], id_execucao)
        
        if request.method == 'GET':
            # Carregar lista de órgãos para os filtros
            try:
                with open(current_app.config['PARAMS_FILE'], 'r') as f:
                    params_data = json.load(f)
                available_organs = sorted(list(params_data.get('configurations', {}).keys()))
            except Exception as e:
                logging.error(f"Erro ao carregar órgãos para filtro: {e}")
                available_organs = []

            return render_template('form_idades.html', id_execucao=id_execucao, organs=available_organs)
            
        # POST
        idade_exposicao = request.form.get('idade_exposicao', type=float)
        idade_atual = request.form.get('idade_atual', type=float)
        
        # Captura de Filtros Avançados
        filters = {
            'show_4sv': 'filter_4sv' in request.form,
            'sexes': [],
            'models': [],
            'organs': request.form.getlist('filter_organs')
        }
        
        if 'filter_sex_m' in request.form: filters['sexes'].append('M')
        if 'filter_sex_f' in request.form: filters['sexes'].append('F')
        
        if 'filter_model_err' in request.form: filters['models'].append('ERR')
        if 'filter_model_lar' in request.form: filters['models'].append('LAR')

        # Se nenhum órgão selecionado, assume todos (fallback de segurança)
        if not filters['organs']:
             # Recarrega se vazio para garantir processamento completo se user desmarcar tudo sem querer?
             # User disse "todos selecionados por padrão". Se desmarcar, teoricamente não processa nada.
             # Mas vamos manter o comportamento explícito do form.
             pass 

        
        if idade_exposicao is None or idade_atual is None:
            flash(_('Informe as idades corretamente.'))
            return redirect(url_for('main.processar', id_execucao=id_execucao))
            
        if not os.path.exists(pasta_upload) or not os.listdir(pasta_upload):
            flash(_('Arquivos de entrada não encontrados.'))
            return redirect(url_for('main.index'))

        # Generate unique Output ID for this specific run
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        id_saida = f"{id_execucao}_{timestamp}"
        pasta_saida = os.path.join(current_app.config['OUTPUT_FOLDER'], id_saida)

        # Create Snapshot of Input Files (Start)
        # We copy the original uploaded files to a new folder strictly for this processing run
        # This satisfies the requirement: "deve ter uma pasta para cada processamento também" in uploads
        pasta_entrada_snapshot = os.path.join(current_app.config['UPLOAD_FOLDER'], id_saida)
        if not os.path.exists(pasta_entrada_snapshot):
             shutil.copytree(pasta_upload, pasta_entrada_snapshot)
        # (End)

        pipeline = HotspotPipeline(
            input_folder=pasta_entrada_snapshot,
            exposure_age=idade_exposicao,
            current_age=idade_atual,
            output_folder=pasta_saida,
            params_file=current_app.config['PARAMS_FILE'],
            filters=filters
        )
        pipeline.run()
        
        if not os.path.exists(pasta_saida):
             flash(_('Erro: Pasta de saída não criada.'))
             return redirect(url_for('main.index'))

        arquivos_saida = sorted([f for f in os.listdir(pasta_saida) if f.endswith('.csv') or f.endswith('.log') or f.endswith('.html')], reverse=True)
        
        if not arquivos_saida:
            flash(_('Nenhum arquivo de saída gerado.'))
            return redirect(url_for('main.index'))
            
        # Listar gráficos gerados (se houver)
        imagens_graficos = []
        pasta_charts = os.path.join(pasta_saida, 'charts')
        if os.path.exists(pasta_charts):
            imagens_graficos = sorted([f for f in os.listdir(pasta_charts) if f.endswith('.png')])
            
        return render_template('resultado.html', arquivos_saida=arquivos_saida, id_saida=id_saida, id_entrada=id_execucao, imagens_graficos=imagens_graficos)
        
    except Exception as e:
        flash(_('Erro no processamento: %(error)s', error=str(e)))
        return redirect(url_for('main.index'))

@main_bp.route('/download/<id_execucao>/<nome_arquivo>')
def download_arquivo(id_execucao, nome_arquivo):
    try:
        pasta_saida = os.path.join(current_app.config['OUTPUT_FOLDER'], id_execucao)
        return send_from_directory(pasta_saida, nome_arquivo, as_attachment=True)
    except Exception as e:
        flash(_('Erro ao baixar arquivo: %(error)s', error=str(e)))
        return redirect(url_for('main.index'))

@main_bp.route('/download_todos/<id_saida>')
def download_todos(id_saida):
    try:
        pasta_saida = os.path.join(current_app.config['OUTPUT_FOLDER'], id_saida)
        # Snapshot folder uses the same ID in UPLOADS
        pasta_entrada = os.path.join(current_app.config['UPLOAD_FOLDER'], id_saida)
        
        if not os.path.exists(pasta_saida):
            flash(_('Pasta de saída não encontrada.'))
            return redirect(url_for('main.index'))

        # Determine ZIP filename based on log file if possible
        zip_filename = f"Dose2Risk_execution_{id_saida}.zip"
        for f in os.listdir(pasta_saida):
            if f.startswith("4_execution_log_") and f.endswith(".log"):
                # Extract suffix: 4_execution_log_SUFFIX.log -> Dose2Risk_execution_SUFFIX.zip
                suffix = f.replace("4_execution_log_", "").replace(".log", "")
                zip_filename = f"Dose2Risk_execution_{suffix}.zip"
                break

        # Create ZIP in memory
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add Output Files
            # Add Output Files (Recursive)
            for root, dirs, files in os.walk(pasta_saida):
                for file in files:
                    # Inclui tudo (csv, log, html, png, etc) e preserva estrutura de pastas
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, pasta_saida)
                    zf.write(abs_path, arcname=rel_path)
            
            # Add Input Files
            if os.path.exists(pasta_entrada):
                for root, dirs, files in os.walk(pasta_entrada):
                    for file in files:
                         abs_path = os.path.join(root, file)
                         zf.write(abs_path, arcname=f"inputs/{file}")
        
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )

    except Exception as e:
        flash(_('Erro ao gerar ZIP: %(error)s', error=str(e)))
        logging.error(f"Erro ao gerar ZIP: {e}")
        return redirect(url_for('main.index'))

@main_bp.route('/resultados/<id_saida>/charts/<path:filename>')
def serve_chart_image(id_saida, filename):
    """Rota para servir as imagens dos gráficos"""
    try:
        pasta_saida = os.path.join(current_app.config['OUTPUT_FOLDER'], id_saida)
        pasta_charts = os.path.join(pasta_saida, 'charts')
        return send_from_directory(pasta_charts, filename)
    except Exception as e:
        return "Image not found", 404

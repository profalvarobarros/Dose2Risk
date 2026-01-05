
import os
from dotenv import load_dotenv
from flask import Flask, request, session
from flask_babel import Babel

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

babel = Babel()

def get_locale():
    try:
        lang = session.get('lang')
        if lang in {'en', 'es', 'fr', 'pt_BR'}:
            return lang
        return request.accept_languages.best_match(['pt_BR', 'en', 'es', 'fr'])
    except RuntimeError:
        return 'pt_BR'

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    
    # Configuration - Security First
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev_key_fallback_insegura')
    
    # Paths (Assuming run.py is at root)
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'data', 'uploads')
    app.config['OUTPUT_FOLDER'] = os.path.join(base_dir, 'data', 'outputs')
    
    # Configurable Params File
    default_params = os.path.join(base_dir, 'config', 'beir_hotspot_parameters.json')
    app.config['PARAMS_FILE'] = os.getenv('PARAMS_FILE', default_params)
    
    # Babel
    app.config['BABEL_DEFAULT_LOCALE'] = 'pt_BR'
    app.config['LANGUAGES'] = {
        'en': 'English',
        'es': 'Español',
        'fr': 'Français',
        'pt_BR': 'Português'
    }
    
    babel.init_app(app, locale_selector=get_locale)

    # Register Blueprints
    from .routes import main_bp
    app.register_blueprint(main_bp)
    
    # Context Processor
    @app.context_processor
    def inject_locale():
        return dict(get_locale=get_locale)

    return app

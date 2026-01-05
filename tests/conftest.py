import os
import sys
import pytest
from flask import Flask

# Adiciona o diretório raiz ao PYTHONPATH para permitir imports do módulo dose2risk
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dose2risk.api import create_app

@pytest.fixture
def app():
    """Fixture que cria uma instância da aplicação Flask para testes."""
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['FLASK_SECRET_KEY'] = 'test_key'
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    yield app

@pytest.fixture
def client(app):
    """Fixture que fornece um cliente de teste para requisições HTTP."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Fixture para executar comandos da CLI (se houver)."""
    return app.test_cli_runner()

@pytest.fixture
def real_config_path():
    """Retorna o caminho absoluto para o JSON de configuração real."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.join(base_dir, 'config', 'beir_hotspot_parameters.json')

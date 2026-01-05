
import json
import logging
import jsonschema
from jsonschema import validate

# -----------------------------------------------------------------------------
# Definição do Esquema JSON (JSON Schema) para Validação Estrita
# -----------------------------------------------------------------------------
# Este esquema define as regras estruturais e de tipagem para o arquivo
# beir_hotspot_parameters.json. Qualquer desvio (ex: string onde se espera float)
# causará uma falha imediata na validação.
# -----------------------------------------------------------------------------

RISK_PARAMS_SCHEMA = {
    "type": "object",
    "properties": {
        "_metadata": {
            "type": "object",
            "properties": {
                "version": {"type": "string"},
                "description": {"type": "string"},
                "last_update": {"type": "string"}
            },
            "required": ["version"]
        },
        "configurations": {
            "type": "object",
            "patternProperties": {
                "^.*$": {  # Para cada chave de órgão (ex: lung, liver)
                    "type": "object",
                    "properties": {
                        "hotspot_organ": {"type": "string"},
                        "beir_VII_equivalence": {"type": "string"},
                        "baseline_incidence": {
                            "type": "object",
                            "properties": {
                                "M": {"type": "number"},
                                "F": {"type": "number"}
                            },
                            "required": ["M", "F"]
                        },
                        "beir_vii": {
                            "type": "object",
                            "properties": {
                                "model_type": {"type": "string"},
                                "latency": {"type": "number"},
                                "ddref": {"type": "number"},
                                "params": {
                                    "type": "object",
                                    "properties": {
                                        # Parâmetros genéricos podem ser float ou dict (M/F)
                                        "gamma": {"type": ["number", "null"]},
                                        "eta": {"type": ["number", "null"]},
                                        "beta": {
                                            "anyOf": [
                                                {"type": "number"},
                                                {"type": "object", "properties": {"M": {}, "F": {}}}
                                            ]
                                        }
                                    }
                                }
                            }
                        },
                        "beir_v": {
                            "type": "object",
                            "properties": {
                                "model_type": {"type": "string"},
                                "params": {
                                    "type": "object",
                                    "properties": {
                                        "coef": {
                                            "anyOf": [
                                                {"type": "number"},
                                                {"type": "object", "properties": {"M": {}, "F": {}}}
                                            ]
                                        },
                                        "time_windows": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "max_age_exposure": {"type": "number"},
                                                    "intervals": {
                                                        "type": "array",
                                                        "items": {
                                                            "type": "object",
                                                            "properties": {
                                                                "max_years_since": {"type": "number"},
                                                                "beta": {"type": "number"}
                                                            },
                                                            "required": ["max_years_since", "beta"]
                                                        }
                                                    },
                                                    "fallback_beta": {"type": "number"}
                                                },
                                                "required": ["max_age_exposure", "intervals"]
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "required": ["hotspot_organ", "baseline_incidence"]
                }
            }
        }
    },
    "required": ["configurations"]
}

def validate_risk_parameters(json_data: dict) -> bool:
    """
    Valida o dicionário de configuração de risco contra o esquema estrito.
    
    Args:
        json_data (dict): Dicionário carregado do JSON.
        
    Raises:
        jsonschema.ValidationError: Se a validação falhar.
        
    Returns:
        bool: True se válido.
    """
    try:
        validate(instance=json_data, schema=RISK_PARAMS_SCHEMA)
        logging.info("AUDIT_SUCCESS: Arquivo de parâmetros validado com sucesso contra o JSON Schema.")
        return True
    except jsonschema.ValidationError as e:
        error_msg = f"FALHA DE VALIDAÇÃO DE SCHEMA: {e.message} (Caminho: {list(e.path)})"
        logging.error(f"AUDIT_FAILURE: {error_msg}")
        raise e

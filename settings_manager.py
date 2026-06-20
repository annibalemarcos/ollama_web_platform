import os
from pathlib import Path
from typing import Dict

from ai_providers import provider_env_defaults

ENV_PATH = Path(__file__).resolve().parent / ".env"

DEFAULTS = {
    "OLLAMA_API_KEY": "",
    "OLLAMA_LOCAL_URL": "http://127.0.0.1:11434",
    "OLLAMA_MODEL": "gemma3:4b",
    "APP_HOST": "127.0.0.1",
    "APP_PORT": "5388",
    "FLASK_DEBUG": "0",
    "API_HOURLY_LIMIT": "0",
    "API_DAILY_LIMIT": "0",
    "API_WEEKLY_LIMIT": "0",
    "API_MONTHLY_LIMIT": "0",
    "DEFAULT_MAX_RESULTS": "3",
    "MAX_RESULTS_CAP": "5",
    "MAX_SOURCE_CHARS": "1200",
    "MAX_TOTAL_SOURCE_CHARS": "4500",
    "OLLAMA_NUM_CTX": "2048",
    "OLLAMA_NUM_PREDICT": "512",
    "OLLAMA_NUM_THREAD": "2",
    "OLLAMA_KEEP_ALIVE": "0",
    "OLLAMA_REQUEST_TIMEOUT": "600",
    "CLOUD_AI_TIMEOUT": "120",
    "APP_BUSY_REJECT": "1",
    "PC_STATS_ENABLED": "0",
    "READY_MADE_SEARCH_ENABLED": "0",
    "AI_CHATGPT_MODEL": "gpt-4o-mini",
    "AI_PERPLEXITY_MODEL": "sonar",
    "AI_CLAUDE_MODEL": "claude-3-5-haiku-latest",
    "AI_GEMINI_MODEL": "gemini-3.1-flash-lite",
}
DEFAULTS.update(provider_env_defaults())


def read_env_file() -> Dict[str, str]:
    data = DEFAULTS.copy()
    if not ENV_PATH.exists():
        return data

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def write_env_file(updates: Dict[str, str]) -> Dict[str, str]:
    data = read_env_file()
    data.update({k: str(v).strip() for k, v in updates.items() if k in DEFAULTS})

    content = [
        "# Configurações locais do Ollama Web Platform",
        "# Não suba este arquivo para GitHub se ele tiver chave de API.",
        f"OLLAMA_API_KEY={data.get('OLLAMA_API_KEY', '')}",
        f"OLLAMA_LOCAL_URL={data.get('OLLAMA_LOCAL_URL', DEFAULTS['OLLAMA_LOCAL_URL'])}",
        f"OLLAMA_MODEL={data.get('OLLAMA_MODEL', DEFAULTS['OLLAMA_MODEL'])}",
        f"APP_HOST={data.get('APP_HOST', DEFAULTS['APP_HOST'])}",
        f"APP_PORT={data.get('APP_PORT', DEFAULTS['APP_PORT'])}",
        f"FLASK_DEBUG={data.get('FLASK_DEBUG', DEFAULTS['FLASK_DEBUG'])}",
        "",
        "# Limites configuráveis para o painel local de uso.",
        "# Use 0 para desativar. A API da Ollama pode não expor quota restante via endpoint público.",
        f"API_HOURLY_LIMIT={data.get('API_HOURLY_LIMIT', '0')}",
        f"API_DAILY_LIMIT={data.get('API_DAILY_LIMIT', '0')}",
        f"API_WEEKLY_LIMIT={data.get('API_WEEKLY_LIMIT', '0')}",
        f"API_MONTHLY_LIMIT={data.get('API_MONTHLY_LIMIT', '0')}",
        "",
        "# Modo econômico / proteção contra travar o PC",
        f"DEFAULT_MAX_RESULTS={data.get('DEFAULT_MAX_RESULTS', '3')}",
        f"MAX_RESULTS_CAP={data.get('MAX_RESULTS_CAP', '5')}",
        f"MAX_SOURCE_CHARS={data.get('MAX_SOURCE_CHARS', '1200')}",
        f"MAX_TOTAL_SOURCE_CHARS={data.get('MAX_TOTAL_SOURCE_CHARS', '4500')}",
        f"OLLAMA_NUM_CTX={data.get('OLLAMA_NUM_CTX', '2048')}",
        f"OLLAMA_NUM_PREDICT={data.get('OLLAMA_NUM_PREDICT', '512')}",
        f"OLLAMA_NUM_THREAD={data.get('OLLAMA_NUM_THREAD', '2')}",
        f"OLLAMA_KEEP_ALIVE={data.get('OLLAMA_KEEP_ALIVE', '0')}",
        f"OLLAMA_REQUEST_TIMEOUT={data.get('OLLAMA_REQUEST_TIMEOUT', '600')}",
        f"CLOUD_AI_TIMEOUT={data.get('CLOUD_AI_TIMEOUT', '120')}",
        f"APP_BUSY_REJECT={data.get('APP_BUSY_REJECT', '1')}",
        f"PC_STATS_ENABLED={data.get('PC_STATS_ENABLED', '0')}",
        f"READY_MADE_SEARCH_ENABLED={data.get('READY_MADE_SEARCH_ENABLED', '0')}",
        "",
        "# Provedores externos de IA/busca. Chaves ficam locais neste .env.",
    ]
    for key in sorted(k for k in DEFAULTS if k.startswith("AI_")):
        content.append(f"{key}={data.get(key, '')}")
    content.append("")
    ENV_PATH.write_text("\n".join(content), encoding="utf-8")

    for key, value in data.items():
        os.environ[key] = value

    return data


def apply_env_to_process() -> Dict[str, str]:
    data = read_env_file()
    for key, value in data.items():
        os.environ.setdefault(key, value)
    return data


def mask_secret(value: str) -> str:
    if not value:
        return "não definida"
    if len(value) <= 10:
        return "***"
    return f"{value[:6]}...{value[-4:]}"


def as_int(value: str, default: int = 0) -> int:
    try:
        return max(0, int(str(value).strip() or default))
    except ValueError:
        return default
